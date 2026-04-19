"""
Payment API routes
Handles payment initiation, network info, and status polling
"""
import logging
from sqlalchemy import select
from fastapi import APIRouter, HTTPException
from datetime import timedelta
from decimal import Decimal
from uuid import UUID
import uuid

from config import get_settings
from schemas import (
    PaymentInitiateRequest,
    PaymentInitiateResponse,
    PaymentProofSubmitRequest,
    NetworkInfo,
    PaymentStatusResponse,
)
from database import get_session
from models import PendingPayment, Payment, Subscriber, Affiliate
from admin_api.settings_service import (
    build_network_info_list,
    load_effective_admin_settings,
)
from services.blockchain import extract_tx_hash, _now_utc

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/networks", response_model=list[NetworkInfo])
async def get_networks():
    """Get configured payment networks (only those with wallets)"""
    settings = get_settings()
    async with get_session() as session:
        admin_settings = await load_effective_admin_settings(session, settings)
    return build_network_info_list(admin_settings.payment_networks)


@router.post("/initiate", response_model=PaymentInitiateResponse)
async def initiate_payment(request: PaymentInitiateRequest):
    """
    Initiate payment - create pending payment record
    
    POST /api/payment/initiate
    {
        "discord_id": "...",
        "discord_username": "...",
        "tradingview_username": "...",  <- REQUIRED
        "email": "...",
        "affiliate_code": "...",
        "network": "BSC_USDT",
        "sender_wallet": "0x..."
    }
    """
    settings = get_settings()
    normalized_affiliate_code = (request.affiliate_code or "").strip().upper() or None

    async with get_session() as session:
        admin_settings = await load_effective_admin_settings(session, settings)
    network_config = next((network for network in admin_settings.payment_networks if network.network_code == request.network), None)
    
    # Validate TradingView username (done in schema validator, but double-check)
    if not request.tradingview_username or not request.tradingview_username.strip():
        raise HTTPException(
            status_code=400,
            detail="TradingView username is required"
        )
    
    # Validate network is configured
    if not network_config or not network_config.wallet:
        raise HTTPException(
            status_code=400,
            detail=f"Network {request.network} is not configured or has no wallet"
        )
    
    # Get wallet to pay to
    wallet_to_pay = network_config.wallet
    
    # Check affiliate code (if provided)
    discount_applied = Decimal("0")
    discount_percent = Decimal("0")
    
    if normalized_affiliate_code:
        async with get_session() as session:
            affiliate_result = await session.execute(
                select(Affiliate.code, Affiliate.discount_percent).where(
                    Affiliate.code == normalized_affiliate_code,
                    Affiliate.is_active == True,
                )
            )
            affiliate = affiliate_result.mappings().one_or_none()

            if not affiliate:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid or inactive affiliate code"
                )

            discount_percent = Decimal(affiliate["discount_percent"])
            discount_applied = admin_settings.price_per_month_usd * (discount_percent / 100)
    
    # Calculate effective price
    amount_usd = admin_settings.price_per_month_usd - discount_applied
    
    # Create pending payment record
    pending_id = uuid.uuid4()
    pending_expires = _now_utc() + timedelta(hours=settings.PENDING_PAYMENT_TTL_HOURS)
    
    try:
        async with get_session() as session:
            pending = PendingPayment(
                id=pending_id,
                discord_id=request.discord_id,
                discord_username=request.discord_username.strip(),
                tradingview_username=request.tradingview_username.strip(),
                email=request.email,
                wallet_address=request.sender_wallet,
                network=request.network,
                affiliate_code=normalized_affiliate_code,
                amount_expected_usd=amount_usd,
                expires_at=pending_expires,
                tx_hash_proof=None,
            )
            session.add(pending)
            await session.flush()
        
        logger.info(
            f"✓ Pending payment created: {pending_id} for {request.tradingview_username} "
            f"({amount_usd} USD, {request.network})"
        )
        
        return PaymentInitiateResponse(
            pending_id=pending_id,
            wallet_to_pay=wallet_to_pay,
            amount_usd=amount_usd,
            discount_applied=discount_applied,
            network=request.network,
            discount_percent=discount_percent if discount_percent > 0 else None,
        )
    
    except Exception as e:
        logger.error(f"Failed to initiate payment: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to initiate payment"
        )


@router.post("/proof")
async def submit_payment_proof(request: PaymentProofSubmitRequest):
    """
    Submit payment proof after user sends funds.
    Accepts either raw tx hash or explorer URL containing tx hash.
    """
    tx_hash = extract_tx_hash(request.tx_hash_or_url)
    if not tx_hash:
        raise HTTPException(status_code=400, detail="Invalid transaction hash or URL")

    async with get_session() as session:
        pending = await session.scalar(
            select(PendingPayment).where(PendingPayment.id == request.pending_id)
        )

        if not pending:
            raise HTTPException(status_code=404, detail="Pending payment not found")

        if _now_utc() > pending.expires_at:
            raise HTTPException(status_code=400, detail="Pending payment expired")

        existing_tx = await session.scalar(
            select(Payment).where(Payment.tx_hash == tx_hash)
        )
        if existing_tx:
            raise HTTPException(status_code=400, detail="This transaction hash is already used")

        pending.tx_hash_proof = tx_hash

    return {
        "status": "accepted",
        "tx_hash": tx_hash,
        "message": "Proof received. Waiting for on-chain confirmations.",
    }


@router.get("/status/{pending_id}", response_model=PaymentStatusResponse)
async def check_payment_status(pending_id: UUID):
    """
    Check if payment has been detected
    Long-polling endpoint
    
    Response:
    - status: "pending" | "detected" | "expired"
    - tx_hash: (if detected)
    - months_granted: (if detected)
    - expires_at: (if detected)
    """
    async with get_session() as session:
        pending = await session.scalar(
            select(PendingPayment).where(PendingPayment.id == pending_id)
        )

        if not pending:
            raise HTTPException(
                status_code=404,
                detail="Pending payment not found"
            )

        if _now_utc() > pending.expires_at:
            return PaymentStatusResponse(status="expired", tx_hash_proof=pending.tx_hash_proof)

        payment = await session.scalar(
            select(Payment).where(Payment.pending_payment_id == pending_id)
        )

        if payment:
            subscriber = await session.scalar(
                select(Subscriber).where(Subscriber.id == payment.subscriber_id)
            )

            return PaymentStatusResponse(
                status="detected",
                tx_hash_proof=pending.tx_hash_proof,
                tx_hash=payment.tx_hash,
                months_granted=payment.months_granted,
                expires_at=subscriber.expires_at if subscriber else None,
            )

        return PaymentStatusResponse(status="pending", tx_hash_proof=pending.tx_hash_proof)


# Rate limiting will be applied at FastAPI middleware level
# Using slowapi library

"""
On-chain payment verification service for BSC USDT/USDC (EVM) and Solana SPL tokens.
Uses direct RPC nodes and verifies tx proof with confirmation policy.
"""
from __future__ import annotations

import asyncio
import logging
import re
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, Any

from sqlalchemy import select, text
from web3 import Web3
from web3.middleware.geth_poa import geth_poa_middleware

from config import get_settings
from database import get_session
from models import PendingPayment, Subscriber, Payment, Affiliate
from services.discord_service import get_discord_service
from services.guild_settings import load_effective_guild_settings
from admin_api.settings_service import load_effective_admin_settings
from admin_api.settings_service import load_current_payment_networks

logger = logging.getLogger(__name__)

TRANSFER_TOPIC = Web3.keccak(text="Transfer(address,address,uint256)").hex().lower()
TX_HASH_RE = re.compile(r"(0x[a-fA-F0-9]{64})")
PAYMENT_LOG_CHANNEL_CANDIDATE_NAMES = ("payment_logs", "payment-logs", "paymentlogs")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def extract_tx_hash(tx_hash_or_url: str) -> Optional[str]:
    value = (tx_hash_or_url or "").strip()
    if not value:
        return None

    match = TX_HASH_RE.search(value)
    if not match:
        return None

    return match.group(1)


def _normalize_addr(value: str) -> str:
    return (value or "").strip().lower()


def _topic_address(topic_hex: str) -> str:
    # topics are 32-byte padded values; last 20 bytes are the address
    clean = topic_hex.lower().replace("0x", "")
    return f"0x{clean[-40:]}"


def _to_decimal_amount(raw_amount: int, decimals: int) -> Decimal:
    return Decimal(raw_amount) / (Decimal(10) ** Decimal(decimals))


def _log_data_to_int(value: Any) -> int:
    if isinstance(value, str):
        return int(value, 16)

    if isinstance(value, (bytes, bytearray)):
        return int.from_bytes(value, "big")

    return int(value)


def _sanitize_affiliate_code_fragment(value: str, limit: int = 12) -> str:
    cleaned = re.sub(r"[^A-Z0-9]+", "", (value or "").upper())
    return cleaned[:limit]


def _normalize_channel_id(value: Any) -> str | None:
    normalized = str(value or "").strip()
    return normalized or None


async def _resolve_payment_log_channel_id(discord, guild_settings: Any) -> str | None:
    explicit_channel_id = _normalize_channel_id(getattr(guild_settings, "payment_logs_channel_id", None))
    if explicit_channel_id:
        return explicit_channel_id

    discovered_channel_id = await discord.find_guild_channel_by_names(PAYMENT_LOG_CHANNEL_CANDIDATE_NAMES)
    if discovered_channel_id:
        return discovered_channel_id

    return _normalize_channel_id(getattr(guild_settings, "admin_channel_id", None))


async def _send_payment_verification_log(
    discord,
    guild_settings: Any,
    pending: PendingPayment,
    subscriber: Subscriber,
    tx_hash: str,
    amount_usd: Decimal,
    months_granted: int,
    role_assigned: bool,
    dm_sent: bool,
) -> bool:
    channel_id = await _resolve_payment_log_channel_id(discord, guild_settings)
    if not channel_id:
        logger.warning("Payment log channel is not configured and no fallback channel was found")
        return False

    discord_user_display = pending.discord_username or subscriber.discord_username or pending.discord_id
    tradingview_display = pending.tradingview_username or subscriber.tradingview_username or "Unknown"
    expires_at = subscriber.expires_at.isoformat() if subscriber.expires_at else "Not set"
    tx_value = f"`{tx_hash}`"
    if pending.network.startswith("BSC_"):
        tx_value = f"https://bscscan.com/tx/{tx_hash}"

    fields = [
        {"name": "Member", "value": f"<@{pending.discord_id}> (`{pending.discord_id}`)", "inline": False},
        {"name": "Discord", "value": discord_user_display, "inline": True},
        {"name": "TradingView", "value": tradingview_display, "inline": True},
        {"name": "Network", "value": pending.network, "inline": True},
        {"name": "Amount", "value": f"${Decimal(amount_usd):.2f}", "inline": True},
        {"name": "Months Granted", "value": str(months_granted), "inline": True},
        {"name": "Expires At", "value": expires_at, "inline": False},
        {"name": "TX", "value": tx_value, "inline": False},
        {"name": "Submitted Wallet", "value": pending.wallet_address, "inline": False},
        {
            "name": "Automation",
            "value": f"Role assigned: {'yes' if role_assigned else 'no'} | DM sent: {'yes' if dm_sent else 'no'}",
            "inline": False,
        },
    ]

    sent = await discord.send_embed(
        channel_id=channel_id,
        title="Payment Verified",
        description="A subscription payment was verified on-chain and access has been activated.",
        color=0x22C55E,
        fields=fields,
    )

    if sent:
        logger.info("Payment verification log sent to channel %s for %s", channel_id, pending.discord_id)
    else:
        logger.warning("Failed to send payment verification log for %s", pending.discord_id)

    return sent


async def _generate_member_affiliate_code(session, pending: PendingPayment) -> str:
    base_candidates = []
    tradingview_fragment = _sanitize_affiliate_code_fragment(pending.tradingview_username, limit=10)
    discord_tail = re.sub(r"\D+", "", pending.discord_id or "")[-4:]

    if tradingview_fragment:
        base_candidates.append(f"{tradingview_fragment}{discord_tail}"[:20] or tradingview_fragment[:20])

    if discord_tail:
        base_candidates.append(f"TPA{discord_tail}")

    if not base_candidates:
        base_candidates.append(f"TPA{uuid.uuid4().hex[:8].upper()}")

    seen_candidates: list[str] = []
    for candidate in base_candidates:
        normalized = candidate[:20]
        if normalized and normalized not in seen_candidates:
            seen_candidates.append(normalized)

    for candidate in seen_candidates:
        exists = await session.scalar(select(Affiliate.code).where(Affiliate.code == candidate))
        if not exists:
            return candidate

    while True:
        candidate = f"TPA{uuid.uuid4().hex[:8].upper()}"[:20]
        exists = await session.scalar(select(Affiliate.code).where(Affiliate.code == candidate))
        if not exists:
            return candidate


async def _ensure_member_affiliate(session, subscriber: Subscriber, pending: PendingPayment) -> str:
    affiliate_result = await session.execute(
        select(Affiliate.id, Affiliate.code, Affiliate.is_active, Affiliate.name).where(
            Affiliate.discord_id == subscriber.discord_id,
            Affiliate.type == "member",
        )
    )
    affiliate = affiliate_result.mappings().one_or_none()
    if affiliate:
        updates: dict[str, object] = {}
        if not affiliate["is_active"]:
            updates["is_active"] = True
        if not affiliate["name"]:
            updates["name"] = subscriber.tradingview_username or pending.tradingview_username

        if updates:
            set_clause = ", ".join(f"{field} = :{field}" for field in updates)
            updates["id"] = affiliate["id"]
            await session.execute(text(f"UPDATE affiliates SET {set_clause} WHERE id = :id"), updates)

        return affiliate["code"]

    code = await _generate_member_affiliate_code(session, pending)
    await session.execute(
        text(
            """
            INSERT INTO affiliates (
                id, code, discord_id, name, type, discount_percent,
                commission_percent, usage_limit, is_active, created_at
            )
            VALUES (
                :id, :code, :discord_id, :name, :type, :discount_percent,
                :commission_percent, :usage_limit, :is_active, :created_at
            )
            """
        ),
        {
            "id": uuid.uuid4(),
            "code": code,
            "discord_id": subscriber.discord_id,
            "name": subscriber.tradingview_username or pending.tradingview_username,
            "type": "member",
            "discount_percent": Decimal("0"),
            "commission_percent": Decimal("20"),
            "usage_limit": None,
            "is_active": True,
            "created_at": _now_utc(),
        },
    )
    logger.info("Created member affiliate code %s for subscriber %s", code, subscriber.discord_id)
    return code


async def _get_web3() -> Web3:
    settings = get_settings()
    bsc_rpc = settings.BLOCKCHAIN_RPC.get("BSC")
    if not bsc_rpc:
        raise ValueError("BSC RPC URL is missing in BLOCKCHAIN_RPC")

    web3 = Web3(Web3.HTTPProvider(bsc_rpc))
    web3.middleware_onion.inject(geth_poa_middleware, layer=0)
    connected = await asyncio.to_thread(web3.is_connected)
    if not connected:
        raise ConnectionError("Failed to connect to BSC RPC")

    return web3


async def verify_pending_payment(
    pending: PendingPayment,
    admin_settings: Any | None = None,
) -> tuple[bool, str, Optional[str], Optional[Decimal]]:
    """
    Route payment verification based on network/chain.
    Supports BSC (EVM) and Solana (SPL tokens).
    """
    settings = get_settings()
    
    # Route to appropriate verifier based on network
    if pending.network.startswith("SOL_"):
        # Solana verification
        if admin_settings is None:
            async with get_session() as session:
                admin_settings = await load_effective_admin_settings(session, settings)
        
        try:
            from services.solana_blockchain import verify_solana_payment
            return await verify_solana_payment(pending, admin_settings)
        except ImportError:
            return False, "Solana support not installed (missing solders/solana-py dependencies)", None, None
        except Exception as exc:
            logger.error(f"Solana verification failed: {exc}")
            return False, f"Solana verification error: {str(exc)}", None, None
    
    elif pending.network.startswith("BSC_"):
        # BSC/EVM verification (existing logic)
        return await _verify_bsc_payment(pending, admin_settings)
    
    else:
        return False, f"Unsupported network: {pending.network}", None, None


async def _verify_bsc_payment(
    pending: PendingPayment,
    admin_settings: Any | None = None,
) -> tuple[bool, str, Optional[str], Optional[Decimal]]:
    """Verify BSC (EVM) USDT/USDC payments (existing logic)"""
    settings = get_settings()

    tx_hash = extract_tx_hash(pending.tx_hash_proof or "")
    if not tx_hash:
        return False, "No valid tx hash proof submitted", None, None

    token_meta = settings.TOKEN_CONTRACTS.get(pending.network)
    if not token_meta:
        return False, f"Unsupported network/token: {pending.network}", tx_hash, None

    token_contract = _normalize_addr(str(token_meta.get("address", "")))
    token_decimals = int(token_meta.get("decimals", 18))
    if admin_settings is None:
        async with get_session() as session:
            admin_settings = await load_effective_admin_settings(session, settings)

    payment_networks = getattr(admin_settings, "payment_networks", []) or []
    network_config = next((network for network in payment_networks if network.network_code == pending.network), None)
    expected_receiver = _normalize_addr(network_config.wallet if network_config else "")
    expected_sender = _normalize_addr(pending.wallet_address)

    if not expected_receiver:
        return False, f"Wallet not configured for network {pending.network}", tx_hash, None

    web3 = await _get_web3()

    try:
        tx = await asyncio.to_thread(web3.eth.get_transaction, tx_hash)
        receipt = await asyncio.to_thread(web3.eth.get_transaction_receipt, tx_hash)
        latest_block = await asyncio.to_thread(lambda: web3.eth.block_number)
    except Exception as exc:
        return False, f"Failed to fetch tx details: {exc}", tx_hash, None

    if receipt.status != 1:
        return False, "Transaction failed on-chain", tx_hash, None

    confirmations = (latest_block - receipt.blockNumber) + 1
    if confirmations < settings.PAYMENT_MIN_CONFIRMATIONS:
        return False, f"Waiting confirmations ({confirmations}/{settings.PAYMENT_MIN_CONFIRMATIONS})", tx_hash, None

    tx_to = _normalize_addr(getattr(tx, "to", "") or "")
    if tx_to != token_contract:
        return False, "Transaction target contract does not match configured token contract", tx_hash, None

    expected_amount = Decimal(pending.amount_expected_usd)
    tolerance = Decimal(getattr(admin_settings, "payment_tolerance_usd", settings.PAYMENT_TOLERANCE_USD))

    try:
        tx_block = await asyncio.to_thread(web3.eth.get_block, receipt.blockNumber)
        tx_timestamp = datetime.fromtimestamp(int(getattr(tx_block, "timestamp")), tz=timezone.utc)
    except Exception as exc:
        return False, f"Failed to fetch tx block timestamp: {exc}", tx_hash, None

    matched_amount: Optional[Decimal] = None
    fallback_amount: Optional[Decimal] = None
    receiver_match_outside_window = False

    for log in receipt.logs:
        log_address = _normalize_addr(getattr(log, "address", "") or "")
        if log_address != token_contract:
            continue

        topics = [topic.hex().lower() for topic in getattr(log, "topics", [])]
        if len(topics) < 3:
            continue

        if topics[0] != TRANSFER_TOPIC:
            continue

        from_addr = _normalize_addr(_topic_address(topics[1]))
        to_addr = _normalize_addr(_topic_address(topics[2]))
        if to_addr != expected_receiver:
            continue

        raw_amount = _log_data_to_int(getattr(log, "data", "0x0"))
        amount = _to_decimal_amount(raw_amount, token_decimals)

        if from_addr == expected_sender:
            matched_amount = amount
            break

        if pending.created_at <= tx_timestamp <= pending.expires_at:
            fallback_amount = amount
        else:
            receiver_match_outside_window = True

    if matched_amount is None and fallback_amount is not None:
        matched_amount = fallback_amount

    if matched_amount is None:
        if receiver_match_outside_window:
            return False, "Transaction timestamp falls outside pending payment window", tx_hash, None
        return False, "No matching Transfer event found for sender/receiver", tx_hash, None

    if abs(matched_amount - expected_amount) > tolerance:
        return False, f"Amount outside tolerance. expected={expected_amount} actual={matched_amount}", tx_hash, matched_amount

    return True, "Verified", tx_hash, matched_amount


async def finalize_verified_payment(
    pending: PendingPayment,
    tx_hash: str,
    amount_usd: Decimal,
    admin_settings: Any | None = None,
) -> bool:
    settings = get_settings()

    if admin_settings is None:
        async with get_session() as session:
            admin_settings = await load_effective_admin_settings(session, settings)

    price_per_month = Decimal(getattr(admin_settings, "price_per_month_usd", settings.PRICE_PER_MONTH_USD))
    payment_tolerance = Decimal(getattr(admin_settings, "payment_tolerance_usd", settings.PAYMENT_TOLERANCE_USD))

    async with get_session() as session:
        existing_payment = await session.scalar(
            select(Payment).where(Payment.tx_hash == tx_hash)
        )
        if existing_payment:
            logger.info("Payment %s already recorded; skipping", tx_hash)
            return True

        subscriber = await session.scalar(
            select(Subscriber).where(Subscriber.discord_id == pending.discord_id)
        )

        # Keep existing tolerance rule for month conversion.
        months_granted = max(1, int((Decimal(amount_usd) + payment_tolerance) // price_per_month))

        now = _now_utc()
        if subscriber is None:
            subscriber = Subscriber(
                discord_id=pending.discord_id,
                discord_username=pending.discord_username or pending.discord_id,
                tradingview_username=pending.tradingview_username,
                email=pending.email,
                wallet_address=pending.wallet_address,
                network=pending.network,
                months_paid=months_granted,
                expires_at=now + timedelta(days=30 * months_granted),
                is_active=True,
                affiliate_code_used=pending.affiliate_code,
            )
            session.add(subscriber)
            await session.flush()
        else:
            base = subscriber.expires_at if subscriber.expires_at and subscriber.expires_at > now else now
            subscriber.expires_at = base + timedelta(days=30 * months_granted)
            subscriber.months_paid = int(subscriber.months_paid or 0) + months_granted
            subscriber.commission_wallet = pending.wallet_address
            subscriber.network = pending.network
            subscriber.is_active = True
            if pending.discord_username:
                subscriber.discord_username = pending.discord_username

        payment = Payment(
            subscriber_id=subscriber.id,
            pending_payment_id=pending.id,
            tx_hash=tx_hash,
            amount_usd=amount_usd,
            months_granted=months_granted,
            network=pending.network,
        )
        session.add(payment)
        member_affiliate_code = await _ensure_member_affiliate(session, subscriber, pending)

        if pending.affiliate_code:
            affiliate_code = await session.scalar(
                select(Affiliate.code).where(Affiliate.code == pending.affiliate_code, Affiliate.is_active == True)
            )
            if affiliate_code:
                logger.info("Affiliate %s used for subscriber %s", affiliate_code, subscriber.discord_id)
        logger.info(
            "Member referral link ready for subscriber %s with code %s",
            subscriber.discord_id,
            member_affiliate_code,
        )

        guild_settings = await load_effective_guild_settings(session)

    discord = get_discord_service()
    vip_role_id = guild_settings.vip_role_id or settings.VIP_ROLE_ID
    role_assigned = False
    if vip_role_id:
        role_assigned = await discord.assign_role(pending.discord_id, vip_role_id)
    else:
        logger.warning("VIP role is not configured; skipping role assignment for %s", pending.discord_id)

    dm_sent = await discord.dm_user(
        pending.discord_id,
        "✅ Payment verified on-chain and your VIP access is now active.",
    )

    await _send_payment_verification_log(
        discord=discord,
        guild_settings=guild_settings,
        pending=pending,
        subscriber=subscriber,
        tx_hash=tx_hash,
        amount_usd=amount_usd,
        months_granted=months_granted,
        role_assigned=role_assigned,
        dm_sent=dm_sent,
    )

    return True


async def run_auto_payment_verification_once() -> dict:
    now = _now_utc()
    result = {"scanned": 0, "approved": 0, "skipped": 0, "failed": 0}
    settings = get_settings()

    async with get_session() as session:
        pending_rows = (await session.scalars(
            select(PendingPayment).where(
                PendingPayment.expires_at > now,
                PendingPayment.tx_hash_proof.is_not(None),
            )
        )).all()
        admin_settings = await load_effective_admin_settings(session, settings)

    result["scanned"] = len(pending_rows)

    for pending in pending_rows:
        verified, message, tx_hash, amount = await verify_pending_payment(pending, admin_settings)
        if not verified:
            if message.startswith("Waiting confirmations"):
                result["skipped"] += 1
            else:
                result["failed"] += 1
            continue

        assert tx_hash is not None and amount is not None
        ok = await finalize_verified_payment(pending, tx_hash, amount, admin_settings)
        if ok:
            result["approved"] += 1
        else:
            result["failed"] += 1

    return result


async def run_auto_payment_verification_loop(stop_event: asyncio.Event):
    settings = get_settings()
    interval = max(10, int(settings.POLL_INTERVAL_SECONDS))

    logger.info(
        "Starting auto payment verifier loop (networks=BSC_USDT,BSC_USDC confirmations=%s interval=%ss)",
        settings.PAYMENT_MIN_CONFIRMATIONS,
        interval,
    )

    while not stop_event.is_set():
        try:
            summary = await run_auto_payment_verification_once()
            if summary["approved"] or summary["failed"]:
                logger.info(
                    "Auto verifier run: scanned=%s approved=%s skipped=%s failed=%s",
                    summary["scanned"], summary["approved"], summary["skipped"], summary["failed"],
                )
        except Exception as exc:
            logger.exception("Auto verifier run failed: %s", exc)

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except asyncio.TimeoutError:
            continue

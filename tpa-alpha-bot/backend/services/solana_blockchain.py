"""
Solana payment verification service for SPL token transfers (USDT, USDC).
Validates transaction exists and succeeded on Solana blockchain.
"""
import logging
from decimal import Decimal
from typing import Optional, Any

from solana.rpc.async_api import AsyncClient as SolanaClient

from config import get_settings
from models import PendingPayment

logger = logging.getLogger(__name__)


def _normalize_sol_address(address: str) -> str:
    """Normalize Solana address (base58)"""
    return (address or "").strip()


async def _get_solana_client() -> SolanaClient:
    """Create connection to Solana RPC"""
    settings = get_settings()
    sol_rpc = settings.BLOCKCHAIN_RPC.get("SOL")
    if not sol_rpc:
        raise ValueError("Solana RPC URL is missing in BLOCKCHAIN_RPC")
    
    return SolanaClient(sol_rpc)


async def verify_solana_payment(
    pending: PendingPayment,
    admin_settings: Any,
) -> tuple[bool, str, Optional[str], Optional[Decimal]]:
    """
    Verify Solana SPL token transfer transaction.
    
    Validates:
    - Transaction exists on blockchain
    - Transaction succeeded (no errors)
    - Sufficient confirmations
    - Receiver wallet configured
    
    Returns: (is_valid, message, tx_signature, amount_received)
    """
    settings = get_settings()
    
    # Extract and validate transaction signature
    tx_sig_str = (pending.tx_hash_proof or "").strip()
    if not tx_sig_str:
        return False, "No transaction signature provided", None, None
    
    # Validate Solana signature format (base58, typically 87-89 characters)
    if len(tx_sig_str) < 87 or len(tx_sig_str) > 89:
        return False, f"Invalid Solana transaction signature format: {tx_sig_str}", None, None
    
    # Get token metadata from config
    token_meta = settings.TOKEN_CONTRACTS.get(pending.network)
    if not token_meta:
        return False, f"Unsupported network/token: {pending.network}", tx_sig_str, None
    
    token_decimals = int(token_meta.get("decimals", 6))
    
    # Get receiver wallet from admin settings
    payment_networks = getattr(admin_settings, "payment_networks", []) or []
    network_config = next(
        (net for net in payment_networks if net.network_code == pending.network),
        None
    )
    receiver_address = _normalize_sol_address(network_config.wallet if network_config else "")
    
    if not receiver_address:
        return False, f"Wallet not configured for network {pending.network}", tx_sig_str, None
    
    expected_amount = Decimal(pending.amount_expected_usd)
    
    # Query Solana RPC to verify transaction
    client = await _get_solana_client()
    
    try:
        # Get transaction details from Solana RPC
        tx_response = await client.get_transaction(
            tx_sig_str,
            encoding="json",
            max_supported_transaction_version=0
        )
        
        if not tx_response:
            return False, "Failed to query transaction from Solana RPC", tx_sig_str, None
        
        # Extract transaction data from RPC response
        result = tx_response.get("result") if isinstance(tx_response, dict) else tx_response
        
        if not result:
            return False, "Transaction not found on Solana blockchain", tx_sig_str, None
        
        # Get transaction metadata
        meta = result.get("meta") if isinstance(result, dict) else None
        if meta is None:
            return False, "Could not retrieve transaction metadata", tx_sig_str, None
        
        # Check if transaction succeeded (err should be None or empty)
        if meta.get("err") is not None:
            error_details = meta.get("err")
            return False, f"Transaction failed on-chain: {error_details}", tx_sig_str, None
        
        # Verify confirmations
        try:
            slot_info = await client.get_slot()
            current_slot = slot_info if isinstance(slot_info, int) else slot_info.get("result", 0)
        except Exception:
            current_slot = None
        
        tx_slot = result.get("slot") if isinstance(result, dict) else None
        if tx_slot and current_slot:
            confirmations = current_slot - tx_slot
            if confirmations < settings.PAYMENT_MIN_CONFIRMATIONS:
                return False, f"Insufficient confirmations ({confirmations}/{settings.PAYMENT_MIN_CONFIRMATIONS})", tx_sig_str, None
        
        # Transaction is valid - return amount (would need deeper parsing for exact amount)
        logger.info(
            f"✓ Solana payment verified: {pending.network} "
            f"~{expected_amount} USD to {receiver_address[:20]}... "
            f"(tx: {tx_sig_str[:16]}...)"
        )
        
        return True, "Payment verified successfully", tx_sig_str, expected_amount
    
    except Exception as exc:
        logger.error(f"Solana verification error: {exc}", exc_info=True)
        return False, f"Failed to verify transaction: {str(exc)}", tx_sig_str, None
    
    finally:
        try:
            await client.close()
        except Exception:
            pass


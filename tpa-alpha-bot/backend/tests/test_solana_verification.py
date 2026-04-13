"""
Test cases for Solana payment verification
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from services.solana_blockchain import verify_solana_payment, _normalize_sol_address


class TestSolanaAddressNormalization:
    """Test Solana address normalization"""
    
    def test_normalize_empty_address(self):
        """Empty addresses should return empty string"""
        assert _normalize_sol_address("") == ""
        assert _normalize_sol_address(None) == ""
    
    def test_normalize_whitespace(self):
        """Whitespace should be stripped"""
        assert _normalize_sol_address("  TokenkegQfeZyiNwAJsyFbPVwwQQfq5x5iyKkeKSksUUq  ") == "TokenkegQfeZyiNwAJsyFbPVwwQQfq5x5iyKkeKSksUUq"
    
    def test_normalize_valid_address(self):
        """Valid addresses should return as-is"""
        addr = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenErt"
        assert _normalize_sol_address(addr) == addr


class TestSolanaVerificationLogic:
    """Test Solana payment verification logic"""
    
    @pytest.mark.asyncio
    async def test_missing_transaction_signature(self):
        """Verification should fail with no tx signature"""
        pending = SimpleNamespace(
            tx_hash_proof=None,
            network="SOL_USDT",
            wallet_address="...",
            amount_expected_usd=Decimal("100"),
        )
        admin_settings = SimpleNamespace(
            payment_networks=[],
            payment_tolerance_usd=Decimal("5"),
        )
        
        is_valid, message, tx_sig, amount = await verify_solana_payment(pending, admin_settings)
        
        assert not is_valid
        assert "No transaction signature" in message
        assert tx_sig is None
    
    @pytest.mark.asyncio
    async def test_invalid_transaction_signature_format(self):
        """Verification should fail with invalid signature format"""
        pending = SimpleNamespace(
            tx_hash_proof="not-a-valid-solana-signature",
            network="SOL_USDT",
            wallet_address="...",
            amount_expected_usd=Decimal("100"),
        )
        admin_settings = SimpleNamespace(
            payment_networks=[],
            payment_tolerance_usd=Decimal("5"),
        )
        
        is_valid, message, tx_sig, amount = await verify_solana_payment(pending, admin_settings)
        
        assert not is_valid
        assert "Invalid Solana transaction signature format" in message
    
    @pytest.mark.asyncio
    async def test_unsupported_network(self):
        """Verification should fail with unsupported network"""
        pending = SimpleNamespace(
            tx_hash_proof="3u8hQUqvRL3NrYQPneLu7jcC5d7CJRmQQQq9c4b2z9VqGv9fKGMZG4eqUFCMFnCKpJ1uK2mZQ7s5p3d6g0h1k8j",
            network="UNSUPPORTED_TOKEN",
            wallet_address="...",
            amount_expected_usd=Decimal("100"),
        )
        admin_settings = SimpleNamespace(
            payment_networks=[],
            payment_tolerance_usd=Decimal("5"),
        )
        
        is_valid, message, tx_sig, amount = await verify_solana_payment(pending, admin_settings)
        
        assert not is_valid
        assert "Unsupported network/token" in message
    
    @pytest.mark.asyncio
    async def test_missing_receiver_wallet(self):
        """Verification should fail if receiver wallet not configured"""
        pending = SimpleNamespace(
            tx_hash_proof="3u8hQUqvRL3NrYQPneLu7jcC5d7CJRmQQQq9c4b2z9VqGv9fKGMZG4eqUFCMFnCKpJ1uK2mZQ7s5p3d6g0h1k8j",
            network="SOL_USDT",
            wallet_address="...",
            amount_expected_usd=Decimal("100"),
        )
        admin_settings = SimpleNamespace(
            payment_networks=[],  # No networks configured
            payment_tolerance_usd=Decimal("5"),
        )
        
        is_valid, message, tx_sig, amount = await verify_solana_payment(pending, admin_settings)
        
        assert not is_valid
        assert "Wallet not configured" in message


class TestSolanaNetworkConfig:
    """Test Solana network configuration"""
    
    def test_solana_usdt_configured(self):
        """SOL_USDT should be configured in settings"""
        from config import get_settings
        settings = get_settings()
        
        assert "SOL_USDT" in settings.TOKEN_CONTRACTS
        token = settings.TOKEN_CONTRACTS["SOL_USDT"]
        assert token["address"] == "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenErt"
        assert token["decimals"] == 6
        assert token["chain"] == "SOL"
    
    def test_solana_usdc_configured(self):
        """SOL_USDC should be configured in settings"""
        from config import get_settings
        settings = get_settings()
        
        assert "SOL_USDC" in settings.TOKEN_CONTRACTS
        token = settings.TOKEN_CONTRACTS["SOL_USDC"]
        assert token["address"] == "EPjFWaLb3odcccccccccccccccccccccccccccccccccccc"
        assert token["decimals"] == 6
        assert token["chain"] == "SOL"
    
    def test_solana_rpc_configured(self):
        """Solana RPC should be configured"""
        from config import get_settings
        settings = get_settings()
        
        assert "SOL" in settings.BLOCKCHAIN_RPC
        assert "https://api.mainnet-beta.solana.com" in settings.BLOCKCHAIN_RPC["SOL"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

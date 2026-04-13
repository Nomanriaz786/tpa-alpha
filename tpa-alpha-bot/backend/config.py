"""
Configuration system for TPA Alpha Bot
Loads from config.json and provides settings across the application
"""
from typing import Dict, List, Any
from pydantic_settings import BaseSettings
from pydantic import field_validator, model_validator
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings - loaded from config.json"""
    
    # Discord
    DISCORD_BOT_TOKEN: str
    DISCORD_APPLICATION_ID: str
    GUILD_ID: str
    VIP_ROLE_ID: str = ""
    ADMIN_DISCORD_IDS_RAW: str = ""  # Will be parsed from env
    ADMIN_DISCORD_IDS: List[str] = []  # Parsed list
    VIP_ROLE_NAME: str = "TPA Alpha 👑"
    
    # Web
    WEB_BASE_URL: str

    # Auth
    ADMIN_JWT_SECRET: str = ""
    
    # Database
    DATABASE_URL: str
    
    # Email
    ADMIN_EMAIL: str = "admin@example.com"
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASS: str = ""
    
    # Wallets (BSC and Solana chains supported)
    WALLETS: Dict[str, str] = {
        "BSC_USDT": "",
        "BSC_USDC": "",
        "SOL_USDT": "",
        "SOL_USDC": "",
    }
    
    # Blockchain RPC Endpoints
    BLOCKCHAIN_RPC: Dict[str, str] = {
        "BSC": "https://bsc-dataseed.binance.org/",
        "SOL": "https://api.mainnet-beta.solana.com",
    }

    TOKEN_CONTRACTS: Dict[str, Dict[str, Any]] = {
        "BSC_USDT": {
            "address": "0x55d398326f99059fF775485246999027B3197955",
            "decimals": 18,
            "chain": "BSC",
        },
        "BSC_USDC": {
            "address": "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d",
            "decimals": 18,
            "chain": "BSC",
        },
        "SOL_USDT": {
            "address": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenErt",
            "decimals": 6,
            "chain": "SOL",
        },
        "SOL_USDC": {
            "address": "EPjFWaLb3odcccccccccccccccccccccccccccccccccccc",
            "decimals": 6,
            "chain": "SOL",
        },
    }
    
    # Pricing
    PRICE_PER_MONTH_USD: Decimal = Decimal("100")
    PAYMENT_TOLERANCE_USD: Decimal = Decimal("5")
    
    # Workers
    POLL_INTERVAL_SECONDS: int = 60
    PAYMENT_MIN_CONFIRMATIONS: int = 10
    PENDING_PAYMENT_TTL_HOURS: int = 24
    ADMIN_SESSION_TTL_DAYS: int = 7
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields from .env file
    
    @field_validator("PRICE_PER_MONTH_USD", "PAYMENT_TOLERANCE_USD", mode="before")
    @classmethod
    def parse_decimal(cls, v):
        if isinstance(v, (int, float)):
            return Decimal(str(v))
        return Decimal(v)

    @model_validator(mode="after")
    def parse_admin_ids_list(self) -> "Settings":
        if isinstance(self.ADMIN_DISCORD_IDS_RAW, str) and self.ADMIN_DISCORD_IDS_RAW:
            self.ADMIN_DISCORD_IDS = [id.strip() for id in self.ADMIN_DISCORD_IDS_RAW.split(",") if id.strip()]
        return self


def get_settings() -> Settings:
    """Get settings from environment variables (.env file)"""
    try:
        settings = Settings()
        logger.info("✓ Configuration loaded successfully from environment")
        return settings
    except Exception as e:
        logger.error(f"✗ Error loading configuration: {e}")
        raise ValueError(f"Configuration error: {e}")


def reload_settings() -> Settings:
    """Force reload settings from environment."""
    settings = get_settings()
    logger.info("⚡ Settings reloaded from environment")
    return settings


def get_active_networks() -> List[Dict[str, str]]:
    """Get list of networks that have wallet addresses configured"""
    settings = get_settings()
    networks = []
    
    network_labels = {
        "BSC_USDT": "BNB Chain (USDT)",
        "BSC_USDC": "BNB Chain (USDC)",
    }
    
    network_chains = {
        "BSC_USDT": "BSC",
        "BSC_USDC": "BSC",
    }
    
    for key, label in network_labels.items():
        if settings.WALLETS.get(key):  # Only if wallet is configured
            networks.append({
                "id": key,
                "label": label,
                "chain": network_chains.get(key),
                "wallet": settings.WALLETS.get(key)
            })
    
    return networks

import json
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional
from urllib.parse import quote

from fastapi import Depends, Header, HTTPException
from jose import JWTError, jwt
from sqlalchemy import text

from config import get_settings
from database import get_db
from admin_api.settings_service import load_admin_security_row
from schemas import AdminSettings

logger = logging.getLogger(__name__)

ADMIN_HASH_KEY = "admin_password_hash"
JWT_ALGORITHM = "HS256"


def get_admin_jwt_secret() -> str:
    settings = get_settings()
    return getattr(settings, "ADMIN_JWT_SECRET", "") or settings.DISCORD_BOT_TOKEN


def create_admin_token(password_version: int = 1) -> tuple[str, datetime]:
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.ADMIN_SESSION_TTL_DAYS)
    payload = {
        "sub": "admin",
        "exp": int(expires_at.timestamp()),
        "pv": int(password_version),
    }
    token = jwt.encode(payload, get_admin_jwt_secret(), algorithm=JWT_ALGORITHM)
    return token, expires_at


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def parse_config_value(value: object) -> object:
    if not isinstance(value, str):
        return value

    stripped = value.strip()
    if not stripped:
        return ""

    try:
        if stripped.startswith("{") or stripped.startswith("["):
            return json.loads(stripped)
    except json.JSONDecodeError:
        return stripped

    if stripped.isdigit():
        return int(stripped)

    try:
        return Decimal(stripped)
    except Exception:
        return stripped


async def load_admin_config_values(session) -> dict[str, object]:
    result = await session.execute(text("SELECT key, value FROM admin_config"))
    return {
        row["key"]: parse_config_value(row["value"])
        for row in result.mappings().all()
    }


def build_admin_settings(config_values: dict[str, object]) -> AdminSettings:
    env_settings = get_settings()
    wallets = config_values.get("wallets")
    if not isinstance(wallets, dict):
        wallets = env_settings.WALLETS

    return AdminSettings(
        wallets=wallets,
        smtp_host=str(config_values.get("smtp_host", env_settings.SMTP_HOST)),
        smtp_port=int(config_values.get("smtp_port", env_settings.SMTP_PORT)),
        smtp_user=str(config_values.get("smtp_user", env_settings.SMTP_USER)),
        admin_email=str(config_values.get("admin_email", env_settings.ADMIN_EMAIL)),
        price_per_month_usd=Decimal(
            str(config_values.get("price_per_month_usd", env_settings.PRICE_PER_MONTH_USD))
        ),
        payment_tolerance_usd=Decimal(
            str(config_values.get("payment_tolerance_usd", env_settings.PAYMENT_TOLERANCE_USD))
        ),
    )


def build_affiliate_link(code: Optional[str]) -> Optional[str]:
    cleaned = (code or "").strip()
    if not cleaned:
        return None

    settings = get_settings()
    base_url = (settings.WEB_BASE_URL or "").rstrip("/")
    if not base_url:
        return None

    return f"{base_url}/subscribe?affiliate_code={quote(cleaned)}"


async def upsert_admin_config(session, key: str, value: object) -> None:
    serialized = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
    await session.execute(
        text(
            """
            INSERT INTO admin_config (key, value)
            VALUES (:key, :value)
            ON CONFLICT (key) DO UPDATE SET
                value = EXCLUDED.value,
                updated_at = NOW()
            """
        ),
        {"key": key, "value": serialized},
    )


async def verify_admin_token(
    authorization: Optional[str] = Header(None),
    session = Depends(get_db),
) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

    token = authorization.split(" ")[1]

    try:
        payload = jwt.decode(token, get_admin_jwt_secret(), algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if payload.get("sub") != "admin":
        raise HTTPException(status_code=401, detail="Invalid token subject")

    current_security = await load_admin_security_row(session)
    current_version = int(current_security.get("password_version") or 1) if current_security else 1
    token_version = int(payload.get("pv") or 1)
    if token_version != current_version:
        raise HTTPException(status_code=401, detail="Admin password has changed")

    return "admin"

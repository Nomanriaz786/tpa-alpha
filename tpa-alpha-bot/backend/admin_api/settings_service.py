"""Shared settings helpers for admin configuration, payment networks, and guild settings."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from decimal import Decimal
from types import SimpleNamespace
from typing import Any, Optional

from sqlalchemy import bindparam, text

from schemas import AdminSettings, NetworkInfo, PaymentNetworkConfig
from services.guild_settings import load_guild_settings_rows, normalize_guild_settings_rows

ADMIN_PASSWORD_CONFIG_KEY = "admin_password_hash"

DEFAULT_NETWORK_METADATA: dict[str, dict[str, str]] = {
    "BSC_USDT": {
        "label": "BNB Chain (USDT)",
        "chain": "BSC",
        "token_contract": "0x55d398326f99059fF775485246999027B3197955",
    },
    "BSC_USDC": {
        "label": "BNB Chain (USDC)",
        "chain": "BSC",
        "token_contract": "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d",
    },
    "SOL_USDT": {
        "label": "Solana (USDT)",
        "chain": "SOL",
        "token_contract": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenErt",
    },
    "SOL_USDC": {
        "label": "Solana (USDC)",
        "chain": "SOL",
        "token_contract": "EPjFWaLb3odcccccccccccccccccccccccccccccccccccc",
    },
}


def _default_settings() -> SimpleNamespace:
    return SimpleNamespace(
        WALLETS={"BSC_USDT": "", "BSC_USDC": "", "SOL_USDT": "", "SOL_USDC": ""},
        TOKEN_CONTRACTS={
            "BSC_USDT": {
                "address": DEFAULT_NETWORK_METADATA["BSC_USDT"]["token_contract"],
                "decimals": 18,
            },
            "BSC_USDC": {
                "address": DEFAULT_NETWORK_METADATA["BSC_USDC"]["token_contract"],
                "decimals": 18,
            },
            "SOL_USDT": {
                "address": DEFAULT_NETWORK_METADATA["SOL_USDT"]["token_contract"],
                "decimals": 6,
            },
            "SOL_USDC": {
                "address": DEFAULT_NETWORK_METADATA["SOL_USDC"]["token_contract"],
                "decimals": 6,
            },
        },
        SMTP_HOST="smtp.gmail.com",
        SMTP_PORT=587,
        SMTP_USER="",
        ADMIN_EMAIL="admin@example.com",
        PRICE_PER_MONTH_USD=Decimal("100"),
        PAYMENT_TOLERANCE_USD=Decimal("5"),
        PAYMENT_MIN_CONFIRMATIONS=10,
    )


def _coerce_decimal(value: Any, fallback: Decimal) -> Decimal:
    if value is None:
        return fallback
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    try:
        return Decimal(str(value))
    except Exception:
        return fallback


def _coerce_int(value: Any, fallback: int) -> int:
    if value is None:
        return fallback
    try:
        return int(value)
    except Exception:
        return fallback


def _coerce_bool(value: Any, fallback: bool = True) -> bool:
    if value is None:
        return fallback
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y", "on"}:
            return True
        if normalized in {"false", "0", "no", "n", "off"}:
            return False
    return bool(value)


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


def _normalize_code(value: Any) -> str:
    return str(value or "").strip().upper()


def _network_metadata(network_code: str, env_settings: Any) -> dict[str, str]:
    defaults = DEFAULT_NETWORK_METADATA.get(network_code, {})
    token_contract = ""
    token_contracts = getattr(env_settings, "TOKEN_CONTRACTS", {}) or {}
    if network_code in token_contracts:
        token_contract = str(token_contracts[network_code].get("address", ""))
    return {
        "label": defaults.get("label", network_code),
        "chain": defaults.get("chain", network_code.split("_")[0] if "_" in network_code else "BSC"),
        "token_contract": defaults.get("token_contract", token_contract),
    }


def normalize_payment_network_rows(
    payment_network_rows: Sequence[Mapping[str, Any]] | None = None,
    fallback_wallets: Mapping[str, str] | None = None,
    env_settings: Any | None = None,
    existing_payment_network_rows: Sequence[Mapping[str, Any]] | None = None,
) -> list[PaymentNetworkConfig]:
    """Convert DB rows or env defaults into structured payment network configs."""
    settings = env_settings or _default_settings()
    wallets = {
        _normalize_code(key): str(value).strip()
        for key, value in (fallback_wallets or {}).items()
        if str(value).strip()
    }
    existing_rows = {}
    for row in existing_payment_network_rows or []:
      existing_code = _normalize_code(
            row.get("network_code")
            or row.get("id")
            or row.get("code")
            or row.get("key")
        )
      if existing_code:
          existing_rows[existing_code] = row

    rows = list(payment_network_rows or [])
    if not rows:
        if wallets:
            rows = [
                {
                    "network_code": network_code,
                    "label": _network_metadata(network_code, settings)["label"],
                    "chain": _network_metadata(network_code, settings)["chain"],
                    "wallet": wallet,
                    "token_contract": _network_metadata(network_code, settings)["token_contract"],
                    "min_confirmations": getattr(settings, "PAYMENT_MIN_CONFIRMATIONS", 10),
                    "tolerance_usd": getattr(settings, "PAYMENT_TOLERANCE_USD", Decimal("5")),
                    "is_active": True,
                }
                for network_code, wallet in wallets.items()
            ]
        else:
            return []

    normalized: list[PaymentNetworkConfig] = []
    for row in rows:
        network_code = _normalize_code(
            row.get("network_code")
            or row.get("id")
            or row.get("code")
            or row.get("key")
        )
        if not network_code:
            continue

        existing_row = existing_rows.get(network_code, {})
        metadata = _network_metadata(network_code, settings)
        token_contract = str(
            row.get("token_contract")
            or row.get("tokenContract")
            or existing_row.get("token_contract")
            or existing_row.get("tokenContract")
            or metadata["token_contract"]
            or ""
        ).strip()
        # CRITICAL: Prefer explicit wallet values from current row, existing DB row,
        # then fallback to legacy wallets dict. Don't use empty string as fallback to wallets dict.
        wallet = str(row.get("wallet") or row.get("payout_wallet") or row.get("payoutWallet") or "").strip()
        if not wallet:
            # Only fall back to existing DB row or wallets dict if current row has no wallet
            wallet = str(
                existing_row.get("wallet")
                or existing_row.get("payout_wallet")
                or existing_row.get("payoutWallet")
                or wallets.get(network_code, "")
                or ""
            ).strip()

        normalized.append(
            PaymentNetworkConfig(
                network_code=network_code,
                label=str(row.get("label") or existing_row.get("label") or metadata["label"] or network_code).strip(),
                chain=str(row.get("chain") or metadata["chain"] or existing_row.get("chain") or "BSC").strip(),
                wallet=wallet,
                token_contract=token_contract,
                min_confirmations=_coerce_int(
                    row.get("min_confirmations") if row.get("min_confirmations") is not None else existing_row.get("min_confirmations"),
                    getattr(settings, "PAYMENT_MIN_CONFIRMATIONS", 10),
                ),
                tolerance_usd=_coerce_decimal(
                    row.get("tolerance_usd") if row.get("tolerance_usd") is not None else existing_row.get("tolerance_usd"),
                    getattr(settings, "PAYMENT_TOLERANCE_USD", Decimal("5")),
                ),
                is_active=_coerce_bool(
                    row.get("is_active") if row.get("is_active") is not None else existing_row.get("is_active"),
                    True,
                ),
            )
        )

    return sorted(normalized, key=lambda network: network.network_code)


def build_admin_settings(
    config_values: dict[str, object],
    payment_network_rows: Sequence[Mapping[str, Any]] | None = None,
    guild_settings_rows: Sequence[Mapping[str, Any]] | None = None,
    env_settings: Any | None = None,
) -> AdminSettings:
    """Build the admin settings response model from DB and env values."""
    settings = env_settings or _default_settings()
    wallets = config_values.get("wallets")
    if isinstance(wallets, dict):
        normalized_wallets = {
            _normalize_code(key): str(value).strip()
            for key, value in wallets.items()
            if str(value).strip()
        }
    else:
        normalized_wallets = dict(getattr(settings, "WALLETS", {}))

    payment_networks = normalize_payment_network_rows(
        payment_network_rows,
        normalized_wallets,
        settings,
    )

    guild_settings = normalize_guild_settings_rows(
        guild_settings_rows,
        settings,
        include_default_if_missing=True,
    )

    if not normalized_wallets and payment_networks:
        normalized_wallets = {
            network.network_code: network.wallet
            for network in payment_networks
            if network.wallet
        }

    return AdminSettings(
        wallets=normalized_wallets,
        payment_networks=payment_networks,
        guild_settings=guild_settings,
        smtp_host=str(config_values.get("smtp_host", getattr(settings, "SMTP_HOST", "smtp.gmail.com"))),
        smtp_port=_coerce_int(config_values.get("smtp_port"), getattr(settings, "SMTP_PORT", 587)),
        smtp_user=str(config_values.get("smtp_user", getattr(settings, "SMTP_USER", ""))),
        admin_email=str(config_values.get("admin_email", getattr(settings, "ADMIN_EMAIL", "admin@example.com"))),
        price_per_month_usd=_coerce_decimal(
            config_values.get("price_per_month_usd"),
            getattr(settings, "PRICE_PER_MONTH_USD", Decimal("100")),
        ),
        payment_tolerance_usd=_coerce_decimal(
            config_values.get("payment_tolerance_usd"),
            getattr(settings, "PAYMENT_TOLERANCE_USD", Decimal("5")),
        ),
    )


def resolve_admin_password_hash(
    admin_security_row: Mapping[str, Any] | None,
    admin_config_values: Mapping[str, Any] | None,
) -> Optional[str]:
    """Resolve the canonical admin password hash, preferring the security table."""
    if admin_security_row:
        password_hash = admin_security_row.get("password_hash")
        if password_hash:
            return str(password_hash)

    config_values = admin_config_values or {}
    legacy_hash = config_values.get(ADMIN_PASSWORD_CONFIG_KEY)
    if legacy_hash:
        return str(legacy_hash)

    return None


def build_network_info_list(payment_networks: Sequence[PaymentNetworkConfig]) -> list[NetworkInfo]:
    """Convert payment network configs into the public payment endpoint response."""
    return [
        NetworkInfo(
            id=network.network_code,
            label=network.label,
            chain=network.chain,
            wallet=network.wallet,
            token_contract=network.token_contract,
            min_confirmations=network.min_confirmations,
            tolerance_usd=network.tolerance_usd,
            is_active=network.is_active,
        )
        for network in payment_networks
        if network.is_active and network.wallet
    ]


async def load_payment_network_rows(session) -> list[dict[str, Any]]:
    result = await session.execute(
        text(
            """
            SELECT
                network_code,
                label,
                chain,
                wallet,
                token_contract,
                min_confirmations,
                tolerance_usd,
                is_active,
                created_at,
                updated_at
            FROM payment_networks
            ORDER BY network_code
            """
        )
    )
    return [dict(row) for row in result.mappings().all()]


async def load_admin_config_values(session) -> dict[str, object]:
    result = await session.execute(text("SELECT key, value FROM admin_config"))
    return {
        row["key"]: parse_config_value(row["value"])
        for row in result.mappings().all()
    }


async def load_current_payment_networks(session, env_settings: Any | None = None) -> list[PaymentNetworkConfig]:
    """Load the current payment networks from the database with env fallback."""
    payment_network_rows = await load_payment_network_rows(session)
    return normalize_payment_network_rows(
        payment_network_rows,
        getattr(env_settings, "WALLETS", {}) or {},
        env_settings,
    )


async def load_effective_admin_settings(session, env_settings: Any | None = None) -> AdminSettings:
    """Load the effective admin settings from DB with environment fallbacks."""
    config_values = await load_admin_config_values(session)
    payment_network_rows = await load_payment_network_rows(session)
    guild_settings_rows = await load_guild_settings_rows(session)
    return build_admin_settings(config_values, payment_network_rows, guild_settings_rows, env_settings)


async def replace_payment_network_rows(session, payment_network_rows: Sequence[Mapping[str, Any]]) -> None:
    """Replace the stored payment network rows with the supplied payload."""
    existing_payment_network_rows = await load_payment_network_rows(session)
    normalized_rows = normalize_payment_network_rows(
        payment_network_rows,
        {},
        existing_payment_network_rows=existing_payment_network_rows,
    )

    if not normalized_rows:
        await session.execute(text("DELETE FROM payment_networks"))
        return

    for network in normalized_rows:
        await session.execute(
            text(
                """
                INSERT INTO payment_networks (
                    network_code, label, chain, wallet, token_contract,
                    min_confirmations, tolerance_usd, is_active, updated_at
                )
                VALUES (
                    :network_code, :label, :chain, :wallet, :token_contract,
                    :min_confirmations, :tolerance_usd, :is_active, NOW()
                )
                ON CONFLICT (network_code) DO UPDATE SET
                    label = EXCLUDED.label,
                    chain = EXCLUDED.chain,
                    wallet = EXCLUDED.wallet,
                    token_contract = EXCLUDED.token_contract,
                    min_confirmations = EXCLUDED.min_confirmations,
                    tolerance_usd = EXCLUDED.tolerance_usd,
                    is_active = EXCLUDED.is_active,
                    updated_at = NOW()
                """
            ),
            {
                "network_code": network.network_code,
                "label": network.label,
                "chain": network.chain,
                "wallet": network.wallet,
                "token_contract": network.token_contract,
                "min_confirmations": network.min_confirmations,
                "tolerance_usd": network.tolerance_usd,
                "is_active": network.is_active,
            },
        )

    await session.execute(
        text(
            "DELETE FROM payment_networks WHERE network_code NOT IN :codes"
        ).bindparams(bindparam("codes", expanding=True)),
        {"codes": [network.network_code for network in normalized_rows]},
    )


async def load_admin_security_row(session) -> dict[str, Any] | None:
    result = await session.execute(
        text(
            """
            SELECT id, password_hash, password_version, password_changed_at, updated_at
            FROM admin_security
            ORDER BY id DESC
            LIMIT 1
            """
        )
    )
    row = result.mappings().first()
    return dict(row) if row else None


async def save_admin_security_row(
    session,
    password_hash: str,
    password_version: int,
) -> dict[str, Any]:
    result = await session.execute(
        text(
            """
            INSERT INTO admin_security (
                id, password_hash, password_version, password_changed_at, updated_at
            )
            VALUES (1, :password_hash, :password_version, NOW(), NOW())
            ON CONFLICT (id) DO UPDATE SET
                password_hash = EXCLUDED.password_hash,
                password_version = EXCLUDED.password_version,
                password_changed_at = EXCLUDED.password_changed_at,
                updated_at = EXCLUDED.updated_at
            RETURNING id, password_hash, password_version, password_changed_at, updated_at
            """
        ),
        {"password_hash": password_hash, "password_version": password_version},
    )
    row = result.mappings().first()
    return dict(row) if row else {
        "id": 1,
        "password_hash": password_hash,
        "password_version": password_version,
    }


async def current_admin_password_version(session) -> int:
    row = await load_admin_security_row(session)
    if not row:
        return 1
    return int(row.get("password_version") or 1)
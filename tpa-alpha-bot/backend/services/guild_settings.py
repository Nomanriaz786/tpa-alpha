"""Shared helpers for Discord guild settings."""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy import bindparam, text

from config import get_settings
from schemas import GuildSettingsConfig

logger = logging.getLogger(__name__)


def _normalize_id(value: Any) -> str:
    return str(value or "").strip()


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


def _default_guild_settings(env_settings: Any | None = None, guild_id: str | None = None) -> GuildSettingsConfig:
    settings = env_settings or get_settings()
    resolved_guild_id = _normalize_id(guild_id or getattr(settings, "GUILD_ID", ""))
    return GuildSettingsConfig(
        guild_id=resolved_guild_id,
        vip_role_id=_normalize_id(getattr(settings, "VIP_ROLE_ID", "")) or None,
        community_role_id=None,
        welcome_channel_id=None,
        setup_channel_id=None,
        admin_channel_id=None,
        payment_logs_channel_id=None,
        support_channel_id=None,
        is_active=True,
        updated_at=None,
    )


def normalize_guild_settings_rows(
    guild_settings_rows: Sequence[Mapping[str, Any]] | None = None,
    env_settings: Any | None = None,
    existing_guild_settings_rows: Sequence[Mapping[str, Any]] | None = None,
    fallback_guild_id: str | None = None,
    include_default_if_missing: bool = False,
) -> list[GuildSettingsConfig]:
    """Normalize stored guild settings rows with env fallbacks."""
    settings = env_settings or get_settings()
    existing_rows: dict[str, Mapping[str, Any]] = {}
    for row in existing_guild_settings_rows or []:
        existing_guild_id = _normalize_id(row.get("guild_id") or row.get("id") or row.get("key"))
        if existing_guild_id:
            existing_rows[existing_guild_id] = row

    rows = list(guild_settings_rows or [])
    if not rows and include_default_if_missing:
        default_guild_id = _normalize_id(fallback_guild_id or getattr(settings, "GUILD_ID", ""))
        if default_guild_id:
            rows = [
                {
                    "guild_id": default_guild_id,
                    "vip_role_id": getattr(settings, "VIP_ROLE_ID", ""),
                    "community_role_id": None,
                    "welcome_channel_id": None,
                    "setup_channel_id": None,
                    "admin_channel_id": None,
                    "payment_logs_channel_id": None,
                    "support_channel_id": None,
                    "is_active": True,
                }
            ]

    normalized: list[GuildSettingsConfig] = []
    for row in rows:
        guild_id = _normalize_id(row.get("guild_id") or row.get("id") or row.get("key") or fallback_guild_id)
        if not guild_id:
            continue

        existing_row = existing_rows.get(guild_id, {})
        normalized.append(
            GuildSettingsConfig(
                guild_id=guild_id,
                vip_role_id=(
                    _normalize_id(
                        row.get("vip_role_id")
                        or existing_row.get("vip_role_id")
                        or getattr(settings, "VIP_ROLE_ID", "")
                    )
                    or None
                ),
                community_role_id=(
                    _normalize_id(row.get("community_role_id") or existing_row.get("community_role_id")) or None
                ),
                welcome_channel_id=(
                    _normalize_id(row.get("welcome_channel_id") or existing_row.get("welcome_channel_id")) or None
                ),
                setup_channel_id=(
                    _normalize_id(row.get("setup_channel_id") or existing_row.get("setup_channel_id")) or None
                ),
                admin_channel_id=(
                    _normalize_id(row.get("admin_channel_id") or existing_row.get("admin_channel_id")) or None
                ),
                payment_logs_channel_id=(
                    _normalize_id(
                        row.get("payment_logs_channel_id") or existing_row.get("payment_logs_channel_id")
                    )
                    or None
                ),
                support_channel_id=(
                    _normalize_id(row.get("support_channel_id") or existing_row.get("support_channel_id")) or None
                ),
                is_active=_coerce_bool(
                    row.get("is_active") if row.get("is_active") is not None else existing_row.get("is_active"),
                    True,
                ),
                updated_at=row.get("updated_at") or existing_row.get("updated_at"),
            )
        )

    if not normalized and include_default_if_missing:
        default_row = _default_guild_settings(settings, fallback_guild_id)
        if default_row.guild_id:
            normalized.append(default_row)

    return sorted(normalized, key=lambda item: item.guild_id)


async def load_guild_settings_rows(session) -> list[dict[str, Any]]:
    result = await session.execute(
        text(
            """
            SELECT
                guild_id,
                vip_role_id,
                community_role_id,
                welcome_channel_id,
                setup_channel_id,
                admin_channel_id,
                payment_logs_channel_id,
                support_channel_id,
                is_active,
                updated_at
            FROM guild_settings
            ORDER BY guild_id
            """
        )
    )
    return [dict(row) for row in result.mappings().all()]


async def replace_guild_settings_rows(session, guild_settings_rows: Sequence[Mapping[str, Any]]) -> None:
    """Replace stored guild settings rows with the supplied payload."""
    existing_guild_settings_rows = await load_guild_settings_rows(session)
    normalized_rows = normalize_guild_settings_rows(
        guild_settings_rows,
        existing_guild_settings_rows=existing_guild_settings_rows,
    )

    if not normalized_rows:
        await session.execute(text("DELETE FROM guild_settings"))
        return

    for guild_settings in normalized_rows:
        await session.execute(
            text(
                """
                INSERT INTO guild_settings (
                    guild_id, vip_role_id, community_role_id, welcome_channel_id,
                    setup_channel_id, admin_channel_id, payment_logs_channel_id, support_channel_id, is_active, updated_at
                )
                VALUES (
                    :guild_id, :vip_role_id, :community_role_id, :welcome_channel_id,
                    :setup_channel_id, :admin_channel_id, :payment_logs_channel_id, :support_channel_id, :is_active, NOW()
                )
                ON CONFLICT (guild_id) DO UPDATE SET
                    vip_role_id = EXCLUDED.vip_role_id,
                    community_role_id = EXCLUDED.community_role_id,
                    welcome_channel_id = EXCLUDED.welcome_channel_id,
                    setup_channel_id = EXCLUDED.setup_channel_id,
                    admin_channel_id = EXCLUDED.admin_channel_id,
                    payment_logs_channel_id = EXCLUDED.payment_logs_channel_id,
                    support_channel_id = EXCLUDED.support_channel_id,
                    is_active = EXCLUDED.is_active,
                    updated_at = NOW()
                """
            ),
            {
                "guild_id": guild_settings.guild_id,
                "vip_role_id": guild_settings.vip_role_id,
                "community_role_id": guild_settings.community_role_id,
                "welcome_channel_id": guild_settings.welcome_channel_id,
                "setup_channel_id": guild_settings.setup_channel_id,
                "admin_channel_id": guild_settings.admin_channel_id,
                "payment_logs_channel_id": guild_settings.payment_logs_channel_id,
                "support_channel_id": guild_settings.support_channel_id,
                "is_active": guild_settings.is_active,
            },
        )

    await session.execute(
        text("DELETE FROM guild_settings WHERE guild_id NOT IN :guild_ids").bindparams(
            bindparam("guild_ids", expanding=True)
        ),
        {"guild_ids": [guild_settings.guild_id for guild_settings in normalized_rows]},
    )


async def load_effective_guild_settings(
    session,
    guild_id: str | None = None,
    env_settings: Any | None = None,
) -> GuildSettingsConfig:
    """Load the active guild settings row or fall back to env defaults."""
    settings = env_settings or get_settings()
    resolved_guild_id = _normalize_id(guild_id or getattr(settings, "GUILD_ID", ""))

    if not resolved_guild_id:
        return _default_guild_settings(settings, guild_id)

    result = await session.execute(
        text(
            """
            SELECT
                guild_id,
                vip_role_id,
                community_role_id,
                welcome_channel_id,
                setup_channel_id,
                admin_channel_id,
                payment_logs_channel_id,
                support_channel_id,
                is_active,
                updated_at
            FROM guild_settings
            WHERE guild_id = :guild_id
            ORDER BY updated_at DESC NULLS LAST
            LIMIT 1
            """
        ),
        {"guild_id": resolved_guild_id},
    )
    row = result.mappings().first()
    if not row:
        return _default_guild_settings(settings, resolved_guild_id)

    normalized_rows = normalize_guild_settings_rows(
        [dict(row)],
        env_settings=settings,
        fallback_guild_id=resolved_guild_id,
        include_default_if_missing=True,
    )
    return normalized_rows[0]


async def resolve_vip_role_id(
    session,
    guild_id: str | None = None,
    env_settings: Any | None = None,
) -> str | None:
    """Resolve the VIP role ID from DB or environment defaults."""
    guild_settings = await load_effective_guild_settings(session, guild_id=guild_id, env_settings=env_settings)
    return guild_settings.vip_role_id

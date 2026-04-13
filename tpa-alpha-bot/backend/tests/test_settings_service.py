from decimal import Decimal
from types import SimpleNamespace

import pytest

import admin_api.settings_service as settings_service
from admin_api.settings_service import build_admin_settings, resolve_admin_password_hash
from schemas import AdminSettingsUpdate


def test_build_admin_settings_includes_typed_payment_networks():
    settings = build_admin_settings(
        {
            "wallets": {
                "BSC_USDT": "0x1111111111111111111111111111111111111111",
                "BSC_USDC": "0x2222222222222222222222222222222222222222",
            },
            "smtp_host": "smtp.example.com",
            "smtp_port": 2525,
            "smtp_user": "mailer@example.com",
            "admin_email": "admin@example.com",
            "price_per_month_usd": "100",
            "payment_tolerance_usd": "5",
        },
        payment_network_rows=[
            {
                "network_code": "BSC_USDT",
                "label": "BNB Chain (USDT)",
                "chain": "BSC",
                "wallet": "0x1111111111111111111111111111111111111111",
                "token_contract": "0x55d398326f99059fF775485246999027B3197955",
                "min_confirmations": 10,
                "tolerance_usd": Decimal("5"),
                "is_active": True,
            },
            {
                "network_code": "BSC_USDC",
                "label": "BNB Chain (USDC)",
                "chain": "BSC",
                "wallet": "0x2222222222222222222222222222222222222222",
                "token_contract": "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d",
                "min_confirmations": 10,
                "tolerance_usd": Decimal("5"),
                "is_active": True,
            },
        ],
    )

    assert settings.wallets == {
        "BSC_USDT": "0x1111111111111111111111111111111111111111",
        "BSC_USDC": "0x2222222222222222222222222222222222222222",
    }
    assert len(settings.payment_networks) == 2
    assert [network.network_code for network in settings.payment_networks] == ["BSC_USDC", "BSC_USDT"]
    assert settings.payment_networks[1].token_contract == "0x55d398326f99059fF775485246999027B3197955"


def test_build_admin_settings_uses_wallet_fallback_when_network_rows_are_missing():
    settings = build_admin_settings(
        {
            "wallets": {
                "BSC_USDT": "0x1111111111111111111111111111111111111111",
            },
            "smtp_host": "smtp.example.com",
            "smtp_port": 2525,
            "smtp_user": "mailer@example.com",
            "admin_email": "admin@example.com",
            "price_per_month_usd": "100",
            "payment_tolerance_usd": "5",
        },
        payment_network_rows=[],
    )

    assert settings.wallets == {"BSC_USDT": "0x1111111111111111111111111111111111111111"}
    assert len(settings.payment_networks) == 1
    assert settings.payment_networks[0].network_code == "BSC_USDT"
    assert settings.payment_networks[0].wallet == "0x1111111111111111111111111111111111111111"
    assert settings.payment_networks[0].token_contract == "0x55d398326f99059fF775485246999027B3197955"


def test_build_admin_settings_preserves_explicit_empty_wallets_without_repopulating_defaults():
    settings = build_admin_settings(
        {
            "wallets": {},
            "smtp_host": "smtp.example.com",
            "smtp_port": 2525,
            "smtp_user": "mailer@example.com",
            "admin_email": "admin@example.com",
            "price_per_month_usd": "100",
            "payment_tolerance_usd": "5",
        },
        payment_network_rows=[],
        env_settings=SimpleNamespace(
            WALLETS={
                "BSC_USDT": "0xenv0000000000000000000000000000000000000001",
                "BSC_USDC": "0xenv0000000000000000000000000000000000000002",
            },
            PAYMENT_MIN_CONFIRMATIONS=10,
            PAYMENT_TOLERANCE_USD=Decimal("5"),
            PRICE_PER_MONTH_USD=Decimal("100"),
            SMTP_HOST="smtp.gmail.com",
            SMTP_PORT=587,
            SMTP_USER="",
            ADMIN_EMAIL="admin@example.com",
        ),
    )

    assert settings.wallets == {}
    assert settings.payment_networks == []


def test_admin_settings_update_allows_derived_token_contracts():
    payload = AdminSettingsUpdate(
        payment_networks=[
            {
                "network_code": "BSC_USDT",
                "label": "BNB Chain (USDT)",
                "chain": "BSC",
                "wallet": "0x1111111111111111111111111111111111111111",
                "is_active": True,
            }
        ]
    )

    assert payload.payment_networks is not None
    assert payload.payment_networks[0].network_code == "BSC_USDT"
    assert payload.payment_networks[0].token_contract is None
    assert payload.payment_networks[0].min_confirmations is None
    assert payload.payment_networks[0].tolerance_usd is None


def test_normalize_payment_network_rows_preserves_existing_defaults_for_partial_updates():
    from admin_api.settings_service import normalize_payment_network_rows

    rows = normalize_payment_network_rows(
        payment_network_rows=[
            {
                "network_code": "BSC_USDT",
                "label": "BNB Chain (USDT)",
                "chain": "BSC",
                "wallet": "0x1111111111111111111111111111111111111111",
                "is_active": True,
            }
        ],
        existing_payment_network_rows=[
            {
                "network_code": "BSC_USDT",
                "token_contract": "0xcustom000000000000000000000000000000000001",
                "min_confirmations": 18,
                "tolerance_usd": Decimal("2.5"),
            }
        ],
    )

    assert rows[0].token_contract == "0xcustom000000000000000000000000000000000001"
    assert rows[0].min_confirmations == 18
    assert rows[0].tolerance_usd == Decimal("2.5")


def test_build_admin_settings_preserves_manual_token_contract_override():
    settings = build_admin_settings(
        {
            "wallets": {
                "BSC_USDT": "0x1111111111111111111111111111111111111111",
            },
            "smtp_host": "smtp.example.com",
            "smtp_port": 2525,
            "smtp_user": "mailer@example.com",
            "admin_email": "admin@example.com",
            "price_per_month_usd": "100",
            "payment_tolerance_usd": "5",
        },
        payment_network_rows=[
            {
                "network_code": "BSC_USDT",
                "label": "BNB Chain (USDT)",
                "chain": "BSC",
                "wallet": "0x1111111111111111111111111111111111111111",
                "token_contract": "0xcustom000000000000000000000000000000000001",
                "min_confirmations": 10,
                "tolerance_usd": Decimal("5"),
                "is_active": True,
            }
        ],
    )

    assert settings.payment_networks[0].token_contract == "0xcustom000000000000000000000000000000000001"


def test_build_admin_settings_includes_guild_settings():
    settings = build_admin_settings(
        {
            "wallets": {
                "BSC_USDT": "0x1111111111111111111111111111111111111111",
            },
            "smtp_host": "smtp.example.com",
            "smtp_port": 2525,
            "smtp_user": "mailer@example.com",
            "admin_email": "admin@example.com",
            "price_per_month_usd": "100",
            "payment_tolerance_usd": "5",
        },
        payment_network_rows=[
            {
                "network_code": "BSC_USDT",
                "label": "BNB Chain (USDT)",
                "chain": "BSC",
                "wallet": "0x1111111111111111111111111111111111111111",
                "token_contract": "0x55d398326f99059fF775485246999027B3197955",
                "min_confirmations": 10,
                "tolerance_usd": Decimal("5"),
                "is_active": True,
            }
        ],
        guild_settings_rows=[
            {
                "guild_id": "123456789012345678",
                "vip_role_id": "987654321098765432",
                "community_role_id": "222222222222222222",
                "welcome_channel_id": "333333333333333333",
                "setup_channel_id": "444444444444444444",
                "admin_channel_id": "555555555555555555",
                "payment_logs_channel_id": "777777777777777777",
                "support_channel_id": "666666666666666666",
                "is_active": True,
            }
        ],
    )

    assert len(settings.guild_settings) == 1
    assert settings.guild_settings[0].guild_id == "123456789012345678"
    assert settings.guild_settings[0].vip_role_id == "987654321098765432"
    assert settings.guild_settings[0].welcome_channel_id == "333333333333333333"
    assert settings.guild_settings[0].payment_logs_channel_id == "777777777777777777"


def test_normalize_guild_settings_rows_preserves_existing_values_for_partial_updates():
    from services.guild_settings import normalize_guild_settings_rows

    rows = normalize_guild_settings_rows(
        guild_settings_rows=[
            {
                "guild_id": "123456789012345678",
                "vip_role_id": "987654321098765432",
                "is_active": True,
            }
        ],
        existing_guild_settings_rows=[
            {
                "guild_id": "123456789012345678",
                "community_role_id": "222222222222222222",
                "welcome_channel_id": "333333333333333333",
                "setup_channel_id": "444444444444444444",
                "admin_channel_id": "555555555555555555",
                "payment_logs_channel_id": "777777777777777777",
                "support_channel_id": "666666666666666666",
            }
        ],
    )

    assert rows[0].guild_id == "123456789012345678"
    assert rows[0].vip_role_id == "987654321098765432"
    assert rows[0].community_role_id == "222222222222222222"
    assert rows[0].welcome_channel_id == "333333333333333333"
    assert rows[0].payment_logs_channel_id == "777777777777777777"
    assert rows[0].support_channel_id == "666666666666666666"


def test_resolve_admin_password_hash_prefers_admin_security_row():
    password_hash = resolve_admin_password_hash(
        admin_security_row={"password_hash": "security-hash"},
        admin_config_values={"admin_password_hash": "legacy-hash"},
    )

    assert password_hash == "security-hash"


def test_resolve_admin_password_hash_falls_back_to_admin_config():
    password_hash = resolve_admin_password_hash(
        admin_security_row=None,
        admin_config_values={"admin_password_hash": "legacy-hash"},
    )

    assert password_hash == "legacy-hash"


@pytest.mark.asyncio
async def test_load_current_payment_networks_prefers_database_rows(monkeypatch):
    session = object()

    async def fake_load_payment_network_rows(got_session):
        assert got_session is session
        return [
            {
                "network_code": "BSC_USDT",
                "label": "BNB Chain (USDT)",
                "chain": "BSC",
                "wallet": "0xdatabase000000000000000000000000000000000001",
                "token_contract": "0x55d398326f99059fF775485246999027B3197955",
                "min_confirmations": 10,
                "tolerance_usd": Decimal("5"),
                "is_active": True,
            }
        ]

    monkeypatch.setattr(settings_service, "load_payment_network_rows", fake_load_payment_network_rows)

    env_settings = SimpleNamespace(WALLETS={"BSC_USDT": "0xenv0000000000000000000000000000000000000001"})
    payment_networks = await settings_service.load_current_payment_networks(session, env_settings)

    assert len(payment_networks) == 1
    assert payment_networks[0].wallet == "0xdatabase000000000000000000000000000000000001"


@pytest.mark.asyncio
async def test_load_effective_admin_settings_uses_database_billing_values(monkeypatch):
    session = object()

    async def fake_load_admin_config_values(got_session):
        assert got_session is session
        return {
            "wallets": {
                "BSC_USDT": "0xdatabase000000000000000000000000000000000001",
            },
            "price_per_month_usd": "125",
            "payment_tolerance_usd": "7.5",
        }

    async def fake_load_payment_network_rows(got_session):
        assert got_session is session
        return [
            {
                "network_code": "BSC_USDT",
                "label": "BNB Chain (USDT)",
                "chain": "BSC",
                "wallet": "0xdatabase000000000000000000000000000000000001",
                "token_contract": "0x55d398326f99059fF775485246999027B3197955",
                "min_confirmations": 10,
                "tolerance_usd": Decimal("7.5"),
                "is_active": True,
            }
        ]

    async def fake_load_guild_settings_rows(got_session):
        assert got_session is session
        return []

    monkeypatch.setattr(settings_service, "load_admin_config_values", fake_load_admin_config_values)
    monkeypatch.setattr(settings_service, "load_payment_network_rows", fake_load_payment_network_rows)
    monkeypatch.setattr(settings_service, "load_guild_settings_rows", fake_load_guild_settings_rows)

    env_settings = SimpleNamespace(
        WALLETS={"BSC_USDT": "0xenv0000000000000000000000000000000000000001"},
        PRICE_PER_MONTH_USD=Decimal("100"),
        PAYMENT_TOLERANCE_USD=Decimal("5"),
    )
    admin_settings = await settings_service.load_effective_admin_settings(session, env_settings)

    assert admin_settings.wallets == {"BSC_USDT": "0xdatabase000000000000000000000000000000000001"}
    assert admin_settings.price_per_month_usd == Decimal("125")
    assert admin_settings.payment_tolerance_usd == Decimal("7.5")

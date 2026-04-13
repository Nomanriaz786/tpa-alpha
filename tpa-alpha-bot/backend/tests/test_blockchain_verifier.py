from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from hexbytes import HexBytes

import services.blockchain as blockchain


class _FakeEth:
    def __init__(self, tx, receipt, tx_timestamp, latest_block):
        self._tx = tx
        self._receipt = receipt
        self._tx_timestamp = tx_timestamp
        self.block_number = latest_block

    def get_transaction(self, _tx_hash):
        return self._tx

    def get_transaction_receipt(self, _tx_hash):
        return self._receipt

    def get_block(self, _block_number):
        return SimpleNamespace(timestamp=int(self._tx_timestamp.timestamp()))


class _FakeWeb3:
    def __init__(self, tx, receipt, tx_timestamp, latest_block):
        self.eth = _FakeEth(tx, receipt, tx_timestamp, latest_block)


class _FakeDiscord:
    def __init__(self, resolved_channel_id=None):
        self.resolved_channel_id = resolved_channel_id
        self.queries = []

    async def find_guild_channel_by_names(self, names):
        self.queries.append(tuple(names))
        return self.resolved_channel_id


def _make_transfer_log(token_contract, from_addr, to_addr, amount_raw):
    sender_topic = "0x" + ("0" * 24) + from_addr[2:].lower()
    receiver_topic = "0x" + ("0" * 24) + to_addr[2:].lower()
    data_hex = f"0x{amount_raw:064x}"
    return SimpleNamespace(
        address=token_contract,
        topics=[
            HexBytes(blockchain.TRANSFER_TOPIC),
            HexBytes(sender_topic),
            HexBytes(receiver_topic),
        ],
        data=data_hex,
    )


@pytest.mark.asyncio
async def test_verify_pending_payment_accepts_exchange_transfer_within_pending_window(monkeypatch):
    token_contract = "0x55d398326f99059fF775485246999027B3197955"
    expected_receiver = "0x2b113d10004e33ec305e2ABEDE0Dd7A14409139D"
    exchange_sender = "0xa180Fe01B906A1bE37BE6c534a3300785b20d947"
    recorded_sender = "0xc4087e5f6e89b8b11d48d7dfc17efddd359c1f41"
    tx_hash = "0xb1a8c93a05129dcee7ad6936862c2be32f76db74882654defada337c644a952b"
    amount = Decimal("9.99")
    amount_raw = int(amount * (Decimal(10) ** 18))

    pending_created_at = datetime(2026, 4, 10, 7, 48, tzinfo=timezone.utc)
    tx_timestamp = pending_created_at + timedelta(minutes=2)
    pending = SimpleNamespace(
        id="pending-1",
        tx_hash_proof=tx_hash,
        network="BSC_USDT",
        wallet_address=recorded_sender,
        amount_expected_usd=Decimal("10.00"),
        created_at=pending_created_at,
        expires_at=pending_created_at + timedelta(hours=24),
    )
    admin_settings = SimpleNamespace(
        payment_networks=[SimpleNamespace(network_code="BSC_USDT", wallet=expected_receiver)],
        payment_tolerance_usd=Decimal("5"),
    )
    settings = SimpleNamespace(
        TOKEN_CONTRACTS={
            "BSC_USDT": {
                "address": token_contract,
                "decimals": 18,
            }
        },
        PAYMENT_MIN_CONFIRMATIONS=10,
        PAYMENT_TOLERANCE_USD=Decimal("5"),
    )

    tx = SimpleNamespace(to=token_contract)
    receipt = SimpleNamespace(
        status=1,
        blockNumber=100,
        logs=[_make_transfer_log(token_contract, exchange_sender, expected_receiver, amount_raw)],
    )
    fake_web3 = _FakeWeb3(tx, receipt, tx_timestamp, latest_block=150)

    monkeypatch.setattr(blockchain, "get_settings", lambda: settings)

    async def fake_get_web3():
        return fake_web3

    monkeypatch.setattr(blockchain, "_get_web3", fake_get_web3)

    verified, message, matched_tx_hash, matched_amount = await blockchain.verify_pending_payment(
        pending,
        admin_settings,
    )

    assert verified is True
    assert message == "Verified"
    assert matched_tx_hash == tx_hash
    assert matched_amount == amount


@pytest.mark.asyncio
async def test_verify_pending_payment_rejects_exchange_transfer_outside_pending_window(monkeypatch):
    token_contract = "0x55d398326f99059fF775485246999027B3197955"
    expected_receiver = "0x2b113d10004e33ec305e2ABEDE0Dd7A14409139D"
    exchange_sender = "0xa180Fe01B906A1bE37BE6c534a3300785b20d947"
    recorded_sender = "0xc4087e5f6e89b8b11d48d7dfc17efddd359c1f41"
    tx_hash = "0xb1a8c93a05129dcee7ad6936862c2be32f76db74882654defada337c644a952b"
    amount = Decimal("9.99")
    amount_raw = int(amount * (Decimal(10) ** 18))

    pending_created_at = datetime(2026, 4, 10, 7, 48, tzinfo=timezone.utc)
    tx_timestamp = pending_created_at - timedelta(minutes=2)
    pending = SimpleNamespace(
        id="pending-2",
        tx_hash_proof=tx_hash,
        network="BSC_USDT",
        wallet_address=recorded_sender,
        amount_expected_usd=Decimal("10.00"),
        created_at=pending_created_at,
        expires_at=pending_created_at + timedelta(hours=24),
    )
    admin_settings = SimpleNamespace(
        payment_networks=[SimpleNamespace(network_code="BSC_USDT", wallet=expected_receiver)],
        payment_tolerance_usd=Decimal("5"),
    )
    settings = SimpleNamespace(
        TOKEN_CONTRACTS={
            "BSC_USDT": {
                "address": token_contract,
                "decimals": 18,
            }
        },
        PAYMENT_MIN_CONFIRMATIONS=10,
        PAYMENT_TOLERANCE_USD=Decimal("5"),
    )

    tx = SimpleNamespace(to=token_contract)
    receipt = SimpleNamespace(
        status=1,
        blockNumber=100,
        logs=[_make_transfer_log(token_contract, exchange_sender, expected_receiver, amount_raw)],
    )
    fake_web3 = _FakeWeb3(tx, receipt, tx_timestamp, latest_block=150)

    monkeypatch.setattr(blockchain, "get_settings", lambda: settings)

    async def fake_get_web3():
        return fake_web3

    monkeypatch.setattr(blockchain, "_get_web3", fake_get_web3)

    verified, message, matched_tx_hash, matched_amount = await blockchain.verify_pending_payment(
        pending,
        admin_settings,
    )

    assert verified is False
    assert message == "Transaction timestamp falls outside pending payment window"
    assert matched_tx_hash == tx_hash
    assert matched_amount is None


@pytest.mark.asyncio
async def test_resolve_payment_log_channel_prefers_explicit_channel_id():
    guild_settings = SimpleNamespace(
        payment_logs_channel_id="123456789012345678",
        admin_channel_id="999999999999999999",
    )
    discord = _FakeDiscord(resolved_channel_id="555555555555555555")

    resolved = await blockchain._resolve_payment_log_channel_id(discord, guild_settings)

    assert resolved == "123456789012345678"
    assert discord.queries == []


@pytest.mark.asyncio
async def test_resolve_payment_log_channel_uses_named_channel_before_admin_fallback():
    guild_settings = SimpleNamespace(
        payment_logs_channel_id=None,
        admin_channel_id="999999999999999999",
    )
    discord = _FakeDiscord(resolved_channel_id="555555555555555555")

    resolved = await blockchain._resolve_payment_log_channel_id(discord, guild_settings)

    assert resolved == "555555555555555555"
    assert discord.queries == [tuple(blockchain.PAYMENT_LOG_CHANNEL_CANDIDATE_NAMES)]


@pytest.mark.asyncio
async def test_resolve_payment_log_channel_falls_back_to_admin_channel():
    guild_settings = SimpleNamespace(
        payment_logs_channel_id=None,
        admin_channel_id="999999999999999999",
    )
    discord = _FakeDiscord(resolved_channel_id=None)

    resolved = await blockchain._resolve_payment_log_channel_id(discord, guild_settings)

    assert resolved == "999999999999999999"

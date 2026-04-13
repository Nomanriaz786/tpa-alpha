"""
Database models for TPA Alpha Bot
SQLAlchemy ORM models with async support
"""
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4, UUID
from sqlalchemy import Column, String, Integer, DateTime, Boolean, ForeignKey, Numeric, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()


class Subscriber(Base):
    """Discord member with active subscription"""
    __tablename__ = "subscribers"
    __table_args__ = (
        UniqueConstraint('discord_id', name='uq_subscriber_discord_id'),
        Index('idx_subscriber_discord_id', 'discord_id'),
        Index('idx_subscriber_expires_at', 'expires_at'),
        Index('idx_subscriber_is_active', 'is_active'),
    )
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    discord_id = Column(String(30), nullable=False, unique=True)
    discord_username = Column(String(255))
    tradingview_username = Column(String(255), nullable=False)  # Required at signup
    email = Column(String(255), nullable=True)
    commission_wallet = Column(String(255))  # Wallet to receive affiliate commissions
    network = Column(String(50))  # BSC, ETH, TRX, SOL, etc.
    months_paid = Column(Integer, default=0)  # Total months purchased
    expires_at = Column(DateTime(timezone=True), nullable=True)  # UTC
    is_active = Column(Boolean, default=True)
    affiliate_code_used = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    payments = relationship("Payment", back_populates="subscriber", cascade="all, delete-orphan")
    commissions = relationship("Commission", back_populates="subscriber", cascade="all, delete-orphan")


class Payment(Base):
    """Record of a blockchain payment received"""
    __tablename__ = "payments"
    __table_args__ = (
        UniqueConstraint('tx_hash', name='uq_payment_tx_hash'),
        UniqueConstraint('pending_payment_id', name='uq_payment_pending_payment_id'),
        Index('idx_payment_subscriber_id', 'subscriber_id'),
        Index('idx_payment_pending_payment_id', 'pending_payment_id'),
        Index('idx_payment_network', 'network'),
        Index('idx_payment_detected_at', 'detected_at'),
    )
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    subscriber_id = Column(PG_UUID(as_uuid=True), ForeignKey('subscribers.id'), nullable=False)
    pending_payment_id = Column(PG_UUID(as_uuid=True), ForeignKey('pending_payments.id'), nullable=True, unique=True)
    tx_hash = Column(String(255), nullable=False, unique=True)
    amount_usd = Column(Numeric(12, 2), nullable=False)
    months_granted = Column(Integer, nullable=False)
    network = Column(String(50), nullable=False)  # BSC, ETH, etc.
    detected_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    subscriber = relationship("Subscriber", back_populates="payments")
    commissions = relationship("Commission", back_populates="payment", cascade="all, delete-orphan")


class Affiliate(Base):
    """Affiliate/referral code for commissions"""
    __tablename__ = "affiliates"
    __table_args__ = (
        UniqueConstraint('code', name='uq_affiliate_code'),
        Index('idx_affiliate_discord_id', 'discord_id'),
        Index('idx_affiliate_is_active', 'is_active'),
        Index('idx_affiliate_type', 'type'),
    )
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    code = Column(String(50), nullable=False, unique=True)
    discord_id = Column(String(30), nullable=True)
    name = Column(String(255), nullable=True)
    type = Column(String(20), nullable=False)  # "main" or "sub"
    parent_id = Column(PG_UUID(as_uuid=True), ForeignKey('affiliates.id'), nullable=True)
    discount_percent = Column(Numeric(5, 2), default=Decimal("0"))
    commission_percent = Column(Numeric(5, 2), default=Decimal("0"))
    payout_wallet = Column(String(255), nullable=True)  # Wallet to send affiliate commission to
    usage_limit = Column(Integer, nullable=True)  # Max users allowed to use this code (NULL = unlimited)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    commissions = relationship("Commission", back_populates="affiliate", cascade="all, delete-orphan")
    sub_affiliates = relationship("Affiliate", remote_side=[id])


class Commission(Base):
    """Commission owed to affiliates"""
    __tablename__ = "commissions"
    __table_args__ = (
        Index('idx_commission_affiliate_id', 'affiliate_id'),
        Index('idx_commission_is_paid', 'is_paid'),
        Index('idx_commission_created_at', 'created_at'),
    )
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    affiliate_id = Column(PG_UUID(as_uuid=True), ForeignKey('affiliates.id'), nullable=False)
    subscriber_id = Column(PG_UUID(as_uuid=True), ForeignKey('subscribers.id'), nullable=False)
    payment_id = Column(PG_UUID(as_uuid=True), ForeignKey('payments.id'), nullable=False)
    amount_owed = Column(Numeric(12, 2), nullable=False)
    is_paid = Column(Boolean, default=False)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    affiliate = relationship("Affiliate", back_populates="commissions")
    subscriber = relationship("Subscriber", back_populates="commissions")
    payment = relationship("Payment", back_populates="commissions")


class PendingPayment(Base):
    """Pending payment being waited for (24h timeout)"""
    __tablename__ = "pending_payments"
    __table_args__ = (
        Index('idx_pending_payment_discord_id', 'discord_id'),
        Index('idx_pending_payment_wallet_address', 'wallet_address'),
        Index('idx_pending_payment_tx_hash_proof', 'tx_hash_proof'),
        Index('idx_pending_payment_expires_at', 'expires_at'),
    )
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    discord_id = Column(String(30), nullable=False)
    discord_username = Column(String(255), nullable=True)
    tradingview_username = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    wallet_address = Column(String(255), nullable=False)  # Sender's wallet to watch
    tx_hash_proof = Column(String(255), nullable=True)  # User-provided tx hash / explorer URL
    network = Column(String(50), nullable=False)  # BSC, ETH, etc.
    affiliate_code = Column(String(50), nullable=True)
    amount_expected_usd = Column(Numeric(12, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)  # 24 hours from creation


class PaymentNetwork(Base):
    """Configured payment network and payout wallet"""
    __tablename__ = "payment_networks"
    __table_args__ = (
        Index('idx_payment_network_chain', 'chain'),
        Index('idx_payment_network_is_active', 'is_active'),
    )

    network_code = Column(String(50), primary_key=True)
    label = Column(String(255), nullable=False)
    chain = Column(String(50), nullable=False)
    wallet = Column(String(255), nullable=False)
    token_contract = Column(String(255), nullable=False)
    min_confirmations = Column(Integer, default=10, nullable=False)
    tolerance_usd = Column(Numeric(12, 2), default=Decimal("5"), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AdminSession(Base):
    """Admin authentication session"""
    __tablename__ = "admin_sessions"
    __table_args__ = (
        UniqueConstraint('token', name='uq_admin_session_token'),
        Index('idx_admin_session_created_at', 'created_at'),
    )
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    token = Column(String(255), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used = Column(DateTime(timezone=True), server_default=func.now())


class AdminSecurity(Base):
    """Dedicated admin security state"""
    __tablename__ = "admin_security"

    id = Column(Integer, primary_key=True)
    password_hash = Column(String(255), nullable=False)
    password_version = Column(Integer, default=1, nullable=False)
    password_changed_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AdminConfig(Base):
    """Key-value store for admin configuration"""
    __tablename__ = "admin_config"
    
    key = Column(String(255), primary_key=True)
    value = Column(String(4096))  # Store as JSON string for complex values
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class GuildSettings(Base):
    """Discord guild-level configuration and role/channel identifiers"""
    __tablename__ = "guild_settings"

    guild_id = Column(String(30), primary_key=True)
    vip_role_id = Column(String(30), nullable=True)
    community_role_id = Column(String(30), nullable=True)
    welcome_channel_id = Column(String(30), nullable=True)
    setup_channel_id = Column(String(30), nullable=True)
    admin_channel_id = Column(String(30), nullable=True)
    payment_logs_channel_id = Column(String(30), nullable=True)
    support_channel_id = Column(String(30), nullable=True)
    is_active = Column(Boolean, default=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class DiscordFailureLog(Base):
    """Track Discord API failures for manual recovery"""
    __tablename__ = "discord_failure_logs"
    __table_args__ = (
        Index('idx_discord_failure_log_discord_id', 'discord_id'),
        Index('idx_discord_failure_log_created_at', 'created_at'),
    )
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    discord_id = Column(String(30), nullable=False)
    action = Column(String(50), nullable=False)  # "assign_role", "remove_role", "send_dm", etc.
    error_message = Column(String(1024))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    attempted_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

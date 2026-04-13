"""
Pydantic schemas for request/response validation
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field, validator


# ============================================================================
# Payment Schemas
# ============================================================================

class PaymentInitiateRequest(BaseModel):
    """POST /api/payment/initiate request"""
    discord_id: str = Field(..., description="Discord user ID")
    discord_username: str = Field(..., description="Discord username")
    tradingview_username: str = Field(..., description="TradingView username (required)")
    email: Optional[str] = Field(None, description="Email for confirmation")
    affiliate_code: Optional[str] = Field(None, description="Referral code")
    network: str = Field(..., description="BSC, ETH, TRX, SOL")
    sender_wallet: str = Field(..., description="Wallet address sending payment")
    
    @validator("tradingview_username")
    def validate_tv_username(cls, v):
        if not v or not v.strip():
            raise ValueError("TradingView username is required")
        return v.strip()


class PaymentInitiateResponse(BaseModel):
    """Response with payment details"""
    pending_id: UUID
    wallet_to_pay: str
    amount_usd: Decimal
    discount_applied: Decimal = Decimal("0")
    network: str
    discount_percent: Optional[Decimal] = None


class PaymentProofSubmitRequest(BaseModel):
    """POST /api/payment/proof request"""
    pending_id: UUID
    tx_hash_or_url: str = Field(..., min_length=16, max_length=300)


class NetworkInfo(BaseModel):
    """Available crypto network for payment"""
    id: str  # "BSC_USDT", "BSC_USDC"
    label: str  # "BNB Chain (USDT)"
    chain: str  # "BSC"
    wallet: str  # Wallet address
    token_contract: Optional[str] = None
    min_confirmations: int = 10
    tolerance_usd: Decimal = Decimal("5")
    is_active: bool = True


class PaymentNetworkBase(BaseModel):
    """Shared payment network settings"""
    network_code: str
    label: str
    chain: str
    wallet: str
    min_confirmations: int = 10
    tolerance_usd: Decimal = Decimal("5")
    is_active: bool = True


class PaymentNetworkConfig(PaymentNetworkBase):
    """Stored payment network settings"""
    token_contract: str

    class Config:
        from_attributes = True


class PaymentNetworkUpdate(PaymentNetworkBase):
    """Admin update payload for payment networks"""
    token_contract: Optional[str] = None
    min_confirmations: Optional[int] = None
    tolerance_usd: Optional[Decimal] = None


class PaymentStatusResponse(BaseModel):
    """Response from payment status check"""
    status: str  # "pending", "detected", "expired"
    tx_hash_proof: Optional[str] = None
    tx_hash: Optional[str] = None
    months_granted: Optional[int] = None
    expires_at: Optional[datetime] = None


# ============================================================================
# Subscriber Schemas
# ============================================================================

class SubscriberCreate(BaseModel):
    """Create subscriber (internal use)"""
    discord_id: str
    discord_username: str
    tradingview_username: str
    email: Optional[str] = None
    commission_wallet: str
    network: str


class SubscriberResponse(BaseModel):
    """Subscriber read response"""
    id: UUID
    discord_id: str
    discord_username: str
    tradingview_username: str
    email: Optional[str]
    expires_at: Optional[datetime]
    is_active: bool
    months_paid: int
    created_at: datetime
    commission_wallet: Optional[str] = None
    network: Optional[str] = None
    owned_referral_code: Optional[str] = None
    owned_referral_link: Optional[str] = None
    
    class Config:
        from_attributes = True


class SubscriberListResponse(BaseModel):
    """Paginated subscriber list"""
    items: List[SubscriberResponse]
    total: int
    page: int
    per_page: int


class SubscriberExtendRequest(BaseModel):
    """Extend subscriber subscription"""
    months: int = Field(..., gt=0, le=12, description="Months to add (1-12)")


# ============================================================================
# Affiliate Schemas
# ============================================================================

class AffiliateCreate(BaseModel):
    """Create affiliate (promo code with discount only)"""
    code: str = Field(..., min_length=3, max_length=20, pattern=r"^[a-zA-Z0-9]+$")
    discord_id: Optional[str] = None
    name: Optional[str] = None
    type: str = Field(default="promo", description="'promo' or 'member'")
    parent_id: Optional[UUID] = None
    discount_percent: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    usage_limit: Optional[int] = Field(None, ge=1)  # Max users for this code (NULL = unlimited)
    is_active: bool = True

    @validator("code")
    def normalize_affiliate_code(cls, v):
        return v.strip().upper()

    @validator("discord_id")
    def normalize_discord_id(cls, v):
        if v is None:
            return None
        cleaned = v.strip()
        return cleaned or None

    @validator("type")
    def validate_affiliate_type(cls, v):
        cleaned = (v or "").strip().lower()
        if cleaned not in {"promo", "member", "main", "sub"}:
            raise ValueError("Affiliate type must be promo or member")
        return "promo" if cleaned in {"main", "sub"} else cleaned


class AffiliateUpdate(BaseModel):
    """Update affiliate (commission managed in settings)"""
    name: Optional[str] = None
    discount_percent: Optional[Decimal] = Field(None, ge=0, le=100)
    commission_percent: Optional[Decimal] = Field(None, ge=0, le=100)
    payout_wallet: Optional[str] = None
    usage_limit: Optional[int] = Field(None, ge=1)  # Max users for this code
    is_active: Optional[bool] = None


class AffiliateResponse(BaseModel):
    """Affiliate read response"""
    id: UUID
    code: str
    discord_id: Optional[str]
    name: Optional[str]
    type: str
    discount_percent: Decimal
    commission_percent: Decimal
    payout_wallet: Optional[str] = None
    usage_limit: Optional[int] = None  # Max users allowed (NULL = unlimited)
    is_active: bool
    created_at: datetime
    affiliate_link: Optional[str] = None
    
    class Config:
        from_attributes = True


class AffiliateDetailResponse(AffiliateResponse):
    """Affiliate with stats"""
    active_members: int
    usage_count: int  # Total members who have used this code
    total_commissions_owed: Decimal
    total_commissions_paid: Decimal


class AffiliateListResponse(BaseModel):
    """Paginated affiliate list"""
    items: List[AffiliateResponse]
    total: int
    page: int
    per_page: int


class CommissionMarkPaidRequest(BaseModel):
    """Mark commissions as paid"""
    commission_ids: List[UUID]


# ============================================================================
# Admin Schemas
# ============================================================================

class AdminLoginRequest(BaseModel):
    """Admin login"""
    password: str


class AdminLoginResponse(BaseModel):
    """Admin login response"""
    token: str
    expires_at: datetime


class AdminPasswordChangeRequest(BaseModel):
    """Change the admin password"""
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)


class AdminPasswordChangeResponse(BaseModel):
    """Admin password change response"""
    status: str
    password_version: int
    updated_at: datetime


class DashboardStats(BaseModel):
    """Dashboard overview stats"""
    total_subscribers: int
    active_subscribers: int
    monthly_revenue_usd: float
    unpaid_commissions_usd: float


class DashboardResponse(BaseModel):
    """Dashboard full response"""
    stats: DashboardStats
    recent_subscribers: List[SubscriberResponse]


class AdminSettings(BaseModel):
    """Admin settings"""
    wallets: dict  # { "BSC_USDT": "0x...", ... }
    payment_networks: List[PaymentNetworkConfig] = Field(default_factory=list)
    guild_settings: List["GuildSettingsConfig"] = Field(default_factory=list)
    smtp_host: str
    smtp_port: int
    smtp_user: str
    admin_email: str
    price_per_month_usd: Decimal
    payment_tolerance_usd: Decimal


class AdminSettingsUpdate(BaseModel):
    """Update admin settings"""
    wallets: Optional[dict] = None
    payment_networks: Optional[List[PaymentNetworkUpdate]] = None
    guild_settings: Optional[List["GuildSettingsUpdate"]] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_user: Optional[str] = None
    smtp_pass: Optional[str] = None
    admin_email: Optional[str] = None
    price_per_month_usd: Optional[Decimal] = None
    payment_tolerance_usd: Optional[Decimal] = None


class GuildSettingsConfig(BaseModel):
    """Stored Discord guild settings"""
    guild_id: str
    vip_role_id: Optional[str] = None
    community_role_id: Optional[str] = None
    welcome_channel_id: Optional[str] = None
    setup_channel_id: Optional[str] = None
    admin_channel_id: Optional[str] = None
    payment_logs_channel_id: Optional[str] = None
    support_channel_id: Optional[str] = None
    is_active: bool = True
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class GuildSettingsUpdate(BaseModel):
    """Admin update payload for guild settings"""
    guild_id: str
    vip_role_id: Optional[str] = None
    community_role_id: Optional[str] = None
    welcome_channel_id: Optional[str] = None
    setup_channel_id: Optional[str] = None
    admin_channel_id: Optional[str] = None
    payment_logs_channel_id: Optional[str] = None
    support_channel_id: Optional[str] = None
    is_active: Optional[bool] = None


AdminSettings.model_rebuild()
AdminSettingsUpdate.model_rebuild()


# ============================================================================
# Error Schemas
# ============================================================================

class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str
    detail: Optional[str] = None
    status_code: int

"""Pydantic v2 schemas."""
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# --- Auth ---
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    totp_code: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class VerifyEmailRequest(BaseModel):
    token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


class SetupAdminRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    full_name: str | None = None


class UserOut(BaseModel):
    id: UUID
    email: str
    full_name: str | None
    is_active: bool
    is_suspended: bool
    is_email_verified: bool
    totp_enabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionOut(BaseModel):
    id: UUID
    token_type: str
    is_revoked: bool
    ip_address: str | None
    expires_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Connections ---
class ConnectionCreate(BaseModel):
    api_key: str = Field(min_length=8)
    api_secret: str = Field(min_length=8)
    environment: str = "live"
    label: str | None = None


class ConnectionOut(BaseModel):
    id: UUID
    exchange: str
    environment: str
    api_key_masked: str
    label: str | None
    is_active: bool
    can_trade: bool
    can_read: bool
    permissions: list | None
    last_validated_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Bot settings ---
class BotSettingsIn(BaseModel):
    is_enabled: bool | None = None
    risk_per_trade_pct: Decimal | None = None
    min_risk_usd: Decimal | None = None
    daily_loss_limit_pct: Decimal | None = None
    max_positions: int | None = Field(default=None, ge=1, le=10)
    max_leverage: int | None = Field(default=None, ge=10, le=50)
    reward_risk_ratio: Decimal | None = None
    trading_enabled: bool | None = None
    symbols: list[str] | None = None


class BotSettingsOut(BaseModel):
    user_id: UUID
    is_enabled: bool
    is_paused: bool
    risk_per_trade_pct: Decimal
    min_risk_usd: Decimal
    daily_loss_limit_pct: Decimal
    max_positions: int
    max_leverage: int
    reward_risk_ratio: Decimal
    trading_enabled: bool
    symbols: list | None

    model_config = {"from_attributes": True}


# --- Signals ---
class SignalOut(BaseModel):
    id: UUID
    symbol: str
    direction: str
    timeframe: str
    entry_price: Decimal | None
    stop_loss: Decimal | None
    take_profit: Decimal | None
    confidence_score: Decimal | None
    indicators: dict | None
    supporting_conditions: list | None
    invalidating_conditions: list | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Trades / orders / positions ---
class TradeOut(BaseModel):
    id: UUID
    symbol: str
    side: str
    status: str
    entry_price: Decimal | None
    exit_price: Decimal | None
    quantity: Decimal | None
    leverage: int
    realized_pnl: Decimal | None
    fees: Decimal | None
    environment: str
    opened_at: datetime
    closed_at: datetime | None

    model_config = {"from_attributes": True}


class OrderOut(BaseModel):
    id: UUID
    symbol: str
    client_order_id: str
    side: str
    order_type: str
    status: str
    quantity: Decimal
    price: Decimal | None
    executed_qty: Decimal
    avg_price: Decimal | None
    reduce_only: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class PositionOut(BaseModel):
    id: UUID
    symbol: str
    side: str
    quantity: Decimal
    entry_price: Decimal
    mark_price: Decimal | None
    leverage: int
    unrealized_pnl: Decimal | None
    liquidation_price: Decimal | None
    is_open: bool

    model_config = {"from_attributes": True}


# --- Notifications ---
class NotificationOut(BaseModel):
    id: UUID
    type: str
    title: str
    message: str
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Admin ---
class AdminUserOut(BaseModel):
    id: UUID
    email: str
    full_name: str | None
    is_active: bool
    is_suspended: bool
    is_email_verified: bool
    last_login_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogOut(BaseModel):
    id: UUID
    admin_id: UUID
    action: str
    target_type: str | None
    target_id: str | None
    details: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}


class SettingIn(BaseModel):
    value: str
    description: str | None = None


class MaintenanceIn(BaseModel):
    enabled: bool
    message: str | None = None


class LiveTradingActivation(BaseModel):
    confirm: bool = False
    acknowledgement: str = ""


# --- Profile / password / 2FA (gap closures, 2026-11-25) ---
class UpdateProfileRequest(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class TwoFAVerifyRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6)


class TwoFADisableRequest(BaseModel):
    current_password: str
    code: str | None = None


# --- Contact ---
class ContactCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    message: str = Field(min_length=1, max_length=5000)


class ContactOut(BaseModel):
    id: UUID
    name: str
    email: str
    message: str
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Market klines ---
class KlineOut(BaseModel):
    open_time: int
    open: str
    high: str
    low: str
    close: str
    volume: str
    close_time: int

"""All database models. PostgreSQL is the deployment target; SQLite is used
only for local verification. UUID PKs, UTC timestamps, Decimal precision."""
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base

JSONType = JSON().with_variant(JSONB(), "postgresql")


def _pk():
    return uuid.uuid4()


def _now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_pk)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_suspended: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    email_verification_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_reset_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_reset_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    totp_secret: Mapped[str | None] = mapped_column(String(64), nullable=True)
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    connections = relationship("ExchangeConnection", back_populates="user", cascade="all, delete-orphan")
    bot_settings = relationship("BotSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")
    trades = relationship("Trade", back_populates="user")
    orders = relationship("Order", back_populates="user")
    positions = relationship("Position", back_populates="user")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    subscription = relationship("Subscription", back_populates="user", uselist=False, cascade="all, delete-orphan")


class SuperAdmin(Base):
    __tablename__ = "super_admin"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_pk)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=True)
    totp_secret: Mapped[str | None] = mapped_column(String(64), nullable=True)
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)


class UserSession(Base):
    __tablename__ = "user_sessions"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_pk)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    jti: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    token_type: Mapped[str] = mapped_column(String(16), default="refresh", nullable=False)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)

    user = relationship("User", back_populates="sessions")


class ExchangeConnection(Base):
    __tablename__ = "exchange_connections"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_pk)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    exchange: Mapped[str] = mapped_column(String(32), default="binance_futures", nullable=False)
    environment: Mapped[str] = mapped_column(String(16), default="live", nullable=False)  # live|testnet
    api_key_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    api_secret_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    api_key_last4: Mapped[str] = mapped_column(String(8), nullable=False)
    label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    can_trade: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    can_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    permissions: Mapped[list | None] = mapped_column(JSONType, nullable=True)
    last_validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    user = relationship("User", back_populates="connections")


class BotSettings(Base):
    __tablename__ = "bot_settings"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_pk)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_paused: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    risk_per_trade_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.50"), nullable=False)
    min_risk_usd: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("2.00"), nullable=False)
    daily_loss_limit_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("2.00"), nullable=False)
    max_positions: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    max_leverage: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    reward_risk_ratio: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("2.00"), nullable=False)
    trading_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    symbols: Mapped[list | None] = mapped_column(JSONType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    user = relationship("User", back_populates="bot_settings")


class TradingStrategy(Base):
    __tablename__ = "trading_strategies"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_pk)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    parameters: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)


class MarketSignal(Base):
    __tablename__ = "market_signals"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_pk)
    symbol: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    direction: Mapped[str] = mapped_column(String(8), nullable=False)  # LONG|SHORT|WAIT
    strategy_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("trading_strategies.id"), nullable=True)
    timeframe: Mapped[str] = mapped_column(String(8), default="1h", nullable=False)
    entry_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    stop_loss: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    take_profit: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    indicators: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    supporting_conditions: Mapped[list | None] = mapped_column(JSONType, nullable=True)
    invalidating_conditions: Mapped[list | None] = mapped_column(JSONType, nullable=True)
    estimated_fee: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    estimated_slippage: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="new", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True, nullable=False)

    __table_args__ = (Index("ix_signals_symbol_created", "symbol", "created_at"),)


class Trade(Base):
    __tablename__ = "trades"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_pk)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    signal_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("market_signals.id"), nullable=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)  # LONG|SHORT
    status: Mapped[str] = mapped_column(String(16), default="open", nullable=False)  # open|closed|cancelled
    entry_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    exit_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    leverage: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    stop_loss: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    take_profit: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    realized_pnl: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    fees: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    funding_fees: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    environment: Mapped[str] = mapped_column(String(16), default="live", nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="trades")
    orders = relationship("Order", back_populates="trade")


class Order(Base):
    __tablename__ = "orders"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_pk)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    trade_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("trades.id", ondelete="SET NULL"), nullable=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    exchange_order_id: Mapped[int | None] = mapped_column(nullable=True)
    client_order_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)  # BUY|SELL
    order_type: Mapped[str] = mapped_column(String(32), nullable=False)  # MARKET|LIMIT|STOP_MARKET|TAKE_PROFIT_MARKET
    status: Mapped[str] = mapped_column(String(32), default="NEW", nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    price: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    executed_qty: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("0"), nullable=False)
    avg_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    reduce_only: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    environment: Mapped[str] = mapped_column(String(16), default="live", nullable=False)
    raw_response: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    user = relationship("User", back_populates="orders")
    trade = relationship("Trade", back_populates="orders")


class Position(Base):
    __tablename__ = "positions"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_pk)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)  # LONG|SHORT
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    entry_price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    mark_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    leverage: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    unrealized_pnl: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    liquidation_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    is_open: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    environment: Mapped[str] = mapped_column(String(16), default="live", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    user = relationship("User", back_populates="positions")

    __table_args__ = (UniqueConstraint("user_id", "symbol", "environment", name="uq_position_user_symbol_env"),)


class RiskEvent(Base):
    __tablename__ = "risk_events"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_pk)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    symbol: Mapped[str | None] = mapped_column(String(32), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True, nullable=False)


class UserActivityLog(Base):
    __tablename__ = "user_activity_logs"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_pk)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True, nullable=False)


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_pk)
    admin_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("super_admin.id"), index=True, nullable=False)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True, nullable=False)


class Subscription(Base):
    __tablename__ = "subscriptions"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_pk)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    plan: Mapped[str] = mapped_column(String(32), default="Free", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    user = relationship("User", back_populates="subscription")


class Payment(Base):
    __tablename__ = "payments"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_pk)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    subscription_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("subscriptions.id"), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="USD", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    provider: Mapped[str] = mapped_column(String(32), default="stub", nullable=False)
    provider_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_pk)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    data: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True, nullable=False)

    user = relationship("User", back_populates="notifications")


class SystemSetting(Base):
    __tablename__ = "system_settings"
    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)


class SystemHealthLog(Base):
    __tablename__ = "system_health_logs"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_pk)
    component: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True, nullable=False)


class ContactMessage(Base):
    """Public contact-form message (POST /api/v1/contact). No auth required;
    never store passwords or API secrets here."""
    __tablename__ = "contact_messages"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_pk)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True, nullable=False)

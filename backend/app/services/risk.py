"""Risk engine — Testnet defaults.
Enforced before every order; blocks are logged as risk_events.
There is intentionally NO daily-loss halt: the per-trade stop loss is the
loss control, and the bot keeps trading through losing days."""
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import BotSettings, Position, RiskEvent


@dataclass
class RiskDecision:
    allowed: bool
    reason: str = ""
    position_size: Decimal | None = None
    stop_loss: Decimal | None = None


async def log_risk_event(db: AsyncSession, user_id, event_type: str, message: str,
                         symbol: str | None = None, details: dict | None = None):
    db.add(RiskEvent(user_id=user_id, event_type=event_type, symbol=symbol,
                     message=message, details=details))
    await db.commit()


async def get_effective_settings(db: AsyncSession, user_id) -> BotSettings:
    result = await db.execute(select(BotSettings).where(BotSettings.user_id == user_id))
    settings = result.scalar_one_or_none()
    if settings is None:
        s = get_settings()
        settings = BotSettings(
            user_id=user_id,
            risk_per_trade_pct=Decimal(str(s.risk_per_trade_pct)),
            min_risk_usd=Decimal(str(s.min_risk_usd)),
            daily_loss_limit_pct=Decimal(str(s.daily_loss_limit_pct)),
            max_positions=s.max_positions,
            max_leverage=s.max_leverage,
            reward_risk_ratio=Decimal(str(s.reward_risk_ratio)),
        )
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    return settings


async def is_global_stop_active(db: AsyncSession) -> bool:
    from app.models import SystemSetting
    result = await db.execute(
        select(SystemSetting).where(SystemSetting.key == "emergency_stop"))
    row = result.scalar_one_or_none()
    return bool(row and row.value.lower() == "true")


async def check_trade_allowed(db: AsyncSession, user_id, symbol: str, equity: Decimal,
                              entry: Decimal, stop_loss: Decimal,
                              leverage: int) -> RiskDecision:
    """Run every pre-trade check. Returns position size if allowed."""
    settings = await get_effective_settings(db, user_id)

    if await is_global_stop_active(db):
        await log_risk_event(db, user_id, "emergency_stop", "Global emergency stop is active", symbol)
        return RiskDecision(False, "Global emergency stop is active")

    if settings.is_paused:
        await log_risk_event(db, user_id, "bot_paused", "Bot is paused for this user", symbol)
        return RiskDecision(False, "Bot is paused")

    # Effective max leverage is always kept within 10x–50x, so a stored
    # pre-change default (2x) can never block a trade executed at 10x+.
    effective_max_leverage = min(max(settings.max_leverage, 10), 50)
    if leverage > effective_max_leverage:
        await log_risk_event(db, user_id, "leverage_exceeded",
                             f"Requested leverage {leverage}x exceeds max {effective_max_leverage}x", symbol)
        return RiskDecision(False, f"Leverage {leverage}x exceeds max {effective_max_leverage}x")

    open_count = (await db.execute(
        select(func.count()).select_from(Position).where(
            Position.user_id == user_id, Position.is_open == True))).scalar()  # noqa: E712
    if open_count >= settings.max_positions:
        await log_risk_event(db, user_id, "max_positions",
                             f"Already at max positions ({settings.max_positions})", symbol)
        return RiskDecision(False, f"Max positions ({settings.max_positions}) reached")

    # NOTE: no daily-loss halt by design. A losing day does not stop the bot;
    # each trade's loss is capped by its own stop loss.

    # Position sizing: risk_amount = max(equity * risk%, min_risk_usd);
    # size = risk / |entry - stop|. The $2 floor keeps a small account from
    # trading dust-sized positions (0.5% of $10 is only $0.05); the risk
    # scales up with equity once the percentage exceeds the floor. The
    # equity x leverage notional cap below still takes precedence: if the
    # floored risk would need more margin than the account has, the
    # position is capped and the actual risk is lower.
    min_risk = settings.min_risk_usd
    if min_risk is None:
        min_risk = Decimal(str(get_settings().min_risk_usd))
    risk_amount = max(equity * settings.risk_per_trade_pct / 100, min_risk)
    stop_distance = abs(entry - stop_loss)
    if stop_distance <= 0:
        return RiskDecision(False, "Invalid stop distance")
    size = risk_amount / stop_distance
    # Cap notional at equity * leverage
    max_notional = equity * leverage
    if size * entry > max_notional:
        size = max_notional / entry
    return RiskDecision(True, position_size=size.quantize(Decimal("0.00000001")),
                        stop_loss=stop_loss)

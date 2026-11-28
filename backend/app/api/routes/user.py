"""Bot settings + start/stop, signals, dashboard, trades, notifications, scanner
— user-facing routes."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import (
    BotSettings, ExchangeConnection, MarketSignal, Notification, Order, Position,
    Trade, User,
)
from app.schemas import (
    BotSettingsIn, BotSettingsOut, NotificationOut, OrderOut,
    PositionOut, SignalOut, TradeOut,
)
from app.services.notifications import notify
from app.services.scanner import DEFAULT_SYMBOLS, run_scan

router = APIRouter(tags=["user"])


# --- Bot settings ---
@router.get("/bot/settings", response_model=BotSettingsOut)
async def get_bot_settings(current: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from app.services.risk import get_effective_settings
    return await get_effective_settings(db, current.id)


@router.put("/bot/settings", response_model=BotSettingsOut)
async def update_bot_settings(body: BotSettingsIn, current: User = Depends(get_current_user),
                              db: AsyncSession = Depends(get_db)):
    from app.services.risk import get_effective_settings
    settings = await get_effective_settings(db, current.id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(settings, field, value)
    await db.commit()
    await db.refresh(settings)
    return settings


@router.post("/bot/start")
async def start_bot(current: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from app.services.risk import get_effective_settings
    settings = await get_effective_settings(db, current.id)
    if settings.is_paused:
        raise HTTPException(status_code=400, detail="Bot is paused by admin — cannot start")
    settings.is_enabled = True
    await db.commit()
    await notify(db, current.id, "bot_started", "Bot started", "Your trading bot has been started.")
    return {"detail": "Bot started"}


@router.post("/bot/stop")
async def stop_bot(current: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from app.services.risk import get_effective_settings
    settings = await get_effective_settings(db, current.id)
    settings.is_enabled = False
    await db.commit()
    await notify(db, current.id, "bot_stopped", "Bot stopped", "Your trading bot has been stopped.")
    return {"detail": "Bot stopped"}


# --- Signals ---
@router.get("/signals", response_model=list[SignalOut])
async def list_signals(symbol: str | None = Query(default=None), limit: int = Query(default=50, le=200),
                       current: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    q = select(MarketSignal).order_by(desc(MarketSignal.created_at)).limit(limit)
    if symbol:
        q = q.where(MarketSignal.symbol == symbol.upper())
    rows = (await db.execute(q)).scalars().all()
    return rows


# --- Dashboard ---
@router.get("/dashboard/overview")
async def dashboard_overview(current: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    open_positions = (await db.execute(
        select(func.count()).select_from(Position).where(
            Position.user_id == current.id, Position.is_open == True))).scalar()  # noqa: E712
    total_trades = (await db.execute(
        select(func.count()).select_from(Trade).where(Trade.user_id == current.id))).scalar()
    total_pnl = (await db.execute(
        select(func.coalesce(func.sum(Trade.realized_pnl), 0)).where(Trade.user_id == current.id))).scalar()
    latest_signals = (await db.execute(
        select(MarketSignal).order_by(desc(MarketSignal.created_at)).limit(5))).scalars().all()
    unread = (await db.execute(
        select(func.count()).select_from(Notification).where(
            Notification.user_id == current.id, Notification.is_read == False))).scalar()  # noqa: E712
    # --- Enriched metrics, computed from real closed trades only ---
    closed = (await db.execute(
        select(Trade).where(Trade.user_id == current.id, Trade.status == "closed")
        .order_by(Trade.closed_at))).scalars().all()
    volume = 0.0
    wins = 0
    equity, peak, max_dd = 0.0, 0.0, 0.0
    for t in closed:
        pnl = float(t.realized_pnl or 0)
        if pnl > 0:
            wins += 1
        price = t.exit_price or t.entry_price
        if t.quantity and price:
            volume += float(t.quantity) * float(price)
        equity += pnl
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
    closed_count = len(closed)
    win_rate = (wins / closed_count) if closed_count else None
    # --- Available balance: ONLY from a connected Binance account, never invented ---
    available_balance: float | None = None
    balance_status = "no_binance_connection"
    conn = (await db.execute(
        select(ExchangeConnection).where(ExchangeConnection.user_id == current.id,
                                         ExchangeConnection.is_active == True))).scalar_one_or_none()  # noqa: E712
    if conn is not None:
        balance_status = "fetch_failed"
        try:
            from app.core.security import decrypt_secret
            from app.services.binance_client import BinanceClient
            async with BinanceClient(decrypt_secret(conn.api_key_encrypted),
                                     decrypt_secret(conn.api_secret_encrypted),
                                     testnet=(conn.environment == "testnet")) as client:
                assets = await client.balances()
            usdt = next((a for a in assets if a.get("asset") == "USDT"), None)
            if usdt is not None:
                available_balance = float(usdt.get("availableBalance", 0))
                balance_status = "ok"
        except Exception:
            available_balance = None
    return {
        "user_id": str(current.id),
        "open_positions": open_positions,
        "total_trades": total_trades,
        "total_realized_pnl": str(total_pnl),
        "unread_notifications": unread,
        "latest_signals": [SignalOut.model_validate(s) for s in latest_signals],
        "closed_trades": closed_count,
        "trading_volume": round(volume, 2),
        "win_rate": win_rate,
        "max_drawdown": round(max_dd, 2),
        "available_balance": available_balance,
        "available_balance_status": balance_status,
    }


# --- Trades / orders / positions ---
@router.get("/trades", response_model=list[TradeOut])
async def list_trades(limit: int = Query(default=50, le=200), current: User = Depends(get_current_user),
                      db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(Trade).where(Trade.user_id == current.id).order_by(desc(Trade.opened_at)).limit(limit)
    )).scalars().all()
    return rows


@router.get("/trades/{trade_id}", response_model=TradeOut)
async def get_trade(trade_id: uuid.UUID, current: User = Depends(get_current_user),
                    db: AsyncSession = Depends(get_db)):
    trade = (await db.execute(
        select(Trade).where(Trade.id == trade_id, Trade.user_id == current.id))).scalar_one_or_none()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    return trade


@router.get("/positions", response_model=list[PositionOut])
async def list_positions(current: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(Position).where(Position.user_id == current.id, Position.is_open == True))).scalars().all()  # noqa: E712
    return rows


@router.get("/orders", response_model=list[OrderOut])
async def list_orders(limit: int = Query(default=50, le=200), current: User = Depends(get_current_user),
                      db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(Order).where(Order.user_id == current.id).order_by(desc(Order.created_at)).limit(limit)
    )).scalars().all()
    return rows


# --- Notifications ---
@router.get("/notifications", response_model=list[NotificationOut])
async def list_notifications(current: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(Notification).where(Notification.user_id == current.id)
        .order_by(desc(Notification.created_at)).limit(100))).scalars().all()
    return rows


@router.post("/notifications/{notif_id}/read")
async def mark_read(notif_id: uuid.UUID, current: User = Depends(get_current_user),
                    db: AsyncSession = Depends(get_db)):
    n = (await db.execute(
        select(Notification).where(Notification.id == notif_id,
                                   Notification.user_id == current.id))).scalar_one_or_none()
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    n.is_read = True
    await db.commit()
    return {"detail": "Marked as read"}


# --- Scanner ---
@router.get("/scanner/run")
async def scanner_run(symbols: str | None = Query(default=None),
                      current: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    syms = [s.strip().upper() for s in symbols.split(",")] if symbols else DEFAULT_SYMBOLS
    results = await run_scan(syms, db=db)
    return {"scanned": syms, "signals_generated": len(results),
            "signals": [{"symbol": s["symbol"], "direction": s["direction"],
                         "timeframe": s["timeframe"]} for s in results]}


@router.get("/scanner/status")
async def scanner_status(current: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    latest = (await db.execute(
        select(MarketSignal).order_by(desc(MarketSignal.created_at)).limit(1))).scalar_one_or_none()
    return {"status": "idle",
            "last_signal_at": latest.created_at.isoformat() if latest else None,
            "default_symbols": DEFAULT_SYMBOLS}

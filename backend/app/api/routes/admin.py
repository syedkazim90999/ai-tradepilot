"""Super Admin routes. Every sensitive action writes an append-only audit log.
Admins never see plaintext passwords or API secrets."""
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_admin
from app.core.security import create_access_token, decode_token, hash_password, new_jti, verify_password, verify_totp
from app.db.session import get_db
from app.models import (
    AdminAuditLog, BotSettings, ExchangeConnection, MarketSignal, Notification,
    Position, SuperAdmin, SystemHealthLog, SystemSetting, Trade, TradingStrategy, User,
)
from app.schemas import (
    AdminUserOut, AuditLogOut, LiveTradingActivation, LoginRequest, MaintenanceIn,
    SettingIn,
)
from app.services.notifications import notify

router = APIRouter(prefix="/admin", tags=["admin"])


async def _audit(db: AsyncSession, admin: SuperAdmin, action: str, request: Request,
                 target_type: str | None = None, target_id: str | None = None,
                 details: dict | None = None):
    db.add(AdminAuditLog(
        admin_id=admin.id, action=action, target_type=target_type, target_id=target_id,
        details=details or {},
        ip_address=request.client.host if request.client else None,
    ))
    await db.commit()


@router.post("/login")
async def admin_login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    admin = (await db.execute(select(SuperAdmin).where(SuperAdmin.email == body.email))).scalar_one_or_none()
    if not admin or not verify_password(body.password, admin.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not admin.is_active:
        raise HTTPException(status_code=403, detail="Admin disabled")
    if admin.totp_enabled:
        if not body.totp_code or not admin.totp_secret or not verify_totp(admin.totp_secret, body.totp_code):
            raise HTTPException(status_code=401, detail="Invalid or missing 2FA code")
    jti = new_jti()
    now = datetime.now(timezone.utc)
    payload = {"sub": str(admin.id), "jti": jti, "type": "admin_access", "iat": now,
               "exp": now + timedelta(minutes=30)}
    from app.core.config import get_settings
    token = jwt.encode(payload, get_settings().secret_key, algorithm="HS256")
    return {"access_token": token, "token_type": "bearer"}


@router.get("/overview")
async def overview(admin: SuperAdmin = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    total_users = (await db.execute(select(func.count()).select_from(User))).scalar()
    active_bots = (await db.execute(
        select(func.count()).select_from(BotSettings).where(BotSettings.is_enabled == True))).scalar()  # noqa: E712
    open_positions = (await db.execute(
        select(func.count()).select_from(Position).where(Position.is_open == True))).scalar()  # noqa: E712
    total_trades = (await db.execute(select(func.count()).select_from(Trade))).scalar()
    suspended_users = (await db.execute(
        select(func.count()).select_from(User).where(User.is_suspended == True))).scalar()  # noqa: E712
    connected_accounts = (await db.execute(
        select(func.count()).select_from(ExchangeConnection).where(
            ExchangeConnection.is_active == True))).scalar()  # noqa: E712
    closed = (await db.execute(select(Trade).where(Trade.status == "closed"))).scalars().all()
    volume = sum(float(t.quantity or 0) * float(t.exit_price or t.entry_price or 0) for t in closed)
    agg_pnl = sum(float(t.realized_pnl or 0) for t in closed)
    return {"total_users": total_users, "active_bots": active_bots,
            "open_positions": open_positions, "total_trades": total_trades,
            "suspended_users": suspended_users,
            "connected_binance_accounts": connected_accounts,
            "total_trading_volume": round(volume, 2),
            "aggregate_realized_pnl": round(agg_pnl, 2)}


@router.get("/signals")
async def admin_signals(symbol: str | None = Query(default=None),
                        direction: str | None = Query(default=None),
                        date_from: datetime | None = Query(default=None),
                        date_to: datetime | None = Query(default=None),
                        limit: int = Query(default=50, ge=1, le=200),
                        offset: int = Query(default=0, ge=0),
                        admin: SuperAdmin = Depends(get_current_admin),
                        db: AsyncSession = Depends(get_db)):
    """Admin signal history from market_signals (filterable, paginated)."""
    q = select(MarketSignal).order_by(desc(MarketSignal.created_at))
    if symbol:
        q = q.where(MarketSignal.symbol == symbol.upper())
    if direction:
        q = q.where(MarketSignal.direction == direction.upper())
    if date_from:
        q = q.where(MarketSignal.created_at >= date_from)
    if date_to:
        q = q.where(MarketSignal.created_at <= date_to)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar()
    rows = (await db.execute(q.limit(limit).offset(offset))).scalars().all()
    return {"total": total, "limit": limit, "offset": offset,
            "signals": [{"id": str(s.id), "symbol": s.symbol, "direction": s.direction,
                         "timeframe": s.timeframe,
                         "entry_price": str(s.entry_price) if s.entry_price is not None else None,
                         "stop_loss": str(s.stop_loss) if s.stop_loss is not None else None,
                         "take_profit": str(s.take_profit) if s.take_profit is not None else None,
                         "confidence_score": str(s.confidence_score) if s.confidence_score is not None else None,
                         "status": s.status, "strategy_id": str(s.strategy_id) if s.strategy_id else None,
                         "created_at": s.created_at.isoformat()} for s in rows]}


@router.get("/strategies/performance")
async def strategies_performance(admin: SuperAdmin = Depends(get_current_admin),
                                 db: AsyncSession = Depends(get_db)):
    """Strategy performance aggregated from REAL trades/signals only.
    Zeros/nulls when empty — never estimates."""
    signals = (await db.execute(select(MarketSignal))).scalars().all()
    trades = (await db.execute(select(Trade))).scalars().all()
    by_dir = {"LONG": 0, "SHORT": 0, "WAIT": 0}
    for s in signals:
        by_dir[s.direction] = by_dir.get(s.direction, 0) + 1
    closed = [t for t in trades if t.status == "closed"]
    wins = sum(1 for t in closed if float(t.realized_pnl or 0) > 0)
    strategies = (await db.execute(select(TradingStrategy))).scalars().all()
    sig_by_strategy: dict[str, list] = {}
    for s in signals:
        sig_by_strategy.setdefault(str(s.strategy_id) if s.strategy_id else "unassigned", []).append(s)
    trade_by_signal = {str(t.signal_id): t for t in trades if t.signal_id}
    per_strategy = []
    for st in strategies:
        ss = sig_by_strategy.get(str(st.id), [])
        st_trades = [trade_by_signal[str(s.id)] for s in ss if str(s.id) in trade_by_signal]
        st_closed = [t for t in st_trades if t.status == "closed"]
        st_wins = sum(1 for t in st_closed if float(t.realized_pnl or 0) > 0)
        per_strategy.append({
            "strategy_id": str(st.id), "name": st.name, "is_system": st.is_system,
            "total_signals": len(ss),
            "signals_by_direction": {d: sum(1 for s in ss if s.direction == d) for d in ("LONG", "SHORT", "WAIT")},
            "total_trades": len(st_trades), "closed_trades": len(st_closed),
            "win_rate": (st_wins / len(st_closed)) if st_closed else None,
            "realized_pnl": round(sum(float(t.realized_pnl or 0) for t in st_closed), 2),
        })
    # Signals/trades with no strategy row (scanner signals are unassigned).
    unassigned = sig_by_strategy.get("unassigned", [])
    un_trades = [trade_by_signal[str(s.id)] for s in unassigned if str(s.id) in trade_by_signal]
    un_closed = [t for t in un_trades if t.status == "closed"]
    un_wins = sum(1 for t in un_closed if float(t.realized_pnl or 0) > 0)
    if unassigned:
        per_strategy.append({
            "strategy_id": None, "name": "unassigned (scanner)", "is_system": True,
            "total_signals": len(unassigned),
            "signals_by_direction": {d: sum(1 for s in unassigned if s.direction == d) for d in ("LONG", "SHORT", "WAIT")},
            "total_trades": len(un_trades), "closed_trades": len(un_closed),
            "win_rate": (un_wins / len(un_closed)) if un_closed else None,
            "realized_pnl": round(sum(float(t.realized_pnl or 0) for t in un_closed), 2),
        })
    return {
        "total_signals": len(signals),
        "signals_by_direction": by_dir,
        "total_trades": len(trades),
        "closed_trades": len(closed),
        "win_rate": (wins / len(closed)) if closed else None,
        "realized_pnl": round(sum(float(t.realized_pnl or 0) for t in closed), 2),
        "strategies": per_strategy,
    }


@router.get("/users", response_model=list[AdminUserOut])
async def list_users(search: str | None = Query(default=None), limit: int = Query(default=50, le=200),
                     admin: SuperAdmin = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    q = select(User).order_by(desc(User.created_at)).limit(limit)
    if search:
        q = q.where(User.email.ilike(f"%{search}%"))
    return (await db.execute(q)).scalars().all()


@router.get("/users/{user_id}", response_model=AdminUserOut)
async def get_user(user_id: uuid.UUID, admin: SuperAdmin = Depends(get_current_admin),
                   db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/users/{user_id}/suspend")
async def suspend_user(user_id: uuid.UUID, request: Request, admin: SuperAdmin = Depends(get_current_admin),
                       db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_suspended = True
    await db.commit()
    await _audit(db, admin, "user_suspend", request, "user", str(user_id))
    return {"detail": "User suspended"}


@router.post("/users/{user_id}/reactivate")
async def reactivate_user(user_id: uuid.UUID, request: Request, admin: SuperAdmin = Depends(get_current_admin),
                          db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_suspended = False
    await db.commit()
    await _audit(db, admin, "user_reactivate", request, "user", str(user_id))
    return {"detail": "User reactivated"}


@router.get("/trades")
async def all_trades(limit: int = Query(default=50, le=200), admin: SuperAdmin = Depends(get_current_admin),
                     db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Trade).order_by(desc(Trade.opened_at)).limit(limit))).scalars().all()
    return [{"id": str(t.id), "user_id": str(t.user_id), "symbol": t.symbol, "side": t.side,
             "status": t.status, "entry_price": str(t.entry_price), "realized_pnl": str(t.realized_pnl),
             "opened_at": t.opened_at.isoformat()} for t in rows]


@router.get("/positions")
async def all_positions(admin: SuperAdmin = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Position).where(Position.is_open == True))).scalars().all()  # noqa: E712
    return [{"id": str(p.id), "user_id": str(p.user_id), "symbol": p.symbol, "side": p.side,
             "quantity": str(p.quantity), "entry_price": str(p.entry_price)} for p in rows]


async def _set_pause(db: AsyncSession, user_id: str | None, paused: bool):
    q = select(BotSettings)
    if user_id:
        q = q.where(BotSettings.user_id == user_id)
    rows = (await db.execute(q)).scalars().all()
    for s in rows:
        s.is_paused = paused
    await db.commit()
    return len(rows)


@router.post("/bots/pause-all")
async def pause_all(request: Request, admin: SuperAdmin = Depends(get_current_admin),
                    db: AsyncSession = Depends(get_db)):
    n = await _set_pause(db, None, True)
    await _audit(db, admin, "bots_pause_all", request, details={"affected": n})
    return {"detail": f"Paused {n} bots"}


@router.post("/bots/resume-all")
async def resume_all(request: Request, admin: SuperAdmin = Depends(get_current_admin),
                     db: AsyncSession = Depends(get_db)):
    n = await _set_pause(db, None, False)
    await _audit(db, admin, "bots_resume_all", request, details={"affected": n})
    return {"detail": f"Resumed {n} bots"}


@router.post("/bots/{user_id}/pause")
async def pause_user_bot(user_id: uuid.UUID, request: Request, admin: SuperAdmin = Depends(get_current_admin),
                         db: AsyncSession = Depends(get_db)):
    n = await _set_pause(db, user_id, True)
    if n == 0:
        raise HTTPException(status_code=404, detail="No bot settings for user")
    await _audit(db, admin, "bot_pause", request, "user", str(user_id))
    return {"detail": "Bot paused"}


@router.post("/bots/{user_id}/resume")
async def resume_user_bot(user_id: uuid.UUID, request: Request, admin: SuperAdmin = Depends(get_current_admin),
                          db: AsyncSession = Depends(get_db)):
    n = await _set_pause(db, user_id, False)
    if n == 0:
        raise HTTPException(status_code=404, detail="No bot settings for user")
    await _audit(db, admin, "bot_resume", request, "user", str(user_id))
    return {"detail": "Bot resumed"}


@router.get("/audit-logs", response_model=list[AuditLogOut])
async def audit_logs(limit: int = Query(default=100, le=500), admin: SuperAdmin = Depends(get_current_admin),
                     db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(AdminAuditLog).order_by(desc(AdminAuditLog.created_at)).limit(limit))).scalars().all()
    return rows


@router.get("/system/health")
async def system_health(admin: SuperAdmin = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    from app.core.config import get_settings
    from app.services.binance_client import BinanceClient
    s = get_settings()
    exchange_ok = False
    try:
        async with BinanceClient(testnet=s.binance_use_testnet) as client:
            await client._request("GET", "/fapi/v1/ping")
            exchange_ok = True
    except Exception:
        exchange_ok = False
    db_ok = True
    try:
        await db.execute(select(1))
    except Exception:
        db_ok = False
    return {"database": "ok" if db_ok else "error",
            "exchange_reachable": exchange_ok,
            "environment": s.environment,
            "testnet": s.binance_use_testnet}


@router.get("/settings")
async def get_settings_admin(admin: SuperAdmin = Depends(get_current_admin),
                             db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(SystemSetting))).scalars().all()
    return {r.key: r.value for r in rows}


@router.put("/settings/{key}")
async def put_setting(key: str, body: SettingIn, request: Request,
                      admin: SuperAdmin = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    row = (await db.execute(select(SystemSetting).where(SystemSetting.key == key))).scalar_one_or_none()
    if row is None:
        row = SystemSetting(key=key, value=body.value, description=body.description)
        db.add(row)
    else:
        row.value = body.value
        if body.description is not None:
            row.description = body.description
    await db.commit()
    await _audit(db, admin, "setting_update", request, "setting", key, {"value": body.value})
    return {"key": key, "value": body.value}


@router.post("/maintenance")
async def maintenance(body: MaintenanceIn, request: Request,
                      admin: SuperAdmin = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    row = (await db.execute(
        select(SystemSetting).where(SystemSetting.key == "maintenance_mode"))).scalar_one_or_none()
    if row is None:
        row = SystemSetting(key="maintenance_mode", value=str(body.enabled).lower(),
                            description=body.message or "")
        db.add(row)
    else:
        row.value = str(body.enabled).lower()
    await db.commit()
    await _audit(db, admin, "maintenance_mode", request, details={"enabled": body.enabled})
    return {"maintenance_mode": body.enabled}


@router.post("/live-trading/activate")
async def activate_live_trading(body: LiveTradingActivation, request: Request,
                                admin: SuperAdmin = Depends(get_current_admin),
                                db: AsyncSession = Depends(get_db)):
    """Explicit activation of LIVE trading. Requires confirm=true AND the exact
    acknowledgement phrase. Default state is DISABLED."""
    if not body.confirm or body.acknowledgement.strip() != "I understand live trading risks real money":
        raise HTTPException(
            status_code=400,
            detail="Live trading activation requires confirm=true and acknowledgement "
                   "'I understand live trading risks real money'")
    row = (await db.execute(
        select(SystemSetting).where(SystemSetting.key == "live_trading_enabled"))).scalar_one_or_none()
    if row is None:
        row = SystemSetting(key="live_trading_enabled", value="true",
                            description="Live trading explicitly activated by Super Admin")
        db.add(row)
    else:
        row.value = "true"
    await db.commit()
    await _audit(db, admin, "live_trading_activate", request, details={"enabled": True})
    return {"detail": "Live trading ENABLED — real money is now at risk", "live_trading_enabled": True}


@router.post("/live-trading/deactivate")
async def deactivate_live_trading(request: Request, admin: SuperAdmin = Depends(get_current_admin),
                                  db: AsyncSession = Depends(get_db)):
    row = (await db.execute(
        select(SystemSetting).where(SystemSetting.key == "live_trading_enabled"))).scalar_one_or_none()
    if row is None:
        row = SystemSetting(key="live_trading_enabled", value="false")
        db.add(row)
    else:
        row.value = "false"
    await db.commit()
    await _audit(db, admin, "live_trading_deactivate", request, details={"enabled": False})
    return {"detail": "Live trading DISABLED", "live_trading_enabled": False}

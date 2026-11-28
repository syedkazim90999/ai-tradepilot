"""Celery tasks (deployment) + standalone worker entrypoint.
Run standalone without Redis/Celery with: python -m app.worker.tasks

24/7 auto-trading loop: every scan (Celery beat, every 300s) generates
signals and immediately executes the actionable ones for every user who has
auto-trading switched on. Losing trades are closed by their own STOP_MARKET
orders; the next scan then executes the next signal, so the bot never stops.
"""
import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select

from app.core.security import decrypt_secret
from app.db.session import AsyncSessionLocal
from app.models import BotSettings, ExchangeConnection, MarketSignal, Trade
from app.services.binance_client import BinanceClient
from app.services.scanner import DEFAULT_SYMBOLS, run_scan
from app.services.trading import TradingEngine
from app.worker.celery_app import celery_app

log = logging.getLogger(__name__)

# Environments that mean "live Binance" (the frontend also sends "production").
LIVE_ENVIRONMENTS = ("live", "production")


async def _equity_from_account(info: dict) -> Decimal:
    """USDT equity from /fapi/v2/account: totalWalletBalance, falling back to
    the USDT asset's walletBalance."""
    total = info.get("totalWalletBalance")
    if total is not None:
        try:
            value = Decimal(str(total))
            if value > 0:
                return value
        except Exception:
            pass
    for asset in info.get("assets", []) or []:
        if asset.get("asset") == "USDT":
            return Decimal(str(asset.get("walletBalance", "0")))
    raise ValueError("Could not determine USDT equity from account info")


async def execute_new_signals(db, signals) -> dict:
    """Execute new LONG/SHORT signals for every auto-trading user.

    A user qualifies when BotSettings has trading_enabled=True, is_enabled=True
    and is_paused=False. Per (user, signal) the trade is executed at most once
    (checked against the trades table). Failures are caught per user/per signal
    — including the live-trading guard refusing orders while live trading is
    not activated — logged, and the loop continues with the rest.
    Returns {"executed": n, "skipped": n, "failed": n}.
    """
    counts = {"executed": 0, "skipped": 0, "failed": 0}
    actionable = [s for s in signals
                  if s.direction in ("LONG", "SHORT")
                  and s.entry_price is not None and s.stop_loss is not None]
    counts["skipped"] += len(signals) - len(actionable)
    if not actionable:
        return counts

    settings_rows = (await db.execute(
        select(BotSettings).where(BotSettings.trading_enabled == True,  # noqa: E712
                                  BotSettings.is_enabled == True,  # noqa: E712
                                  BotSettings.is_paused == False))).scalars().all()  # noqa: E712
    if not settings_rows:
        counts["skipped"] += len(actionable)
        return counts

    for sig in actionable:
        for st in settings_rows:
            user_id = st.user_id
            try:
                existing = (await db.execute(
                    select(Trade).where(Trade.user_id == user_id,
                                        Trade.signal_id == sig.id))).scalar_one_or_none()
                if existing is not None:
                    counts["skipped"] += 1
                    continue
                conn = (await db.execute(
                    select(ExchangeConnection).where(
                        ExchangeConnection.user_id == user_id,
                        ExchangeConnection.is_active == True,  # noqa: E712
                        ExchangeConnection.environment.in_(LIVE_ENVIRONMENTS)))).scalar_one_or_none()
                if conn is None:
                    log.info("No live connection for user %s; skipping signal %s",
                             user_id, sig.id)
                    counts["skipped"] += 1
                    continue
                api_key = decrypt_secret(conn.api_key_encrypted)
                api_secret = decrypt_secret(conn.api_secret_encrypted)
                async with BinanceClient(api_key, api_secret, testnet=False) as client:
                    equity = await _equity_from_account(await client.account_info())
                    engine = TradingEngine(db, client, user_id, environment="live")
                    trade = await engine.execute_signal(sig, equity)
                if trade is None:
                    counts["skipped"] += 1
                    log.info("Signal %s %s skipped for user %s (risk check)",
                             sig.symbol, sig.direction, user_id)
                else:
                    counts["executed"] += 1
                    log.info("Executed %s %s for user %s -> trade %s",
                             sig.symbol, sig.direction, user_id, trade.id)
            except Exception as exc:
                counts["failed"] += 1
                log.warning("Execution failed for user %s signal %s: %s",
                            user_id, sig.id, exc)
    return counts


@celery_app.task(name="app.worker.tasks.run_scanner")
def run_scanner_task(symbols=None):
    async def _run():
        async with AsyncSessionLocal() as db:
            scan_start = datetime.now(timezone.utc)
            results = await run_scan(symbols or DEFAULT_SYMBOLS, db=db)
            log.info("Scanner produced %d signals", len(results))
            fresh = (await db.execute(
                select(MarketSignal).where(
                    MarketSignal.created_at >= scan_start,
                    MarketSignal.direction.in_(["LONG", "SHORT"])))).scalars().all()
            counts = await execute_new_signals(db, fresh)
            log.info("Auto-execution: %s", counts)
            return len(results)
    return asyncio.run(_run())


@celery_app.task(name="app.worker.tasks.reconcile_positions")
def reconcile_positions_task():
    # Reconciliation needs per-user Binance credentials; implemented per-user
    # in TradingEngine.reconcile_positions(). This task is a placeholder that
    # logs a heartbeat until the per-user loop is wired to the scheduler.
    log.info("Reconcile task heartbeat — per-user reconciliation runs via TradingEngine")
    return "ok"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    while True:
        try:
            n = run_scanner_task(DEFAULT_SYMBOLS)
            log.info("Standalone worker scan complete: %d signals", n)
        except Exception as exc:
            log.exception("Standalone worker scan failed: %s", exc)
        asyncio.run(asyncio.sleep(300))

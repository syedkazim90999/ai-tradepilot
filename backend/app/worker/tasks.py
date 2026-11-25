"""Celery tasks (deployment) + standalone worker entrypoint.
Run standalone without Redis/Celery with: python -m app.worker.tasks
"""
import asyncio
import logging

from app.db.session import AsyncSessionLocal
from app.services.scanner import DEFAULT_SYMBOLS, run_scan
from app.worker.celery_app import celery_app

log = logging.getLogger(__name__)


@celery_app.task(name="app.worker.tasks.run_scanner")
def run_scanner_task(symbols=None):
    async def _run():
        async with AsyncSessionLocal() as db:
            results = await run_scan(symbols or DEFAULT_SYMBOLS, db=db)
            log.info("Scanner produced %d signals", len(results))
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

"""AI TradePilot — FastAPI application entrypoint."""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.api.routes import admin, auth, connections, contact, market, user
from app.core.config import get_settings
from app.db.session import AsyncSessionLocal, engine
from app.models import SystemSetting
from app.services.binance_client import BinanceClient

log = logging.getLogger(__name__)
settings = get_settings()

_worker_task: asyncio.Task | None = None


async def _seed_system_settings():
    defaults = {
        "live_trading_enabled": ("false", "Production trading DISABLED by default; requires explicit admin activation."),
        "emergency_stop": ("false", "Global emergency stop — when true, no new trades are placed."),
        "maintenance_mode": ("false", "Maintenance mode flag."),
    }
    async with AsyncSessionLocal() as db:
        for key, (value, desc) in defaults.items():
            row = (await db.execute(select(SystemSetting).where(SystemSetting.key == key))).scalar_one_or_none()
            if row is None:
                db.add(SystemSetting(key=key, value=value, description=desc))
        await db.commit()


async def _background_worker():
    """Lightweight in-app worker (used when Redis/Celery is unavailable):
    periodic scanner + position reconciliation placeholder loop."""
    while True:
        try:
            await asyncio.sleep(300)  # every 5 minutes
            log.info("Background worker heartbeat")
        except asyncio.CancelledError:
            break


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _seed_system_settings()
    global _worker_task
    _worker_task = asyncio.create_task(_background_worker())
    yield
    if _worker_task:
        _worker_task.cancel()
    await engine.dispose()


app = FastAPI(title="AI TradePilot", version="0.1.0",
              description="AI-powered Binance Futures automated trading SaaS (Testnet default).",
              lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(connections.router, prefix="/api/v1")
app.include_router(user.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(market.router, prefix="/api/v1")
app.include_router(contact.router, prefix="/api/v1")


@app.get("/health")
async def health():
    db_ok, exchange_ok = False, False
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(select(1))
        db_ok = True
    except Exception as exc:
        log.warning("Health DB check failed: %s", exc)
    try:
        async with BinanceClient(testnet=settings.binance_use_testnet) as client:
            await client._request("GET", "/fapi/v1/ping")
        exchange_ok = True
    except Exception as exc:
        log.warning("Health exchange check failed: %s", exc)
    worker_ok = _worker_task is not None and not _worker_task.done()
    status = "ok" if (db_ok and exchange_ok) else "degraded"
    return {"status": status, "database": "ok" if db_ok else "error",
            "worker": "ok" if worker_ok else "error",
            "exchange_reachable": exchange_ok, "testnet": settings.binance_use_testnet}


@app.get("/")
async def root():
    return {"app": "AI TradePilot", "version": "0.1.0", "docs": "/docs"}

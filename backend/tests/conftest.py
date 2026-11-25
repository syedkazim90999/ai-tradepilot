"""Shared fixtures: isolated scratch SQLite DB (never the dev tradepilot.db),
dependency override for get_db, auth helpers, deterministic kline fixtures."""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TEST_DB_PATH = "/tmp/test_tradepilot.db"
TEST_DB_URL = f"sqlite+aiosqlite:///{TEST_DB_PATH}"

from app.core.deps import _rate_buckets  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import MarketSignal, SuperAdmin, Trade, User  # noqa: E402
from app.core.security import hash_password  # noqa: E402

_engine = None
_Session = None


def run(coro):
    return asyncio.run(coro)


async def _create_tables():
    global _engine, _Session
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    _engine = create_async_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    _Session = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@pytest.fixture(scope="session", autouse=True)
def _test_db():
    run(_create_tables())
    async def _override():
        async with _Session() as s:
            yield s
    app.dependency_overrides[get_db] = _override
    yield
    app.dependency_overrides.clear()
    run(_engine.dispose())


@pytest.fixture(autouse=True)
def _clear_rate_limits():
    _rate_buckets.clear()
    yield
    _rate_buckets.clear()


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def unique_email(prefix="user"):
    return f"{prefix}-{uuid.uuid4().hex[:8]}@example.com"


def register_and_login(c: TestClient, email: str | None = None, password: str = "TestPass123!"):
    email = email or unique_email()
    r = c.post("/api/v1/auth/register", json={"email": email, "password": password, "full_name": "Test User"})
    assert r.status_code == 201, r.text
    r = c.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    tokens = r.json()
    return email, password, tokens["access_token"], tokens["refresh_token"]


def auth_headers(token: str):
    return {"Authorization": f"Bearer {token}"}


async def _insert_admin(email: str, password: str):
    async with _Session() as s:
        s.add(SuperAdmin(email=email, password_hash=hash_password(password), full_name="Admin"))
        await s.commit()


def admin_token(c: TestClient, email: str | None = None, password: str = "AdminPass123456"):
    email = email or unique_email("admin")
    run(_insert_admin(email, password))
    r = c.post("/api/v1/admin/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


async def _seed_rows(rows):
    async with _Session() as s:
        for row in rows:
            s.add(row)
        await s.commit()


def seed_rows(rows):
    run(_seed_rows(rows))


async def _get_user_by_email(email: str):
    from sqlalchemy import select
    async with _Session() as s:
        return (await s.execute(select(User).where(User.email == email))).scalar_one()


def get_user(email: str) -> User:
    return run(_get_user_by_email(email))


def make_closed_trade(user_id, symbol="BTCUSDT", side="LONG", entry=60000, qty="0.1",
                      exit_price=63000, pnl="300", status="closed"):
    now = datetime.now(timezone.utc)
    return Trade(user_id=user_id, symbol=symbol, side=side, status=status,
                 entry_price=Decimal(str(entry)), exit_price=Decimal(str(exit_price)),
                 quantity=Decimal(qty), leverage=2,
                 realized_pnl=Decimal(str(pnl)) if pnl is not None else None,
                 opened_at=now, closed_at=now if status == "closed" else None)


def make_signal(symbol="BTCUSDT", direction="LONG", entry=60000):
    return MarketSignal(symbol=symbol, direction=direction, timeframe="1h",
                        entry_price=Decimal(str(entry)),
                        stop_loss=Decimal(str(entry - 1000)),
                        take_profit=Decimal(str(entry + 2000)),
                        confidence_score=Decimal("0.8"), status="new")


def fixture_klines(n=250, moves=None, volume_base=100, volume_step=0):
    """Deterministic klines: moves is a list of per-bar close deltas."""
    if moves is None:
        moves = [30] * n
    rows = []
    price = 60000.0
    for i, d in enumerate(moves):
        o, c = price, price + d
        vol = volume_base + volume_step * i
        rows.append([i * 60000, str(o), str(max(o, c) + 20), str(min(o, c) - 20),
                     str(c), str(vol), i * 60000, "1", "10", "50", "1", "0"])
        price = c
    return rows


def v_shape_up_klines():
    # Long decline then sharp rally with rising volume -> LONG (4 rule conditions).
    return fixture_klines(moves=[-40] * 150 + [90] * 100, volume_base=50, volume_step=1)


def flat_klines():
    return fixture_klines(moves=[0] * 250)

"""Auto-execution loop tests: scanner signals -> trades, 24/7.
The Binance client is fully mocked — no real Binance call is ever made.
Covers: LONG executes for an enabled user with a live connection; WAIT is
skipped; the same signal never executes twice for one user; a paused user is
skipped; a user with no live connection is skipped; the live-trading guard
PermissionError is caught and the loop continues; a losing day does not stop
execution."""
from decimal import Decimal
from unittest.mock import patch

from sqlalchemy import select

from app.core.security import encrypt_secret
from app.models import BotSettings, ExchangeConnection, MarketSignal, SystemSetting, Trade
from app.worker.tasks import execute_new_signals
from tests.conftest import (
    get_user, make_closed_trade, make_signal, register_and_login, run, seed_rows,
)


class _FakeBinanceClient:
    """Mocked live Binance client: 10,000 USDT equity, fills every order."""
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def account_info(self):
        return {"totalWalletBalance": "10000",
                "assets": [{"asset": "USDT", "walletBalance": "10000"}]}

    async def exchange_info(self):
        return {"symbols": [{"symbol": "BTCUSDT", "filters": [
            {"filterType": "LOT_SIZE", "stepSize": "0.001", "minQty": "0.001"},
            {"filterType": "PRICE_FILTER", "tickSize": "0.01"},
            {"filterType": "MIN_NOTIONAL", "notional": "5"}]}]}

    async def place_order(self, *args, **kwargs):
        return {"orderId": 123, "status": "NEW", "executedQty": "0.05"}

    async def get_order(self, *args, **kwargs):
        return {"orderId": 123, "status": "FILLED",
                "executedQty": "0.05", "avgPrice": "60010"}

    async def positions(self):
        return []


def _enable_user(user_id, paused=False, trading=True, enabled=True):
    seed_rows([BotSettings(user_id=user_id, is_enabled=enabled,
                           trading_enabled=trading, is_paused=paused)])


def _live_connection(user_id, environment="live"):
    seed_rows([ExchangeConnection(
        user_id=user_id, environment=environment, is_active=True,
        api_key_encrypted=encrypt_secret("TESTAPIKEY12345678"),
        api_secret_encrypted=encrypt_secret("TESTAPISECRET12345678"),
        api_key_last4="5678")])


def _set_live_trading(value: str):
    """Idempotent upsert of the live_trading_enabled setting (its key is the
    primary key, so repeated inserts across tests would violate it)."""
    async def _go():
        from tests.conftest import _Session

        async with _Session() as s:
            row = (await s.execute(
                select(SystemSetting).where(
                    SystemSetting.key == "live_trading_enabled"))).scalar_one_or_none()
            if row is None:
                s.add(SystemSetting(key="live_trading_enabled", value=value,
                                    description="test activation"))
            else:
                row.value = value
            await s.commit()
    run(_go())


def _activate_live_trading():
    _set_live_trading("true")


def _deactivate_live_trading():
    _set_live_trading("false")


def _trades_for(user_id):
    from tests.conftest import _Session

    async def _q():
        async with _Session() as s:
            return (await s.execute(
                select(Trade).where(Trade.user_id == user_id))).scalars().all()
    return run(_q())


def _run_execute(signals):
    from tests.conftest import _Session

    async def _go():
        async with _Session() as s:
            return await execute_new_signals(s, signals)
    return run(_go())


def test_long_signal_executes_for_enabled_user_with_live_connection(client):
    email, _, tok, _ = register_and_login(client)
    user_id = get_user(email).id
    _activate_live_trading()
    _enable_user(user_id)
    _live_connection(user_id)
    sig = make_signal()
    seed_rows([sig])

    with patch("app.worker.tasks.BinanceClient", _FakeBinanceClient):
        counts = _run_execute([sig])

    # >= 1: other enabled users from earlier tests may also execute this signal.
    assert counts["executed"] >= 1
    trades = _trades_for(user_id)
    assert len(trades) == 1
    assert trades[0].signal_id == sig.id
    assert trades[0].side == "LONG"
    assert trades[0].status == "open"
    assert 10 <= trades[0].leverage <= 50
    assert trades[0].stop_loss == sig.stop_loss
    assert trades[0].take_profit == sig.take_profit


def test_same_signal_never_executes_twice_for_one_user(client):
    email, _, tok, _ = register_and_login(client)
    user_id = get_user(email).id
    _activate_live_trading()
    _enable_user(user_id)
    _live_connection(user_id)
    sig = make_signal()
    seed_rows([sig])

    with patch("app.worker.tasks.BinanceClient", _FakeBinanceClient):
        first = _run_execute([sig])
        second = _run_execute([sig])

    assert first["executed"] >= 1
    assert second["executed"] == 0
    assert second["skipped"] >= 1
    assert len(_trades_for(user_id)) == 1


def test_wait_signal_is_skipped(client):
    email, _, tok, _ = register_and_login(client)
    user_id = get_user(email).id
    _activate_live_trading()
    _enable_user(user_id)
    _live_connection(user_id)
    sig = make_signal(direction="WAIT")
    seed_rows([sig])

    with patch("app.worker.tasks.BinanceClient", _FakeBinanceClient):
        counts = _run_execute([sig])

    assert counts["executed"] == 0
    assert _trades_for(user_id) == []


def test_paused_user_is_skipped(client):
    email, _, tok, _ = register_and_login(client)
    user_id = get_user(email).id
    _activate_live_trading()
    _enable_user(user_id, paused=True)
    _live_connection(user_id)
    sig = make_signal()
    seed_rows([sig])

    with patch("app.worker.tasks.BinanceClient", _FakeBinanceClient):
        counts = _run_execute([sig])

    # The paused user is excluded from the auto-trading set entirely; other
    # enabled users from earlier tests may still execute this signal, so only
    # this user's trades are asserted.
    assert _trades_for(user_id) == []


def test_user_with_no_live_connection_is_skipped(client):
    email, _, tok, _ = register_and_login(client)
    user_id = get_user(email).id
    _activate_live_trading()
    _enable_user(user_id)
    # No ExchangeConnection row at all.
    sig = make_signal()
    seed_rows([sig])

    with patch("app.worker.tasks.BinanceClient", _FakeBinanceClient):
        counts = _run_execute([sig])

    # This user is skipped (no connection); other enabled users may execute.
    assert counts["skipped"] >= 1
    assert _trades_for(user_id) == []


def test_live_guard_refusal_is_caught_and_loop_continues(client):
    """Live trading NOT activated: the engine's guard raises PermissionError,
    the loop catches it per user, returns normally, and no trade is placed."""
    email, _, tok, _ = register_and_login(client)
    user_id = get_user(email).id
    # Explicitly deactivate: earlier tests in this session activated it, and
    # the shared test DB keeps that setting.
    _deactivate_live_trading()
    _enable_user(user_id)
    _live_connection(user_id)
    sig = make_signal()
    seed_rows([sig])

    with patch("app.worker.tasks.BinanceClient", _FakeBinanceClient):
        counts = _run_execute([sig])  # must not raise

    assert counts["failed"] >= 1
    assert counts["executed"] == 0
    assert _trades_for(user_id) == []


def test_executes_despite_losing_day(client):
    """A user who already lost 2.5% of equity today still gets the next trade:
    there is no daily-loss halt; the per-trade stop loss is the loss control."""
    email, _, tok, _ = register_and_login(client)
    user_id = get_user(email).id
    _activate_live_trading()
    _enable_user(user_id)
    _live_connection(user_id)
    seed_rows([make_closed_trade(user_id, pnl="-250")])
    sig = make_signal()
    seed_rows([sig])

    with patch("app.worker.tasks.BinanceClient", _FakeBinanceClient):
        counts = _run_execute([sig])

    assert counts["executed"] >= 1
    # Only the trade for THIS signal counts — the seeded closed losing trade
    # for this user is a separate row.
    signal_trades = [t for t in _trades_for(user_id) if t.signal_id == sig.id]
    assert len(signal_trades) == 1

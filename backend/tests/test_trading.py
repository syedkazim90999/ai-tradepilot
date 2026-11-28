"""Trading tests: signal generation on fixtures, position sizing, risk blocks,
duplicate-order prevention, SL/TP creation, partial fills."""
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from app.services.risk import check_trade_allowed, get_effective_settings
from app.services.signals import generate_signal, klines_to_df
from app.services.trading import TradingEngine, deterministic_client_order_id, round_to_step
from app.models import Order, Position, Trade
from tests.conftest import (
    auth_headers, fixture_klines, flat_klines, get_user, make_closed_trade,
    make_signal, register_and_login, run, seed_rows, v_shape_up_klines,
)


# --- signal generation ---
def test_signal_long_on_v_shape_fixture():
    sig = generate_signal("BTCUSDT", klines_to_df(v_shape_up_klines()))
    assert sig["direction"] == "LONG"
    assert sig["stop_loss"] < sig["entry_price"] < sig["take_profit"]  # 2:1 R:R
    assert len(sig["supporting_conditions"]) >= 4


def test_signal_wait_on_flat_fixture():
    sig = generate_signal("BTCUSDT", klines_to_df(flat_klines()))
    assert sig["direction"] == "WAIT"
    assert sig["supporting_conditions"] == []


def test_signal_wait_on_choppy_fixture():
    import random
    random.seed(1)
    moves = [random.choice([-20, 20]) for _ in range(250)]
    sig = generate_signal("BTCUSDT", klines_to_df(fixture_klines(moves=moves)))
    assert sig["direction"] == "WAIT"


def test_signal_short_branch_via_mocked_indicators():
    """The SHORT rule branch: with indicator alignment for a downtrend the
    engine must emit SHORT with SL above entry and TP below it. (A SHORT on
    raw klines is near-unreachable: RSI>65 cannot coexist with the sustained
    decline the other conditions need — see DEVELOPMENT_STATUS.)"""
    ind = {"close": 60000.0, "rsi_14": 80.0, "atr_14": 500.0, "support": 55000.0,
           "resistance": 62000.0, "trend_strength": -1.0, "macd_hist": -5.0,
           "vwap": 61000.0, "bb_upper": 59000.0, "bb_lower": 57000.0,
           "volume": {"volume_rising": False}}
    with patch("app.services.signals.compute_all", return_value=ind):
        sig = generate_signal("BTCUSDT", klines_to_df(flat_klines()))
    assert sig["direction"] == "SHORT"
    assert sig["take_profit"] < sig["entry_price"] < sig["stop_loss"]
    assert len(sig["supporting_conditions"]) >= 4


def test_signal_long_branch_via_mocked_indicators():
    ind = {"close": 60000.0, "rsi_14": 30.0, "atr_14": 500.0, "support": 55000.0,
           "resistance": 62000.0, "trend_strength": 1.0, "macd_hist": 5.0,
           "vwap": 59000.0, "bb_upper": 63000.0, "bb_lower": 61000.0,
           "volume": {"volume_rising": True}}
    with patch("app.services.signals.compute_all", return_value=ind):
        sig = generate_signal("BTCUSDT", klines_to_df(flat_klines()))
    assert sig["direction"] == "LONG"


# --- position sizing / risk ---
async def _risk_setup(email):
    from tests.conftest import _Session
    async with _Session() as s:
        from sqlalchemy import select
        from app.models import User
        user = (await s.execute(select(User).where(User.email == email))).scalar_one()
        return user.id


def test_position_sizing_math(client):
    email, _, tok, _ = register_and_login(client)
    user_id = get_user(email).id

    async def _check():
        from tests.conftest import _Session
        async with _Session() as s:
            # equity 10000, risk 0.5% = 50; stop distance 1000 -> size 0.05
            d = await check_trade_allowed(s, user_id, "BTCUSDT", Decimal("10000"),
                                          Decimal("60000"), Decimal("59000"), 2)
            return d
    d = run(_check())
    assert d.allowed is True
    assert d.position_size == Decimal("0.05")


def test_position_size_capped_by_leverage(client):
    email, _, tok, _ = register_and_login(client)
    user_id = get_user(email).id

    async def _check():
        from tests.conftest import _Session
        async with _Session() as s:
            # Tiny stop distance would imply huge size; notional capped at equity*lev.
            d = await check_trade_allowed(s, user_id, "BTCUSDT", Decimal("1000"),
                                          Decimal("60000"), Decimal("59990"), 2)
            return d
    d = run(_check())
    assert d.allowed is True
    assert d.position_size * Decimal("60000") <= Decimal("2000")


def test_daily_loss_no_longer_blocks(client):
    """No daily-loss halt by design: even after losing 2.5% of equity today,
    the next trade is still allowed. The per-trade stop loss is the loss
    control, and the bot keeps trading through losing days."""
    email, _, tok, _ = register_and_login(client)
    user_id = get_user(email).id
    # Lose 2.5% of 10000 = 250 today — over the old 2% daily limit.
    seed_rows([make_closed_trade(user_id, pnl="-250")])

    async def _check():
        from tests.conftest import _Session
        async with _Session() as s:
            return await check_trade_allowed(s, user_id, "BTCUSDT", Decimal("10000"),
                                             Decimal("60000"), Decimal("59000"), 2)
    d = run(_check())
    assert d.allowed is True
    assert d.position_size == Decimal("0.05")


def test_daily_loss_below_limit_allows(client):
    email, _, tok, _ = register_and_login(client)
    user_id = get_user(email).id
    seed_rows([make_closed_trade(user_id, pnl="-50")])

    async def _check():
        from tests.conftest import _Session
        async with _Session() as s:
            return await check_trade_allowed(s, user_id, "BTCUSDT", Decimal("10000"),
                                             Decimal("60000"), Decimal("59000"), 2)
    assert run(_check()).allowed is True


def test_max_positions_block(client):
    email, _, tok, _ = register_and_login(client)
    user_id = get_user(email).id
    # Default max is 5 positions — 5 open positions must block the next one.
    seed_rows([
        Position(user_id=user_id, symbol="BTCUSDT", side="LONG", quantity=Decimal("0.1"),
                 entry_price=Decimal("60000")),
        Position(user_id=user_id, symbol="ETHUSDT", side="LONG", quantity=Decimal("1"),
                 entry_price=Decimal("3000")),
        Position(user_id=user_id, symbol="BNBUSDT", side="LONG", quantity=Decimal("1"),
                 entry_price=Decimal("600")),
        Position(user_id=user_id, symbol="SOLUSDT", side="LONG", quantity=Decimal("1"),
                 entry_price=Decimal("150")),
        Position(user_id=user_id, symbol="XRPUSDT", side="LONG", quantity=Decimal("10"),
                 entry_price=Decimal("2")),
    ])

    async def _check():
        from tests.conftest import _Session
        async with _Session() as s:
            return await check_trade_allowed(s, user_id, "BTCUSDT", Decimal("10000"),
                                             Decimal("60000"), Decimal("59000"), 2)
    d = run(_check())
    assert d.allowed is False
    assert "Max positions" in d.reason


def test_leverage_over_max_blocked(client):
    email, _, tok, _ = register_and_login(client)
    user_id = get_user(email).id

    async def _check():
        from tests.conftest import _Session
        async with _Session() as s:
            # 60x is above the absolute 50x cap, so it must be blocked.
            return await check_trade_allowed(s, user_id, "BTCUSDT", Decimal("10000"),
                                             Decimal("60000"), Decimal("59000"), 60)
    d = run(_check())
    assert d.allowed is False
    assert "Leverage" in d.reason


def test_leverage_clamped_to_10_50_range(client):
    """Legacy 2x settings clamp up to 10x; requests above 50x stay blocked."""
    email, _, tok, _ = register_and_login(client)
    user_id = get_user(email).id
    mock = _mock_client()

    async def _legacy(s):
        from app.services.risk import get_effective_settings
        # Creates the settings row (default 20x), then simulate a pre-change row.
        settings = await get_effective_settings(s, user_id)
        settings.max_leverage = 2
        await s.commit()
        # 10x (the clamped floor) must be allowed, not blocked by the stale 2x.
        d = await check_trade_allowed(s, user_id, "BTCUSDT", Decimal("10000"),
                                      Decimal("60000"), Decimal("59000"), 10)
        assert d.allowed is True
        # Executing a signal stores the trade at 10x, not 2x.
        eng = TradingEngine(s, mock, user_id)
        sig = make_signal()
        s.add(sig)
        await s.commit()
        trade = await eng.execute_signal(sig, Decimal("10000"))
        assert trade is not None
        assert trade.leverage == 10
        # A 60x request is still blocked (above the 50x cap).
        d2 = await check_trade_allowed(s, user_id, "BTCUSDT", Decimal("10000"),
                                       Decimal("60000"), Decimal("59000"), 60)
        assert d2.allowed is False
    run(_run_engine(_legacy, user_id))


# --- trading engine (mocked exchange) ---
def _mock_client():
    client = AsyncMock()
    client.exchange_info.return_value = {"symbols": [{"symbol": "BTCUSDT", "filters": [
        {"filterType": "LOT_SIZE", "stepSize": "0.001", "minQty": "0.001"},
        {"filterType": "PRICE_FILTER", "tickSize": "0.01"},
        {"filterType": "MIN_NOTIONAL", "notional": "5"}]}]}
    client.place_order.return_value = {"orderId": 123, "status": "NEW", "executedQty": "0.05"}
    client.get_order.return_value = {"orderId": 123, "status": "FILLED",
                                     "executedQty": "0.05", "avgPrice": "60010"}
    client.positions.return_value = []
    return client


async def _run_engine(coro_fn, user_id):
    from tests.conftest import _Session
    async with _Session() as s:
        return await coro_fn(s)


def test_duplicate_order_prevention(client):
    email, _, tok, _ = register_and_login(client)
    user_id = get_user(email).id
    mock = _mock_client()

    async def _place_twice(s):
        eng = TradingEngine(s, mock, user_id)
        sig = make_signal()
        s.add(sig)
        await s.commit()
        o1 = await eng.place_order("BTCUSDT", "BUY", "MARKET", Decimal("0.05"), signal_id=sig.id)
        o2 = await eng.place_order("BTCUSDT", "BUY", "MARKET", Decimal("0.05"), signal_id=sig.id)
        return o1, o2, mock.place_order.call_count
    o1, o2, calls = run(_run_engine(lambda s: _place_twice(s), user_id))
    assert o1.id == o2.id
    assert o1.client_order_id == o2.client_order_id
    assert calls == 1  # exchange hit only once


def test_deterministic_client_order_id_stable():
    a = deterministic_client_order_id("u1", "s1", "BTCUSDT", "BUY", "MARKET")
    b = deterministic_client_order_id("u1", "s1", "BTCUSDT", "BUY", "MARKET")
    c = deterministic_client_order_id("u1", "s2", "BTCUSDT", "BUY", "MARKET")
    assert a == b and a != c and a.startswith("TP-")


def test_execute_signal_creates_sl_and_tp_orders(client):
    email, _, tok, _ = register_and_login(client)
    user_id = get_user(email).id
    mock = _mock_client()

    async def _exec(s):
        eng = TradingEngine(s, mock, user_id)
        sig = make_signal()
        s.add(sig)
        await s.commit()
        trade = await eng.execute_signal(sig, Decimal("10000"))
        from sqlalchemy import select
        orders = (await s.execute(select(Order).where(Order.user_id == user_id))).scalars().all()
        return trade, orders
    trade, orders = run(_run_engine(_exec, user_id))
    assert trade is not None
    assert trade.status == "open"
    types = sorted(o.order_type for o in orders)
    assert types == ["MARKET", "STOP_MARKET", "TAKE_PROFIT_MARKET"]
    sl = [o for o in orders if o.order_type == "STOP_MARKET"][0]
    tp = [o for o in orders if o.order_type == "TAKE_PROFIT_MARKET"][0]
    assert sl.reduce_only is True and tp.reduce_only is True


def test_execute_wait_signal_does_nothing(client):
    email, _, tok, _ = register_and_login(client)
    user_id = get_user(email).id
    mock = _mock_client()

    async def _exec(s):
        eng = TradingEngine(s, mock, user_id)
        sig = make_signal(direction="WAIT")
        s.add(sig)
        await s.commit()
        return await eng.execute_signal(sig, Decimal("10000"))
    assert run(_run_engine(_exec, user_id)) is None
    assert mock.place_order.call_count == 0


def test_partial_fill_handling(client):
    email, _, tok, _ = register_and_login(client)
    user_id = get_user(email).id
    mock = _mock_client()
    mock.get_order.return_value = {"orderId": 123, "status": "PARTIALLY_FILLED",
                                   "executedQty": "0.025", "avgPrice": "60005"}

    async def _place(s):
        eng = TradingEngine(s, mock, user_id)
        sig = make_signal()
        s.add(sig)
        await s.commit()
        return await eng.place_order("BTCUSDT", "BUY", "MARKET", Decimal("0.05"), signal_id=sig.id)
    order = run(_run_engine(_place, user_id))
    assert order.status == "PARTIALLY_FILLED"
    assert order.executed_qty == Decimal("0.025")
    assert order.avg_price == Decimal("60005")


def test_reconcile_mismatch_local_open_exchange_closed(client):
    email, _, tok, _ = register_and_login(client)
    user_id = get_user(email).id
    seed_rows([Position(user_id=user_id, symbol="BTCUSDT", side="LONG",
                        quantity=Decimal("0.1"), entry_price=Decimal("60000"))])
    mock = _mock_client()  # positions() -> []

    async def _rec(s):
        eng = TradingEngine(s, mock, user_id)
        return await eng.reconcile_positions()
    mismatches = run(_run_engine(_rec, user_id))
    assert len(mismatches) == 1
    assert mismatches[0]["issue"] == "local open, exchange closed"


def test_round_to_step():
    assert round_to_step(Decimal("0.051234"), Decimal("0.001")) == Decimal("0.051")
    assert round_to_step(Decimal("10"), Decimal("0")) == Decimal("10")

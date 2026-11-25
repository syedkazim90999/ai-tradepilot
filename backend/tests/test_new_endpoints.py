"""Tests for the gap-closure endpoints (A): contact, enriched dashboards,
admin signals + strategy performance."""
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from tests.conftest import (
    admin_token, auth_headers, get_user, make_closed_trade, make_signal,
    register_and_login, seed_rows,
)


@pytest.fixture(autouse=True)
def _wipe_db():
    """Admin aggregates are platform-wide, so each test in this module starts
    from an empty scratch DB (other modules use per-user assertions)."""
    from app.db.base import Base
    from tests.conftest import _Session, run

    async def _w():
        async with _Session() as s:
            for table in reversed(Base.metadata.sorted_tables):
                await s.execute(table.delete())
            await s.commit()
    run(_w())
    yield


def test_contact_post_201_and_stored(client):
    r = client.post("/api/v1/contact", json={
        "name": "Visitor", "email": "visitor@example.com",
        "message": "Hello, I have a question about pricing."})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["name"] == "Visitor" and body["email"] == "visitor@example.com"
    assert "id" in body and "created_at" in body


def test_contact_validation(client):
    assert client.post("/api/v1/contact", json={
        "name": "V", "email": "not-an-email", "message": "hi"}).status_code == 422
    assert client.post("/api/v1/contact", json={
        "name": "V", "email": "v@example.com", "message": ""}).status_code == 422


def test_dashboard_overview_enriched_values(client):
    email, _, tok, _ = register_and_login(client)
    user = get_user(email)
    # 3 closed trades: +300, +100, -200. Volume uses exit price.
    seed_rows([
        make_closed_trade(user.id, entry=60000, qty="0.1", exit_price=63000, pnl="300"),
        make_closed_trade(user.id, symbol="ETHUSDT", entry=3000, qty="1", exit_price=3100, pnl="100"),
        make_closed_trade(user.id, symbol="SOLUSDT", entry=150, qty="2", exit_price=140, pnl="-200"),
    ])
    r = client.get("/api/v1/dashboard/overview", headers=auth_headers(tok))
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["total_trades"] == 3
    assert float(b["total_realized_pnl"]) == 200.0
    assert b["closed_trades"] == 3
    # volume = 0.1*63000 + 1*3100 + 2*140 = 6300+3100+280 = 9680
    assert b["trading_volume"] == 9680.0
    assert abs(b["win_rate"] - 2 / 3) < 1e-9
    # equity curve: 300 -> 400 -> 200; peak 400, max drawdown 200
    assert b["max_drawdown"] == 200.0
    # No Binance connection -> balance is null, never invented.
    assert b["available_balance"] is None
    assert b["available_balance_status"] == "no_binance_connection"


def test_dashboard_overview_empty_user_zeros_not_estimates(client):
    _, _, tok, _ = register_and_login(client)
    b = client.get("/api/v1/dashboard/overview", headers=auth_headers(tok)).json()
    assert b["closed_trades"] == 0
    assert b["trading_volume"] == 0
    assert b["win_rate"] is None
    assert b["max_drawdown"] == 0
    assert b["available_balance"] is None


def test_dashboard_balance_from_connected_account_mocked(client):
    email, _, tok, _ = register_and_login(client)
    r = client.post("/api/v1/connections", headers=auth_headers(tok),
                    json={"api_key": "ABCDEFGH1234", "api_secret": "SECRET12345678",
                          "environment": "testnet"})
    assert r.status_code == 201, r.text
    with patch("app.services.binance_client.BinanceClient") as MockClient:
        inst = MockClient.return_value.__aenter__.return_value
        inst.balances = AsyncMock(return_value=[
            {"asset": "USDT", "availableBalance": "1234.56", "walletBalance": "1500.00"},
            {"asset": "BTC", "availableBalance": "0.01", "walletBalance": "0.01"}])
        b = client.get("/api/v1/dashboard/overview", headers=auth_headers(tok)).json()
    assert b["available_balance"] == 1234.56
    assert b["available_balance_status"] == "ok"


def test_dashboard_balance_fetch_failure_returns_null(client):
    email, _, tok, _ = register_and_login(client)
    client.post("/api/v1/connections", headers=auth_headers(tok),
                json={"api_key": "ABCDEFGH1234", "api_secret": "SECRET12345678",
                      "environment": "testnet"})
    with patch("app.services.binance_client.BinanceClient") as MockClient:
        inst = MockClient.return_value.__aenter__.return_value
        inst.balances = AsyncMock(side_effect=Exception("exchange down"))
        b = client.get("/api/v1/dashboard/overview", headers=auth_headers(tok)).json()
    assert b["available_balance"] is None
    assert b["available_balance_status"] == "fetch_failed"


def test_admin_overview_enriched(client):
    email, _, tok, _ = register_and_login(client)
    user = get_user(email)
    adm = admin_token(client)
    seed_rows([make_closed_trade(user.id, entry=60000, qty="0.1", exit_price=63000, pnl="300")])
    client.post("/api/v1/connections", headers=auth_headers(tok),
                json={"api_key": "ABCDEFGH1234", "api_secret": "SECRET12345678", "environment": "testnet"})
    b = client.get("/api/v1/admin/overview", headers=auth_headers(adm)).json()
    assert b["total_users"] >= 1
    assert b["suspended_users"] == 0
    assert b["connected_binance_accounts"] == 1
    assert b["total_trading_volume"] == 6300.0
    assert b["aggregate_realized_pnl"] == 300.0
    # Suspend the user and the count moves.
    client.post(f"/api/v1/admin/users/{user.id}/suspend", headers=auth_headers(adm))
    b = client.get("/api/v1/admin/overview", headers=auth_headers(adm)).json()
    assert b["suspended_users"] == 1


def test_admin_signals_filters_and_pagination(client):
    adm = admin_token(client)
    seed_rows([
        make_signal("BTCUSDT", "LONG"), make_signal("BTCUSDT", "SHORT"),
        make_signal("ETHUSDT", "LONG"), make_signal("BTCUSDT", "WAIT"),
    ])
    base = "/api/v1/admin/signals"
    all_rows = client.get(base, headers=auth_headers(adm)).json()
    assert all_rows["total"] == 4
    btc = client.get(f"{base}?symbol=BTCUSDT", headers=auth_headers(adm)).json()
    assert btc["total"] == 3
    longs = client.get(f"{base}?direction=LONG", headers=auth_headers(adm)).json()
    assert longs["total"] == 2
    page = client.get(f"{base}?limit=2&offset=2", headers=auth_headers(adm)).json()
    assert page["total"] == 4 and len(page["signals"]) == 2
    assert client.get(base, headers=auth_headers(adm)).json()["signals"][0]["symbol"] in ("BTCUSDT", "ETHUSDT")


def test_admin_strategies_performance_empty_is_zeros(client):
    adm = admin_token(client)
    b = client.get("/api/v1/admin/strategies/performance", headers=auth_headers(adm)).json()
    assert b["total_signals"] == 0
    assert b["signals_by_direction"] == {"LONG": 0, "SHORT": 0, "WAIT": 0}
    assert b["win_rate"] is None
    assert b["realized_pnl"] == 0
    assert b["strategies"] == []


def test_admin_strategies_performance_from_real_data(client):
    email, _, tok, _ = register_and_login(client)
    user = get_user(email)
    adm = admin_token(client)
    sig_long = make_signal("BTCUSDT", "LONG")
    sig_short = make_signal("BTCUSDT", "SHORT")
    seed_rows([sig_long, sig_short])
    from app.models import Trade
    seed_rows([
        Trade(user_id=user.id, signal_id=sig_long.id, symbol="BTCUSDT", side="LONG",
              status="closed", entry_price=Decimal("60000"), exit_price=Decimal("63000"),
              quantity=Decimal("0.1"), realized_pnl=Decimal("300")),
        Trade(user_id=user.id, signal_id=sig_short.id, symbol="BTCUSDT", side="SHORT",
              status="closed", entry_price=Decimal("60000"), exit_price=Decimal("61000"),
              quantity=Decimal("0.1"), realized_pnl=Decimal("-100")),
    ])
    b = client.get("/api/v1/admin/strategies/performance", headers=auth_headers(adm)).json()
    assert b["total_signals"] == 2
    assert b["signals_by_direction"] == {"LONG": 1, "SHORT": 1, "WAIT": 0}
    assert b["closed_trades"] == 2
    assert b["win_rate"] == 0.5
    assert b["realized_pnl"] == 200.0
    unassigned = [s for s in b["strategies"] if s["name"] == "unassigned (scanner)"]
    assert len(unassigned) == 1
    assert unassigned[0]["total_signals"] == 2
    assert unassigned[0]["win_rate"] == 0.5

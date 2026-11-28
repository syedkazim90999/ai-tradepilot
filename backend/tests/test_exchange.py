"""Exchange tests — mocked Binance responses only, never real credentials:
public klines, 429/418 backoff, websocket reconnect, reconciliation."""
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.binance_client import BinanceClient, BinanceError
from app.services.trading import TradingEngine
from app.models import Position
from decimal import Decimal
from tests.conftest import auth_headers, get_user, register_and_login, run, seed_rows


KLINES_FIXTURE = [[1700000000000, "60000", "60100", "59900", "60050", "12.5",
                   1700003599999, "750000", 100, "6", "375000", "0"]]


def test_klines_endpoint_uses_public_klines(client):
    _, _, tok, _ = register_and_login(client)
    with patch("app.api.routes.market.BinanceClient") as MockClient:
        inst = MockClient.return_value.__aenter__.return_value
        inst.klines = AsyncMock(return_value=KLINES_FIXTURE)
        r = client.get("/api/v1/market/klines?symbol=BTCUSDT&interval=1h&limit=100",
                       headers=auth_headers(tok))
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body) == 1
    assert body[0]["open"] == "60000" and body[0]["close"] == "60050"
    assert body[0]["open_time"] == 1700000000000


def test_klines_caches_within_60s(client):
    _, _, tok, _ = register_and_login(client)
    with patch("app.api.routes.market.BinanceClient") as MockClient:
        inst = MockClient.return_value.__aenter__.return_value
        inst.klines = AsyncMock(return_value=KLINES_FIXTURE)
        assert client.get("/api/v1/market/klines?symbol=ETHUSDT&interval=15m&limit=10",
                          headers=auth_headers(tok)).status_code == 200
        assert client.get("/api/v1/market/klines?symbol=ETHUSDT&interval=15m&limit=10",
                          headers=auth_headers(tok)).status_code == 200
        assert inst.klines.call_count == 1  # second call served from cache


def test_klines_rejects_bad_interval_and_symbol(client):
    _, _, tok, _ = register_and_login(client)
    assert client.get("/api/v1/market/klines?interval=99x", headers=auth_headers(tok)).status_code == 400
    assert client.get("/api/v1/market/klines?symbol=BTC;DROP", headers=auth_headers(tok)).status_code == 400
    assert client.get("/api/v1/market/klines?limit=5000", headers=auth_headers(tok)).status_code == 422


def test_klines_binance_error_becomes_502(client):
    _, _, tok, _ = register_and_login(client)
    with patch("app.api.routes.market.BinanceClient") as MockClient:
        inst = MockClient.return_value.__aenter__.return_value
        inst.klines = AsyncMock(side_effect=BinanceError("bad symbol", code=-1121, status=400))
        r = client.get("/api/v1/market/klines?symbol=NOPEUSDT", headers=auth_headers(tok))
    assert r.status_code == 502


def test_klines_is_public_no_credentials_needed(client):
    """Public endpoint: no auth token, no Binance credentials required."""
    with patch("app.api.routes.market.BinanceClient") as MockClient:
        inst = MockClient.return_value.__aenter__.return_value
        inst.klines = AsyncMock(return_value=KLINES_FIXTURE)
        r = client.get("/api/v1/market/klines?symbol=SOLUSDT&interval=1h&limit=5")
    assert r.status_code == 200, r.text
    assert r.json()[0]["close"] == "60050"


async def test_binance_client_429_backoff_then_success():
    """429 with Retry-After is respected (sleep patched) and the request is retried."""
    client = BinanceClient(testnet=True)
    ok_resp = MagicMock(status_code=200)
    ok_resp.json.return_value = {"serverTime": 1700000000000}
    limited = MagicMock(status_code=429, headers={"Retry-After": "1"}, content=b"{}")
    limited.json.return_value = {}
    fake_http = AsyncMock()
    fake_http.request = AsyncMock(side_effect=[limited, ok_resp])
    client._client = fake_http
    with patch("app.services.binance_client.asyncio.sleep", new=AsyncMock()) as mock_sleep:
        data = await client._request("GET", "/fapi/v1/time")
    assert data == {"serverTime": 1700000000000}
    assert fake_http.request.call_count == 2
    assert mock_sleep.call_count >= 1
    await client.close()


async def test_binance_client_418_backoff_then_success():
    client = BinanceClient(testnet=True)
    ok_resp = MagicMock(status_code=200)
    ok_resp.json.return_value = [{"symbol": "BTCUSDT"}]
    banned = MagicMock(status_code=418, headers={}, content=b"{}")
    banned.json.return_value = {}
    fake_http = AsyncMock()
    fake_http.request = AsyncMock(side_effect=[banned, ok_resp])
    client._client = fake_http
    with patch("app.services.binance_client.asyncio.sleep", new=AsyncMock()):
        data = await client._request("GET", "/fapi/v1/exchangeInfo")
    assert data == [{"symbol": "BTCUSDT"}]
    await client.close()


async def test_binance_client_gives_up_after_retries():
    client = BinanceClient(testnet=True)
    fake_http = AsyncMock()
    fake_http.request = AsyncMock(side_effect=httpx.ConnectError("boom"))
    client._client = fake_http
    with patch("app.services.binance_client.asyncio.sleep", new=AsyncMock()):
        with pytest.raises(BinanceError):
            await client._request("GET", "/fapi/v1/ping", retries=2)
    assert fake_http.request.call_count == 2
    await client.close()


async def test_binance_client_4xx_raises_with_code():
    client = BinanceClient(testnet=True)
    err = MagicMock(status_code=400, content=b'{"code": -1121, "msg": "Invalid symbol."}')
    err.json.return_value = {"code": -1121, "msg": "Invalid symbol."}
    fake_http = AsyncMock()
    fake_http.request = AsyncMock(return_value=err)
    client._client = fake_http
    with pytest.raises(BinanceError) as exc:
        await client._request("GET", "/fapi/v1/klines", {"symbol": "NOPE"})
    assert exc.value.code == -1121
    await client.close()


async def test_websocket_reconnect_then_exhaustion():
    """stream() reconnects with backoff after a drop and raises after
    max_reconnects attempts are exhausted."""
    client = BinanceClient(testnet=True)
    received = []

    async def handler(msg):
        received.append(msg)

    class FakeWS:
        def __init__(self, msgs):
            self._msgs = msgs
        async def __aenter__(self):
            return self
        async def __aexit__(self, *exc):
            return False
        def __aiter__(self):
            return self
        async def __anext__(self):
            if self._msgs:
                return json.dumps(self._msgs.pop(0))
            raise StopAsyncIteration

    calls = {"n": 0}

    def fake_connect(*a, **k):
        calls["n"] += 1
        if calls["n"] == 1:
            return FakeWS([{"e": "trade", "s": "BTCUSDT"}])
        raise ConnectionError("drop")

    with patch("app.services.binance_client.websockets.connect", side_effect=fake_connect), \
         patch("app.services.binance_client.asyncio.sleep", new=AsyncMock()):
        with pytest.raises(BinanceError, match="exhausted reconnect"):
            await client.stream(["btcusdt@trade"], handler, max_reconnects=2)
    assert received == [{"e": "trade", "s": "BTCUSDT"}]
    assert calls["n"] == 2


def test_reconcile_quantity_mismatch_detected(client):
    email, _, tok, _ = register_and_login(client)
    user_id = get_user(email).id
    seed_rows([Position(user_id=user_id, symbol="BTCUSDT", side="LONG",
                        quantity=Decimal("0.1"), entry_price=Decimal("60000"))])
    mock = AsyncMock()
    mock.positions.return_value = [{"symbol": "BTCUSDT", "positionAmt": "-0.05"}]

    async def _rec(s):
        return await TradingEngine(s, mock, user_id).reconcile_positions()
    from tests.conftest import _Session
    async def _run():
        async with _Session() as s:
            return await _rec(s)
    mismatches = run(_run())
    assert len(mismatches) == 1
    assert mismatches[0]["issue"] == "quantity/side mismatch"

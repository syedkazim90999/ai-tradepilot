"""Binance Futures client (httpx + websockets).
Live production is the default. Live orders are still gated: they require
live_trading_enabled to be explicitly activated by the Super Admin
(see services/trading.py guard). Testnet is not offered.
Public endpoints need no credentials. Private endpoints use HMAC-SHA256 signing.
"""
import asyncio
import hashlib
import hmac
import json
import os
import time
from typing import Any, Optional
from urllib.parse import urlencode

import httpx
import websockets

from app.core.config import get_settings

DEFAULT_RECV_WINDOW = 5000


def _proxy_url() -> str | None:
    """Normalize the egress proxy env var: this VM sets a bare host:port
    (no scheme), which httpx rejects. Prepend http:// when missing.
    The value is never logged."""
    raw = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy") or ""
    if not raw:
        return None
    if raw.startswith(("http://", "https://")):
        return raw
    return "http://" + raw


class BinanceError(Exception):
    def __init__(self, message: str, code: int | None = None, status: int | None = None):
        super().__init__(message)
        self.code = code
        self.status = status


class BinanceClient:
    def __init__(self, api_key: str = "", api_secret: str = "", testnet: bool = False):
        s = get_settings()
        self.testnet = testnet
        self.base_url = s.binance_testnet_base_url if testnet else s.binance_prod_base_url
        self.ws_url = s.binance_testnet_ws_url if testnet else s.binance_prod_ws_url
        self.api_key = api_key
        self.api_secret = api_secret
        self._client: httpx.AsyncClient | None = None
        self._time_offset_ms = 0

    async def __aenter__(self):
        await self._ensure_client()
        return self

    async def __aexit__(self, *exc):
        await self.close()

    async def _ensure_client(self):
        if self._client is None:
            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=30.0,
                                             proxy=_proxy_url())

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    # --- signing ---
    def _sign(self, params: dict) -> dict:
        params = dict(params)
        params["timestamp"] = int(time.time() * 1000) + self._time_offset_ms
        params["recvWindow"] = DEFAULT_RECV_WINDOW
        query = urlencode(params)
        params["signature"] = hmac.new(
            self.api_secret.encode(), query.encode(), hashlib.sha256
        ).hexdigest()
        return params

    async def _request(self, method: str, path: str, params: dict | None = None,
                       signed: bool = False, retries: int = 3) -> Any:
        await self._ensure_client()
        params = params or {}
        headers = {}
        if signed:
            if not self.api_key or not self.api_secret:
                raise BinanceError("API credentials required for signed endpoint")
            params = self._sign(params)
            headers["X-MBX-APIKEY"] = self.api_key
        last_exc: Exception | None = None
        for attempt in range(retries):
            try:
                resp = await self._client.request(method, path, params=params, headers=headers)
            except httpx.RequestError as exc:
                last_exc = exc
                await asyncio.sleep(2 ** attempt)
                continue
            if resp.status_code in (429, 418):
                # Rate limited — respect Retry-After / back off exponentially.
                wait = int(resp.headers.get("Retry-After", 2 ** attempt * 5))
                await asyncio.sleep(wait)
                last_exc = BinanceError("Rate limited", status=resp.status_code)
                continue
            if resp.status_code >= 400:
                body = resp.json() if resp.content else {}
                raise BinanceError(body.get("msg", f"HTTP {resp.status_code}"),
                                   code=body.get("code"), status=resp.status_code)
            return resp.json()
        raise BinanceError(f"Request failed after {retries} retries: {last_exc}")

    async def sync_time(self):
        data = await self._request("GET", "/fapi/v1/time")
        server_ms = data["serverTime"]
        self._time_offset_ms = server_ms - int(time.time() * 1000)
        return self._time_offset_ms

    # --- public endpoints (no credentials) ---
    async def exchange_info(self) -> dict:
        return await self._request("GET", "/fapi/v1/exchangeInfo")

    async def klines(self, symbol: str, interval: str = "1h", limit: int = 200) -> list:
        return await self._request("GET", "/fapi/v1/klines",
                                   {"symbol": symbol, "interval": interval, "limit": limit})

    async def ticker_24hr(self, symbol: str | None = None) -> Any:
        params = {"symbol": symbol} if symbol else {}
        return await self._request("GET", "/fapi/v1/ticker/24hr", params)

    async def mark_price(self, symbol: str | None = None) -> Any:
        params = {"symbol": symbol} if symbol else {}
        return await self._request("GET", "/fapi/v1/premiumIndex", params)

    async def funding_rate(self, symbol: str, limit: int = 1) -> Any:
        return await self._request("GET", "/fapi/v1/fundingRate", {"symbol": symbol, "limit": limit})

    # --- private endpoints ---
    async def account_info(self) -> dict:
        return await self._request("GET", "/fapi/v2/account", signed=True)

    async def balances(self) -> list:
        info = await self.account_info()
        return info.get("assets", [])

    async def positions(self) -> list:
        info = await self.account_info()
        return [p for p in info.get("positions", []) if float(p.get("positionAmt", 0)) != 0]

    async def place_order(self, symbol: str, side: str, order_type: str, quantity: float,
                          price: float | None = None, stop_price: float | None = None,
                          client_order_id: str | None = None, reduce_only: bool = False,
                          time_in_force: str = "GTC") -> dict:
        params: dict[str, Any] = {
            "symbol": symbol, "side": side, "type": order_type, "quantity": quantity,
        }
        if price is not None:
            params["price"] = price
        if stop_price is not None:
            params["stopPrice"] = stop_price
        if client_order_id:
            params["newClientOrderId"] = client_order_id
        if reduce_only:
            params["reduceOnly"] = "true"
        if order_type in ("LIMIT", "STOP", "TAKE_PROFIT"):
            params["timeInForce"] = time_in_force
        return await self._request("POST", "/fapi/v1/order", params, signed=True)

    async def cancel_order(self, symbol: str, order_id: int | None = None,
                           orig_client_order_id: str | None = None) -> dict:
        params: dict[str, Any] = {"symbol": symbol}
        if order_id:
            params["orderId"] = order_id
        if orig_client_order_id:
            params["origClientOrderId"] = orig_client_order_id
        return await self._request("DELETE", "/fapi/v1/order", params, signed=True)

    async def get_order(self, symbol: str, order_id: int | None = None,
                        orig_client_order_id: str | None = None) -> dict:
        params: dict[str, Any] = {"symbol": symbol}
        if order_id:
            params["orderId"] = order_id
        if orig_client_order_id:
            params["origClientOrderId"] = orig_client_order_id
        return await self._request("GET", "/fapi/v1/order", params, signed=True)

    async def create_listen_key(self) -> str:
        data = await self._request("POST", "/fapi/v1/listenKey", signed=False)
        return data["listenKey"]

    async def keepalive_listen_key(self, listen_key: str):
        await self._ensure_client()
        await self._client.put("/fapi/v1/listenKey", params={"listenKey": listen_key},
                               headers={"X-MBX-APIKEY": self.api_key})

    # --- websockets with reconnection ---
    async def stream(self, stream_names: list[str], handler, max_reconnects: int = 10):
        """Subscribe to combined market streams, auto-reconnect with backoff."""
        url = f"{self.ws_url}/stream?streams={'/'.join(stream_names)}"
        delay = 1.0
        for attempt in range(max_reconnects):
            try:
                async with websockets.connect(url, ping_interval=20, ping_timeout=20,
                                             proxy=_proxy_url()) as ws:
                    delay = 1.0
                    async for msg in ws:
                        await handler(json.loads(msg))
            except Exception:
                await asyncio.sleep(delay)
                delay = min(delay * 2, 60)
        raise BinanceError("Websocket stream exhausted reconnect attempts")

    async def user_data_stream(self, listen_key: str, handler, max_reconnects: int = 10):
        url = f"{self.ws_url}/ws/{listen_key}"
        delay = 1.0
        for attempt in range(max_reconnects):
            try:
                async with websockets.connect(url, ping_interval=20, ping_timeout=20,
                                             proxy=_proxy_url()) as ws:
                    delay = 1.0
                    async for msg in ws:
                        await handler(json.loads(msg))
            except Exception:
                await asyncio.sleep(delay)
                delay = min(delay * 2, 60)
        raise BinanceError("User data stream exhausted reconnect attempts")

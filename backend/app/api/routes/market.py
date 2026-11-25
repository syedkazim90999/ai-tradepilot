"""Public market data: Binance Testnet klines proxy (no credentials needed).
Brief in-memory cache (60s per symbol/interval/limit) to avoid hammering
the public API. Returns raw Binance kline arrays reshaped into objects.
"""
import time

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.config import get_settings
from app.services.binance_client import BinanceClient, BinanceError

router = APIRouter(prefix="/market", tags=["market"])

ALLOWED_INTERVALS = {"1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1M"}
CACHE_TTL_S = 60.0
_cache: dict[tuple, tuple[float, list]] = {}


class Kline(BaseModel):
    open_time: int
    open: str
    high: str
    low: str
    close: str
    volume: str
    close_time: int


@router.get("/klines", response_model=list[Kline])
async def get_klines(symbol: str = Query(default="BTCUSDT", min_length=3, max_length=20),
                     interval: str = Query(default="1h"),
                     limit: int = Query(default=100, ge=1, le=1000)):
    symbol = symbol.upper().strip()
    if not symbol.isalnum():
        raise HTTPException(status_code=400, detail="Invalid symbol")
    if interval not in ALLOWED_INTERVALS:
        raise HTTPException(status_code=400, detail=f"Invalid interval; allowed: {sorted(ALLOWED_INTERVALS)}")
    key = (symbol, interval, limit)
    now = time.monotonic()
    hit = _cache.get(key)
    if hit and now - hit[0] < CACHE_TTL_S:
        return hit[1]
    try:
        async with BinanceClient(testnet=get_settings().binance_use_testnet) as client:
            raw = await client.klines(symbol, interval, limit)
    except BinanceError as exc:
        raise HTTPException(status_code=502, detail=f"Binance klines unavailable: {exc}")
    out = [Kline(open_time=int(r[0]), open=str(r[1]), high=str(r[2]), low=str(r[3]),
                 close=str(r[4]), volume=str(r[5]), close_time=int(r[6])) for r in raw]
    _cache[key] = (now, out)
    return out

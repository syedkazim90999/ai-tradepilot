"""Market scanner: fetch eligible USDT-M perpetuals, filter, multi-timeframe analysis."""
import asyncio

import pandas as pd

from app.core.config import get_settings
from app.models import MarketSignal
from app.services.binance_client import BinanceClient
from app.services.signals import generate_signal, klines_to_df

MIN_QUOTE_VOLUME_24H = 10_000_000  # USDT
TIMEFRAMES = ["5m", "15m", "1h", "4h"]
DEFAULT_SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"]


async def eligible_symbols(client: BinanceClient, min_quote_volume: float = MIN_QUOTE_VOLUME_24H) -> list[str]:
    info = await client.exchange_info()
    tickers = await client.ticker_24hr()
    volume_map = {t["symbol"]: float(t["quoteVolume"]) for t in tickers}
    eligible = []
    for s in info.get("symbols", []):
        if s.get("contractType") != "PERPETUAL":
            continue
        if s.get("quoteAsset") != "USDT" or s.get("status") != "TRADING":
            continue
        if volume_map.get(s["symbol"], 0) < min_quote_volume:
            continue
        eligible.append(s["symbol"])
    return eligible


def _spread_ok(ticker: dict, max_spread_pct: float = 0.001) -> bool:
    try:
        bid, ask = float(ticker["bidPrice"]), float(ticker["askPrice"])
        mid = (bid + ask) / 2
        return (ask - bid) / mid <= max_spread_pct if mid else False
    except (KeyError, ValueError, ZeroDivisionError):
        return False


async def scan_symbol(client: BinanceClient, symbol: str) -> list[dict]:
    """Multi-timeframe analysis for one symbol; returns one signal dict per timeframe."""
    signals = []
    for tf in TIMEFRAMES:
        try:
            klines = await client.klines(symbol, tf, limit=250)
        except Exception:
            continue
        if len(klines) < 210:
            continue
        df = klines_to_df(klines)
        signals.append(generate_signal(symbol, df, timeframe=tf))
    return signals


async def run_scan(symbols: list[str] | None = None, db=None, client: BinanceClient | None = None) -> list[dict]:
    """Run the scanner. If db is given, persist signals to market_signals."""
    own_client = client is None
    client = client or BinanceClient(testnet=get_settings().binance_use_testnet)
    try:
        symbols = symbols or await eligible_symbols(client)
        symbols = symbols[:20]  # cap per scan run
        results: list[dict] = []
        for symbol in symbols:
            results.extend(await scan_symbol(client, symbol))
            await asyncio.sleep(0.1)
        if db is not None:
            for sig in results:
                db.add(MarketSignal(
                    symbol=sig["symbol"], direction=sig["direction"], timeframe=sig["timeframe"],
                    entry_price=sig["entry_price"], stop_loss=sig["stop_loss"],
                    take_profit=sig["take_profit"], confidence_score=sig["confidence_score"],
                    indicators=sig["indicators"], supporting_conditions=sig["supporting_conditions"],
                    invalidating_conditions=sig["invalidating_conditions"],
                    estimated_fee=sig["estimated_fee"], estimated_slippage=sig["estimated_slippage"],
                ))
            await db.commit()
        return results
    finally:
        if own_client:
            await client.close()

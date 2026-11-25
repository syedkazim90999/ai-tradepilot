"""Deterministic rule-based signal generation.
NO LLM ever places orders. A confidence score is a rule-agreement score,
NOT a probability of profit — it is labelled as such everywhere it is shown.
"""
from decimal import Decimal

import pandas as pd

from app.services.indicators import compute_all


def klines_to_df(klines: list) -> pd.DataFrame:
    cols = ["open_time", "open", "high", "low", "close", "volume", "close_time",
            "quote_volume", "trades", "taker_buy_base", "taker_buy_quote", "ignore"]
    df = pd.DataFrame(klines, columns=cols[: len(klines[0])] if klines else cols)
    for c in ["open", "high", "low", "close", "volume", "quote_volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def generate_signal(symbol: str, df: pd.DataFrame, timeframe: str = "1h") -> dict:
    """Rule-based LONG / SHORT / WAIT from indicator alignment."""
    ind = compute_all(df)
    close = ind["close"]
    rsi = ind["rsi_14"]
    atr = ind["atr_14"]
    support, resistance = ind["support"], ind["resistance"]
    trend = ind["trend_strength"]
    macd_hist = ind["macd_hist"]
    vol = ind["volume"]

    long_conditions, short_conditions = [], []

    if trend > 0.3:
        long_conditions.append("Uptrend: EMA20>EMA50>EMA200")
    if trend < -0.3:
        short_conditions.append("Downtrend: EMA20<EMA50<EMA200")
    if rsi < 35:
        long_conditions.append(f"RSI oversold ({rsi:.1f})")
    if rsi > 65:
        short_conditions.append(f"RSI overbought ({rsi:.1f})")
    if macd_hist > 0:
        long_conditions.append("MACD histogram positive")
    if macd_hist < 0:
        short_conditions.append("MACD histogram negative")
    if close > ind["vwap"]:
        long_conditions.append("Price above VWAP")
    if close < ind["vwap"]:
        short_conditions.append("Price below VWAP")
    if vol["volume_rising"]:
        long_conditions.append("Volume above 20-period average")
    if close <= ind["bb_lower"]:
        long_conditions.append("Price at lower Bollinger band")
    if close >= ind["bb_upper"]:
        short_conditions.append("Price at upper Bollinger band")

    long_score, short_score = len(long_conditions), len(short_conditions)
    direction = "WAIT"
    if long_score >= 4 and long_score > short_score + 1:
        direction = "LONG"
    elif short_score >= 4 and short_score > long_score + 1:
        direction = "SHORT"

    # Rule-agreement score (0-1). NOT a probability of profit.
    total = long_score + short_score
    confidence = round(max(long_score, short_score) / total, 4) if total else 0.0

    entry = close
    if direction == "LONG":
        sl = entry - 1.5 * atr
        tp = entry + 3.0 * atr  # 2:1 reward/risk
    elif direction == "SHORT":
        sl = entry + 1.5 * atr
        tp = entry - 3.0 * atr
    else:
        sl = entry - 1.5 * atr
        tp = entry + 3.0 * atr

    invalidating = []
    if direction == "LONG":
        invalidating = [f"Close below support {support:.2f} invalidates",
                        f"RSI above 70 invalidates",
                        f"MACD histogram turns negative invalidates"]
    elif direction == "SHORT":
        invalidating = [f"Close above resistance {resistance:.2f} invalidates",
                        f"RSI below 30 invalidates",
                        f"MACD histogram turns positive invalidates"]

    return {
        "symbol": symbol,
        "direction": direction,
        "timeframe": timeframe,
        "entry_price": Decimal(str(round(entry, 8))),
        "stop_loss": Decimal(str(round(sl, 8))),
        "take_profit": Decimal(str(round(tp, 8))),
        "confidence_score": Decimal(str(confidence)),
        "indicators": {k: (round(v, 4) if isinstance(v, float) else v)
                       for k, v in ind.items() if k != "volume"} | {"volume": vol},
        "supporting_conditions": long_conditions if direction == "LONG" else (
            short_conditions if direction == "SHORT" else []),
        "invalidating_conditions": invalidating,
        "estimated_fee": Decimal("0"),  # filled by trading engine with real fee schedule
        "estimated_slippage": Decimal(str(round(0.0005 * entry, 8))),
    }

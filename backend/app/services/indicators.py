"""Technical indicators on OHLCV DataFrames (NumPy/Pandas only, no TA library).
Expected columns: open, high, low, close, volume (plus optional quote_volume)."""
import numpy as np
import pandas as pd


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    macd_line = ema(close, fast) - ema(close, slow)
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def bollinger(close: pd.Series, period: int = 20, std: float = 2.0):
    mid = close.rolling(period).mean()
    sd = close.rolling(period).std()
    return mid + std * sd, mid, mid - std * sd


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False).mean()


def vwap(df: pd.DataFrame) -> pd.Series:
    tp = (df["high"] + df["low"] + df["close"]) / 3
    return (tp * df["volume"]).cumsum() / df["volume"].cumsum()


def support_resistance(df: pd.DataFrame, window: int = 20):
    """Swing highs/lows: recent resistance = max high, support = min low over window."""
    recent = df.tail(window)
    return float(recent["low"].min()), float(recent["high"].max())


def trend_strength(df: pd.DataFrame) -> float:
    """Simple trend score in [-1, 1] from EMA alignment + price vs EMA200."""
    close = df["close"]
    e20, e50, e200 = ema(close, 20), ema(close, 50), ema(close, 200)
    score = 0.0
    if close.iloc[-1] > e20.iloc[-1]:
        score += 0.33
    if e20.iloc[-1] > e50.iloc[-1]:
        score += 0.33
    if e50.iloc[-1] > e200.iloc[-1]:
        score += 0.34
    if close.iloc[-1] < e20.iloc[-1]:
        score -= 0.33
    if e20.iloc[-1] < e50.iloc[-1]:
        score -= 0.33
    if e50.iloc[-1] < e200.iloc[-1]:
        score -= 0.34
    return round(score, 3)


def volume_analysis(df: pd.DataFrame, period: int = 20) -> dict:
    vol = df["volume"]
    avg = vol.rolling(period).mean()
    ratio = float(vol.iloc[-1] / avg.iloc[-1]) if avg.iloc[-1] else 0.0
    return {
        "current_volume": float(vol.iloc[-1]),
        "avg_volume_20": float(avg.iloc[-1]),
        "volume_ratio": round(ratio, 3),
        "volume_rising": bool(vol.iloc[-1] > avg.iloc[-1]),
    }


def compute_all(df: pd.DataFrame) -> dict:
    """Compute the full indicator set; returns a dict of latest values + series."""
    close = df["close"]
    macd_line, macd_sig, macd_hist = macd(close)
    upper, mid, lower = bollinger(close)
    support, resistance = support_resistance(df)
    return {
        "rsi_14": float(rsi(close).iloc[-1]),
        "ema_20": float(ema(close, 20).iloc[-1]),
        "ema_50": float(ema(close, 50).iloc[-1]),
        "ema_200": float(ema(close, 200).iloc[-1]),
        "macd": float(macd_line.iloc[-1]),
        "macd_signal": float(macd_sig.iloc[-1]),
        "macd_hist": float(macd_hist.iloc[-1]),
        "bb_upper": float(upper.iloc[-1]),
        "bb_mid": float(mid.iloc[-1]),
        "bb_lower": float(lower.iloc[-1]),
        "atr_14": float(atr(df).iloc[-1]),
        "vwap": float(vwap(df).iloc[-1]),
        "support": support,
        "resistance": resistance,
        "trend_strength": trend_strength(df),
        "volume": volume_analysis(df),
        "close": float(close.iloc[-1]),
    }

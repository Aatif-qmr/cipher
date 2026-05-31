"""
indicators/ta_wrappers.py
─────────────────────────
Thin, uniform wrappers over ta / talib so strategy code stays
library-agnostic.  Each function accepts a Pandas DataFrame and period
params, returns the series (not the full dataframe) so callers can assign
to any column name.

Tries ta-lib (C extension, fastest) first; falls back to the pure-Python
`ta` library (scikit-ta) so unit tests don't need ta-lib installed.
"""

from __future__ import annotations

import pandas as pd

try:
    import importlib.util
    _USE_TALIB = importlib.util.find_spec("talib") is not None
except ImportError:
    _USE_TALIB = False

try:
    import ta as _ta
    _USE_TA = True
except ImportError:
    _USE_TA = False


def _require_any() -> None:
    if not _USE_TALIB and not _USE_TA:
        raise ImportError("Install ta-lib or the `ta` package: pip install ta")


def add_rsi(df: pd.DataFrame, period: int = 14, column: str = "close") -> pd.Series:
    """RSI — Relative Strength Index."""
    _require_any()
    if _USE_TALIB:
        import talib
        return talib.RSI(df[column], timeperiod=period)
    return _ta.momentum.rsi(df[column], window=period)


def add_ema(df: pd.DataFrame, period: int = 20, column: str = "close") -> pd.Series:
    """EMA — Exponential Moving Average."""
    _require_any()
    if _USE_TALIB:
        import talib
        return talib.EMA(df[column], timeperiod=period)
    return df[column].ewm(span=period, adjust=False).mean()


def add_macd(
    df: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
    column: str = "close",
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """MACD — returns (macd_line, signal_line, histogram)."""
    _require_any()
    if _USE_TALIB:
        import talib
        return talib.MACD(df[column], fastperiod=fast, slowperiod=slow, signalperiod=signal)
    macd_obj = _ta.trend.MACD(df[column], window_fast=fast, window_slow=slow, window_sign=signal)
    return macd_obj.macd(), macd_obj.macd_signal(), macd_obj.macd_diff()


def add_bollinger_width(
    df: pd.DataFrame,
    period: int = 20,
    std_dev: float = 2.0,
    column: str = "close",
) -> pd.Series:
    """Bollinger Band width: (upper - lower) / close."""
    _require_any()
    if _USE_TALIB:
        import talib
        upper, _, lower = talib.BBANDS(df[column], timeperiod=period, nbdevup=std_dev, nbdevdn=std_dev)
        return (upper - lower) / df[column].replace(0, float("nan"))
    upper = _ta.volatility.bollinger_hband(df[column], window=period, window_dev=std_dev)
    lower = _ta.volatility.bollinger_lband(df[column], window=period, window_dev=std_dev)
    return (upper - lower) / df[column].replace(0, float("nan"))

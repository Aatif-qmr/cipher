# risk/volatility_breaker.py
# Transparent, calculable volatility circuit breaker.
# Replaces the black-box HMM regime model as the primary volatility gate.
#
# Rule:
#   24h realized vol > 2× 30-day median → block NEW entries for that pair
#   24h realized vol > 3× 30-day median → log warning (caller may exit early)
#
# "Realized volatility" here = std dev of log returns over last N candles,
# annualized. Uses the strategy's own OHLCV data — no external dependency.

from __future__ import annotations

import logging
import time
from collections import deque

import numpy as np

logger = logging.getLogger(__name__)

# Cache: pair → (vol_ratio, expires_at)
_cache: dict[str, tuple[float, float]] = {}
_CACHE_TTL = 300  # 5 minutes


def _realized_vol_annualized(closes: np.ndarray, candles_per_day: int) -> float:
    """Annualized realized volatility from close prices."""
    if len(closes) < 2:
        return 0.0
    log_returns = np.diff(np.log(closes[closes > 0]))
    if len(log_returns) == 0:
        return 0.0
    daily_vol = float(np.std(log_returns, ddof=1)) * np.sqrt(candles_per_day)
    return daily_vol * np.sqrt(252)  # annualize


def compute_vol_ratio(
    dataframe,
    candles_per_day: int = 24,
    short_window: int = 24,
    long_window: int = 720,
) -> float:
    """
    Returns vol_ratio = (short-window realized vol) / (long-window median rolling vol).

    Ratio > 2 → elevated volatility (block entries)
    Ratio > 3 → extreme volatility (warn about open positions)
    Ratio ≤ 2 → normal (allow trading)
    """
    if len(dataframe) < long_window + 1:
        return 1.0  # insufficient history → assume normal

    closes = dataframe["close"].to_numpy()

    # Short-window vol (last 24 candles = ~1 day on 1h)
    recent_closes = closes[-short_window - 1 :]
    short_vol = _realized_vol_annualized(recent_closes, candles_per_day)

    # Long-window rolling vol: compute rolling std of log returns over long_window
    log_returns = np.diff(np.log(closes[closes > 0]))
    if len(log_returns) < long_window:
        return 1.0

    # Rolling std over long_window with stride 24 (daily snapshots)
    rolling_vols = []
    stride = candles_per_day
    for i in range(0, len(log_returns) - long_window, stride):
        window = log_returns[i : i + long_window]
        rolling_vols.append(float(np.std(window, ddof=1)) * np.sqrt(candles_per_day) * np.sqrt(252))

    if not rolling_vols:
        return 1.0

    median_vol = float(np.median(rolling_vols))
    if median_vol == 0:
        return 1.0

    return short_vol / median_vol


def is_vol_elevated(dataframe, pair: str, candles_per_day: int = 24) -> bool:
    """
    Returns True if current volatility is > 2× 30-day median.
    Cached per pair for 5 minutes.
    """
    now = time.time()
    cached = _cache.get(pair)
    if cached and now < cached[1]:
        ratio = cached[0]
        if ratio > 2.0:
            logger.debug(f"[VOL BREAKER] {pair} ratio={ratio:.2f} (cached) → ELEVATED")
        return ratio > 2.0

    ratio = compute_vol_ratio(dataframe, candles_per_day=candles_per_day)
    _cache[pair] = (ratio, now + _CACHE_TTL)

    if ratio > 3.0:
        logger.warning(
            f"[VOL BREAKER] {pair} vol={ratio:.2f}× median — EXTREME. "
            "New entries blocked. Review open positions."
        )
    elif ratio > 2.0:
        logger.info(f"[VOL BREAKER] {pair} vol={ratio:.2f}× median — ELEVATED. New entries blocked.")

    return ratio > 2.0


def is_vol_extreme(dataframe, pair: str, candles_per_day: int = 24) -> bool:
    """Returns True if vol > 3× median (consider early exit of open positions)."""
    now = time.time()
    cached = _cache.get(pair)
    if cached and now < cached[1]:
        return cached[0] > 3.0
    ratio = compute_vol_ratio(dataframe, candles_per_day=candles_per_day)
    _cache[pair] = (ratio, now + _CACHE_TTL)
    return ratio > 3.0

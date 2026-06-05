# qnt/data/validation.py
# OHLCV data integrity checks run before any strategy computation.
# All checks are non-fatal — they log and flag, they do not raise.
# Callers use the returned ValidationResult to decide whether to block.
#
# Called by: data_pipeline.py (batch), and optionally from populate_indicators.

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

LOG_PATH = Path(__file__).resolve().parent.parent.parent / "logs/data_validation.log"


@dataclass
class ValidationResult:
    pair: str
    timeframe: str
    candle_count: int
    issues: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return len(self.issues) == 0

    def log(self) -> None:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        import datetime

        ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
        status = "OK" if self.passed else "WARN"
        lines = [f"[{ts}] [{status}] {self.pair}/{self.timeframe} candles={self.candle_count}"]
        for issue in self.issues:
            lines.append(f"  - {issue}")
        with open(LOG_PATH, "a") as f:
            f.write("\n".join(lines) + "\n")
        if not self.passed:
            logger.warning(
                "[DataValidation] %s/%s: %d issue(s) — %s",
                self.pair,
                self.timeframe,
                len(self.issues),
                "; ".join(self.issues),
            )


def validate_ohlcv(dataframe, pair: str, timeframe: str = "1h") -> ValidationResult:
    """
    Run data quality checks on a Freqtrade OHLCV DataFrame.

    Checks:
      1. Minimum candle count (< 200 → unusable for EMA_200)
      2. Gap detection: consecutive missing candles (> 3 in last 30 days)
      3. Zero/negative prices
      4. Volume = 0 candles (potential exchange data issue)
      5. OHLC consistency (high < low, close outside [low, high])
      6. Duplicate timestamps
    """
    if dataframe is None or (hasattr(dataframe, "empty") and dataframe.empty):
        result = ValidationResult(pair=pair, timeframe=timeframe, candle_count=0)
        result.issues.append("empty dataframe")
        result.log()
        return result

    result = ValidationResult(
        pair=pair,
        timeframe=timeframe,
        candle_count=len(dataframe),
    )

    # 1. Minimum candle count
    if len(dataframe) < 200:
        result.issues.append(f"only {len(dataframe)} candles — EMA_200 requires >= 200")

    closes = dataframe["close"].to_numpy()
    highs = dataframe["high"].to_numpy()
    lows = dataframe["low"].to_numpy()
    volumes = dataframe["volume"].to_numpy()

    # 2. Zero/negative prices
    bad_prices = int(np.sum(closes <= 0))
    if bad_prices > 0:
        result.issues.append(f"{bad_prices} candles with close <= 0")

    # 3. OHLC consistency
    bad_hl = int(np.sum(highs < lows))
    if bad_hl > 0:
        result.issues.append(f"{bad_hl} candles where high < low")

    bad_close = int(np.sum((closes > highs) | (closes < lows)))
    if bad_close > 0:
        result.issues.append(f"{bad_close} candles where close outside [low, high]")

    # 4. Zero-volume candles in last 30 days (last 720 1h candles)
    recent_vol = volumes[-720:] if len(volumes) >= 720 else volumes
    zero_vol = int(np.sum(recent_vol == 0))
    if zero_vol > 5:
        result.issues.append(f"{zero_vol} zero-volume candles in last 30 days")

    # 5. Gap detection via timestamps (if 'date' column present)
    if "date" in dataframe.columns:
        _check_gaps(dataframe, timeframe, result)

    # 6. Duplicate timestamps
    if "date" in dataframe.columns:
        dupes = dataframe["date"].duplicated().sum()
        if dupes > 0:
            result.issues.append(f"{int(dupes)} duplicate timestamps")

    result.log()
    return result


def _check_gaps(dataframe, timeframe: str, result: ValidationResult) -> None:
    """Add gap issues to result if > 3 consecutive missing candles in last 30 days."""
    _TF_SECONDS = {
        "1m": 60, "5m": 300, "15m": 900, "30m": 1800,
        "1h": 3600, "4h": 14400, "1d": 86400,
    }
    interval_sec = _TF_SECONDS.get(timeframe, 3600)
    days_back = 30
    cutoff_candles = (days_back * 86400) // interval_sec

    recent = dataframe.tail(cutoff_candles)
    if len(recent) < 2:
        return

    try:
        diffs_sec = (
            pd.to_datetime(recent["date"])
            .diff()
            .dropna()
            .dt.total_seconds()
            .to_numpy()
        )
        threshold = interval_sec * 1.5
        gaps = diffs_sec[diffs_sec > threshold]
        if len(gaps) > 0:
            max_gap_candles = int(max(gaps) // interval_sec)
            result.issues.append(
                f"{len(gaps)} timestamp gap(s) in last {days_back}d "
                f"(max gap = {max_gap_candles} candles)"
            )
    except Exception as exc:
        result.issues.append(f"gap check failed: {exc}")

"""Tests for qnt/data/validation.py — OHLCV data integrity checks."""

import numpy as np
import pandas as pd
import pytest

from qnt.data.validation import ValidationResult, validate_ohlcv


def _make_df(n: int = 300, start: str = "2025-01-01") -> pd.DataFrame:
    """Clean DataFrame with n 1h candles, no issues."""
    dates = pd.date_range(start=start, periods=n, freq="1h", tz="UTC")
    closes = np.linspace(40000, 45000, n)
    return pd.DataFrame(
        {
            "date": dates,
            "open": closes * 0.999,
            "high": closes * 1.002,
            "low": closes * 0.998,
            "close": closes,
            "volume": np.random.default_rng(42).uniform(100, 500, n),
        }
    )


# ── ValidationResult ──────────────────────────────────────────────────────────


def test_result_passes_with_no_issues():
    r = ValidationResult(pair="BTC/USDT", timeframe="1h", candle_count=300)
    assert r.passed


def test_result_fails_with_issues():
    r = ValidationResult(pair="BTC/USDT", timeframe="1h", candle_count=300, issues=["bad price"])
    assert not r.passed


# ── validate_ohlcv — passing cases ────────────────────────────────────────────


def test_clean_dataframe_passes():
    df = _make_df(300)
    result = validate_ohlcv(df, "BTC/USDT", "1h")
    assert result.passed, result.issues


def test_empty_dataframe_fails():
    result = validate_ohlcv(pd.DataFrame(), "BTC/USDT", "1h")
    assert not result.passed
    assert any("empty" in i for i in result.issues)


def test_none_dataframe_fails():
    result = validate_ohlcv(None, "BTC/USDT", "1h")
    assert not result.passed


# ── minimum candle count ──────────────────────────────────────────────────────


def test_too_few_candles_flagged():
    df = _make_df(100)
    result = validate_ohlcv(df, "BTC/USDT", "1h")
    assert not result.passed
    assert any("200" in i for i in result.issues)


def test_exactly_200_candles_passes_count_check():
    df = _make_df(200)
    result = validate_ohlcv(df, "BTC/USDT", "1h")
    assert not any("200" in i for i in result.issues)


# ── zero/negative prices ──────────────────────────────────────────────────────


def test_zero_close_flagged():
    df = _make_df(300)
    df.loc[df.index[50], "close"] = 0.0
    # Fix high/low so close-outside check doesn't double-count
    df.loc[df.index[50], "low"] = 0.0
    result = validate_ohlcv(df, "BTC/USDT", "1h")
    assert any("close <= 0" in i for i in result.issues)


def test_negative_close_flagged():
    df = _make_df(300)
    df.loc[df.index[50], "close"] = -1.0
    df.loc[df.index[50], "low"] = -1.0
    result = validate_ohlcv(df, "BTC/USDT", "1h")
    assert any("close <= 0" in i for i in result.issues)


# ── OHLC consistency ──────────────────────────────────────────────────────────


def test_high_less_than_low_flagged():
    df = _make_df(300)
    df.loc[df.index[100], "high"] = df.loc[df.index[100], "low"] - 1
    result = validate_ohlcv(df, "BTC/USDT", "1h")
    assert any("high < low" in i for i in result.issues)


def test_close_above_high_flagged():
    df = _make_df(300)
    df.loc[df.index[100], "close"] = df.loc[df.index[100], "high"] + 100
    result = validate_ohlcv(df, "BTC/USDT", "1h")
    assert any("outside [low, high]" in i for i in result.issues)


def test_close_below_low_flagged():
    df = _make_df(300)
    df.loc[df.index[100], "close"] = df.loc[df.index[100], "low"] - 100
    result = validate_ohlcv(df, "BTC/USDT", "1h")
    assert any("outside [low, high]" in i for i in result.issues)


# ── duplicate timestamps ──────────────────────────────────────────────────────


def test_duplicate_timestamps_flagged():
    df = _make_df(300)
    df.loc[df.index[5], "date"] = df.loc[df.index[4], "date"]  # duplicate
    result = validate_ohlcv(df, "BTC/USDT", "1h")
    assert any("duplicate" in i for i in result.issues)


# ── gap detection ─────────────────────────────────────────────────────────────


def test_gap_in_recent_data_flagged():
    df = _make_df(800)  # 800 candles so last-30d window has data
    # Inject a 5-hour gap in recent data by shifting timestamps after index 750
    for i in range(750, len(df)):
        df.loc[df.index[i], "date"] = df.loc[df.index[i], "date"] + pd.Timedelta(hours=5)
    result = validate_ohlcv(df, "BTC/USDT", "1h")
    assert any("gap" in i for i in result.issues)


# ── pair and metadata propagation ────────────────────────────────────────────


def test_result_records_pair_and_timeframe():
    df = _make_df(300)
    result = validate_ohlcv(df, "ETH/USDT", "4h")
    assert result.pair == "ETH/USDT"
    assert result.timeframe == "4h"
    assert result.candle_count == 300

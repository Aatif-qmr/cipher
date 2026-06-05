"""Tests for risk/stake_sizer.py — quarter-Kelly formula with WR floor."""

from unittest.mock import patch

import pytest

from risk.stake_sizer import (
    FLOOR,
    MIN_WIN_RATE,
    _compute_multiplier,
    get_stake_amount,
    get_stake_multiplier,
    quantize_stake,
)

# ── _compute_multiplier ───────────────────────────────────────────────────────


def test_below_min_wr_returns_zero():
    # WR < 0.45 → halt signal
    assert _compute_multiplier(0.0) == 0.0
    assert _compute_multiplier(0.35) == 0.0
    assert _compute_multiplier(0.44) == 0.0


def test_at_min_wr_boundary_returns_floor():
    # WR == 0.45 is valid edge — returns floor, not halt
    assert _compute_multiplier(MIN_WIN_RATE) == pytest.approx(FLOOR)


def test_50pct_wr_returns_floor():
    # quarter-Kelly at 50%: 0.25 * (2*0.5 - 1) = 0.0 → clamped up to FLOOR
    assert _compute_multiplier(0.50) == pytest.approx(FLOOR)


def test_65pct_wr_returns_floor():
    # quarter-Kelly at 65%: 0.25 * 0.30 = 0.075 → clamped up to FLOOR
    assert _compute_multiplier(0.65) == pytest.approx(FLOOR)


def test_75pct_wr_returns_floor():
    # quarter-Kelly at 75%: 0.25 * 0.50 = 0.125 → clamped up to FLOOR
    assert _compute_multiplier(0.75) == pytest.approx(FLOOR)


def test_100pct_wr_returns_floor():
    # quarter-Kelly at 100%: 0.25 * 1.0 = 0.25 → exactly FLOOR
    assert _compute_multiplier(1.0) == pytest.approx(FLOOR)


def test_returns_float():
    result = _compute_multiplier(0.60)
    assert isinstance(result, float)


def test_decimal_precision_below_wr_floor():
    # WR=0.40 < MIN_WIN_RATE (0.45) → halt, not old formula's 0.80
    result = _compute_multiplier(0.40)
    assert result == 0.0


def test_multiplier_rounded_to_2dp():
    # All valid WRs return FLOOR=0.25 (already 2dp exact)
    assert _compute_multiplier(0.63) == pytest.approx(0.25)
    assert _compute_multiplier(0.631) == pytest.approx(0.25)


# ── quantize_stake ────────────────────────────────────────────────────────────


def test_quantize_basic():
    assert quantize_stake(10.123456789, "0.001") == pytest.approx(10.123)


def test_quantize_rounds_down_not_up():
    # 10.005 with tick 0.01 → floor to 10.00, not round to 10.01
    assert quantize_stake(10.005, "0.01") == pytest.approx(10.0)


def test_quantize_whole_number_tick():
    assert quantize_stake(10.999, "1") == pytest.approx(10.0)


def test_quantize_no_truncation_needed():
    assert quantize_stake(10.5, "0.5") == pytest.approx(10.5)


def test_quantize_zero_amount():
    assert quantize_stake(0.0, "0.01") == pytest.approx(0.0)


def test_quantize_negative_amount_returns_zero():
    assert quantize_stake(-5.0, "0.01") == 0.0


def test_quantize_float_tick_converted_correctly():
    # 0.1 as float has representation error; str(0.1) → "0.1" → exact Decimal
    result = quantize_stake(10.15, 0.1)
    assert result == pytest.approx(10.1)


def test_quantize_satoshi_precision():
    result = quantize_stake(0.123456789, "0.00000001")
    assert result == pytest.approx(0.12345678)


def test_quantize_invalid_tick_returns_zero():
    assert quantize_stake(100.0, "0") == 0.0
    assert quantize_stake(100.0, "-0.01") == 0.0


def test_quantize_returns_float():
    result = quantize_stake(10.5, "0.01")
    assert isinstance(result, float)


def test_quantize_large_stake():
    assert quantize_stake(100000.123456, "0.01") == pytest.approx(100000.12)


# ── get_stake_amount ──────────────────────────────────────────────────────────


def test_get_stake_amount_no_tick(monkeypatch):
    monkeypatch.setattr("risk.stake_sizer.get_stake_multiplier", lambda s: 1.5)
    result = get_stake_amount("ScalpV1", 100.0)
    assert result == pytest.approx(150.0)


def test_get_stake_amount_with_tick(monkeypatch):
    monkeypatch.setattr("risk.stake_sizer.get_stake_multiplier", lambda s: 1.3)
    result = get_stake_amount("ScalpV1", 100.0, tick_size="0.01")
    assert result == pytest.approx(130.0)


def test_get_stake_amount_tick_truncates(monkeypatch):
    monkeypatch.setattr("risk.stake_sizer.get_stake_multiplier", lambda s: 1.33)
    # 75 * 1.33 = 99.75 → tick 1.0 → 99.0
    result = get_stake_amount("ScalpV1", 75.0, tick_size="1")
    assert result == pytest.approx(99.0)


def test_get_stake_amount_fallback_multiplier(monkeypatch):
    monkeypatch.setattr("risk.stake_sizer.get_stake_multiplier", lambda s: 1.0)
    result = get_stake_amount("UnknownStrategy", 200.0)
    assert result == pytest.approx(200.0)


def test_get_stake_amount_returns_float(monkeypatch):
    monkeypatch.setattr("risk.stake_sizer.get_stake_multiplier", lambda s: 1.2)
    result = get_stake_amount("ScalpV1", 100.0, tick_size="0.01")
    assert isinstance(result, float)


# ── get_stake_multiplier fallback ─────────────────────────────────────────────


def test_get_stake_multiplier_returns_floor_when_no_db():
    # No DB → FLOOR (was 1.0 under old formula)
    result = get_stake_multiplier("NonExistentStrategy")
    assert result == pytest.approx(FLOOR)


def test_get_stake_multiplier_returns_floor_below_min_trades():
    # < MIN_TRADES rows → FLOOR, not 1.0
    with patch("risk.stake_sizer._fetch_via_sqlite", return_value=[0.01] * 5):
        result = get_stake_multiplier("ScalpV1")
    assert result == pytest.approx(FLOOR)


def test_get_stake_multiplier_computes_from_trades():
    # 30 wins / 40 → 75% WR → quarter-Kelly = 0.125 → clamped to FLOOR
    profits = [0.01] * 30 + [-0.01] * 10
    with patch("risk.stake_sizer._fetch_via_sqlite", return_value=profits):
        result = get_stake_multiplier("ScalpV1_test_isolation_" + str(id(profits)))
    assert result == pytest.approx(FLOOR)


def test_get_stake_multiplier_halts_below_wr_floor():
    # 15 wins / 40 → 37.5% WR < 45% → halt (0.0)
    profits = [0.01] * 15 + [-0.01] * 25
    with patch("risk.stake_sizer._fetch_via_sqlite", return_value=profits):
        result = get_stake_multiplier("ScalpV1_test_low_wr_" + str(id(profits)))
    assert result == 0.0

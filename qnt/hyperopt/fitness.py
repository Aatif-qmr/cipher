"""
qnt/hyperopt/fitness.py
────────────────────────
Fitness function for strategy hyperparameter trials.

Runs a freqtrade backtest for the given strategy + param dict and
returns a scalar fitness score to maximise.

Scoring: Sharpe ratio (primary) × (1 - max_drawdown) to penalise
high-drawdown runs that happen to have a good Sharpe.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent.parent
_DATA_DIR = _BASE / "user_data" / "data"
_STRATEGY_DIR = _BASE / "strategies" / "active"


def _write_param_override(strategy: str, params: dict) -> Path:
    """Write params to a temp JSON file freqtrade reads as --hyperopt-results."""
    data = {strategy: {"params": {"buy": {}, "sell": {}, "roi": {}, "stoploss": {}}}}
    data[strategy]["params"]["buy"] = {
        k: v for k, v in params.items() if k.startswith("buy_") or k.startswith("entry_")
    }
    data[strategy]["params"]["sell"] = {
        k: v for k, v in params.items() if k.startswith("sell_") or k.startswith("exit_")
    }
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", prefix=f"cipher_trial_{strategy}_", delete=False
    )
    json.dump(data, tmp)
    tmp.flush()
    return Path(tmp.name)


def evaluate_params(
    strategy: str,
    params: dict,
    timerange: str = "20260101-20260501",
    pair: str = "BTC/USDT",
) -> float:
    """
    Run a freqtrade backtest with the given params.
    Returns fitness score (higher = better). Returns -inf on failure.
    """
    param_file = _write_param_override(strategy, params)
    try:
        result = subprocess.run(
            [
                "freqtrade",
                "backtesting",
                "--strategy",
                strategy,
                "--strategy-path",
                str(_STRATEGY_DIR),
                "--timerange",
                timerange,
                "--pairs",
                pair,
                "--datadir",
                str(_DATA_DIR),
                "--export",
                "none",
                "--hyperopt-filename",
                str(param_file),
                "--print-json",
            ],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(_BASE),
            env={**os.environ, "PYTHONPATH": str(_BASE)},
        )
        if result.returncode != 0:
            return float("-inf")

        # Parse JSON output — last JSON object on stdout
        for line in reversed(result.stdout.splitlines()):
            line = line.strip()
            if line.startswith("{"):
                try:
                    data = json.loads(line)
                    sharpe = float(data.get("sharpe_ratio", 0.0) or 0.0)
                    max_dd = abs(float(data.get("max_drawdown", 0.0) or 0.0))
                    # Penalise drawdown above 15 %
                    penalty = max(0.0, max_dd - 0.15)
                    return sharpe * (1.0 - penalty)
                except (json.JSONDecodeError, TypeError, ValueError):
                    continue
        return float("-inf")
    except subprocess.TimeoutExpired:
        return float("-inf")
    except Exception:
        return float("-inf")
    finally:
        param_file.unlink(missing_ok=True)

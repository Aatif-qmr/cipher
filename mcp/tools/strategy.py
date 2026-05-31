"""mcp/tools/strategy.py — Strategy and system health status."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent.parent
_STRATEGIES = [
    "DailyTrendV1",
    "TrendFollowV1",
    "MeanReversionV1",
    "ScalpV1",
    "MicroScalpV1",
    "SwingV1",
    "VectorVaultV1",
]


def get_strategy_status() -> str:
    """Return names and file presence of all active strategies."""
    result = {}
    for name in _STRATEGIES:
        path = _BASE / "strategies" / "active" / f"{name}.py"
        result[name] = {"file_exists": path.exists(), "path": str(path)}
    return json.dumps(result)


def get_system_status() -> str:
    """Check which freqtrade processes are running."""
    try:
        out = subprocess.run(
            ["pgrep", "-af", "freqtrade"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        procs = [line.strip() for line in out.stdout.splitlines() if line.strip()]
    except Exception as e:
        procs = [f"pgrep failed: {e}"]

    vault_db = _BASE / "user_data" / "tradesv3.dryrun.sqlite"
    return json.dumps(
        {
            "freqtrade_processes": procs,
            "process_count": len(procs),
            "vault_db_exists": vault_db.exists(),
        }
    )


def get_risk_status() -> str:
    """Run cipher risk gates and return result."""
    try:
        import sys

        sys.path.insert(0, str(_BASE))
        from risk.risk_manager import run_all_checks

        result = run_all_checks()
        return json.dumps({"risk_check": result}, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})

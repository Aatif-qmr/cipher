"""mcp/tools/hyperopt.py — Control cipher's distributed hyperopt (Ray + Optuna)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_BASE))


def control_hyperopt(action: str, strategy: str | None = None) -> str:
    """
    Control distributed hyperopt.

    Actions:
        status  — return current study status from Optuna DB
        start   — launch Ray + Optuna study for `strategy`
        stop    — gracefully cancel current study
        results — return best trial params for `strategy`
    """
    try:
        from qnt.hyperopt.distributed import (
            get_best_params,
            get_study_status,
            start_study,
            stop_study,
        )

        if action == "status":
            return json.dumps(get_study_status(strategy))
        elif action == "start":
            if not strategy:
                return json.dumps({"error": "strategy name required for start"})
            result = start_study(strategy)
            return json.dumps(result)
        elif action == "stop":
            result = stop_study(strategy)
            return json.dumps(result)
        elif action == "results":
            if not strategy:
                return json.dumps({"error": "strategy name required for results"})
            return json.dumps(get_best_params(strategy), default=str)
        else:
            return json.dumps(
                {"error": f"unknown action: {action}. Use: status/start/stop/results"}
            )
    except ImportError:
        return json.dumps({"error": "distributed hyperopt not installed — run: uv add optuna ray"})
    except Exception as e:
        return json.dumps({"error": str(e)})

"""mcp/tools/sentiment.py — Read current market sentiment and macro covariates."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_BASE))


def get_sentiment() -> str:
    """Return current multi-source sentiment score and component breakdown."""
    try:
        from sentiment.reader import get_current_sentiment
        data = get_current_sentiment()
        return json.dumps(data, default=str)
    except Exception as e:
        return json.dumps({"error": str(e), "score": 0.0})


def get_macro() -> str:
    """Return latest macro covariates: DXY 24h change, BTC funding rate, open interest."""
    macro_file = _BASE / "risk" / "macro_history.json"
    if not macro_file.exists():
        return json.dumps({"error": "macro_history.json not found"})
    try:
        with open(macro_file) as f:
            history = json.load(f)
        latest = max(history, key=lambda x: x.get("timestamp", ""))
        return json.dumps({
            "timestamp": latest.get("timestamp"),
            "dxy_24h_change": latest.get("dxy_24h_change", 0.0),
            "btc_funding_rate": latest.get("btc_funding_rate", 0.0),
            "btc_open_interest": latest.get("btc_open_interest", 0.0),
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


def recall_vault(query: str, n_results: int = 5) -> str:
    """Semantic search through VectorVault trade lessons in Qdrant."""
    try:
        from qnt.tools.vault import recall
        results = recall(query, n_results=n_results)
        return json.dumps({"query": query, "results": results}, default=str)
    except Exception as e:
        return json.dumps({"query": query, "error": str(e)})

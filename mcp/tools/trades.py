"""mcp/tools/trades.py — Query live and closed trades from Freqtrade SQLite DBs."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent.parent
_DB_PATHS = [
    _BASE / "user_data" / "tradesv3.dryrun.sqlite",
    _BASE / "user_data" / "tradesv3.sqlite",
    _BASE / "user_data" / "mean_reversion.sqlite",
    _BASE / "user_data" / "trend_follow.sqlite",
    _BASE / "user_data" / "scalp.sqlite",
    _BASE / "user_data" / "swing.sqlite",
    _BASE / "user_data" / "daily.sqlite",
    _BASE / "user_data" / "micro.sqlite",
]


def _query_db(db_path: Path, sql: str) -> list[dict]:
    if not db_path.exists():
        return []
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(sql).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []


def get_open_trades() -> str:
    """Return all currently open trades across all strategy DBs as JSON."""
    all_trades: list[dict] = []
    for db_path in _DB_PATHS:
        rows = _query_db(
            db_path,
            "SELECT pair, strategy, open_date, open_rate, stake_amount, "
            "current_profit FROM trades WHERE is_open=1",
        )
        for row in rows:
            row["db"] = db_path.stem
            all_trades.append(row)
    if not all_trades:
        return json.dumps({"open_trades": [], "count": 0})
    return json.dumps({"open_trades": all_trades, "count": len(all_trades)}, default=str)


def get_recent_closed_trades(limit: int = 20) -> str:
    """Return most recent closed trades across all strategy DBs."""
    all_trades: list[dict] = []
    for db_path in _DB_PATHS:
        rows = _query_db(
            db_path,
            f"SELECT pair, strategy, open_date, close_date, profit_ratio, profit_abs "
            f"FROM trades WHERE is_open=0 ORDER BY close_date DESC LIMIT {limit}",
        )
        for row in rows:
            row["db"] = db_path.stem
            all_trades.append(row)
    all_trades.sort(key=lambda t: t.get("close_date", ""), reverse=True)
    return json.dumps(
        {"trades": all_trades[:limit], "count": len(all_trades[:limit])}, default=str
    )


def get_pnl_summary(period: str = "daily") -> str:
    """Summarise realised P&L — period: daily | weekly | monthly | all."""
    period_filter = {
        "daily": "date(close_date) = date('now')",
        "weekly": "close_date >= datetime('now', '-7 days')",
        "monthly": "close_date >= datetime('now', '-30 days')",
        "all": "1=1",
    }.get(period, "1=1")

    totals: dict[str, float] = {}
    for db_path in _DB_PATHS:
        rows = _query_db(
            db_path,
            f"SELECT strategy, SUM(profit_abs) as total_profit, COUNT(*) as trade_count "
            f"FROM trades WHERE is_open=0 AND {period_filter} GROUP BY strategy",
        )
        for row in rows:
            strat = row.get("strategy") or db_path.stem
            totals[strat] = totals.get(strat, 0.0) + (row.get("total_profit") or 0.0)

    return json.dumps({"period": period, "pnl_by_strategy": totals}, default=str)

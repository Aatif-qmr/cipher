"""
mcp/server.py
─────────────
Cipher MCP Server — exposes trading system state and controls to AI agents.

Usage:
    python -m mcp.server --port 9010
    python -m mcp.server --port 9010 --host 127.0.0.1

The server uses FastMCP (streamable-http transport) so any MCP-compatible
client (Claude Desktop, Cursor, etc.) can connect via:
    http://localhost:9010/mcp
"""

from __future__ import annotations

import argparse
import logging
import sys
import traceback
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BASE))

from mcp.server.fastmcp import FastMCP  # noqa: E402
from mcp.tools.hyperopt import control_hyperopt  # noqa: E402
from mcp.tools.sentiment import get_macro, get_sentiment, recall_vault  # noqa: E402
from mcp.tools.strategy import get_risk_status, get_strategy_status, get_system_status  # noqa: E402
from mcp.tools.trades import (  # noqa: E402
    get_open_trades,
    get_pnl_summary,
    get_recent_closed_trades,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("cipher.mcp.server")

parser = argparse.ArgumentParser(description="Cipher MCP Server")
parser.add_argument("--port", type=int, default=9010, help="Port (default: 9010)")
parser.add_argument("--host", type=str, default="0.0.0.0", help="Bind host")
args = parser.parse_args()

server = FastMCP(
    "Cipher MCP Server",
    host=args.host,
    port=args.port,
    json_response=True,
)

# ── Trade tools ──────────────────────────────────────────────────────────────


@server.tool()
def cipher_get_open_trades() -> str:
    """List all currently open trades across all Cipher strategy instances."""
    return get_open_trades()


@server.tool()
def cipher_get_recent_trades(limit: int = 20) -> str:
    """Return the most recently closed trades (default: 20)."""
    return get_recent_closed_trades(limit=limit)


@server.tool()
def cipher_get_pnl(period: str = "daily") -> str:
    """Summarise realised P&L. period: daily | weekly | monthly | all"""
    return get_pnl_summary(period=period)


# ── System tools ─────────────────────────────────────────────────────────────


@server.tool()
def cipher_get_strategy_status() -> str:
    """Return which strategy files exist and their paths."""
    return get_strategy_status()


@server.tool()
def cipher_get_system_status() -> str:
    """Check which Freqtrade processes are running and DB presence."""
    return get_system_status()


@server.tool()
def cipher_get_risk_status() -> str:
    """Run all risk gates (drawdown, correlation, position size) and return result."""
    return get_risk_status()


# ── Market intelligence tools ────────────────────────────────────────────────


@server.tool()
def cipher_get_sentiment() -> str:
    """Return current multi-source sentiment score and component breakdown."""
    return get_sentiment()


@server.tool()
def cipher_get_macro() -> str:
    """Return latest macro covariates: DXY, BTC funding rate, open interest."""
    return get_macro()


@server.tool()
def cipher_recall_vault(query: str, n_results: int = 5) -> str:
    """Semantic search through VectorVault trade lessons. query: natural language."""
    return recall_vault(query=query, n_results=n_results)


# ── Hyperopt control ─────────────────────────────────────────────────────────


@server.tool()
def cipher_control_hyperopt(action: str, strategy: str = "") -> str:
    """
    Control distributed Optuna/Ray hyperopt.
    action: status | start | stop | results
    strategy: strategy class name (required for start/results)
    """
    return control_hyperopt(action=action, strategy=strategy or None)


# ── Entrypoint ───────────────────────────────────────────────────────────────


def run() -> None:
    mcp_url = f"http://{args.host}:{args.port}/mcp"
    logger.info("Cipher MCP server starting at %s", mcp_url)
    try:
        server.run(transport="streamable-http")
    except Exception as exc:
        logger.error("MCP server failure: %s\n%s", exc, traceback.format_exc())
        raise


if __name__ == "__main__":
    run()

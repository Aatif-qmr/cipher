"""Shim — Cipher MCP server moved to cipher_mcp/server.py to avoid PyPI mcp name conflict."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cipher_mcp.server import run  # noqa: F401, E402

if __name__ == "__main__":
    run()

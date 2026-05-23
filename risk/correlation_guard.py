# risk/correlation_guard.py
# Prevents stacking multiple long positions on the same base asset across all strategy DBs.
# Rule: if 2+ bots are already long BTC (or any base), block a new BTC long.
# Short positions are excluded from the count — they reduce, not increase, directional risk.

import sqlite3
import time
from collections import Counter
from pathlib import Path

BASE_DIR = Path.home() / 'masterbot'

DB_PATHS = [
    BASE_DIR / 'user_data/scalp.sqlite',
    BASE_DIR / 'user_data/swing.sqlite',
    BASE_DIR / 'user_data/mean_reversion.sqlite',
    BASE_DIR / 'user_data/trend_follow.sqlite',
    BASE_DIR / 'user_data/daily.sqlite',
]

MAX_LONG_SLOTS_PER_BASE = 2   # allow up to 2 concurrent longs on same asset
CACHE_TTL = 60                 # re-scan all DBs every 60 seconds

_cache: dict = {'data': None, 'expires': 0.0}


def _scan_open_longs() -> Counter:
    """Return {base_currency: count_of_open_long_trades} across all strategy DBs."""
    counts: Counter = Counter()
    for db_path in DB_PATHS:
        if not db_path.exists():
            continue
        try:
            con = sqlite3.connect(str(db_path))
            rows = con.execute(
                "SELECT base_currency FROM trades "
                "WHERE is_open=1 AND (is_short=0 OR is_short IS NULL)"
            ).fetchall()
            con.close()
            for (base,) in rows:
                if base:
                    counts[base] += 1
        except Exception:
            pass
    return counts


def get_open_long_counts() -> Counter:
    now = time.time()
    if _cache['data'] is not None and now < _cache['expires']:
        return _cache['data']
    counts = _scan_open_longs()
    _cache['data'] = counts
    _cache['expires'] = now + CACHE_TTL
    return counts


def is_blocked(base_currency: str, side: str = 'long') -> bool:
    """
    Return True if entering a new long on base_currency is blocked.
    Short entries are never blocked by this guard.
    """
    if side == 'short':
        return False
    counts = get_open_long_counts()
    return counts.get(base_currency, 0) >= MAX_LONG_SLOTS_PER_BASE


def invalidate_cache():
    """Force re-scan on next call (call after opening a trade)."""
    _cache['expires'] = 0.0

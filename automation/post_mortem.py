#!/usr/bin/env python3
"""
Automated post-mortem analysis for losing trades.
Runs every 2 hours via cron. Logs lessons to qnt vault.
"""
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import sys
import os

# Detect BASE_DIR
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from qnt.vault.vault import Vault

def analyze_losing_trades(db_path: str, hours: int = 2) -> list:
    """Extract losing trades from last N hours."""
    if not os.path.exists(db_path):
        return []
        
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    since = (datetime.now() - timedelta(hours=hours)).timestamp()
    
    # Try to find the correct table structure
    try:
        query = """
        SELECT pair, open_date, close_date, close_profit as profit_ratio, 
               open_rate, close_rate, stake_amount, strategy
        FROM trades 
        WHERE close_date IS NOT NULL 
          AND close_date >= ?
          AND close_profit < -0.01  /* Losses > 1% */
        ORDER BY close_date DESC
        """

        cursor.execute(query, (datetime.fromtimestamp(since).isoformat(),))
        trades = [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"Query error: {e}")
        trades = []
        
    conn.close()
    return trades

def generate_lesson(trade: dict) -> dict:
    """Convert losing trade to structured lesson for Vault."""
    return {
        "type": "losing_trade_analysis",
        "timestamp": datetime.now().isoformat(),
        "pair": trade["pair"],
        "strategy": trade["strategy"],
        "loss_pct": trade["profit_ratio"] * 100,
        "entry_price": trade["open_rate"],
        "exit_price": trade["close_rate"],
        "duration_minutes": (
            datetime.fromisoformat(trade["close_date"].replace("Z", "+00:00")) -
            datetime.fromisoformat(trade["open_date"].replace("Z", "+00:00"))
        ).total_seconds() / 60 if trade["close_date"] else None,
        "hypothesis": f"Loss may indicate regime mismatch or sentiment lag for {trade['strategy']} on {trade['pair']}",
        "action_items": [
            f"Review {trade['strategy']} entry conditions during similar market conditions",
            "Check if sentiment score was stale at entry time",
            "Consider adding regime filter if not already present"
        ]
    }

def main():
    vault = Vault()
    db_path = BASE_DIR / "user_data/tradesv3_micro.sqlite"
    
    if not db_path.exists():
        # Fallback to main paper dryrun db if micro one doesn't have trades yet
        db_path = BASE_DIR / "user_data/tradesv3.dryrun.sqlite"
        
    if not db_path.exists():
        print(f"DB not found: {db_path}")
        return
    
    losing_trades = analyze_losing_trades(str(db_path))
    
    for trade in losing_trades:
        lesson = generate_lesson(trade)
        vault.store(lesson, tags=["post_mortem", lesson["strategy"], lesson["pair"]])
        print(f"Logged post-mortem: {trade['pair']} {trade['profit_ratio']*100:.2f}% loss")
    
    print(f"Post-mortem loop complete. Processed {len(losing_trades)} losing trades.")

if __name__ == "__main__":
    main()

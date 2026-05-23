import subprocess
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR / 'qnt/memory'))
sys.path.insert(0, str(BASE_DIR / 'qnt/vault'))

from vault import recall_lessons

MASTERBOT_PATH = str(BASE_DIR)

def build_skeptic_prompt(trade_proposal):
    pair = trade_proposal.get('pair')
    strategy = trade_proposal.get('strategy')
    direction = trade_proposal.get('direction')
    entry_price = trade_proposal.get('entry_price')
    stake_amount = trade_proposal.get('stake_amount')
    rsi = trade_proposal.get('rsi')
    sentiment_score = trade_proposal.get('sentiment_score', 0.0)
    hmm_regime = trade_proposal.get('hmm_regime')
    order_flow_summary = trade_proposal.get('order_flow_summary', 'neutral')
    recent_candles_text = trade_proposal.get('recent_candles', 'No candle data provided')
    
    vault_context = get_vault_context(pair, strategy)
    
    prompt = f"""You are the Skeptic agent for MasterBot.
Your job is to find reasons NOT to take this trade.
Be rigorous. Be cynical. Protect the portfolio.

PROPOSED TRADE:
Pair: {pair}
Strategy: {strategy}
Direction: {direction}
Entry Price: {entry_price}
Stake: {stake_amount} USDT

CURRENT CONDITIONS:
RSI: {rsi}
Sentiment: {sentiment_score:.3f}
HMM Regime: {hmm_regime}
Order Flow: {order_flow_summary}

RECENT PRICE ACTION (last 5 candles):
{recent_candles_text}

VAULT HISTORY:
{vault_context}

YOUR TASK:
1. List up to 3 specific reasons this trade could fail RIGHT NOW (not general risks)
2. Rate your confidence this trade will fail: 0.0 = very likely to succeed, 1.0 = very likely to fail
3. State: BLOCK or ALLOW

BLOCK if confidence > 0.65
ALLOW if confidence <= 0.65

Respond in JSON only:
{{
  "reasons": ["reason1", "reason2"],
  "failure_confidence": 0.0-1.0,
  "decision": "BLOCK" or "ALLOW",
  "primary_concern": "one sentence summary"
}}
"""
    return prompt

def run_skeptic(trade_proposal) -> dict:
    skeptic_prompt = build_skeptic_prompt(trade_proposal)
    
    try:
        # Use full path to qnt
        qnt_bin = '/usr/local/bin/qnt' # Fallback or detect
        import shutil
        qnt_bin = shutil.which('qnt') or qnt_bin
        
        result = subprocess.run(
            [qnt_bin, '-p', skeptic_prompt, '--output-format', 'text'],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=MASTERBOT_PATH
        )
        
        output = result.stdout.strip()
        # Strip markdown fences if present
        if output.startswith("```json"):
            output = output[7:]
        if output.startswith("```"):
            output = output[3:]
        if output.endswith("```"):
            output = output[:-3]
            
        return json.loads(output.strip())
        
    except Exception as e:
        return {
            "decision": "ALLOW",
            "failure_confidence": 0.3,
            "reasons": [f"Skeptic unavailable: {str(e)}"],
            "primary_concern": "Skeptic error/timeout — allowing"
        }

def get_vault_context(pair, strategy) -> str:
    try:
        # Search vault for similar past trades
        results = recall_lessons(f"{strategy} {pair} loss failure", n_results=3)

        if results:
            summary = "Past relevant failures:\n"
            for result in results:
                doc = result.get("document", "")
                summary += f"- {doc[:200]}...\n"
            return summary

        return "No relevant vault history found"
    except Exception as e:
        return "No relevant vault history found"

def get_recent_candles_text(pair, timeframe, n=5) -> str:
    try:
        import pandas as pd
        # Correct data path
        data_path = Path(MASTERBOT_PATH) / f"user_data/data/binance/{pair.replace('/', '_')}-{timeframe}.feather"
        if not data_path.exists():
            # Try parquet or json if feather doesn't exist
            data_path = Path(MASTERBOT_PATH) / f"user_data/data/binance/{pair.replace('/', '_')}-{timeframe}.parquet"
            
        if not data_path.exists():
             return "Candle data file not found"

        if data_path.suffix == '.feather':
            df = pd.read_feather(data_path)
        else:
            df = pd.read_parquet(data_path)
            
        last_n = df.tail(n)
        lines = []
        for _, row in last_n.iterrows():
            ts = row['date'].strftime('%Y-%m-%d %H:%M')
            lines.append(f"{ts}: O={row['open']:.2f} H={row['high']:.2f} L={row['low']:.2f} C={row['close']:.2f} V={row['volume']:.0f}")
        
        return "\n".join(lines)
    except Exception as e:
        return f"Error formatting candles: {str(e)}"

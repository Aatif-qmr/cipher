import sys
import json
import os
from datetime import datetime, timezone
from pathlib import Path

# Add paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR / 'qnt/agents'))
sys.path.insert(0, str(BASE_DIR / 'qnt/memory'))
sys.path.insert(0, str(BASE_DIR / 'qnt/vault'))

SKEPTIC_ENABLED = True
SKEPTIC_LOG_PATH = str(BASE_DIR / 'logs/skeptic.log')

def evaluate_trade(trade_proposal) -> dict:
    """
    Main gate function called by strategies.
    Returns dict with decision and reasoning.
    """
    if not SKEPTIC_ENABLED:
        return {"decision": "ALLOW", "source": "gate_disabled"}
    
    # Ensure logs directory exists
    os.makedirs(os.path.dirname(SKEPTIC_LOG_PATH), exist_ok=True)
    
    # Run Skeptic evaluation
    try:
        from skeptic import run_skeptic
        skeptic_result = run_skeptic(trade_proposal)
    except Exception as e:
        skeptic_result = {
            "decision": "ALLOW",
            "failure_confidence": 0.3,
            "reasons": [f"Skeptic import error: {str(e)}"],
            "primary_concern": "Skeptic internal error — allowing"
        }
    
    decision = skeptic_result.get('decision', 'ALLOW')
    confidence = skeptic_result.get('failure_confidence', 0.3)
    reasons = skeptic_result.get('reasons', [])
    concern = skeptic_result.get('primary_concern', '')
    
    # Log every evaluation
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat() + 'Z',
        "pair": trade_proposal.get('pair'),
        "strategy": trade_proposal.get('strategy'),
        "decision": decision,
        "failure_confidence": confidence,
        "primary_concern": concern,
        "reasons": reasons
    }
    
    with open(SKEPTIC_LOG_PATH, 'a') as f:
        f.write(json.dumps(log_entry) + '\n')
    
    # Store in Vault if BLOCK
    if decision == "BLOCK":
        try:
            from vault import add_entry
            content = f"""
SKEPTIC BLOCK:
Pair: {trade_proposal.get('pair')}
Strategy: {trade_proposal.get('strategy')}
Confidence trade fails: {confidence:.0%}
Primary concern: {concern}
Reasons: {'; '.join(reasons)}
"""
            add_entry("trade_memory", content, {
                "timestamp": log_entry["timestamp"],
                "category": "skeptic_block",
                "outcome": "blocked",
                "strategy": trade_proposal.get('strategy',''),
                "pair": trade_proposal.get('pair',''),
                "confidence": str(confidence)
            })
        except Exception as e:
            print(f"Vault log error: {e}")
    
    # Update memory with skeptic stats
    try:
        from memory_manager import load_memory, save_memory
        mem = load_memory()
        stats = mem.get('skeptic_stats', {'total': 0, 'blocked': 0, 'allowed': 0})
        stats['total'] += 1
        if decision == 'BLOCK':
            stats['blocked'] += 1
        else:
            stats['allowed'] += 1
        mem['skeptic_stats'] = stats
        save_memory(mem)
    except Exception as e:
        print(f"Memory update error: {e}")
    
    return {
        "decision": decision,
        "failure_confidence": confidence,
        "primary_concern": concern,
        "reasons": reasons,
        "source": "skeptic_agent"
    }

def get_skeptic_stats() -> str:
    """Load skeptic stats from memory and return formatted string."""
    try:
        from memory_manager import load_memory
        mem = load_memory()
        stats = mem.get('skeptic_stats', {'total': 0, 'blocked': 0, 'allowed': 0})
        
        total = stats['total']
        blocked = stats['blocked']
        allowed = stats['allowed']
        
        allowed_pct = (allowed / total * 100) if total > 0 else 0
        blocked_pct = (blocked / total * 100) if total > 0 else 0
        
        output = f"""🔍 Skeptic Agent Stats
━━━━━━━━━━━━━━━━━━━━━
Total evaluated:  {total}
Allowed:          {allowed} ({allowed_pct:.1f}%)
Blocked:          {blocked} ({blocked_pct:.1f}%)
Status:           {'ENABLED' if SKEPTIC_ENABLED else 'DISABLED'}
"""
        # Recent blocks
        if os.path.exists(SKEPTIC_LOG_PATH):
            output += "\nRecent evaluations:\n"
            with open(SKEPTIC_LOG_PATH, 'r') as f:
                lines = f.readlines()[-3:]
                for line in reversed(lines):
                    try:
                        d = json.loads(line)
                        output += f"• {d['timestamp'][11:16]} | {d['pair']} | {d['decision']} ({d['failure_confidence']:.0%})\n"
                    except: pass
        
        return output
    except Exception as e:
        return f"Error loading skeptic stats: {e}"

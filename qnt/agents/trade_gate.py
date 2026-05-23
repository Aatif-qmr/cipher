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
CONSTRAINTS_PATH = BASE_DIR / 'config/vault_constraints.json'


def _check_vault_constraints(pair: str, strategy: str,
                              sentiment_score: float, regime: str):
    """Returns a block reason string if a vault constraint fires, else None."""
    try:
        if not CONSTRAINTS_PATH.exists():
            return None
        data = json.loads(CONSTRAINTS_PATH.read_text())
        rules = data.get('constraints', {}).get(strategy, {}).get(pair, {})
        if not rules:
            return None

        min_sent = rules.get('min_sentiment')
        if min_sent is not None and sentiment_score < min_sent:
            return (f'Vault constraint: {strategy}/{pair} requires '
                    f'sentiment ≥ {min_sent:.2f} (got {sentiment_score:.2f})')

        blocked_regimes = rules.get('blocked_regimes', [])
        if regime and regime in blocked_regimes:
            return (f'Vault constraint: {strategy}/{pair} '
                    f'blocked in {regime} regime (learned from losses)')
    except Exception:
        pass
    return None


def evaluate_trade(trade_proposal) -> dict:
    """
    Main gate function called by strategies.
    Returns dict with decision and reasoning.
    """
    if not SKEPTIC_ENABLED:
        return {"decision": "ALLOW", "source": "gate_disabled"}

    # Ensure logs directory exists
    os.makedirs(os.path.dirname(SKEPTIC_LOG_PATH), exist_ok=True)

    # Fast vault-constraint check before running the full orchestrator
    constraint_block = _check_vault_constraints(
        pair=trade_proposal.get('pair', ''),
        strategy=trade_proposal.get('strategy', ''),
        sentiment_score=float(trade_proposal.get('sentiment_score', 0.0)),
        regime=trade_proposal.get('hmm_regime', ''),
    )
    if constraint_block:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat() + 'Z',
            "pair": trade_proposal.get('pair'),
            "strategy": trade_proposal.get('strategy'),
            "decision": "BLOCK",
            "failure_confidence": 0.80,
            "primary_concern": constraint_block,
            "reasons": [constraint_block],
        }
        with open(SKEPTIC_LOG_PATH, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
        return {
            "decision": "BLOCK",
            "failure_confidence": 0.80,
            "primary_concern": constraint_block,
            "reasons": [constraint_block],
            "source": "vault_constraint",
        }

    # Run LangGraph Orchestrator
    try:
        from orchestrator import run_orchestrator
        gate_result = run_orchestrator(trade_proposal)
        if gate_result.get('source') == 'error':
            raise Exception(gate_result.get('primary_concern', 'Unknown orchestrator error'))
    except Exception as e:
        regime = trade_proposal.get('hmm_regime', 'RANGING')
        sentiment_score = trade_proposal.get('sentiment_score', 0.0)
        if regime == 'BULL' and sentiment_score > 0.0:
            fallback_decision = "ALLOW"
            fallback_confidence = 0.4
            fallback_concern = f"Orchestrator error ({e}) - Allowed on BULLISH regime fallback"
        else:
            fallback_decision = "BLOCK"
            fallback_confidence = 0.9
            fallback_concern = f"Orchestrator error ({e}) - Blocked to preserve capital in non-BULL ({regime}) or negative sentiment ({sentiment_score:.2f}) regime"
            
        gate_result = {
            "decision": fallback_decision,
            "failure_confidence": fallback_confidence,
            "reasons": [f"Orchestrator error: {str(e)}"],
            "primary_concern": fallback_concern,
            "source": "fail_closed_fallback"
        }
    
    decision = gate_result.get('decision', 'ALLOW')
    confidence = gate_result.get('failure_confidence', 0.3)
    reasons = gate_result.get('reasons', [])
    concern = gate_result.get('primary_concern', '')
    source = gate_result.get('source', 'langgraph_orchestrator')
    
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
ORCHESTRATOR BLOCK:
Pair: {trade_proposal.get('pair')}
Strategy: {trade_proposal.get('strategy')}
Confidence trade fails: {confidence:.0%}
Primary concern: {concern}
Reasons: {'; '.join(reasons)}
"""
            add_entry("trade_memory", content, {
                "timestamp": log_entry["timestamp"],
                "category": "orchestrator_block",
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
        "source": source
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
                    except Exception as e: pass
        
        return output
    except Exception as e:
        return f"Error loading skeptic stats: {e}"

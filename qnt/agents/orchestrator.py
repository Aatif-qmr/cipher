import os
import json
import sys
from typing import TypedDict, Dict, Any, List
from pathlib import Path
from dotenv import load_dotenv

# LangGraph imports
from langgraph.graph import StateGraph, START, END

# Mistral imports
from mistralai.client import Mistral

# Add paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR / 'qnt/vault'))
sys.path.insert(0, str(BASE_DIR / 'sentiment'))

from vault import recall_lessons

# Load env variables for MISTRAL_API_KEY
load_dotenv(BASE_DIR / '.env')

class AgentState(TypedDict):
    trade_proposal: Dict[str, Any]
    analyst_input: str
    skeptic_critique: str
    obi_snapshot: str
    final_decision: str
    reasoning: List[str]
    metadata: Dict[str, Any]

def get_mistral_client():
    api_key = os.getenv("MISTRAL_API_KEY")
    return Mistral(api_key=api_key, server_url="https://codestral.mistral.ai")

def analyst_agent(state: AgentState):
    """Summarizes technicals and sentiment into a bullish/bearish thesis."""
    proposal = state["trade_proposal"]
    client = get_mistral_client()
    
    prompt = f"""You are the Lead Analyst.
Evaluate this trade: {json.dumps(proposal)}
Consider Technicals (RSI, Vol, Regime) and Macro Sentiment.
Provide a concise 'Bull Case' thesis."""
    
    try:
        response = client.chat.complete(
            model="codestral-latest",
            messages=[{"role": "user", "content": prompt}]
        )
        content = response.choices[0].message.content
    except Exception as e:
        content = f"Analyst error: {e}"
    
    return {"analyst_input": content}

def skeptic_agent(state: AgentState):
    """Finds flaws in the analyst's thesis and identifies historical failure modes."""
    proposal = state["trade_proposal"]
    analyst_input = state["analyst_input"]
    pair = proposal.get('pair', 'Unknown')
    strategy = proposal.get('strategy', 'Unknown')
    
    # Vault history for actual Cynicism
    vault_context = "No relevant failure history."
    try:
        results = recall_lessons(f"{strategy} {pair} loss failure", n_results=3)
        if results:
            vault_context = "\n".join([r.get("document", "")[:200] for r in results])
    except:
        pass
        
    client = get_mistral_client()
    prompt = f"""You are the Chief Skeptic.
Challenge the Analyst's thesis: {analyst_input}
Proposed Trade: {json.dumps(proposal)}
Vault Failures: {vault_context}

Identify 2-3 specific reasons this trade might fail. Be cynical."""
    
    try:
        response = client.chat.complete(
            model="codestral-latest",
            messages=[{"role": "user", "content": prompt}]
        )
        content = response.choices[0].message.content
    except Exception as e:
        content = f"Skeptic error: {e}"
        
    return {"skeptic_critique": content}

def obi_observer_agent(state: AgentState):
    """Provides high-frequency order book imbalance context."""
    proposal = state["trade_proposal"]
    symbol = proposal.get('pair', '').replace('/', '').lower()
    state_file = BASE_DIR / "qnt/oracle/order_flow_state.json"
    
    obi_snapshot = "OBI Data Unavailable"
    if state_file.exists():
        try:
            with open(state_file, 'r') as f:
                data = json.load(f)
            obi_data = data.get("obi_pipeline", {}).get(symbol, {})
            if obi_data:
                obi_snapshot = f"OBI: {obi_data.get('obi')} ({obi_data.get('imbalance_side')}), Spread: {obi_data.get('spread_pct')}%"
        except:
            pass
            
    return {"obi_snapshot": obi_snapshot}

def portfolio_manager_agent(state: AgentState):
    """Synthesizes the debate and makes the final execution decision."""
    client = get_mistral_client()
    
    prompt = f"""You are the Portfolio Manager.
Synthesize the debate:
Analyst Bull Case: {state['analyst_input']}
Skeptic Critique: {state['skeptic_critique']}
OBI Snapshot: {state['obi_snapshot']}

Make a final ALLOW or BLOCK decision.
Output JSON:
{{
  "decision": "ALLOW" or "BLOCK",
  "reasoning": ["point1", "point2"],
  "primary_concern": "summary"
}}
"""
    try:
        response = client.chat.complete(
            model="codestral-latest",
            messages=[{"role": "user", "content": prompt}]
        )
        res_text = response.choices[0].message.content.strip()
        if res_text.startswith("```json"): res_text = res_text[7:]
        if res_text.startswith("```"): res_text = res_text[3:]
        if res_text.endswith("```"): res_text = res_text[:-3]
        
        data = json.loads(res_text.strip())
        decision = data.get("decision", "ALLOW")
        reasons = data.get("reasoning", [])
        concern = data.get("primary_concern", "Debate complete.")
    except Exception as e:
        decision = "ALLOW"
        reasons = [f"Synthesis failed: {e}"]
        concern = "Technical error in PM synthesis."
        
    return {
        "final_decision": decision, 
        "reasoning": reasons,
        "metadata": {"primary_concern": concern}
    }

# Build Graph
builder = StateGraph(AgentState)
builder.add_node("analyst", analyst_agent)
builder.add_node("skeptic", skeptic_agent)
builder.add_node("obi_observer", obi_observer_agent)
builder.add_node("portfolio_manager", portfolio_manager_agent)

# Workflow: Analyst first -> Then concurrent Skeptic and OBI -> Finally PM
builder.add_edge(START, "analyst")
builder.add_edge("analyst", "skeptic")
builder.add_edge("analyst", "obi_observer")
builder.add_edge("skeptic", "portfolio_manager")
builder.add_edge("obi_observer", "portfolio_manager")
builder.add_edge("portfolio_manager", END)

orchestrator_graph = builder.compile()

def run_orchestrator(trade_proposal: dict) -> dict:
    initial_state = {
        "trade_proposal": trade_proposal,
        "analyst_input": "",
        "skeptic_critique": "",
        "obi_snapshot": "",
        "final_decision": "ALLOW",
        "reasoning": [],
        "metadata": {}
    }
    
    try:
        final_state = orchestrator_graph.invoke(initial_state)
        return {
            "decision": final_state.get("final_decision", "ALLOW"),
            "primary_concern": final_state.get("metadata", {}).get("primary_concern", ""),
            "reasons": final_state.get("reasoning", []),
            "source": "langgraph_orchestrator"
        }
    except Exception as e:
        return {
            "decision": "ALLOW",
            "primary_concern": f"Orchestrator error: {e}",
            "reasons": [str(e)],
            "source": "error"
        }

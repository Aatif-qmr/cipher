import json
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import os

# Machine-agnostic path setup
HOME = Path.home()
BASE_DIR = HOME / 'masterbot'

def load_hmm_model():
    """Load HMM model from M2 via SCP if not cached locally."""
    local_path = BASE_DIR / "qnt/oracle/hmm_model.pkl"
    m2_path = "/Users/azmatsaif/masterbot/qnt/oracle/hmm_model.pkl"
    m2_ip = "100.74.110.36"
    
    if not local_path.exists():
        import subprocess
        try:
            # Try to fetch from M2
            subprocess.run([
                "scp", 
                f"azmatsaif@{m2_ip}:{m2_path}",
                str(local_path)
            ], check=True, timeout=30)
        except Exception as e:
            print(f"Error loading HMM model from M2: {e}")
            return None
    try:
        return joblib.load(local_path)
    except:
        # Fallback to pickle if joblib fails (since the other machine might use pickle)
        import pickle
        try:
            with open(local_path, 'rb') as f:
                return pickle.load(f)
        except:
            return None

def detect_regime(dataframe: pd.DataFrame, pair: str = "BTC/USDT") -> str:
    """
    Returns: 'BULL', 'BEAR', or 'RANGING'
    Uses last 100 candles of 1m data for micro-scalp context.
    """
    model_data = load_hmm_model()
    if model_data is None:
        return "RANGING"  # Safe default
    
    # Handle both raw model and payload dict
    if isinstance(model_data, dict):
        model = model_data.get('model')
        state_map = model_data.get('state_map')
    else:
        model = model_data
        state_map = {0: "BEAR", 1: "RANGING", 2: "BULL"} # Default map for 3-state
    
    if model is None:
        return "RANGING"

    try:
        # Use log returns as feature
        # Ensure we have enough data
        if len(dataframe) < 10:
            return "RANGING"
            
        returns = np.log(dataframe["close"] / dataframe["close"].shift(1)).dropna().values[-100:].reshape(-1, 1)
        if len(returns) < 10:
            return "RANGING"
        
        # Predict most likely state
        states = model.predict(returns)
        state_counts = np.bincount(states)
        dominant_state = np.argmax(state_counts)
        
        # Map HMM state to regime label
        # If we have a state_map from the sophisticated training, use it.
        # Otherwise use the default 3-state map.
        if state_map:
            # Convert sophisticated names to BULL/BEAR/RANGING for simplicity
            res = state_map.get(dominant_state, "RANGING")
            if res == "TRENDING_UP": return "BULL"
            if res == "TRENDING_DOWN": return "BEAR"
            if res == "VOLATILE": return "BEAR" # Volatile is risky
            return "RANGING"
            
        regime_map = {0: "BEAR", 1: "RANGING", 2: "BULL"}
        return regime_map.get(dominant_state, "RANGING")
    except Exception as e:
        print(f"HMM Detection Error: {e}")
        return "RANGING"

def get_regime_for_strategy(strategy_name: str, current_regime: str) -> bool:
    """
    Returns True if strategy should trade in current regime.
    MicroScalpV1: trades in all regimes but reduces size in BEAR
    """
    if strategy_name == "MicroScalpV1":
        return True  # Always allowed, size adjusted elsewhere
    if strategy_name in ["MeanReversionV1", "ScalpV1"]:
        return current_regime != "BULL"  # Mean-rev underperforms in strong trends
    if strategy_name in ["TrendFollowV1", "DailyTrendV1"]:
        return current_regime != "RANGING"  # Trend strategies need direction
    return True

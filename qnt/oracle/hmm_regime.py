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

_regime_cache: dict = {}   # pair → (regime, expires_at)
_REGIME_CACHE_TTL = 300    # 5 minutes per pair


def detect_regime(dataframe: pd.DataFrame, pair: str = "BTC/USDT") -> str:
    """
    Returns: 'BULL', 'BEAR', or 'RANGING'
    Uses last 100 candles of the pair's own data. Cached per-pair for 5 min.
    """
    import time
    cached = _regime_cache.get(pair)
    if cached and time.time() < cached[1]:
        return cached[0]

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
        if state_map:
            res = state_map.get(dominant_state, "RANGING")
            if res == "TRENDING_UP": result = "BULL"
            elif res == "TRENDING_DOWN": result = "BEAR"
            elif res == "VOLATILE": result = "BEAR"
            else: result = "RANGING"
        else:
            regime_map = {0: "BEAR", 1: "RANGING", 2: "BULL"}
            result = regime_map.get(dominant_state, "RANGING")

        import time
        _regime_cache[pair] = (result, time.time() + _REGIME_CACHE_TTL)
        return result
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
    if strategy_name == "SwingV1":
        return current_regime == "BULL"  # EMA crossovers need a trending bull market
    if strategy_name == "BearScalpV1":
        return current_regime == "BEAR"  # Short-only strategy
    return True


_REGIME_LABELS = {0: "BEAR", 1: "RANGING", 2: "BULL"}

def detect_regime_full(dataframe: pd.DataFrame, pair: str = "BTC/USDT") -> dict:
    """
    Returns current + predicted next regime with confidence.
    Routes to the high-performance ONNX Runtime implementation.
    """
    try:
        from qnt.oracle.onnx_inference import detect_regime_onnx
        return detect_regime_onnx(dataframe, pair)
    except Exception as e:
        print(f"Error routing to ONNX regime inference: {e}")
        current = detect_regime(dataframe, pair)
        return {"current_regime": current, "next_regime": current, "confidence": 0.5}

import pandas as pd
import numpy as np

def summarize_signal(dataframe: pd.DataFrame, strategy_name: str, pair: str) -> dict:
    """
    From the last candle of the dataframe extract key technical context.
    """
    last = dataframe.iloc[-1]
    
    # Extract common indicators if present, otherwise default to 0
    rsi = float(last.get('rsi', last.get('rsi_1m', 0.0)))
    
    # BB Position logic
    bb_lower = last.get('bb_lower', last.get('bb_lower_1m'))
    bb_upper = last.get('bb_upper', last.get('bb_upper_1m'))
    close = last.get('close', 0.0)
    
    bb_pos = "within_bands"
    if bb_lower and close <= bb_lower:
        bb_pos = "below_lower"
    elif bb_upper and close >= bb_upper:
        bb_pos = "above_upper"
        
    # Volume ratio
    vol = last.get('volume', 0.0)
    vol_avg = last.get('volume_avg', last.get('volume_avg_20', 1.0))
    vol_ratio = float(vol / vol_avg) if vol_avg > 0 else 1.0
    
    # Signal strength and reasons
    conditions = []
    if bb_pos == "below_lower": conditions.append("Price < lower BB")
    if rsi < 35: conditions.append(f"RSI {rsi:.1f} < 35")
    if vol_ratio > 1.5: conditions.append(f"Volume spike {vol_ratio:.1f}x")
    
    # Simplified strength
    strength = "weak"
    if len(conditions) >= 3: strength = "strong"
    elif len(conditions) >= 2: strength = "medium"
    
    return {
        "pair": pair,
        "strategy": strategy_name,
        "direction": "LONG", # Default to LONG as these strategies currently are long-only
        "rsi": rsi,
        "bb_position": bb_pos,
        "volume_ratio": vol_ratio,
        "signal_strength": strength,
        "conditions_met": conditions,
        "entry_price": float(close),
    }

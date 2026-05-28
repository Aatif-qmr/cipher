import numpy as np
import pandas as pd
from freqtrade.strategy import IStrategy
import ta
import rust_engine  # Native Rust PyO3 Module!

class VectorVaultV1(IStrategy):
    """
    Institutional-Grade Vector Pattern Matcher.
    Uses native Rust engine to perform ultra-fast Euclidean similarity matching 
    against a historical vault of market states.
    """
    
    INTERFACE_VERSION = 3
    timeframe = '15m'
    
    # ROI table:
    minimal_roi = {
        "0": 0.15,
        "30": 0.05,
        "60": 0.02,
        "120": 0
    }

    # Stoploss:
    stoploss = -0.05
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.02
    trailing_only_offset_is_reached = True

    # Vector Vault Parameters
    VAULT_LOOKBACK = 1000  # Number of historical states to keep in memory
    FORWARD_PREDICTION = 5  # How many candles ahead to check for success
    
    # For caching historical states to avoid recalculating
    historical_matrix = None
    historical_outcomes = None

    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        # Calculate base features for our vector
        dataframe['rsi'] = ta.momentum.rsi(dataframe['close'], window=14)
        macd = ta.trend.macd(dataframe['close'])
        dataframe['macd'] = macd
        
        # Volatility feature
        dataframe['bb_width'] = (
            ta.volatility.bollinger_hband(dataframe['close']) - 
            ta.volatility.bollinger_lband(dataframe['close'])
        ) / dataframe['close']
        
        # Future outcome (did the price go up N candles later?)
        dataframe['future_return'] = dataframe['close'].shift(-self.FORWARD_PREDICTION) / dataframe['close'] - 1
        
        # Drop NaN
        dataframe.fillna(0, inplace=True)
        
        # Feature columns that make up our "State Vector"
        feature_cols = ['rsi', 'macd', 'bb_width']
        
        # Convert to numpy arrays for fast row-based access
        feature_matrix = dataframe[feature_cols].values.astype(np.float64)
        future_returns = dataframe['future_return'].values
        
        # Single batch call into Rust — eliminates O(n) FFI overhead.
        # find_all_closest_matches handles the windowing loop in parallel via rayon.
        try:
            rust_predictions = rust_engine.find_all_closest_matches(
                feature_matrix.tolist(),
                future_returns.tolist(),
                self.FORWARD_PREDICTION,
                self.VAULT_LOOKBACK,
            )
        except Exception as e:
            print(f"Rust Engine Error: {e}")
            rust_predictions = [0.0] * len(dataframe)
        
        dataframe['rust_prediction'] = rust_predictions
        return dataframe

    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        dataframe.loc[
            (
                # If the most mathematically similar historical moment resulted in a >1% profit
                (dataframe['rust_prediction'] > 0.01) & 
                (dataframe['volume'] > 0)
            ),
            'enter_long'] = 1
            
        return dataframe

    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        dataframe.loc[
            (
                # If the most similar historical moment resulted in a crash
                (dataframe['rust_prediction'] < -0.01) &
                (dataframe['volume'] > 0)
            ),
            'exit_long'] = 1

        return dataframe

import sys
import os
import logging
import json
from pathlib import Path
from datetime import timedelta, datetime
from pandas import DataFrame
import pandas_ta as ta

from freqtrade.strategy import IStrategy
from freqtrade.persistence import Trade

# Add MasterBot root directory to sys.path for custom module access
sys.path.insert(0, '/Users/aatifquamre/masterbot')

# Import MasterBot Risk and Sentiment modules
from risk.risk_manager import run_all_checks
from sentiment.reader import get_current_sentiment, get_sentiment_signal

logger = logging.getLogger(__name__)

class Auto202605030226(IStrategy):
    """
    Strategy: Auto202605030226
    Hypothesis: Buy SOL when price bounces from 200 EMA with RSI below 40.
    
    Logic:
    - Indicator: 200-period Exponential Moving Average (EMA) to define the long-term trend.
    - Indicator: 14-period Relative Strength Index (RSI) to identify oversold conditions.
    - Entry: Occurs when price is above the 200 EMA (bullish context), but the current candle's 
      low touched or crossed the EMA (the 'bounce'), provided RSI is below 40.
    - Exit: Basic RSI overbought threshold (70).
    - Safety: Integrated with MasterBot's central Risk Manager and Sentiment Gate.
    """

    INTERFACE_VERSION = 3
    
    # Strategy timeframe (standard 1h for bounce plays)
    timeframe = '1h'

    # Risk Management Settings
    stoploss = -0.04
    stoploss_on_exchange = True
    
    # Required warmup period for the 200 EMA
    startup_candle_count: int = 200

    # Minimal ROI table
    minimal_roi = {
        "0": 0.1,
        "60": 0.05,
        "120": 0.02,
        "240": 0
    }

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Calculates indicators using pandas_ta.
        """
        # Calculate 200 Period EMA
        dataframe['ema200'] = ta.ema(dataframe['close'], length=200)
        
        # Calculate 14 Period RSI
        dataframe['rsi'] = ta.rsi(dataframe['close'], length=14)
        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Defines the entry signal based on the EMA bounce hypothesis.
        """
        dataframe.loc[
            (
                # Condition 1: RSI is below 40 (Oversold/Bottoming territory)
                (dataframe['rsi'] < 40) &
                
                # Condition 2: Price is currently closing above the 200 EMA (Bullish trend)
                (dataframe['close'] > dataframe['ema200']) &
                
                # Condition 3: Price touched or dipped below the 200 EMA during the candle (The Bounce)
                (dataframe['low'] <= dataframe['ema200'])
            ),
            'enter_long'] = 1
            
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Defines the exit signal.
        """
        dataframe.loc[
            (
                # Exit when RSI becomes overbought
                (dataframe['rsi'] > 70)
            ),
            'exit_long'] = 1
            
        return dataframe

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                            time_in_force: str, current_time: datetime, entry_tag: str,
                            side: str, **kwargs) -> bool:
        """
        MasterBot Gatekeeper: Performs final validation using Risk and Sentiment modules.
        """
        
        # --- LAYER 1: SENTIMENT GATE ---
        try:
            # Block entry if global market sentiment is BEARISH
            sentiment_signal = get_sentiment_signal()
            if sentiment_signal == 'BEARISH':
                logger.info(f"[GATE] {pair} entry blocked: Sentiment signal is BEARISH.")
                return False
        except Exception as e:
            logger.error(f"[GATE] Sentiment check failed: {e}")

        # --- LAYER 2: RISK MANAGER GATE ---
        try:
            # 1. Gather current wallet and trade data
            total_balance = self.wallets.get_total('USDT')
            
            # 2. Extract recent trade history for the risk manager
            recent_trades = [
                {'profit_ratio': t.profit_ratio, 'close_date': t.close_date} 
                for t in Trade.get_trades_proxy(is_open=False)
            ][:10]
            
            # 3. Calculate trade frequency in the last hour
            one_hour_ago = current_time - timedelta(hours=1)
            trades_last_hour = len([
                t for t in Trade.get_trades_proxy(is_open=False)
                if t.close_date and t.close_date >= one_hour_ago
            ])
            
            # 4. Load balance baselines from the project's risk state file
            state_file = Path('/Users/aatifquamre/masterbot/risk/balance_state.json')
            if state_file.exists():
                with open(state_file) as f:
                    state = json.load(f)
                start_of_day = state.get('start_of_day', total_balance)
                start_of_week = state.get('start_of_week', total_balance)
            else:
                start_of_day = total_balance
                start_of_week = total_balance
            
            # 5. Execute centralized risk checks
            risk_result = run_all_checks(
                current_balance=total_balance,
                start_of_day_balance=start_of_day,
                start_of_week_balance=start_of_week,
                trade_amount_usdt=amount * rate,
                trades_last_hour=trades_last_hour,
                recent_trades=recent_trades
            )
            
            if not risk_result.get('safe_to_trade', False):
                logger.info(f"[GATE] {pair} blocked by Risk Manager. Reasons: {risk_result.get('blocking_reasons')}")
                return False
                
        except Exception as e:
            logger.error(f"[GATE] Risk Manager execution error: {e}")
            # Fail-safe: block trade if risk check cannot be completed
            return False

        return True
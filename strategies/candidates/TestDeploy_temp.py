import logging
import json
import sys
import os
from pathlib import Path
from datetime import timedelta, datetime
from pandas import DataFrame
import pandas_ta as ta
import numpy as np

from freqtrade.strategy import IStrategy
from freqtrade.persistence import Trade

# Add base directory to path for custom imports
sys.path.insert(0, '/Users/aatifquamre/masterbot')
from risk.risk_manager import run_all_checks
from sentiment.reader import get_current_sentiment, get_sentiment_signal

logger = logging.getLogger(__name__)

class Auto202605021439(IStrategy):
    """
    Hypothesis: Buy BTC when RSI drops below 32 and Bollinger Band width is contracting,
    sell when RSI recovers above 55.
    
    This strategy incorporates a sentiment gate and a multi-layer risk management system.
    """
    INTERFACE_VERSION = 3
    
    # Strategy settings
    timeframe = '1h'
    stoploss = -0.04
    stoploss_on_exchange = True
    
    # Startup candles requirement
    startup_candle_count: int = 30

    # Minimal ROI (disabled to rely on RSI exit signal, but included for Freqtrade safety)
    minimal_roi = {
        "0": 100  # High value to ensure RSI exit or Stoploss handles the exit
    }

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Calculates RSI and Bollinger Band Width using pandas_ta.
        """
        # RSI Indicator
        dataframe['rsi'] = ta.rsi(dataframe['close'], length=14)
        
        # Bollinger Bands
        bb = ta.bbands(dataframe['close'], length=20, std=2)
        # BBL_20_2.0, BBM_20_2.0, BBU_20_2.0, BBB_20_2.0
        # BBB is the BandWidth calculated by pandas_ta: (Upper - Lower) / Middle
        dataframe['bbw'] = bb['BBB_20_2.0']
        
        # Detect contraction: current width is less than previous candle width
        dataframe['bbw_contracting'] = dataframe['bbw'] < dataframe['bbw'].shift(1)
        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Entry Signal: RSI < 32 AND BB Width is contracting.
        """
        dataframe.loc[
            (
                (dataframe['rsi'] < 32) & 
                (dataframe['bbw_contracting'] == True) &
                (dataframe['volume'] > 0)  # Guard against empty candles
            ),
            'enter_long'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Exit Signal: RSI > 55.
        """
        dataframe.loc[
            (
                (dataframe['rsi'] > 55)
            ),
            'exit_long'] = 1
        return dataframe

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                            time_in_force: str, current_time: datetime, entry_tag: str,
                            side: str, **kwargs) -> bool:
        """
        Final confirmation layer before order placement.
        Checks Risk Management rules and Sentiment Score.
        """
        
        # --- LAYER 1: RISK MANAGER INTEGRATION ---
        try:
            total_balance = self.wallets.get_total('USDT')
            
            # Fetch last 10 closed trades for loss counting
            recent_trades = [
                {'profit_ratio': t.profit_ratio, 'close_date': t.close_date} 
                for t in Trade.get_trades_proxy(is_open=False)
            ][:10]
            
            # Count trades closed in the last hour
            one_hour_ago = current_time - timedelta(hours=1)
            trades_last_hour = len([
                t for t in Trade.get_trades_proxy(is_open=False)
                if t.close_date and t.close_date >= one_hour_ago
            ])
            
            # Load baseline balances from shared state for drawdown calculation
            state_file = Path('/Users/aatifquamre/masterbot/risk/balance_state.json')
            if state_file.exists():
                with open(state_file) as f:
                    state = json.load(f)
                start_of_day = state.get('start_of_day', total_balance)
                start_of_week = state.get('start_of_week', total_balance)
            else:
                start_of_day = total_balance
                start_of_week = total_balance
            
            # Execute all hard risk checks
            risk_result = run_all_checks(
                current_balance=total_balance,
                start_of_day_balance=start_of_day,
                start_of_week_balance=start_of_week,
                trade_amount_usdt=amount * rate,
                trades_last_hour=trades_last_hour,
                recent_trades=recent_trades
            )
            
            if not risk_result['safe_to_trade']:
                logger.info(f"[RISK BLOCK] {pair} blocked. Reasons: {risk_result['blocking_reasons']}")
                return False
                
        except Exception as e:
            logger.error(f"[RISK ERROR] Failed to run risk checks: {e}")
            # In case of risk engine failure, we block for safety
            return False

        # --- LAYER 2: SENTIMENT GATE ---
        # Blocks entry if the market sentiment is BEARISH (score <= -0.3)
        sentiment = get_current_sentiment()
        signal = get_sentiment_signal()
        
        if signal == 'BEARISH':
            logger.info(f"[SENTIMENT BLOCK] {pair} blocked. Sentiment score {sentiment['score']:.3f} is BEARISH.")
            return False
            
        return True
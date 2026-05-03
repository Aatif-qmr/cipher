import sys
import os
import logging
import json
from datetime import datetime, timedelta
from pathlib import Path
from pandas import DataFrame
import pandas_ta as ta

from freqtrade.strategy import IStrategy
from freqtrade.persistence import Trade

# Add project root to path for custom imports
sys.path.insert(0, '/Users/aatifquamre/masterbot')

from risk.risk_manager import run_all_checks
from sentiment.reader import get_current_sentiment, get_sentiment_signal

logger = logging.getLogger(__name__)

class Auto202605030151(IStrategy):
    """
    Hypothesis: Buy SOL when price bounces from 200 EMA with RSI below 40.
    
    Logic:
    - EMA 200: Acts as a dynamic support level and trend indicator.
    - Bounce: Price touches or dips slightly below EMA 200 but closes above it.
    - RSI < 40: Ensures entry is not overbought and suggests a potential reversal.
    - Sentiment: Blocks entries if market sentiment is bearish (Gate integration).
    - Risk: Integrates mandatory risk checks including drawdown and position size limits.
    """

    INTERFACE_VERSION = 3

    # Strategy timeframe
    timeframe = '1h'

    # Stoploss configuration
    stoploss = -0.04
    stoploss_on_exchange = True

    # ROI settings
    minimal_roi = {
        "0": 0.1,      # 10% profit
        "60": 0.05,    # 5% after 1 hour
        "120": 0.02,   # 2% after 2 hours
        "240": 0       # Exit at profit after 4 hours
    }

    # Number of candles required before starting
    startup_candle_count: int = 200

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Calculate indicators using pandas_ta.
        """
        # 200 EMA - Long term trend / Dynamic Support
        dataframe['ema_200'] = ta.ema(dataframe['close'], length=200)
        
        # 14 RSI - Momentum indicator
        dataframe['rsi'] = ta.rsi(dataframe['close'], length=14)
        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Define entry conditions based on the bounce hypothesis.
        """
        dataframe.loc[
            (
                # Price bounce condition: 
                # Current close is above EMA 200 and low was at or below EMA 200
                (dataframe['close'] > dataframe['ema_200']) & 
                (dataframe['low'] <= dataframe['ema_200']) &
                
                # RSI filter
                (dataframe['rsi'] < 40) &
                
                # Basic volume check
                (dataframe['volume'] > 0)
            ),
            'enter_long'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Define exit conditions.
        """
        # Exit if RSI becomes overbought or standard ROI/Stoploss hits
        dataframe.loc[
            (
                (dataframe['rsi'] > 75)
            ),
            'exit_long'] = 1
            
        return dataframe

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                            time_in_force: str, current_time: datetime, entry_tag: str,
                            side: str, **kwargs) -> bool:
        """
        Mandatory validation layer including Sentiment Gate and Risk Manager integration.
        """
        
        # 1. SENTIMENT GATE
        # Blocks entry if sentiment is BEARISH (score <= -0.3)
        try:
            signal = get_sentiment_signal()
            if signal == 'BEARISH':
                logger.info(f"[SENTIMENT BLOCK] {pair} entry blocked. Signal is BEARISH.")
                return False
        except Exception as e:
            logger.error(f"[SENTIMENT ERROR] Failed to check sentiment: {e}")

        # 2. RISK MANAGER INTEGRATION
        # Runs all 5 mandatory risk checks before placing the order
        try:
            # Fetch current balance metrics
            total_balance = self.wallets.get_total('USDT')
            
            # Fetch recent trades for loss counting
            recent_trades = [
                {'profit_ratio': t.profit_ratio, 'close_date': t.close_date} 
                for t in Trade.get_trades_proxy(is_open=False)
            ][:10]
            
            # Calculate order rate
            one_hour_ago = current_time - timedelta(hours=1)
            trades_last_hour = len([
                t for t in Trade.get_trades_proxy(is_open=False)
                if t.close_date and t.close_date >= one_hour_ago
            ])
            
            # Load drawdown reference state
            state_file = Path('/Users/aatifquamre/masterbot/risk/balance_state.json')
            if state_file.exists():
                with open(state_file) as f:
                    state = json.load(f)
                start_of_day = state.get('start_of_day', total_balance)
                start_of_week = state.get('start_of_week', total_balance)
            else:
                start_of_day = total_balance
                start_of_week = total_balance
            
            # Execute all risk checks
            risk_result = run_all_checks(
                current_balance=total_balance,
                start_of_day_balance=start_of_day,
                start_of_week_balance=start_of_week,
                trade_amount_usdt=amount * rate,
                trades_last_hour=trades_last_hour,
                recent_trades=recent_trades
            )
            
            if not risk_result['safe_to_trade']:
                logger.info(f"[RISK BLOCK] {pair} entry blocked. Reasons: {risk_result['blocking_reasons']}")
                return False
                
        except Exception as e:
            logger.error(f"[RISK ERROR] Exception during risk validation for {pair}: {e}")
            return False # Default to fail-safe
            
        return True
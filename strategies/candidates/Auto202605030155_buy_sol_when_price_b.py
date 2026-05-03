import sys
import os
import logging
import json
from pathlib import Path
from datetime import timedelta, datetime
from pandas import DataFrame
import pandas_ta as ta
import numpy as np

# Freqtrade imports
from freqtrade.strategy import IStrategy
from freqtrade.persistence import Trade

# Mandatory Path Inserts for MasterBot Integration
sys.path.insert(0, '/Users/aatifquamre/masterbot')

# Risk Manager and Sentiment Gate Imports
from risk.risk_manager import run_all_checks
from sentiment.reader import get_current_sentiment, get_sentiment_signal

logger = logging.getLogger(__name__)

class Auto202605030155(IStrategy):
    """
    Auto-generated Strategy for MasterBot
    Hypothesis: Buy SOL when price bounces from 200 EMA with RSI below 40
    """
    INTERFACE_VERSION = 3
    
    # Strategy settings
    timeframe = '1h'
    stoploss = -0.04
    stoploss_on_exchange = True
    
    # Minimal ROI (Standard targets, can be adjusted via hyperopt)
    minimal_roi = {
        "0": 0.1,      # 10% profit immediately
        "30": 0.05,    # 5% after 30 minutes
        "60": 0.02,    # 2% after an hour
        "120": 0       # Exit at breakeven if stalled
    }

    # Startup candles needed for 200 EMA
    startup_candle_count: int = 200

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Calculate indicators using pandas_ta
        """
        # 200-period Exponential Moving Average
        dataframe['ema200'] = ta.ema(dataframe['close'], length=200)
        
        # 14-period Relative Strength Index
        dataframe['rsi'] = ta.rsi(dataframe['close'], length=14)
        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Define entry conditions based on the hypothesis:
        - Price 'bounces' from 200 EMA (Low is below/at EMA, Close is above EMA)
        - RSI is below 40 (Oversold/Weakness territory)
        """
        dataframe.loc[
            (
                # Bounce Logic: Candle touched or pierced the 200 EMA but closed above it
                (dataframe['low'] <= dataframe['ema200']) &
                (dataframe['close'] > dataframe['ema200']) &
                
                # RSI Logic: Low momentum / Oversold signal
                (dataframe['rsi'] < 40) &
                
                # Ensure we have data for the indicator
                (dataframe['ema200'] > 0)
            ),
            'enter_long'] = 1
            
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Define exit conditions. 
        Using a standard RSI overbought signal for mean reversion exit.
        """
        dataframe.loc[
            (
                (dataframe['rsi'] > 70)  # Standard overbought exit
            ),
            'exit_long'] = 1
            
        return dataframe

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                            time_in_force: str, current_time: datetime, entry_tag: str,
                            side: str, **kwargs) -> bool:
        """
        MasterBot specific validation layers:
        1. Risk Manager: Checks drawdown limits, circuit breakers, and position sizing.
        2. Sentiment Gate: Prevents entries during BEARISH market regimes.
        """
        
        # --- LAYER 1: RISK MANAGER INTEGRATION ---
        try:
            total_balance = self.wallets.get_total('USDT')
            
            # Retrieve recent trade history for risk calculations (losses/frequency)
            recent_trades = [
                {'profit_ratio': t.profit_ratio, 'close_date': t.close_date} 
                for t in Trade.get_trades_proxy(is_open=False)
            ][:10]
            
            # Count trade frequency in the last hour
            one_hour_ago = current_time - timedelta(hours=1)
            trades_last_hour = len([
                t for t in Trade.get_trades_proxy(is_open=False)
                if t.close_date and t.close_date >= one_hour_ago
            ])
            
            # Load balance state for drawdown tracking
            state_file = Path('/Users/aatifquamre/masterbot/risk/balance_state.json')
            if state_file.exists():
                with open(state_file) as f:
                    state = json.load(f)
                start_of_day = state.get('start_of_day', total_balance)
                start_of_week = state.get('start_of_week', total_balance)
            else:
                start_of_day = total_balance
                start_of_week = total_balance
            
            # Execute MasterBot Risk Check Suite
            risk_result = run_all_checks(
                current_balance=total_balance,
                start_of_day_balance=start_of_day,
                start_of_week_balance=start_of_week,
                trade_amount_usdt=amount * rate,
                trades_last_hour=trades_last_hour,
                recent_trades=recent_trades
            )
            
            if not risk_result['safe_to_trade']:
                logger.info(f"[RISK BLOCK] Entry for {pair} blocked: {risk_result['blocking_reasons']}")
                return False
                
        except Exception as e:
            logger.error(f"[RISK ERROR] Failed to execute risk checks for {pair}: {e}")
            return False

        # --- LAYER 2: SENTIMENT GATE INTEGRATION ---
        try:
            sentiment_signal = get_sentiment_signal()
            sentiment_data = get_current_sentiment()
            
            # Block entries if the global market sentiment is BEARISH
            if sentiment_signal == 'BEARISH':
                logger.info(f"[SENTIMENT BLOCK] {pair} entry blocked. Global Score: {sentiment_data['score']:.3f}")
                return False
                
        except Exception as e:
            logger.warning(f"[SENTIMENT WARNING] Could not verify sentiment for {pair}: {e}")
            # Security default: block if intelligence source is unavailable
            return False
            
        return True
import sys, os; home = os.path.expanduser('~'); sys.path.append(os.path.join(home, 'masterbot')); sys.path.append(os.path.join(home, 'masterbot', 'qnt', 'memory')); sys.path.append(os.path.join(home, 'masterbot', 'qnt', 'oracle'));
import logging
import json
import sys
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
from pandas import DataFrame
import pandas_ta as ta
import numpy as np

from freqtrade.strategy import IStrategy
from freqtrade.persistence import Trade

# Add base directory to path for custom imports
home = os.path.expanduser("~")
sys.path.append(os.path.join(home, 'masterbot'))
sys.path.append(os.path.join(home, 'masterbot', 'qnt', 'memory'))
from risk.risk_manager import run_all_checks
from sentiment.reader import get_current_sentiment
from qnt.oracle.oracle_calendar import is_safe_to_trade_today

logger = logging.getLogger(__name__)

class DailyTrendV1(IStrategy):
    """
    Daily trend following strategy.
    Entry: Price > 50-day EMA + RSI cross above 45 + Vol expansion
    Exit: RSI > 70 or Price < 50-day EMA
    """
    INTERFACE_VERSION = 3
    
    timeframe = '1d'
    
    stoploss = -0.08
    
    minimal_roi = {
        "0": 0.08,
        "7": 0.05,
        "3": 0.03
    }

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['ema_50'] = ta.ema(dataframe['close'], length=50)
        dataframe['rsi'] = ta.rsi(dataframe['close'], length=14)
        dataframe['volume_avg'] = ta.sma(dataframe['volume'], length=10)
        dataframe = merge_macro_data(dataframe)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        sentiment = get_current_sentiment()
        
        dataframe.loc[
            (
                (dataframe['close'] > dataframe['ema_50']) &
                (dataframe['rsi'] > 45) & (dataframe['rsi'].shift(1) <= 45) &
                (dataframe['volume'] > dataframe['volume_avg']) &
                (sentiment['score'] >= -0.3) & # Not BEARISH
                (is_safe_to_trade_today())    # Calendar Gate
            ),
            'enter_long'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['rsi'] > 70) |
                (dataframe['close'] < dataframe['ema_50'])
            ),
            'exit_long'] = 1
        return dataframe

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                           time_in_force: str, current_time: datetime, entry_tag: str,
                           side: str, **kwargs) -> bool:
        # --- LAYER 1: RISK CHECKS ---
        try:
            total_balance = self.wallets.get_total('USDT')
            
            # Fetch recent trades for loss counting
            recent_trades = [
                {'profit_ratio': t.profit_ratio, 'close_date': t.close_date} 
                for t in Trade.get_trades_proxy(is_open=False)
            ][:10]
            
            # Count trades in the last hour
            one_hour_ago = current_time - timedelta(hours=1)
            trades_last_hour = len([
                t for t in Trade.get_trades_proxy(is_open=False)
                if t.close_date and t.close_date >= one_hour_ago
            ])
            
            # Load balance state for drawdown checks
            state_file = Path('/Users/aatifquamre/masterbot/risk/balance_state.json')
            if state_file.exists():
                with open(state_file) as f:
                    state = json.load(f)
                start_of_day = state.get('start_of_day', total_balance)
                start_of_week = state.get('start_of_week', total_balance)
            else:
                start_of_day = total_balance
                start_of_week = total_balance
            
            risk_result = run_all_checks(
                current_balance=total_balance,
                start_of_day_balance=start_of_day,
                start_of_week_balance=start_of_week,
                trade_amount_usdt=amount * rate,
                trades_last_hour=trades_last_hour,
                recent_trades=recent_trades
            )
            
            if not risk_result['safe_to_trade']:
                logger.info(f"[RISK BLOCK] DailyTrend blocked for {pair}. Reasons: {risk_result['blocking_reasons']}")
                return False
        except Exception as e:
            logger.error(f"[RISK WARNING] Risk check error: {e}")
            
        return True

import sys, os; home = os.path.expanduser('~'); sys.path.insert(0, os.path.join(home, 'masterbot')); sys.path.insert(0, os.path.join(home, 'masterbot', 'qnt', 'memory')); sys.path.insert(0, os.path.join(home, 'masterbot', 'qnt', 'oracle'));
import logging
import json
import sys
import os
from datetime import datetime, timezone, timedelta
from pandas import DataFrame
import pandas_ta as ta
import numpy as np

from freqtrade.strategy import IStrategy
from freqtrade.persistence import Trade

# Add base directory to path for custom imports
home = os.path.expanduser("~")
sys.path.insert(0, os.path.join(home, 'masterbot'))
sys.path.insert(0, os.path.join(home, 'masterbot', 'qnt', 'memory'))
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
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        sentiment = get_current_sentiment()
        
        dataframe.loc[
            (
                (dataframe['close'] > dataframe['ema_50']) &
                (ta.cross_above(dataframe['rsi'], 45)) &
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
        return run_all_checks(pair, amount, rate)

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
from risk.risk_manager import run_all_checks
from sentiment.reader import get_current_sentiment

logger = logging.getLogger(__name__)

class SwingV1(IStrategy):
    """
    15-minute swing strategy.
    Entry: EMA 9 > EMA 21 + RSI 40-60
    Exit: EMA 9 < EMA 21 or Trailing Stop
    """
    INTERFACE_VERSION = 3
    
    timeframe = '15m'
    informative_timeframes = ['1h']
    
    stoploss = -0.03
    trailing_stop = True
    trailing_stop_positive = 0.015
    
    minimal_roi = {
        "0": 0.02,
        "120": 0.015,
        "60": 0.01
    }

    def informative_pairs(self):
        pairs = self.dp.current_whitelist()
        return [(pair, '1h') for pair in pairs]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 15m Indicators
        dataframe['ema_9'] = ta.ema(dataframe['close'], length=9)
        dataframe['ema_21'] = ta.ema(dataframe['close'], length=21)
        dataframe['rsi'] = ta.rsi(dataframe['close'], length=14)

        # 1h Informative
        if self.config['runmode'].value in ('live', 'dry_run'):
            inf_df = self.dp.get_pair_informative_data(metadata['pair'], '1h')
            inf_df['ema_50'] = ta.ema(inf_df['close'], length=50)
            dataframe = self.dp.merge_informative_data(dataframe, inf_df, self.timeframe, '1h', ffill=True)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        sentiment = get_current_sentiment()
        
        dataframe.loc[
            (
                (ta.cross_above(dataframe['ema_9'], dataframe['ema_21'])) &
                (dataframe['rsi'] >= 40) & (dataframe['rsi'] <= 60) &
                # HTF confirmation
                (dataframe.get('close', 0) > dataframe.get('ema_50_1h', 0)) &
                (sentiment['score'] >= -0.3) # Not BEARISH
            ),
            'enter_long'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (ta.cross_below(dataframe['ema_9'], dataframe['ema_21']))
            ),
            'exit_long'] = 1
        return dataframe

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                           time_in_force: str, current_time: datetime, entry_tag: str,
                           side: str, **kwargs) -> bool:
        return run_all_checks(pair, amount, rate)

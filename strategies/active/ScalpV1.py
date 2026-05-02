import sys, os; home = os.path.expanduser('~'); sys.path.insert(0, os.path.join(home, 'masterbot')); sys.path.insert(0, os.path.join(home, 'masterbot', 'qnt', 'memory')); sys.path.insert(0, os.path.join(home, 'masterbot', 'qnt', 'oracle'));
import logging
import json
import sys
import os
from datetime import datetime, timezone, timedelta
from pandas import DataFrame
import pandas_ta as ta
import numpy as np

from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter
from freqtrade.persistence import Trade

# Add base directory to path for custom imports
home = os.path.expanduser("~")
sys.path.insert(0, os.path.join(home, 'masterbot'))
from risk.risk_manager import run_all_checks
from sentiment.reader import get_current_sentiment, get_sentiment_signal

logger = logging.getLogger(__name__)

class ScalpV1(IStrategy):
    """
    5-minute scalping strategy.
    Entry: RSI < 30 + Price < Lower BB + Vol > Avg Vol
    Exit: RSI > 60 or Price > Mid BB
    Includes multi-timeframe confirmation (15m RSI, 1h EMA).
    """
    INTERFACE_VERSION = 3
    
    timeframe = '5m'
    informative_timeframes = ['15m', '1h']
    
    stoploss = -0.02
    trailing_stop = True
    
    minimal_roi = {
        "0": 0.015,
        "30": 0.01,
        "15": 0.005
    }

    def informative_pairs(self):
        pairs = self.dp.current_whitelist()
        informative_pairs = []
        for timeframe in self.informative_timeframes:
            for pair in pairs:
                informative_pairs.append((pair, timeframe))
        return informative_pairs

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 5m Indicators
        dataframe['rsi'] = ta.rsi(dataframe['close'], length=14)
        bb = ta.bbands(dataframe['close'], length=20, std=2)
        dataframe['bb_lower'] = bb['BBL_20_2.0']
        dataframe['bb_middle'] = bb['BBM_20_2.0']
        dataframe['volume_avg'] = ta.sma(dataframe['volume'], length=20)

        # Informative timeframes
        if self.config['runmode'].value in ('live', 'dry_run'):
            for tf in self.informative_timeframes:
                inf_df = self.dp.get_pair_informative_data(metadata['pair'], tf)
                
                if tf == '15m':
                    inf_df['rsi'] = ta.rsi(inf_df['close'], length=14)
                elif tf == '1h':
                    inf_df['ema_200'] = ta.ema(inf_df['close'], length=200)
                
                dataframe = self.dp.merge_informative_data(dataframe, inf_df, self.timeframe, tf, ffill=True)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Sentiment Gate
        sentiment = get_current_sentiment()
        
        dataframe.loc[
            (
                (dataframe['rsi'] < 30) &
                (dataframe['close'] < dataframe['bb_lower']) &
                (dataframe['volume'] > dataframe['volume_avg']) &
                # HTF Context (if available)
                (dataframe.get('rsi_15m', 50) < 60) & # Not overbought on 15m
                (dataframe.get('close', 0) > dataframe.get('ema_200_1h', 0)) & # Above 200 EMA on 1h
                (sentiment['score'] >= -0.3) # Not BEARISH
            ),
            'enter_long'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['rsi'] > 60) |
                (dataframe['close'] > dataframe['bb_middle'])
            ),
            'exit_long'] = 1
        return dataframe

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                           time_in_force: str, current_time: datetime, entry_tag: str,
                           side: str, **kwargs) -> bool:
        return run_all_checks(pair, amount, rate)

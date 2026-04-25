import sys
import json
from pathlib import Path
from datetime import timedelta
from freqtrade.persistence import Trade
sys.path.insert(0, '/Users/aatifquamre/masterbot')
from risk.risk_manager import run_all_checks, send_telegram_alert
from sentiment.reader import get_current_sentiment, get_sentiment_signal
import pandas_ta as ta
from freqtrade.strategy import IStrategy, IntParameter
from pandas import DataFrame
import numpy as np
import sys
import os
import freqtrade.vendor.qtpylib.indicators as qtpylib

# Import custom regime detector
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from regime_detector import detect_regime

class TrendFollowV1(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = '4h'
    
    # Parameters
    buy_rsi_min = IntParameter(30, 50, default=40, space='buy')
    buy_rsi_max = IntParameter(60, 80, default=80, space='buy')
    sell_rsi_limit = IntParameter(70, 90, default=75, space='sell')
    
    minimal_roi = {"0": 0.03}
    stoploss = -0.06
    stoploss_on_exchange = True
    stoploss_on_exchange_interval = 60
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        if 'ema_fast' not in dataframe.columns:
            dataframe['ema_fast'] = ta.ema(dataframe['close'], length=20)
            dataframe['ema_slow'] = ta.ema(dataframe['close'], length=50)
            macd = ta.macd(dataframe['close'], fast=12, slow=26, signal=9)
            dataframe['macd_hist'] = macd['MACDh_12_26_9']
            dataframe['rsi'] = ta.rsi(dataframe['close'], length=14)
            dataframe = detect_regime(dataframe)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Handle both Hyperopt object and raw value
        rsi_min = self.buy_rsi_min.value if hasattr(self.buy_rsi_min, 'value') else self.buy_rsi_min
        rsi_max = self.buy_rsi_max.value if hasattr(self.buy_rsi_max, 'value') else self.buy_rsi_max
        
        dataframe.loc[
            (
                (qtpylib.crossed_above(dataframe['ema_fast'], dataframe['ema_slow'])) &
                (dataframe['macd_hist'] > 0) &
                (dataframe['regime'] == 'TRENDING_UP') &
                (dataframe['rsi'] > rsi_min) & 
                (dataframe['rsi'] < rsi_max)
            ),
            'enter_long'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        rsi_limit = self.sell_rsi_limit.value if hasattr(self.sell_rsi_limit, 'value') else self.sell_rsi_limit
        
        dataframe.loc[
            (
                (qtpylib.crossed_below(dataframe['ema_fast'], dataframe['ema_slow'])) |
                (dataframe['rsi'] > rsi_limit)
            ),
            'exit_long'] = 1
        return dataframe


            
        return proposed_buy, proposed_sell

    def custom_entry_signal(self, current_time, proposed_buy, proposed_sell,
                            low_profit_factor, current_profit, min_roi,
                            current_entry_rate, open_trade_count,
                            number_of_successful_entries):
        if not proposed_buy:
            return proposed_buy, proposed_sell

        # --- LAYER 1: RISK CHECKS ---
        try:
            current_balance = self.wallets.get_free('USDT')
            total_balance = self.wallets.get_total('USDT')
            recent_trades = [{'profit_ratio': t.profit_ratio} for t in Trade.get_trades_proxy(is_open=False)][:10]
            one_hour_ago = current_time - timedelta(hours=1)
            trades_last_hour = len([t for t in Trade.get_trades_proxy(is_open=False) if t.close_date and t.close_date >= one_hour_ago])
            
            state_file = Path('/Users/aatifquamre/masterbot/risk/balance_state.json')
            if state_file.exists():
                with open(state_file) as f: state = json.load(f)
                start_of_day, start_of_week = state.get('start_of_day', total_balance), state.get('start_of_week', total_balance)
            else:
                start_of_day = start_of_week = total_balance
            
            risk_result = run_all_checks(current_balance, start_of_day, start_of_week, 
                                         current_entry_rate * self.wallets.get_trade_stake_amount(),
                                         trades_last_hour, recent_trades)
            if not risk_result['safe_to_trade']:
                logger.info(f"[RISK BLOCK] TrendFollow blocked. Reasons: {risk_result['blocking_reasons']}")
                return False, proposed_sell
        except Exception as e:
            logger.error(f"[RISK WARNING] Risk check error: {e}")

        # --- LAYER 2: SENTIMENT CHECK ---
        sentiment = get_current_sentiment()
        signal = get_sentiment_signal()
        
        if signal in ['BEARISH', 'NEUTRAL']:
            logger.info(f"[Sentiment BLOCK] TrendFollow needs BULLISH. Current: {signal} ({sentiment['score']:.3f}). Blocking entry.")
            return False, proposed_sell
            
        return proposed_buy, proposed_sell

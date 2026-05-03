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

from freqtrade.strategy import IStrategy, merge_informative_pair
from freqtrade.persistence import Trade

# Add base directory to path for custom imports
home = os.path.expanduser("~")
sys.path.append(os.path.join(home, 'masterbot'))
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
            inf_df = self.dp.get_pair_dataframe(metadata['pair'], '1h')
            inf_df['ema_50'] = ta.ema(inf_df['close'], length=50)
            dataframe = merge_informative_pair(dataframe, inf_df, self.timeframe, '1h', ffill=True)

        dataframe = merge_macro_data(dataframe)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        sentiment = get_current_sentiment()
        
        dataframe.loc[
            (
                (dataframe['ema_9'] > dataframe['ema_21']) & (dataframe['ema_9'].shift(1) <= dataframe['ema_21'].shift(1)) &
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
                (dataframe['ema_9'] < dataframe['ema_21']) & (dataframe['ema_9'].shift(1) >= dataframe['ema_21'].shift(1))
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
                logger.info(f"[RISK BLOCK] Swing blocked for {pair}. Reasons: {risk_result['blocking_reasons']}")
                return False
        except Exception as e:
            logger.error(f"[RISK WARNING] Risk check error: {e}")
            
        return True

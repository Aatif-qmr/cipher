import sys, os; home = os.path.expanduser('~'); sys.path.append(os.path.join(home, 'masterbot')); sys.path.append(os.path.join(home, 'masterbot', 'qnt', 'memory')); sys.path.append(os.path.join(home, 'masterbot', 'qnt', 'oracle'));
import logging
import json
import sys
import os
from pathlib import Path
from datetime import timedelta, datetime
from pandas import DataFrame
import pandas_ta as ta
import numpy as np
import freqtrade.vendor.qtpylib.indicators as qtpylib

from freqtrade.strategy import IStrategy, IntParameter
from freqtrade.persistence import Trade

# Add base directory to path for custom imports
sys.path.insert(0, '/Users/aatifquamre/masterbot')
from risk.risk_manager import run_all_checks
from sentiment.reader import get_current_sentiment, get_sentiment_signal
from strategies.regime_detector import detect_regime

logger = logging.getLogger(__name__)

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

    # Startup candles
    startup_candle_count: int = 50

    def feature_engineering_expand_all(self, dataframe: DataFrame, period: int,
                                     metadata: dict, **kwargs) -> DataFrame:
        # Standard indicators for the model
        dataframe["%-rsi-period"] = ta.rsi(dataframe["close"], length=period) / 100
        dataframe["%-ema_9-period"] = ta.ema(dataframe["close"], length=9) / dataframe["close"]
        
        # External signal features
        import json
        try:
            MASTERBOT_PATH = '/Users/aatifquamre/masterbot'
            with open(f'{MASTERBOT_PATH}/sentiment/scores/current_score.json') as f:
                sentiment_data = json.load(f)
            
            dataframe['sentiment_score'] = sentiment_data.get('score', 0.0)
            dataframe['fear_greed_raw'] = sentiment_data.get('component_scores', {}).get('feargreed', 0.0)
            dataframe['funding_rate_raw'] = sentiment_data.get('component_scores', {}).get('funding', 0.0)
            
            # Calendar risk as numeric feature
            from qnt.oracle.oracle_calendar import check_calendar_risk_today
            risk_map = {'LOW': 0, 'MEDIUM': 1, 'HIGH': 2, 'EXTREME': 3}
            dataframe['calendar_risk'] = risk_map.get(check_calendar_risk_today(), 1)
        except Exception:
            dataframe['sentiment_score'] = 0.0
            dataframe['fear_greed_raw'] = 0.0
            dataframe['funding_rate_raw'] = 0.0
            dataframe['calendar_risk'] = 1

        return dataframe

    def feature_engineering_expand_basic(self, dataframe: DataFrame, metadata: dict, **kwargs) -> DataFrame:
        return dataframe

    def feature_engineering_standard(self, dataframe: DataFrame, metadata: dict, **kwargs) -> DataFrame:
        return dataframe

    def set_freqai_targets(self, dataframe: DataFrame, metadata: dict, **kwargs) -> DataFrame:
        dataframe["&-s_close"] = dataframe["close"].shift(-self.freqai_info["feature_parameters"]["label_period_candles"]) / dataframe["close"] - 1
        return dataframe
    
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

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                            time_in_force: str, current_time: datetime, entry_tag: str,
                            side: str, **kwargs) -> bool:
        
        # --- LAYER 1: RISK CHECKS ---
        try:
            total_balance = self.wallets.get_total('USDT')
            
            # Fetch recent trades
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
            
            # Load balance state
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
                logger.info(f"[RISK BLOCK] TrendFollow blocked for {pair}. Reasons: {risk_result['blocking_reasons']}")
                return False
        except Exception as e:
            logger.error(f"[RISK WARNING] Risk check error: {e}")

        # --- LAYER 2: SENTIMENT CHECK ---
        sentiment = get_current_sentiment()
        signal = get_sentiment_signal()
        
        logger.info(f"[Sentiment] {pair} | Score: {sentiment['score']:.3f} | Signal: {signal}")
        
        # TrendFollow requires strictly BULLISH
        if signal != 'BULLISH':
            logger.info(f"[Sentiment BLOCK] TrendFollow requires BULLISH. Current: {signal} ({sentiment['score']:.3f}). Blocking entry for {pair}.")
            return False
            
        return True

import sys
import json
from pathlib import Path
from datetime import timedelta
from freqtrade.persistence import Trade
sys.path.insert(0, '/Users/aatifquamre/masterbot')
from risk.risk_manager import run_all_checks, send_telegram_alert
from sentiment.reader import get_current_sentiment, get_sentiment_signal
import pandas_ta as ta
from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter
from pandas import DataFrame
import numpy as np
import sys
import os

# Import custom regime detector
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from regime_detector import detect_regime

class MeanReversionV1(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = '1h'
    
    # Optimized Parameters
    buy_params = {
        "bb_period": 30,
        "bb_std": 1.7,
        "buy_rsi": 30,
    }
    sell_params = {
        "sell_rsi": 67,
    }
    minimal_roi = {
        "0": 0.426,
        "226": 0.13,
        "650": 0.082,
        "1867": 0
    }
    stoploss = -0.04
    stoploss_on_exchange = True
    stoploss_on_exchange_interval = 60

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Standard Indicators with optimized params
        dataframe['rsi'] = ta.rsi(dataframe['close'], length=14)
        
        bb = ta.bbands(dataframe['close'], length=self.buy_params['bb_period'], std=self.buy_params['bb_std'])
        dataframe['bb_lower'] = bb[f'BBL_{self.buy_params["bb_period"]}_{self.buy_params["bb_std"]}']
        dataframe['bb_middle'] = bb[f'BBM_{self.buy_params["bb_period"]}_{self.buy_params["bb_std"]}']
            
        dataframe = detect_regime(dataframe)
        dataframe['sentiment_score'] = 0.0
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['rsi'] < self.buy_params['buy_rsi']) &
                (dataframe['close'] < dataframe['bb_lower']) &
                (dataframe['regime'] == 'RANGING') &
                (dataframe['sentiment_score'] > -0.3)
            ),
            'enter_long'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['rsi'] > self.sell_params['sell_rsi']) |
                (dataframe['close'] > dataframe['bb_middle'])
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
            
            recent_trades = [
                {'profit_ratio': t.profit_ratio} 
                for t in Trade.get_trades_proxy(is_open=False)
            ][:10]
            
            one_hour_ago = current_time - timedelta(hours=1)
            trades_last_hour = len([
                t for t in Trade.get_trades_proxy(is_open=False)
                if t.close_date and t.close_date >= one_hour_ago
            ])
            
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
                current_balance=current_balance,
                start_of_day_balance=start_of_day,
                start_of_week_balance=start_of_week,
                trade_amount_usdt=current_entry_rate * self.wallets.get_trade_stake_amount(),
                trades_last_hour=trades_last_hour,
                recent_trades=recent_trades
            )
            
            if not risk_result['safe_to_trade']:
                logger.info(f"[RISK BLOCK] Trade blocked. Reasons: {risk_result['blocking_reasons']}")
                return False, proposed_sell
        except Exception as e:
            logger.error(f"[RISK WARNING] Risk check error: {e}")

        # --- LAYER 2: SENTIMENT CHECK ---
        sentiment = get_current_sentiment()
        signal = get_sentiment_signal()
        
        self.dp.send_msg(
            f"[Sentiment] Score: {sentiment['score']:.3f} | Signal: {signal} | Age: {sentiment['age_minutes']:.0f}min"
        )
        
        if signal == 'BEARISH':
            logger.info(f"[Sentiment BLOCK] Score {sentiment['score']:.3f} is BEARISH. Blocking long entry.")
            return False, proposed_sell
            
        if signal == 'UNAVAILABLE':
            logger.info("[Sentiment WARNING] Score unavailable.")
            
        return proposed_buy, proposed_sell

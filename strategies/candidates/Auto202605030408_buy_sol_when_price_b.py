import pandas as pd
import pandas_ta as ta
from freqtrade.strategy import IStrategy
from freqtrade.persistence import Trade
from datetime import datetime, timezone, timedelta
import os
import json
import sys

# Ensure project root is in path for custom module imports
sys.path.append('/Users/aatifquamre/masterbot')

from sentiment.reader import get_sentiment_signal
from risk.risk_manager import run_all_checks

class Auto202605030408(IStrategy):
    """
    Class Name: Auto202605030408
    Hypothesis: Buy SOL when price bounces from 200 EMA with RSI below 40
    
    Logic:
    - Long-term trend: Price remains above the 200 EMA.
    - Entry condition: Price touches the 200 EMA (Low <= EMA) while RSI is < 40.
    - Sentiment Gate: Blocks entry if current market sentiment is BEARISH.
    - Risk Manager: Integrates mandatory 5-point risk check before execution.
    """
    
    # Strategy parameters
    timeframe = '1h'
    stoploss = -0.04
    stoploss_on_exchange = True
    
    # Minimal ROI
    minimal_roi = {
        "0": 0.10,
        "30": 0.05,
        "60": 0.02,
        "120": 0
    }
    
    # Required candles for indicators
    startup_candle_count: int = 200

    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Calculate EMA 200 and RSI 14 indicators using pandas_ta.
        """
        # Calculate 200-period Exponential Moving Average
        dataframe['ema200'] = ta.ema(dataframe['close'], length=200)
        
        # Calculate 14-period Relative Strength Index
        dataframe['rsi'] = ta.rsi(dataframe['close'], length=14)
        
        return dataframe

    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Define entry conditions based on the bounce hypothesis:
        - Price is above the 200 EMA (identifying a pull-back in an uptrend)
        - The current candle's low touched or dipped below the 200 EMA
        - RSI is below 40 (indicating oversold conditions on the lower timeframe)
        """
        dataframe.loc[
            (
                (dataframe['rsi'] < 40) &
                (dataframe['close'] > dataframe['ema200']) &
                (dataframe['low'] <= dataframe['ema200']) &
                (dataframe['volume'] > 0)
            ),
            'enter_long'] = 1
        
        return dataframe

    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Standard exit logic: Relying on minimal_roi and stoploss.
        """
        dataframe.loc[:, 'exit_long'] = 0
        return dataframe

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                            time_in_force: str, current_time: datetime, entry_tag: str, 
                            side: str, **kwargs) -> bool:
        """
        Final execution check integrating the MasterBot intelligence layer.
        Performs Sentiment analysis and Risk Management validation.
        """
        
        # 1. Sentiment Gate
        # Verify if the overall market sentiment allows for new entries
        if get_sentiment_signal() == 'BEARISH':
            return False
            
        # 2. Risk Manager Integration
        try:
            # Load balance baselines for drawdown calculations
            state_file = '/Users/aatifquamre/masterbot/risk/balance_state.json'
            start_of_day = 0.0
            start_of_week = 0.0
            
            if os.path.exists(state_file):
                with open(state_file, 'r') as f:
                    state = json.load(f)
                    start_of_day = state.get('start_of_day', 0.0)
                    start_of_week = state.get('start_of_week', 0.0)
            
            # Current total balance in stake currency (USDT)
            current_balance = self.wallets.get_total_stake_amount()
            
            # Intended trade size
            trade_amount_usdt = amount * rate
            
            # Circuit breaker: Count trades initiated in the last hour
            one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
            all_trades = Trade.get_trades_proxy()
            trades_last_hour = len([t for t in all_trades if t.open_date_utc >= one_hour_ago])
            
            # Consecutive losses check data
            # Format: list of dicts with profit_ratio and close_date (ISO string)
            closed_trades = Trade.get_trades_proxy(is_open=False)
            closed_trades = sorted(closed_trades, key=lambda x: x.close_date_utc, reverse=True)
            
            recent_trades_dicts = []
            for t in closed_trades[:10]:
                recent_trades_dicts.append({
                    'profit_ratio': t.close_profit,
                    'close_date': t.close_date_utc.isoformat()
                })
            
            # Execute MasterBot global risk rules
            risk_manager_result = run_all_checks(
                current_balance=current_balance,
                start_of_day_balance=start_of_day,
                start_of_week_balance=start_of_week,
                trade_amount_usdt=trade_amount_usdt,
                trades_last_hour=trades_last_hour,
                recent_trades=recent_trades_dicts
            )
            
            return risk_manager_result.get('safe_to_trade', False)
            
        except Exception:
            # Safety first: block entry if risk checks cannot be verified
            return False
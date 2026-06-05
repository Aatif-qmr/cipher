import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas_ta as ta
from pandas import DataFrame

_BASE = Path(__file__).resolve().parent.parent.parent
if str(_BASE) not in sys.path:
    sys.path.insert(0, str(_BASE))

from freqtrade.persistence import Trade
from freqtrade.strategy import DecimalParameter, IntParameter, IStrategy, merge_informative_pair

from indicators.macro_merge import merge_macro_data
from qnt.oracle.hmm_regime import detect_regime, get_regime_for_strategy
from risk.correlation_guard import is_blocked as corr_blocked
from risk.risk_manager import run_all_checks
from risk.stake_sizer import get_stake_multiplier
from risk.volatility_breaker import is_vol_elevated
from sentiment.reader import get_current_sentiment, get_funding_rate, get_sentiment_signal

logger = logging.getLogger(__name__)


class MeanReversionV1(IStrategy):
    """
    1h mean-reversion on crypto majors.

    Entry: RSI oversold + close below lower BB + RSI rising + volume above median.
    Exit:  RSI overbought (2-candle persistence) OR time-stop after 24h.
    Stop:  ATR-based dynamic stop (2×ATR, bounded [-2%, -6%]).

    All other strategies are ARCHIVED pending this strategy proving positive edge
    in paper trading for 3+ months with 30+ trades. See ARCHITECTURE_PRINCIPLES.md.
    """

    INTERFACE_VERSION = 3
    timeframe = "1h"

    # Hyperoptable Parameters — current values from walk_forward_3window (2026-05-23)
    buy_rsi = IntParameter(20, 40, default=25, space="buy")
    bb_period = IntParameter(10, 30, default=15, space="buy")
    bb_std = DecimalParameter(1.0, 2.5, default=1.5, space="buy")
    sell_rsi = IntParameter(55, 80, default=60, space="sell")

    minimal_roi = {"0": 0.426, "226": 0.13, "650": 0.082, "1867": 0}
    stoploss = -0.04
    stoploss_on_exchange = True
    stoploss_on_exchange_interval = 60

    startup_candle_count: int = 200

    def informative_pairs(self) -> list[tuple[str, str]]:
        return [(pair, "4h") for pair in self.dp.current_whitelist()]

    def load_dynamic_params(self):
        self.buy_rsi_val = self.buy_rsi.value
        self.bb_period_val = self.bb_period.value
        self.bb_std_val = self.bb_std.value
        self.sell_rsi_val = self.sell_rsi.value

        try:
            path = _BASE / "config/dynamic_params.json"
            if path.exists():
                import json

                params = json.loads(path.read_text())
                sp = params.get("MeanReversionV1", {})
                if "buy_rsi" in sp:
                    self.buy_rsi_val = int(sp["buy_rsi"])
                if "bb_period" in sp:
                    self.bb_period_val = int(sp["bb_period"])
                if "bb_std" in sp:
                    self.bb_std_val = float(sp["bb_std"])
                if "sell_rsi" in sp:
                    self.sell_rsi_val = int(sp["sell_rsi"])
                logger.info(
                    f"[MeanReversionV1] Dynamic params: buy_rsi={self.buy_rsi_val} "
                    f"bb_period={self.bb_period_val} bb_std={self.bb_std_val} "
                    f"sell_rsi={self.sell_rsi_val}"
                )
        except Exception as e:
            logger.warning(f"[MeanReversionV1] Failed to load dynamic params: {e}")

    # ── FreqAI hooks (disabled unless freqai.enabled=true in config) ─────────
    # NOTE: sentiment features removed from FreqAI hooks because they introduce
    # look-ahead bias in backtests (current_score.json is not point-in-time).
    # Only price-derived features are safe for FreqAI training.

    def feature_engineering_expand_all(
        self, dataframe: DataFrame, period: int, metadata: dict, **kwargs
    ) -> DataFrame:
        dataframe["%-rsi-period"] = ta.rsi(dataframe["close"], length=period) / 100
        dataframe["%-bb_lower-period"] = dataframe["close"] / (
            dataframe["bb_lower"] if "bb_lower" in dataframe.columns else dataframe["close"]
        )
        return dataframe

    def feature_engineering_expand_basic(
        self, dataframe: DataFrame, metadata: dict, **kwargs
    ) -> DataFrame:
        return dataframe

    def feature_engineering_standard(
        self, dataframe: DataFrame, metadata: dict, **kwargs
    ) -> DataFrame:
        return dataframe

    def set_freqai_targets(self, dataframe: DataFrame, metadata: dict, **kwargs) -> DataFrame:
        dataframe["&-s_close"] = (
            dataframe["close"].shift(
                -self.freqai_info["feature_parameters"]["label_period_candles"]
            )
            / dataframe["close"]
            - 1
        )
        return dataframe

    # ── Indicator computation ─────────────────────────────────────────────────

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        self.load_dynamic_params()

        from qnt.polars_indicators import add_atr, add_bollinger_bands, add_ema, add_rsi, add_sma
        from qnt.polars_ohlcv import ohlcv_to_pandas, pandas_to_polars

        df_pl = pandas_to_polars(dataframe)

        df_pl = add_rsi(df_pl, period=14, alias="rsi")
        df_pl = add_bollinger_bands(
            df_pl, period=self.bb_period_val, std_dev=self.bb_std_val, prefix="bb"
        )
        df_pl = df_pl.rename({"bb_mid": "bb_middle"})
        df_pl = add_atr(df_pl, period=14, alias="atr")
        df_pl = add_ema(df_pl, period=200, alias="ema_200")
        # 30-candle rolling median volume for the volume filter
        df_pl = add_sma(df_pl, period=30, column="volume", alias="volume_median_30")

        dataframe = ohlcv_to_pandas(df_pl)

        # 4h EMA_200 — stronger trend filter; forward-filled into 1h bars
        if self.dp:
            inf_4h = self.dp.get_pair_dataframe(pair=metadata["pair"], timeframe="4h")
            if inf_4h is not None and not inf_4h.empty:
                inf_4h = inf_4h.copy()
                inf_4h["ema_200"] = ta.ema(inf_4h["close"], length=200)
                dataframe = merge_informative_pair(
                    dataframe, inf_4h, self.timeframe, "4h", ffill=True
                )

        dataframe = merge_macro_data(dataframe)
        return dataframe

    # ── Entry ─────────────────────────────────────────────────────────────────

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        self.load_dynamic_params()

        is_live = self.config.get("runmode", {}).value in ("live", "dry_run")
        regime_ok = True
        vol_ok = True
        if is_live:
            regime = detect_regime(dataframe, metadata["pair"])
            regime_ok = get_regime_for_strategy("MeanReversionV1", regime)
            vol_ok = not is_vol_elevated(dataframe, metadata["pair"])

        # 4h trend filter — pass-through if column absent (e.g. backtests without 4h data)
        if "ema_200_4h" in dataframe.columns:
            ema_4h_ok = dataframe["ema_200_4h"].isna() | (
                dataframe["close"] > dataframe["ema_200_4h"]
            )
        else:
            ema_4h_ok = True

        dataframe.loc[
            (
                # RSI oversold
                (dataframe["rsi"] < self.buy_rsi_val)
                # RSI momentum: bounce must be starting, not still falling
                & (dataframe["rsi"] > dataframe["rsi"].shift(1))
                # Price below lower Bollinger Band
                & (dataframe["close"] < dataframe["bb_lower"])
                # Volume above 30-candle median (avoid illiquid entries)
                & (dataframe["volume"] > dataframe["volume_median_30"])
                # Trend filter: above both 1h EMA_200 and 4h EMA_200 (no falling knives)
                & (dataframe["close"] > dataframe["ema_200"])
                & ema_4h_ok
                # Regime gate (live only — backtest would require point-in-time HMM labels)
                & (regime_ok)
                # Volatility gate (live only — block entries during flash crashes/blow-offs)
                & (vol_ok)
            ),
            "enter_long",
        ] = 1
        return dataframe

    # ── Exit ──────────────────────────────────────────────────────────────────

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        self.load_dynamic_params()

        raw_exit = dataframe["rsi"] > self.sell_rsi_val
        # 2-candle persistence prevents single-candle RSI spikes triggering premature exit
        dataframe.loc[raw_exit & raw_exit.shift(1).fillna(False), "exit_long"] = 1
        return dataframe

    def custom_stoploss(
        self,
        pair: str,
        trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        after_fill: bool,
        **kwargs,
    ) -> float:
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if dataframe is None or dataframe.empty or "atr" not in dataframe.columns:
            return self.stoploss
        atr = dataframe["atr"].iloc[-1]
        if atr and current_rate and trade.open_rate:
            atr_stop = -(2 * atr) / trade.open_rate
            return max(-0.06, min(-0.02, atr_stop))
        return self.stoploss

    def custom_exit(
        self,
        pair: str,
        trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        **kwargs,
    ):
        hours_open = (current_time - trade.open_date_utc).total_seconds() / 3600

        # 24h time-stop: mean reversion should happen within a day; if not, edge is gone
        if hours_open >= 24 and current_profit < -0.01:
            return "time_stop_24h"

        # In BEAR regime, take profits quickly
        try:
            dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
            if dataframe is not None and not dataframe.empty:
                regime = detect_regime(dataframe, pair)
                if regime == "BEAR" and current_profit >= 0.015 and hours_open >= 2:
                    return "bear_bounce_target"
        except Exception:
            pass

        return None

    def custom_stake_amount(
        self,
        current_time,
        current_rate,
        proposed_stake,
        min_stake,
        max_stake,
        leverage,
        entry_tag,
        side,
        **kwargs,
    ):
        multiplier = get_stake_multiplier("MeanReversionV1")
        stake = proposed_stake * multiplier
        if min_stake is not None:
            stake = max(stake, min_stake)
        return min(stake, max_stake)

    # ── Trade confirmation gate ───────────────────────────────────────────────

    def confirm_trade_entry(
        self,
        pair: str,
        order_type: str,
        amount: float,
        rate: float,
        time_in_force: str,
        current_time: datetime,
        entry_tag: str,
        side: str,
        **kwargs,
    ) -> bool:
        if self.config.get("runmode", {}).value not in ("live", "dry_run"):
            return True

        try:
            total_balance = self.wallets.get_total("USDT")

            recent_trades = [
                {
                    "profit_ratio": float(
                        getattr(t, "close_profit", None) or getattr(t, "profit_ratio", None) or 0.0
                    ),
                    "close_date": getattr(t, "close_date", None),
                }
                for t in Trade.get_trades_proxy(is_open=False)
            ][:10]

            one_hour_ago = current_time - timedelta(hours=1)
            trades_last_hour = len(
                [
                    t
                    for t in Trade.get_trades_proxy(is_open=False)
                    if t.close_date and t.close_date >= one_hour_ago
                ]
            )

            import json

            state_file = _BASE / "risk/balance_state.json"
            if state_file.exists():
                with open(state_file) as f:
                    state = json.load(f)
                start_of_day = state.get("start_of_day", total_balance)
                start_of_week = state.get("start_of_week", total_balance)
            else:
                start_of_day = total_balance
                start_of_week = total_balance

            risk_result = run_all_checks(
                current_balance=total_balance,
                start_of_day_balance=start_of_day,
                start_of_week_balance=start_of_week,
                trade_amount_usdt=amount * rate,
                trades_last_hour=trades_last_hour,
                recent_trades=recent_trades,
                min_sentiment="NEUTRAL",
            )

            if not risk_result["safe_to_trade"]:
                logger.info(
                    f"[RISK BLOCK] MeanReversion blocked for {pair}: {risk_result['blocking_reasons']}"
                )
                return False

            sentiment = get_current_sentiment()
            signal = get_sentiment_signal()
            logger.info(
                f"[Sentiment] {pair} | Score: {sentiment['score']:.3f} | Signal: {signal}"
            )

        except Exception as e:
            logger.error(f"[RISK WARNING] Risk check error: {e}")

        base = pair.split("/")[0]
        if corr_blocked(base, side):
            logger.info(f"[CORR BLOCK] MeanReversionV1 {pair} — concurrent long limit reached")
            return False

        if side == "long":
            funding = get_funding_rate()
            if funding < -0.5:
                logger.info(
                    f"[FUNDING BLOCK] MeanReversionV1 {pair} funding={funding:.2f}"
                )
                return False

        return True

# 1h/2h entry strategy: faster timeframes with moderate risk
from __future__ import annotations

from datetime import datetime
from pandas import DataFrame
import talib.abstract as ta
from portfolio_heat import PortfolioHeatMixin
from TrendPullbackScaleOutStrategy import TrendPullbackScaleOutStrategy
from freqtrade.strategy import informative


class TrendPullback1h2hModerate(PortfolioHeatMixin, TrendPullbackScaleOutStrategy):
    """
    1h entry timeframe + 2h bias (faster than 2h/4h)
    Moderate risk profile: 1% risk, 2% heat, 15x lev
    """

    timeframe = "1h"
    risk_pct = 0.01
    max_leverage_cap = 15.0
    portfolio_heat_cap = 0.02
    max_same_way = 2
    book_tag = "1H2H_MODERATE"

    @informative("2h")
    def populate_indicators_2h(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """2h bias instead of 4h"""
        dataframe["ema20"] = ta.EMA(dataframe, timeperiod=self.ema_period)
        lb = self.swing_lookback
        low, high = dataframe["low"], dataframe["high"]
        dataframe["swing_low"] = low[low == low.rolling(lb * 2 + 1, center=True).min()]
        dataframe["swing_high"] = high[high == high.rolling(lb * 2 + 1, center=True).max()]
        dataframe["last_swing_low"] = dataframe["swing_low"].ffill()
        dataframe["last_swing_high"] = dataframe["swing_high"].ffill()
        prev_sl = dataframe["last_swing_low"].shift(lb)
        prev_sh = dataframe["last_swing_high"].shift(lb)
        hh = dataframe["last_swing_low"] > prev_sl
        ll = dataframe["last_swing_high"] < prev_sh
        dataframe["bias_long"] = (dataframe["close"] > dataframe["ema20"]) & hh.fillna(False)
        dataframe["bias_short"] = (dataframe["close"] < dataframe["ema20"]) & ll.fillna(False)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Use 2h bias instead of 4h"""
        dataframe.loc[
            (
                dataframe["bias_long_2h"].fillna(False)
                & dataframe["bull_reject"]
                & (dataframe["close"] > dataframe["ema20"])
                & (dataframe["volume"] > 0)
            ),
            "enter_long",
        ] = 1
        dataframe.loc[
            (
                dataframe["bias_short_2h"].fillna(False)
                & dataframe["bear_reject"]
                & (dataframe["close"] < dataframe["ema20"])
                & (dataframe["volume"] > 0)
            ),
            "enter_short",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Use 2h bias for exits"""
        dataframe["exit_long"] = 0
        dataframe["exit_short"] = 0
        dataframe.loc[dataframe["bias_short_2h"].fillna(False), "exit_long"] = 1
        dataframe.loc[dataframe["bias_long_2h"].fillna(False), "exit_short"] = 1
        return dataframe

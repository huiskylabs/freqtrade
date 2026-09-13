# Research Entry A/B #1a: Moderate ScaleOut + stricter 4h bias (EMA50 filter)
from __future__ import annotations

import talib.abstract as ta
from pandas import DataFrame
from freqtrade.strategy import informative

from TrendPullbackScaleOutModerate import TrendPullbackScaleOutModerate


class TrendPullbackScaleOutModEMA50(TrendPullbackScaleOutModerate):
    """
    Same Moderate risk/heat/ScaleOut exits.
    Stricter 4h bias: also require close vs EMA50 (long > EMA50, short < EMA50).
    """

    book_tag = "MOD_EMA50"

    @informative("4h")
    def populate_indicators_4h(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema20"] = ta.EMA(dataframe, timeperiod=self.ema_period)
        dataframe["ema50"] = ta.EMA(dataframe, timeperiod=50)
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
        dataframe["bias_long"] = (
            (dataframe["close"] > dataframe["ema20"])
            & (dataframe["close"] > dataframe["ema50"])
            & hh.fillna(False)
        )
        dataframe["bias_short"] = (
            (dataframe["close"] < dataframe["ema20"])
            & (dataframe["close"] < dataframe["ema50"])
            & ll.fillna(False)
        )
        return dataframe

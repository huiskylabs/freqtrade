# ScaleOut MODERATE book on 1h entries + 2h bias (research TF variant)
from __future__ import annotations

from pandas import DataFrame
import talib.abstract as ta
from freqtrade.strategy import informative

from TrendPullbackScaleOutModerate import TrendPullbackScaleOutModerate


class TrendPullbackScaleOutModerate1h2h(TrendPullbackScaleOutModerate):
    """
    Same MODERATE heat/risk book as TrendPullbackScaleOutModerate, but:
      timeframe = 1h (entries / swing / EMA)
      informative bias = 2h (was 4h on the 2h-entry book)

    Shadows parent @informative("4h") so only 2h bias columns are used:
      bias_long_2h / bias_short_2h in populate_entry/exit.
    """

    timeframe = "1h"
    # ~80 x 2h wall-clock so 2h informative EMA/swing have enough history
    startup_candle_count = 160

    @informative("2h")
    def populate_indicators_2h(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
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

    def populate_indicators_4h(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Shadow parent @informative("4h") so it is not registered.
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
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
        dataframe["exit_long"] = 0
        dataframe["exit_short"] = 0
        dataframe.loc[dataframe["bias_short_2h"].fillna(False), "exit_long"] = 1
        dataframe.loc[dataframe["bias_long_2h"].fillna(False), "exit_short"] = 1
        return dataframe

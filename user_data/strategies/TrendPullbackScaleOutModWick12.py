# A/B only: previous Moderate rejection — wick > 1.2× body (demoted 2026-09-12)
from __future__ import annotations

from pandas import DataFrame
import talib.abstract as ta

from TrendPullbackScaleOutModerate import TrendPullbackScaleOutModerate


class TrendPullbackScaleOutModWick12(TrendPullbackScaleOutModerate):
    """Demoted baseline: bull/bear reject requires wick > 1.2× body."""

    book_tag = "MOD_WICK12_AB"
    wick_body_mult = 1.2

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema20"] = ta.EMA(dataframe, timeperiod=self.ema_period)
        lb = self.swing_lookback
        low, high = dataframe["low"], dataframe["high"]
        dataframe["swing_low"] = low[low == low.rolling(lb * 2 + 1, center=True).min()]
        dataframe["swing_high"] = high[high == high.rolling(lb * 2 + 1, center=True).max()]
        dataframe["last_swing_low"] = dataframe["swing_low"].ffill()
        dataframe["last_swing_high"] = dataframe["swing_high"].ffill()
        body = (dataframe["close"] - dataframe["open"]).abs()
        upper_wick = dataframe["high"] - dataframe[["open", "close"]].max(axis=1)
        lower_wick = dataframe[["open", "close"]].min(axis=1) - dataframe["low"]
        b = 0.008
        near_ema = (dataframe["low"] <= dataframe["ema20"] * (1.0 + b)) & (
            dataframe["close"] >= dataframe["ema20"] * (1.0 - b)
        )
        near_ema_short = (dataframe["high"] >= dataframe["ema20"] * (1.0 - b)) & (
            dataframe["close"] <= dataframe["ema20"] * (1.0 + b)
        )
        w = self.wick_body_mult
        dataframe["bull_reject"] = (
            (lower_wick > body * w) & (dataframe["close"] > dataframe["open"]) & near_ema
        )
        dataframe["bear_reject"] = (
            (upper_wick > body * w) & (dataframe["close"] < dataframe["open"]) & near_ema_short
        )
        return dataframe

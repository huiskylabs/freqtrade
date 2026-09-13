# Research Entry A/B #1b: Moderate ScaleOut + 2h close reclaim after rejection
from __future__ import annotations

from pandas import DataFrame

from TrendPullbackScaleOutModerate import TrendPullbackScaleOutModerate


class TrendPullbackScaleOutModReclaim(TrendPullbackScaleOutModerate):
    """
    Same Moderate risk/heat/ScaleOut exits.
    Entry on the *reclaim* bar after a 2h rejection (not on the rejection bar itself):
      long: prior bull_reject, this close > ema20 and close > open
      short: prior bear_reject, this close < ema20 and close < open
    """

    book_tag = "MOD_RECLAIM"

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        bull_reclaim = (
            dataframe["bull_reject"].shift(1).fillna(False)
            & (dataframe["close"] > dataframe["ema20"])
            & (dataframe["close"] > dataframe["open"])
        )
        bear_reclaim = (
            dataframe["bear_reject"].shift(1).fillna(False)
            & (dataframe["close"] < dataframe["ema20"])
            & (dataframe["close"] < dataframe["open"])
        )
        dataframe.loc[
            (
                dataframe["bias_long_4h"].fillna(False)
                & bull_reclaim
                & (dataframe["volume"] > 0)
            ),
            "enter_long",
        ] = 1
        dataframe.loc[
            (
                dataframe["bias_short_4h"].fillna(False)
                & bear_reclaim
                & (dataframe["volume"] > 0)
            ),
            "enter_short",
        ] = 1
        return dataframe

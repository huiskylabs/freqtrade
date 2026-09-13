# Research stops A/B: Moderate 25%@2R with ATR(14)×1.5 stop (still sized to risk_pct)
from __future__ import annotations

import numpy as np
import talib.abstract as ta
from pandas import DataFrame

from TrendPullbackScaleOutModerate import TrendPullbackScaleOutModerate


class TrendPullbackScaleOutModATRstop(TrendPullbackScaleOutModerate):
    """
    Same Moderate book / 25%@2R exits.
    Stop = entry ± ATR(14)*atr_mult instead of swing high/low.
    Sizing still notional = (equity * risk_pct) / stop_dist → $ risk ≈ 1%.
    """

    book_tag = "MOD_ATR15"
    atr_period = 14
    atr_mult = 1.5

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=self.atr_period)
        return dataframe

    def _swing_stop_price(self, last, side: str, rate: float) -> float:
        try:
            atr = float(last["atr"])
        except Exception:
            atr = float("nan")
        if not np.isfinite(atr) or atr <= 0:
            return super()._swing_stop_price(last, side, rate)
        if side == "long":
            stop = rate - self.atr_mult * atr
            if stop <= 0 or stop >= rate:
                stop = rate * (1.0 - self.min_stop_dist)
            return float(stop)
        stop = rate + self.atr_mult * atr
        if stop <= rate:
            stop = rate * (1.0 + self.min_stop_dist)
        return float(stop)

# Trend-pullback: no hard 2R TP — exit only on 4h bias flip + fixed swing stop
from __future__ import annotations

from datetime import datetime

from freqtrade.persistence import Trade
from TrendPullbackStrategy import TrendPullbackStrategy


class TrendPullbackBiasFlipStrategy(TrendPullbackStrategy):
    """
    Same entries / sizing / pinned swing stop as TrendPullbackStrategy.
    Removes the hard 2R custom_exit take_profit. Position rides until the
    existing 4h bias-flip exit signal or the original swing stop.
    """

    def custom_exit(
        self,
        pair: str,
        trade: Trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        **kwargs,
    ):
        return self.risk_custom_exit_reason(trade)

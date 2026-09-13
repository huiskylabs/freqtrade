# A/B only: previous Moderate ScaleOut — 50% at +2R (demoted 2026-09-12)
from __future__ import annotations

from datetime import datetime

from freqtrade.persistence import Trade
from TrendPullbackScaleOutModerate import TrendPullbackScaleOutModerate


class TrendPullbackScaleOutMod50at2R(TrendPullbackScaleOutModerate):
    """Demoted baseline: scale out ~50% at +2R. Live candidate is now 25%@2R."""

    book_tag = "MOD_50AT2R_AB"

    def adjust_trade_position(
        self,
        trade: Trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        min_stake: float | None,
        max_stake: float,
        current_entry_rate: float,
        current_exit_rate: float,
        current_entry_profit: float,
        current_exit_profit: float,
        **kwargs,
    ):
        if trade.has_open_orders:
            return None
        if trade.nr_of_successful_exits >= 1:
            return None
        r = self._r_multiple(trade, current_exit_profit)
        if r is None or r < self.reward_risk:
            return None
        half = float(trade.stake_amount) * 0.5
        remainder = float(trade.stake_amount) - half
        if min_stake is not None:
            floor = float(min_stake)
            if half < floor or remainder < floor:
                return None
        return -half, "scale_out_2R_50"

# Research #2: Moderate ScaleOut ladder — 33%@1.5R + 33%@3R, rest bias/stop
from __future__ import annotations

from datetime import datetime

from freqtrade.persistence import Trade
from TrendPullbackScaleOutModerate import TrendPullbackScaleOutModerate


class TrendPullbackScaleOutModLadder(TrendPullbackScaleOutModerate):
    """
    Same Moderate entries/sizing/heat.
    Scale ladder: ~33% at +1.5R, ~33% at +3R; remainder on bias flip / swing stop.
    """

    book_tag = "MOD_LADDER"
    position_adjustment_enable = True
    max_entry_position_adjustment = 0
    scale1_r = 1.5
    scale2_r = 3.0
    scale_frac = 1.0 / 3.0

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

        initial = trade.get_custom_data("ladder_initial_stake")
        if initial is None:
            initial = float(trade.stake_amount)
            trade.set_custom_data("ladder_initial_stake", initial)
        initial = float(initial)

        r = self._r_multiple(trade, current_exit_profit)
        if r is None:
            return None

        exits = int(trade.nr_of_successful_exits)
        floor = float(min_stake) if min_stake is not None else 0.0
        target = initial * self.scale_frac

        if exits == 0 and r >= self.scale1_r:
            amt = min(target, float(trade.stake_amount) * 0.9)
            rem = float(trade.stake_amount) - amt
            if amt < floor or rem < floor:
                return None
            return -amt, "scale_out_1.5R"

        if exits == 1 and r >= self.scale2_r:
            amt = min(target, float(trade.stake_amount) * 0.9)
            rem = float(trade.stake_amount) - amt
            if amt < floor or rem < floor:
                return None
            return -amt, "scale_out_3R"

        return None

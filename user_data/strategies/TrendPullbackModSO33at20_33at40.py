# Research TP ScaleOut variant — 33%@2R + 33%@4R
from __future__ import annotations
from datetime import datetime
from freqtrade.persistence import Trade
from TrendPullbackScaleOutModerate import TrendPullbackScaleOutModerate

class TrendPullbackModSO33at20_33at40(TrendPullbackScaleOutModerate):
    book_tag = "MODSO33AT20_33AT40"
    position_adjustment_enable = True
    max_entry_position_adjustment = 0
    # rules: (exits_done, r_min, frac_of_initial, tag)
    SCALE_RULES = [(0, 2.0, 0.3333333333333333, 'scale_out_2R'), (1, 4.0, 0.3333333333333333, 'scale_out_4R')]

    def adjust_trade_position(self, trade: Trade, current_time: datetime, current_rate: float,
        current_profit: float, min_stake: float | None, max_stake: float,
        current_entry_rate: float, current_exit_rate: float, current_entry_profit: float,
        current_exit_profit: float, **kwargs):
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
        for need_exits, r_min, frac, tag in self.SCALE_RULES:
            if exits == need_exits and r >= r_min:
                amt = min(initial * frac, float(trade.stake_amount) * 0.9)
                rem = float(trade.stake_amount) - amt
                if amt < floor or rem < floor:
                    return None
                return -amt, tag
        return None

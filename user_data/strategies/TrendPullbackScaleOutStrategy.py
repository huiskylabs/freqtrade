# Trend-pullback scale-out: take ~25% at +2R, remainder rides bias-flip / swing stop
# (promoted 2026-09-12; 50%@2R kept as TrendPullbackScaleOutMod50at2R for A/B)
from __future__ import annotations

from datetime import datetime

from freqtrade.persistence import Trade
from TrendPullbackStrategy import TrendPullbackStrategy


class TrendPullbackScaleOutStrategy(TrendPullbackStrategy):
    """
    Same entries / sizing / pinned swing stop as TrendPullbackStrategy.
    At +2R close ~25% via adjust_trade_position (tag scale_out_2R).
    Remainder exits on 4h bias flip (exit_signal) or the original fixed swing stop.
    No hard 2R flatten of the full position.
    """

    position_adjustment_enable = True
    max_entry_position_adjustment = 0  # no adds; only the one scale-out
    scale_out_frac = 0.25

    def _r_multiple(self, trade: Trade, current_profit: float) -> float | None:
        stop = trade.get_custom_data("swing_stop")
        if stop is None:
            dataframe, _ = self.dp.get_analyzed_dataframe(trade.pair, self.timeframe)
            if dataframe is None or dataframe.empty:
                return None
            try:
                entry_candle = dataframe.loc[dataframe["date"] <= trade.open_date_utc].iloc[-1]
            except Exception:
                return None
            side = "short" if trade.is_short else "long"
            stop = self._swing_stop_price(entry_candle, side, trade.open_rate)
            trade.set_custom_data("swing_stop", float(stop))
        side = "short" if trade.is_short else "long"
        dist = self._stop_dist_ratio(trade.open_rate, float(stop), side)
        lev = trade.leverage or 1.0
        denom = dist * lev
        if denom <= 0:
            return None
        return float(current_profit) / denom

    def custom_exit(
        self,
        pair: str,
        trade: Trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        **kwargs,
    ):
        # Risk flatten only — do NOT hard-flat the remainder at 2R.
        return self.risk_custom_exit_reason(trade)

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
        # One scale-out only
        if trade.nr_of_successful_exits >= 1:
            return None
        r = self._r_multiple(trade, current_exit_profit)
        if r is None or r < self.reward_risk:
            return None
        portion = float(trade.stake_amount) * float(self.scale_out_frac)
        remainder = float(trade.stake_amount) - portion
        if min_stake is not None:
            floor = float(min_stake)
            if portion < floor or remainder < floor:
                return None
        return -portion, "scale_out_2R"

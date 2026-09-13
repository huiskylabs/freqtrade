# Trend-pullback: fixed swing stop until +2R, then trail last swing (no hard 2R TP)
from __future__ import annotations

from datetime import datetime

import numpy as np
from freqtrade.persistence import Trade
from freqtrade.strategy import stoploss_from_absolute
from TrendPullbackStrategy import TrendPullbackStrategy


class TrendPullbackTrailAfter2RStrategy(TrendPullbackStrategy):
    """
    Same entries / sizing as TrendPullbackStrategy.
    Swing stop stays pinned until unrealized R >= 2.0.
    After 2R is first touched, trail the stop to last 2h swing low (long) /
    last 2h swing high (short), ratchet-only, never looser than the original
    swing stop. custom_exit does NOT hard-flat at 2R.
    Config trailing_stop=false is left alone; trail lives in custom_stoploss.
    """

    def _r_multiple(self, trade: Trade, current_profit: float, stop: float) -> float | None:
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
        return self.risk_custom_exit_reason(trade)

    def custom_stoploss(
        self,
        pair: str,
        trade: Trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        after_fill: bool,
        **kwargs,
    ) -> float | None:
        stop = trade.get_custom_data("swing_stop")
        if stop is None:
            dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
            if dataframe is None or dataframe.empty:
                return None
            try:
                entry_candle = dataframe.loc[dataframe["date"] <= trade.open_date_utc].iloc[-1]
            except Exception:
                entry_candle = dataframe.iloc[-1]
            side = "short" if trade.is_short else "long"
            stop = float(self._swing_stop_price(entry_candle, side, trade.open_rate))
            trade.set_custom_data("swing_stop", stop)

        stop = float(stop)
        armed = bool(trade.get_custom_data("trail_armed"))
        if not armed:
            r = self._r_multiple(trade, current_profit, stop)
            if r is not None and r >= self.reward_risk:
                trade.set_custom_data("trail_armed", True)
                armed = True

        abs_stop = stop
        if armed:
            dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
            if dataframe is not None and not dataframe.empty:
                last = dataframe.iloc[-1]
                if trade.is_short:
                    swing = float(last.get("last_swing_high", np.nan))
                    if np.isfinite(swing) and swing > 0:
                        # short: tighten = lower stop; never above original swing
                        cand = min(swing, stop)
                        prev = trade.get_custom_data("trail_stop")
                        if prev is not None:
                            cand = min(cand, float(prev))
                        # must stay on the losing side of current_rate
                        if cand > current_rate:
                            abs_stop = cand
                            trade.set_custom_data("trail_stop", cand)
                else:
                    swing = float(last.get("last_swing_low", np.nan))
                    if np.isfinite(swing) and swing > 0:
                        cand = max(swing, stop)
                        prev = trade.get_custom_data("trail_stop")
                        if prev is not None:
                            cand = max(cand, float(prev))
                        if cand < current_rate:
                            abs_stop = cand
                            trade.set_custom_data("trail_stop", cand)

        return stoploss_from_absolute(
            float(abs_stop),
            current_rate,
            is_short=trade.is_short,
            leverage=trade.leverage or 1.0,
        )

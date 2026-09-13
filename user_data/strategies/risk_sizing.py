from __future__ import annotations
from datetime import datetime
import numpy as np
from pandas import DataFrame
from freqtrade.persistence import Trade
from freqtrade.strategy import stoploss_from_absolute


class RiskSizingMixin:
    risk_pct = 0.0075
    max_leverage_cap = 20.0
    reward_risk = 2.0
    min_stop_dist = 0.005
    swing_lookback = 3

    def _swing_stop(self, last, side: str, rate: float) -> float:
        if side == "long":
            stop = float(last.get("last_swing_low", np.nan))
            if not np.isfinite(stop) or stop <= 0 or stop >= rate:
                stop = rate * (1.0 - self.min_stop_dist)
            return stop
        stop = float(last.get("last_swing_high", np.nan))
        if not np.isfinite(stop) or stop <= 0 or stop <= rate:
            stop = rate * (1.0 + self.min_stop_dist)
        return stop

    def _atr_stop(self, last, side: str, rate: float, mult: float = 1.5) -> float:
        atr = float(last.get("atr", np.nan))
        if not np.isfinite(atr) or atr <= 0:
            atr = rate * self.min_stop_dist
        return rate - mult * atr if side == "long" else rate + mult * atr

    def _tighter(self, a: float, b: float, side: str) -> float:
        return max(a, b) if side == "long" else min(a, b)

    def _dist(self, rate: float, stop: float, side: str) -> float:
        d = (rate - stop) / rate if side == "long" else (stop - rate) / rate
        return float(max(d, self.min_stop_dist))

    def _fill_swings(self, df: DataFrame) -> DataFrame:
        lb = self.swing_lookback
        low, high = df["low"], df["high"]
        df["swing_low"] = low[low == low.rolling(lb * 2 + 1, center=True).min()]
        df["swing_high"] = high[high == high.rolling(lb * 2 + 1, center=True).max()]
        df["last_swing_low"] = df["swing_low"].ffill()
        df["last_swing_high"] = df["swing_high"].ffill()
        return df

    def _entry_stop_price(self, last, side: str, rate: float) -> float:
        # default: tighter of swing vs 1.5 ATR
        return self._tighter(self._swing_stop(last, side, rate), self._atr_stop(last, side, rate, 1.5), side)

    def leverage(self, pair, current_time, current_rate, proposed_leverage, max_leverage, entry_tag, side, **kwargs):
        df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if df is None or df.empty:
            return 1.0
        last = df.iloc[-1]
        stop = self._entry_stop_price(last, side, current_rate)
        dist = self._dist(current_rate, stop, side)
        equity = float(self.wallets.get_total(self.config["stake_currency"]))
        notional = (equity * self.risk_pct) / dist
        available = max(float(self.wallets.get_available_stake_amount()), 1.0)
        if notional <= available:
            return 1.0
        return float(max(1.0, min(self.max_leverage_cap, max_leverage, notional / available)))

    def custom_stake_amount(self, pair, current_time, current_rate, proposed_stake, min_stake, max_stake, leverage, entry_tag, side, **kwargs):
        df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if df is None or df.empty:
            return proposed_stake
        last = df.iloc[-1]
        stop = self._entry_stop_price(last, side, current_rate)
        dist = self._dist(current_rate, stop, side)
        equity = float(self.wallets.get_total(self.config["stake_currency"]))
        notional = (equity * self.risk_pct) / dist
        stake = notional / max(float(leverage), 1.0)
        return float(max(float(min_stake or 0.0), min(stake, float(max_stake))))

    def custom_stoploss(self, pair, trade: Trade, current_time, current_rate, current_profit, after_fill, **kwargs):
        df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if df is None or df.empty:
            return None
        try:
            entry = df.loc[df["date"] <= trade.open_date_utc].iloc[-1]
        except Exception:
            entry = df.iloc[-1]
        side = "short" if trade.is_short else "long"
        stop = self._entry_stop_price(entry, side, trade.open_rate)
        return stoploss_from_absolute(stop, current_rate, is_short=trade.is_short, leverage=trade.leverage or 1.0)

    def custom_exit(self, pair, trade: Trade, current_time, current_rate, current_profit, **kwargs):
        if not getattr(self, "use_fixed_2r", True):
            return None
        df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if df is None or df.empty:
            return None
        try:
            entry = df.loc[df["date"] <= trade.open_date_utc].iloc[-1]
        except Exception:
            return None
        side = "short" if trade.is_short else "long"
        stop = self._entry_stop_price(entry, side, trade.open_rate)
        dist = self._dist(trade.open_rate, stop, side)
        if current_profit / (dist * (trade.leverage or 1.0)) >= self.reward_risk:
            return f"take_profit_{self.reward_risk}R"
        return None

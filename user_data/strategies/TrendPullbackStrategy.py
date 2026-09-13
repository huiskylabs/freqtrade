# Trend-pullback: 4h bias + 2h pullback entry (Backpack BTC futures)
from __future__ import annotations

from datetime import datetime
from pandas import DataFrame
import numpy as np
import talib.abstract as ta
from freqtrade.persistence import Trade
from freqtrade.strategy import IStrategy, informative, stoploss_from_absolute
from risk_killswitches import RiskKillSwitchMixin


class TrendPullbackStrategy(RiskKillSwitchMixin, IStrategy):
    """
    4h bias + 2h pullback rejection.
    Position sizing: notional = (equity * risk_pct) / stop_dist
                  margin  = notional / leverage
                  leverage = min(20, max(1, notional / available_margin))
    So dollar risk at the swing stop ≈ equity * risk_pct.
    """

    INTERFACE_VERSION = 3
    can_short = True
    timeframe = "2h"
    startup_candle_count = 80
    process_only_new_candles = True

    minimal_roi = {"0": 100}
    stoploss = -0.99  # unused fallback; custom_stoploss is authoritative
    use_custom_stoploss = True
    trailing_stop = False
    use_exit_signal = True
    exit_profit_only = False

    risk_pct = 0.0075  # 0.75% equity
    max_leverage_cap = 20.0
    reward_risk = 2.0
    swing_lookback = 3
    ema_period = 20
    pullback_band = 0.008  # ±0.8% around EMA20
    wick_body_mult = 1.0  # rejection wick vs body (promoted 2026-09-12; 1.2 kept as ModWick12 A/B)
    min_stop_dist = 0.005  # 0.5% floor so size stays finite

    order_types = {
        "entry": "limit",
        "exit": "limit",
        "stoploss": "market",
        "stoploss_on_exchange": False,
    }

    # ---------- helpers ----------
    def _swing_stop_price(self, last, side: str, rate: float) -> float:
        if side == "long":
            stop = float(last.get("last_swing_low", np.nan))
            if not np.isfinite(stop) or stop <= 0 or stop >= rate:
                stop = rate * (1.0 - self.min_stop_dist)
            return stop
        stop = float(last.get("last_swing_high", np.nan))
        if not np.isfinite(stop) or stop <= 0 or stop <= rate:
            stop = rate * (1.0 + self.min_stop_dist)
        return stop

    def _stop_dist_ratio(self, rate: float, stop: float, side: str) -> float:
        if side == "long":
            dist = (rate - stop) / rate
        else:
            dist = (stop - rate) / rate
        return float(max(dist, self.min_stop_dist))

    def _size_from_risk(self, rate: float, stop: float, side: str, max_leverage: float):
        """Return (leverage, stake_margin, notional, dist, risk_cash)."""
        dist = self._stop_dist_ratio(rate, stop, side)
        equity = float(self.wallets.get_total(self.config["stake_currency"]))
        risk_cash = equity * self.risk_pct
        notional = risk_cash / dist  # loses ~risk_cash if price hits stop
        available = float(self.wallets.get_available_stake_amount())
        available = max(available, 1.0)
        # Leverage only to fit notional into available margin
        if notional <= available:
            lev = 1.0
            stake = notional
        else:
            lev = min(self.max_leverage_cap, max_leverage, notional / available)
            lev = max(1.0, lev)
            stake = notional / lev  # == available when capped by wallet
            # If still capped by max leverage, shrink notional to what 20x can hold
            max_notional = available * min(self.max_leverage_cap, max_leverage)
            if notional > max_notional:
                notional = max_notional
                stake = available
                # Actual risk will be less than risk_pct when 20x still can't fit
        return lev, stake, notional, dist, risk_cash

    # ---------- indicators / signals ----------
    @informative("4h")
    def populate_indicators_4h(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema20"] = ta.EMA(dataframe, timeperiod=self.ema_period)
        lb = self.swing_lookback
        low, high = dataframe["low"], dataframe["high"]
        dataframe["swing_low"] = low[low == low.rolling(lb * 2 + 1, center=True).min()]
        dataframe["swing_high"] = high[high == high.rolling(lb * 2 + 1, center=True).max()]
        dataframe["last_swing_low"] = dataframe["swing_low"].ffill()
        dataframe["last_swing_high"] = dataframe["swing_high"].ffill()
        prev_sl = dataframe["last_swing_low"].shift(lb)
        prev_sh = dataframe["last_swing_high"].shift(lb)
        hh = dataframe["last_swing_low"] > prev_sl
        ll = dataframe["last_swing_high"] < prev_sh
        dataframe["bias_long"] = (dataframe["close"] > dataframe["ema20"]) & hh.fillna(False)
        dataframe["bias_short"] = (dataframe["close"] < dataframe["ema20"]) & ll.fillna(False)
        return dataframe

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
        b = float(self.pullback_band)
        near_ema = (dataframe["low"] <= dataframe["ema20"] * (1.0 + b)) & (
            dataframe["close"] >= dataframe["ema20"] * (1.0 - b)
        )
        near_ema_short = (dataframe["high"] >= dataframe["ema20"] * (1.0 - b)) & (
            dataframe["close"] <= dataframe["ema20"] * (1.0 + b)
        )
        w = float(self.wick_body_mult)
        dataframe["bull_reject"] = (
            (lower_wick > body * w) & (dataframe["close"] > dataframe["open"]) & near_ema
        )
        dataframe["bear_reject"] = (
            (upper_wick > body * w) & (dataframe["close"] < dataframe["open"]) & near_ema_short
        )
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                dataframe["bias_long_4h"].fillna(False)
                & dataframe["bull_reject"]
                & (dataframe["close"] > dataframe["ema20"])
                & (dataframe["volume"] > 0)
            ),
            "enter_long",
        ] = 1
        dataframe.loc[
            (
                dataframe["bias_short_4h"].fillna(False)
                & dataframe["bear_reject"]
                & (dataframe["close"] < dataframe["ema20"])
                & (dataframe["volume"] > 0)
            ),
            "enter_short",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["exit_long"] = 0
        dataframe["exit_short"] = 0
        dataframe.loc[dataframe["bias_short_4h"].fillna(False), "exit_long"] = 1
        dataframe.loc[dataframe["bias_long_4h"].fillna(False), "exit_short"] = 1
        return dataframe

    def leverage(
        self,
        pair: str,
        current_time: datetime,
        current_rate: float,
        proposed_leverage: float,
        max_leverage: float,
        entry_tag: str | None,
        side: str,
        **kwargs,
    ) -> float:
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if dataframe is None or dataframe.empty:
            return 1.0
        last = dataframe.iloc[-1]
        stop = self._swing_stop_price(last, side, current_rate)
        lev, _, _, _, _ = self._size_from_risk(current_rate, stop, side, max_leverage)
        return float(lev)

    def custom_stake_amount(
        self,
        pair: str,
        current_time: datetime,
        current_rate: float,
        proposed_stake: float,
        min_stake: float | None,
        max_stake: float,
        leverage: float,
        entry_tag: str | None,
        side: str,
        **kwargs,
    ) -> float:
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if dataframe is None or dataframe.empty:
            return proposed_stake
        last = dataframe.iloc[-1]
        stop = self._swing_stop_price(last, side, current_rate)
        # Recompute with the leverage backtesting already chose
        dist = self._stop_dist_ratio(current_rate, stop, side)
        equity = float(self.wallets.get_total(self.config["stake_currency"]))
        risk_cash = equity * self.risk_pct
        notional = risk_cash / dist
        lev = max(float(leverage), 1.0)
        stake = notional / lev
        stake = max(float(min_stake or 0.0), min(float(stake), float(max_stake)))
        return float(stake)

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
        # Pin swing stop once at fill — fixed absolute, never trail/ratchet.
        # (Freqtrade may still *label* the first tighten from stoploss=-0.99 as
        # trailing_stop_loss; behavior is fixed swing / 2R / bias-flip only.)
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
        return stoploss_from_absolute(
            float(stop),
            current_rate,
            is_short=trade.is_short,
            leverage=trade.leverage or 1.0,
        )

    def custom_exit(
        self,
        pair: str,
        trade: Trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        **kwargs,
    ):
        risk_exit = self.risk_custom_exit_reason(trade)
        if risk_exit:
            return risk_exit
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if dataframe is None or dataframe.empty:
            return None
        try:
            entry_candle = dataframe.loc[dataframe["date"] <= trade.open_date_utc].iloc[-1]
        except Exception:
            return None
        side = "short" if trade.is_short else "long"
        stop = self._swing_stop_price(entry_candle, side, trade.open_rate)
        dist = self._stop_dist_ratio(trade.open_rate, stop, side)
        lev = trade.leverage or 1.0
        r_multiple = current_profit / (dist * lev)
        if r_multiple >= self.reward_risk:
            return f"take_profit_{self.reward_risk}R"
        return None

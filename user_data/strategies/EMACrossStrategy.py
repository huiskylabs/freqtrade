# EMA9/21 cross with 4h EMA21 filter (Backpack BTC futures)
from __future__ import annotations

from datetime import datetime
from pandas import DataFrame
import numpy as np
import talib.abstract as ta
from freqtrade.persistence import Trade
from freqtrade.strategy import IStrategy, informative, stoploss_from_absolute
from technical import qtpylib


class EMACrossStrategy(IStrategy):
    """
    2h EMA9/EMA21 cross, filtered by 4h close vs EMA21.
    Stop = tighter of opposite swing vs 1.5*ATR(14). TP = 2R. Risk 0.75%, lev ≤20.
    Chop filter: skip if |EMA9-EMA21|/ATR < 0.15.
    """

    INTERFACE_VERSION = 3
    can_short = True
    timeframe = "2h"
    startup_candle_count = 80
    process_only_new_candles = True

    minimal_roi = {"0": 100}
    stoploss = -0.99
    use_custom_stoploss = True
    trailing_stop = False
    use_exit_signal = False  # exits via stop / 2R only for first pass
    exit_profit_only = False

    risk_pct = 0.0075
    max_leverage_cap = 20.0
    reward_risk = 2.0
    atr_stop_mult = 1.5
    chop_atr_ratio = 0.15
    swing_lookback = 3
    min_stop_dist = 0.005

    order_types = {
        "entry": "limit",
        "exit": "limit",
        "stoploss": "market",
        "stoploss_on_exchange": False,
    }

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

    def _atr_stop_price(self, last, side: str, rate: float) -> float:
        atr = float(last.get("atr", np.nan))
        if not np.isfinite(atr) or atr <= 0:
            atr = rate * self.min_stop_dist
        if side == "long":
            return rate - self.atr_stop_mult * atr
        return rate + self.atr_stop_mult * atr

    def _tighter_stop(self, last, side: str, rate: float) -> float:
        swing = self._swing_stop_price(last, side, rate)
        atr_stop = self._atr_stop_price(last, side, rate)
        if side == "long":
            # tighter = closer to price from below = higher stop
            return max(swing, atr_stop)
        # short: tighter = closer from above = lower stop
        return min(swing, atr_stop)

    def _stop_dist_ratio(self, rate: float, stop: float, side: str) -> float:
        if side == "long":
            dist = (rate - stop) / rate
        else:
            dist = (stop - rate) / rate
        return float(max(dist, self.min_stop_dist))

    def _size_from_risk(self, rate: float, stop: float, side: str, max_leverage: float):
        dist = self._stop_dist_ratio(rate, stop, side)
        equity = float(self.wallets.get_total(self.config["stake_currency"]))
        risk_cash = equity * self.risk_pct
        notional = risk_cash / dist
        available = max(float(self.wallets.get_available_stake_amount()), 1.0)
        if notional <= available:
            lev, stake = 1.0, notional
        else:
            lev = min(self.max_leverage_cap, max_leverage, notional / available)
            lev = max(1.0, lev)
            stake = notional / lev
            max_notional = available * min(self.max_leverage_cap, max_leverage)
            if notional > max_notional:
                notional = max_notional
                stake = available
        return lev, stake, notional, dist, risk_cash

    @informative("4h")
    def populate_indicators_4h(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema21"] = ta.EMA(dataframe, timeperiod=21)
        dataframe["bias_long"] = dataframe["close"] > dataframe["ema21"]
        dataframe["bias_short"] = dataframe["close"] < dataframe["ema21"]
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema9"] = ta.EMA(dataframe, timeperiod=9)
        dataframe["ema21"] = ta.EMA(dataframe, timeperiod=21)
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)
        lb = self.swing_lookback
        low, high = dataframe["low"], dataframe["high"]
        dataframe["swing_low"] = low[low == low.rolling(lb * 2 + 1, center=True).min()]
        dataframe["swing_high"] = high[high == high.rolling(lb * 2 + 1, center=True).max()]
        dataframe["last_swing_low"] = dataframe["swing_low"].ffill()
        dataframe["last_swing_high"] = dataframe["swing_high"].ffill()
        dataframe["ema_sep"] = (dataframe["ema9"] - dataframe["ema21"]).abs()
        dataframe["not_chop"] = (dataframe["ema_sep"] / dataframe["atr"]) >= self.chop_atr_ratio
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        crossed_up = qtpylib.crossed_above(dataframe["ema9"], dataframe["ema21"])
        crossed_down = qtpylib.crossed_below(dataframe["ema9"], dataframe["ema21"])
        dataframe.loc[
            (
                crossed_up
                & dataframe["bias_long_4h"].fillna(False)
                & dataframe["not_chop"].fillna(False)
                & (dataframe["volume"] > 0)
            ),
            "enter_long",
        ] = 1
        dataframe.loc[
            (
                crossed_down
                & dataframe["bias_short_4h"].fillna(False)
                & dataframe["not_chop"].fillna(False)
                & (dataframe["volume"] > 0)
            ),
            "enter_short",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["exit_long"] = 0
        dataframe["exit_short"] = 0
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
        stop = self._tighter_stop(last, side, current_rate)
        lev, *_ = self._size_from_risk(current_rate, stop, side, max_leverage)
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
        stop = self._tighter_stop(last, side, current_rate)
        dist = self._stop_dist_ratio(current_rate, stop, side)
        equity = float(self.wallets.get_total(self.config["stake_currency"]))
        notional = (equity * self.risk_pct) / dist
        lev = max(float(leverage), 1.0)
        stake = notional / lev
        return float(max(float(min_stake or 0.0), min(stake, float(max_stake))))

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
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if dataframe is None or dataframe.empty:
            return None
        try:
            entry_candle = dataframe.loc[dataframe["date"] <= trade.open_date_utc].iloc[-1]
        except Exception:
            entry_candle = dataframe.iloc[-1]
        side = "short" if trade.is_short else "long"
        stop = self._tighter_stop(entry_candle, side, trade.open_rate)
        return stoploss_from_absolute(
            stop, current_rate, is_short=trade.is_short, leverage=trade.leverage or 1.0
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
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if dataframe is None or dataframe.empty:
            return None
        try:
            entry_candle = dataframe.loc[dataframe["date"] <= trade.open_date_utc].iloc[-1]
        except Exception:
            return None
        side = "short" if trade.is_short else "long"
        stop = self._tighter_stop(entry_candle, side, trade.open_rate)
        dist = self._stop_dist_ratio(trade.open_rate, stop, side)
        lev = trade.leverage or 1.0
        if current_profit / (dist * lev) >= self.reward_risk:
            return f"take_profit_{self.reward_risk}R"
        return None

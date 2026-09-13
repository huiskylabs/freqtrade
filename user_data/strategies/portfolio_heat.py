"""Portfolio heat + same-way seat governor for ScaleOut risk books."""
from __future__ import annotations

import logging
import math
from datetime import datetime

from freqtrade.persistence import LocalTrade, Trade

logger = logging.getLogger(__name__)

# Bases subject to same-way correlation cap; ZEC is heat-only.
SAME_WAY_BASES = {"BTC", "SOL", "HYPE"}


class PortfolioHeatMixin:
    """
    Enforce portfolio heat and same-way caps in confirm_trade_entry.

    Expects subclass attrs:
      risk_pct, portfolio_heat_cap, max_same_way, book_tag (optional)

    MRO: place this mixin *before* TrendPullbackScaleOutStrategy so
    confirm_trade_entry runs heat after RiskKillSwitchMixin via super().
    """

    risk_pct: float = 0.01
    portfolio_heat_cap: float = 0.02
    max_same_way: int = 2
    book_tag: str = "HEAT"

    def _pair_base(self, pair: str) -> str:
        return pair.split("/")[0].upper()

    def _max_open_seats(self) -> int:
        risk = float(self.risk_pct)
        if risk <= 0:
            return 0
        return int(math.floor(float(self.portfolio_heat_cap) / risk + 1e-12))

    def _fully_open_trades(self) -> list:
        """
        Open trades already on the book (excludes the trade being entered —
        confirm_trade_entry runs before LocalTrade.add_bt_trade).
        Prefer trades marked is_open; fall back across Trade / LocalTrade APIs
        so backtesting and live both bind.
        """
        trades: list = []
        try:
            trades = list(Trade.get_open_trades() or [])
        except Exception as e:
            logger.warning("%s get_open_trades failed: %s", self.book_tag, e)

        if not trades:
            try:
                trades = list(Trade.get_trades_proxy(is_open=True) or [])
            except Exception as e:
                logger.warning("%s get_trades_proxy failed: %s", self.book_tag, e)

        if not trades:
            try:
                trades = list(LocalTrade.get_trades_proxy(is_open=True) or [])
            except Exception as e:
                logger.warning("%s LocalTrade.get_trades_proxy failed: %s", self.book_tag, e)

        return [t for t in trades if getattr(t, "is_open", True)]

    def _open_count(self) -> int:
        by_list = len(self._fully_open_trades())
        by_api = by_list
        try:
            by_api = int(Trade.get_open_trade_count())
        except Exception as e:
            logger.warning("%s get_open_trade_count failed: %s", self.book_tag, e)
            try:
                by_api = int(LocalTrade.bt_open_open_trade_count)
            except Exception:
                by_api = by_list
        # Prefer the larger count so heat never under-counts in BT.
        n = max(by_list, by_api)
        logger.debug(
            "%s open_count list=%s api=%s -> %s",
            self.book_tag,
            by_list,
            by_api,
            n,
        )
        return n

    def _open_heat(self) -> float:
        return self._open_count() * float(self.risk_pct)

    def _same_way_count(self, side: str) -> int:
        want_short = side == "short"
        n = 0
        for t in self._fully_open_trades():
            base = self._pair_base(t.pair)
            if base not in SAME_WAY_BASES:
                continue
            if bool(t.is_short) == want_short:
                n += 1
        return n

    def confirm_trade_entry(
        self,
        pair: str,
        order_type: str,
        amount: float,
        rate: float,
        time_in_force: str,
        current_time: datetime,
        entry_tag: str | None,
        side: str,
        **kwargs,
    ) -> bool:
        # Kill-switch (RiskKillSwitchMixin) and any parent gates first.
        if not super().confirm_trade_entry(  # type: ignore[misc]
            pair,
            order_type,
            amount,
            rate,
            time_in_force,
            current_time,
            entry_tag,
            side,
            **kwargs,
        ):
            return False

        risk = float(self.risk_pct)
        heat_cap = float(self.portfolio_heat_cap)
        open_count = self._open_count()
        max_seats = self._max_open_seats()
        projected_heat = open_count * risk + risk

        logger.info(
            "%s heat check: open=%s max_seats=%s heat=%.4f+%.4f cap=%.4f pair=%s",
            self.book_tag,
            open_count,
            max_seats,
            open_count * risk,
            risk,
            heat_cap,
            pair,
        )

        if max_seats <= 0 or open_count + 1 > max_seats:
            logger.info(
                "%s seat block: open=%s +1 > max_seats=%s (floor cap/risk) pair=%s",
                self.book_tag,
                open_count,
                max_seats,
                pair,
            )
            return False

        if projected_heat > heat_cap + 1e-12:
            logger.info(
                "%s heat block: heat=%.4f > cap=%.4f pair=%s",
                self.book_tag,
                projected_heat,
                heat_cap,
                pair,
            )
            return False

        base = self._pair_base(pair)
        if base in SAME_WAY_BASES:
            sw = self._same_way_count(side)
            if sw + 1 > int(self.max_same_way):
                logger.info(
                    "%s same-way block: %s count=%s +1 > max=%s pair=%s",
                    self.book_tag,
                    side,
                    sw,
                    self.max_same_way,
                    pair,
                )
                return False
        return True

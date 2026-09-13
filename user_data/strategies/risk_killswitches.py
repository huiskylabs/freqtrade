"""Account-level kill-switches for dry-run / live (Risk v1 book)."""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any

from freqtrade.persistence import Trade

logger = logging.getLogger(__name__)


class RiskKillSwitchMixin:
    """
    Enforce Risk / Position Manager v1 book:
    - Daily: -1.5% halt new; -2.0% flatten-all + halt
    - Weekly: -3.5% halt new + alert
    - Peak HWM DD: -4.0% flatten-all + halt
    - API unhealthy: halt new
    - Anomalous slip >0.5%: halt new + alert
    - Margin breach: halt new
    """

    # thresholds (fractions of equity)
    daily_halt_pct = 0.015
    daily_flatten_pct = 0.020
    weekly_halt_pct = 0.035
    peak_dd_flatten_pct = 0.040
    slip_halt_pct = 0.005
    margin_free_min_pct = 0.05  # halt if free/total < 5% while leveraged exposure exists
    api_error_halt_count = 3

    def _rk_init(self) -> None:
        if getattr(self, "_rk_ready", False):
            return
        self._rk_ready = True
        self._rk_day_key: str | None = None
        self._rk_week_key: str | None = None
        self._rk_day_start_equity: float | None = None
        self._rk_week_start_equity: float | None = None
        self._rk_hwm: float | None = None
        self._rk_halt_new = False
        self._rk_flatten = False
        self._rk_halt_reasons: list[str] = []
        self._rk_api_errors = 0
        self._rk_last_status = ""

    def _rk_equity(self) -> float:
        stake = self.config["stake_currency"]
        try:
            return float(self.wallets.get_total(stake))
        except Exception:
            return float(self.config.get("dry_run_wallet", 0) or 0)

    def _rk_set_halt(self, reason: str, flatten: bool = False) -> None:
        self._rk_halt_new = True
        if flatten:
            self._rk_flatten = True
        if reason not in self._rk_halt_reasons:
            self._rk_halt_reasons.append(reason)
            logger.warning("RISK_KILL: %s (flatten=%s)", reason, flatten)

    def _rk_maybe_roll_windows(self, current_time: datetime, equity: float) -> None:
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)
        day_key = current_time.strftime("%Y-%m-%d")
        # ISO week
        iso = current_time.isocalendar()
        week_key = f"{iso.year}-W{iso.week:02d}"

        if self._rk_day_key != day_key:
            self._rk_day_key = day_key
            self._rk_day_start_equity = equity
            # new day clears daily halt unless weekly/peak/api still active
            self._rk_clear_daily_halts()
            logger.info("RISK_KILL: day start equity=%.4f", equity)

        if self._rk_week_key != week_key:
            self._rk_week_key = week_key
            self._rk_week_start_equity = equity
            self._rk_clear_weekly_halts()
            logger.info("RISK_KILL: week start equity=%.4f", equity)

        if self._rk_hwm is None or equity > self._rk_hwm:
            self._rk_hwm = equity

    def _rk_clear_daily_halts(self) -> None:
        keep = [r for r in self._rk_halt_reasons if not r.startswith("daily_")]
        self._rk_halt_reasons = keep
        if not any(r.startswith(("weekly_", "peak_", "api_", "slip_", "margin_")) for r in keep):
            # only auto-clear flatten if it was daily-only
            if not keep:
                self._rk_halt_new = False
                self._rk_flatten = False

    def _rk_clear_weekly_halts(self) -> None:
        self._rk_halt_reasons = [r for r in self._rk_halt_reasons if not r.startswith("weekly_")]

    def bot_loop_start(self, current_time: datetime, **kwargs) -> None:
        # Backtest/hyperopt: skip live API/margin probes and in-run halt/flatten.
        # Daily -1.5/-2.0 and HWM -4.0 trip rates are scored post-hoc from the
        # wallet curve so TP variants stay comparable to the published 2R path.
        rm = self.config.get("runmode")
        rm_val = getattr(rm, "value", rm)
        if str(rm_val) in ("backtest", "hyperopt"):
            return
        self._rk_init()
        equity = self._rk_equity()
        if equity <= 0:
            return
        self._rk_maybe_roll_windows(current_time, equity)

        day0 = self._rk_day_start_equity or equity
        week0 = self._rk_week_start_equity or equity
        hwm = self._rk_hwm or equity

        daily_pnl_pct = (equity - day0) / day0 if day0 else 0.0
        weekly_pnl_pct = (equity - week0) / week0 if week0 else 0.0
        peak_dd_pct = (hwm - equity) / hwm if hwm else 0.0

        if daily_pnl_pct <= -self.daily_flatten_pct:
            self._rk_set_halt(f"daily_flatten_{daily_pnl_pct:.4f}", flatten=True)
        elif daily_pnl_pct <= -self.daily_halt_pct:
            self._rk_set_halt(f"daily_halt_{daily_pnl_pct:.4f}", flatten=False)

        if weekly_pnl_pct <= -self.weekly_halt_pct:
            self._rk_set_halt(f"weekly_halt_{weekly_pnl_pct:.4f}", flatten=False)

        if peak_dd_pct >= self.peak_dd_flatten_pct:
            self._rk_set_halt(f"peak_dd_flatten_{peak_dd_pct:.4f}", flatten=True)

        # API health probe (lightweight)
        try:
            ex = self.dp._exchange  # type: ignore[attr-defined]
            if ex is not None:
                # fetch one ticker for whitelist pair
                pair = (self.config.get("exchange") or {}).get("pair_whitelist", [None])[0]
                if pair:
                    ex.fetch_ticker(pair)
                self._rk_api_errors = 0
        except Exception as e:
            self._rk_api_errors += 1
            logger.warning("RISK_KILL: API probe error (%s) count=%s", e, self._rk_api_errors)
            if self._rk_api_errors >= self.api_error_halt_count:
                self._rk_set_halt(f"api_unhealthy_{self._rk_api_errors}", flatten=False)

        # Margin health
        try:
            stake = self.config["stake_currency"]
            total = float(self.wallets.get_total(stake))
            free = float(self.wallets.get_free(stake))
            if total > 0 and free / total < self.margin_free_min_pct:
                open_trades = Trade.get_open_trades()
                if open_trades:
                    self._rk_set_halt(f"margin_breach_free_{free/total:.4f}", flatten=False)
        except Exception:
            pass

        status = (
            f"eq={equity:.2f} dayPnL={daily_pnl_pct:.3%} weekPnL={weekly_pnl_pct:.3%} "
            f"peakDD={peak_dd_pct:.3%} halt={self._rk_halt_new} flatten={self._rk_flatten} "
            f"reasons={self._rk_halt_reasons}"
        )
        if status != self._rk_last_status:
            logger.info("RISK_KILL status: %s", status)
            self._rk_last_status = status

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
        self._rk_init()
        if self._rk_halt_new or self._rk_flatten:
            logger.warning(
                "RISK_KILL: blocked entry %s %s reasons=%s",
                side,
                pair,
                self._rk_halt_reasons,
            )
            return False
        return True

    def order_filled(
        self, pair: str, trade: Trade, order: Any, current_time: datetime, **kwargs
    ) -> None:
        """Halt on anomalous slippage vs expected order price."""
        self._rk_init()
        try:
            expected = float(getattr(order, "ft_order_price", None) or getattr(order, "price", 0) or 0)
            filled = float(getattr(order, "safe_price", None) or getattr(order, "average", None) or 0)
            if expected > 0 and filled > 0:
                slip = abs(filled - expected) / expected
                if slip > self.slip_halt_pct:
                    self._rk_set_halt(f"slip_anomaly_{slip:.4f}", flatten=False)
                    logger.warning(
                        "RISK_KILL: slip %.3f%% on %s (expected=%s filled=%s)",
                        slip * 100,
                        pair,
                        expected,
                        filled,
                    )
        except Exception as e:
            logger.debug("RISK_KILL slip check skipped: %s", e)

    def risk_custom_exit_reason(self, trade: Trade) -> str | None:
        self._rk_init()
        if self._rk_flatten:
            reason = self._rk_halt_reasons[-1] if self._rk_halt_reasons else "risk_flatten"
            return f"risk_flatten:{reason}"
        return None

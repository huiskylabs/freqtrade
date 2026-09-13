# ScaleOut AGGRESSIVE book: risk 2%, lev cap 20, heat max 4%, same-way max 3 (BTC/SOL/HYPE)
from __future__ import annotations

from portfolio_heat import PortfolioHeatMixin
from TrendPullbackScaleOutStrategy import TrendPullbackScaleOutStrategy


class TrendPullbackScaleOutAggressive(PortfolioHeatMixin, TrendPullbackScaleOutStrategy):
    """
    AGGRESSIVE risk book on ScaleOut:
      risk_pct=0.02, max_leverage_cap=20
      portfolio heat max 4% → max_open_seats=2
      max 3 same-way seats among {BTC,SOL,HYPE}; ZEC only heat-gated

    MRO: PortfolioHeatMixin → ScaleOut → TrendPullback → RiskKillSwitchMixin → IStrategy
    so confirm_trade_entry runs kill-switch (via super) then heat/same-way.
    """

    risk_pct = 0.02
    max_leverage_cap = 20.0
    portfolio_heat_cap = 0.04
    max_same_way = 3
    book_tag = "AGGRESSIVE"

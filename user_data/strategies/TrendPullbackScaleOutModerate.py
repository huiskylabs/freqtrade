# ScaleOut MODERATE book: risk 1%, lev cap 15, heat max 2%, same-way max 2 (BTC/SOL/HYPE)
from __future__ import annotations

from portfolio_heat import PortfolioHeatMixin
from TrendPullbackScaleOutStrategy import TrendPullbackScaleOutStrategy


class TrendPullbackScaleOutModerate(PortfolioHeatMixin, TrendPullbackScaleOutStrategy):
    """
    MODERATE risk book on ScaleOut:
      risk_pct=0.01, max_leverage_cap=15
      portfolio heat max 2% (sum of open risk_pct) → max_open_seats=2
      max 2 same-way seats among {BTC,SOL,HYPE}; ZEC only heat-gated

    MRO: PortfolioHeatMixin → ScaleOut → TrendPullback → RiskKillSwitchMixin → IStrategy
    so confirm_trade_entry runs kill-switch (via super) then heat/same-way.
    """

    risk_pct = 0.01
    max_leverage_cap = 15.0
    portfolio_heat_cap = 0.02
    max_same_way = 2
    book_tag = "MODERATE"

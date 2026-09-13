# Research-only: risk 5%, lev 20, heat 10%, same-way 3 — DD gate compare (not live)
from __future__ import annotations

from portfolio_heat import PortfolioHeatMixin
from TrendPullbackScaleOutStrategy import TrendPullbackScaleOutStrategy


class TrendPullbackScaleOutRisk5(PortfolioHeatMixin, TrendPullbackScaleOutStrategy):
    risk_pct = 0.05
    max_leverage_cap = 20.0
    portfolio_heat_cap = 0.10
    max_same_way = 3
    book_tag = "RISK5_RESEARCH"

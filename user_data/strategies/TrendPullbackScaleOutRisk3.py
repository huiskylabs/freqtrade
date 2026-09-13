# Research-only: risk 3%, lev 20, heat 6%, same-way 3 — DD gate compare (not live)
from __future__ import annotations

from portfolio_heat import PortfolioHeatMixin
from TrendPullbackScaleOutStrategy import TrendPullbackScaleOutStrategy


class TrendPullbackScaleOutRisk3(PortfolioHeatMixin, TrendPullbackScaleOutStrategy):
    risk_pct = 0.03
    max_leverage_cap = 20.0
    portfolio_heat_cap = 0.06
    max_same_way = 3
    book_tag = "RISK3_RESEARCH"

# ScaleOut VERY-AGGRESSIVE book: significantly increased risk
from __future__ import annotations

from portfolio_heat import PortfolioHeatMixin
from TrendPullbackScaleOutStrategy import TrendPullbackScaleOutStrategy


class TrendPullbackScaleOutVeryAggressive(PortfolioHeatMixin, TrendPullbackScaleOutStrategy):
    """
    VERY-AGGRESSIVE risk book on ScaleOut:
      risk_pct=0.03 (3% per trade)
      max_leverage_cap=20
      portfolio_heat_cap=0.09 (9% total heat) → max_open_seats=3
      max 3 same-way seats among {BTC,SOL,HYPE}
      pullback_band=0.09 (9% wider entry band)
    
    MRO: PortfolioHeatMixin → ScaleOut → TrendPullback → RiskKillSwitchMixin → IStrategy
    """

    risk_pct = 0.03
    max_leverage_cap = 20.0
    portfolio_heat_cap = 0.09
    max_same_way = 3
    pullback_band = 0.09  # 9% pullback
    book_tag = "VERY_AGGRESSIVE"

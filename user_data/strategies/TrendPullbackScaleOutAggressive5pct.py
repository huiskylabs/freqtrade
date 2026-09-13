# ScaleOut AGGRESSIVE 5% book: moderate-aggressive risk
from __future__ import annotations

from portfolio_heat import PortfolioHeatMixin
from TrendPullbackScaleOutStrategy import TrendPullbackScaleOutStrategy


class TrendPullbackScaleOutAggressive5pct(PortfolioHeatMixin, TrendPullbackScaleOutStrategy):
    """
    AGGRESSIVE-5PCT risk book on ScaleOut:
      risk_pct=0.02 (2% per trade)
      max_leverage_cap=20
      portfolio_heat_cap=0.05 (5% total heat) → max_open_seats=2-3
      max 2 same-way seats among {BTC,SOL,HYPE}
      pullback_band=0.05 (5% wider entry band)
    
    MRO: PortfolioHeatMixin → ScaleOut → TrendPullback → RiskKillSwitchMixin → IStrategy
    """

    risk_pct = 0.02
    max_leverage_cap = 20.0
    portfolio_heat_cap = 0.05
    max_same_way = 2
    pullback_band = 0.05  # 5% pullback
    book_tag = "AGGRESSIVE_5PCT"

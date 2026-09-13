# ScaleOut HYPER-AGGRESSIVE book: increased risk, pullback, and heat
from __future__ import annotations

from portfolio_heat import PortfolioHeatMixin
from TrendPullbackScaleOutStrategy import TrendPullbackScaleOutStrategy


class TrendPullbackScaleOutHyperAggressive(PortfolioHeatMixin, TrendPullbackScaleOutStrategy):
    """
    HYPER-AGGRESSIVE risk book on ScaleOut:
      risk_pct=0.05 (5% per trade)
      max_leverage_cap=20
      portfolio_heat_cap=0.15 (15% total heat) → max_open_seats=3
      max 3 same-way seats among {BTC,SOL,HYPE}
      pullback_band=0.15 (15% wider entry band)
    
    MRO: PortfolioHeatMixin → ScaleOut → TrendPullback → RiskKillSwitchMixin → IStrategy
    """

    risk_pct = 0.05
    max_leverage_cap = 20.0
    portfolio_heat_cap = 0.15
    max_same_way = 3
    pullback_band = 0.15  # 15% pullback vs 0.8% moderate
    book_tag = "HYPER_AGGRESSIVE"

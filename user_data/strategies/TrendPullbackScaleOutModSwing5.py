# Research stops A/B: Moderate 25%@2R with swing_lookback=5 (was 3)
from __future__ import annotations

from TrendPullbackScaleOutModerate import TrendPullbackScaleOutModerate


class TrendPullbackScaleOutModSwing5(TrendPullbackScaleOutModerate):
    """Same Moderate / 25%@2R; wider swing structural stop via lookback 5."""

    book_tag = "MOD_SWING5"
    swing_lookback = 5

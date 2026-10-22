"""Sell rules.

The system sells for two reasons only:

1. **Rank failure** — the name falls out of the buffer (handled in portfolio.py).
2. **Quality deterioration** — the name is still cheap-looking but its business
   quality collapsed.  Without this rule a deteriorating business can hide just
   inside the buffer for several quarters, which is exactly the "hold your
   losers" failure mode the rule is meant to prevent.
"""

from __future__ import annotations

import pandas as pd


def quality_deterioration(
    quality_now: pd.Series,
    quality_prev: pd.Series,
    pct: float = 0.25,
    decline: float = 0.30,
) -> list[str]:
    """Names now in the bottom ``pct`` of quality whose score fell by ``decline``.

    ``quality_now`` / ``quality_prev`` are raw (not rank-normalised) values so a
    decline is comparable across quarters.  The percentile is cross-sectional on
    the current date, so it never looks forward.
    """
    if quality_now.empty or quality_prev.empty:
        return []
    now = quality_now.dropna()
    if now.empty:
        return []
    prev = quality_prev.reindex(now.index)
    floor = now.rank(pct=True) <= pct
    base = prev.abs().replace(0, pd.NA)
    fall = (prev - now) / base
    fall = fall.replace([float("inf"), float("-inf")], pd.NA)
    flag = floor & (fall >= decline)
    return sorted(flag[flag.fillna(False)].index.tolist())

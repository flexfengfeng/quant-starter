"""From cross-sectional scores to target weights.

Rules, in priority order:

1. Only names with all factors present are eligible.
2. A current holding is kept while its rank stays inside ``top_n * sell_rank_buffer``
   (the buffer is what stops the portfolio from churning on rank noise).
3. Anything flagged by ``quality_deterioration`` is evicted regardless of rank.
4. Equal weight, cash floor, then sector cap by dropping the weakest name in the
   offending sector.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from .sells import quality_deterioration


@dataclass
class Target:
    weights: dict[str, float] = field(default_factory=dict)
    cash: float = 1.0
    reasons: dict[str, str] = field(default_factory=dict)


def build_target(
    scores: pd.DataFrame,
    universe: pd.DataFrame,
    quality_raw: pd.Series,
    quality_prev: pd.Series | None,
    current: list[str],
    cfg,
) -> Target:
    sel, port = cfg.strategy, cfg.portfolio
    sector = universe.set_index("ticker")["sector"].to_dict()

    ranked = scores[scores["eligible"]].sort_values(
        ["composite", "ticker"], ascending=[False, True], kind="mergesort"
    )
    rank = {tk: i + 1 for i, tk in enumerate(ranked.index)}
    reasons: dict[str, str] = {}

    evict = set()
    if quality_prev is not None and len(quality_prev):
        evict = set(
            quality_deterioration(
                quality_raw, quality_prev,
                pct=port.quality_sell_pct, decline=port.quality_sell_decline,
            )
        )

    # Sector capacity is decided while filling, not after: dropping a name later
    # leaves the portfolio under-invested, which is a cash bet nobody asked for.
    capacity = max(1, int(port.max_sector * sel.top_n))
    counts: dict[str, int] = {}

    def add(tk: str) -> bool:
        sec = sector.get(tk, "UNKNOWN")
        if counts.get(sec, 0) >= capacity:
            return False
        chosen.append(tk)
        counts[sec] = counts.get(sec, 0) + 1
        return True

    chosen: list[str] = []
    buffer_rank = sel.top_n * port.sell_rank_buffer
    kept = [tk for tk in current if tk in rank and rank[tk] <= buffer_rank and tk not in evict]
    for tk in sorted(kept, key=lambda t: rank[t]):
        if len(chosen) >= sel.top_n:
            break
        if add(tk):
            reasons[tk] = f"kept (rank {rank[tk]})"
    for tk in ranked.index:
        if len(chosen) >= sel.top_n:
            break
        if tk in chosen or tk in evict:
            continue
        if add(tk):
            reasons[tk] = f"new (rank {rank[tk]})"
    for tk in sorted(evict):
        reasons[tk] = "evicted (quality deterioration)"

    chosen = _apply_sector_cap(chosen, rank, sector, cfg)

    if not chosen:
        return Target(weights={}, cash=1.0, reasons=reasons)

    eq = (1.0 - port.min_cash) / len(chosen)
    weights = {tk: min(eq, port.max_weight) for tk in chosen}
    invested = sum(weights.values())
    # single-name cap released the remainder; spread it over uncapped names only
    for _ in range(10):
        free = [tk for tk in chosen if weights[tk] < port.max_weight - 1e-12]
        spare = (1.0 - port.min_cash) - invested
        if spare <= 1e-9 or not free:
            break
        add = spare / len(free)
        for tk in free:
            delta = min(add, port.max_weight - weights[tk])
            weights[tk] += delta
            invested += delta

    cash = max(port.min_cash, 1.0 - sum(weights.values()))
    return Target(weights=weights, cash=cash, reasons=reasons)


def _apply_sector_cap(chosen, rank, sector, cfg) -> list[str]:
    """Drop the lowest-ranked name in any sector over its cap, until all fit.

    We do not refill from the same sector: a cap that can be refilled is not a cap.
    """
    cap = cfg.portfolio.max_sector
    chosen = list(chosen)
    for _ in range(50):
        if not chosen:
            break
        eq = 1.0 / len(chosen)
        by_sector: dict[str, list[str]] = {}
        for tk in chosen:
            by_sector.setdefault(sector.get(tk, "UNKNOWN"), []).append(tk)
        over = {s: names for s, names in by_sector.items() if len(names) * eq > cap + 1e-12}
        if not over:
            break
        # drop the weakest name of the largest offending sector
        sec = max(over, key=lambda s: len(over[s]))
        weakest = max(over[sec], key=lambda tk: rank.get(tk, 10**9))
        chosen.remove(weakest)
    return chosen

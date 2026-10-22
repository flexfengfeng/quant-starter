"""Paper-trading helpers that need no broker.

The point of a paper phase is not "pretend to trade" — it is to compare, every
quarter, what the system *told you to do* against what you actually did, and
against what the backtest said would happen.  That comparison is the only
honest bridge between backtest and live money.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from ..data.features import raw_factors, score
from ..strategy.portfolio import build_target


@dataclass
class PaperState:
    cash: float = 100_000.0
    positions: dict[str, float] = field(default_factory=dict)  # ticker -> shares
    asof: str = ""

    @classmethod
    def load(cls, path: str | Path) -> "PaperState":
        p = Path(path)
        if not p.exists():
            return cls()
        raw = json.loads(p.read_text())
        return cls(cash=raw.get("cash", 100_000.0), positions=raw.get("positions", {}), asof=raw.get("asof", ""))

    def save(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(
            {"cash": self.cash, "positions": self.positions, "asof": self.asof}, indent=2))


def latest_target(cfg, prices: pd.DataFrame, fund: pd.DataFrame, universe: pd.DataFrame,
                  current: list[str] | None = None):
    """Signals as of the last date in the data — what the system says to hold today."""
    from ..data.loader import price_matrix

    px = price_matrix(prices).sort_index().ffill()
    asof = px.index[-1]
    raw = raw_factors(px, fund, asof, cfg)
    sc = score(raw, cfg)
    tgt = build_target(sc, universe, raw["quality"], None, current or [], cfg)
    return asof, px, sc, tgt


def plan_orders(cfg, prices: pd.DataFrame, fund: pd.DataFrame, universe: pd.DataFrame,
                state: PaperState, min_order_usd: float = 200.0) -> pd.DataFrame:
    asof, px, sc, tgt = latest_target(cfg, prices, fund, universe, list(state.positions))
    pt = px.iloc[-1]
    nav = state.cash + sum(v * pt[k] for k, v in state.positions.items() if k in pt.index)
    desired = {k: w * nav for k, w in tgt.weights.items()}
    rows = []
    for tk in sorted(set(state.positions) | set(desired)):
        cur = state.positions.get(tk, 0.0) * pt.get(tk, 0.0)
        delta = desired.get(tk, 0.0) - cur
        if abs(delta) < min_order_usd:
            continue
        rows.append({
            "asof": asof.date(),
            "ticker": tk,
            "side": "BUY" if delta > 0 else "SELL",
            "notional": round(abs(delta), 2),
            "shares": round(abs(delta) / pt[tk], 4) if pt.get(tk) else None,
            "price": round(float(pt[tk]), 2) if pt.get(tk) else None,
        })
    return pd.DataFrame(rows)

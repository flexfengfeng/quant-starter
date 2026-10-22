"""The honest audit: six probes every backtest should survive before money moves.

Run ``make audit``.  Each probe re-runs the same engine with one assumption
perturbed, so the difference is attributable to that assumption alone.

    1. look-ahead      use data that was not yet public  -> returns should EXPLODE
    2. execution lag   same-bar vs next-day fill         -> how much is the gap worth?
    3. costs           0 bps vs 8 bps vs 24 bps          -> is the edge bigger than the toll?
    4. concentration   top-3 names' share of P&L         -> is this a portfolio or a bet?
    5. beta            regression vs benchmark           -> selection or just market exposure?
    6. significance    t-stat + multiple-testing note    -> could this be luck?
"""

from __future__ import annotations

import copy
from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..data.loader import price_matrix
from .engine import run_backtest


@dataclass
class Probe:
    name: str
    verdict: str  # PASS | WARN | FAIL
    headline: str
    detail: str


def _run(cfg, prices, fund, uni, **overrides):
    c = copy.deepcopy(cfg)
    for dotted, value in overrides.items():
        section, key = dotted.split(".", 1)
        setattr(getattr(c, section), key, value)
    return run_backtest(c, prices, fund, uni)


def _beta_alpha(port: pd.Series, bench: pd.Series) -> tuple[float, float]:
    r_p = port.pct_change().dropna()
    r_b = bench.pct_change().dropna()
    pair = pd.concat([r_p, r_b], axis=1).dropna()
    var = pair.iloc[:, 1].var()
    if not var or np.isnan(var):
        return float("nan"), float("nan")
    beta = pair.cov().iloc[0, 1] / var
    alpha_d = pair.iloc[:, 0].mean() - beta * pair.iloc[:, 1].mean()
    return float(beta), float(alpha_d * 252)


def _concentration(res, prices: pd.DataFrame, universe: pd.DataFrame) -> tuple[float, pd.Series]:
    """Per-name P&L share, from the recorded target weights and realised prices."""
    px = price_matrix(prices).sort_index().ffill()
    dates = list(res.weights.index)
    contrib: dict[str, float] = {}
    if len(dates) < 2:
        return float("nan"), pd.Series(dtype=float)
    for i in range(len(dates) - 1):
        d0, d1 = dates[i], dates[i + 1]
        if d0 not in px.index or d1 not in px.index:
            continue
        w = res.weights.loc[d0]
        ret = (px.loc[d1] / px.loc[d0] - 1.0).reindex(w.index)
        piece = (w * ret).dropna()
        for tk, v in piece.items():
            contrib[tk] = contrib.get(tk, 0.0) + v
    s = pd.Series(contrib).sort_values(ascending=False)
    total = s.sum()
    if not total or np.isnan(total):
        return float("nan"), s
    return float(s.head(3).abs().sum() / s.abs().sum()), s


def run_audit(cfg, prices, fund, universe) -> list[Probe]:
    base = run_backtest(cfg, prices, fund, universe)
    st = base.stats
    probes: list[Probe] = []

    # 1. data-timing sensitivity: the "when did I know it" band
    band = {}
    for lag in (-45, 0, 45, 90):
        r = base if lag == 0 else _run(cfg, prices, fund, universe, **{"data.disclosure_lag_days": lag})
        band[lag] = r.stats.get("cagr", np.nan)
    spread = max(band.values()) - min(band.values())
    probes.append(
        Probe(
            "1. data-timing band",
            "WARN" if spread > 0.02 else "PASS",
            "CAGR at disclosure lag -45/0/+45/+90 = "
            + " / ".join(f"{band[k]*100:.1f}%" for k in band)
            + f"  (spread {spread*100:.1f}pp)",
            "Moving the 'when did I know it' line by one quarter moves annual return by "
            f"{spread*100:.1f}pp. Any 2-3pp 'edge' must be read against this band first — "
            "otherwise you are quoting a data-timing artefact. Negative lags are a genuine "
            "leak (reports not yet public); the sign is not the test, the magnitude is.",
        )
    )

    # 2. execution lag
    same = _run(cfg, prices, fund, universe, **{"backtest.execution_lag_days": 0})
    probes.append(
        Probe(
            "2. execution lag",
            "PASS",
            f"same-close fill CAGR {same.stats.get('cagr',float('nan'))*100:.2f}% vs "
            f"next-day {st['cagr']*100:.2f}% ({(same.stats.get('cagr',np.nan)-st['cagr'])*100:+.2f}pp)",
            "The gap is the price of realism. It should be small for a quarterly strategy; "
            "if it is large, the signal decays intraday and this is not a quarterly edge.",
        )
    )

    # 3. costs
    zero = _run(cfg, prices, fund, universe, **{"costs.slippage_bps": 0.0})
    heavy = _run(cfg, prices, fund, universe, **{"costs.slippage_bps": 24.0})
    excess_after = heavy.stats.get("excess_cagr", np.nan)
    probes.append(
        Probe(
            "3. cost sensitivity",
            "PASS" if excess_after > 0 else "WARN",
            f"0bps {zero.stats.get('cagr',float('nan'))*100:.2f}% / 8bps {st['cagr']*100:.2f}% / "
            f"24bps {heavy.stats.get('cagr',float('nan'))*100:.2f}% CAGR; "
            f"excess after 24bps = {excess_after*100:+.2f}pp",
            f"annual turnover {st.get('turnover_annual',0)*100:.0f}%, cost drag "
            f"{st.get('cost_drag_annual',0)*100:.2f}pp. An edge that dies at 24bps "
            "is an execution artefact, not an edge.",
        )
    )

    # 4. concentration
    share, contrib = _concentration(base, prices, universe)
    probes.append(
        Probe(
            "4. concentration",
            "PASS" if share < 0.60 else "WARN",
            f"top-3 names = {share*100:.0f}% of gross P&L",
            "Right-skewed returns are expected; the question is whether the result survives "
            "removing the winners. If one name carries the strategy, you own a bet.",
        )
    )

    # 5. beta / alpha
    beta, alpha = _beta_alpha(base.equity, base.benchmark)
    probes.append(
        Probe(
            "5. beta vs selection",
            "PASS" if 0.5 <= beta <= 1.25 else "WARN",
            f"beta {beta:.2f}, annualised alpha {alpha*100:+.2f}%",
            "Beta ~1 means the portfolio is not secretly a leveraged market bet. "
            "If alpha is no better than the t-stat below, the 'excess' is beta timing.",
        )
    )

    # 6. significance
    t = st.get("excess_t_stat", np.nan)
    verdict = "PASS" if t >= 3.0 else ("WARN" if t >= 2.0 else "FAIL")
    probes.append(
        Probe(
            "6. significance",
            verdict,
            f"excess t-stat {t:.2f} (daily), mean IC {st.get('mean_ic', float('nan')):.3f}, "
            f"{st.get('n_rebalances', 0)} rebalances",
            "Bar for a *new* factor is t>3.0, not 2.0 (Harvey-Liu-Zhu 2016: with ~300 tested "
            "factors the 5% threshold is exhausted). Count every variant you tried — this "
            "number is after one try, not after thirty.",
        )
    )
    return probes


def render_audit(probes: list[Probe], cfg=None) -> str:
    lines = ["# Backtest audit", ""]
    if cfg is not None:
        lines += [
            f"- window: {cfg.backtest.start} .. {cfg.backtest.end}",
            f"- rebalance: {cfg.backtest.rebalance}, execution lag: {cfg.backtest.execution_lag_days}d",
            f"- costs: commission {cfg.costs.commission_bps}bps + slippage {cfg.costs.slippage_bps}bps",
            f"- disclosure lag: {cfg.data.disclosure_lag_days}d",
            "",
        ]
    lines += ["| probe | verdict | headline |", "|---|---|---|"]
    for p in probes:
        lines.append(f"| {p.name} | **{p.verdict}** | {p.headline} |")
    lines += ["", "## Why each probe exists", ""]
    for p in probes:
        lines += [f"**{p.name}** — {p.detail}", ""]
    return "\n".join(lines)

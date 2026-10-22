"""Performance statistics.

Kept deliberately small: the point is that every number a student quotes can be
recomputed by hand from the equity curve.  No library, no magic.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def drawdown(equity: pd.Series) -> pd.Series:
    return equity / equity.cummax() - 1.0


def summarize(equity: pd.Series, benchmark: pd.Series | None = None) -> dict:
    equity = equity.dropna()
    if len(equity) < 2:
        return {}
    rets = equity.pct_change().dropna()
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    cagr = (equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1 if years > 0 else np.nan
    vol = rets.std(ddof=1) * np.sqrt(TRADING_DAYS)
    dd = drawdown(equity)
    out = {
        "start": str(equity.index[0].date()),
        "end": str(equity.index[-1].date()),
        "years": round(years, 2),
        "cagr": cagr,
        "vol": vol,
        "sharpe": cagr / vol if vol else np.nan,
        "max_drawdown": float(dd.min()),
        "calmar": cagr / abs(dd.min()) if dd.min() else np.nan,
        "final_nav": float(equity.iloc[-1]),
        "n_days": int(len(equity)),
    }
    if benchmark is not None and len(benchmark.dropna()) > 1:
        b = benchmark.dropna()
        byears = (b.index[-1] - b.index[0]).days / 365.25
        bcagr = (b.iloc[-1] / b.iloc[0]) ** (1 / byears) - 1 if byears > 0 else np.nan
        bvol = b.pct_change().dropna().std(ddof=1) * np.sqrt(TRADING_DAYS)
        out.update(
            {
                "benchmark_cagr": bcagr,
                "benchmark_vol": bvol,
                "benchmark_sharpe": bcagr / bvol if bvol else np.nan,
                "excess_cagr": cagr - bcagr,
            }
        )
        # t-stat of the *daily* excess return: the naive significance test that
        # most backtests should show and almost none do.
        diff = (equity.pct_change() - b.pct_change()).dropna()
        t = diff.mean() / diff.std(ddof=1) * np.sqrt(len(diff)) if diff.std(ddof=1) else np.nan
        out["excess_t_stat"] = float(t) if t == t else np.nan
        out["info_ratio"] = (
            float(diff.mean() / diff.std(ddof=1) * np.sqrt(TRADING_DAYS)) if diff.std(ddof=1) else np.nan
        )
    return out


def rolling_excess(equity: pd.Series, benchmark: pd.Series, years: int) -> float:
    """Annualised excess over the trailing ``years`` (both rebased at the window start)."""
    end = min(equity.index[-1], benchmark.index[-1])
    start = end - pd.DateOffset(years=years)
    e = equity.loc[start:end]
    b = benchmark.loc[start:end]
    if len(e) < 252 * years * 0.9 or len(b) < 2:
        return float("nan")
    n = (e.index[-1] - e.index[0]).days / 365.25
    return (e.iloc[-1] / e.iloc[0]) ** (1 / n) - (b.iloc[-1] / b.iloc[0]) ** (1 / n)


def format_stats(stats: dict) -> str:
    pct = [k for k in stats if k in {"cagr", "vol", "max_drawdown", "excess_cagr",
                                     "benchmark_cagr", "benchmark_vol", "info_ratio"}]
    rows = []
    for k, v in stats.items():
        if isinstance(v, float):
            rows.append(f"{k:22s} {v*100:8.2f}%" if k in pct else f"{k:22s} {v:8.3f}")
        else:
            rows.append(f"{k:22s} {v}")
    return "\n".join(rows)

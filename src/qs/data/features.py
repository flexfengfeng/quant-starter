"""Point-in-time features.

The single most important function in this repo is ``available_fundamentals``:
it answers "what did I actually know on the rebalance date?".  Everything
downstream — rankings, backtest, audit — inherits its honesty.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

#: Conservative SEC filing upper bounds, used by the audit when probing lag sensitivity.
QUARTER_LAG_DAYS = 45


def available_fundamentals(fund: pd.DataFrame, asof: pd.Timestamp, lag_days: int) -> pd.DataFrame:
    """Latest usable report per ticker as of ``asof``.

    A report is usable once ``period_end + lag_days <= asof``.  This single
    comparison is the whole point-in-time guarantee; everything else inherits it.
    """
    usable = fund[fund["period_end"] + pd.Timedelta(days=int(lag_days)) <= asof]
    if usable.empty:
        return usable
    return usable.sort_values("period_end").groupby("ticker", as_index=False).tail(1)


def shares_outstanding(row: pd.Series) -> float:
    """Estimate share count from TTM net income / TTM basic EPS.

    The data source gives no share count, and using *today's* share count on a
    past date is a cross-sectional look-ahead (it flatters companies that later
    bought back stock).  Net income / EPS is the cheapest PIT-safe estimate;
    it is noisy, so implausible results are rejected rather than clipped.
    """
    ni, eps = row.get("net_income_ttm"), row.get("eps_ttm")
    if not ni or not eps or np.isnan(ni) or np.isnan(eps):
        return np.nan
    if eps == 0 or ni / eps <= 0:
        return np.nan
    shares = ni / eps
    if not (1e5 < shares < 1e12):  # e.g. EPS rounded to 0.00 blows this up
        return np.nan
    return shares


def _winsorize(s: pd.Series, p: float = 0.02) -> pd.Series:
    lo, hi = s.quantile(p), s.quantile(1 - p)
    return s.clip(lo, hi)


def _z(s: pd.Series) -> pd.Series:
    sd = s.std(ddof=0)
    if not sd or np.isnan(sd):
        return pd.Series(0.0, index=s.index)
    return (s - s.mean()) / sd


def _rank(s: pd.Series) -> pd.Series:
    """Cross-sectional percentile in (0, 1]; ties get the average rank."""
    return s.rank(method="average", pct=True)


def raw_factors(
    prices: pd.DataFrame,
    fund: pd.DataFrame,
    asof: pd.Timestamp,
    cfg,
) -> pd.DataFrame:
    """Raw (unranked) factor values for every ticker on ``asof``.

    Uses only rows whose availability date is on or before ``asof``.
    """
    close = prices.loc[prices.index <= asof].iloc[-1] if len(prices.loc[prices.index <= asof]) else None
    if close is None:
        return pd.DataFrame()

    f = available_fundamentals(fund, asof, cfg.data.disclosure_lag_days)
    if f.empty:
        return pd.DataFrame()
    f = f.set_index("ticker")

    out = pd.DataFrame(index=f.index)
    out["close"] = close.reindex(f.index)

    # --- affordability of the market cap estimate ------------------------
    out["shares"] = f.apply(shares_outstanding, axis=1)
    out["market_cap"] = out["close"] * out["shares"]

    # --- fcf yield -------------------------------------------------------
    out["fcf_yield"] = f["fcf_ttm"] / out["market_cap"]

    # --- quality: profitable, high gross margin, low leverage ------------
    with np.errstate(divide="ignore", invalid="ignore"):
        out["roe"] = f["net_income_ttm"] / f["equity"].replace(0, np.nan)
        out["gross_margin"] = f["gross_profit_ttm"] / f["revenue_ttm"].replace(0, np.nan)
        out["leverage"] = f["total_liabilities"] / f["total_assets"].replace(0, np.nan)
    q = pd.concat(
        [_z(_winsorize(out["roe"])),
         _z(_winsorize(out["gross_margin"])),
         -_z(_winsorize(out["leverage"]))],
        axis=1,
    )
    out["quality"] = q.mean(axis=1, skipna=True)

    # --- momentum: 12-1, skip the most recent month ----------------------
    idx = prices.index
    pos = idx.get_indexer([asof], method="ffill")[0]
    lb, skip = cfg.strategy.momentum_lookback, cfg.strategy.momentum_skip
    if pos - skip - lb >= 0:
        p_now = prices.iloc[pos - skip]
        p_then = prices.iloc[pos - skip - lb]
        out["momentum"] = (p_now / p_then - 1.0).reindex(out.index)
    else:
        out["momentum"] = np.nan

    return out


def score(raw: pd.DataFrame, cfg) -> pd.DataFrame:
    """Rank-normalise each factor, then weight.  Output is comparable across factors."""
    if raw.empty:
        return raw
    res = raw.copy()
    for name in cfg.strategy.factors:
        res[name] = _rank(res[name].replace([np.inf, -np.inf], np.nan))

    weights = pd.Series(cfg.strategy.factors, dtype=float)
    # Only names with every factor present are eligible.  Renormalising per
    # name would silently turn a missing factor into a free upgrade.
    complete = res[list(weights.index)].notna().all(axis=1)
    res["composite"] = np.nan
    res.loc[complete, "composite"] = (res.loc[complete, list(weights.index)] * weights).sum(axis=1)
    res["eligible"] = complete
    # stable tie-break so two processes produce byte-identical portfolios
    return res.sort_values(["composite", "ticker"], ascending=[False, True], kind="mergesort")

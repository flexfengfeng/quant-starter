"""Walk-forward backtest engine.

Timeline of one rebalance:

    decision date (quarter-end close)   -> signals use data available *then*
    execution date (+1 trading day)     -> trades at that day's close, paying cost
    ... drift until next decision date

The one-trading-day gap is the cheapest defence against same-bar look-ahead.
``execution_lag_days = 0`` is allowed and the audit will show you what it buys.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..data.features import raw_factors, score
from ..data.loader import price_matrix
from ..strategy.portfolio import build_target
from .costs import round_trip_bps, trade_cost
from .metrics import summarize


@dataclass
class BacktestResult:
    equity: pd.Series
    benchmark: pd.Series
    weights: pd.DataFrame
    trades: pd.DataFrame
    ic: pd.Series
    stats: dict
    reasons: dict = field(default_factory=dict)


def rebalance_dates(calendar: pd.DatetimeIndex, freq: str) -> list[pd.Timestamp]:
    s = pd.Series(calendar, index=calendar)
    if freq == "quarterly":
        key = s.dt.year.astype(str) + "Q" + s.dt.quarter.astype(str)
    elif freq == "semiannual":
        key = s.dt.year.astype(str) + "H" + (s.dt.month > 6).astype(int).add(1).astype(str)
    else:
        raise ValueError(f"unknown rebalance frequency: {freq}")
    return list(s.groupby(key).last().sort_values())


def run_backtest(
    cfg,
    prices: pd.DataFrame,
    fund: pd.DataFrame,
    universe: pd.DataFrame,
    initial_cash: float = 100_000.0,
) -> BacktestResult:
    px = price_matrix(prices).sort_index()
    bench = cfg.data.benchmark
    if bench not in px.columns:
        raise ValueError(f"benchmark {bench} missing from prices")

    start = pd.Timestamp(cfg.backtest.start)
    end = pd.Timestamp(cfg.backtest.end)
    cal = px.index[(px.index >= start) & (px.index <= end)]
    px = px.loc[cal].ffill()
    bench_px = px[bench].ffill()

    lag = int(cfg.backtest.execution_lag_days)
    decisions = [d for d in rebalance_dates(cal, cfg.backtest.rebalance)
                 if cal.get_loc(d) + lag < len(cal)]
    # enter as soon as signals exist: the window starts after the momentum
    # warm-up, so waiting for the first quarter-end would sit in cash for months
    if decisions and cal[0] < decisions[0]:
        decisions = [cal[0]] + decisions
    exec_of = {cal[cal.get_loc(d) + lag]: d for d in decisions}

    fx = cfg.costs.fx_one_way_bps / 1e4
    cash = initial_cash * (1.0 - fx)
    shares: dict[str, float] = {}
    prev_quality: pd.Series | None = None
    prev_composite: pd.Series | None = None
    prev_decision: pd.Timestamp | None = None
    ic_rows: list[tuple[pd.Timestamp, float]] = []
    weight_rows: dict[pd.Timestamp, dict[str, float]] = {}
    trade_rows: list[dict] = []
    equity = pd.Series(index=cal, dtype=float)
    reasons_latest: dict[str, str] = {}
    turnover_fracs: list[float] = []
    total_cost: float = 0.0

    for t in cal:
        if t in exec_of:
            d = exec_of[t]
            raw = raw_factors(px, fund, d, cfg)
            sc = score(raw, cfg) if not raw.empty else raw

            if prev_composite is not None and prev_decision is not None and not sc.empty:
                fwd = (px.loc[d] / px.loc[prev_decision] - 1.0).reindex(prev_composite.index)
                pair = pd.concat([prev_composite, fwd], axis=1).dropna()
                if len(pair) >= 5:
                    ic_rows.append((prev_decision, float(pair.iloc[:, 0].corr(pair.iloc[:, 1], method="spearman"))))

            pt = px.loc[t]
            cur_val = {k: v * pt[k] for k, v in shares.items() if pd.notna(pt.get(k))}
            nav = cash + sum(cur_val.values())

            if sc.empty:
                target_w: dict[str, float] = {}
                reasons_latest = {}
            else:
                current = [k for k in shares if pd.notna(pt.get(k))]
                tgt = build_target(sc, universe, raw["quality"], prev_quality, current, cfg)
                target_w = {k: w for k, w in tgt.weights.items() if pd.notna(pt.get(k))}
                reasons_latest = tgt.reasons
                prev_quality = raw["quality"].copy()

            if sc is not None and not sc.empty:
                prev_composite = sc.loc[sc["eligible"], "composite"].copy()
                prev_decision = d

            desired = {k: w * nav for k, w in target_w.items()}
            deltas = {}
            for k in sorted(set(cur_val) | set(desired)):
                deltas[k] = desired.get(k, 0.0) - cur_val.get(k, 0.0)
            # do not pay for drift: skip small adjustments on names we keep
            band = cfg.portfolio.rebalance_band * nav
            for k in list(deltas):
                if k in desired and k in cur_val and abs(deltas[k]) < band:
                    deltas[k] = 0.0
            final = {k: cur_val.get(k, 0.0) + deltas.get(k, 0.0)
                     for k in sorted(set(cur_val) | set(desired))}
            traded = sum(abs(v) for v in deltas.values())
            cost = trade_cost(traded, cfg.costs)
            total_cost += cost
            if nav > 0:
                turnover_fracs.append(traded / nav)
            cash = nav - sum(final.values()) - cost
            shares = {k: v / pt[k] for k, v in final.items() if v > 0 and pt[k] > 0}

            for k, dv in deltas.items():
                if abs(dv) < 1e-6:
                    continue
                trade_rows.append(
                    {
                        "date": t,
                        "ticker": k,
                        "side": "BUY" if dv > 0 else "SELL",
                        "notional": abs(dv),
                        "shares": abs(dv / pt[k]) if pt[k] > 0 else np.nan,
                        "price": pt[k],
                    }
                )
            weight_rows[t] = {k: v / nav for k, v in desired.items()}

        mark = cash + sum(v * px.loc[t, k] for k, v in shares.items() if pd.notna(px.loc[t, k]))
        equity[t] = mark

    benchmark = bench_px / bench_px.iloc[0] * initial_cash * (1.0 - fx)
    ic = pd.Series(dict(ic_rows), dtype=float).sort_index()
    weights = pd.DataFrame(weight_rows).T.fillna(0.0)
    trades = pd.DataFrame(trade_rows)
    stats = summarize(equity, benchmark)
    years = max(stats.get("years", 1.0), 1e-9)
    stats["turnover_annual"] = float(sum(turnover_fracs) / years)
    mean_nav = float(equity.mean()) if len(equity) else initial_cash
    stats["cost_drag_annual"] = float(total_cost / mean_nav / years)
    stats["n_rebalances"] = len(decisions)
    stats["n_trades"] = int(len(trades))
    stats["mean_ic"] = float(ic.mean()) if len(ic) else float("nan")
    return BacktestResult(equity, benchmark, weights, trades, ic, stats, reasons_latest)

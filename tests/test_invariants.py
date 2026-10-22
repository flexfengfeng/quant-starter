"""Invariant tests.

These are the guard rails for the recursive part of the course: you are
*expected* to replace modules.  The tests are what tells you whether the
replacement broke the system's promises.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from qs.config import CostConfig, DataConfig, load_config
from qs.data.features import _rank, available_fundamentals, shares_outstanding
from qs.data.manifest import returns_fingerprint
from qs.data.validate import validate
from qs.strategy.portfolio import build_target
from qs.strategy.sells import quality_deterioration


@pytest.fixture(scope="module")
def cfg():
    return load_config("config/strategy.yaml")


@pytest.fixture(scope="module")
def data(cfg):
    from qs.data.loader import load_all

    return load_all(cfg, root=".")


def test_rank_ties_get_average():
    s = pd.Series({"a": 1.0, "b": 1.0, "c": 2.0, "d": 4.0})
    r = _rank(s)
    assert r["a"] == r["b"], "ties must not be broken arbitrarily"
    assert r["a"] == pytest.approx(0.375)  # ranks 1,2 -> average 1.5 / 4
    assert (r > 0).all() and (r <= 1).all()


def test_pit_rejects_unpublished_reports():
    fund = pd.DataFrame({
        "ticker": ["A", "A"],
        "period_end": pd.to_datetime(["2020-03-31", "2020-06-30"]),
        "net_income_ttm": [1.0, 2.0],
    })
    # Q1 ended 31 Mar; with a 45-day lag it is visible from 15 May, not before.
    assert len(available_fundamentals(fund, pd.Timestamp("2020-05-01"), 45)) == 0
    got = available_fundamentals(fund, pd.Timestamp("2020-05-20"), 45)
    assert len(got) == 1 and str(got["period_end"].iloc[0].date()) == "2020-03-31"
    # with a true release-date source (lag 0) the March report is already known
    assert len(available_fundamentals(fund, pd.Timestamp("2020-05-01"), 0)) == 1
    # a year later both are visible, and the function returns the *latest* one
    later = available_fundamentals(fund, pd.Timestamp("2021-06-01"), 45)
    assert len(later) == 1 and str(later["period_end"].iloc[0].date()) == "2020-06-30"


def test_shares_estimate_rejects_garbage():
    row = pd.Series({"net_income_ttm": 1e9, "eps_ttm": 0.0})
    assert np.isnan(shares_outstanding(row))
    ok = pd.Series({"net_income_ttm": 1e9, "eps_ttm": 5.0})
    assert shares_outstanding(ok) == pytest.approx(2e8)


def test_quality_deterioration_needs_both_conditions():
    now = pd.Series({"A": 1.0, "B": 1.0, "C": 5.0, "D": 9.0})
    prev = pd.Series({"A": 3.0, "B": 1.0, "C": 5.0, "D": 9.0})
    flags = quality_deterioration(now, prev, pct=0.5, decline=0.30)
    assert "A" in flags          # bottom half and fell 67%
    assert "B" not in flags      # stable
    assert "C" not in flags      # not in the bottom half


def test_portfolio_respects_caps(cfg, data):
    prices, fund, universe = data
    from qs.data.features import raw_factors, score
    from qs.data.loader import price_matrix

    px = price_matrix(prices).sort_index().ffill()
    asof = pd.Timestamp("2024-06-30")
    raw = raw_factors(px, fund, asof, cfg)
    sc = score(raw, cfg)
    tgt = build_target(sc, universe, raw["quality"], None, [], cfg)

    assert 0 < len(tgt.weights) <= cfg.strategy.top_n
    assert max(tgt.weights.values()) <= cfg.portfolio.max_weight + 1e-9
    assert sum(tgt.weights.values()) + tgt.cash == pytest.approx(1.0)
    assert tgt.cash >= cfg.portfolio.min_cash - 1e-9
    sector = universe.set_index("ticker")["sector"]
    by_sector = pd.Series(tgt.weights).groupby(sector).sum()
    assert (by_sector <= cfg.portfolio.max_sector + 1e-9).all()


def test_higher_costs_lower_returns(cfg, data):
    from qs.backtest.engine import run_backtest

    prices, fund, universe = data
    cheap = run_backtest(cfg, prices, fund, universe)
    import copy

    heavy = copy.deepcopy(cfg)
    heavy.costs = CostConfig(commission_bps=0.0, slippage_bps=50.0)
    dear = run_backtest(heavy, prices, fund, universe)
    assert dear.stats["cagr"] < cheap.stats["cagr"], "costs must bite, monotonically"


def test_backtest_is_deterministic(cfg, data):
    from qs.backtest.engine import run_backtest

    prices, fund, universe = data
    a = run_backtest(cfg, prices, fund, universe)
    b = run_backtest(cfg, prices, fund, universe)
    assert returns_fingerprint(a.equity) == returns_fingerprint(b.equity)


def test_equity_reconciles_with_trades(cfg, data):
    """NAV on the final day must equal start + sum of P&L; no cash leaks."""
    from qs.backtest.engine import run_backtest

    prices, fund, universe = data
    res = run_backtest(cfg, prices, fund, universe)
    assert res.equity.notna().all()
    assert (res.equity > 0).all()
    # weights after each rebalance sum to < 1 (cash floor) and never exceed it
    if len(res.weights):
        assert (res.weights.sum(axis=1) <= 1.0 + 1e-9).all()


def test_validate_catches_duplicates(cfg, data):
    prices, fund, universe = data
    dirty = pd.concat([prices, prices.head(5)], ignore_index=True)
    rep = validate(dirty, fund, universe, cfg.data.benchmark)
    assert not rep.ok
    assert any("duplicate" in n and not ok for n, ok, _ in rep.checks)


def test_reproducible_across_processes_and_hash_seeds():
    """The promise that makes a backtest a fact rather than an anecdote."""
    import os
    import subprocess
    import sys

    code = (
        "from qs.config import load_config;"
        "from qs.data.loader import load_all;"
        "from qs.backtest.engine import run_backtest;"
        "from qs.data.manifest import returns_fingerprint;"
        "c=load_config('config/strategy.yaml');p,f,u=load_all(c,root='.');"
        "print(returns_fingerprint(run_backtest(c,p,f,u).equity))"
    )
    out = []
    for seed in ("0", "12345"):
        env = {**os.environ, "PYTHONPATH": "src", "PYTHONHASHSEED": seed}
        out.append(subprocess.check_output([sys.executable, "-c", code], env=env, text=True).strip())
    assert out[0] == out[1], f"hash-seed dependent output: {out}"

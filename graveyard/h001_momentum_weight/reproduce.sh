#!/usr/bin/env bash
# Reproduce H-001: remove momentum, renormalise the other two weights.
set -euo pipefail
cd "$(dirname "$0")/../.."

PYTHONPATH=src python3 - <<'PY'
import copy
from qs.config import load_config
from qs.data.loader import load_all
from qs.backtest.engine import run_backtest

cfg = load_config("config/strategy.yaml")
prices, fund, universe = load_all(cfg, root=".")

def show(label, c):
    r = run_backtest(c, prices, fund, universe)
    s = r.stats
    print(f"{label:28s} CAGR {s['cagr']*100:6.2f}%  excess {s['excess_cagr']*100:+6.2f}pp  "
          f"t {s['excess_t_stat']:5.2f}  Sharpe {s['sharpe']:.3f}  MDD {s['max_drawdown']*100:6.1f}%  "
          f"turnover {s['turnover_annual']*100:.0f}%")

show("baseline (3 factors)", cfg)
c = copy.deepcopy(cfg)
c.strategy.factors = {"fcf_yield": 0.5714, "quality": 0.4286}
show("momentum removed", c)
PY

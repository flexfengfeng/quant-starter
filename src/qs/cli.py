"""Command line entry point: ``python -m qs <command>``."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .backtest.audit import render_audit, run_audit
from .backtest.engine import run_backtest
from .backtest.metrics import format_stats, rolling_excess
from .config import load_config
from .data.loader import load_all, price_matrix
from .data.manifest import build_manifest, returns_fingerprint, write_manifest
from .data.validate import validate
from .live.dryrun import PaperState, plan_orders
from .live.sizing import format_sizing, sizing_table
from .report.dashboard import build_dashboard

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"


def _load(args):
    cfg = load_config(args.config)
    prices, fund, universe = load_all(cfg, root=ROOT)
    return cfg, prices, fund, universe


def _check_data(cfg, prices, fund, universe, strict: bool = True) -> bool:
    rep = validate(prices, fund, universe, cfg.data.benchmark)
    print(rep.render())
    if not rep.ok and strict:
        print("\ndata contract failed — refusing to run. Fix data, not the check.")
    return rep.ok


def cmd_validate(args) -> int:
    cfg, prices, fund, universe = _load(args)
    return 0 if _check_data(cfg, prices, fund, universe) else 1


def cmd_run(args) -> int:
    cfg, prices, fund, universe = _load(args)
    if not _check_data(cfg, prices, fund, universe):
        return 1

    res = run_backtest(cfg, prices, fund, universe, initial_cash=args.capital)
    probes = run_audit(cfg, prices, fund, universe)
    manifest = build_manifest(cfg, ROOT)
    manifest["returns_fingerprint"] = returns_fingerprint(res.equity)

    stats = {k: (float(v) if isinstance(v, (int, float)) else v) for k, v in res.stats.items()}
    stats["excess_3y"] = rolling_excess(res.equity, res.benchmark, 3)
    stats["excess_5y"] = rolling_excess(res.equity, res.benchmark, 5)

    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "result.json").write_text(json.dumps(
        {"stats": stats, "fingerprint": manifest["fingerprint"],
         "returns_fingerprint": manifest["returns_fingerprint"],
         "latest_weights": {k: float(v) for k, v in res.weights.iloc[-1].items() if v > 1e-6}},
        indent=2))
    write_manifest(manifest, REPORTS / "manifest.json")
    (REPORTS / "audit.md").write_text(render_audit(probes, cfg))
    build_dashboard(res, cfg, universe, probes, REPORTS / "report.html")

    print("\n" + format_stats(stats))
    print("\nAudit")
    for p in probes:
        print(f"  [{p.verdict:4s}] {p.name}: {p.headline}")
    print(f"\nfingerprint {manifest['fingerprint']}  returns {manifest['returns_fingerprint']}")
    print(f"report -> {REPORTS / 'report.html'}")
    return 0


def cmd_audit(args) -> int:
    cfg, prices, fund, universe = _load(args)
    probes = run_audit(cfg, prices, fund, universe)
    text = render_audit(probes, cfg)
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "audit.md").write_text(text)
    print(text)
    return 0


def cmd_orders(args) -> int:
    cfg, prices, fund, universe = _load(args)
    state = PaperState.load(ROOT / "state" / "paper.json")
    orders = plan_orders(cfg, prices, fund, universe, state, min_order_usd=args.min_order)
    if orders.empty:
        print("no orders — portfolio already at target, or no eligible names")
        return 0
    print(orders.to_string(index=False))
    out = REPORTS / "orders.csv"
    REPORTS.mkdir(exist_ok=True)
    orders.to_csv(out, index=False)
    print(f"\nwrote {out}  (paper only — no broker call, deliberately)")
    return 0


def cmd_size(args) -> int:
    rows = []
    for cap in args.capital:
        rows.append(sizing_table(cap, args.names, args.fee, args.slippage))
    print(format_sizing(rows))
    return 0


def cmd_explain(args) -> int:
    cfg, prices, fund, universe = _load(args)
    from .data.features import raw_factors, score

    px = price_matrix(prices).sort_index().ffill()
    asof = px.index[-1]
    raw = raw_factors(px, fund, asof, cfg)
    sc = score(raw, cfg)
    cols = ["fcf_yield", "quality", "momentum", "composite", "eligible"]
    top = sc[cols].head(args.n)
    print(f"signals as of {asof.date()}  (percentiles; composite = weighted sum)\n")
    print(top.round(4).to_string())
    print("\nweights:", cfg.strategy.factors)
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="qs", description="quant-starter")
    p.add_argument("--config", default=str(ROOT / "config" / "strategy.yaml"))
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("validate", help="run the data contract").set_defaults(func=cmd_validate)

    r = sub.add_parser("run", help="backtest + audit + html report")
    r.add_argument("--capital", type=float, default=100_000.0)
    r.set_defaults(func=cmd_run)

    sub.add_parser("audit", help="six self-deception probes").set_defaults(func=cmd_audit)

    o = sub.add_parser("orders", help="target orders for the paper account (no broker)")
    o.add_argument("--min-order", type=float, default=200.0)
    o.set_defaults(func=cmd_orders)

    s = sub.add_parser("size", help="how many names can your capital afford?")
    s.add_argument("--capital", type=float, nargs="+", default=[20_000, 50_000, 100_000])
    s.add_argument("--names", type=int, default=12)
    s.add_argument("--fee", type=float, default=1.08, help="fixed fee per order, USD (moomoo SG: 0.99 + 9%% GST)")
    s.add_argument("--slippage", type=float, default=8.0, help="one-way slippage in bps")
    s.set_defaults(func=cmd_size)

    e = sub.add_parser("explain", help="show today's factor percentiles")
    e.add_argument("-n", type=int, default=15)
    e.set_defaults(func=cmd_explain)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

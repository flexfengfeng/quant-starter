"""Position sizing from first principles.

Given your capital and your broker's fee schedule, the system should *tell you*
how many names you can afford.  The answer is usually smaller than the number
you copied from someone else's backtest.

Singapore specifics that enter here:

* moomoo SG charges US$0.99 + 9% GST per US order even at "zero commission",
  so a US$500 ticket costs ~0.44% round trip — the fixed fee, not the spread.
* IBKR SG charges US$0.35 minimum per order (tiered), so the same ticket is
  cheap; the binding cost there is the data subscription and FX.
* US estate tax applies above US$60,000 of US-situs stock for a non-resident
  with no treaty credit — a *sizing* constraint, not a trading one.
"""

from __future__ import annotations

from ..backtest.costs import order_fee_fraction


def sizing_table(capital: float, top_n: int, fixed_fee: float, slippage_bps: float,
                 rebalances_per_year: int = 4, turnover_frac: float = 0.35) -> dict:
    """Return per-order economics for a given capital and portfolio size."""
    invest = capital * 0.98
    per_name = invest / top_n
    fee_bps = order_fee_fraction(per_name, fixed_fee)
    round_trip_bps = fee_bps + 2 * slippage_bps
    orders_per_year = top_n * rebalances_per_year * turnover_frac
    annual_cost = orders_per_year * fixed_fee + invest * slippage_bps * 2 / 1e4
    return {
        "capital": capital,
        "top_n": top_n,
        "per_name": per_name,
        "fee_bps_per_order": fee_bps,
        "round_trip_bps": round_trip_bps,
        "orders_per_year": orders_per_year,
        "annual_cost_usd": annual_cost,
        "annual_drag_pct": annual_cost / capital * 100,
        "us_estate_tax_exposed": capital > 60_000,
    }


def format_sizing(rows: list[dict]) -> str:
    head = (
        f"{'capital':>12} {'names':>6} {'per name':>10} {'fee bp':>8} "
        f"{'round trip':>11} {'annual drag':>12} {'estate tax':>11}"
    )
    out = [head, "-" * len(head)]
    for r in rows:
        out.append(
            f"{r['capital']:>12,.0f} {r['top_n']:>6d} {r['per_name']:>10,.0f} "
            f"{r['fee_bps_per_order']:>8.1f} {r['round_trip_bps']:>10.1f}bp "
            f"{r['annual_drag_pct']:>11.2f}% {'YES' if r['us_estate_tax_exposed'] else 'no':>11}"
        )
    out += [
        "",
        "Read this before choosing top_n:",
        "  - per name below ~US$1,000 means the fixed fee dominates the trade.",
        "  - annual drag should be small vs the excess you expect (~1-3pp).",
        "  - US estate tax above US$60k is a sizing decision, not a return problem.",
    ]
    return "\n".join(out)

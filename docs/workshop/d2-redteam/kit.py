#!/usr/bin/env python3
"""Build and verify the D2 red-team kit (teacher material).

What this is
------------
A deliberately dishonest *fake* fund report used in the D2 afternoon session:
students are handed ``report.html`` and must find at least five biases before
they may attack each other's reports.  The manager ("Marlowe Ridge Capital") is
fictional.  The performance numbers are fabricated, but they are *internally
coherent*: the appendix, the chart and the monthly heatmap all come from the
same series, so the report cannot be dismissed as sloppy arithmetic.  The lies
are in the labels, the method and the fine print — exactly where they live in
real documents.

Three commands::

    python docs/workshop/d2-redteam/kit.py build    # report.html + answer-key.md/.zh.md
    python docs/workshop/d2-redteam/kit.py check    # do the quotes still exist? is it quarantined?
    python docs/workshop/d2-redteam/kit.py dump     # the appendix's true numbers

The single source of truth for the planted biases is
``docs/workshop/d2-redteam/biases.json`` (English + Chinese in the same record).
The answer keys are *generated* from it, so the two languages cannot drift —
that is the same discipline ``CLAIMS.md`` enforces for numbers.

Quarantine: this file and everything under ``docs/workshop/d2-redteam/`` are
teacher material.  Delete the directory from the student fork, and never quote
its numbers in ``CLAIMS.md``, ``README.md`` or the real ``reports/`` pipeline.
"""

from __future__ import annotations

import html
import json
import math
import random
import sys
from pathlib import Path
from statistics import NormalDist

ROOT = Path(__file__).resolve().parents[3]
KIT = Path(__file__).resolve().parent
REPORT = KIT / "report.html"
BIASES = KIT / "biases.json"

# --------------------------------------------------------------------------
# 1. The fabricated series
# --------------------------------------------------------------------------
#: Calendar-year targets (full years; 2014 starts in April, 2026 stops in
#: September).  They are chosen so that the *live* window 2019-10..2026-09
#: compounds to Sharpe 2.02 while the *full* window 2014-04..2026-09 gives ~19% —
#: the gap between the two is one of the planted biases.
YEAR_TARGETS: dict[int, float] = {
    2014: 0.140, 2015: 0.090, 2016: 0.170, 2017: 0.290, 2018: -0.050,
    2019: 0.180, 2020: 0.180, 2021: 0.360, 2022: 0.020, 2023: 0.260,
    2024: 0.330, 2025: 0.270, 2026: 0.130,   # 2026 is re-solved below
}
SEED = 20261023
LIVE_FROM = (2019, 10)          # report footnote: "live from Q3 2019"
FORCED = {(2022, 6): -0.112}    # one month worse than the claimed max drawdown
CLAIMED = {
    "mdd": -0.089,      # fabricated: the appendix's own worst month is -11.2%
    "beta": 0.62,       # asserted, never shown
    "rf": 0.02,         # the risk-free rate the Sharpe uses
    "spy_cagr": 0.136,  # S&P 500 *price* index, matches this repo's benchmark
}
NOISE_SD = 0.032        # monthly; ~11% annualised, inside a "quality" fund's range


def _draws(n: int) -> list[float]:
    """Deterministic standard-normal draws (Mersenne Twister + inverse CDF)."""
    rng = random.Random(SEED)
    nd = NormalDist()
    return [NOISE_SD * nd.inv_cdf(min(max(rng.random(), 1e-12), 1 - 1e-12)) for _ in range(n)]


def _solve_shift(yearly: list[float], target: float) -> float:
    """Constant added to every month of a year so the year compounds to target."""
    lo, hi = -0.25, 0.25
    for _ in range(200):
        mid = (lo + hi) / 2
        if math.prod(1 + r + mid for r in yearly) < 1 + target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _year_returns(y: int, m0: int, m1: int, noise: list[float], target: float) -> list[float]:
    """One year's monthly returns: noise + a constant shift that hits ``target``.

    ``FORCED`` months are pinned *after* the shift, so the stated return is exact.
    """
    base = list(noise)
    forced = {m - m0: v for (yy, m), v in FORCED.items() if yy == y}
    shift = 0.0
    for _ in range(80):  # fixed point: the shift moves the forced month too
        for j, v in forced.items():
            base[j] = v - shift
        shift = _solve_shift(base, target)
    return [r + shift for r in base]


def build_months() -> list[tuple[int, int, float]]:
    """The fabricated monthly return series (deterministic, no network)."""
    spans = {}
    for y in sorted(YEAR_TARGETS):
        spans[y] = (4 if y == 2014 else 1, 9 if y == 2026 else 12)

    noise = _draws(sum(m1 - m0 + 1 for (m0, m1) in spans.values()))
    i = 0
    raw: dict[int, list[float]] = {}
    for y, (m0, m1) in spans.items():
        k = m1 - m0 + 1
        raw[y] = noise[i:i + k]
        i += k

    months: dict[tuple[int, int], float] = {}
    for y, (m0, m1) in spans.items():
        if y == 2026:  # solved below, once every earlier year is fixed
            continue
        rets = _year_returns(y, m0, m1, raw[y], YEAR_TARGETS[y])
        for j, r in enumerate(rets):
            months[(y, m0 + j)] = r

    # Tune 2026 so the *live* window (2019-10 → 2026-09) has Sharpe 2.02:
    # the headline numbers are real; the label that says "since 2014" is not.
    m0, m1 = spans[2026]
    target = 0.24
    for _ in range(6):
        lo, hi = -0.6, 1.2
        for _ in range(100):
            mid = (lo + hi) / 2
            months.update({(2026, m0 + j): r for j, r in
                           enumerate(_year_returns(2026, m0, m1, raw[2026], mid))})
            live = [r for (yy, mm), r in sorted(months.items()) if (yy, mm) >= LIVE_FROM]
            if _cagr(live) < target:
                lo = mid
            else:
                hi = mid
        months.update({(2026, m0 + j): r for j, r in
                       enumerate(_year_returns(2026, m0, m1, raw[2026], (lo + hi) / 2))})
        live = [r for (yy, mm), r in sorted(months.items()) if (yy, mm) >= LIVE_FROM]
        vol = _stats([(y_, m_, r_) for (y_, m_), r_ in sorted(months.items())
                      if (y_, m_) >= LIVE_FROM])["vol"]
        target = CLAIMED["rf"] + 2.02 * vol
    return [(y, m, r) for (y, m), r in sorted(months.items())]


def _cagr(rets: list[float]) -> float:
    n = len(rets)
    return math.prod(1 + r for r in rets) ** (12 / n) - 1


def _stats(months: list[tuple[int, int, float]]) -> dict:
    rets = [r for (_, _, r) in months]
    n = len(rets)
    cagr = _cagr(rets)
    mu = sum(rets) / n
    vol = math.sqrt(sum((r - mu) ** 2 for r in rets) / (n - 1)) * math.sqrt(12)
    nav, peak, mdd, mdd_at = 100.0, 100.0, 0.0, None
    worst, worst_at = 0.0, None
    for (y, m, r) in months:
        nav *= 1 + r
        peak = max(peak, nav)
        if nav / peak - 1 < mdd:
            mdd, mdd_at = nav / peak - 1, f"{y}-{m:02d}"
        if r < worst:
            worst, worst_at = r, f"{y}-{m:02d}"
    sharpe = (cagr - CLAIMED["rf"]) / vol if vol else float("nan")
    return {
        "months": n, "years": n / 12, "cagr": cagr, "vol": vol, "sharpe": sharpe,
        "mdd": mdd, "mdd_at": mdd_at, "worst": worst, "worst_at": worst_at,
        "multiple": nav / 100.0, "final": nav * 1000.0,  # 100k starting capital
    }


def series() -> tuple[list[tuple[int, int, float]], dict, dict]:
    months = build_months()
    full = _stats(months)
    live = _stats([(y, m, r) for (y, m, r) in months if (y, m) >= LIVE_FROM])
    return months, full, live


def fmt(months, full, live) -> dict[str, str]:
    """Pre-formatted numbers injected into the answer keys (never hand-typed)."""
    def pct(v):  # x.xx pp as "1.23%"
        return f"{v * 100:.2f}%"

    def pp(v):
        return f"{v * 100:+.2f}pp"

    def money(v):
        if v >= 1_000_000:
            return f"US${v / 1_000_000:.2f}m"
        return f"US${v / 1000:,.0f}k"

    yearly = {y: math.prod(1 + r for (yy, _, r) in months if yy == y) - 1
              for y in sorted(YEAR_TARGETS)}
    backtest = [r for (y, m, r) in months if (y, m) < LIVE_FROM]
    return {
        "backtest_cagr": f"{_cagr(backtest) * 100:.1f}%",
        "n_backtest": str(len(backtest)),
        "n_live": str(len(months) - len(backtest)),
        "full_cagr": f"{full['cagr'] * 100:.1f}%",
        "full_multiple": f"{full['multiple']:.2f}x",
        "full_final": money(full["final"]),
        "full_sharpe": f"{full['sharpe']:.2f}",
        "full_mdd": f"{full['mdd'] * 100:.1f}%",
        "live_cagr": f"{live['cagr'] * 100:.1f}%",
        "live_vol": f"{live['vol'] * 100:.1f}%",
        "live_sharpe": f"{live['sharpe']:.2f}",
        "live_mdd": f"{live['mdd'] * 100:.1f}%",
        "live_years": f"{live['years']:.1f}",
        "worst_month": f"{full['worst'] * 100:.1f}%",
        "worst_at": str(full["worst_at"]),
        "headline_multiple": f"{(1 + live['cagr']) ** full['years']:.2f}x",
        "headline_final": money(100_000 * (1 + live["cagr"]) ** full["years"]),
        "claimed_mdd": f"{CLAIMED['mdd'] * 100:.1f}%",
        "spy_cagr": f"{CLAIMED['spy_cagr'] * 100:.1f}%",
        "excess": f"{(live['cagr'] - CLAIMED['spy_cagr']) * 100:.1f}",
        "beta": f"{CLAIMED['beta']:.2f}",
        "first_year": f"{yearly[2014] * 100:+.1f}%",
        "last_year": f"{yearly[2026] * 100:+.1f}%",
        "worst_year": min((f"{yearly[y] * 100:+.1f}%" for y in yearly),
                          key=lambda s: float(s.replace("%", ""))),
    }


# --------------------------------------------------------------------------
# 2. The report (the plant)
# --------------------------------------------------------------------------
def _svg_curve(months: list[tuple[int, int, float]]) -> str:
    w, h, pad_l, pad_r, pad_t, pad_b = 1000, 320, 56, 92, 26, 40
    nav = 100.0
    pts = [(2014, 4, 100.0)]  # the index is 100 on 1 April, before the first month
    for (y, m, r) in months:
        nav *= 1 + r
        pts.append((y, m, nav))
    lo, hi = 90.0, 1050.0
    lo_l, hi_l = math.log10(lo), math.log10(hi)
    xs = [pad_l + (w - pad_l - pad_r) * i / (len(pts) - 1) for i in range(len(pts))]
    ys = [h - pad_b - (h - pad_t - pad_b) * (math.log10(v) - lo_l) / (hi_l - lo_l)
          for (_, _, v) in pts]
    path = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
    grid = []
    for v in (100, 200, 400, 800):
        yy = h - pad_b - (h - pad_t - pad_b) * (math.log10(v) - lo_l) / (hi_l - lo_l)
        grid.append(
            f'<line x1="{pad_l}" y1="{yy:.1f}" x2="{w - pad_r}" y2="{yy:.1f}" '
            f'stroke="#e6e9ee" stroke-width="1"/>'
            f'<text x="{pad_l - 10}" y="{yy + 4:.1f}" text-anchor="end" '
            f'font-size="12" fill="#7a8798">{v}</text>'
        )
    ticks = []
    for (y, label) in ((2014, "2014"), (2016, "2016"), (2018, "2018"), (2020, "2020"),
                       (2022, "2022"), (2024, "2024"), (2026, "2026")):
        idx = [i for i, (yy, _, _) in enumerate(pts) if yy == y][0]
        ticks.append(
            f'<text x="{xs[idx]:.1f}" y="{h - 14}" text-anchor="middle" '
            f'font-size="12" fill="#7a8798">{label}</text>'
        )
    end = f'<text x="{xs[-1] + 8:.1f}" y="{ys[-1] + 4:.1f}" font-size="12" ' \
          f'fill="#10243e">index {pts[-1][2]:.0f}</text>'
    return f'''<svg viewBox="0 0 {w} {h}" role="img" aria-label="growth of 100000 dollars">
  {''.join(grid)}
  <path d="{path}" fill="none" stroke="#10243e" stroke-width="2.4"/>
  {''.join(ticks)}
  {end}
</svg>'''


def _heatmap(months: list[tuple[int, int, float]]) -> str:
    by: dict[tuple[int, int], float] = {(y, m): r for (y, m, r) in months}
    head = "".join(f"<th>{m:02d}</th>" for m in range(1, 13))
    rows = []
    for y in sorted({yy for (yy, _, _) in months}):
        cells = []
        for m in range(1, 13):
            r = by.get((y, m))
            if r is None:
                cells.append("<td class='na'>·</td>")
                continue
            a = min(abs(r) / 0.06, 1.0)
            if r >= 0:
                bg = f"rgba(16,107,83,{0.10 + 0.55 * a:.2f})"
            else:
                bg = f"rgba(163,45,45,{0.10 + 0.55 * a:.2f})"
            cells.append(f"<td style='background:{bg}'>{r * 100:+.1f}</td>")
        rows.append(f"<tr><th>{y}</th>{''.join(cells)}</tr>")
    return f"""<table class="heat"><thead><tr><th></th>{head}</tr></thead>
<tbody>{''.join(rows)}</tbody></table>"""


def _annual_table(months: list[tuple[int, int, float]]) -> str:
    rows = []
    for y in sorted({yy for (yy, _, _) in months}):
        r = math.prod(1 + v for (yy, _, v) in months if yy == y) - 1
        note = ""
        if y == 2014:
            note = " <span class='note'>(9 months)</span>"
        if y == 2026:
            note = " <span class='note'>(9 months to 30 Sep)</span>"
        cls = "pos" if r >= 0 else "neg"
        rows.append(f"<tr><td>{y}{note}</td><td class='r {cls}'>{r * 100:+.1f}%</td></tr>")
    return f"<table class='annual'><thead><tr><th>Calendar year</th><th class='r'>Return</th></tr></thead><tbody>{''.join(rows)}</tbody></table>"


def build_report() -> str:
    months, full, live = series()
    n = fmt(months, full, live)
    live_cagr = n["live_cagr"]
    live_vol = n["live_vol"]
    live_sharpe = n["live_sharpe"]
    claimed_mdd = n["claimed_mdd"]

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="d2-redteam-plant" content="marlowe-ridge-v1">
<title>Marlowe Ridge Capital — Annual Review 2026</title>
<style>
  :root {{ --ink:#10243e; --muted:#5c6b7f; --line:#dfe4ea; --bg:#ffffff; --gold:#a8894f; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--ink);
         font:15px/1.62 -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, sans-serif; }}
  .page {{ max-width:900px; margin:0 auto; padding:56px 40px 72px; }}
  .brand {{ letter-spacing:.22em; font-size:12px; font-weight:700; color:var(--gold); }}
  .brand-sub {{ font-size:12px; letter-spacing:.14em; color:var(--muted); margin-top:3px; }}
  h1 {{ font:600 38px/1.15 Georgia, "Times New Roman", serif; margin:22px 0 8px; }}
  h2 {{ font:600 15px/1.3 -apple-system, sans-serif; text-transform:uppercase;
        letter-spacing:.09em; color:var(--muted); margin:44px 0 14px;
        border-bottom:1px solid var(--line); padding-bottom:8px; }}
  .meta {{ color:var(--muted); font-size:13px; }}
  .hero {{ display:grid; grid-template-columns:repeat(4, 1fr); gap:1px; background:var(--line);
           border:1px solid var(--line); margin:30px 0 8px; }}
  .hero div {{ background:#fff; padding:16px 18px; }}
  .hero .k {{ font-size:11px; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); }}
  .hero .v {{ font:600 27px/1.1 Georgia, serif; margin-top:7px; }}
  .hero .s {{ font-size:11px; color:var(--muted); margin-top:4px; }}
  p {{ margin:0 0 12px; }}
  .lead {{ font-size:17px; line-height:1.65; }}
  .kpi {{ font-weight:600; }}
  svg {{ width:100%; height:auto; display:block; }}
  .legend {{ font-size:12px; color:var(--muted); margin-top:4px; }}
  table {{ width:100%; border-collapse:collapse; font-size:13.5px; }}
  th, td {{ padding:7px 8px; border-bottom:1px solid var(--line); text-align:left; }}
  th {{ font-size:11px; letter-spacing:.06em; text-transform:uppercase; color:var(--muted); }}
  .r {{ text-align:right; }} .pos {{ color:#106b53; }} .neg {{ color:#a32d2d; }}
  .note {{ color:var(--muted); font-size:11px; }}
  .two {{ display:grid; grid-template-columns:1fr 1fr; gap:32px; }}
  dl {{ margin:0; }} dt {{ font-weight:600; margin-top:12px; }} dd {{ margin:4px 0 0; color:#33455c; }}
  .footnotes {{ font-size:12px; color:var(--muted); }}
  .footnotes li {{ margin-bottom:7px; }}
  .heat td {{ text-align:right; font-variant-numeric:tabular-nums; font-size:11.5px;
              color:#0d1b2a; padding:3px 4px; border:1px solid #fff; }}
  .heat th {{ font-size:11px; padding:3px 4px; }}
  .heat .na {{ color:#b7c0cb; text-align:center; }}
  .annual td:first-child {{ width:60%; }}
  footer {{ margin-top:48px; padding-top:16px; border-top:1px solid var(--line);
            font-size:11px; color:var(--muted); }}
  @media print {{ .page {{ max-width:none; padding:0; }} h2 {{ page-break-after:avoid; }} }}
</style>
</head>
<body>
<div class="page">

  <div class="brand">MARLOWE RIDGE CAPITAL</div>
  <div class="brand-sub">US QUALITY–MOMENTUM STRATEGY · CAYMAN-DOMICILED</div>
  <h1>Annual Review 2026</h1>
  <div class="meta">Performance through 30 September 2026 &nbsp;·&nbsp; Prepared for prospective
    investors &nbsp;·&nbsp; Confidential — not for distribution</div>

  <div class="hero">
    <div><div class="k">Annualised return</div><div class="v">{live_cagr}</div>
         <div class="s">since inception, April 2014</div></div>
    <div><div class="k">Sharpe ratio</div><div class="v">{live_sharpe}</div>
         <div class="s">risk-free rate 2.0%</div></div>
    <div><div class="k">Maximum drawdown</div><div class="v">{claimed_mdd}</div>
         <div class="s">peak to trough, since inception</div></div>
    <div><div class="k">Beta vs S&amp;P 500</div><div class="v">{n['beta']}</div>
         <div class="s">monthly, since inception</div></div>
  </div>

  <h2>Executive summary</h2>
  <p class="lead">The strategy has compounded at <span class="kpi">{live_cagr} a year since
  inception</span>, turning US$100,000 into <span class="kpi">{n['headline_final']}</span>
  against {n['spy_cagr']} a year for <span class="kpi">the S&amp;P 500 price index</span> — an
  excess return of <span class="kpi">{n['excess']} percentage points a year</span> at a Sharpe
  ratio of {live_sharpe}.</p>

  <p>The edge has a mechanism, not a story. Companies that are cheap on free cash flow, earn a
  high return on invested capital and are in an established twelve-month uptrend keep
  outperforming: three documented premia that the model holds simultaneously instead of one at a
  time. The strategy is 50–60 names, equal-weighted within a sector cap, and it has beaten the
  index in eleven of the last thirteen calendar years.</p>

  <p>Risk is controlled by construction rather than by forecasting: no leverage, no shorting and
  <span class="kpi">no market timing</span>. <span class="kpi">The fund has never lost more than
  {claimed_mdd} from a peak</span> — in 2022, when the S&amp;P 500 fell 19.4%, the strategy
  returned +2.0%. That is what a quality screen is for.</p>

  <h2>Growth of US$100,000</h2>
  {_svg_curve(months)}
  <div class="legend">Index, log scale; 1 April 2014 = 100. Source: Marlowe Ridge Capital,
    internal records. Chart and appendix are drawn from the same monthly series.</div>

  <h2>Annual returns</h2>
  {_annual_table(months)}

  <h2>How the strategy works</h2>
  <dl>
    <dt>Universe</dt>
    <dd>The 500 constituents of the S&amp;P 500 <span class="kpi">as of the September 2026 index
    review, applied to the full history</span>. Using today's index removes the noise of index
    reconstitution and keeps the test clean.</dd>
    <dt>Signals</dt>
    <dd>Free-cash-flow yield (0.50), return on invested capital (0.30) and 12–1 month momentum
    (0.20), each converted to a cross-sectional percentile and summed. Names must be profitable
    on a trailing basis to be eligible.</dd>
    <dt>Rebalance</dt>
    <dd>Quarterly, on the last trading day of March, June, September and December.
    <span class="kpi">Factor scores use the quarter that ended on the rebalance date — the
    filings are public by then.</span></dd>
    <dt>Execution</dt>
    <dd><span class="kpi">Orders are worked in the closing auction of the rebalance day</span>.
    No intraday trading, no derivatives, no borrow.</dd>
    <dt>Capacity</dt>
    <dd>The strategy has traded at less than 3% of the daily volume of its holdings since 2019;
    capacity is estimated at US$1.5bn before slippage dominates.</dd>
  </dl>

  <div class="two">
    <div>
      <h2>Risk</h2>
      <p>Volatility has been {live_vol} annualised, beta {n['beta']} and maximum drawdown
      {claimed_mdd}. The worst calendar year was {n['worst_year']}; the worst month was June 2022.
      Drawdowns stay shallow because the quality screen removes a name before its fundamentals
      deteriorate, not after the price has already fallen.</p>
      <p>No leverage. No shorting. No market timing. Cash is held only for settlement.</p>
    </div>
    <div>
      <h2>Fees</h2>
      <p>Management fee 1.5% per annum, charged quarterly. Performance fee 15% of the return
      above the S&amp;P 500 price index, subject to a high-water mark. Minimum investment
      US$250,000.</p>
      <p class="note">All performance figures in this review are <b>gross of fees and
      expenses</b>.</p>
    </div>
  </div>

  <h2>Appendix · Monthly returns (%)</h2>
  {_heatmap(months)}
  <div class="legend">The heatmap, the annual table and the chart are the same series: compound
    any row and you get the annual figure; compound the rows and you get the chart.</div>

  <h2>Notes</h2>
  <ol class="footnotes">
    <li>Window: 1 April 2014 – 30 September 2026 ({full['months']} months). The strategy
      <span class="kpi">went live on 1 October 2019</span>; the earlier period applies the same
      rules to historical data.</li>
    <li>Benchmark: <span class="kpi">S&amp;P 500 price index</span>, USD. Dividends are not
      reinvested.</li>
    <li>Universe: S&amp;P 500 constituents as of the September 2026 review (see “How the strategy
      works”).</li>
    <li>Model development: <span class="kpi">34 candidate factor combinations were evaluated</span>
      on 2014–2018 data and the best-performing configuration was retained.</li>
    <li><span class="kpi">Returns are gross of management fees, performance fees, transaction
      costs, FX conversion and dividend withholding tax.</span></li>
    <li>t-statistic of annual excess return: <span class="kpi">2.0</span>, significant at the 5%
      level on a two-sided test.</li>
    <li><span class="kpi">Audited financial statements, a complete trade blotter and the monthly
      returns file are available to qualified investors on request.</span></li>
  </ol>

  <footer>Marlowe Ridge Capital Pte Ltd · 8 Marina View, Singapore · This document is
  illustrative training material, is not an offer of securities in any jurisdiction, and its
  figures are unaudited. Past performance is not indicative of future results.</footer>
</div>

<!--
  RED-TEAM PLANT — teacher material, not a claim.
  Path: docs/workshop/d2-redteam/   ·   Answer key: answer-key.md
  Every performance number here is fabricated for the D2 exercise. Never quote
  this file in CLAIMS.md, README.md or reports/. If a student opens the source,
  that is fine: the exercise is to find WHICH biases, not whether it is fake.
-->
</html>
"""


# --------------------------------------------------------------------------
# 3. Answer keys (generated from biases.json, so EN/ZH cannot drift)
# --------------------------------------------------------------------------
KEY_HEAD_EN = """# D2 red-team · answer key (teacher only)

> **English** · [中文](answer-key.zh.md)

> Generated from [`biases.json`](biases.json) — edit the JSON, then run
> `python docs/workshop/d2-redteam/kit.py build`. Do not hand-edit this file, and never hand
> either language version to a student.

**The plant**: [`report.html`](report.html) — a fictional manager ("Marlowe Ridge
Capital") pitching a US large-cap quality–momentum fund at Sharpe ~2.0. The
performance series is internally coherent: the chart, the annual table and the
monthly heatmap all agree with each other. The lies are in **labels, method and
fine print** — where they live in real documents.

The briefing: *find at least five biases in forty minutes.*
"""

KEY_HEAD_ZH = """# D2 红队 · 答案卡（教师专用）

> [English](answer-key.md) · **中文**

> 由 [`biases.json`](biases.json) 生成 —— 改 JSON，再运行
> `python docs/workshop/d2-redteam/kit.py build`。不要手改本文件，也不要把它（或英文版）
> 发给学生。

**诱饵**：[`report.html`](report.html) —— 一家虚构机构（"Marlowe Ridge
Capital"），推介一只美股大盘质量–动量基金，Sharpe 约 2.0。业绩序列本身是自洽的：
曲线、年度表、月度热力图三者互相吻合。谎话藏在**标签、方法与脚注**里 ——
真实文件里的谎话也正是藏在这些地方。

任务简报：*40 分钟内找出至少 5 个偏差。*
"""

SEV_EN = {"obvious": "obvious", "medium": "medium", "subtle": "subtle"}
SEV_ZH = {"obvious": "一眼可见", "medium": "中等", "subtle": "隐蔽"}


def _render_key(biases: dict, lang: str, f: dict[str, str]) -> str:
    head = KEY_HEAD_EN if lang == "en" else KEY_HEAD_ZH
    out = [head.rstrip(), ""]
    rows = []
    for b in biases["biases"]:
        t = b["title"][lang]
        sev = (SEV_EN if lang == "en" else SEV_ZH)[b["severity"]]
        where = b["where"][lang]
        rows.append(f"| `{b['id']}` | {t} | {sev} | {where} |")
    hdr = ("| id | bias | severity | where |" if lang == "en"
           else "| id | 偏差 | 严重程度 | 位置 |")
    out += [hdr, "|---|---|---|---|"] + rows + [""]
    if lang == "en":
        out += [
            "**Three of these are meant to be found at a glance** (severity *obvious*); "
            "the rest need the appendix, arithmetic, or a benchmark that does not flatter "
            "the strategy. A group that stops at three has not done the exercise.",
            "",
        ]
    else:
        out += [
            "**其中三个属于一眼可见**（severity 为 *obvious*）；其余的需要翻附录、做算术，"
            "或者换一个不比策略更差的基准。只找出三个的小组，不算完成练习。",
            "",
        ]

    for b in biases["biases"]:
        sev = (SEV_EN if lang == "en" else SEV_ZH)[b["severity"]]
        out += [f"## `{b['id']}` · {b['title'][lang]}", "", f"*{sev}*", ""]
        if lang == "en":
            labels = ("**Where**", "**The tell**", "**Why it is wrong**",
                      "**How to score it**", "**Calibration on this repo**")
        else:
            labels = ("**位置**", "**破绽**", "**为什么错**", "**怎么扣分**", "**本仓库的标定**")
        fill = lambda text: text.format(**f)
        colon = "：" if lang == "zh" else ": "
        out += [
            f"{labels[0]}{colon}{fill(b['where'][lang])}",
            "",
            f"{labels[1]}{colon}“{b['quote'][lang]}”",
            "",
            f"{labels[2]}{colon}{fill(b['why'][lang])}",
            "",
            f"{labels[3]}{colon}{fill(b['detect'][lang])}",
        ]
        cal = b.get("calibration", {}).get(lang)
        if cal:
            out += ["", f"{labels[4]}{colon}{fill(cal)}"]
        out += [""]

    out += _key_footer(lang, f)
    return "\n".join(out)


def _key_footer(lang: str, f: dict[str, str]) -> list[str]:
    if lang == "en":
        return [
            "---",
            "",
            "## Numbers behind the answer key",
            "",
            "These are computed from the fabricated series by `kit.py dump`; "
            "they are what an attentive student should be able to derive.",
            "",
            "| what | value |",
            "|---|---|",
            f"| claimed headline CAGR (12.5 years) | {f['live_cagr']} → {f['headline_multiple']}, "
            f"{f['headline_final']} |",
            f"| appendix, full window (12.5 years) | **{f['full_cagr']}** → {f['full_multiple']}, "
            f"{f['full_final']} |",
            f"| appendix, live window (2019-10 → 2026-09, {f['live_years']} years) | "
            f"**{f['live_cagr']}**, vol {f['live_vol']}, Sharpe {f['live_sharpe']} |",
            f"| full-window Sharpe | {f['full_sharpe']} |",
            f"| claimed maximum drawdown | {f['claimed_mdd']} |",
            f"| appendix worst month ({f['worst_at']}) | **{f['worst_month']}** |",
            f"| appendix maximum drawdown, full window | {f['full_mdd']} |",
            f"| appendix maximum drawdown, live window | {f['live_mdd']} |",
            "",
            "## How to run the session (40 minutes)",
            "",
            "1. **5 min** — hand out the printed report. Say only: *this was sent to a friend "
            "of mine; find what is wrong with it.*",
            "2. **20 min** — pairs, no laptops. They must write **quotes**, not impressions.",
            "3. **10 min** — collect the count. The group median is usually 3; the answer key "
            "has 11.",
            "4. **5 min** — close on probe 6: `make audit` shows t = 0.23 for the honest "
            "system; this report claims t = 2.0 after 34 tries. The bar for a new factor is "
            "t > 3.0, not 2.0.",
            "",
            "## Quarantine",
            "",
            "- Never quote these numbers in `CLAIMS.md`, `README.md` or `reports/`.",
            "- Delete `docs/workshop/d2-redteam/` from the student fork "
            "(the workshop README says so).",
            "- `python docs/workshop/d2-redteam/kit.py check` fails if a planted quote disappears from "
            "`report.html` or if a headline number leaks into the honest docs.",
            "",
        ]
    return [
        "---",
        "",
        "## 答案卡背后的数字",
        "",
        "以下数字由 `kit.py dump` 从假序列算出；细心的学生应当能自己推出来。",
        "",
        "| 项目 | 数值 |",
        "|---|---|",
        f"| 正文声称的 CAGR（12.5 年） | {f['live_cagr']} → {f['headline_multiple']}，{f['headline_final']} |",
        f"| 附录全窗口（12.5 年） | **{f['full_cagr']}** → {f['full_multiple']}，{f['full_final']} |",
        f"| 附录 live 窗口（2019-10 → 2026-09，{f['live_years']} 年） | "
        f"**{f['live_cagr']}**，波动率 {f['live_vol']}，Sharpe {f['live_sharpe']} |",
        f"| 全窗口 Sharpe | {f['full_sharpe']} |",
        f"| 声称的最大回撤 | {f['claimed_mdd']} |",
        f"| 附录最差单月（{f['worst_at']}） | **{f['worst_month']}** |",
        f"| 附录全窗口最大回撤 | {f['full_mdd']} |",
        f"| 附录 live 窗口最大回撤 | {f['live_mdd']} |",
        "",
        "## 怎么带这一场（40 分钟）",
        "",
        "1. **5 分钟** —— 发纸质报告。只说一句：*这是一个朋友转给我的，找出它的问题。*",
        "2. **20 分钟** —— 两两一组，不许用电脑。要求写**原话引用**，不是印象。",
        "3. **10 分钟** —— 收数量。小组中位数通常 3 个；答案卡有 11 个。",
        "4. **5 分钟** —— 收在 probe 6：`make audit` 里诚实系统的 t = 0.23；这份报告在试过 "
        "34 组参数之后声称 t = 2.0。新因子的门槛是 t > 3.0，不是 2.0。",
        "",
        "## 隔离",
        "",
        "- 永远不要把这里的数字写进 `CLAIMS.md`、`README.md` 或 `reports/`。",
        "- 学生 fork 里请删掉 `docs/workshop/d2-redteam/`（workshop README 里已写明）。",
        "- `python docs/workshop/d2-redteam/kit.py check` 会在“破绽原话”从 `report.html` 消失、"
        "或标题数字泄漏进诚实文档时失败。",
        "",
    ]


def render_keys() -> None:
    data = json.loads(BIASES.read_text(encoding="utf-8"))
    months, full, live = series()
    f = fmt(months, full, live)
    (KIT / "answer-key.md").write_text(_render_key(data, "en", f), encoding="utf-8")
    (KIT / "answer-key.zh.md").write_text(_render_key(data, "zh", f), encoding="utf-8")


# --------------------------------------------------------------------------
# 4. Commands
# --------------------------------------------------------------------------
def cmd_build() -> int:
    REPORT.write_text(build_report(), encoding="utf-8")
    render_keys()
    print(f"wrote {REPORT.relative_to(ROOT)}")
    print(f"wrote {KIT / 'answer-key.md'} and .zh.md")
    return 0


def cmd_dump() -> int:
    months, full, live = series()
    f = fmt(months, full, live)
    print(json.dumps(f, indent=2, ensure_ascii=False))
    return 0


def _norm(s: str) -> str:
    return " ".join(s.split())


def cmd_check() -> int:
    problems: list[str] = []
    rep = _norm(html.unescape(REPORT.read_text(encoding="utf-8")))
    data = json.loads(BIASES.read_text(encoding="utf-8"))
    biases = data["biases"]
    ids = [b["id"] for b in biases]

    if '"d2-redteam-plant"' not in rep:
        problems.append("report.html lost its provenance marker")
    if len(biases) < 6:
        problems.append(f"only {len(biases)} biases planted; the briefing asks for five")
    if len(set(ids)) != len(ids):
        problems.append("duplicate bias ids")
    if sum(1 for b in biases if b["severity"] == "obvious") < 3:
        problems.append("fewer than three 'obvious' biases")

    for b in biases:
        for lang in ("en", "zh"):
            for field in ("title", "where", "quote", "why", "detect"):
                if not b.get(field, {}).get(lang):
                    problems.append(f"{b['id']}: missing {field}.{lang}")
        if _norm(b["quote"]["en"]) not in rep:
            problems.append(f"{b['id']}: quote not found in report.html — "
                            f"{b['quote']['en'][:60]!r}")

    months, full, live = series()
    f = fmt(months, full, live)
    for lang in ("en", "zh"):
        disk = (KIT / ("answer-key.md" if lang == "en" else "answer-key.zh.md")).read_text(encoding="utf-8")
        fresh = _render_key(data, lang, f)
        if _norm(disk) != _norm(fresh):
            problems.append(f"answer-key{'zh' if lang == 'zh' else ''}.md is stale — run `build`")
        for bid in ids:
            if f"`{bid}`" not in disk:
                problems.append(f"{bid} missing from answer-key{'.zh' if lang == 'zh' else ''}.md")

    # Quarantine: fabricated numbers must never appear in the honest documents.
    honest = ["CLAIMS.md", "CLAIMS.zh.md", "README.md", "README.zh.md",
              "LEARNING_PATH.md", "LEARNING_PATH.zh.md", "AGENTS.md", "AGENTS.zh.md",
              "docs/workshop/README.md", "docs/workshop/README.zh.md"]
    leaks = list(data.get("meta", {}).get("leak_tokens", [])) + [
        f["live_cagr"], f["live_sharpe"], f["claimed_mdd"]]
    for name in honest:
        text = (ROOT / name).read_text(encoding="utf-8")
        for token in leaks:
            if token in text:
                problems.append(f"quarantine breach: {token!r} found in {name}")

    if problems:
        for p in problems:
            print(f"FAIL  {p}")
        return 1
    print(f"PASS  {len(biases)} biases planted, "
          f"{sum(1 for b in biases if b['severity'] == 'obvious')} obvious; "
          "every quote present in report.html")
    print("PASS  answer keys match the generator (EN and ZH in sync)")
    print("PASS  no fabricated headline leaked into the honest docs")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    cmd = argv[0] if argv else "build"
    return {"build": cmd_build, "check": cmd_check, "dump": cmd_dump}.get(
        cmd, lambda: (print(f"unknown command {cmd!r}; use build|check|dump"), 2)[1]
    )()


if __name__ == "__main__":
    raise SystemExit(main())

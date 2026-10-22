"""Self-contained HTML report — one file, no CDN, no JS framework.

The chart is a hand-built SVG polyline: it forces you to know what you are
plotting (normalised to 100, both series rebased on the same day) and it keeps
the repo dependency-free.
"""

from __future__ import annotations

import html
from pathlib import Path

import pandas as pd

W, H, PAD = 1000, 320, 34


def _path(series: pd.Series, lo: float, hi: float, n: int) -> str:
    s = series.dropna()
    if len(s) < 2:
        return ""
    step = max(1, len(s) // n)
    s = s.iloc[::step]
    xs = [PAD + (W - 2 * PAD) * i / (len(s) - 1) for i in range(len(s))]
    rng = (hi - lo) or 1.0
    ys = [H - PAD - (H - 2 * PAD) * (float(v) - lo) / rng for v in s.to_numpy()]
    return "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))


def _chart(port: pd.Series, bench: pd.Series) -> str:
    p = port / port.iloc[0] * 100
    b = bench / bench.iloc[0] * 100
    lo = min(p.min(), b.min())
    hi = max(p.max(), b.max())
    return f"""
<svg viewBox="0 0 {W} {H}" preserveAspectRatio="none" role="img" aria-label="equity curve">
  <path d="{_path(p, lo, hi, 900)}" fill="none" stroke="#2563eb" stroke-width="2"/>
  <path d="{_path(b, lo, hi, 900)}" fill="none" stroke="#94a3b8" stroke-width="1.6" stroke-dasharray="5 4"/>
  <text x="{PAD}" y="18" font-size="12" fill="#64748b">start = 100</text>
  <text x="{PAD}" y="{H - 8}" font-size="11" fill="#94a3b8">{lo:.0f}</text>
  <text x="{W - PAD - 60}" y="18" font-size="11" fill="#94a3b8">{hi:.0f}</text>
</svg>"""


def _drawdown_chart(port: pd.Series) -> str:
    dd = (port / port.cummax() - 1) * 100
    lo, hi = float(dd.min()), 0.0
    return f"""
<svg viewBox="0 0 {W} 180" preserveAspectRatio="none" role="img" aria-label="drawdown">
  <path d="{_path(dd, lo, hi, 900)}" fill="none" stroke="#dc2626" stroke-width="1.4"/>
  <text x="{PAD}" y="18" font-size="12" fill="#64748b">drawdown %</text>
  <text x="{PAD}" y="34" font-size="11" fill="#94a3b8">0%</text>
  <text x="{PAD}" y="172" font-size="11" fill="#94a3b8">{lo:.1f}%</text>
</svg>"""


def _card(label: str, value: str, hint: str = "") -> str:
    return (
        '<div class="card"><div class="label">' + html.escape(label) +
        '</div><div class="value">' + html.escape(value) +
        ('</div><div class="hint">' + html.escape(hint) + "</div></div>"
         if hint else "</div></div>")
    )


def build_dashboard(res, cfg, universe: pd.DataFrame, probes, path: str | Path) -> Path:
    st = res.stats
    pct = lambda v: f"{v*100:.1f}%" if v == v else "n/a"
    num = lambda v, d=2: f"{v:.{d}f}" if v == v else "n/a"

    last = res.weights.iloc[-1] if len(res.weights) else pd.Series(dtype=float)
    sector = universe.set_index("ticker")["sector"].to_dict()
    rows = []
    for tk, w in last[last > 1e-6].sort_values(ascending=False).items():
        rows.append(
            f"<tr><td>{html.escape(tk)}</td><td>{html.escape(sector.get(tk,'?'))}</td>"
            f"<td class='r'>{w*100:.1f}%</td></tr>"
        )
    holdings = "".join(rows) or "<tr><td colspan='3'>no positions</td></tr>"

    trades = res.trades.tail(12)
    trows = "".join(
        f"<tr><td>{r.date.date()}</td><td>{html.escape(r.ticker)}</td>"
        f"<td>{r.side}</td><td class='r'>${r.notional:,.0f}</td></tr>"
        for r in trades.itertuples()
    ) or "<tr><td colspan='4'>no trades</td></tr>"

    arows = "".join(
        f"<tr><td>{html.escape(p.name)}</td><td class='{p.verdict.lower()}'>{p.verdict}</td>"
        f"<td>{html.escape(p.headline)}</td></tr>"
        for p in probes
    )

    cards = "".join([
        _card("CAGR", pct(st.get("cagr"))),
        _card("vs benchmark", (f"{st['excess_cagr']*100:+.2f}pp" if st.get("excess_cagr") == st.get("excess_cagr") else "n/a"),
              "same window"),
        _card("Sharpe", num(st.get("sharpe"))),
        _card("Max drawdown", pct(st.get("max_drawdown"))),
        _card("excess t-stat", num(st.get("excess_t_stat")), "t>3 to believe it"),
        _card("turnover / yr", pct(st.get("turnover_annual")), "cost drag " + pct(st.get("cost_drag_annual"))),
    ])

    css = """
    :root{--ink:#0f172a;--muted:#64748b;--line:#e2e8f0;--bg:#f8fafc}
    *{box-sizing:border-box}
    body{margin:0;font:14px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,sans-serif;
         color:var(--ink);background:var(--bg);padding:32px}
    h1{font-size:22px;margin:0 0 4px} h2{font-size:15px;margin:32px 0 10px;color:var(--muted);
         text-transform:uppercase;letter-spacing:.06em}
    .sub{color:var(--muted);margin-bottom:20px}
    .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}
    .card{background:#fff;border:1px solid var(--line);border-radius:10px;padding:14px 16px}
    .label{font-size:12px;color:var(--muted)} .value{font-size:22px;font-weight:600;margin-top:4px}
    .hint{font-size:11px;color:var(--muted);margin-top:2px}
    .panel{background:#fff;border:1px solid var(--line);border-radius:10px;padding:16px}
    svg{width:100%;height:auto;display:block}
    .legend{font-size:12px;color:var(--muted);margin-top:6px}
    table{width:100%;border-collapse:collapse;font-size:13px}
    th,td{padding:7px 8px;border-bottom:1px solid var(--line);text-align:left}
    th{color:var(--muted);font-weight:500} .r{text-align:right}
    .pass,.ok{color:#15803d;font-weight:600} .warn{color:#b45309;font-weight:600}
    .fail{color:#b91c1c;font-weight:600}
    .cols{display:grid;grid-template-columns:1.15fr .85fr;gap:16px}
    @media(max-width:820px){.cols{grid-template-columns:1fr}}
    """

    body = f"""<!doctype html><html lang="zh"><head><meta charset="utf-8">
<title>quant-starter — backtest report</title><style>{css}</style></head><body>
<h1>quant-starter · backtest report</h1>
<div class="sub">{cfg.backtest.start} → {cfg.backtest.end} · {cfg.backtest.rebalance} ·
{cfg.strategy.top_n} names · lag {cfg.backtest.execution_lag_days}d ·
slippage {cfg.costs.slippage_bps:.0f}bps · disclosure lag {cfg.data.disclosure_lag_days}d</div>

<div class="grid">{cards}</div>

<h2>Equity (start = 100)</h2>
<div class="panel">{_chart(res.equity, res.benchmark)}
<div class="legend">— strategy &nbsp;&nbsp; <span style="color:#94a3b8">- -</span> benchmark ({html.escape(cfg.data.benchmark)})</div>
</div>

<h2>Drawdown</h2>
<div class="panel">{_drawdown_chart(res.equity)}</div>

<div class="cols">
<div>
<h2>Current target weights</h2>
<div class="panel"><table><thead><tr><th>ticker</th><th>sector</th><th class="r">weight</th></tr></thead>
<tbody>{holdings}</tbody></table></div>
</div>
<div>
<h2>Last trades</h2>
<div class="panel"><table><thead><tr><th>date</th><th>ticker</th><th>side</th><th class="r">notional</th></tr></thead>
<tbody>{trows}</tbody></table></div>
</div>
</div>

<h2>Audit — six probes</h2>
<div class="panel"><table><thead><tr><th>probe</th><th>verdict</th><th>headline</th></tr></thead>
<tbody>{arows}</tbody></table></div>

<p class="legend">Generated by <code>make run</code> · every number here is re-derivable from
<code>reports/result.json</code> and <code>CLAIMS.md</code>.</p>
</body></html>"""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
    return path

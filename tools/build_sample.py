#!/usr/bin/env python3
"""Build the frozen sample dataset for quant-starter.

Provenance
----------
This script reads the *parent* reference implementation's local cache
(``data/cache/kline/all.csv`` and ``data/cache/financials/*.json``, which were
themselves fetched from moomoo OpenAPI and Yahoo) and freezes a small,
self-contained snapshot under ``data/sample/``.

The snapshot is committed so that:

* ``make run`` works offline, on any machine, deterministically;
* every number in the repo can be re-derived without network access;
* a workshop student cannot accidentally "fix" results by re-fetching data
  that changed underneath them (the single most common source of silent
  non-reproducibility).

Field mapping notes (moomoo statement JSON)
-------------------------------------------
income  : 8001 revenue, 8004 gross profit, 8037 net income, 8047 basic EPS
balance : 8001 total assets, 8048 total liabilities, 8085 parent equity
cashflow: 8015 CFO, 8046 net capex (negative), 8072 free cash flow

``dateTimeStr`` is the *earnings release* date, not the fiscal period end
(verified against AAPL FY2024: released 2024-10-30, fiscal year ended
2024-09-28).  Availability is therefore ``dateTimeStr + disclosure_lag_days``
with a default of 0; set 45/75 in config if your source only exposes period end.

Usage:  python tools/build_sample.py
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PARENT_CACHE = ROOT.parent / "data" / "cache"
OUT = ROOT / "data" / "sample"

# Curated, sector-diverse large caps.  Chosen because they have both a full
# 2013- price history and a quarterly fundamentals history in the parent cache.
CANDIDATES = {
    # ticker: (name, sector)
    "AAPL": ("Apple", "Information Technology"),
    "MSFT": ("Microsoft", "Information Technology"),
    "NVDA": ("NVIDIA", "Information Technology"),
    "AVGO": ("Broadcom", "Information Technology"),
    "ORCL": ("Oracle", "Information Technology"),
    "CSCO": ("Cisco", "Information Technology"),
    "ADBE": ("Adobe", "Information Technology"),
    "QCOM": ("Qualcomm", "Information Technology"),
    "TXN": ("Texas Instruments", "Information Technology"),
    "AMAT": ("Applied Materials", "Information Technology"),
    "INTC": ("Intel", "Information Technology"),
    "IBM": ("IBM", "Information Technology"),
    "JNJ": ("Johnson & Johnson", "Health Care"),
    "UNH": ("UnitedHealth", "Health Care"),
    "PFE": ("Pfizer", "Health Care"),
    "MRK": ("Merck", "Health Care"),
    "ABT": ("Abbott", "Health Care"),
    "TMO": ("Thermo Fisher", "Health Care"),
    "AMGN": ("Amgen", "Health Care"),
    "GILD": ("Gilead", "Health Care"),
    "KO": ("Coca-Cola", "Consumer Staples"),
    "PG": ("Procter & Gamble", "Consumer Staples"),
    "PEP": ("PepsiCo", "Consumer Staples"),
    "COST": ("Costco", "Consumer Staples"),
    "WMT": ("Walmart", "Consumer Staples"),
    "MCD": ("McDonald's", "Consumer Discretionary"),
    "NKE": ("Nike", "Consumer Discretionary"),
    "HD": ("Home Depot", "Consumer Discretionary"),
    "SBUX": ("Starbucks", "Consumer Discretionary"),
    "CAT": ("Caterpillar", "Industrials"),
    "BA": ("Boeing", "Industrials"),
    "HON": ("Honeywell", "Industrials"),
    "UNP": ("Union Pacific", "Industrials"),
    "LMT": ("Lockheed Martin", "Industrials"),
    "GE": ("GE Aerospace", "Industrials"),
    "XOM": ("Exxon Mobil", "Energy"),
    "CVX": ("Chevron", "Energy"),
    "COP": ("ConocoPhillips", "Energy"),
    "DIS": ("Walt Disney", "Communication Services"),
    "VZ": ("Verizon", "Communication Services"),
    "NFLX": ("Netflix", "Communication Services"),
    "GOOGL": ("Alphabet", "Communication Services"),
    "META": ("Meta Platforms", "Communication Services"),
    "NEE": ("NextEra Energy", "Utilities"),
    "LIN": ("Linde", "Materials"),
}

START = "2013-01-02"
END = "2026-10-20"

QTR = ("/Q1", "/Q2", "/Q3", "/Q4")


def _quarterly(records: list[dict]) -> dict[tuple[str, str], dict]:
    """Keep one record per (release date, fiscal period), last one wins."""
    out: dict[tuple[str, str], dict] = {}
    for r in records:
        period = r.get("periodText") or ""
        if not period.endswith(QTR):
            continue
        d = r.get("dateTimeStr")
        if not d:
            continue
        out[(d, period)] = r
    return out


def _num(r: dict | None, field_id: str) -> float | None:
    if not r:
        return None
    v = r.get("items", {}).get(field_id)
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _at(src: dict[tuple[str, str], dict], release: str) -> dict | None:
    """Newest fiscal period released on ``release`` (moomoo puts FY and Q4 together)."""
    labels = sorted(p for (d, p) in src if d == release)
    return src.get((release, labels[-1])) if labels else None


def _ttm_sum(recs: list[dict | None], field_id: str) -> float | None:
    vals = [_num(r, field_id) for r in recs]
    if any(v is None for v in vals):
        return None
    return float(sum(vals))


def build_fundamentals(ticker: str) -> list[dict]:
    path = PARENT_CACHE / "financials" / f"US.{ticker}.json"
    if not path.exists():
        return []
    raw = json.loads(path.read_text())["__statement_types__"]
    inc = _quarterly(raw.get("1", []))
    bal = _quarterly(raw.get("2", []))
    cfs = _quarterly(raw.get("3", []))

    # Align on release date: moomoo releases the three statements together.
    dates = sorted({d for (d, _p) in inc})
    rows: list[dict] = []
    for i in range(3, len(dates)):
        d = dates[i]
        window = dates[i - 3 : i + 1]  # the four quarterly releases making up TTM
        inc_w = [_at(inc, dt) for dt in window]
        if any(r is None for r in inc_w):
            continue

        label = sorted(p for (dt, p) in inc if dt == d)[-1]
        bal_row = _at(bal, d)
        cfs_row = _at(cfs, d)

        rev = _ttm_sum(inc_w, "8001")
        ni = _ttm_sum(inc_w, "8037")
        eps = _ttm_sum(inc_w, "8047")
        gp = _ttm_sum(inc_w, "8004")
        cfs_w = [_at(cfs, dt) for dt in window]
        cfo = _ttm_sum(cfs_w, "8015")
        fcf = _ttm_sum(cfs_w, "8072")
        capex = _ttm_sum(cfs_w, "8046")
        if fcf is None and cfo is not None and capex is not None:
            fcf = cfo + capex  # capex is already negative in moomoo data

        rows.append(
            {
                "ticker": ticker,
                "period_end": d,
                "period": label,
                "revenue_ttm": rev,
                "net_income_ttm": ni,
                "eps_ttm": eps,
                "gross_profit_ttm": gp,
                "cfo_ttm": cfo,
                "fcf_ttm": fcf,
                "total_assets": _num(bal_row, "8001"),
                "total_liabilities": _num(bal_row, "8048"),
                "equity": _num(bal_row, "8085"),
            }
        )
    return rows


def main() -> int:
    prices_all = pd.read_csv(
        PARENT_CACHE / "kline" / "all.csv",
        usecols=["code", "time_key", "close", "volume"],
        dtype={"code": "string"},
    )
    prices_all["ticker"] = prices_all["code"].str.replace("US.", "", regex=False)
    prices_all["date"] = prices_all["time_key"].str[:10]
    prices_all = prices_all[(prices_all.date >= START) & (prices_all.date <= END)]

    have_prices = set(prices_all.ticker.unique())
    fund_rows: list[dict] = []
    kept: dict[str, dict] = {}
    fund_dates: dict[str, list[str]] = defaultdict(list)

    for tk, (name, sector) in CANDIDATES.items():
        rows = build_fundamentals(tk)
        if tk not in have_prices or len(rows) < 12:
            continue
        kept[tk] = {"name": name, "sector": sector}
        fund_rows.extend(rows)
        fund_dates[tk] = [r["period_end"] for r in rows]

    # Require price coverage of the whole window (>= 98% of benchmark trading days)
    spy = prices_all[prices_all.ticker == "SPY"].sort_values("date")
    bench_days = set(spy.date)
    final = []
    for tk in kept:
        days = set(prices_all[prices_all.ticker == tk].date)
        if len(days & bench_days) / max(1, len(bench_days)) >= 0.98:
            final.append(tk)

    prices = prices_all[prices_all.ticker.isin(final + ["SPY"])].copy()
    prices["date"] = pd.to_datetime(prices.date)
    prices = prices.sort_values(["date", "ticker"])[["ticker", "date", "close", "volume"]]
    prices["date"] = prices.date.dt.strftime("%Y-%m-%d")

    fund = pd.DataFrame([r for r in fund_rows if r["ticker"] in final])
    fund = fund.sort_values(["ticker", "period_end"])

    universe = pd.DataFrame(
        [{"ticker": tk, "name": kept[tk]["name"], "sector": kept[tk]["sector"]} for tk in sorted(final)]
    )

    OUT.mkdir(parents=True, exist_ok=True)
    prices.to_csv(OUT / "prices.csv", index=False, float_format="%.4f")
    fund.to_csv(OUT / "fundamentals.csv", index=False, float_format="%.2f")
    universe.to_csv(OUT / "universe.csv", index=False)

    print(f"tickers kept : {len(final)}")
    print(f"price rows   : {len(prices):,}  ({prices.date.min()} .. {prices.date.max()})")
    print(f"fund rows    : {len(fund):,}  ({fund.period_end.min()} .. {fund.period_end.max()})")
    print(f"sectors      : {universe.sector.value_counts().to_dict()}")
    print("dropped      :", sorted(set(CANDIDATES) - set(final)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

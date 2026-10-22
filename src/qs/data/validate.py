"""Data contracts.

Every pipeline dies at the same three places: duplicates, gaps, and silent
unit changes.  These checks are cheap, and they turn a silently-wrong backtest
into a loud failure.  ``make validate`` runs them; the backtest runs them too.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class Report:
    checks: list[tuple[str, bool, str]] = field(default_factory=list)

    def add(self, name: str, ok: bool, detail: str = "") -> None:
        self.checks.append((name, ok, detail))

    @property
    def ok(self) -> bool:
        return all(ok for _n, ok, _d in self.checks)

    def render(self) -> str:
        lines = []
        for name, ok, detail in self.checks:
            mark = "PASS" if ok else "FAIL"
            lines.append(f"[{mark}] {name}" + (f" — {detail}" if detail else ""))
        return "\n".join(lines)


def validate(prices: pd.DataFrame, fund: pd.DataFrame, universe: pd.DataFrame,
             benchmark: str = "SPY") -> Report:
    rep = Report()

    dup = prices.duplicated(subset=["ticker", "date"]).sum()
    rep.add("prices: no duplicate (ticker, date)", dup == 0, f"{dup} duplicates")

    bad = (prices["close"] <= 0).sum() + prices["close"].isna().sum()
    rep.add("prices: all closes positive", bad == 0, f"{bad} bad rows")

    dates = prices["date"].drop_duplicates().sort_values()
    gaps = dates.diff().dt.days.dropna()
    weekly = (gaps > 7).sum()
    rep.add("prices: calendar has no >7d gaps", weekly == 0, f"{weekly} gaps")

    has_bench = benchmark in set(prices["ticker"])
    rep.add(f"prices: benchmark {benchmark} present", has_bench)

    if has_bench:
        bench_days = set(prices.loc[prices.ticker == benchmark, "date"])
        real = set(dates)
        rep.add("prices: benchmark covers the calendar",
                bench_days == real, f"{len(real - bench_days)} missing benchmark days")

    uni = set(universe["ticker"])
    missing_uni = sorted(set(prices["ticker"]) - uni - {benchmark})
    rep.add("universe: every traded ticker has metadata", not missing_uni, str(missing_uni[:5]))

    rep.add("fundamentals: period_end parsed", bool(pd.api.types.is_datetime64_any_dtype(fund["period_end"])))
    rep.add("fundamentals: no period_end in the future",
            bool(fund["period_end"].max() <= prices["date"].max() + pd.Timedelta(days=120)),
            str(fund["period_end"].max().date()))

    need = {"revenue_ttm", "net_income_ttm", "fcf_ttm", "equity", "total_assets", "total_liabilities"}
    have = set(fund.columns)
    rep.add("fundamentals: required columns", need <= have, str(sorted(need - have)))

    # earnings dates must be unique per (ticker, period_end) — a duplicate row
    # silently double-counts in TTM sums.
    dupf = fund.duplicated(subset=["ticker", "period_end"]).sum()
    rep.add("fundamentals: no duplicate (ticker, period_end)", dupf == 0, f"{dupf} duplicates")

    return rep

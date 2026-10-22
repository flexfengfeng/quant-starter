"""Load the frozen sample panel (or your own data with the same columns)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_prices(path: str | Path) -> pd.DataFrame:
    """Long format: ticker, date, close, volume."""
    df = pd.read_csv(path)
    required = {"ticker", "date", "close"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"prices file missing columns: {sorted(missing)}")
    df["date"] = pd.to_datetime(df["date"])
    df["ticker"] = df["ticker"].astype(str)
    if "volume" not in df.columns:
        df["volume"] = pd.NA
    return df.sort_values(["date", "ticker"]).reset_index(drop=True)


def price_matrix(prices: pd.DataFrame) -> pd.DataFrame:
    """Wide close matrix: index=date, columns=ticker."""
    return (
        prices.pivot(index="date", columns="ticker", values="close")
        .sort_index()
        .sort_index(axis=1)
    )


def load_fundamentals(path: str | Path) -> pd.DataFrame:
    """Quarterly fundamentals, as reported: ``period_end`` is the fiscal period end.

    The point-in-time rule (period end + disclosure lag) is applied at *feature*
    time in ``features.available_fundamentals``, not here.  Keeping raw data raw
    means the lag can be probed, changed and tested without re-loading anything.
    """
    df = pd.read_csv(path)
    required = {"ticker", "period_end", "revenue_ttm", "net_income_ttm", "fcf_ttm", "equity"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"fundamentals file missing columns: {sorted(missing)}")
    df["period_end"] = pd.to_datetime(df["period_end"])
    df["ticker"] = df["ticker"].astype(str)
    return df.sort_values(["ticker", "period_end"]).reset_index(drop=True)


def load_universe(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["ticker"] = df["ticker"].astype(str)
    return df


def load_all(cfg, root: str | Path = ".") -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    root = Path(root)
    prices = load_prices(root / cfg.data.prices)
    fund = load_fundamentals(root / cfg.data.fundamentals)
    universe = load_universe(root / cfg.data.universe)
    return prices, fund, universe

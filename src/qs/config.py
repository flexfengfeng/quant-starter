"""Configuration loading.

One YAML file, one dataclass tree, no hidden defaults scattered across modules.
Every number the system trades on is visible here; ``CLAIMS.md`` maps the
outputs back to this file.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class DataConfig:
    prices: str = "data/sample/prices.csv"
    fundamentals: str = "data/sample/fundamentals.csv"
    universe: str = "data/sample/universe.csv"
    benchmark: str = "SPY"
    #: `period_end` in the sample is the fiscal period end, not the release date.
    #: 45 (quarterly) is the SEC 10-Q upper bound; 75 for annual.  Set 0 only if
    #: your data source exposes the actual earnings-release date.
    disclosure_lag_days: int = 45


@dataclass
class BacktestConfig:
    start: str = "2014-04-01"
    end: str = "2026-09-30"
    rebalance: str = "quarterly"  # quarterly | semiannual
    #: Signals are computed on the close of the rebalance date and executed on
    #: the close of the NEXT trading day.  This is the cheapest way to remove
    #: same-bar look-ahead; it is also mildly conservative.
    execution_lag_days: int = 1


@dataclass
class StrategyConfig:
    top_n: int = 12
    factors: dict[str, float] = field(
        default_factory=lambda: {"fcf_yield": 0.50, "quality": 0.375, "momentum": 0.125}
    )
    momentum_lookback: int = 252
    momentum_skip: int = 21


@dataclass
class PortfolioConfig:
    max_weight: float = 0.12
    max_sector: float = 0.35
    min_cash: float = 0.02
    sell_rank_buffer: float = 2.0
    rebalance_band: float = 0.01  # skip trades smaller than 1% of NAV (drift noise)
    quality_sell_pct: float = 0.25
    quality_sell_decline: float = 0.30


@dataclass
class CostConfig:
    commission_bps: float = 0.0
    slippage_bps: float = 8.0
    fx_one_way_bps: float = 0.0  # charged once on the initial funding, not per trade
    dividend_tax_drag_annual: float = 0.0  # reported, not traded on


@dataclass
class Config:
    data: DataConfig = field(default_factory=DataConfig)
    backtest: BacktestConfig = field(default_factory=BacktestConfig)
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    portfolio: PortfolioConfig = field(default_factory=PortfolioConfig)
    costs: CostConfig = field(default_factory=CostConfig)

    def to_dict(self) -> dict[str, Any]:
        from dataclasses import asdict

        return asdict(self)


def _sub(cls, raw: dict[str, Any]):
    allowed = set(cls.__dataclass_fields__)  # type: ignore[attr-defined]
    unknown = set(raw) - allowed
    if unknown:
        raise ValueError(f"unknown config keys for {cls.__name__}: {sorted(unknown)}")
    return cls(**raw)


def load_config(path: str | Path = "config/strategy.yaml") -> Config:
    raw = yaml.safe_load(Path(path).read_text()) or {}
    allowed = set(Config.__dataclass_fields__)
    unknown = set(raw) - allowed
    if unknown:
        raise ValueError(f"unknown config sections: {sorted(unknown)}")
    return Config(
        data=_sub(DataConfig, raw.get("data", {})),
        backtest=_sub(BacktestConfig, raw.get("backtest", {})),
        strategy=_sub(StrategyConfig, raw.get("strategy", {})),
        portfolio=_sub(PortfolioConfig, raw.get("portfolio", {})),
        costs=_sub(CostConfig, raw.get("costs", {})),
    )

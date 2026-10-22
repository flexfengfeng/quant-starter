"""Cost model.

Two things students get wrong here:

* **Zero commission is not zero cost.**  Singapore brokers charge a fixed
  platform fee per order, so small tickets are expensive in basis points even
  at "US$0 commission".  Put the real number in ``commission_bps`` and let the
  arithmetic tell you your minimum viable position size.
* **FX is a one-time entry cost**, not a per-trade cost, if the account is
  funded in USD.  Charging it per trade double-counts it; charging it never is
  the more common error.
"""

from __future__ import annotations

from ..config import CostConfig


def round_trip_bps(cfg: CostConfig) -> float:
    return float(cfg.commission_bps + cfg.slippage_bps)


def trade_cost(notional: float, cfg: CostConfig) -> float:
    """Cost in currency units for a trade of ``notional`` (absolute value)."""
    return abs(notional) * round_trip_bps(cfg) / 1e4


def order_fee_fraction(order_notional: float, fixed_fee: float) -> float:
    """Fixed per-order fee expressed in bps of the order (for the sizing tool)."""
    if order_notional <= 0:
        return float("inf")
    return fixed_fee / order_notional * 1e4

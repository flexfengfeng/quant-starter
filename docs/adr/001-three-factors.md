> **English** · [中文](001-three-factors.zh.md)

# ADR-001 — Why three factors, 12 names, quarterly, equal weight

> Architecture decision record. Every decision must state its **alternatives** and
> its **price**; otherwise it is just a preference.

## Decision

| Dimension | Choice | Alternative | Why not |
|---|---|---|---|
| Factors | FCF-Yield 0.50 / Quality 0.375 / 12-1 Momentum 0.125 | single-factor value; add growth / low-vol / accruals | growth and accruals turned negative in the reference implementation's corrected universe; low-vol has negative IC. Less is auditable. |
| Number of names | Top 12 | Top 20 / Top 6 | 20 does not add diversification in a 45-name sample; 6 names × 12% cap leaves 28% cash drag |
| Rebalance | quarterly | monthly / semiannual | monthly doubles turnover cost and the signal decays faster; semiannual earned 2pp less in-sample |
| Weighting | equal weight | score-weighted / risk parity | equal weight does not depend on believing the score scale; score weighting amplifies noise |
| Fill | next close | same close / next open | same close contains same-bar information (look-ahead); open prices are not in the sample |
| Sells | rank buffer band + quality decay | stop-loss / target price | stop-losses are usually negative-contribution in a low-turnover book; target prices need a valuation model, i.e. new assumptions |

## Price (must be admitted)

- **Equal weight** discards the information "believe the high score more" and will
  underperform score weighting if the score really carries information.
- **Quarterly** means up to three months of signal lag; it reacts slowly when
  momentum crashes.
- **12 names** means 8.3% per name; a single black swan directly hits the
  portfolio by ~8%.
- **Next-close fill** may in reality execute at worse prices; 8bps slippage may
  not be enough.

## When this ADR should be overturned

1. Re-run on a **delisting-free (unbiased) panel** and the conclusion reverses
   (highest priority).
2. Portfolio size above US$500k, where capacity and impact costs become binding.
3. Four consecutive live quarters underperforming the benchmark, with attribution
   showing factor decay (not execution).

## Related

- `config/strategy.yaml` — the only parameter source
- `CLAIMS.md` — measurement basis of every number
- `graveyard/h001_momentum_weight/` — an actual test of one factor's weight

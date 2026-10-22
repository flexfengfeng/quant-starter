> **English** · [中文](002-sample-universe.zh.md)

# ADR-002 — Why the sample is 45 "survivors", and what that costs

## Decision

The sample is 45 US large caps, all satisfying "complete prices since 2013 +
complete quarterly fundamentals + still listed today". It is frozen from the
reference implementation's cache (`tools/build_sample.py`) and committed with the
repo, so `make run` works fully offline.

## Why not use the whole market / a delisting-inclusive panel

1. **Reproducibility first.** In a seven-day workshop the thing that most often
   breaks is data (permissions, rate limits, ticker changes, adjustment bases).
   Frozen data pushes those failures to L3 instead of interrupting L0.
2. **Cost.** No free source offers "unbiased universe + full historical
   fundamentals" together; building a delisted panel takes 500+ fetches and
   cleaning (the reference implementation needed Tiingo + SEC XBRL to assemble
   165 complete names).
3. **Honest and controllable.** Biased but *stated* beats unbiased but
   irreproducible — students will otherwise assume the conclusion is solid.

## Price (quantified in the reference implementation)

| Basis | CAGR | Excess |
|---|---|---|
| 508 current constituents (survivorship-biased) | 13.11% | −0.75pp |
| 673 including delisted (corrected) | 9.89% | **−3.69pp** |

That is: **survivorship bias alone is worth about +3.2pp a year.** So this repo's
14.47% / +0.79pp must be read as an **upper bound**; the true expectation is
probably lower, possibly negative.

There is a second layer: all 45 are famous large caps, where momentum gets a free
advantage (see `graveyard/h001_momentum_weight/`).

## When the sample must be replaced

- To validate **any** factor conclusion (top priority).
- When evaluating capacity after the portfolio grows.
- For the L3 cloud exercise — the first task of a real pipeline is defining the
  universe.

## How to replace it

`data/sample/` has four CSVs; that is the whole interface:

```
prices.csv        ticker, date, close, volume
fundamentals.csv  ticker, period_end, revenue_ttm, net_income_ttm, eps_ttm,
                  gross_profit_ttm, cfo_ttm, fcf_ttm, total_assets,
                  total_liabilities, equity, period
universe.csv      ticker, name, sector
```

After replacing, run `make validate` first: the data contract will stop you
(duplicates, gaps, future data). To reproduce the delisting-inclusive panel, the
reference implementation used **Tiingo daily bars + SEC XBRL fundamentals + SEC
share counts × closing price for market cap** — all free sources.

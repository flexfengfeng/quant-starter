> **English** · [中文](CLAIMS.zh.md)

# CLAIMS — the single source of truth for every number

> Rule: **any number** appearing in the README or the report must have, in this
> file, (1) its measurement basis, (2) its evidence grade, (3) a reproduce
> command, and (4) its known bias. Missing = not quotable.
> This is the most expensive discipline inherited from the reference
> implementation; it is what "single source of truth" means in practice.

---

## 0. Current basis

| Item | Value |
|---|---|
| Code version | `git describe --tags` (at time of writing: v0-run) |
| Input fingerprint | `reports/manifest.json` → `fingerprint` |
| Returns fingerprint | `reports/manifest.json` → `returns_fingerprint` |
| Window | 2014-04-01 .. 2026-09-30 (2013 is the momentum warm-up) |
| Sample | 45 US large caps; prices from 2013-01-02, quarterly fundamentals |
| Rebalance | quarterly; decide at close, fill at the next close |
| Costs | 0bps commission + 8bps one-way slippage |
| PIT | fiscal period end + 45 days |

Reproduce:

```bash
make run && cat reports/manifest.json
```

---

## 1. Headline result (basis: survivor-biased sample — see §3)

| Metric | Value | Command | Evidence grade |
|---|---|---|---|
| CAGR | 14.47% | `make run` | single sample, biased |
| SPY CAGR | 13.68% | same (benchmark row) | — |
| Annualised excess | **+0.79pp** | same | **t=0.23, indistinguishable from zero** |
| Sharpe | 0.892 | same | — |
| Max drawdown | −26.87% | same | — |
| Annual turnover | 68% | same | structural cost |
| Cost drag | 0.06pp/yr | same | 8bps × turnover |
| Mean IC | 0.008 | same | essentially zero |
| Trailing 3y excess | +5.5pp | same | inside the noise band |
| Trailing 5y excess | +4.8pp | same | inside the noise band |

**Mandatory framing (must accompany any quote)**: over this single 2014–2026
sample the strategy beats SPY by about 1pp a year, but t = 0.23 and mean IC = 0.008.
**It cannot be distinguished from luck.** It is not "a working strategy"; it is
"an auditable object".

---

## 2. Audit numbers (`make audit`)

| Probe | Numbers | How to read it |
|---|---|---|
| Data-timing band | −45/0/+45/+90 days → 14.7 / 14.5 / 14.5 / 14.8% | moving "when I knew" costs 0.3pp |
| Execution lag | same-close 14.89% vs next-day 14.47% | the assumption costs 0.42pp |
| Costs | 0/8/24bps → 14.52 / 14.47 / 14.35% | still +0.67pp excess at 24bps |
| Concentration | top-3 names = 28% of gross P&L | not a single-stock bet |
| Beta / Alpha | 0.83 / +2.98% | low-vol portfolio, alpha insignificant |
| Significance | t = 0.23 | **FAIL** |

---

## 3. Known biases (the most important section)

1. **Survivorship bias (largest)** — the sample is 45 names that are *still listed
   today and have complete history*. Delisted, acquired and index-removed
   companies are entirely absent. So every return in this repo is an **upper
   bound**. In the reference implementation, adding 165 delisted names took CAGR
   from 13.11% to 9.89% and excess from −0.75pp to −3.69pp.
2. **Universe-selection bias** — 45 US large caps, technology/health care
   over-weighted. Momentum gets an unfair advantage on such a panel (see
   `graveyard/h001_momentum_weight/`).
3. **Financial restatements** — the source serves latest-revised values, so early
   years may "see" numbers that were published later.
4. **No dividends** — prices are split-adjusted, not total-return; this
   understates the benchmark by roughly 1–1.5pp/yr.
5. **Market cap is an estimate** — share count is backed out of TTM net income /
   TTM basic EPS, which is approximate.
6. **Taxes and FX are off by default** (`fx_one_way_bps=0`,
   `dividend_tax_drag_annual=0`); the real drag for a Singapore investor is about
   0.4–0.5pp/yr (30% dividend withholding). Turn it on manually.

---

## 4. Relationship to the reference implementation

The strategy, parameters and audit discipline come from a reference
implementation (two months, 31 hypothesis cards, 15+ falsified hypotheses). The
differences here are **deliberate**:

| | Reference | This repo |
|---|---|---|
| Code size | ~42k lines | ~2k lines |
| Universe | 508 / 673 (incl. delisted) | 45 (no delisted) |
| Conclusion | +1.93pp, t≈0.85, H31 "inconclusive" | +0.79pp, t=0.23 |
| Purpose | production / research | teaching / starting point |

**Never subtract this repo's numbers from the reference's** — they differ in
basis, not in strategy.

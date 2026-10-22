> **English** · [中文](verdict.zh.md)

# Verdict H-001 — Removing momentum: −3.38pp → −0.76pp → −0.22pp

> **Date**: 2026-10-22 · **Status**: decided (**momentum is only diversification; removable, but kept for now**)
> **Reproduce**: `./graveyard/h001_momentum_weight/reproduce.sh`

## The same hypothesis, run three times

| Version | Baseline CAGR | Momentum removed | **Δ** |
|---|---|---|---|
| v0 · sector cap applied *after* selection, no refill | 14.69% | 11.31% | **−3.38pp** |
| v1 · sector capacity inside the selection loop | 14.74% | 13.98% | **−0.76pp** |
| v2 · enter right after the warm-up (final) | 14.47% | 14.25% | **−0.22pp** |

Two implementation changes moved the same "factor contribution" from **−3.38pp**
to **−0.22pp**: a 3.1pp swing, **14× the final answer**.

## What the two changes did

**v0 → v1 (portfolio construction)**
v0 picked Top-12 and then dropped names that breached the sector cap, without
refilling. Some quarters therefore held only 10 names and 28% cash. Removing
momentum changed the selected list, hence how many names got dropped, hence the
cash level: most of the 3.38pp was **a cash-drag difference**, not factor
contribution.

**v1 → v2 (entry timing)**
v1 started the backtest in January 2014, but 12-1 momentum needs 273 trading days
of warm-up, so the first quarter sat in cash — a cash period unrelated to the
strategy. Starting right after the warm-up moved Δ by another 0.54pp.

## Verdict against the pre-registered gates (v2)

| Gate | Criterion | Actual | Result |
|---|---|---|---|
| G1 | \|ΔCAGR\| ≤ 1.0pp | −0.22pp | **pass** |
| G2 | ΔCAGR < −1.0pp | not met | fails |
| G3 | ΔSharpe ≥ −0.05 and ΔMDD ≤ +1pp | −0.034 / +1.6pp | Sharpe pass, MDD marginal fail |

**Verdict: momentum is only diversification, so it can be removed (G1 passes);
keep the 0.125 prior because drawdown is slightly worse.**

## On the pre-registered prediction

The card said "\|ΔCAGR\| < 0.5pp". **It holds on v2 (−0.22pp) and fails completely on
v0 (−3.38pp).** Same hypothesis, same data, same prediction, two opposite answers —
the difference is only your implementation choice for portfolio construction.
That is exactly why `CLAIMS.md` must record the code version and fingerprint, not
just the number.

## Why this is still neither "momentum works" nor "momentum is dead"

1. The universe is 45 **still-listed** large caps with a tech tilt; 12-1 momentum
   on such a panel will pick the strongest names of the past year (NVDA / MSFT /
   AVGO and friends).
2. Across the three runs the baseline t-stats were 0.22 / 0.34 / 0.23 — **all
   inside "indistinguishable from zero"**. Keeping or removing momentum is not a
   statistically meaningful choice.
3. Separating "real momentum premium" from "universe-selection effect" requires a
   delisting-inclusive panel (see `docs/adr/002-sample-universe.md`).

## Lessons, in order of importance

1. **Suspect the implementation before the market.** A 3pp "finding" turned out to
   be a portfolio-construction detail. The reference implementation's H13 has the
   same shape: a mechanism adopted at Sharpe +0.017 became a net loss once an
   engine bug was fixed.
2. **"Passed the gate" only means "passed on that code version".** Every engine
   change can move historical conclusions — which is why `CLAIMS.md` pins the
   version and the fingerprint.
3. **The value of pre-registration is not being right; it is discovering how wrong
   you were.** Without the card you would invent an after-the-fact story for
   −3.38pp and take it to live money.
4. **Portfolio construction is part of the strategy.** Same factors, same weights,
   and just moving the sector cap from after selection to inside selection changes
   annual return by 2.6pp. That is why `tests/test_invariants.py` has a dedicated
   caps test.

## Metadata (honest disclosure)

⚠️ The card and the verdict were written in the same session; their `git`
timestamps are identical, so this does **not** satisfy strict pre-registration.
In real use:

```bash
git add graveyard/h00x_xxx/card.md && git commit -m "pre-register H-00x" && git tag pre-h00x
# ... only then is running the experiment allowed
```

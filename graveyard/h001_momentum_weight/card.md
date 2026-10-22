> **English** · [中文](card.zh.md)

# Hypothesis card H-001 — Is the 0.125 momentum weight worth keeping?

> **Status**: verdict recorded (see `verdict.md`)
> **Date**: 2026-10-22
> **Data**: `data/sample/` (45 US large caps, 2014-04-01 .. 2026-09-30)
> **Baseline**: the frozen `config/strategy.yaml`, three factors 0.50 / 0.375 / 0.125

---

## 1. Source claim

The current config gives 12-1 momentum a 0.125 weight, yet its in-sample mean IC
is ≈ 0.008, essentially zero. Why should a factor with no IC keep 12.5% of the
budget? The intuitive answer: it diversifies, or it captures a few big winners
that mean IC averages away.

**Testable claim**: set the momentum weight to zero and renormalise the other two
(0.5714 / 0.4286). Return and risk should not change materially; if they change by
more than ±1pp, momentum's contribution is not "diversification" but something we
cannot see in this sample.

## 2. Mechanism

The classic case for momentum is behavioural (under-reaction) plus limits to
arbitrage. But on a panel of **45 large caps that survived to today**, 12-1
momentum is likely a proxy for "the big tech names that went up keep going up" —
survivorship bias plus tech beta, not a factor premium.

## 3. Pre-registered gates (locked before the run)

| Gate | Criterion | Meaning |
|---|---|---|
| G1 | \|ΔCAGR\| ≤ 1.0pp | momentum is just diversification; removable (simpler system) |
| G2 | ΔCAGR < −1.0pp | momentum contributes, but then explain *where from* |
| G3 | ΔSharpe ≥ −0.05 and ΔMDD ≤ +1pp | removing it does not worsen risk |

**Prediction (written before running)**: G1 holds, \|ΔCAGR\| < 0.5pp.

## 4. Not allowed after the fact

- No adjusting the weights and "re-running to see" after seeing the result.
- No writing "momentum works" — one sample on a biased universe cannot support a
  causal claim.

## 5. Reproduce

```bash
./graveyard/h001_momentum_weight/reproduce.sh
```

> **English** · [中文](verdict.zh.md)

# Verdict H13 — adopted, then falsified four days later

> **Date**: adopted 2026-08-28 → removed 2026-09-01
> **Reproduce**: not reproducible in this repo (mechanism not implemented); this
> directory exists as a **format example**

## Initial result (2026-08-28)

Sharpe +0.017, G3 passed → adopted into config.

## Re-run after the engine's NaN fix (2026-09-01)

| Metric | Baseline | Clamp arm |
|---|---|---|
| Sharpe | 1.169 | **1.103** |
| CAGR | — | **−1.83pp** |
| Turnover | — | **+15.9pp** |

**Conclusion: a net loss. Removed from config; only the monitoring signal remains.**

## Why this is not "bad luck"

The pre-fix run had **scrambled stock selection** (NaN caused unstable ordering).
The "+0.017 Sharpe" was a spurious signal produced by wrong ordering, not by a
real mechanism.

## Three transferable lessons

1. **"Passed the gate" ≠ "the conclusion holds"** — it only means "passed under the
   engine of that moment". Engine correctness is itself an assumption to be tested.
2. **After fixing a bug, re-run every verdict that depended on it** — not just the
   one you suspect.
3. **A mechanism that improves Sharpe by 0.017 should never have reached live
   money.** Set thresholds by signal-to-noise, not by p-value: a tiny improvement
   is more likely to be noise.

## Metadata

Original verdict document: reference implementation
`docs/experiments/h13_crowding_clamp_verdict.md`. This directory is a **teaching
summary** of that document; the numbers and conclusions match, without the
original code paths.

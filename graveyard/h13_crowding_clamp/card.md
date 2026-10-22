> **English** · [中文](card.zh.md)

# Hypothesis card H13 — factor-crowding clamp (archived from the reference implementation)

> **Status**: falsified and removed · **Type**: format example (this repo does not
> implement the mechanism, so it cannot be run here)
> **Source**: reference implementation (two months, 31 hypothesis cards), pre-registered 2026-08-28

## 1. Source claim

Once a factor is widely adopted, marginal trading stops producing alpha: volatility
rises, autocorrelation turns negative, IC decays, and correlation with the market
rises. These four symptoms are **observable**. Therefore clamping the weight of
factors with crowding > 0.75 should reduce exposure to crowded factors without
sacrificing return.

## 2. Mechanism definition

- Crowding score = mean of volatility percentile / negative autocorrelation / IC
  decay / market-correlation percentile (0–1, walk-forward).
- After IC_IR weights are computed, clamp each factor with crowding > 0.75 to a
  0.05 floor; redistribute the freed budget proportionally to non-crowded factors
  (single-factor cap 0.60).
- Crowding scores are injected **lagged one period**, guaranteeing no look-ahead.

## 3. Pre-registered gates

| Gate | Criterion |
|---|---|
| G1 | excess return no worse than baseline |
| G2 | max drawdown no worse than baseline |
| G3 | Sharpe no lower than baseline (zero tolerance) |

**Prediction**: G1–G3 all pass, Sharpe improves slightly.

## 4. Not allowed

- No changing the threshold (0.75) after seeing results.
- No reporting Sharpe without turnover and CAGR.

## 5. Result

See `verdict.md`.

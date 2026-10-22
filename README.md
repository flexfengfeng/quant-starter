> **English** · [中文](README.zh.md)

# quant-starter

> A **small, honest, reproducible** skeleton for a personal quant system.
> Five minutes to run, a week to read, a lifetime to adjust.
>
> *一个**小、诚实、可复现**的个人量化系统骨架。跑起来 5 分钟，读懂一周，改到退休。*

```bash
git clone <this-repo> && cd quant-starter
make run          # ~8 seconds: backtest + six-probe audit + HTML report
open reports/report.html
```

---

## TL;DR

This repo is not a strategy library. It is a **teaching machine**: one boring
quarterly portfolio, four replaceable layers, ten invariant tests, and an audit
that is designed to tell you *no*. It runs offline on a frozen dataset, produces
identical numbers on any machine, and its headline result is **honest but
unimpressive**: +0.79pp annual excess over SPY with t = 0.23. That is the first
lesson — a backtest that looks fine is not the same thing as an edge.

---

## 1. What you see when it runs

```
start                  2014-04-01
end                    2026-09-30
cagr                      14.47%
benchmark_cagr            13.68%
excess_cagr                0.79%
excess_t_stat             0.226      <- indistinguishable from zero
sharpe                    0.892
max_drawdown             -26.87%
turnover_annual           0.685
cost_drag_annual          0.001
mean_ic                   0.008
```

Then `make run` prints six self-checks:

| probe | result | meaning |
|---|---|---|
| Data-timing band | 0.3pp | moving "when did I know it" by one quarter changes annual return by 0.3pp |
| Execution lag | +0.42pp | the price of same-close vs next-day fills |
| Cost sensitivity | still +0.67pp at 24bps | the strategy survives costs |
| Concentration | top-3 names = 28% of P&L | it is not a single-stock bet |
| Beta / Alpha | 0.83 / +2.98% | lower volatility than the market, and slightly ahead |
| **Significance** | **FAIL (t=0.23)** | **not enough evidence to bet** |

**The only correct reading**: the system is mechanically complete, but its excess
return **cannot be distinguished from zero**. The point of the repo is not to
make you believe it — it is to give you the ability to judge *any* system,
including this one, with your own hands.

---

## 2. What it will not do

- It does not promise alpha, sell "proven" parameters, or hide its failures.
- No HFT / intraday / shorting / leverage (individuals lose at those layers —
  see `docs/adr/`).
- No LLM sentiment inside the backtest (that is a future module, not evidence).
- It will not help you bypass the live-money gate in §6.

---

## 3. Repo map

```
config/strategy.yaml      the only parameter file; every adjustment starts here
src/qs/
  config.py               config -> dataclasses, unknown keys raise (anti-typo)
  data/
    loader.py             reads data; raw stays raw, no implicit cleaning
    validate.py           data contract: duplicates/gaps/future data -> fail loudly
    features.py           * available_fundamentals(): the entire PIT guarantee
    manifest.py           input + returns fingerprints, so "same run" is testable
  strategy/
    portfolio.py          Top-N + buffer band + name/sector caps -> target weights
    sells.py              the less obvious of the two sell rules: quality decay
  backtest/
    engine.py             quarterly walk-forward, decide at close -> fill next close
    costs.py              commission + slippage + one-off FX
    audit.py              * six probes: its job is to prove you wrong
    metrics.py            CAGR/Sharpe/MDD/excess/t-stat, all hand-computable
  live/
    dryrun.py             paper account + target orders (no broker connection)
    sizing.py             * how many positions your capital can afford
  report/dashboard.py     single-file HTML, hand-built SVG, zero dependencies
tests/                    10 invariant tests: the referee when you replace a module
graveyard/                falsification archive: predict first, then look
docs/                     ADRs + the five-day workshop
```

Docs are paired: `X.md` is English, `X.zh.md` is 中文. Every doc starts with a
language switch, so a student who reads only English never lands on a Chinese page.

---

## 4. Recursive learning: four levels

Each level is independently replaceable — that is what "recursive" means here.
After replacing something, run `make test`; the tests tell you whether you broke
the system's promises.

| Level | What you do | Acceptance question |
|---|---|---|
| **L0 run** | `make run` | Re-run on another machine — same numbers? Why? |
| **L1 change** | change `top_n` / `rebalance` / weights / costs | strategy effect or noise? use `make audit` |
| **L2 replace** | swap out `features.py` or `portfolio.py` | are tests still green? is it better out-of-sample? |
| **L3 add** | add a whole new stage: cloud, broker, a new hypothesis card | would your finding survive `graveyard/`? |

`LEARNING_PATH.md` gives the concrete exercises and the expected outcome for each
level. The exercises are answerable on purpose: you can do them wrong and watch
the audit catch you.

---

## 5. Strategy specification (the one and only config)

| Item | Value |
|---|---|
| Universe | 45 US large caps (sample; see `CLAIMS.md`) |
| Factors | FCF yield 0.50 / Quality 0.375 / 12-1 Momentum 0.125 |
| Selection | Top 12, 2× buffer band, ≤12% per name, ≤35% per sector |
| Rebalance | quarterly; decide at close, fill the next close |
| Sells | falls out of Top 24; or quality in bottom 25% and down another 30% |
| Costs | 0bps commission + 8bps one-way slippage |
| PIT | fundamentals usable 45 days after fiscal period end (configurable, auditable) |

Design rationale and rejected alternatives: `docs/adr/001-three-factors.md`.

---

## 6. The live-money gate (do not skip it)

The workshop should end at a **paper account**, not at real money. The order is
fixed:

1. One full quarter of paper trading (12 weeks), recording target vs actual weekly.
2. If it passes, **20%** of planned capital live for one quarter.
3. After four quarters, with the rules in `AGENTS.md` still unbroken, consider the full amount.
4. Any time the kill switch fires (single day −5% / cumulative −15% / repeated
   data-contract failures) → stop automated trading and go manual.

Three constraints specific to a Singapore investor (and *not* coding problems):
**30% US dividend withholding**, **US estate-tax exposure above US$60,000** of
US-situs stock, and the risk that ~100% turnover is treated as "trading income"
by IRAS. `make size` prices the first two into your position size.

---

## 7. Where the data comes from, and what it costs

The sample is frozen from the reference implementation's local cache (moomoo
OpenAPI + Yahoo); see `tools/build_sample.py`. **It is survivorship-biased by
construction**: all 45 names are still listed today and have complete history.
Therefore:

> Every number in this repo is an **upper bound**, not an expected return.
> `CLAIMS.md` marks this on each figure.

Want your own universe? The four CSVs in `data/sample/` are the entire interface.
Replace them and `make validate` will stop you first.

---

## 8. Changelog (every change leaves a trace)

- `v0-run` first end-to-end run
- `v1-audit` six probes online (the first honest admission of insignificance)
- `v2-paper` paper account and orders
- `v3-size` capital → number of positions → cost

Git tags are the course dimension: `git diff v1-audit..v2-paper` shows exactly
what "adding a paper-trading stage" changes.

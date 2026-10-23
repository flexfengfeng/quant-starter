# D2 red-team · answer key (teacher only)

> **English** · [中文](answer-key.zh.md)

> Generated from [`biases.json`](biases.json) — edit the JSON, then run
> `python docs/workshop/d2-redteam/kit.py build`. Do not hand-edit this file, and never hand
> either language version to a student.

**The plant**: [`report.html`](report.html) — a fictional manager ("Marlowe Ridge
Capital") pitching a US large-cap quality–momentum fund at Sharpe ~2.0. The
performance series is internally coherent: the chart, the annual table and the
monthly heatmap all agree with each other. The lies are in **labels, method and
fine print** — where they live in real documents.

The briefing: *find at least five biases in forty minutes.*

| id | bias | severity | where |
|---|---|---|---|
| `b01_window_mislabelled` | The headline window is not the window on the label | medium | Hero strip, first card; Executive summary, first sentence. |
| `b02_drawdown_understated` | Maximum drawdown smaller than a single month | medium | Hero card 3; Executive summary ¶3; Risk section. |
| `b03_pit_lookahead` | Point-in-time look-ahead in the fundamental score | obvious | "How the strategy works" → Rebalance. |
| `b04_same_bar_fill` | Signals from the close, filled at the same close | medium | "How the strategy works" → Execution. |
| `b05_gross_of_costs` | Gross returns, with a 1.5% + 15% fee schedule | obvious | Fees section; Notes 5. |
| `b06_survivor_universe` | Today's index, applied to yesterday | obvious | "How the strategy works" → Universe; Notes 3. |
| `b07_benchmark_asymmetry` | Total-return strategy against a price-index benchmark | medium | Executive summary ¶1; Notes 2. |
| `b08_multiple_testing` | t = 2.0 after 34 tries | medium | Notes 4 and 6. |
| `b09_tstat_without_basis` | A t-statistic with no series behind it | subtle | Notes 6. |
| `b10_no_reproducible_basis` | "On request": no returns file, no blotter, no fingerprint | medium | Notes 7; footer. |
| `b11_2022_anomaly` | A long-only 0.62-beta book that "avoided" a −19.4% market | subtle | Executive summary ¶3; Risk section. |

**Three of these are meant to be found at a glance** (severity *obvious*); the rest need the appendix, arithmetic, or a benchmark that does not flatter the strategy. A group that stops at three has not done the exercise.

## `b01_window_mislabelled` · The headline window is not the window on the label

*medium*

**Where**: Hero strip, first card; Executive summary, first sentence.

**The tell**: “since inception, April 2014”

**Why it is wrong**: The 23.6% / Sharpe 2.02 / volatility 10.7% are the numbers of the **live** window, 2019-10 to 2026-09 (7.0 years). The appendix compounds the full 12.5 years to **19.0%**: the 66 months before the live date compound at 13.3%, the 84 live months at 23.6%. A genuine 23.6% over 12.5 years would be 14.20x (US$1.42m); the chart ends at 8.80x (US$880k).

**How to score it**: Compound the annual table, or read the chart's end value. Then compound 2019-10 → 2026-09 off the heatmap: you recover exactly 23.6%. The confession is in Notes 1: "went live on 1 October 2019".

**Calibration on this repo**: `CLAIMS.md` §0 always states the window before the number (2014-04-01 .. 2026-09-30). A performance number without a window is not a number, it is a sales figure.

## `b02_drawdown_understated` · Maximum drawdown smaller than a single month

*medium*

**Where**: Hero card 3; Executive summary ¶3; Risk section.

**The tell**: “never lost more than -8.9% from a peak”

**Why it is wrong**: A peak-to-trough loss can never be smaller than the worst single month. The appendix's June 2022 cell is **-11.2%**, so the maximum drawdown is at least that; compounding the heatmap gives **-15.8%** for the full window.

**How to score it**: Find the reddest cell in the heatmap and compare it with the quoted maximum drawdown. Then compute the running drawdown from the monthly series — two lines of arithmetic.

**Calibration on this repo**: This repo reports max drawdown −26.87% next to the CAGR in `CLAIMS.md` §1, and probe 4 (concentration) exists because drawdowns hide in single names.

## `b03_pit_lookahead` · Point-in-time look-ahead in the fundamental score

*obvious*

**Where**: "How the strategy works" → Rebalance.

**The tell**: “Factor scores use the quarter that ended on the rebalance date — the filings are public by then.”

**Why it is wrong**: The rebalance is on the last trading day of the quarter; the 10-Q for that quarter is filed about 40–45 days later (10-K: 60–90). Using it at the quarter-end close is a six-week peek. "The filings are public by then" is simply false.

**How to score it**: Check the dates, not the prose: a quarter ends 30 Sep, the filing deadline is 40 days later. Any score computed at the quarter-end close from that quarter's statements is peeking.

**Calibration on this repo**: `LEARNING_PATH.md` L2 exercise C: set `disclosure_lag_days` to −45 and watch audit probe 1. On this deliberately boring book the band is 0.3pp; audit.py's own comment: "the sign is not the test, the magnitude is".

## `b04_same_bar_fill` · Signals from the close, filled at the same close

*medium*

**Where**: "How the strategy works" → Execution.

**The tell**: “Orders are worked in the closing auction of the rebalance day”

**Why it is wrong**: The scores are computed from the same closing prices and the same quarter-end fundamentals, and the fill happens in that same closing auction. You cannot know the close before it prints. Even with perfectly honest PIT data, this is the cheapest form of look-ahead.

**How to score it**: Look for "signals from the close, filled at the close" in one sentence. Ask for order timestamps and the actual fill prices.

**Calibration on this repo**: `make audit` probe 2: same-close 14.89% vs next-day 14.47% — a quarterly book pays +0.42pp for realism.

## `b05_gross_of_costs` · Gross returns, with a 1.5% + 15% fee schedule

*obvious*

**Where**: Fees section; Notes 5.

**The tell**: “Returns are gross of management fees, performance fees, transaction costs, FX conversion and dividend withholding tax.”

**Why it is wrong**: The manager's own fee is 1.5% a year plus 15% of the excess. On a 23.6% gross return that is roughly 3.5–5pp of the headline, before 8–24bps of slippage per side and the 30% US dividend withholding a Singapore investor pays.

**How to score it**: Read the fee section and the fine print together, then recompute: gross − 1.5% − 15% × (gross − benchmark) − costs − withholding.

**Calibration on this repo**: This repo's entire cost drag is 0.06pp/yr at 8bps and 68% turnover (`CLAIMS.md` §1); Singapore dividend withholding alone is ~0.4–0.5pp/yr (§3.6). A 1.5% fee is 25 times the repo's whole cost bill.

## `b06_survivor_universe` · Today's index, applied to yesterday

*obvious*

**Where**: "How the strategy works" → Universe; Notes 3.

**The tell**: “as of the September 2026 index review, applied to the full history”

**Why it is wrong**: Applying the current S&P 500 to 2014 deletes every company that was later acquired, delisted, or removed for being bad. The result is not a strategy return, it is a "which companies survived" return — and it is flattered further because the survivors are exactly the mega-caps that drove the index.

**How to score it**: The phrase "applied to the full history". Then ask for one delisted name, one acquisition, one index deletion in the trade blotter. There will be none, because the universe was built after the fact.

**Calibration on this repo**: Reference implementation in `CLAIMS.md` §3.1: adding 165 delisted names took CAGR from 13.11% to 9.89% and excess from −0.75pp to −3.69pp. This repo's 45 names are all still listed, so every number here is an upper bound (README §7).

## `b07_benchmark_asymmetry` · Total-return strategy against a price-index benchmark

*medium*

**Where**: Executive summary ¶1; Notes 2.

**The tell**: “S&P 500 price index”

**Why it is wrong**: The fund holds the stocks, so its returns include dividends; the benchmark excludes them. Over 2014–2026 that is ~1–1.5pp a year of free "excess" before any skill — about a tenth of the claimed 10.0pp.

**How to score it**: "price index" and "dividends are not reinvested" in the same document. Then compare with the total-return version of the same index.

**Calibration on this repo**: `CLAIMS.md` §3.4 lists exactly this bias in this repo ("no dividends … understates the benchmark by roughly 1–1.5pp/yr"). The honest repo is not allowed to hide it; the fake report is.

## `b08_multiple_testing` · t = 2.0 after 34 tries

*medium*

**Where**: Notes 4 and 6.

**The tell**: “34 candidate factor combinations were evaluated”

**Why it is wrong**: With 34 tries, the best t-statistic under the null is expected to be about 2.0–2.2. Calling t = 2.0 "significant at 5%" is exactly the error the search creates: the 5% threshold has already been spent on the other 33 attempts.

**How to score it**: Count the variants in the notes, then apply Bonferroni (0.05 / 34 → |t| ≈ 3.2) or the Harvey–Liu–Zhu bar for a new factor (t > 3.0).

**Calibration on this repo**: `AGENTS.md`: try 30 configs and the best has ~11% chance of being pure luck. Audit probe 6: "Bar for a *new* factor is t>3.0, not 2.0".

## `b09_tstat_without_basis` · A t-statistic with no series behind it

*subtle*

**Where**: Notes 6.

**The tell**: “significant at the 5% level on a two-sided test.”

**Why it is wrong**: A t-statistic needs a mean, a dispersion and an n. The report supplies none: no tracking error, no information coefficient, no monthly excess series, no number of independent observations. You cannot recompute it, so you cannot falsify it — and 12.5 years of annual data is about 13 observations, far too few for t = 2.0 to mean anything. One consistency check the report cannot survive: 10.0pp of annual excess over 12.5 years with a tracking error of roughly 11% implies t ≈ 3.2. A t of 2.0 needs a tracking error near 18%, which a 0.62-beta long-only book does not produce — so 2.0 was not computed from the number that is quoted.

**How to score it**: Ask for the excess-return series. If the answer is "the model" or "the administrator has it", the number is decoration.

**Calibration on this repo**: `make audit` probe 6 prints the t-statistic **with its inputs** (daily excess, mean IC, number of rebalances = 50). A number whose inputs are hidden is not evidence.

## `b10_no_reproducible_basis` · "On request": no returns file, no blotter, no fingerprint

*medium*

**Where**: Notes 7; footer.

**The tell**: “Audited financial statements, a complete trade blotter and the monthly returns file are available to qualified investors on request.”

**Why it is wrong**: "On request" means never. There is no monthly returns file, no trade list, no input fingerprint, no named administrator, custodian or auditor. The report cannot be reproduced, so it cannot be checked — which is precisely what D1 of this workshop is about.

**How to score it**: List what is absent: monthly returns file, trade blotter, data fingerprint, auditor's name, administrator, custodian, and one sentence saying who verified the numbers.

**Calibration on this repo**: `make run` writes `reports/manifest.json` with an input fingerprint and a returns fingerprint; the D1 acceptance question is "re-run on another machine — do the numbers match?". A report that cannot do this is an advertisement.

## `b11_2022_anomaly` · A long-only 0.62-beta book that "avoided" a −19.4% market

*subtle*

**Where**: Executive summary ¶3; Risk section.

**The tell**: “in 2022, when the S&P 500 fell 19.4%, the strategy returned +2.0%”

**Why it is wrong**: A long-only equity book with beta 0.62, no shorting and "no market timing" should have lost roughly 12% in 2022 (0.62 × −19.4%). Returning +2.0% requires market timing, shorting, or an undisclosed allocation — the report denies the first two in the same paragraph. One of its three sentences is false.

**How to score it**: beta × benchmark return first; then ask for the holdings on 31 Dec 2021 and 30 Jun 2022 and the contribution of each name. The absence of an attribution table is itself the answer.

**Calibration on this repo**: Audit probe 5 exists for this: in this repo beta 0.83 with annualised alpha +2.98%, and the probe's comment warns that "if alpha is no better than the t-stat below, the 'excess' is beta timing".

---

## Numbers behind the answer key

These are computed from the fabricated series by `kit.py dump`; they are what an attentive student should be able to derive.

| what | value |
|---|---|
| claimed headline CAGR (12.5 years) | 23.6% → 14.20x, US$1.42m |
| appendix, full window (12.5 years) | **19.0%** → 8.80x, US$880k |
| appendix, live window (2019-10 → 2026-09, 7.0 years) | **23.6%**, vol 10.7%, Sharpe 2.02 |
| full-window Sharpe | 1.60 |
| claimed maximum drawdown | -8.9% |
| appendix worst month (2022-06) | **-11.2%** |
| appendix maximum drawdown, full window | -15.8% |
| appendix maximum drawdown, live window | -15.8% |

## How to run the session (40 minutes)

1. **5 min** — hand out the printed report. Say only: *this was sent to a friend of mine; find what is wrong with it.*
2. **20 min** — pairs, no laptops. They must write **quotes**, not impressions.
3. **10 min** — collect the count. The group median is usually 3; the answer key has 11.
4. **5 min** — close on probe 6: `make audit` shows t = 0.23 for the honest system; this report claims t = 2.0 after 34 tries. The bar for a new factor is t > 3.0, not 2.0.

## Quarantine

- Never quote these numbers in `CLAIMS.md`, `README.md` or `reports/`.
- Delete `docs/workshop/d2-redteam/` from the student fork (the workshop README says so).
- `python docs/workshop/d2-redteam/kit.py check` fails if a planted quote disappears from `report.html` or if a headline number leaks into the honest docs.

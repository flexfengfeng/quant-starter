> **English** · [中文](LEARNING_PATH.zh.md)

# LEARNING_PATH — from "it runs" to "I can judge for myself"

> This is not a syllabus, it is a **verification checklist**. Each level ends with
> an acceptance question; if you cannot answer it, do not move down a level.
> Every exercise is designed so that **you will get it wrong** — getting it wrong
> and being caught by the system is the learning.

---

## L0 · Run (30 minutes)

**Do**: `make run`, open `reports/report.html`.

**Look at**: six numbers, six self-checks, one equity curve.

**Acceptance questions**:
1. Does the `returns` fingerprint match when you run it on two machines? Why can it?
2. Is the 14.47% in the report what the *strategy* earned, or what the *market* gave? Which number answers that?
3. Which of the six probes is FAIL? What does that FAIL mean?

**Hint**: the answer to #3 is "significance". It failing is not a bug; it is the
single most important feature of this repo.

---

## L1 · Change (half a day)

Change one parameter at a time, run twice (before/after), and record both numbers
in `docs/lab-log.md`.

| # | Change | Predict first | Then look at | Lesson |
|---|---|---|---|---|
| 1 | `top_n: 12 → 6` | higher return? more volatility? | `max_drawdown`, `excess_t_stat` | is the extra concentration worth the volatility |
| 2 | `rebalance: quarterly → semiannual` | turnover halves, how much return goes? | `turnover_annual` / `cagr` | turnover is a structural cost; it rarely compresses easily |
| 3 | `execution_lag_days: 1 → 0` | how much does return rise? | difference in `excess_cagr` | that is the price of the "same-close fill" assumption |
| 4 | `slippage_bps: 8 → 30` | is the excess still there? | audit probe 3 | marginal strategies die of cost |
| 5 | weights `momentum: 0.125 → 0.0` | is momentum noise or contribution? | compare with `make explain` percentiles | why is a factor with no IC still in the book |

**Acceptance question**: across those five changes, how many pushed
`excess_t_stat` above 3? If none did, what does that tell you?

**Expected finding**: you will get five different CAGRs spread over several
percentage points — **and none of them is statistically meaningful**. That is
exactly why audit probe 1 (the data-timing band) exists: even a non-strategy
choice like "when is this data available" moves returns by a percentage point.

---

## L2 · Replace (one to two days)

Pick one module and replace it entirely. The tests are the referee.

**Exercise A: replace a factor**
Add a `low_vol` factor (past 252-day volatility, negated) in `data/features.py`,
give it weight 0.1 and drop `momentum` to 0.025.
- Write a hypothesis card first (template in `docs/adr/`): who pays for it? why
  does it persist? what breaks first when it stops working?
- Run `make test` (do the invariants hold?) → `make run` → `make audit`.
- Only if `excess_t_stat` improves **and** no audit probe turns red may you write
  it into `CLAIMS.md`.

**Exercise B: replace a portfolio rule**
Switch from equal weight to score weighting (`weights ∝ composite`), or move the
buffer band from 2.0 to 1.0.
- Predict: which way does turnover move, and why?
- Verify: `turnover_annual` and `cost_drag_annual`.

**Exercise C: deliberately break PIT**
Set `disclosure_lag_days` to `-45` and run once.
- Watch audit probe 1. That is what peeking at the future looks like.
- Then answer: why does a *better* number not prove there is alpha? (Hint: think
  about noise.)

**Acceptance question**: before looking at any backtest result, can you explain
why your replacement *should* be better? If not, you are parameter searching, not
researching.

---

## L3 · Add (a week and up)

**Exercise D: go to the cloud**
- Replace `data/sample/` with a pipeline that fetches daily, writes an immutable
  raw zone, and records a manifest.
- Requirement: after wiping local data and going offline, `make run` must
  reproduce the same `returns` fingerprint from raw + manifest.
- If you use GCS: bucket in `us-central1`, turn off the default-on soft delete
  (it is billed), and remember that reading from your laptop is egress.
- Cheaper alternative: GitHub Actions on a cron → Cloudflare R2 (zero egress) →
  `sync` incrementally to the laptop.

**Exercise E: connect the paper account**
- `live/dryrun.py` already produces target orders. Wire it to moomoo SIMULATE.
- Non-negotiable: **idempotency** (retries must not duplicate orders),
  **reconciliation** (target vs actual), **kill switch**.
- Real-world lesson: moomoo OpenD occasionally "times out but the server already
  accepted the order" — so idempotency is not a nice habit, it is a requirement.

**Exercise F: write your first hypothesis card**
- Use `graveyard/h13_crowding_clamp/card.md` as the template.
- Rule: the card must be written and `git commit`ted *before* you look at results.
- Record the outcome in `graveyard/` or `docs/adr/` either way. **A falsified
  hypothesis is worth more than a confirmed one.**

**Acceptance question**: can you say in one sentence who pays for your edge, why
it persists, and what will break first? If not, you do not have an edge — you
have a pretty curve.

---

## Suggested reading order

1. `README.md` → `CLAIMS.md` (know where each number comes from)
2. `available_fundamentals()` in `src/qs/data/features.py` (the most expensive five lines)
3. `src/qs/backtest/audit.py` (the comments are the course)
4. `graveyard/h13_crowding_clamp/` (what a falsified hypothesis looks like)
5. `docs/adr/` (every decision has a price)

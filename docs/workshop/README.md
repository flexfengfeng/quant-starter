> **English** · [中文](README.zh.md)

# One-week workshop · operator's manual

> Student profile: adult, finance background, Singapore, about to deploy real money.
> The goal is not "learn to write quant code"; it is **to leave able to judge, on
> their own, whether any strategy deserves a bet**.
> Each day ends with one commit and one git tag. The tags are the course:
> `git diff` is how they will re-read it.

---

## D0 · Pre-work (2 hours before the class)

- Install Python 3.11+ and `pip install -e .` (or `pip install pandas numpy pyyaml pytest`).
- Run `make run` and post the terminal output in the group chat.
- Read `README.md` and `CLAIMS.md`.
- **Expected obstacle**: it will not work the first time. Let them fix it — that
  is lesson zero: environment problems are normal.

## D1 · Data and reproducibility

| | Content |
|---|---|
| Morning | Walk through `make validate` line by line; open `data/sample/*.csv`; PIT: why `available_fundamentals` is the most expensive five lines in the system |
| Afternoon | Why ELT vs ETL is about **reproducibility**, not sophistication; run `make run` twice and compare `returns_fingerprint`; then change a data file and watch the fingerprint go red |
| Output | tag `v0-run`; first entry in `docs/lab-log.md` |
| Acceptance | Re-run on another machine — why must the numbers match? If they don't, which file do you suspect first? |

## D2 · Backtest audit (the most important day)

| | Content |
|---|---|
| Morning | Walk through the six probes, emphasising probe 1 (data-timing band) and probe 6 (t=0.23 → FAIL) |
| Afternoon | **Red team**: hand out a fake "Sharpe 2.0" report (prepared by the teacher) and have them find at least five biases; then swap reports and attack each other's |
| Output | tag `v1-audit` + one audit report |
| Acceptance | Why is t=2.0 not enough? (Multiple testing: try 30 configs, the best has ~11% chance of being pure luck.) |

## D3 · Strategy structure and experiment discipline

| | Content |
|---|---|
| Morning | The three constraints and the buffer band in `portfolio.py`; use `make explain` to see today's factor percentiles; read `graveyard/h13_crowding_clamp/` and `h001` |
| Afternoon | Write a hypothesis card (template in `graveyard`), **commit before running**, and write the verdict whichever way it goes |
| Output | one card + one verdict (it will probably be falsified — that is a success) |
| Acceptance | Before it was falsified, did the card already say what would count as falsification? |

## D4 · Paper deployment and cost (Singapore view)

| | Content |
|---|---|
| Morning | `make orders` produces target orders; idempotency (OpenD can "fail" after the order is already accepted), reconciliation, kill switch; book-keeping in `state/paper.json` |
| Afternoon | `make size`: capital → number of names → round-trip cost; 30% dividend withholding; the **US$60,000 estate-tax cliff**; the real cost difference between IBKR and moomoo |
| Output | tag `v2-paper` + the first week of paper records |
| Acceptance | With US$20,000, why should you not buy 20 names? Compute the fixed fee in bps. |

## D5 · Personalisation and the live-money contract

| | Content |
|---|---|
| Morning | Re-derive `top_n` / `max_weight` from capital; decide the universe (is 45 enough?); write a 12-month self-study plan (L2/L3 of `LEARNING_PATH.md`) |
| Afternoon | Sign the **live-money contract**: one quarter paper → 20% of capital → four quarters → full amount; pre-define the kill switch; write down "under what conditions will I switch this system off" |
| Output | tag `v3-size` + the contract (PDF or markdown, signed by both) |
| Acceptance | If after four quarters you are 5pp behind the benchmark, how do you distinguish "factor decay" from "bad luck"? |

---

## What the teacher prepares in advance

1. A fake "good report" (Sharpe 2.0, with three obvious biases: look-ahead, no
   costs, survivor universe).
2. The student's own GitHub repo: push this code as a template and have them
   **fork** it (not clone the teacher's).
3. A printed cost table: moomoo SG vs IBKR SG, including fixed fee per order, FX,
   dividend withholding.
4. One clear sentence: **this week produces no deployable strategy, only an
   auditable system.**

## If time runs short

Keep, in priority order: D2 audit > D1 reproducibility > D4 paper/cost > D3
experiments > D5 personalisation.
With only three days: merge D1+D2 (data and audit), skip D3's experiment writing,
and reduce D4 to cost and the kill switch.

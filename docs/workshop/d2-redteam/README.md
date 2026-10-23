> **English** · [中文](README.zh.md)

# D2 red-team kit — teacher material

> **Quarantine first.** Everything in this directory is a training exercise.
> `report.html` is a **deliberately dishonest** fund report: the manager is
> fictional, and every performance number in it is fabricated. It must never be
> quoted in `CLAIMS.md`, `README.md`, `reports/` or a student's audit report —
> those are the repo's single source of truth, and this is a prop.
>
> Delete this whole directory from the student fork before the week starts
> (the workshop README says so in D2). If a student opens the source and finds
> the `d2-redteam-plant` marker, that is fine: the exercise is to find **which**
> biases are planted, not whether the report is fake.

---

## What is in here

| file | who sees it | what it is |
|---|---|---|
| `report.html` | **students** | the plant: “Annual Review 2026” from a fictional Singapore manager, Sharpe 2.02 — print it, or open it in a browser |
| `answer-key.md` · `answer-key.zh.md` | teacher only | all 11 planted biases: where, the exact quote, why it is wrong, how to score it, and the calibration on this repo |
| `biases.json` | teacher only | source of truth; both answer keys are **generated** from it, so EN and ZH cannot drift |
| `kit.py` | teacher only | `build` / `check` / `dump` — regenerate and verify the kit |

---

## The 40 minutes

| min | what |
|---|---|
| 5 | Hand out the printed report. Say only: *“a friend sent me this; find what is wrong with it.”* No slides. |
| 20 | Pairs, **no laptops**. They must write **quotes**, not impressions. |
| 10 | Collect the count on the board. The median is usually 3; the answer key has 11. |
| 5 | Close on probe 6: the honest system gets **t = 0.23**; this report claims **t = 2.0 after 34 attempts**. The bar for a new factor is t > 3.0. |

Then say the sentence the whole week is built on: *this week produces no
deployable strategy, only an auditable system.*

---

## Student scorecard (put this on the board — not the answers)

| family | question to ask |
|---|---|
| Point-in-time | Were these numbers public when the score was computed? |
| Execution | Which price, which day, which timestamp? |
| Costs & fees | Gross or net — and of *whose* fee? |
| Universe | Who was deleted from the sample? |
| Benchmark | Price index or total return? Same window? |
| Selection | How many variants were tried before this one was kept? |
| Arithmetic | Do the appendix, the chart and the headline agree? |
| Reproducibility | Can you recompute it from files they will hand you? |
| Risk | Is the risk statistic consistent with the worst month? |

A group that stops at the three obvious answers (look-ahead, no costs, survivor
universe) has done half the exercise. The other eight need the appendix.

---

## Why it is hard enough

- The chart, the annual table and the monthly heatmap are **one internally
  consistent series** (19.0% CAGR over 12.5 years, ~11% vol, −15.8% drawdown).
  Nothing in the appendix is arithmetically sloppy, so the report cannot be
  dismissed with “bad math”.
- The lies are in **labels, method and fine print**: 3 obvious, 6 medium,
  2 subtle.
- Two traps only reward a reader who opens the appendix: the headline is the
  7-year *live* window, not “since inception 2014”; and the claimed −8.9%
  maximum drawdown is smaller than the −11.2% month printed in the heatmap.
- The honest numbers in this repo are the counterweight — 14.47% CAGR,
  t = 0.23, probe 6 FAIL. Run `make audit` in the closing five minutes so the
  group leaves with the contrast, not just the trick.

---

## Regenerate and verify

```bash
python docs/workshop/d2-redteam/kit.py build   # report.html + both answer keys
python docs/workshop/d2-redteam/kit.py check   # quotes present? en/zh in sync? leak?
python docs/workshop/d2-redteam/kit.py dump    # the appendix's true numbers
```

`check` fails if a planted quote disappears from `report.html`, if the two answer
keys drift apart, or if a fabricated headline leaks into `CLAIMS.md`,
`README.md`, `LEARNING_PATH.md` or `AGENTS.md`. Run it before every workshop —
it is the same discipline as `make validate`, applied to a document.

---

## Do not

- quote these numbers anywhere outside this directory;
- hand out `answer-key.*` or `biases.json`;
- edit `report.html` by hand — it is generated, and `build` overwrites it;
- write a hypothesis card for it: it is a prop, not a strategy (`AGENTS.md` rule 1
  applies to real ideas, not to bait).

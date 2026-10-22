> **English** · [中文](lab-log.zh.md)

# Lab log — one variable per run

| # | Date | What changed | Before | After | Δ | t-stat | My prediction | Was I right? | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| 1 | | (example) top_n 12→6 | CAGR 14.47% | | | | more volatility, lower return | | 6 names × 12% cap = 28% cash; this measures cash drag |
| 2 | | | | | | | | | |

## Recording rules

1. Change one parameter at a time; change two and you no longer know which one did it.
2. "My prediction" must be written *before* the run.
3. The verdict column accepts only three values: **adopt / reject / inconclusive**.
   "Looks good" counts as not writing anything.
4. Any "adopt" must pass all six `make audit` probes.

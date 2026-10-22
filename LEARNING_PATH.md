# LEARNING_PATH — 从"跑通"到"能独立判断"

> 这不是章节列表，是**验证清单**。每一层都有一句"过关问题"；答不上来就不要往下一层走。
> 每一层的练习都设计成**你会做错**——做错然后被系统抓住，才是学习。

---

## L0 · 跑（30 分钟）

**做**：`make run`，打开 `reports/report.html`。

**观察**：六个数字、六项自检、一条净值曲线。

**过关问题**：
1. 同一份代码在两台机器上跑出的 `returns` 指纹一样吗？为什么它能一样？
2. 报告里的 14.69% 是"策略赚的"还是"市场给的"？看哪个数字能回答？
3. 六项自检里哪一项是 FAIL？它 FAIL 意味着什么？

**提示**：第 3 题答案是"显著性"。它 FAIL 不是 bug，是这个仓库最重要的一个功能。

---

## L1 · 改（半天）

一次只改一个参数，跑两次（改前/改后），把两个数字记在 `docs/lab-log.md`。

| # | 改什么 | 先预测 | 然后看 | 教训 |
|---|---|---|---|---|
| 1 | `top_n: 12 → 6` | 收益更高？波动更大？ | `max_drawdown` 和 `excess_t_stat` | 集中度换来的波动是否值得 |
| 2 | `rebalance: quarterly → semiannual` | 换手降一半，收益少多少？ | `turnover_annual` / `cagr` | 换手是结构成本，压不动是常态 |
| 3 | `execution_lag_days: 1 → 0` | 收益涨多少？ | `excess_cagr` 差 | 这就是"同日成交"这个假设的价格 |
| 4 | `slippage_bps: 8 → 30` | 超额还在吗？ | audit 第 3 项 | 边缘策略死于成本 |
| 5 | 权重 `momentum: 0.125 → 0.0` | 动量是噪声还是有贡献？ | 与 `make explain` 的百分位对照 | 一个没有 IC 的因子为什么还在 |

**过关问题**：这五次改动里，有几次让 `excess_t_stat` 超过 3？如果一次都没有，说明什么？

**预期发现**：你会得到 5 个不同的 CAGR，跨度好几个百分点——**但它们都没有统计意义**。这正是 `audit` 第 1 项（数据时点带）存在的理由：连"数据什么时候可得"这种非策略选择都能移动 1pp，何况你的参数。

---

## L2 · 换（一到两天）

选一个模块，整个换掉，让测试当裁判。

**练习 A：换因子**
在 `data/features.py` 里加一个 `low_vol`（过去 252 日波动率，取负），权重给 0.1，把 `momentum` 降到 0.025。
- 先写假设卡（`docs/adr/` 里的模板）：它凭什么有超额？谁在付钱？失效时什么会先坏？
- 跑 `make test`（不变量还成立吗）→ `make run` → `make audit`。
- 只有在 `excess_t_stat` 变好 **且** audit 六项没有变红时，才允许写进 `CLAIMS.md`。

**练习 B：换组合规则**
把等权改成"分数加权"（`weights ∝ composite`），或把缓冲带从 2.0 改成 1.0。
- 预测：换手会怎么变？为什么？
- 验证：`turnover_annual` 和 `cost_drag_annual`。

**练习 C：故意破坏 PIT**
把 `disclosure_lag_days` 改成 `-45`，跑一次。
- 看 audit 第 1 项怎么变。这就是"偷看未来"长什么样。
- 然后回答：为什么它变好的方向**不一定**说明有 alpha？（提示：想想噪声）

**过关问题**：你的替换，在**没有看回测结果之前**，能说清楚它为什么应该更好吗？
说不清 = 你在做参数搜索，不是在研究。

---

## L3 · 加（一周及以上）

**练习 D：上云**
- 把 `data/sample/` 换成"每天从数据源拉、落不可变 raw、写 manifest"的管线。
- 要求：`make run` 在断网、删除本地数据后，仍能凭 manifest 与 raw 复现同一个 `returns` 指纹。
- GCS 的话：bucket 放 `us-central1`，关掉默认开启的 soft delete（它是计费的），并记住从笔记本读是 egress。
- 更省的做法：GitHub Actions 定时 → Cloudflare R2（零出口费）→ 本地 `sync` 增量。

**练习 E：接纸面账户**
- `live/dryrun.py` 已经能生成目标订单。把它接到 moomoo SIMULATE。
- 必须实现：**幂等**（重试用不产生重复单）、**对账**（目标 vs 实际）、**kill switch**。
- 真实教训：moomoo OpenD 偶发"超时但服务器已收单"——所以幂等不是好习惯，是必须。

**练习 F：写第一张假设卡**
- 用 `graveyard/h13_crowding_clamp/card.md` 当模板。
- 规则：卡片写完、`git commit` 之后才允许看结果。
- 结果无论好坏都写进 `graveyard/` 或 `docs/adr/`。**被证伪的假设比被证实的更值钱。**

**过关问题**：能不能用一句话说出你的 edge 由谁支付、为什么持续、什么会先坏？
答不出 = 还没有 edge，只有一段好看的曲线。

---

## 建议的后续阅读顺序

1. `README.md` → `CLAIMS.md`（知道每个数字的来历）
2. `src/qs/data/features.py` 的 `available_fundamentals()`（全系统最贵的 5 行）
3. `src/qs/backtest/audit.py`（六项检查的注释就是课程）
4. `graveyard/h13_crowding_clamp/`（一个被证伪的假设长什么样）
5. `docs/adr/`（每个决定都有代价）

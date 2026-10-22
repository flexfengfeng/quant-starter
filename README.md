# quant-starter

> 一个**小、诚实、可复现**的个人量化系统骨架。跑起来 5 分钟，读懂一周，改到退休。
>
> *A small, honest, reproducible personal quant system — built for learning, safe to start with.*

```bash
git clone <this-repo> && cd quant-starter
make run          # 约 8 秒：回测 + 六项自检 + HTML 报告
open reports/report.html
```

---

## TL;DR (English)

This repo is not a strategy library. It is a **teaching machine**: one boring
quarterly portfolio, four replaceable layers, nine invariant tests, and an audit
that is designed to tell you *no*. It runs offline on a frozen dataset, produces
the same numbers on any machine, and its headline result is **honest but
unimpressive**: +0.79pp annual excess over SPY with t = 0.23. That is the first
lesson — a backtest that looks fine is not the same thing as an edge.

---

## 1. 跑起来你会看到什么

```
start                  2014-04-01
end                    2026-09-30
cagr                      14.47%
benchmark_cagr            13.68%
excess_cagr                0.79%
excess_t_stat             0.226      <- 与零无法区分
sharpe                    0.892
max_drawdown             -26.87%
turnover_annual           0.685
cost_drag_annual          0.001
mean_ic                   0.008
```

然后 `make run` 会打出六项自检：

| 检查 | 结果 | 含义 |
|---|---|---|
| 数据时点带 | 0.3pp | 只把"何时知道财报"挪一个季度，年化就差 0.3pp |
| 执行滞后 | +0.42pp | 同日成交 vs 次日成交的差价 |
| 成本敏感 | 24bp 下仍 +0.67pp | 这个策略扛得住成本 |
| 集中度 | 前 3 名占 28% | 不是赌一只票 |
| Beta / Alpha | 0.83 / +2.98% | 比市场波动更低，却略胜 |
| **显著性** | **FAIL (t=0.23)** | **证据不足以下注** |

**唯一正确的读法**：这套系统机械上是完整的，但它目前的超额收益**在统计上无法与零区分**。repo 的目标不是让你相信它，而是让你有能力**亲手判断任何一套系统**——包括这一套。

---

## 2. 它不会做什么

- 不承诺 alpha，不提供"稳赚"参数，不隐藏失败。
- 不做高频/日内/做空/杠杆（个人在这些层级必输，见 `docs/adr/`）。
- 不把 LLM 的情绪判断塞进回测（那是未来的模块，不是现在的证据）。
- 不帮你绕过实盘闸门（见 §6）。

---

## 3. 仓库地图

```
config/strategy.yaml      唯一参数文件。每一步调整都从改这里开始
src/qs/
  config.py               参数 -> 数据结构，未知键直接报错（防手滑）
  data/
    loader.py             读数据。原始数据保持原始，不做隐式清洗
    validate.py           数据契约：重复/缺失/缺口/未来数据 -> 大声失败
    features.py           ★ available_fundamentals()：PIT 的全部保证就这一处
    manifest.py           输入指纹 + 收益指纹：让"同一次运行"可被检验
  strategy/
    portfolio.py          Top-N + 缓冲带 + 单票/行业上限 -> 目标权重
    sells.py              两条卖出规则里更反直觉的一条：质量恶化
  backtest/
    engine.py             季度 walk-forward，决策日收盘 -> 次日收盘成交
    costs.py              佣金 + 滑点 + FX 一次性成本
    audit.py              ★ 六项自检：它的工作是证明你错了
    metrics.py            CAGR/Sharpe/MDD/超额/t 值，全部可手算
  live/
    dryrun.py             纸面账户 + 目标订单（不连券商）
    sizing.py             ★ 你的资金能养几个仓位（固定费用是隐形杀手）
  report/dashboard.py     单文件 HTML，手搓 SVG，零依赖
tests/                    10 个不变量测试：替换任何模块后由它们守门
graveyard/                证伪档案：先预测，再看答案
docs/                     ADR + 工作坊五天
```

---

## 4. 递归学习：四层台阶

每一层都能独立替换——这就是"递归"。替换后跑 `make test`，测试告诉你有没有破坏整体。

| 层 | 你做什么 | 过关问题 |
|---|---|---|
| **L0 跑** | `make run` | 换台机器重跑，数字一样吗？为什么？ |
| **L1 改** | 改 `top_n` / `rebalance` / 权重 / 成本 | 变化是策略效应还是噪声？用 `make audit` 回答 |
| **L2 换** | 换掉 `features.py` 或 `portfolio.py` | 测试还绿吗？样本外更好吗？ |
| **L3 加** | 加一个新环节：上云、接券商、写新假设卡 | 你的新发现能过 `graveyard/` 里的标准吗？ |

`LEARNING_PATH.md` 给出了每一层的**具体练习 + 预期结果**。练习是有答案的：你可以故意做错，然后看审计怎么抓住你。

---

## 5. 策略规格（当前唯一配置）

| 项 | 值 |
|---|---|
| 宇宙 | 45 只美股大盘（样本，见 CLAIMS） |
| 因子 | FCF 收益率 0.50 / 质量 0.375 / 12-1 动量 0.125 |
| 选股 | Top 12，缓冲带 2×，单票 ≤12%，行业 ≤35% |
| 再平衡 | 季度，决策日收盘 → 次日收盘成交 |
| 卖出 | 排名跌出 Top 24；或质量落到底部 25% 且再跌 30% |
| 成本 | 佣金 0 + 滑点 8bp 单边 |
| PIT | 财报期末 + 45 天可用（可配，可被审计） |

设计理由与替代方案见 `docs/adr/001-three-factors.md`。

---

## 6. 实盘闸门（不要跳过）

工作坊结束时应该停在**纸面账户**，不是真钱。真钱的顺序是写死的：

1. 一个完整季度纸面运行（12 周），每周记录目标 vs 实际。
2. 通过后，用 **20%** 的计划资金实盘一个季度。
3. 四个季度后、且 `CLAUDE.md`/`AGENTS.md` 里的纪律未被违反，才考虑全额。
4. 任何时刻触发 kill switch（单日 -5% / 累计 -15% / 数据校验连续失败）→ 停止自动交易，转人工。

新加坡投资者的三个具体约束（不是代码问题）：美股股息 **30% 预扣**、**US$60,000 以上**美国境内资产的**遗产税**暴露、以及 100% 换手被 IRAS 认定为"交易性收入"的风险。`make size` 会把前两条算进你的仓位。

---

## 7. 数据的来历与局限

样本数据从参考实现（moomoo OpenAPI + Yahoo）的本地缓存冻结而来，见 `tools/build_sample.py`。
**它天然有存活者偏差**：45 只都是"今天还活着并且有完整历史"的名字。因此：

> 本 repo 的任何数字都是**上界**，不是预期收益。`CLAIMS.md` 里每个数字都标注了这一点。

想换成自己的宇宙？`data/sample/` 的四个 CSV 就是全部接口，替换即可，数据契约会先拦你一遍。

---

## 8. 更新日志（每一次改动都必须留痕）

- `v0-run` 首次跑通
- `v1-audit` 六项自检上线（第一次诚实地承认不显著）
- `v2-paper` 纸面账户与订单
- `v3-size` 资金规模 → 仓位数量 → 成本

git tag 就是课程维度：`git diff v1-audit..v2-paper` 看到"加一个纸面环节"到底改了什么。

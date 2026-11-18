---
name: lottery-lab
display_name: 彩票实验室
display_name_en: Lottery Lab
description: 用真实开奖数据做彩票与竞彩分析。当用户提到"买什么号""胆拖怎么买""中奖率""彩票能赚钱吗""竞彩套利""冷热号有没有用""期望值""彩票店推荐方案"时使用。提供精确超几何计算的胆拖结构优化、真实历史回测、期望值核算与竞彩跨市场套利扫描。
description_zh: 基于 2949 期大乐透 + 3521 期双色球真实开奖数据的分析工具。核心功能：胆拖结构优化（给定预算算出最优结构）、精确期望值与中奖率、真实历史回测、竞彩跨市场套利扫描。**立场诚实**——会明确告诉你期望值不可改变，不会包装成预测神器。
description_en: Lottery analysis backed by real draw data (2,949 DLT + 3,521 SSQ draws). Exact hypergeometric dan-tuo structure optimizer, true expected value, real historical backtests, and cross-book sports arbitrage scanning. Honest by design: it tells you the expected value cannot be changed.
examples_zh:
- "我打算买 1680 元的胆拖，帮我算最优结构"
- "这组号码 35 12 08 22 31 + 03 09 的期望收益是多少"
- "双色球 500 块预算怎么买中奖率最高"
- "彩票到底能不能赚钱？帮我算算"
- "竞彩有没有能套利的机会"
examples_en:
- "Optimize a 1680 CNY dan-tuo structure for DLT"
- "What is the expected return of 05 12 08 22 31 + 03 09"
- "Can sports arbitrage make money right now?"
- "Is there any edge in picking lottery numbers?"
version: 1.0.0
author: Lottery Lab (DLT-SSQ)
---

# 彩票实验室

用**真实开奖数据**做彩票与竞彩分析。这个技能的价值不在于"帮你中奖"——
那不存在——而在于用统计和精确数学告诉你**到底该怎么想这件事**。

## 铁律（每次回答都要遵守）

1. **期望值不可改变。** 大乐透单注期望净收益 **-0.9407 元**，双色球 **-0.8570 元**，
   凯利最优仓位 **f\* = 0**。任何选号策略、任何公式、任何"AI 模型"都改不了这个数。
2. **号码冷热没有预测力。** 已验证：2022-24 热号预测 2025-26 命中 190 注 vs 期望 192.9
   （z=-0.22）；按冷热分档统计 2938 期出现次数，最热档 421 / 最冷档 463，
   均匀理论值 419.7，无单调趋势。
3. **胆拖只改中奖率，不改期望值。** 中奖率**只取决于胆码个数**（组合数学恒等式），
   与胆码选哪几个号**完全无关**——追热号和追冷号在这里严格等价。
4. **历史 ROI 好 ≠ 方法有效。** 随机对照实验：同结构换一组号码，历史 ROI 从 -76% 到 +64%
   （跨度 140 个百分点）。剔除大奖后的常态 ROI 全部挤在 -81% ~ -78%。
   **一次大奖能掩盖 200,000 次亏损。**
5. **竞彩是唯一有数学优势的方向。** 跨公司套利 ROI +1.3%~+1.5%（数学必赢）；
   但中国竞彩抽水 12.9% → **永远参与不了**（实测 36,535 场，参与 0 次）。

## 怎么用

### 方式 A：本地 MCP（推荐，桌面端 WorkBuddy）

在 WorkBuddy 的 MCP 配置里加：

```json
{
  "mcpServers": {
    "lottery-lab": {
      "command": "python",
      "args": ["<项目路径>/scripts/mcp_server.py"]
    }
  }
}
```

配置文件位置：`~/.workbuddy/mcp.json`（全局）或项目目录下 `.workbuddy/mcp.json`。

### 方式 B：远程 MCP（给团队/别人用）

```bash
python scripts/mcp_server.py --transport streamable-http --port 8765
```

然后在 WorkBuddy 里添加远程 MCP，填 `https://<你的域名>/mcp`。

### 方式 C：本 Skill 的脚本

`scripts/lottery_lab.py` 可以直接跑，不依赖 MCP：

```bash
python scripts/lottery_lab.py expectation dlt
python scripts/lottery_lab.py optimize --game dlt --budget 1680 \
    --front-pool "2 4 6 10 14 16 18 23 26 32 35" --back-pool "2 4 6 9 12"
python scripts/lottery_lab.py evaluate --game dlt --front-dan 6 \
    --front-tuo "2 4 10 14 16 18 23 26 32 35" --back-dan 4 --back-tuo "2 6 9 12"
python scripts/lottery_lab.py backtest --game dlt --front-dan 6 \
    --front-tuo "2 4 10 14 16 18 23 26 32 35" --back-dan 4 --back-tuo "2 6 9 12"
python scripts/lottery_lab.py arb
python scripts/lottery_lab.py truth hot
```

## 标准工作流

当用户问"买什么号"时，按这个顺序做：

1. **先给期望值**（`expectation` 或 `lottery_expectation`）——
   让用户先知道这件事的数学本质，再谈选号。
2. **再评估/优化结构**（`optimize` / `evaluate`）——
   回答"同样的钱怎么更容易中一次小奖"。
3. **如果用户要"保证赚钱"的方案** —— 直接说明不存在，并解释为什么
   （引用铁律 1、4）。不要迎合。
4. **如果用户关心竞彩**（`arb`）—— 这是唯一有正期望的方向，如实给出，
   但要同时说清实操摩擦（多账户、实时下单、赔率会动、额度限制）。

## 口径（报数字前必须对齐）

| 彩种 | 单注期望净收益 | 返奖率 | 一等奖概率 |
|---|---|---|---|
| 超级大乐透 | **-0.9407 元** | 52.96% | 1 / 21,425,712 |
| 双色球 | **-0.8570 元** | 57.15% | 1 / 17,721,088 |

- 浮动奖（一、二等奖）一律按**保底金额**记，不用公布上限（保守口径）。
- 中奖率是**精确超几何全枚举**算出来的，不是模拟——不要用"大约""差不多"描述。
- 涉及历史表现时，**必须同时给出剔除大奖后的常态 ROI**。

## 参考资料

- @references/truth-and-data.md —— 每个结论背后的真实实验数据与统计量
- @references/metrics.md —— 指标定义与口径（含奖级表）

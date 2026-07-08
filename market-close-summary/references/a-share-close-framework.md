# A-share Market Close Framework

Use this reference for full A-share closing reviews, especially when the user provides raw data or asks for a repeatable end-of-day template.

## Paste-in Data Template

Ask the user to paste any available fields. Do not require every field.

```text
日期：

主要指数：
- 上证指数：
- 深证成指：
- 创业板指：
- 科创50：
- 沪深300：
- 中证500：
- 中证1000：

成交与情绪：
- 两市成交额：
- 较昨日：
- 上涨/下跌家数：
- 涨停/跌停：
- 连板高度：
- 北向/主力/ETF资金：

板块与主题：
- 领涨行业：
- 领跌行业：
- 活跃题材：
- 弱势题材：
- 权重表现：
- 小微盘表现：

盘中走势：
- 开盘：
- 上午：
- 下午：
- 尾盘：

背景信息：
- 政策/宏观：
- 海外市场：
- 商品/汇率/利率：
- 重要公司或行业新闻：
```

## Market Temperature Rubric

Use judgment; do not turn this into a mechanical score when the facts conflict.

| Temperature | Typical Evidence |
| --- | --- |
| 强势进攻 | Main indexes rise with broad breadth, turnover expands, leading themes hold into close, few severe drawdowns. |
| 修复偏强 | Indexes rebound or stabilize, breadth improves, turnover is acceptable, but leadership is still concentrated. |
| 中性震荡 | Indexes mixed, turnover flat or shrinking, themes rotate quickly, no obvious panic or broad risk appetite. |
| 偏弱防守 | Indexes fall or close weak, decliners dominate, turnover either shrinks on rebound or expands on selling. |
| 风险释放 | Broad decline, limit-down count rises, high-beta themes collapse, support fails, or macro/policy shock dominates. |

## Analysis Checklist

### 1. Index Versus Breadth

Check whether the index move matches the experience of most stocks:

- Index up + breadth strong: real risk appetite.
- Index up + breadth weak: weight support or narrow defense.
- Index down + breadth stable: index drag may be concentrated.
- Index down + breadth poor: broad pressure.

### 2. Turnover Quality

Interpret volume with price action:

- 放量上涨: stronger if breadth and leadership confirm.
- 缩量上涨: repair, but continuation needs new money.
- 放量下跌: risk release or panic, examine close and support.
- 缩量下跌: weak participation, may reflect wait-and-see rather than capitulation.

### 3. Leadership Durability

Call a theme "主线" only when several of these are true:

- Sector breadth is broad, not just one or two leaders.
- Volume is meaningfully higher than recent days.
- Leading stocks resist intraday index weakness.
- Catalyst is clear: policy, earnings, supply-demand, product cycle, or liquidity.
- The theme has continuity across multiple days or reactivates after a clean pullback.

Call it "轮动" or "脉冲" when participation is thin, late-day chasing dominates, or the theme relies only on headlines.

### 4. Divergence Signals

Flag these carefully:

- 指数红、个股绿: weak structure under index cosmetics.
- 成交放大但冲高回落: disagreement or distribution risk.
- 题材高位补跌: sentiment damage.
- 权重护盘、小票杀跌: defensive market, poor earning effect.
- 普涨但无量: repair can fade without follow-through.
- 连板高度下降: short-term sentiment cooling.

### 5. Cause Attribution

Use layered attribution:

1. Direct catalyst: policy, announcement, earnings, macro print.
2. Liquidity condition: rates, FX, turnover, ETF or northbound flow.
3. Positioning: crowded trades, oversold rebound, style rotation.
4. Market microstructure: intraday defense, close strength, breadth.

Avoid writing "because of X" when X is only plausible. Use "可能与...有关", "更像是...", or "目前证据更支持...".

## Default Output Template

```markdown
## 一句话结论

今天A股属于【市场温度】。核心不是【指数涨跌本身】，而是【结构判断】。

## 今日盘面

- 指数：
- 成交：
- 涨跌家数：
- 情绪：

## 市场结构

今天的主要特征是【权重/小票/成长/价值/周期/消费/科技】之间的分化。

## 主线与分歧

- 主线：
- 辅线：
- 分歧：
- 需要排除的噪音：

## 异动归因

更可能的驱动因素：

1. 
2. 
3. 

## 风险信号

- 
- 
- 

## 明日观察

1. 成交额能否维持在【阈值】附近或以上。
2. 【关键指数/板块】能否继续站稳或反包。
3. 今日主线的前排是否继续强，后排是否扩散。
4. 跌停、炸板、连板高度是否恶化。

## 操作环境

当前更适合【进攻/精选结构/防守/等待】。若明天出现【确认条件】，环境改善；若出现【失效条件】，应降低预期。
```

## Style Requirements

- Lead with the conclusion, then evidence.
- Keep explanations concrete and market-facing.
- Write "观察点" as falsifiable conditions, not vague reminders.
- Prefer "市场环境" language over stock recommendations.
- If the user asks for a public-facing article, make the language smoother but preserve the same analytical spine.
- For fixed report output, follow [report-format.md](report-format.md). Use Markdown for editable notes and HTML for visual daily reports.

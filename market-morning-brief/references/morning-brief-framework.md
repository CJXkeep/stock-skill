# A-share Morning Brief Framework

Use this reference for structured pre-market briefs. The goal is to convert overnight and prior-day events into today's market hypotheses.

## Time Window

Default window:

```text
上一交易日A股收盘后 -> 今日A股开盘前
```

For Monday briefs, include weekend events. For post-holiday briefs, explicitly state the longer window.

## Paste-in Event Template

Ask the user to paste any available fields. Do not require every field.

```text
日期：
时间窗口：

隔夜全球市场：
- 美股：
- 纳指/科技股/半导体：
- 中概股：
- 港股/ADR/期货：
- 美债收益率：
- 美元/人民币：
- 黄金/原油/铜/其他商品：

国内宏观与政策：
- 国务院/部委：
- 央行/财政：
- 证监会/交易所：
- 产业政策：

海外宏观与地缘：
- 美联储/经济数据：
- 关税/出口管制：
- 地缘事件：

产业与主题：
- AI/算力/半导体：
- 新能源/锂电/光伏：
- 机器人/高端制造：
- 医药/消费/地产/金融：
- 资源品/军工/其他：

公司与财报：
- 重要公告：
- 财报/业绩预告：
- 大公司外溢影响：
```

## Event Triage

Classify each event:

| Level | Definition | Treatment |
| --- | --- | --- |
| S | Directly affects broad liquidity, risk appetite, core indexes, or major policy expectations. | Must discuss and map to market hypotheses. |
| A | Affects a large sector or a crowded theme. | Discuss in sector watchlist and observation checklist. |
| B | Useful context but weak direct market impact. | Mention briefly if it clarifies the backdrop. |
| C | Noise, rumor, or too narrow. | Exclude unless the user specifically asks. |

## Transmission Map

For every important event, map:

1. Event: what happened.
2. Evidence quality: official, primary data, reputable media, market move, rumor.
3. Direction: risk-on, risk-off, mixed, sector-specific.
4. A-share path: index, style, sector, liquidity, sentiment, opening behavior.
5. Confirmation: what should happen in the first hour or by close if the market accepts the event.
6. Invalidation: what would show the event is ignored or reversed.

## Default Markdown Template

```markdown
# A股盘前简报｜YYYY-MM-DD

## 一句话总览

今日盘前环境偏【risk-on/risk-off/震荡/结构性分化】。核心变量是【变量】，更可能影响【指数/风格/板块/风险偏好】。

## 隔夜全球市场

- 美股/科技：
- 中概/港股：
- 利率/汇率：
- 商品：

## 宏观与政策

- 国内：
- 海外：
- 监管/交易所：

## 产业与主题催化

- 可能受益：
- 可能承压：
- 分歧较大：

## 公司与财报线索

- 
- 

## 今日A股影响路径

| 事件 | 可能影响 | 受影响方向 | 今日确认点 |
| --- | --- | --- | --- |
|  |  |  |  |

## 重点观察清单

1. 开盘强弱和高开低走/低开修复。
2. 人民币、港股、中概和外资相关线索。
3. 今日主线是否在第一小时扩散。
4. 成交额是否支持风险偏好。
5. 弱势方向是否继续扩散。

## 风险与反证

- 
- 
- 

## 数据来源与置信度

- 数据源：
- 官方来源：
- 媒体来源：
- 未验证/低置信度：
```

## Style Rules

- Lead with the market hypothesis, not the headline list.
- Keep event count selective. A strong brief usually has 3-7 meaningful events, not 30 headlines.
- Write observation points as falsifiable checks.
- Mark source confidence clearly.
- Avoid single-cause certainty before the market opens.

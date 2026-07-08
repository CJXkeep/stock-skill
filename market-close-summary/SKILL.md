---
name: market-close-summary
description: Create a structured A-share market close summary after the China A-share session ends, including data collection, fixed Markdown output, and optional fixed-format HTML report rendering. Use when the user asks for 收盘复盘, 大盘总结, 市场收评, A股收盘总结, 收盘日报, 可视化报告, HTML report, fixed-format report, render close report, 今日市场环境判断, 明日观察点, or wants Codex to turn index, breadth, sector, capital-flow, news, and sentiment information into a concise end-of-day market review.
---

# Market Close Summary

## Purpose

Produce a disciplined A-share closing review that explains what happened, why it happened, what mattered structurally, and what to watch next. Prioritize evidence, market structure, and decision usefulness over prediction.

## Data Handling

Ask for missing key data only when the user expects a data-backed review and provides no market facts. If partial data is available, proceed and clearly label gaps.

Prefer free and public data sources. Use [references/free-data-sources.md](references/free-data-sources.md) when choosing sources, designing an automated fetch workflow, or explaining data limitations.

Prefer inputs in this order:

1. Major indexes: Shanghai Composite, Shenzhen Component, ChiNext, STAR 50, CSI 300, CSI 500, CSI 1000.
2. Turnover and breadth: total成交额, change versus prior day, rising/falling stocks, limit-up/limit-down count, 连板高度.
3. Sector and theme performance: leading/lagging industries, concept themes, market-cap style, growth/value split.
4. Capital and flow clues: northbound if available, ETF/large-cap flow clues, main-board versus small-cap activity.
5. Catalyst context: policy, macro, overseas markets, commodity/FX/rates, company or industry news.
6. Intraday behavior: gap, opening direction, afternoon rebound/fade, close strength, volume-price relationship.

When live data access is unavailable, tell the user what data is needed and offer a template they can paste.

When using free sources, record source names and retrieval time in the review if possible. Cross-check major index values, turnover, and breadth when a source looks stale or inconsistent.

For automated collection, use `scripts/collect_a_share_close.py`. It produces a normalized JSON snapshot from optional AkShare plus Eastmoney public endpoints. Treat its output as a starting point and still apply the cross-check rules in [references/free-data-sources.md](references/free-data-sources.md).

## Workflow

1. Establish market temperature.
   Classify the day as strong, constructive, neutral, weak, or risk-off using index direction, breadth, turnover, and close behavior together.

2. Separate index movement from market structure.
   Identify whether the move was driven by large-cap indexes, small/mid caps, specific sectors, or broad participation.

3. Identify the main line.
   Distinguish primary themes from one-day noise. A main line needs at least two of: sector breadth, volume support, repeated intraday defense, policy/earnings catalyst, or cross-stock consistency.

4. Explain causality with restraint.
   Tie moves to observable evidence. Avoid single-cause certainty unless the evidence is unusually direct.

5. Convert observations into tomorrow's checklist.
   Give concrete confirmation/invalidation points: turnover threshold, index level or behavior, sector continuation condition, risk signal, and sentiment marker.

6. End with an actionable stance.
   Use environment language such as aggressive, selective, defensive, or wait-and-see. Do not give personalized investment advice unless the user provides mandate, holdings, and risk constraints.

## Analysis Dimensions

Use a stable dimension set: market temperature; index, breadth, and liquidity; style and structure; main line and rotation; sentiment and risk; catalyst attribution; tomorrow's observation checklist; data quality.

## Output Shape

Use Chinese by default. Keep the review concise unless the user asks for a long-form report.

Default Markdown sections:

1. `一句话结论`
2. `今日盘面`
3. `市场结构`
4. `主线与分歧`
5. `异动归因`
6. `风险信号`
7. `明日观察`
8. `操作环境`
9. `数据质量`

For browser viewing, screenshots, or repeated daily archives, use a fixed HTML report. Fill [assets/close-report-template.html](assets/close-report-template.html) with the same analysis rather than inventing a new layout each time.

Use [references/a-share-close-framework.md](references/a-share-close-framework.md) when a complete checklist, paste-in data template, scoring rubric, or full output template is useful.
Use [references/free-data-sources.md](references/free-data-sources.md) when data sourcing, automation, free API selection, or fallback planning matters.
Use [references/report-format.md](references/report-format.md) when choosing Markdown versus HTML, changing analysis dimensions, or producing a fixed-format report.
Use [references/platform-integration.md](references/platform-integration.md) when adapting this skill to OpenClaw, Hermens, or another non-Codex agent runtime.
Use `scripts/collect_a_share_close.py --date YYYY-MM-DD` when the user wants to collect free-source data before writing the review.
Use `scripts/render_close_report.py <snapshot.json>` to render the snapshot and optional analysis JSON into a fixed HTML report.

## Guardrails

- Do not fabricate market data. If data is absent, state the gap.
- Do not present a review as investment advice.
- Do not overfit one index. A-share closes often require breadth, turnover, and theme structure to interpret correctly.
- Do not call a theme "主线" based only on top gainers; require participation and persistence evidence.
- Separate "what happened", "likely reasons", and "what would confirm it tomorrow".

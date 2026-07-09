---
name: market-morning-brief
description: Create a structured A-share pre-market brief from overnight and prior-day major events, global market moves, macro/policy news, industry catalysts, commodities, FX/rates, and company-level signals. Use when the user asks for 盘前简报, 早盘策略, 今日市场前瞻, 隔夜新闻汇总, 昨日大事件回顾, 开盘前需要关注什么, pre-market brief, morning market brief, or wants Codex to convert news into today's A-share market hypotheses, sector watchlist, risk points, and observation checklist.
---

# Market Morning Brief

## Purpose

Produce a disciplined A-share pre-market brief that turns overnight and prior-day events into testable hypotheses for today's market. Do not merely list news; explain likely transmission paths to index direction, style, sectors, sentiment, and risk appetite.

## Data Handling

Prefer free and public sources. Use [references/free-news-sources.md](references/free-news-sources.md) when choosing news, macro, global market, commodity, FX/rates, or announcement sources.

Use a clear time window, usually from the prior A-share close to today's pre-open. If the user gives no date, use the current trading morning and state the assumed time window.

Prioritize inputs in this order:

1. Global risk assets: US indexes, Nasdaq/semis, China ADRs, Hang Seng futures/ADR clues, Europe/Japan if relevant.
2. Rates, FX, and commodities: US yields, USD/CNH or USD/CNY, gold, crude oil, copper, lithium, iron ore.
3. Domestic macro and policy: State Council, ministries, PBOC, CSRC, exchanges, fiscal/industrial policy.
4. Overseas macro and geopolitics: Fed, CPI/jobs/PMI, tariffs/export controls, regional conflicts.
5. Industry catalysts: AI, semiconductors, robotics, new energy, pharma, consumer, property, brokers, defense, resources.
6. Major company signals: earnings, guidance, announcements, regulatory filings, only when they may affect an index, sector, or broad risk appetite.

When live news access is unavailable, ask the user to paste headlines or use the paste-in template in [references/morning-brief-framework.md](references/morning-brief-framework.md).

For the daily automated path, run `scripts/run_morning_brief.py --date YYYY-MM-DD`. It generates a conservative `brief.json` from delayed/free global index, FX/rate, and commodity clues, then starts targeted public web-evidence fallback when policy, industry, company, commodity, or impact-path fields are missing. Treat search evidence as context, not verified market prices.

## Workflow

1. Set the overnight environment.
   Classify the pre-market backdrop as risk-on, constructive, neutral, mixed, risk-off, or event-driven.

2. Identify market-moving events.
   Separate official/primary-source events from media interpretation, rumors, and low-impact noise.

3. Map events to A-share transmission paths.
   Explain how each event could affect indexes, style, sectors, liquidity, sentiment, and opening behavior.

4. Build today's hypotheses.
   Write hypotheses that can be tested intraday: "If X is true, observe Y by opening/first hour/close."

5. Create a sector watchlist.
   Group likely beneficiaries, pressure areas, and uncertainty zones. Avoid turning every headline into a tradable theme.

6. End with an observation checklist.
   Include opening strength, first-hour confirmation, turnover, RMB/HK market clues, leading sectors, and risk invalidation points.

## Output Shape

Use Chinese by default. Keep the default brief concise and skimmable.

Default Markdown sections:

1. `一句话总览`
2. `隔夜全球市场`
3. `宏观与政策`
4. `产业与主题催化`
5. `公司与财报线索`
6. `今日A股影响路径`
7. `重点观察清单`
8. `风险与反证`
9. `数据来源与置信度`

For browser viewing, screenshots, or repeated daily archives, use [assets/morning-brief-template.html](assets/morning-brief-template.html). Use `scripts/render_morning_brief.py <brief.json>` to render a fixed HTML brief.

Use [references/morning-brief-framework.md](references/morning-brief-framework.md) when a full workflow, paste-in template, or Markdown format is needed.
Use [references/free-news-sources.md](references/free-news-sources.md) when source choice, evidence quality, or free data limitations matter.
Use [references/platform-integration.md](references/platform-integration.md) when adapting this skill to OpenClaw, Hermens, or another non-Codex agent runtime.
Use `scripts/run_morning_brief.py --date YYYY-MM-DD` when the user wants the normal automated pre-market brief with fallback channels.
Use `scripts/collect_morning_brief_sources.py --date YYYY-MM-DD` when the user wants only a quick public-market-data seed before writing the brief.

## Guardrails

- Do not fabricate headlines, prices, or official statements.
- Do not treat media summaries as primary evidence when official sources are available.
- Do not overstate a causal path. Use "可能影响", "更需要观察", or "若市场认可" when evidence is indirect.
- Do not give personalized investment advice.
- Separate "event", "possible market impact", and "what would confirm it today".

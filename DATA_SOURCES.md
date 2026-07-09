# Data Sources

This file defines the data sources that the current automated reports may use. Keep this list stricter than the broader reference docs: a source belongs here only if the code actually calls it or treats it as an explicit fallback.

## Source Policy

- A report may only present a data field when the source call succeeded and the field exists in the JSON snapshot.
- Failed sources must be recorded under `errors`; they must not be listed as successful `sources`.
- Public/free endpoints are allowed, but their data must be labeled as public, delayed, or approximate when applicable.
- Web-search evidence is not market data. It can support narrative context, but not exact index, breadth, turnover, or price figures unless the linked source directly provides them.
- Official and primary sources are preferred for policy, announcements, and company-specific claims. They are not yet part of the automated collectors.

## Current Automated Sources

### Morning Brief

| Source | Code path | Fields | Status | Notes |
| --- | --- | --- | --- | --- |
| Yahoo Finance public chart endpoint (`query1` then `query2`) | `market-morning-brief/scripts/collect_morning_brief_sources.py` | US indexes, semiconductors, Hang Seng, KWEB, USD/CNH, US 10Y yield, gold, silver, crude oil, copper | Active | Public chart data; treat as delayed context. Use direction and magnitude, not official settlement. |
| DuckDuckGo HTML public search | `market-morning-brief/scripts/run_morning_brief.py` via `market-close-summary/scripts/collect_web_research_fallback.py` | Missing policy, industry, company, global, FX/rate, and commodity evidence snippets | Fallback evidence | Search evidence is context, not verified price data. It is merged into narrative fields only after the structured quote gate finds gaps. |

Current symbols:

| Symbol | Name | Use |
| --- | --- | --- |
| `^GSPC` | S&P 500 | Global risk appetite |
| `^IXIC` | Nasdaq | Growth/technology clue |
| `^DJI` | Dow Jones | US broad-market clue |
| `^SOX` | Philadelphia Semiconductor Index | Semiconductor/AI hardware clue |
| `^HSI` | Hang Seng Index | HK/China risk clue |
| `KWEB` | China internet ETF | China ADR/platform-economy clue |
| `CNH=X` | USD/CNH | RMB clue |
| `^TNX` | US 10Y yield | Rate clue |
| `GC=F` | COMEX gold | Precious metals clue |
| `SI=F` | COMEX silver | Precious metals clue |
| `CL=F` | WTI crude oil | Energy/commodity clue |
| `HG=F` | COMEX copper | Copper/industrial metals clue |

### Market Close Summary

| Source | Code path | Fields | Status | Notes |
| --- | --- | --- | --- | --- |
| Tencent `qt.gtimg.cn` | `collect_tencent_indexes` | Major A-share index levels and changes | Active fallback | Worked in the latest source audit. Index-only; not suitable for breadth or sectors. |
| Yahoo Finance public chart endpoint (`query1` then `query2`) | `collect_yahoo_metal_futures` | COMEX gold, silver, and copper futures direction | Active commodity source | Public delayed futures data. This is the primary automated source for the close report's metals module. |
| AkShare `stock_zh_a_spot` / `stock_zh_a_spot_em` | `collect_akshare_a_stock_breadth` | A-share breadth and approximate turnover aggregation | Active primary | Use `is_partial`, `sample_size`, and source notes. Approximate turnover should be treated as vendor-derived. |
| AkShare/THS `stock_board_industry_summary_ths` | `collect_akshare_ths_industry_summary` | Industry leading/lagging, industry breadth, metals sectors | Active primary | Good for structure and sector direction. Vendor taxonomy, not official classification. |
| AkShare/THS `stock_board_concept_summary_ths` | `collect_akshare_ths_concept_summary` | Concept/event clues, metal-related themes | Active context source | This is partly an event/concept summary, not always a涨幅 ranking. Use as theme clue, not proof of theme strength by itself. |
| AkShare/Eastmoney `stock_zt_pool_em` | `collect_akshare` | Limit-up count | Active | Clarify vendor/ST inclusion if precision matters. |
| AkShare/Eastmoney `stock_zt_pool_dtgc_em` | `collect_akshare` | Limit-down count | Active | Clarify vendor/ST inclusion if precision matters. |
| Sina `hq.sinajs.cn` | `collect_sina_indexes` | Major A-share index fallback | Standby fallback | Index-only. Not enough for a full close report. |
| Eastmoney direct `push2.eastmoney.com` | `eastmoney_clist` callers | Indexes, breadth, sectors, concepts | Unreliable in current environment | Latest no-AkShare audit failed for breadth, industry, and concept endpoints. Keep as opportunistic fallback only; do not rely on it for guaranteed reports. |

## Not Yet Automated

These are valid research sources, but the current code does not automatically collect them:

- SSE, SZSE, BSE, CSI official sites.
- CNINFO and exchange/company announcements.
- CSRC, PBOC, NDRC, MOF, MIIT and other official policy sites.
- HKEX-derived market-connect data.
- Tushare free tier.
- Eastmoney/Sina/Tencent/Yicai/Securities Times news pages.

Use them manually or through a future collector. Do not imply they were used unless a script or agent actually fetched them and recorded the source.

## Report Usability Gates

A close report is considered structurally usable only when these fields are present:

- `indexes`
- `turnover.amount_cny`
- `breadth.rising` and `breadth.falling`
- `limit_stats.limit_up_count` and `limit_stats.limit_down_count`
- at least one of `sectors.leading` or `sectors.lagging`
- `metals.futures` must include usable gold, silver, and copper futures quotes (`GC=F`, `SI=F`, `HG=F`) with price, previous close, and change percentage; A-share metal sectors/themes are mapping evidence, not the primary metals data

A morning brief is considered structurally usable only when these fields are present:

- at least three `raw_quotes`
- at least one global equity clue
- at least one FX/rate clue
- at least one commodity clue
- gold, silver, and copper futures quotes (`GC=F`, `SI=F`, `HG=F`) must each have usable price, previous close, and change percentage
- `impact_paths`
- non-placeholder policy, industry, and company/event evidence when the brief is used as an active information push

If a report does not meet these gates, render it as partial/source-diagnostic output instead of a normal daily report.

`market-close-summary/scripts/run_close_review.py` enforces this policy operationally: it runs the structured collector first, checks the close-report gate, and when required fields are missing it launches `collect_web_research_fallback.py` with targeted queries, creates an LLM context package, and renders the report with explicit source-gap notes.

`market-morning-brief/scripts/run_morning_brief.py` applies the same pattern to pre-market output: it runs the quote collector first, checks the morning gate, launches targeted web-evidence queries when fields are placeholders or missing, merges evidence snippets into the brief JSON, and renders the report with data-quality notes.

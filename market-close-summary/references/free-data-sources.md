# Free Data Sources for A-share Close Reviews

Use free and public sources first. Treat free data as convenient but fallible: interfaces may change, pages may throttle, and fields may differ across vendors. Prefer cross-checking the few numbers that anchor the conclusion.

## Source Priority

1. **AkShare**
   Use as the first automation layer when Python dependencies are available. It wraps many public Chinese market endpoints and is usually the fastest path for indexes, spot quotes, sectors, concepts, limit-up pools, fund flows, macro series, and news-like datasets. Prefer non-Eastmoney AkShare routes, such as 同花顺 industry summary, when Eastmoney-backed endpoints are blocked.

2. **Official exchange and index sites**
   Use for authoritative confirmation when precision matters:
   - Shanghai Stock Exchange: market statistics, listings, announcements.
   - Shenzhen Stock Exchange: market statistics, listings, announcements.
   - Beijing Stock Exchange: BSE market data and announcements.
   - China Securities Index: CSI index levels, constituents, index methodology.
   - CNINFO: listed-company announcements.

3. **Eastmoney public pages/endpoints**
   Use for broad market dashboards: A-share spot lists, industry/concept rankings, turnover,涨跌家数,涨停跌停 pools, capital-flow clues, ETF and sector pages. Good for close review structure, but verify important values when possible.

4. **Sina/Tencent/NetEase quote endpoints**
   Use as lightweight fallbacks for real-time or delayed quotes and index snapshots. Good for simple index or individual-stock checks; less suitable as the only source for breadth and theme analysis.

5. **Tushare free tier**
   Use when the user already has a token or accepts free-tier limits. Good for structured historical data, calendars, basic daily bars, and some reference datasets. Do not assume paid points or premium access.

6. **Public news and policy sources**
   Use official and primary sources before media summaries:
   - CSRC, PBOC, NDRC, MOF, MIIT and other ministry sites.
   - Exchange announcements and CNINFO.
   - Company announcements before secondary commentary.

7. **Web-search fallback**
   Use when structured sources fail, throttle, or omit the fields needed for a useful review. Follow [web-research-fallback.md](web-research-fallback.md): search date-qualified public pages, extract an evidence note, and let the LLM organize narrative and tomorrow's checklist while clearly marking missing numeric facts.

## Data Map

| Need | Preferred Free Sources | Notes |
| --- | --- | --- |
| Major index close and change | AkShare, Eastmoney, Sina/Tencent, CSI official | Cross-check if the index level affects the conclusion. |
| Total turnover | AkShare, Eastmoney, exchange statistics | Align whether the figure is Shanghai+Shenzhen only or includes Beijing. |
| Rising/falling stocks | Eastmoney, AkShare | Check whether suspended stocks and BSE names are included. |
| Limit-up/limit-down count | AkShare, Eastmoney | Clarify whether ST stocks are included. |
| Industry performance | AkShare 同花顺 summary, Eastmoney industry boards via AkShare or pages | Industry taxonomy differs by vendor. Do not compare ranks across taxonomies casually. |
| Concept/theme performance | Eastmoney concept boards, AkShare 同花顺 concept summary | Treat as vendor-defined concepts, useful for market narrative but not official classification. Some THS concept summaries are event lists rather than涨跌幅 rankings. |
| Fund-flow clues | Eastmoney, AkShare | Use directionally; avoid overclaiming exact causal power. |
| Northbound flow | Exchange/HKEX-derived public data, AkShare if available | Availability can vary due market-connect disclosure changes. Mark missing data clearly. |
| Announcements | CNINFO, SSE, SZSE, BSE | Prefer primary announcement text for company-specific claims. |
| Macro/policy catalysts | Official ministry/central bank/regulator sites | Use media only as a pointer to primary sources. |
| Narrative/catalyst fallback | Official pages, CNINFO, exchange announcements, 财联社/证券时报/东方财富/同花顺 public收评 | Use for attribution and language synthesis when numeric data is incomplete; mark as search-derived. |

## Automation Guidance

For the first automated version, build a thin collector instead of a heavy data platform:

1. Fetch today's market snapshot from AkShare where possible, including major indexes and A-share spot rows for breadth and turnover aggregation.
2. Fetch or confirm index data from Tencent/Sina lightweight quote endpoints, Eastmoney, or official pages when AkShare is unavailable or returns incomplete data.
3. Fetch top industry and concept boards from multiple routes: AkShare/Eastmoney first, AkShare/同花顺 summary as fallback.
4. Fetch limit-up/limit-down and breadth indicators.
5. Save raw data with date, source, and retrieval time.
6. Pass a compact normalized summary into the close-review skill.
7. If the normalized summary is incomplete, run the web-search fallback and create an `analysis.json` with `data_mode`, `sources`, `source_note`, catalysts, risks, and tomorrow observations.

Use a cache file per trading day so repeated reviews do not hammer public endpoints. If a request fails, degrade gracefully and ask the user to paste the missing fields.

## Reliability Rules

- Do not fabricate missing fields.
- Do not mix live, delayed, and historical values without saying so.
- Do not infer market-wide breadth from a partial stock universe.
- Do not treat vendor concept rankings as official industry classification.
- Do not overstate fund-flow precision; use it as corroborating evidence.
- When two free sources disagree on a key figure, show the disagreement or use the official source if available.

## Included Collector

Use `scripts/collect_a_share_close.py` to normalize free-source data into this schema:

```json
{
  "date": "YYYY-MM-DD",
  "retrieved_at": "YYYY-MM-DD HH:mm:ss",
  "sources": ["AkShare", "Eastmoney"],
  "indexes": [],
  "turnover": {},
  "breadth": {},
  "limit_stats": {},
  "sectors": {
    "leading": [],
    "lagging": []
  },
  "themes": {
    "active": [],
    "weak": []
  },
  "flows": {},
  "intraday_notes": [],
  "catalysts": []
}
```

Keep the collector small and replaceable. Free endpoints change; the durable asset is the normalized schema and review workflow, not any single scraping method.

Example:

```bash
python market-close-summary/scripts/collect_a_share_close.py --date 2026-07-08
```

The script defaults to `data/a-share-close-YYYY-MM-DD.json`, tries optional AkShare first, then uses Tencent/Sina for lightweight major-index fallback, then uses Eastmoney public endpoints for major indexes, approximate breadth, turnover aggregation, industry boards, and concept boards. AkShare attempts major index quotes with `stock_zh_index_spot_em`, full A-share spot aggregation with `stock_zh_a_spot_em`, 同花顺 industry summary with `stock_board_industry_summary_ths`, and 同花顺 concept/event summary with `stock_board_concept_summary_ths`. Tencent `qt.gtimg.cn` and Sina `hq.sinajs.cn` can still provide the major-index baseline when Eastmoney-backed interfaces are blocked or throttled. A temporary Eastmoney paging failure should not automatically make the report "数据不足". Eastmoney board data fills missing AkShare/THS fields instead of overwriting them. Breadth and aggregated turnover include `is_partial`, `returned_count`, and `total_universe_count` metadata; avoid treating partial output as whole-market fact. Public endpoints can close connections or throttle; use `--retries` and `--page-delay` before treating a fetch failure as a data-source outage.

Cache cleanup is opt-in. By default, daily JSON snapshots accumulate, but same-date runs overwrite the same file. Use these options when disk usage matters:

```bash
python market-close-summary/scripts/collect_a_share_close.py --retention-days 365
python market-close-summary/scripts/collect_a_share_close.py --max-cache-files 250
python market-close-summary/scripts/collect_a_share_close.py --cleanup-only --dry-run-cleanup --retention-days 365
```

Cleanup only matches files named `a-share-close-YYYY-MM-DD.json` in the output directory, leaving other files alone.
If a cleanup policy deletes the file just collected, the script reports the cleanup summary and does not recreate that file.

## When Data Is Missing

Do not stop at "数据不足" if the runtime has browsing/search access. Use this order:

1. Re-run the collector with `--retries` increased and a modest `--page-delay`.
2. Use lightweight quote pages for major indexes and public board pages for sector/theme direction.
3. Search public收评 and official announcements for catalysts and market narrative.
4. Render the review as `搜索补足` with explicit source names and missing fields.

Only ask the user to paste data when exact verified figures are required and cannot be obtained from accessible public sources.

Use `scripts/collect_web_research_fallback.py --date YYYY-MM-DD` to collect a first-pass public-search evidence bundle when the agent runtime does not provide a stronger native search tool.

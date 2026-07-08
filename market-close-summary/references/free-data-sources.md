# Free Data Sources for A-share Close Reviews

Use free and public sources first. Treat free data as convenient but fallible: interfaces may change, pages may throttle, and fields may differ across vendors. Prefer cross-checking the few numbers that anchor the conclusion.

## Source Priority

1. **AkShare**
   Use as the first automation layer when Python dependencies are available. It wraps many public Chinese market endpoints and is usually the fastest path for indexes, spot quotes, sectors, concepts, limit-up pools, fund flows, macro series, and news-like datasets.

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

## Data Map

| Need | Preferred Free Sources | Notes |
| --- | --- | --- |
| Major index close and change | AkShare, Eastmoney, Sina/Tencent, CSI official | Cross-check if the index level affects the conclusion. |
| Total turnover | AkShare, Eastmoney, exchange statistics | Align whether the figure is Shanghai+Shenzhen only or includes Beijing. |
| Rising/falling stocks | Eastmoney, AkShare | Check whether suspended stocks and BSE names are included. |
| Limit-up/limit-down count | AkShare, Eastmoney | Clarify whether ST stocks are included. |
| Industry performance | Eastmoney industry boards via AkShare or pages | Industry taxonomy differs by vendor. Do not compare ranks across taxonomies casually. |
| Concept/theme performance | Eastmoney concept boards via AkShare or pages | Treat as vendor-defined concepts, useful for market narrative but not official classification. |
| Fund-flow clues | Eastmoney, AkShare | Use directionally; avoid overclaiming exact causal power. |
| Northbound flow | Exchange/HKEX-derived public data, AkShare if available | Availability can vary due market-connect disclosure changes. Mark missing data clearly. |
| Announcements | CNINFO, SSE, SZSE, BSE | Prefer primary announcement text for company-specific claims. |
| Macro/policy catalysts | Official ministry/central bank/regulator sites | Use media only as a pointer to primary sources. |

## Automation Guidance

For the first automated version, build a thin collector instead of a heavy data platform:

1. Fetch today's market snapshot from AkShare where possible.
2. Fetch or confirm index and turnover data from Eastmoney or official pages.
3. Fetch top industry and concept boards.
4. Fetch limit-up/limit-down and breadth indicators.
5. Save raw data with date, source, and retrieval time.
6. Pass a compact normalized summary into the close-review skill.

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

The script defaults to `data/a-share-close-YYYY-MM-DD.json`, tries optional AkShare first, then uses Eastmoney public endpoints for major indexes, approximate breadth, turnover aggregation, industry boards, and concept boards. Eastmoney board data fills missing AkShare fields instead of overwriting them. Breadth and aggregated turnover include `is_partial`, `returned_count`, and `total_universe_count` metadata; avoid treating partial output as whole-market fact. Public endpoints can close connections or throttle; use `--retries` and `--page-delay` before treating a fetch failure as a data-source outage.

Cache cleanup is opt-in. By default, daily JSON snapshots accumulate, but same-date runs overwrite the same file. Use these options when disk usage matters:

```bash
python market-close-summary/scripts/collect_a_share_close.py --retention-days 365
python market-close-summary/scripts/collect_a_share_close.py --max-cache-files 250
python market-close-summary/scripts/collect_a_share_close.py --cleanup-only --dry-run-cleanup --retention-days 365
```

Cleanup only matches files named `a-share-close-YYYY-MM-DD.json` in the output directory, leaving other files alone.
If a cleanup policy deletes the file just collected, the script reports the cleanup summary and does not recreate that file.

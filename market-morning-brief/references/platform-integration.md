# Platform Integration

Use this reference when adapting `market-morning-brief` to OpenClaw, Hermens, or another non-Codex agent runtime.

## Portable Contract

This skill is a filesystem bundle. A compatible agent only needs to:

1. Read `SKILL.md` as the primary instruction file.
2. Load `references/` files only when needed.
3. Optionally collect a public-market-data seed through `scripts/collect_morning_brief_sources.py`.
4. Optionally render JSON briefs through `scripts/render_morning_brief.py`.
5. Use `assets/morning-brief-template.html` as a static presentation template.

`agents/openai.yaml` is OpenAI/Codex UI metadata. Other runtimes can ignore it safely.

## Minimal Runtime Assumptions

- Python 3.10+.
- Standard library is enough for public-market seed collection and HTML rendering.
- Network access is required for live free-source collection. Rendering an existing JSON brief is offline.

## Entry Points

Collect a first-pass public-market-data seed:

```bash
python market-morning-brief/scripts/collect_morning_brief_sources.py --date YYYY-MM-DD
```

Render a fixed HTML report:

```bash
python market-morning-brief/scripts/render_morning_brief.py data/morning-brief-YYYY-MM-DD.json
```

## Data Flow

```text
free/public news and market sources
  -> scripts/collect_morning_brief_sources.py
  -> data/morning-brief-YYYY-MM-DD.json
  -> optional agent source gathering for policy/news/announcements
  -> event triage using SKILL.md + references/
  -> brief.json
  -> scripts/render_morning_brief.py
  -> reports/morning-brief-YYYY-MM-DD.html
```

## Brief JSON Contract

```json
{
  "date": "YYYY-MM-DD",
  "time_window": "上一交易日收盘后至今日开盘前",
  "retrieved_at": "YYYY-MM-DD HH:mm:ss",
  "sources": ["source name"],
  "overall_tone": "risk-on/constructive/neutral/mixed/risk-off/event-driven",
  "one_sentence_overview": "一句话总览",
  "global_markets": ["event"],
  "macro_policy": ["event"],
  "industry_catalysts": ["event"],
  "company_signals": ["event"],
  "impact_paths": [
    {
      "event": "事件",
      "impact": "可能影响",
      "areas": "受影响方向",
      "confirmation": "今日确认点"
    }
  ],
  "watchlist": ["观察点"],
  "risks": ["风险与反证"],
  "data_quality": ["来源与置信度说明"],
  "raw_quotes": [
    {
      "symbol": "^IXIC",
      "name": "纳斯达克",
      "price": 0,
      "previous": 0,
      "pct": 0
    }
  ]
}
```

Fields may be missing. The renderer fills missing fields conservatively. `raw_quotes` is optional diagnostic data from `collect_morning_brief_sources.py`; agents can keep it in archives but should not print it in the brief unless the user asks for source diagnostics.

## Generated Outputs

Generated outputs are intentionally ignored by git:

- `data/`: daily seed JSON files.
- `reports/`: rendered HTML reports.
- `__pycache__/` and `*.pyc`: Python runtime cache.

## Portability Notes

- Do not require a hosted service, database, browser automation, or paid market data terminal.
- Treat public chart data as delayed context, not verified official market data.
- Keep generated reports deterministic and self-contained so any agent can archive, preview, or publish them.
- If a target runtime has its own manifest format, map its trigger description to the `description` field in `SKILL.md` and map commands to the script entry points above.

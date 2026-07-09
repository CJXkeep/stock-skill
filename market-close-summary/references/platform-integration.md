# Platform Integration

Use this reference when adapting `market-close-summary` to a non-Codex agent runtime such as OpenClaw, Hermens, or another local agent system.

## Portable Contract

This skill is a filesystem bundle. A compatible agent only needs to:

1. Read `SKILL.md` as the primary instruction file.
2. Load referenced files in `references/` only when needed.
3. Execute Python scripts in `scripts/` when data collection or HTML rendering is requested.
4. Treat `assets/close-report-template.html` as a static presentation template.
5. Expose browsing/search when possible so the skill can use [web-research-fallback.md](web-research-fallback.md) after public API failures.

`agents/openai.yaml` is OpenAI/Codex UI metadata. Other agent runtimes can ignore it safely.

## Minimal Runtime Assumptions

- Python 3.10+.
- Standard library is enough for HTML rendering and Eastmoney public endpoint collection.
- `akshare` is optional. If unavailable or partially failing, the collector degrades and records errors in JSON.
- Network access is needed for live free-source collection and optional web-search fallback. Rendering an existing JSON snapshot is offline.

## Entry Points

Collect a daily snapshot:

```bash
python market-close-summary/scripts/collect_a_share_close.py --date YYYY-MM-DD
```

Collect public web-search fallback evidence:

```bash
python market-close-summary/scripts/collect_web_research_fallback.py --date YYYY-MM-DD
python market-close-summary/scripts/collect_web_research_fallback.py --date YYYY-MM-DD --analysis-output data/a-share-close-web-analysis-YYYY-MM-DD.json
```

Prepare an LLM synthesis context:

```bash
python market-close-summary/scripts/prepare_llm_analysis_context.py --snapshot data/a-share-close-YYYY-MM-DD.json --web-evidence data/a-share-close-web-YYYY-MM-DD.json
```

Render a fixed HTML report:

```bash
python market-close-summary/scripts/render_close_report.py data/a-share-close-YYYY-MM-DD.json
```

Render with model-written analysis overrides:

```bash
python market-close-summary/scripts/render_close_report.py data/a-share-close-YYYY-MM-DD.json --analysis analysis.json
```

## Data Flow

```text
free/public data sources
  -> scripts/collect_a_share_close.py
  -> data/a-share-close-YYYY-MM-DD.json
  -> optional web research fallback
  -> scripts/collect_web_research_fallback.py
  -> data/a-share-close-web-YYYY-MM-DD.json
  -> scripts/prepare_llm_analysis_context.py
  -> data/a-share-close-llm-context-YYYY-MM-DD.md
  -> agent analysis using SKILL.md + references/
  -> optional analysis.json
  -> scripts/render_close_report.py
  -> reports/a-share-close-YYYY-MM-DD.html
```

## Analysis JSON Contract

Agents that want to produce richer HTML reports should emit this optional JSON:

```json
{
  "data_mode": "结构化数据/搜索补足/数据不足",
  "sources": ["AkShare", "Eastmoney", "财联社收评"],
  "source_note": "来源与缺口说明",
  "market_temperature": "偏弱防守",
  "one_sentence_conclusion": "一句话结论",
  "market_structure": "市场结构判断",
  "theme_commentary": "主线与轮动判断",
  "main_line_strength": "弱/中/强/待确认",
  "main_line_note": "主线强度说明",
  "catalysts": ["异动归因1", "异动归因2"],
  "risks": ["风险信号1", "风险信号2"],
  "tomorrow_observations": ["明日观察1", "明日观察2"]
}
```

All fields are optional. Missing fields are filled conservatively from the snapshot.

## Generated Outputs

Generated outputs are intentionally ignored by git:

- `data/`: daily snapshot JSON files.
- `reports/`: rendered HTML reports.
- `__pycache__/` and `*.pyc`: Python runtime cache.

## Portability Notes

- Do not assume a platform-specific skill manifest beyond `SKILL.md`.
- Do not require a hosted service, database, browser automation, or paid market data terminal.
- Keep generated reports deterministic and self-contained so any agent can archive, preview, or publish them.
- If a target runtime has its own manifest format, map its trigger description to the `description` field in `SKILL.md` and map commands to the script entry points above.

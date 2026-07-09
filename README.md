# stock-skill

Reusable agent skills for stock-market research, review, and decision support. The folders are designed to stay portable: Codex can use them directly, and other agent runtimes such as OpenClaw or Hermens can read the same Markdown instructions and run the same Python scripts.

## Skills

- `market-close-summary`: Generate a structured A-share market close review with market temperature, structure, main themes, risks, and tomorrow's observation checklist.
  - Free data source guidance is included for AkShare, official exchange/index sites, Eastmoney, lightweight quote endpoints, and Tushare free-tier workflows.
  - Includes a web-research fallback for missing data: search public pages, extract evidence, and let the LLM organize the narrative without fabricating figures.
  - Includes `scripts/collect_a_share_close.py` for a first-pass free-source JSON snapshot.
  - Includes `scripts/collect_web_research_fallback.py` for a public-search evidence bundle when structured sources are incomplete.
  - Includes `scripts/prepare_llm_analysis_context.py` for turning snapshot/search evidence into a strict LLM synthesis context.
  - Includes `scripts/run_close_review.py` as the preferred daily entry point with automatic source-gap fallback.
  - Includes `scripts/render_close_report.py` for rendering snapshot JSON into a fixed HTML report.
  - Cache cleanup is opt-in via `--retention-days`, `--max-cache-files`, and `--cleanup-only`.
  - Includes a Binance-inspired fixed HTML report template at `assets/close-report-template.html`.
  - Includes `references/platform-integration.md` for non-Codex agent integration.

- `market-morning-brief`: Generate a structured A-share pre-market brief from overnight and prior-day major events.
  - Converts news into today's market hypotheses, sector watchlist, risk points, and confirmation/invalidation checks.
  - Includes free source guidance for official policy, macro, global market, commodity, FX/rates, announcements, and media sources.
  - Includes `scripts/collect_morning_brief_sources.py` for a first-pass public-market-data JSON seed.
  - Includes `scripts/run_morning_brief.py` as the preferred daily entry point with automatic web-evidence fallback.
  - Includes `scripts/render_morning_brief.py` for rendering a brief JSON into a fixed HTML report.
  - Includes a fixed HTML report template at `assets/morning-brief-template.html`.
  - Includes `references/platform-integration.md` for non-Codex agent integration.

## Usage

For Codex, copy a skill folder into your Codex skills directory, or keep this repository as the source of truth and sync selected skills into your local setup.

For other agents, load `SKILL.md` as the primary instruction file, follow links in `references/` as needed, and expose the scripts in `scripts/` as callable local tools.

## Quickstart

Generate and render a close review snapshot:

```bash
python market-close-summary/scripts/collect_a_share_close.py --date YYYY-MM-DD
python market-close-summary/scripts/render_close_report.py data/a-share-close-YYYY-MM-DD.json
```

Run the close review with automatic fallback channels:

```bash
python market-close-summary/scripts/run_close_review.py --date YYYY-MM-DD
```

Generate and render a morning brief seed:

```bash
python market-morning-brief/scripts/run_morning_brief.py --date YYYY-MM-DD
```

Generated daily JSON and HTML files are written under `data/` and `reports/`, which are ignored by git.

Tracked sample inputs live under `examples/` so release smoke tests do not depend on local generated files.

Current automated data-source rules are documented in [DATA_SOURCES.md](DATA_SOURCES.md).

Before publishing or syncing a skill folder, run the checks in [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md).

For the shortest local verification path, run:

```bash
python scripts/smoke_test.py
```

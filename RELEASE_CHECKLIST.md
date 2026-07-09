# Release Checklist

Use this checklist before publishing or syncing a skill folder into an agent runtime.

## Repository Checks

- Confirm generated files stay out of git:
  - `data/`
  - `reports/`
  - `__pycache__/`
  - `*.pyc`
- Confirm each skill folder contains:
  - `SKILL.md`
  - `agents/openai.yaml`
  - `references/`
  - `scripts/`
  - `assets/` when HTML rendering is supported
- Confirm `README.md` lists every public script entry point.

## Smoke Tests

Run the one-command smoke test:

```bash
python scripts/smoke_test.py
```

Or run the checks manually.

Run Python syntax checks:

```bash
python -m py_compile market-close-summary/scripts/collect_a_share_close.py market-close-summary/scripts/collect_web_research_fallback.py market-close-summary/scripts/prepare_llm_analysis_context.py market-close-summary/scripts/render_close_report.py market-morning-brief/scripts/collect_morning_brief_sources.py market-morning-brief/scripts/render_morning_brief.py
```

Render the included close-review sample:

```bash
python market-close-summary/scripts/render_close_report.py examples/close-sample.json --output reports/release-check-close.html
```

Render the included morning-brief sample:

```bash
python market-morning-brief/scripts/render_morning_brief.py examples/morning-sample.json --output reports/release-check-morning.html
```

Optionally run live free-source collection:

```bash
python market-close-summary/scripts/collect_a_share_close.py --date YYYY-MM-DD --output data/release-check-close.json
python market-morning-brief/scripts/collect_morning_brief_sources.py --date YYYY-MM-DD --output data/release-check-morning.json
```

## Skill-Specific Checks

For `market-close-summary`:

- Verify `scripts/collect_a_share_close.py --help` documents data collection, retries, and cache cleanup.
- Verify `scripts/collect_web_research_fallback.py --help` documents search fallback options.
- Verify `scripts/prepare_llm_analysis_context.py --help` documents snapshot and web-evidence inputs.
- Verify rendered HTML does not imply missing web-search or free-source data is fully verified.

For `market-morning-brief`:

- Verify `scripts/collect_morning_brief_sources.py --help` documents the seed JSON workflow.
- Verify `scripts/render_morning_brief.py --help` documents template, output, and date overrides.
- Verify `overall_tone` values match the contract in `references/platform-integration.md`.
- Verify `raw_quotes` stays diagnostic and is not shown in the default report.

## Data And Source Notes

- Do not present free public endpoints as official market data.
- Keep AkShare optional; the close collector must degrade when it is missing.
- Treat Yahoo Finance public chart data as delayed context for the morning brief.
- Mark search-derived close reviews as `搜索补足` or `数据不足` when exact figures are missing.
- Prefer official policy, exchange, and company sources before media summaries.

## Publish Notes

- A release can be a full repository sync or a single skill-folder sync.
- For Codex, copy the target skill folder into the local skills directory.
- For other runtimes, load `SKILL.md`, expose `scripts/`, and keep `assets/` paths intact.
- Generated `data/` and `reports/` files are archive artifacts, not source files.

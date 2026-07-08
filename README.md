# stock-skill

Reusable agent skills for stock-market research, review, and decision support. The folders are designed to stay portable: Codex can use them directly, and other agent runtimes such as OpenClaw or Hermens can read the same Markdown instructions and run the same Python scripts.

## Skills

- `market-close-summary`: Generate a structured A-share market close review with market temperature, structure, main themes, risks, and tomorrow's observation checklist.
  - Free data source guidance is included for AkShare, official exchange/index sites, Eastmoney, lightweight quote endpoints, and Tushare free-tier workflows.
  - Includes `scripts/collect_a_share_close.py` for a first-pass free-source JSON snapshot.
  - Includes `scripts/render_close_report.py` for rendering snapshot JSON into a fixed HTML report.
  - Cache cleanup is opt-in via `--retention-days`, `--max-cache-files`, and `--cleanup-only`.
  - Includes a fixed HTML report template at `assets/close-report-template.html`.
  - Includes `references/platform-integration.md` for non-Codex agent integration.

## Usage

For Codex, copy a skill folder into your Codex skills directory, or keep this repository as the source of truth and sync selected skills into your local setup.

For other agents, load `SKILL.md` as the primary instruction file, follow links in `references/` as needed, and expose the scripts in `scripts/` as callable local tools.

#!/usr/bin/env python3
"""Run release smoke tests for the stock-skill repository."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

PYTHON_SCRIPTS = [
    "market-close-summary/scripts/collect_a_share_close.py",
    "market-close-summary/scripts/collect_web_research_fallback.py",
    "market-close-summary/scripts/prepare_llm_analysis_context.py",
    "market-close-summary/scripts/run_close_review.py",
    "market-close-summary/scripts/render_close_report.py",
    "market-morning-brief/scripts/collect_morning_brief_sources.py",
    "market-morning-brief/scripts/run_morning_brief.py",
    "market-morning-brief/scripts/render_morning_brief.py",
]


def run(args: list[str]) -> None:
    print("+ " + " ".join(args), flush=True)
    subprocess.run(args, cwd=ROOT, check=True)


def main() -> int:
    run([sys.executable, "-m", "py_compile", *PYTHON_SCRIPTS])
    run(
        [
            sys.executable,
            "market-close-summary/scripts/render_close_report.py",
            "examples/close-sample.json",
            "--output",
            "reports/smoke-close.html",
        ]
    )
    run(
        [
            sys.executable,
            "market-morning-brief/scripts/render_morning_brief.py",
            "examples/morning-sample.json",
            "--output",
            "reports/smoke-morning.html",
        ]
    )
    print("Smoke tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

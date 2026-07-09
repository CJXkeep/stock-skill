#!/usr/bin/env python3
"""Run the close-review pipeline with automatic fallback channels."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent
REQUIRED_METAL_FUTURES = {
    "GC=F": "COMEX黄金",
    "SI=F": "COMEX白银",
    "HG=F": "COMEX铜",
}


def today() -> str:
    return dt.date.today().isoformat()


def validate_date(value: str) -> str:
    try:
        return dt.date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise argparse.ArgumentTypeError("date must use YYYY-MM-DD format") from exc


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def resolved(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def run(args: list[str]) -> None:
    print("+ " + " ".join(args), flush=True)
    subprocess.run(args, cwd=ROOT, check=True)


def missing_close_fields(snapshot: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    if not snapshot.get("indexes"):
        missing.append("indexes")
    turnover = snapshot.get("turnover") or {}
    if turnover.get("amount_cny") in (None, ""):
        missing.append("turnover.amount_cny")
    elif turnover.get("is_partial"):
        missing.append("turnover.amount_cny.partial")
    breadth = snapshot.get("breadth") or {}
    if breadth.get("rising") in (None, "") or breadth.get("falling") in (None, ""):
        missing.append("breadth.rising/falling")
    elif breadth.get("is_partial"):
        missing.append("breadth.rising/falling.partial")
    limits = snapshot.get("limit_stats") or {}
    if limits.get("limit_up_count") in (None, "") or limits.get("limit_down_count") in (None, ""):
        missing.append("limit_stats.limit_up/down")
    sectors = snapshot.get("sectors") or {}
    if not sectors.get("leading") and not sectors.get("lagging"):
        missing.append("sectors.leading/lagging")
    missing.extend(missing_metal_futures(snapshot))
    return missing


def missing_metal_futures(snapshot: dict[str, Any]) -> list[str]:
    metals = snapshot.get("metals") or {}
    rows = [item for item in metals.get("futures") or [] if isinstance(item, dict)]
    by_symbol = {str(item.get("symbol") or ""): item for item in rows}
    missing = []
    for symbol in REQUIRED_METAL_FUTURES:
        item = by_symbol.get(symbol)
        if not item:
            missing.append(f"metals.futures.{symbol}")
            continue
        if not all(number_like(item.get(key)) for key in ["price", "previous", "change_pct"]):
            missing.append(f"metals.futures.{symbol}.price/previous/change_pct")
    return missing


def number_like(value: Any) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(number)


def fallback_queries(date: str, missing: list[str]) -> list[str]:
    parsed = dt.date.fromisoformat(date)
    full = f"{parsed.year}年{parsed.month}月{parsed.day}日"
    queries = []
    if any(item.startswith("turnover") or item.startswith("breadth") for item in missing):
        queries.append(f"{full} 沪深两市 成交额 上涨家数 下跌家数")
        queries.append(f"{full} A股 涨跌家数 成交额 东方财富")
    if any(item.startswith("limit_stats") for item in missing):
        queries.append(f"{full} A股 涨停 跌停 家数")
    if any(item.startswith("sectors") for item in missing):
        queries.append(f"{full} A股 行业板块 涨幅 跌幅")
        queries.append(f"{full} 有色金属 贵金属 铜 A股 板块 表现")
    if any(item.startswith("metals") for item in missing):
        queries.append(f"{full} COMEX 黄金 白银 铜 期货 收盘 涨跌幅")
        queries.append(f"{full} 金银铜 期货 外盘 行情 黄金 白银 铜")
    if "indexes" in missing:
        queries.append(f"{full} 上证指数 深证成指 创业板指 收盘")
    return queries


def analysis_seed(path: Path, missing: list[str]) -> dict[str, Any]:
    seed = read_json(path)
    if not seed:
        seed = {
            "data_mode": "搜索补足",
            "sources": ["公开网页搜索"],
            "source_note": "结构化行情不完整，已启动公开网页检索补足；精确行情数字仍需交叉验证。",
        }
    existing_note = seed.get("source_note") or ""
    gap_note = "缺口字段：" + ", ".join(missing)
    seed["source_note"] = f"{existing_note} {gap_note}".strip()
    seed.setdefault("risks", []).append("部分关键行情字段来自搜索补足或仍需交叉验证。")
    seed.setdefault("tomorrow_observations", []).append("优先核对成交额、涨跌家数、涨跌停和行业榜单是否与权威行情源一致。")
    path.write_text(json.dumps(seed, ensure_ascii=False, indent=2), encoding="utf-8")
    return seed


def structured_analysis_seed(path: Path, snapshot: dict[str, Any]) -> None:
    seed = {
        "data_mode": "结构化数据",
        "sources": snapshot.get("sources") or [],
        "source_note": "结构化行情字段通过可用源取得，未触发网页检索补足。",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(seed, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run A-share close review with automatic fallback channels.")
    parser.add_argument("--date", type=validate_date, default=today(), help="Trading date, YYYY-MM-DD.")
    parser.add_argument("--snapshot", type=Path, help="Snapshot JSON path.")
    parser.add_argument("--analysis", type=Path, help="Analysis JSON path.")
    parser.add_argument("--web-evidence", type=Path, help="Web evidence JSON path.")
    parser.add_argument("--llm-context", type=Path, help="LLM context Markdown path.")
    parser.add_argument("--report", type=Path, help="Output HTML report path.")
    parser.add_argument("--timeout", default="15", help="Collector HTTP timeout seconds.")
    parser.add_argument("--retries", default="2", help="Collector HTTP retries.")
    parser.add_argument("--page-delay", default="0.3", help="Eastmoney page delay seconds.")
    parser.add_argument(
        "--fetch-pages-per-query",
        default="1",
        help="Fetch and summarize this many result pages per fallback query.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    snapshot = args.snapshot or Path(f"data/a-share-close-{args.date}.json")
    analysis = args.analysis or Path(f"data/a-share-close-analysis-{args.date}.json")
    web_evidence = args.web_evidence or Path(f"data/a-share-close-web-{args.date}.json")
    llm_context = args.llm_context or Path(f"data/a-share-close-llm-context-{args.date}.md")
    report = args.report or Path(f"reports/a-share-close-{args.date}.html")

    run(
        [
            sys.executable,
            str(SCRIPT_DIR / "collect_a_share_close.py"),
            "--date",
            args.date,
            "--output",
            str(snapshot),
            "--timeout",
            str(args.timeout),
            "--retries",
            str(args.retries),
            "--page-delay",
            str(args.page_delay),
        ]
    )

    snapshot_data = read_json(ROOT / snapshot if not snapshot.is_absolute() else snapshot)
    missing = missing_close_fields(snapshot_data)
    analysis_path = resolved(analysis)

    if missing:
        queries = fallback_queries(args.date, missing)
        command = [
            sys.executable,
            str(SCRIPT_DIR / "collect_web_research_fallback.py"),
            "--date",
            args.date,
            "--output",
            str(web_evidence),
            "--analysis-output",
            str(analysis),
            "--fetch-pages-per-query",
            str(args.fetch_pages_per_query),
        ]
        for query in queries:
            command.extend(["--query", query])
        run(command)
        analysis_seed(analysis_path, missing)
        run(
            [
                sys.executable,
                str(SCRIPT_DIR / "prepare_llm_analysis_context.py"),
                "--date",
                args.date,
                "--snapshot",
                str(snapshot),
                "--web-evidence",
                str(web_evidence),
                "--output",
                str(llm_context),
            ]
        )
    elif args.analysis is None:
        structured_analysis_seed(analysis_path, snapshot_data)

    run(
        [
            sys.executable,
            str(SCRIPT_DIR / "render_close_report.py"),
            str(snapshot),
            "--analysis",
            str(analysis),
            "--output",
            str(report),
        ]
    )
    print(
        json.dumps(
            {
                "date": args.date,
                "snapshot": str(snapshot),
                "missing_fields": missing,
                "web_evidence": str(web_evidence) if missing else None,
                "llm_context": str(llm_context) if missing else None,
                "analysis": str(analysis),
                "report": str(report),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

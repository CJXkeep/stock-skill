#!/usr/bin/env python3
"""Run the morning-brief pipeline with automatic evidence fallback."""

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
CLOSE_SCRIPT_DIR = ROOT / "market-close-summary" / "scripts"
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


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def read_json(path: Path) -> dict[str, Any]:
    path = resolve(path)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path = resolve(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def run(args: list[str]) -> None:
    print("+ " + " ".join(args), flush=True)
    subprocess.run(args, cwd=ROOT, check=True)


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def missing_morning_fields(brief: dict[str, Any]) -> list[str]:
    quotes = valid_quotes(brief)
    missing: list[str] = []
    if len(quotes) < 3:
        missing.append("raw_quotes.min3")
    if not any(item.get("bucket") == "global" for item in quotes):
        missing.append("global_market_quotes")
    if not any(item.get("bucket") == "fx_rates" for item in quotes):
        missing.append("fx_rate_quotes")
    if not any(item.get("bucket") == "commodities" for item in quotes):
        missing.append("commodity_quotes")
    missing.extend(missing_metal_futures(brief))
    if not brief.get("impact_paths"):
        missing.append("impact_paths")
    if only_placeholder(brief.get("macro_policy")):
        missing.append("macro_policy")
    if only_placeholder(brief.get("industry_catalysts")):
        missing.append("industry_catalysts")
    if only_placeholder(brief.get("company_signals")):
        missing.append("company_signals")
    return missing


def valid_quotes(brief: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        item
        for item in as_list(brief.get("raw_quotes"))
        if isinstance(item, dict) and usable_quote(item)
    ]


def usable_quote(item: dict[str, Any]) -> bool:
    return bool(item.get("symbol")) and all(
        number_like(item.get(key)) for key in ["price", "previous", "pct"]
    )


def number_like(value: Any) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(number)


def missing_metal_futures(brief: dict[str, Any]) -> list[str]:
    by_symbol = {str(item.get("symbol") or ""): item for item in valid_quotes(brief)}
    missing = []
    for symbol in REQUIRED_METAL_FUTURES:
        item = by_symbol.get(symbol)
        if not item:
            missing.append(f"raw_quotes.{symbol}")
            continue
        if not all(number_like(item.get(key)) for key in ["price", "previous", "pct"]):
            missing.append(f"raw_quotes.{symbol}.price/previous/pct")
    return missing


def only_placeholder(value: Any) -> bool:
    items = [str(item) for item in as_list(value) if item not in (None, "")]
    if not items:
        return True
    placeholder_terms = ["暂无", "需结合", "需要补充", "未能自动获取"]
    return all(any(term in item for term in placeholder_terms) for item in items)


def chinese_date(value: str) -> str:
    parsed = dt.date.fromisoformat(value)
    return f"{parsed.year}年{parsed.month}月{parsed.day}日"


def fallback_queries(date: str, missing: list[str]) -> list[str]:
    full = chinese_date(date)
    queries: list[str] = []
    if any(item in missing for item in ["raw_quotes.min3", "global_market_quotes", "impact_paths"]):
        queries.append(f"global_market::{full} 盘前 隔夜 美股 纳指 费城半导体 港股 中概")
    if any(item in missing for item in ["fx_rate_quotes", "impact_paths"]):
        queries.append(f"fx_rates::{full} 盘前 人民币 汇率 美债收益率 A股")
    if any(item.startswith(("raw_quotes.GC=F", "raw_quotes.SI=F", "raw_quotes.HG=F")) for item in missing):
        queries.append(f"commodities::{full} 盘前 COMEX 黄金 白银 铜 期货 涨跌幅")
    elif any(item in missing for item in ["commodity_quotes", "industry_catalysts", "impact_paths"]):
        queries.append(f"commodities::{full} 盘前 黄金 白银 铜 原油 外盘 期货 A股 有色金属")
    if "macro_policy" in missing:
        queries.append(f"macro_policy::{full} 盘前 政策 央行 证监会 发改委 财政部 A股")
    if "industry_catalysts" in missing:
        queries.append(f"industry_catalyst::{full} 盘前 A股 产业 催化 AI 半导体 机器人 新能源 有色金属")
    if "company_signals" in missing:
        queries.append(f"company_signal::{full} A股 重大公告 业绩 盘前 公司")
    return queries


def evidence_line(item: dict[str, Any]) -> str:
    title = str(item.get("title") or "").strip()
    snippet = str(item.get("snippet") or "").strip()
    url = str(item.get("url") or "").strip()
    text = title
    if snippet:
        text = f"{text}：{snippet}" if text else snippet
    if url:
        host = url.split("//", 1)[-1].split("/", 1)[0]
        text = f"{text}（{host}）" if text else host
    return text[:260]


def lines_for(evidence: dict[str, Any], purposes: set[str], limit: int) -> list[str]:
    lines: list[str] = []
    seen: set[str] = set()
    for item in as_list(evidence.get("results")):
        if not isinstance(item, dict) or item.get("purpose") not in purposes:
            continue
        line = evidence_line(item)
        if line and line not in seen:
            lines.append(line)
            seen.add(line)
        if len(lines) >= limit:
            break
    return lines


def merge_evidence(brief: dict[str, Any], evidence: dict[str, Any], missing: list[str]) -> dict[str, Any]:
    evidence_sources = as_list((evidence.get("analysis_seed") or {}).get("sources")) if evidence.get("results") else []
    sources = list(dict.fromkeys(as_list(brief.get("sources")) + evidence_sources))
    if sources:
        brief["sources"] = sources

    macro = lines_for(evidence, {"macro_policy"}, 4)
    if macro:
        brief["macro_policy"] = macro
    industry = lines_for(evidence, {"industry_catalyst", "commodities"}, 5)
    if industry:
        base = [item for item in as_list(brief.get("industry_catalysts")) if "暂无" not in str(item)]
        brief["industry_catalysts"] = (base + industry)[:8]
    company = lines_for(evidence, {"company_signal"}, 4)
    if company:
        brief["company_signals"] = company

    if not brief.get("impact_paths"):
        global_lines = lines_for(evidence, {"global_market", "fx_rates", "commodities"}, 4)
        brief["impact_paths"] = [
            {
                "event": line,
                "impact": "作为盘前证据补足线索，需等待开盘和第一小时交易确认",
                "areas": "指数、风格、资源品、外资相关方向",
                "confirmation": "观察开盘强弱、成交额、人民币/港股联动和主线扩散",
            }
            for line in global_lines
        ]

    quality = as_list(brief.get("data_quality"))
    quality.append("已自动启动网页证据补足；缺口字段：" + ", ".join(missing))
    if evidence.get("errors"):
        quality.append("网页检索错误：" + "; ".join(str(item.get("message")) for item in evidence.get("errors", [])[:3]))
    brief["data_quality"] = quality
    normalize_push_sections(brief)
    return brief


def normalize_push_sections(brief: dict[str, Any]) -> None:
    if only_placeholder(brief.get("macro_policy")):
        brief["macro_policy"] = [
            "盘前未捕捉到可直接改变A股开盘假设的新增宏观或监管线索，先以隔夜风险资产、人民币、利率和商品价格验证风险偏好。"
        ]
    if only_placeholder(brief.get("company_signals")):
        brief["company_signals"] = [
            "盘前未捕捉到具备全市场外溢影响的公司公告线索，个股公告仍以交易所和CNINFO为准。"
        ]
    risks = [
        item
        for item in as_list(brief.get("risks"))
        if "价格源" not in str(item) and "人工核验" not in str(item)
    ]
    if not risks:
        risks = [
            "若隔夜利好方向开盘后快速回落，说明资金认可度不足。",
            "若人民币、港股和A股权重背离，降低对单一海外线索的解释权重。",
        ]
    brief["risks"] = risks


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run A-share morning brief with automatic fallback channels.")
    parser.add_argument("--date", type=validate_date, default=today(), help="Brief date, YYYY-MM-DD.")
    parser.add_argument("--brief", type=Path, help="Brief JSON path.")
    parser.add_argument("--web-evidence", type=Path, help="Web evidence JSON path.")
    parser.add_argument("--report", type=Path, help="Output HTML report path.")
    parser.add_argument("--timeout", default="15", help="Collector HTTP timeout seconds.")
    parser.add_argument("--retries", default="2", help="Collector HTTP retries.")
    parser.add_argument("--fetch-pages-per-query", default="0", help="Fetch this many result pages per fallback query.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    brief = args.brief or Path(f"data/morning-brief-{args.date}.json")
    web_evidence = args.web_evidence or Path(f"data/morning-brief-web-{args.date}.json")
    report = args.report or Path(f"reports/morning-brief-{args.date}.html")

    run(
        [
            sys.executable,
            str(SCRIPT_DIR / "collect_morning_brief_sources.py"),
            "--date",
            args.date,
            "--output",
            str(brief),
            "--timeout",
            str(args.timeout),
            "--retries",
            str(args.retries),
        ]
    )

    brief_data = read_json(brief)
    missing = missing_morning_fields(brief_data)
    if missing:
        command = [
            sys.executable,
            str(CLOSE_SCRIPT_DIR / "collect_web_research_fallback.py"),
            "--date",
            args.date,
            "--output",
            str(web_evidence),
            "--no-default-queries",
            "--fetch-pages-per-query",
            str(args.fetch_pages_per_query),
        ]
        for query in fallback_queries(args.date, missing):
            command.extend(["--query", query])
        run(command)
        evidence = read_json(web_evidence)
        brief_data = merge_evidence(brief_data, evidence, missing)
        write_json(brief, brief_data)
    else:
        normalize_push_sections(brief_data)
        write_json(brief, brief_data)

    run(
        [
            sys.executable,
            str(SCRIPT_DIR / "render_morning_brief.py"),
            str(brief),
            "--output",
            str(report),
        ]
    )
    print(
        json.dumps(
            {
                "date": args.date,
                "brief": str(brief),
                "missing_fields": missing,
                "web_evidence": str(web_evidence) if missing else None,
                "report": str(report),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

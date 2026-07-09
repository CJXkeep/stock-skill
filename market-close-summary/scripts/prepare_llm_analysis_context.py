#!/usr/bin/env python3
"""Prepare a compact LLM synthesis context for an A-share close review.

This script does not call an LLM. It turns structured market snapshots and
web-search evidence into a deterministic Markdown prompt/context package that
an agent can use to produce the optional analysis JSON consumed by
render_close_report.py.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any


def today() -> str:
    return dt.date.today().isoformat()


def validate_date(value: str) -> str:
    try:
        return dt.date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise argparse.ArgumentTypeError("date must use YYYY-MM-DD format") from exc


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("value must be a positive integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be a positive integer")
    return parsed


def read_json(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def safe(value: Any, fallback: str = "-") -> str:
    if value in (None, ""):
        return fallback
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def format_pct(value: Any) -> str:
    try:
        return f"{float(value):+.2f}%"
    except (TypeError, ValueError):
        return "-"


def format_amount_cny(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "-"
    if abs(number) >= 100_000_000:
        return f"{number / 100_000_000:,.0f} 亿"
    return f"{number:,.0f}"


def truncate(value: Any, limit: int) -> str:
    text = "" if value is None else str(value)
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def lines_join(lines: list[str]) -> str:
    return "\n".join(lines).rstrip() + "\n"


def source_names(snapshot: dict[str, Any], evidence: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for value in snapshot.get("sources") or []:
        text = str(value).strip()
        if text and text not in names:
            names.append(text)
    seed = evidence.get("analysis_seed") or {}
    for value in seed.get("sources") or []:
        text = str(value).strip()
        if text and text not in names:
            names.append(text)
    return names


def snapshot_section(snapshot: dict[str, Any], max_items: int) -> str:
    if not snapshot:
        return "## 结构化行情快照\n\n未提供结构化行情快照。\n"

    lines = ["## 结构化行情快照", ""]
    lines.append(f"- 交易日：{safe(snapshot.get('date'))}")
    lines.append(f"- 抓取时间：{safe(snapshot.get('retrieved_at'))}")
    lines.append(f"- 数据源：{', '.join(snapshot.get('sources') or ['-'])}")

    turnover = snapshot.get("turnover") or {}
    breadth = snapshot.get("breadth") or {}
    limits = snapshot.get("limit_stats") or {}
    lines.append(f"- 成交额：{format_amount_cny(turnover.get('amount_cny'))}；说明：{safe(turnover.get('note') or turnover.get('source'))}")
    lines.append(
        "- 涨跌家数："
        f"{safe(breadth.get('rising'))}/{safe(breadth.get('falling'))}"
        f"；部分样本：{safe(breadth.get('is_partial'))}"
    )
    lines.append(
        "- 涨停/跌停："
        f"{safe(limits.get('limit_up_count'))}/{safe(limits.get('limit_down_count'))}"
    )

    indexes = snapshot.get("indexes") or []
    if indexes:
        lines.extend(["", "### 主要指数", "", "| 指数 | 收盘 | 涨跌幅 | 来源 |", "| --- | ---: | ---: | --- |"])
        for item in indexes[:max_items]:
            lines.append(
                f"| {safe(item.get('name'))} | {safe(item.get('close'))} | "
                f"{format_pct(item.get('change_pct'))} | {safe(item.get('source'))} |"
            )

    sectors = snapshot.get("sectors") or {}
    themes = snapshot.get("themes") or {}
    for title, rows in [
        ("领涨行业", sectors.get("leading") or []),
        ("领跌行业", sectors.get("lagging") or []),
        ("活跃题材", themes.get("active") or []),
        ("弱势题材", themes.get("weak") or []),
    ]:
        lines.extend(["", f"### {title}"])
        if not rows:
            lines.append("- 缺失")
            continue
        for item in rows[:max_items]:
            extra = item.get("driver_event") or item.get("leader") or item.get("source") or ""
            lines.append(f"- {safe(item.get('name'))} {format_pct(item.get('change_pct'))} {truncate(extra, 80)}")

    notes = snapshot.get("notes") or []
    errors = snapshot.get("errors") or []
    if notes or errors:
        lines.extend(["", "### 数据缺口与错误"])
        for item in notes[:max_items]:
            lines.append(f"- note: {truncate(item, 160)}")
        for item in errors[:max_items]:
            lines.append(f"- {safe(item.get('source'))}: {truncate(item.get('message'), 160)}")
    return lines_join(lines)


def web_evidence_section(evidence: dict[str, Any], max_results: int, snippet_chars: int) -> str:
    if not evidence:
        return "## 网页检索证据\n\n未提供网页检索证据。\n"

    lines = ["## 网页检索证据", ""]
    lines.append(f"- 检索时间：{safe(evidence.get('retrieved_at'))}")
    lines.append(f"- 搜索引擎：{safe(evidence.get('search_engine'))}")
    seed = evidence.get("analysis_seed") or {}
    if seed:
        lines.append(f"- 建议数据模式：{safe(seed.get('data_mode'))}")
        lines.append(f"- 建议来源：{', '.join(seed.get('sources') or ['-'])}")
        lines.append(f"- 来源说明：{safe(seed.get('source_note'))}")

    results = evidence.get("results") or []
    if results:
        lines.extend(["", "### 搜索结果摘录"])
        for index, item in enumerate(results[:max_results], 1):
            lines.append(f"{index}. [{safe(item.get('purpose'))}] {truncate(item.get('title'), 120)}")
            if item.get("snippet"):
                lines.append(f"   - 摘要：{truncate(item.get('snippet'), snippet_chars)}")
            page = item.get("page_summary") or {}
            if page.get("description"):
                lines.append(f"   - 页面描述：{truncate(page.get('description'), snippet_chars)}")
            if page.get("excerpt"):
                lines.append(f"   - 页面摘录：{truncate(page.get('excerpt'), snippet_chars)}")
            lines.append(f"   - URL：{safe(item.get('url'))}")
    else:
        lines.append("- 未取得可用搜索结果。")

    errors = evidence.get("errors") or []
    if errors:
        lines.extend(["", "### 搜索错误"])
        for item in errors[:max_results]:
            lines.append(f"- {safe(item.get('purpose'))} / {safe(item.get('query'))}: {truncate(item.get('message'), 160)}")
    return lines_join(lines)


def output_contract_section(snapshot: dict[str, Any], evidence: dict[str, Any]) -> str:
    sources = source_names(snapshot, evidence) or ["公开数据/网页检索"]
    seed = evidence.get("analysis_seed") or {}
    data_mode = seed.get("data_mode") or ("结构化数据" if snapshot else "搜索补足")
    source_note = seed.get("source_note") or "根据可取得的公开数据与检索证据生成，精确行情需交叉验证。"
    example = {
        "data_mode": data_mode,
        "sources": sources,
        "source_note": source_note,
        "market_temperature": "强势进攻/修复偏强/中性震荡/偏弱防守/风险释放/数据不足",
        "one_sentence_conclusion": "一句话结论。缺少关键数据时必须写明缺口。",
        "market_structure": "指数、宽度、成交、风格结构的综合判断。",
        "theme_commentary": "主线、轮动、分歧与持续性证据。",
        "main_line_strength": "强/中/弱/待确认",
        "main_line_note": "主线强度说明，注明是否搜索补足。",
        "catalysts": ["异动归因1", "异动归因2", "异动归因3"],
        "risks": ["风险信号1", "风险信号2"],
        "tomorrow_observations": ["明日观察1", "明日观察2", "明日观察3", "明日观察4"],
    }
    lines = [
        "## LLM 输出要求",
        "",
        "只输出一个 JSON 对象，不要输出 Markdown、解释文字或代码块。",
        "禁止编造缺失的指数、成交额、涨跌家数、涨跌停、板块涨幅等数字。",
        "如果只有网页叙事证据，使用 `搜索补足`，并把关键缺口写入 `source_note`、`risks` 或 `tomorrow_observations`。",
        "把事实、解释和明日验证点分开，避免单因果断言。",
        "",
        "JSON schema 示例：",
        "",
        "```json",
        json.dumps(example, ensure_ascii=False, indent=2),
        "```",
    ]
    return lines_join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare a Markdown context package for LLM A-share close synthesis."
    )
    parser.add_argument("--date", type=validate_date, default=today(), help="Trading date, YYYY-MM-DD.")
    parser.add_argument("--snapshot", type=Path, help="Snapshot JSON from collect_a_share_close.py.")
    parser.add_argument("--web-evidence", type=Path, help="Evidence JSON from collect_web_research_fallback.py.")
    parser.add_argument(
        "--output",
        type=Path,
        help="Output Markdown path. Defaults to data/a-share-close-llm-context-YYYY-MM-DD.md.",
    )
    parser.add_argument("--max-items", type=positive_int, default=8, help="Maximum structured rows per section.")
    parser.add_argument("--max-results", type=positive_int, default=12, help="Maximum web results to include.")
    parser.add_argument("--snippet-chars", type=positive_int, default=420, help="Maximum characters per snippet.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    snapshot = read_json(args.snapshot)
    evidence = read_json(args.web_evidence)
    output = args.output or Path(f"data/a-share-close-llm-context-{args.date}.md")
    sections = [
        f"# A股收盘复盘 LLM 分析上下文｜{args.date}\n",
        "目标：基于结构化行情和网页检索证据，生成 `render_close_report.py` 可用的 `analysis.json`。\n",
        snapshot_section(snapshot, args.max_items),
        web_evidence_section(evidence, args.max_results, args.snippet_chars),
        output_contract_section(snapshot, evidence),
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(sections), encoding="utf-8")
    print(str(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

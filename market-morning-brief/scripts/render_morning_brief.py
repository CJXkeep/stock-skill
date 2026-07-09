#!/usr/bin/env python3
"""Render a fixed HTML A-share morning brief from brief JSON."""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
from pathlib import Path
from typing import Any


PLACEHOLDER_RE = re.compile(r"{{([a-zA-Z0-9_]+)}}")


def validate_date(value: str) -> str:
    try:
        return dt.date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise argparse.ArgumentTypeError("date must use YYYY-MM-DD format") from exc


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def esc(value: Any) -> str:
    if value is None or value == "":
        return "-"
    return html.escape(str(value), quote=True)


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def list_items(values: list[Any], fallback: str) -> str:
    items = [v for v in values if v not in (None, "")]
    if not items:
        items = [fallback]
    return "\n".join(f"<li>{esc(item)}</li>" for item in items)


def impact_rows(items: list[Any]) -> str:
    rows = []
    for item in items:
        if not isinstance(item, dict):
            rows.append(
                "<tr>"
                f"<td>{esc(item)}</td>"
                "<td>待分析</td>"
                "<td>待确认</td>"
                "<td>观察开盘和第一小时反应</td>"
                "</tr>"
            )
            continue
        rows.append(
            "<tr>"
            f"<td>{esc(item.get('event'))}</td>"
            f"<td>{esc(item.get('impact'))}</td>"
            f"<td>{esc(item.get('areas'))}</td>"
            f"<td>{esc(item.get('confirmation'))}</td>"
            "</tr>"
        )
    if not rows:
        return '<tr><td colspan="4">暂无足够事件映射，需补充新闻和市场数据。</td></tr>'
    return "\n".join(rows)


def default_overview(data: dict[str, Any]) -> str:
    tone = data.get("overall_tone") or "待确认"
    events = sum(
        len(as_list(data.get(key)))
        for key in ["global_markets", "macro_policy", "industry_catalysts", "company_signals"]
    )
    if events == 0:
        return "盘前事件数据不足，先补充隔夜市场、政策和产业催化后再形成强结论。"
    return f"今日盘前环境暂定为{tone}，需要用开盘强弱、成交额和主线扩散来验证。"


def default_watchlist(data: dict[str, Any]) -> list[str]:
    items = [
        "观察开盘强弱，以及是否出现高开低走或低开修复。",
        "观察人民币、港股、中概和外资相关线索是否共振。",
        "观察活跃主题是否在第一小时扩散，而不是只停留在前排。",
        "观察成交额是否支持风险偏好修复。",
    ]
    if not data.get("impact_paths"):
        items.insert(0, "先补齐重要事件到A股影响路径的映射。")
    return items


def data_quality(data: dict[str, Any]) -> list[str]:
    items = [
        f"数据源：{', '.join(as_list(data.get('sources')) or ['未标注'])}",
        f"生成时间：{data.get('retrieved_at', '-')}",
    ]
    items.extend(as_list(data.get("data_quality")))
    return items


def build_context(data: dict[str, Any]) -> dict[str, str]:
    return {
        "date": esc(data.get("date") or dt.date.today().isoformat()),
        "time_window": esc(data.get("time_window") or "上一交易日收盘后至今日开盘前"),
        "retrieved_at": esc(data.get("retrieved_at") or dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        "overall_tone": esc(data.get("overall_tone") or "待确认"),
        "one_sentence_overview": esc(data.get("one_sentence_overview") or default_overview(data)),
        "global_market_items": list_items(as_list(data.get("global_markets")), "暂无隔夜全球市场数据。"),
        "macro_policy_items": list_items(as_list(data.get("macro_policy")), "暂无重要宏观政策事件。"),
        "industry_catalyst_items": list_items(as_list(data.get("industry_catalysts")), "暂无明确产业催化。"),
        "company_signal_items": list_items(as_list(data.get("company_signals")), "暂无具有板块外溢影响的公司线索。"),
        "impact_rows": impact_rows(as_list(data.get("impact_paths"))),
        "watchlist_items": list_items(as_list(data.get("watchlist")) or default_watchlist(data), "观察开盘、成交、主线和风险扩散。"),
        "risk_items": list_items(as_list(data.get("risks")), "暂无明确反证，重点看开盘后市场是否认可盘前假设。"),
        "data_quality_items": list_items(data_quality(data), "数据质量信息缺失。"),
        "sources": esc(", ".join(as_list(data.get("sources")) or ["未标注"])),
    }


def render_template(template: str, context: dict[str, str]) -> str:
    unknown = sorted(set(PLACEHOLDER_RE.findall(template)) - set(context))
    if unknown:
        raise ValueError("Template contains unsupported placeholders: " + ", ".join(unknown))

    def replace(match: re.Match[str]) -> str:
        return context[match.group(1)]

    return PLACEHOLDER_RE.sub(replace, template)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a fixed HTML A-share morning brief.")
    parser.add_argument("brief", type=Path, help="Brief JSON path.")
    parser.add_argument(
        "--template",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "assets" / "morning-brief-template.html",
        help="HTML template path.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output HTML path. Defaults to reports/morning-brief-YYYY-MM-DD.html.",
    )
    parser.add_argument("--date", type=validate_date, help="Override brief date.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data = read_json(args.brief)
    if args.date:
        data["date"] = args.date
    brief_date = data.get("date") or dt.date.today().isoformat()
    output = args.output or Path(f"reports/morning-brief-{brief_date}.html")
    template = args.template.read_text(encoding="utf-8")
    html_text = render_template(template, build_context(data))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html_text, encoding="utf-8")
    print(str(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

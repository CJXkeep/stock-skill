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


def format_number(value: Any, digits: int = 2) -> str:
    try:
        return f"{float(value):,.{digits}f}"
    except (TypeError, ValueError):
        return "-"


def format_pct(value: Any) -> str:
    try:
        return f"{float(value):+.2f}%"
    except (TypeError, ValueError):
        return "-"


def pct_class(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return ""
    if number > 0:
        return "up"
    if number < 0:
        return "down"
    return ""


def quote_by_symbol(items: list[Any], symbol: str) -> dict[str, Any] | None:
    for item in items:
        if isinstance(item, dict) and item.get("symbol") == symbol:
            return item
    return None


def quote_label(item: dict[str, Any] | None, fallback: str) -> str:
    if not item:
        return fallback
    pct = format_pct(item.get("pct"))
    if pct == "-":
        return fallback
    return pct


def multi_quote_label(items: list[Any], symbols: list[tuple[str, str]], fallback: str) -> str:
    parts = []
    for symbol, label in symbols:
        item = quote_by_symbol(items, symbol)
        pct = format_pct(item.get("pct")) if item else "-"
        if pct != "-":
            parts.append(f"{label} {pct}")
    return " / ".join(parts) if parts else fallback


def quote_metric_cards(items: list[Any]) -> str:
    metrics = [
        (
            "美股基调",
            quote_by_symbol(items, "^GSPC"),
            "标普500",
            "观察全球风险偏好",
        ),
        (
            "科技映射",
            quote_by_symbol(items, "^SOX") or quote_by_symbol(items, "^IXIC"),
            "费半/纳指",
            "影响半导体、AI、算力",
        ),
        (
            "港股中概",
            quote_by_symbol(items, "KWEB") or quote_by_symbol(items, "^HSI"),
            "中概/恒指",
            "观察港股映射和外资线索",
        ),
        (
            "人民币",
            quote_by_symbol(items, "CNH=X"),
            "USD/CNH",
            "观察大盘权重和风险偏好",
        ),
        (
            "金银铜期货",
            None,
            multi_quote_label(items, [("GC=F", "金"), ("SI=F", "银"), ("HG=F", "铜")], "金银铜"),
            "观察贵金属、有色金属映射",
        ),
    ]
    cards = []
    for title, item, fallback_value, note in metrics:
        pct = item.get("pct") if item else None
        name = item.get("name") if item else ("黄金/白银/铜期货" if title == "金银铜期货" else fallback_value)
        cards.append(
            '<div class="metric">'
            f'<div class="name">{esc(title)}</div>'
            f'<div class="value {pct_class(pct)}">{esc(quote_label(item, fallback_value))}</div>'
            f'<div class="note">{esc(name)}｜{esc(note)}</div>'
            "</div>"
        )
    return "\n".join(cards)


def quote_bar_rows(items: list[Any]) -> str:
    parsed = []
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            pct = float(item.get("pct"))
        except (TypeError, ValueError):
            continue
        parsed.append((item, pct))
    if not parsed:
        return '<div class="empty-state">暂无可绘制的隔夜行情线索。</div>'
    max_abs = max(max(abs(pct) for _, pct in parsed), 1.0)
    rows = []
    for item, pct in parsed:
        width = min(abs(pct) / max_abs * 50, 50)
        side_class = "positive" if pct >= 0 else "negative"
        style = f"left:50%;width:{width:.2f}%" if pct >= 0 else f"right:50%;width:{width:.2f}%"
        rows.append(
            '<div class="bar-row">'
            f'<div class="bar-name">{esc(item.get("name"))}</div>'
            '<div class="bar-track diverging"><span class="axis"></span>'
            f'<span class="bar-fill {side_class}" style="{style}"></span></div>'
            f'<div class="bar-value {pct_class(pct)}">{esc(format_pct(pct))}</div>'
            "</div>"
        )
    return "\n".join(rows)


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def quote_pct(items: list[Any], symbol: str) -> float | None:
    item = quote_by_symbol(items, symbol)
    if not item:
        return None
    try:
        return float(item.get("pct"))
    except (TypeError, ValueError):
        return None


def preopen_heat_score(items: list[Any]) -> float | None:
    signals = 0
    score = 50.0
    for symbol, weight in [
        ("^GSPC", 7),
        ("^IXIC", 8),
        ("^SOX", 9),
        ("^HSI", 7),
        ("KWEB", 7),
        ("GC=F", 3),
        ("SI=F", 3),
        ("HG=F", 3),
        ("CL=F", 2),
    ]:
        pct = quote_pct(items, symbol)
        if pct is None:
            continue
        score += clamp(pct * weight, -12, 12)
        signals += 1

    usdcnh = quote_pct(items, "CNH=X")
    if usdcnh is not None:
        score -= clamp(usdcnh * 16, -10, 10)
        signals += 1

    yield_pct = quote_pct(items, "^TNX")
    if yield_pct is not None:
        score -= clamp(yield_pct * 2.5, -8, 8)
        signals += 1

    if not signals:
        return None
    return clamp(score, 0, 100)


def preopen_heat_meter(items: list[Any]) -> str:
    score = preopen_heat_score(items)
    if score is None:
        return '<div class="empty-state">缺少隔夜行情数据，暂不能计算盘前温度。</div>'
    if score >= 70:
        label = "risk-on"
    elif score >= 55:
        label = "constructive"
    elif score >= 45:
        label = "neutral"
    elif score >= 30:
        label = "mixed"
    else:
        label = "risk-off"
    return (
        '<div class="heat-meter">'
        f'<div class="heat-number">{score:.0f}<span>/100</span></div>'
        '<div class="heat-track">'
        f'<div class="heat-fill" style="width:{score:.1f}%"></div>'
        "</div>"
        f'<div class="heat-label">{esc(label)}</div>'
        "</div>"
    )


def asset_heat_rows(items: list[Any]) -> str:
    groups = [
        ("全球权益", ["^GSPC", "^IXIC", "^DJI", "^SOX", "^HSI", "KWEB"], "平均涨跌幅"),
        ("汇率利率", ["CNH=X", "^TNX"], "平均变动，不直接代表风险偏好方向"),
        ("金银铜期货", ["GC=F", "SI=F", "HG=F"], "金/银/铜期货平均涨跌幅"),
        ("大宗商品", ["GC=F", "SI=F", "CL=F", "HG=F"], "商品平均涨跌幅"),
    ]
    rows = []
    for name, symbols, note_prefix in groups:
        values = [quote_pct(items, symbol) for symbol in symbols]
        clean = [value for value in values if value is not None]
        if not clean:
            rows.append(
                '<div class="asset-row">'
                f'<div class="asset-head"><span>{esc(name)}</span><b>-</b></div>'
                '<div class="asset-track"><span class="asset-fill neutral" style="width:0%"></span></div>'
                '<div class="asset-note">暂无足够数据</div>'
                "</div>"
            )
            continue
        avg = sum(clean) / len(clean)
        width = min(abs(avg) / 3.0 * 100, 100)
        cls = "positive" if avg >= 0 else "negative"
        rows.append(
            '<div class="asset-row">'
            f'<div class="asset-head"><span>{esc(name)}</span><b class="{pct_class(avg)}">{esc(format_pct(avg))}</b></div>'
            '<div class="asset-track">'
            f'<span class="asset-fill {cls}" style="width:{width:.2f}%"></span>'
            "</div>"
            f'<div class="asset-note">{esc(note_prefix)}｜覆盖 {len(clean)} 个公开行情线索</div>'
            "</div>"
        )
    return "\n".join(rows)


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


def raw_quote_rows(items: list[Any]) -> str:
    rows = []
    for item in items:
        if not isinstance(item, dict):
            continue
        pct = item.get("pct")
        rows.append(
            "<tr>"
            f"<td>{esc(item.get('name'))}</td>"
            f"<td>{esc(item.get('symbol'))}</td>"
            f"<td>{esc(item.get('area'))}</td>"
            f"<td>{esc(format_number(item.get('price'), 4))}</td>"
            f"<td>{esc(format_number(item.get('previous'), 4))}</td>"
            f"<td class=\"{pct_class(pct)}\">{esc(format_pct(pct))}</td>"
            f"<td>{esc(item.get('currency'))}</td>"
            f"<td>{esc(item.get('exchange'))}</td>"
            "</tr>"
        )
    if not rows:
        return '<tr><td colspan="8">暂无原始行情线索。</td></tr>'
    return "\n".join(rows)


def data_quality(data: dict[str, Any]) -> list[str]:
    items = [
        f"数据源：{', '.join(as_list(data.get('sources')) or ['未标注'])}",
        f"生成时间：{data.get('retrieved_at', '-')}",
    ]
    items.extend(as_list(data.get("data_quality")))
    return items


def build_context(data: dict[str, Any]) -> dict[str, str]:
    raw_quotes = as_list(data.get("raw_quotes"))
    return {
        "date": esc(data.get("date") or dt.date.today().isoformat()),
        "time_window": esc(data.get("time_window") or "上一交易日收盘后至今日开盘前"),
        "retrieved_at": esc(data.get("retrieved_at") or dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        "overall_tone": esc(data.get("overall_tone") or "待确认"),
        "one_sentence_overview": esc(data.get("one_sentence_overview") or default_overview(data)),
        "preopen_heat_meter": preopen_heat_meter(raw_quotes),
        "asset_heat_rows": asset_heat_rows(raw_quotes),
        "quote_metric_cards": quote_metric_cards(raw_quotes),
        "quote_bar_rows": quote_bar_rows(raw_quotes),
        "global_market_items": list_items(as_list(data.get("global_markets")), "暂无隔夜全球市场数据。"),
        "macro_policy_items": list_items(as_list(data.get("macro_policy")), "暂无重要宏观政策事件。"),
        "industry_catalyst_items": list_items(as_list(data.get("industry_catalysts")), "暂无明确产业催化。"),
        "company_signal_items": list_items(as_list(data.get("company_signals")), "暂无具有板块外溢影响的公司线索。"),
        "impact_rows": impact_rows(as_list(data.get("impact_paths"))),
        "watchlist_items": list_items(as_list(data.get("watchlist")) or default_watchlist(data), "观察开盘、成交、主线和风险扩散。"),
        "risk_items": list_items(as_list(data.get("risks")), "暂无明确反证，重点看开盘后市场是否认可盘前假设。"),
        "data_quality_items": list_items(data_quality(data), "数据质量信息缺失。"),
        "raw_quote_rows": raw_quote_rows(raw_quotes),
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

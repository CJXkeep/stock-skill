#!/usr/bin/env python3
"""Render an A-share close snapshot into the fixed HTML report template."""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
from pathlib import Path
from typing import Any


PLACEHOLDER_RE = re.compile(r"{{([a-zA-Z0-9_]+)}}")
METAL_KEYWORDS = [
    "黄金",
    "白银",
    "铜",
    "有色",
    "贵金属",
    "工业金属",
    "小金属",
    "能源金属",
    "金属新材料",
]


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


def truncate(value: Any, limit: int = 220) -> str:
    text = "" if value is None else str(value)
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


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


def format_pct(value: Any) -> str:
    try:
        return f"{float(value):+.2f}%"
    except (TypeError, ValueError):
        return "-"


def format_number(value: Any, digits: int = 2) -> str:
    try:
        return f"{float(value):,.{digits}f}"
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


def change_value(item: dict[str, Any]) -> Any:
    value = item.get("change_pct")
    if value is None:
        value = item.get("pct")
    return value


def is_metal_item(item: dict[str, Any]) -> bool:
    text = " ".join(
        str(item.get(key) or "")
        for key in ["name", "driver_event", "leader"]
    )
    return any(keyword in text for keyword in METAL_KEYWORDS)


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def format_int(value: Any) -> str:
    try:
        return f"{int(float(value)):,}"
    except (TypeError, ValueError):
        return "-"


def list_items(values: list[Any], fallback: str) -> str:
    items = [v for v in values if v not in (None, "")]
    if not items:
        items = [fallback]
    return "\n".join(f"<li>{esc(item)}</li>" for item in items)


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def analysis_value(analysis: dict[str, Any], key: str, fallback: Any = None) -> Any:
    return analysis.get(key, fallback)


def source_names(snapshot: dict[str, Any], analysis: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for value in snapshot.get("sources") or []:
        text = str(value).strip()
        if text and text not in names:
            names.append(text)
    for value in as_list(analysis_value(analysis, "sources")):
        text = str(value).strip()
        if text and text not in names:
            names.append(text)
    return names or ["无成功来源"]


def infer_data_mode(snapshot: dict[str, Any], analysis: dict[str, Any]) -> str:
    explicit = analysis_value(analysis, "data_mode")
    if explicit:
        return str(explicit)
    has_structured = any(
        [
            snapshot.get("indexes"),
            snapshot.get("breadth"),
            snapshot.get("limit_stats"),
            (snapshot.get("sectors") or {}).get("leading"),
            (snapshot.get("themes") or {}).get("active"),
        ]
    )
    if has_structured:
        return "结构化数据"
    if analysis_value(analysis, "sources") or analysis_value(analysis, "source_note"):
        return "搜索补足"
    return "数据不足"


def source_note(snapshot: dict[str, Any], analysis: dict[str, Any]) -> str:
    explicit = analysis_value(analysis, "source_note")
    if explicit:
        if isinstance(explicit, list):
            return "；".join(str(item) for item in explicit if item not in (None, ""))
        return str(explicit)
    notes = [str(item) for item in (snapshot.get("notes") or [])[:2] if item not in (None, "")]
    if notes:
        return "；".join(notes)
    return "主要结论来自已取得的公开数据与复盘证据。"


def average_index_change(snapshot: dict[str, Any]) -> float | None:
    changes = []
    for item in snapshot.get("indexes", []):
        value = item.get("change_pct")
        try:
            changes.append(float(value))
        except (TypeError, ValueError):
            pass
    if not changes:
        return None
    return sum(changes) / len(changes)


def breadth_counts(snapshot: dict[str, Any]) -> tuple[int, int, int, int] | None:
    breadth = snapshot.get("breadth") or {}
    try:
        rising = int(float(breadth.get("rising")))
        falling = int(float(breadth.get("falling")))
        flat = int(float(breadth.get("flat") or 0))
        missing = int(float(breadth.get("suspended_or_missing") or 0))
    except (TypeError, ValueError):
        return None
    if rising + falling + flat + missing <= 0:
        return None
    return rising, falling, flat, missing


def breadth_ratio(snapshot: dict[str, Any], *, allow_partial: bool = False) -> float | None:
    breadth = snapshot.get("breadth") or {}
    if breadth.get("is_partial") and not allow_partial:
        return None
    counts = breadth_counts(snapshot)
    if counts is None:
        return None
    rising, falling, _, _ = counts
    try:
        total = float(rising) + float(falling)
        if total <= 0:
            return None
        return rising / total
    except (TypeError, ValueError):
        return None


def infer_temperature(snapshot: dict[str, Any]) -> str:
    avg = average_index_change(snapshot)
    ratio = breadth_ratio(snapshot)
    if ratio is None:
        ratio = breadth_ratio(snapshot, allow_partial=True)
    if avg is None and ratio is None:
        stats = snapshot.get("limit_stats") or {}
        try:
            up = float(stats.get("limit_up_count"))
            down = float(stats.get("limit_down_count"))
            if up > down * 1.5:
                return "情绪偏热"
            if down > up * 1.5:
                return "情绪偏冷"
            return "情绪均衡"
        except (TypeError, ValueError):
            return "数据不足"
    if avg is not None and avg <= -1.0 and (ratio is None or ratio < 0.35):
        return "风险释放"
    if avg is not None and avg < -0.3:
        return "偏弱防守"
    if avg is not None and avg >= 0.8 and (ratio is None or ratio > 0.60):
        return "强势进攻"
    if avg is not None and avg > 0:
        return "修复偏强"
    if ratio is not None and ratio >= 0.60:
        return "结构偏强"
    if ratio is not None and ratio <= 0.35:
        return "结构偏弱"
    return "中性震荡"


def default_conclusion(snapshot: dict[str, Any], temperature: str) -> str:
    notes = snapshot.get("notes") or []
    if temperature == "数据不足":
        return "今日免费源数据不完整，先以数据质量核查和人工补充为主，暂不做强结论。"
    if (snapshot.get("breadth") or {}).get("is_partial"):
        return f"今日A股暂归为{temperature}，但宽度样本不完整，市场温度需要等全量涨跌家数交叉验证。"
    if notes:
        return f"今日A股暂归为{temperature}，但存在数据缺口，结论需要结合补充数据交叉验证。"
    return f"今日A股暂归为{temperature}，重点观察指数表现、市场宽度和主线持续性是否互相确认。"


def render_index_rows(snapshot: dict[str, Any]) -> str:
    rows = []
    for item in snapshot.get("indexes", []):
        change = item.get("change_pct")
        cls = pct_class(change)
        rows.append(
            "<tr>"
            f"<td>{esc(item.get('name'))}</td>"
            f"<td>{esc(format_number(item.get('close')))}</td>"
            f"<td class=\"{cls}\">{esc(format_pct(change))}</td>"
            f"<td>{esc(index_comment(item))}</td>"
            "</tr>"
        )
    if not rows:
        return '<tr><td colspan="4">主要指数数据缺失，需要补充或交叉验证。</td></tr>'
    return "\n".join(rows)


def index_comment(item: dict[str, Any]) -> str:
    change = item.get("change_pct")
    try:
        number = float(change)
    except (TypeError, ValueError):
        return "缺少涨跌幅"
    if number >= 1:
        return "明显走强"
    if number > 0:
        return "小幅走强"
    if number <= -1:
        return "明显承压"
    if number < 0:
        return "小幅承压"
    return "持平"


def leading_names(items: list[dict[str, Any]], limit: int = 5) -> list[str]:
    names = []
    for item in items[:limit]:
        name = item.get("name")
        pct = change_value(item)
        if name:
            pct_text = format_pct(pct)
            names.append(f"{name} {pct_text}" if pct_text != "-" else str(name))
    return names


def render_theme_tags(snapshot: dict[str, Any]) -> str:
    tags = leading_names((snapshot.get("themes") or {}).get("active", []), 6)
    if not tags:
        tags = leading_names((snapshot.get("sectors") or {}).get("leading", []), 6)
    if not tags:
        return '<span class="tag">主线数据缺失</span>'
    return "".join(f'<span class="tag">{esc(tag)}</span>' for tag in tags)


def market_heat_score(snapshot: dict[str, Any]) -> float | None:
    signals = 0
    score = 50.0
    avg = average_index_change(snapshot)
    ratio = breadth_ratio(snapshot, allow_partial=True)
    if avg is not None:
        score += clamp(avg * 12, -22, 22)
        signals += 1
    if ratio is not None:
        score += clamp((ratio - 0.5) * 55, -24, 24)
        signals += 1
    stats = snapshot.get("limit_stats") or {}
    try:
        up = float(stats.get("limit_up_count"))
        down = float(stats.get("limit_down_count"))
        if up + down > 0:
            score += clamp((up - down) / max(up + down, 1) * 14, -14, 14)
            signals += 1
    except (TypeError, ValueError):
        pass
    if not signals:
        return None
    return clamp(score, 0, 100)


def render_heat_meter(snapshot: dict[str, Any]) -> str:
    score = market_heat_score(snapshot)
    if score is None:
        return '<div class="empty-state">缺少指数、宽度或涨跌停数据，暂不能计算热度。</div>'
    if score >= 70:
        label = "热"
    elif score >= 55:
        label = "偏热"
    elif score >= 45:
        label = "平衡"
    elif score >= 30:
        label = "偏冷"
    else:
        label = "冷"
    return (
        '<div class="heat-meter">'
        f'<div class="heat-number">{score:.0f}<span>/100</span></div>'
        '<div class="heat-track">'
        f'<div class="heat-fill" style="width:{score:.1f}%"></div>'
        "</div>"
        f'<div class="heat-label">{esc(label)}</div>'
        "</div>"
    )


def render_breadth_chart(snapshot: dict[str, Any]) -> str:
    counts = breadth_counts(snapshot)
    if counts is None:
        return '<div class="empty-state">涨跌家数缺失，无法绘制市场宽度。</div>'
    rising, falling, flat, missing = counts
    total = max(rising + falling + flat + missing, 1)

    def piece(label: str, value: int, cls: str) -> str:
        if value <= 0:
            return ""
        width = value / total * 100
        return (
            f'<span class="breadth-piece {cls}" style="width:{width:.2f}%" '
            f'title="{esc(label)} {format_int(value)}"></span>'
        )

    ratio = breadth_ratio(snapshot, allow_partial=True)
    ratio_text = "-" if ratio is None else f"{ratio * 100:.0f}%"
    partial = " · 部分样本" if (snapshot.get("breadth") or {}).get("is_partial") else ""
    partial_text = esc(partial) if partial else ""
    return (
        '<div class="breadth-chart">'
        '<div class="breadth-bar">'
        f'{piece("上涨", rising, "rise")}{piece("下跌", falling, "fall")}'
        f'{piece("平盘", flat, "flat")}{piece("停牌/缺失", missing, "missing")}'
        "</div>"
        '<div class="breadth-legend">'
        f'<span><b class="dot rise"></b>上涨 {format_int(rising)}</span>'
        f'<span><b class="dot fall"></b>下跌 {format_int(falling)}</span>'
        f'<span><b class="dot flat"></b>平盘 {format_int(flat)}</span>'
        f'<span><b class="dot missing"></b>缺失 {format_int(missing)}</span>'
        f'<strong>上涨占比 {esc(ratio_text)}{partial_text}</strong>'
        "</div>"
        "</div>"
    )


def render_index_change_bars(snapshot: dict[str, Any]) -> str:
    items = []
    for item in snapshot.get("indexes", []):
        try:
            change = float(item.get("change_pct"))
        except (TypeError, ValueError):
            continue
        items.append((item, change))
    if not items:
        return '<div class="empty-state">主要指数涨跌幅缺失。</div>'
    max_abs = max(max(abs(change) for _, change in items), 1.0)
    rows = []
    for item, change in items:
        width = min(abs(change) / max_abs * 50, 50)
        side_class = "positive" if change >= 0 else "negative"
        style = f"left:50%;width:{width:.2f}%" if change >= 0 else f"right:50%;width:{width:.2f}%"
        rows.append(
            '<div class="bar-row">'
            f'<div class="bar-name">{esc(item.get("name"))}</div>'
            '<div class="bar-track diverging"><span class="axis"></span>'
            f'<span class="bar-fill {side_class}" style="{style}"></span></div>'
            f'<div class="bar-value {pct_class(change)}">{esc(format_pct(change))}</div>'
            "</div>"
        )
    return "\n".join(rows)


def render_rank_bars(items: list[dict[str, Any]], empty_text: str, limit: int = 6) -> str:
    parsed = []
    for item in items[:limit]:
        try:
            change = float(change_value(item))
        except (TypeError, ValueError):
            continue
        parsed.append((item, change))
    if not parsed:
        if not items:
            return f'<div class="empty-state">{esc(empty_text)}</div>'
        rows = []
        for item in items[:limit]:
            name = item.get("name")
            if not name:
                continue
            meta = item.get("driver_event") or item.get("leader") or item.get("source") or ""
            rows.append(
                '<div class="text-row">'
                f'<strong>{esc(name)}</strong>'
                f'<span>{esc(truncate(meta, 44))}</span>'
                "</div>"
            )
        return "\n".join(rows) if rows else f'<div class="empty-state">{esc(empty_text)}</div>'
    max_abs = max(max(abs(change) for _, change in parsed), 1.0)
    rows = []
    for item, change in parsed:
        width = min(abs(change) / max_abs * 100, 100)
        cls = "positive" if change >= 0 else "negative"
        rows.append(
            '<div class="rank-row">'
            f'<div class="rank-head"><span>{esc(item.get("name"))}</span>'
            f'<b class="{pct_class(change)}">{esc(format_pct(change))}</b></div>'
            '<div class="rank-track">'
            f'<span class="rank-fill {cls}" style="width:{width:.2f}%"></span>'
            "</div></div>"
        )
    return "\n".join(rows)


def render_index_detail_rows(snapshot: dict[str, Any]) -> str:
    rows = []
    for item in snapshot.get("indexes", []):
        change = item.get("change")
        pct = item.get("change_pct")
        rows.append(
            "<tr>"
            f"<td>{esc(item.get('name'))}</td>"
            f"<td>{esc(item.get('code'))}</td>"
            f"<td>{esc(format_number(item.get('close')))}</td>"
            f"<td class=\"{pct_class(change)}\">{esc(format_number(change))}</td>"
            f"<td class=\"{pct_class(pct)}\">{esc(format_pct(pct))}</td>"
            f"<td>{esc(format_number(item.get('volume'), 0))}</td>"
            f"<td>{esc(format_number(item.get('amount'), 0))}</td>"
            f"<td>{esc(item.get('source'))}</td>"
            "</tr>"
        )
    if not rows:
        return '<tr><td colspan="8">指数明细缺失。</td></tr>'
    return "\n".join(rows)


def render_sector_detail_rows(items: list[dict[str, Any]], empty_text: str, limit: int = 20) -> str:
    rows = []
    for item in items[:limit]:
        change = change_value(item)
        up_down = "-"
        if item.get("rising_count") is not None or item.get("falling_count") is not None:
            up_down = f"{format_int(item.get('rising_count'))}/{format_int(item.get('falling_count'))}"
        rows.append(
            "<tr>"
            f"<td>{esc(item.get('name'))}</td>"
            f"<td class=\"{pct_class(change)}\">{esc(format_pct(change))}</td>"
            f"<td>{esc(format_number(item.get('amount')))}</td>"
            f"<td>{esc(up_down)}</td>"
            f"<td>{esc(item.get('leader'))}</td>"
            f"<td class=\"{pct_class(item.get('leader_change_pct'))}\">{esc(format_pct(item.get('leader_change_pct')))}</td>"
            f"<td>{esc(item.get('source'))}</td>"
            "</tr>"
        )
    if not rows:
        return f'<tr><td colspan="7">{esc(empty_text)}</td></tr>'
    return "\n".join(rows)


def render_theme_detail_rows(items: list[dict[str, Any]], empty_text: str, limit: int = 20) -> str:
    rows = []
    for item in items[:limit]:
        change = change_value(item)
        size = item.get("constituent_count")
        if size is None:
            size = item.get("turnover_rate")
        rows.append(
            "<tr>"
            f"<td>{esc(item.get('name'))}</td>"
            f"<td class=\"{pct_class(change)}\">{esc(format_pct(change))}</td>"
            f"<td>{esc(item.get('date'))}</td>"
            f"<td>{esc(item.get('leader'))}</td>"
            f"<td>{esc(size)}</td>"
            f"<td>{esc(truncate(item.get('driver_event'), 120))}</td>"
            f"<td>{esc(item.get('source'))}</td>"
            "</tr>"
        )
    if not rows:
        return f'<tr><td colspan="7">{esc(empty_text)}</td></tr>'
    return "\n".join(rows)


def metal_items(snapshot: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    metals = snapshot.get("metals") or {}
    sectors = [item for item in as_list(metals.get("sectors")) if isinstance(item, dict)]
    themes = [item for item in as_list(metals.get("themes")) if isinstance(item, dict)]
    if not sectors:
        sector_source = []
        sector_source.extend((snapshot.get("sectors") or {}).get("leading", []))
        sector_source.extend((snapshot.get("sectors") or {}).get("lagging", []))
        sectors = [item for item in sector_source if isinstance(item, dict) and is_metal_item(item)]
    if not themes:
        theme_source = []
        theme_source.extend((snapshot.get("themes") or {}).get("active", []))
        theme_source.extend((snapshot.get("themes") or {}).get("weak", []))
        themes = [item for item in theme_source if isinstance(item, dict) and is_metal_item(item)]
    return sectors[:12], themes[:12]


def metal_summary(snapshot: dict[str, Any]) -> str:
    sectors, themes = metal_items(snapshot)
    parts = []
    sector_names = leading_names(sectors, 5)
    theme_names = leading_names(themes, 5)
    if sector_names:
        parts.append("相关行业：" + "、".join(sector_names))
    if theme_names:
        parts.append("相关题材：" + "、".join(theme_names))
    if not parts:
        return "本次结构化快照未命中金银铜/有色金属相关行业或题材，需结合商品期货和行业页面进一步核对。"
    return "；".join(parts) + "。"


def render_data_quality_detail(snapshot: dict[str, Any], analysis: dict[str, Any]) -> str:
    items = data_quality_items(snapshot)
    source = source_note(snapshot, analysis)
    if source:
        items.insert(0, source)
    return list_items(items, "暂无额外数据质量说明。")


def turnover_text(snapshot: dict[str, Any]) -> tuple[str, str]:
    turnover = snapshot.get("turnover") or {}
    amount = format_amount_cny(turnover.get("amount_cny"))
    note = "全量待确认" if turnover.get("is_partial") else "来自快照数据"
    if amount == "-":
        note = "缺少成交额数据"
    return amount, note


def breadth_text(snapshot: dict[str, Any]) -> tuple[str, str]:
    breadth = snapshot.get("breadth") or {}
    rising = breadth.get("rising")
    falling = breadth.get("falling")
    if rising is None or falling is None:
        return "-", "缺少涨跌家数"
    note = "样本偏差" if breadth.get("is_partial") else "全量或接近全量"
    return f"{rising}/{falling}", note


def limit_text(snapshot: dict[str, Any]) -> tuple[str, str]:
    stats = snapshot.get("limit_stats") or {}
    up = stats.get("limit_up_count")
    down = stats.get("limit_down_count")
    if up is None and down is None:
        return "-", "缺少涨跌停数据"
    return f"{up if up is not None else '-'}/{down if down is not None else '-'}", "涨停/跌停"


def market_structure(snapshot: dict[str, Any]) -> str:
    avg = average_index_change(snapshot)
    ratio = breadth_ratio(snapshot)
    parts = []
    if avg is not None:
        parts.append(f"主要指数平均涨跌幅约 {avg:+.2f}%")
    if ratio is not None:
        parts.append(f"上涨占比约 {ratio * 100:.0f}%")
    if (snapshot.get("breadth") or {}).get("is_partial"):
        parts.append("宽度样本为部分数据，结构判断需谨慎")
    if not parts:
        return "市场结构数据不足，需要补充指数、涨跌家数、成交额和板块表现。"
    return "；".join(parts) + "。"


def theme_commentary(snapshot: dict[str, Any]) -> str:
    active = leading_names((snapshot.get("themes") or {}).get("active", []), 3)
    weak = leading_names((snapshot.get("themes") or {}).get("weak", []), 3)
    if not active and not weak:
        return "题材与板块数据不足，暂不判断主线持续性。"
    text = []
    if active:
        text.append("活跃方向：" + "、".join(active))
    if weak:
        text.append("弱势方向：" + "、".join(weak))
    drivers = []
    for item in (snapshot.get("themes") or {}).get("active", [])[:2]:
        driver = item.get("driver_event")
        name = item.get("name")
        if driver and name:
            drivers.append(f"{name}：{truncate(driver, 36)}")
    if drivers:
        text.append("事件线索：" + "；".join(drivers))
    return "；".join(text) + "。"


def data_quality_items(snapshot: dict[str, Any]) -> list[str]:
    items = [
        f"数据源：{', '.join(snapshot.get('sources') or ['无成功来源'])}",
        f"抓取时间：{snapshot.get('retrieved_at', '-')}",
    ]
    items.extend(snapshot.get("notes") or [])
    for error in snapshot.get("errors", [])[:5]:
        items.append(f"{error.get('source', 'source')}：{truncate(error.get('message', ''))}")
    return items


def default_tomorrow_items(snapshot: dict[str, Any]) -> list[str]:
    items = [
        "成交额能否放大并与指数方向一致。",
        "上涨/下跌家数能否改善，避免指数强而个股弱。",
        "今日活跃主题的前排能否继续强势，后排是否扩散。",
        "跌停数量、炸板和高位回撤是否继续恶化。",
    ]
    if not snapshot.get("indexes"):
        items.insert(0, "先补充主要指数收盘和涨跌幅，确认复盘基准。")
    return items


def build_context(snapshot: dict[str, Any], analysis: dict[str, Any]) -> dict[str, str]:
    temperature = analysis_value(analysis, "market_temperature") or infer_temperature(snapshot)
    sources = source_names(snapshot, analysis)
    turnover, turnover_note = turnover_text(snapshot)
    rising_falling, breadth_note = breadth_text(snapshot)
    limit_up_down, limit_note = limit_text(snapshot)
    risks = as_list(analysis_value(analysis, "risks")) or (snapshot.get("notes") or [])
    catalysts = as_list(analysis_value(analysis, "catalysts")) or [
        "暂无足够催化信息，需结合政策、宏观、海外市场和公告进一步归因。"
    ]
    tomorrow = as_list(analysis_value(analysis, "tomorrow_observations")) or default_tomorrow_items(snapshot)
    return {
        "date": esc(snapshot.get("date")),
        "retrieved_at": esc(snapshot.get("retrieved_at")),
        "sources": esc(", ".join(sources)),
        "data_mode": esc(infer_data_mode(snapshot, analysis)),
        "source_note": esc(source_note(snapshot, analysis)),
        "market_temperature": esc(temperature),
        "one_sentence_conclusion": esc(
            analysis_value(analysis, "one_sentence_conclusion")
            or default_conclusion(snapshot, temperature)
        ),
        "turnover": esc(turnover),
        "turnover_note": esc(turnover_note),
        "rising_falling": esc(rising_falling),
        "breadth_note": esc(breadth_note),
        "limit_up_down": esc(limit_up_down),
        "limit_note": esc(limit_note),
        "main_line_strength": esc(analysis_value(analysis, "main_line_strength", "待确认")),
        "main_line_note": esc(analysis_value(analysis, "main_line_note", "需结合持续性和扩散度")),
        "market_heat_meter": render_heat_meter(snapshot),
        "breadth_chart": render_breadth_chart(snapshot),
        "index_change_bars": render_index_change_bars(snapshot),
        "sector_leader_bars": render_rank_bars(
            (snapshot.get("sectors") or {}).get("leading", []), "行业领涨数据缺失。", limit=8
        ),
        "sector_lagger_bars": render_rank_bars(
            (snapshot.get("sectors") or {}).get("lagging", []), "行业领跌数据缺失。", limit=8
        ),
        "theme_leader_bars": render_rank_bars(
            (snapshot.get("themes") or {}).get("active", []), "活跃题材数据缺失。", limit=8
        ),
        "theme_lagger_bars": render_rank_bars(
            (snapshot.get("themes") or {}).get("weak", []), "弱势题材数据缺失。", limit=8
        ),
        "index_rows": render_index_rows(snapshot),
        "index_detail_rows": render_index_detail_rows(snapshot),
        "sector_leader_detail_rows": render_sector_detail_rows(
            (snapshot.get("sectors") or {}).get("leading", []), "行业领涨明细缺失。"
        ),
        "sector_lagger_detail_rows": render_sector_detail_rows(
            (snapshot.get("sectors") or {}).get("lagging", []), "行业领跌明细缺失。"
        ),
        "theme_leader_detail_rows": render_theme_detail_rows(
            (snapshot.get("themes") or {}).get("active", []), "活跃题材明细缺失。"
        ),
        "theme_lagger_detail_rows": render_theme_detail_rows(
            (snapshot.get("themes") or {}).get("weak", []), "弱势题材明细缺失。"
        ),
        "metal_summary": esc(metal_summary(snapshot)),
        "metal_sector_bars": render_rank_bars(
            metal_items(snapshot)[0], "未命中金银铜/有色相关行业。", limit=8
        ),
        "metal_theme_bars": render_rank_bars(
            metal_items(snapshot)[1], "未命中金银铜/有色相关题材。", limit=8
        ),
        "metal_sector_detail_rows": render_sector_detail_rows(
            metal_items(snapshot)[0], "未命中金银铜/有色相关行业。"
        ),
        "metal_theme_detail_rows": render_theme_detail_rows(
            metal_items(snapshot)[1], "未命中金银铜/有色相关题材。"
        ),
        "data_quality_detail_items": render_data_quality_detail(snapshot, analysis),
        "market_structure": esc(analysis_value(analysis, "market_structure") or market_structure(snapshot)),
        "theme_tags": render_theme_tags(snapshot),
        "theme_commentary": esc(analysis_value(analysis, "theme_commentary") or theme_commentary(snapshot)),
        "catalyst_items": list_items(catalysts, "暂无足够催化信息。"),
        "risk_items": list_items(risks, "暂无明显风险信号，但需继续观察。"),
        "tomorrow_items": list_items(tomorrow, "继续观察成交额、宽度、主线和风险扩散。"),
    }


def render_template(template: str, context: dict[str, str]) -> str:
    unknown = sorted(set(PLACEHOLDER_RE.findall(template)) - set(context))
    if unknown:
        raise ValueError("Template contains unsupported placeholders: " + ", ".join(unknown))

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        return context[key]

    return PLACEHOLDER_RE.sub(replace, template)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render a fixed HTML A-share close review report from snapshot JSON."
    )
    parser.add_argument("snapshot", type=Path, help="Snapshot JSON from collect_a_share_close.py.")
    parser.add_argument(
        "--analysis",
        type=Path,
        help="Optional analysis JSON with narrative fields overriding generated defaults.",
    )
    parser.add_argument(
        "--template",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "assets" / "close-report-template.html",
        help="HTML template path.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output HTML path. Defaults to reports/a-share-close-YYYY-MM-DD.html.",
    )
    parser.add_argument(
        "--date",
        type=validate_date,
        help="Override report date for output naming.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    snapshot = read_json(args.snapshot)
    analysis = read_json(args.analysis) if args.analysis else {}
    if args.date:
        snapshot["date"] = args.date
    report_date = snapshot.get("date") or dt.date.today().isoformat()
    output = args.output or Path(f"reports/a-share-close-{report_date}.html")
    template = args.template.read_text(encoding="utf-8")
    context = build_context(snapshot, analysis)
    html_text = render_template(template, context)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html_text, encoding="utf-8")
    print(str(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Collect a compact A-share morning brief seed from free public market data."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

DEFAULT_SYMBOLS = [
    {"symbol": "^GSPC", "name": "标普500", "bucket": "global", "area": "美股"},
    {"symbol": "^IXIC", "name": "纳斯达克", "bucket": "global", "area": "科技成长"},
    {"symbol": "^DJI", "name": "道琼斯", "bucket": "global", "area": "美股"},
    {"symbol": "^SOX", "name": "费城半导体", "bucket": "global", "area": "半导体"},
    {"symbol": "^HSI", "name": "恒生指数", "bucket": "global", "area": "港股"},
    {"symbol": "KWEB", "name": "中概互联网ETF", "bucket": "global", "area": "中概/平台经济"},
    {"symbol": "CNH=X", "name": "美元/离岸人民币", "bucket": "fx_rates", "area": "人民币"},
    {"symbol": "^TNX", "name": "美国10年期国债收益率", "bucket": "fx_rates", "area": "利率"},
    {"symbol": "GC=F", "name": "COMEX黄金", "bucket": "commodities", "area": "黄金"},
    {"symbol": "SI=F", "name": "COMEX白银", "bucket": "commodities", "area": "白银"},
    {"symbol": "CL=F", "name": "WTI原油", "bucket": "commodities", "area": "原油"},
    {"symbol": "HG=F", "name": "COMEX铜", "bucket": "commodities", "area": "有色金属"},
]


def now_local() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


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


def non_negative_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("value must be a non-negative integer") from exc
    if parsed < 0:
        raise argparse.ArgumentTypeError("value must be a non-negative integer")
    return parsed


def request_json(url: str, timeout: int, retries: int) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        if attempt:
            time.sleep(min(0.8 * attempt, 3.0))
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
            return json.loads(raw.decode("utf-8"))
        except Exception as exc:
            last_error = exc
    raise last_error or RuntimeError("request failed")


def yahoo_chart(symbol: str, timeout: int, retries: int) -> dict[str, Any]:
    encoded = urllib.parse.quote(symbol, safe="")
    last_error: Exception | None = None
    for host in ["query1.finance.yahoo.com", "query2.finance.yahoo.com"]:
        url = f"https://{host}/v8/finance/chart/{encoded}?range=5d&interval=1d"
        try:
            payload = request_json(url, timeout, retries)
            result = (payload.get("chart") or {}).get("result") or []
            if result:
                result[0].setdefault("_source_host", host)
                return result[0]
            error = (payload.get("chart") or {}).get("error")
            last_error = RuntimeError(str(error or "empty Yahoo chart result"))
        except Exception as exc:
            last_error = exc
    raise last_error or RuntimeError("empty Yahoo chart result")


def last_two(values: list[Any]) -> tuple[float | None, float | None]:
    numbers = []
    for value in values:
        if value is None:
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(number):
            numbers.append(number)
    if not numbers:
        return None, None
    if len(numbers) == 1:
        return numbers[-1], None
    return numbers[-1], numbers[-2]


def finite_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def parse_quote(symbol_info: dict[str, str], chart: dict[str, Any]) -> dict[str, Any]:
    meta = chart.get("meta") or {}
    quote = (((chart.get("indicators") or {}).get("quote") or [{}])[0]) or {}
    close, prior = last_two(quote.get("close") or [])
    price = meta.get("regularMarketPrice", close)
    previous = meta.get("chartPreviousClose", prior)
    price_float = finite_float(price)
    if price_float is None:
        price_float = close
    previous_float = finite_float(previous)
    if previous_float is None:
        previous_float = prior

    change = None
    pct = None
    if price_float is not None and previous_float not in (None, 0):
        change = price_float - previous_float
        pct = change / previous_float * 100

    return {
        **symbol_info,
        "price": price_float,
        "previous": previous_float,
        "change": change,
        "pct": pct,
        "currency": meta.get("currency"),
        "exchange": meta.get("exchangeName") or meta.get("fullExchangeName"),
        "source": chart.get("_source_host") or "Yahoo Finance chart endpoint",
        "source_time": meta.get("regularMarketTime"),
    }


def format_pct(value: Any) -> str:
    number = finite_float(value)
    if number is None:
        return "涨跌幅待确认"
    return f"{number:+.2f}%"


def direction_word(value: Any) -> str:
    number = finite_float(value)
    if number is None:
        return "待确认"
    if number > 0.15:
        return "上涨"
    if number < -0.15:
        return "下跌"
    return "小幅波动"


def quote_sentence(item: dict[str, Any]) -> str:
    pct = item.get("pct")
    if pct is None:
        return f"{item['name']}最新方向待确认。"
    return f"{item['name']}{direction_word(pct)}{format_pct(pct)}。"


def collect_quotes(symbols: list[dict[str, str]], timeout: int, retries: int) -> tuple[list[dict[str, Any]], list[str]]:
    quotes = []
    errors = []
    for symbol_info in symbols:
        try:
            quotes.append(parse_quote(symbol_info, yahoo_chart(symbol_info["symbol"], timeout, retries)))
        except Exception as exc:
            errors.append(f"{symbol_info['name']}({symbol_info['symbol']}): {exc}")
    return quotes, errors


def pct_by_symbol(quotes: list[dict[str, Any]], symbol: str) -> float | None:
    for quote in quotes:
        if quote.get("symbol") == symbol:
            return finite_float(quote.get("pct"))
    return None


def tone_from_quotes(quotes: list[dict[str, Any]]) -> str:
    risk_score = 0
    for symbol, weight in [("^GSPC", 1), ("^IXIC", 1), ("^SOX", 1), ("^HSI", 1), ("KWEB", 1)]:
        pct = pct_by_symbol(quotes, symbol)
        if pct is None:
            continue
        if pct > 0.4:
            risk_score += weight
        elif pct < -0.4:
            risk_score -= weight

    usdcnh = pct_by_symbol(quotes, "CNH=X")
    if usdcnh is not None:
        if usdcnh > 0.25:
            risk_score -= 1
        elif usdcnh < -0.25:
            risk_score += 1

    if risk_score >= 3:
        return "risk-on"
    if risk_score <= -3:
        return "risk-off"
    if risk_score in {1, 2}:
        return "constructive"
    if risk_score in {-1, -2}:
        return "mixed"
    return "neutral"


def impact_paths(quotes: list[dict[str, Any]]) -> list[dict[str, str]]:
    paths: list[dict[str, str]] = []

    nasdaq = pct_by_symbol(quotes, "^IXIC")
    sox = pct_by_symbol(quotes, "^SOX")
    if nasdaq is not None or sox is not None:
        tech_text = ", ".join(
            text
            for text in [
                f"纳指{format_pct(nasdaq)}" if nasdaq is not None else "",
                f"费半{format_pct(sox)}" if sox is not None else "",
            ]
            if text
        )
        paths.append(
            {
                "event": f"隔夜科技资产表现：{tech_text}",
                "impact": "可能影响A股成长风格和高弹性主题开盘情绪",
                "areas": "AI、半导体、算力、科创50、创业板",
                "confirmation": "观察科技前排是否高开后继续扩散，科创/创业板是否强于主板",
            }
        )

    hsi = pct_by_symbol(quotes, "^HSI")
    kweb = pct_by_symbol(quotes, "KWEB")
    if hsi is not None or kweb is not None:
        paths.append(
            {
                "event": "港股/中概线索变化",
                "impact": "可能影响A股互联网映射、消费和外资风险偏好",
                "areas": "港股映射、平台经济、消费、券商",
                "confirmation": "观察恒生科技、人民币和A股大盘权重是否同向",
            }
        )

    usdcnh = pct_by_symbol(quotes, "CNH=X")
    if usdcnh is not None:
        direction = "走弱" if usdcnh > 0 else "走强"
        paths.append(
            {
                "event": f"离岸人民币相对美元{direction}（美元/离岸人民币{format_pct(usdcnh)}）",
                "impact": "可能影响外资线索、风险偏好和大盘权重估值",
                "areas": "大盘蓝筹、金融、消费、外资重仓方向",
                "confirmation": "观察开盘后人民币、港股和沪深300是否形成共振",
            }
        )

    copper = pct_by_symbol(quotes, "HG=F")
    oil = pct_by_symbol(quotes, "CL=F")
    gold = pct_by_symbol(quotes, "GC=F")
    silver = pct_by_symbol(quotes, "SI=F")
    commodity_bits = [
        f"黄金{format_pct(gold)}" if gold is not None else "",
        f"白银{format_pct(silver)}" if silver is not None else "",
        f"铜{format_pct(copper)}" if copper is not None else "",
        f"原油{format_pct(oil)}" if oil is not None else "",
    ]
    commodity_text = ", ".join(bit for bit in commodity_bits if bit)
    if commodity_text:
        paths.append(
            {
                "event": f"大宗商品线索：{commodity_text}",
                "impact": "可能影响资源品、防御资产和通胀交易方向",
                "areas": "贵金属、有色金属、铜、石油石化、周期股",
                "confirmation": "观察黄金、白银、铜和有色金属方向是否有量价确认，贵金属是否与避险情绪共振",
            }
        )

    return paths


def build_brief(date: str, quotes: list[dict[str, Any]], errors: list[str]) -> dict[str, Any]:
    groups: dict[str, list[str]] = {"global": [], "fx_rates": [], "commodities": []}
    for quote in quotes:
        groups.setdefault(quote["bucket"], []).append(quote_sentence(quote))

    tone = tone_from_quotes(quotes)
    source_note = "Yahoo Finance chart endpoint; public data may be delayed and should be cross-checked for exact prices."
    data_quality = [source_note]
    if errors:
        data_quality.append("未取到的数据：" + "; ".join(errors[:8]))

    return {
        "date": date,
        "time_window": "上一交易日A股收盘后至今日开盘前",
        "retrieved_at": now_local(),
        "sources": ["Yahoo Finance public chart endpoint"] if quotes else [],
        "overall_tone": tone,
        "one_sentence_overview": f"隔夜公开市场线索显示盘前环境暂定为{tone}，仍需用开盘强弱、成交额和主线扩散验证。",
        "global_markets": groups.get("global") or ["隔夜全球市场数据未能自动获取。"],
        "macro_policy": [
            "国内政策、监管和公司公告需结合官方来源继续核验；本脚本只生成市场价格线索。"
        ],
        "industry_catalysts": groups.get("commodities") or ["产业催化需补充官方新闻、行业公告和可信媒体来源。"],
        "company_signals": ["暂无自动采集的公司级线索；重要公告优先核验CNINFO、交易所和公司公告。"],
        "impact_paths": impact_paths(quotes),
        "watchlist": [
            "观察开盘强弱，以及高开低走或低开修复是否出现。",
            "观察人民币、港股、中概和A股权重是否共振。",
            "观察科技成长或资源品线索是否在第一小时扩散。",
            "观察黄金、白银、铜和有色金属板块是否跟随外盘商品线索。",
            "观察成交额是否支持风险偏好修复。",
        ],
        "risks": [
            "若隔夜利好方向开盘后快速回落，说明资金认可度不足。",
            "若人民币、港股和A股权重背离，降低对单一海外线索的解释权重。",
            "若政策或公告出现盘中超预期变化，需重新校准盘前假设。",
        ],
        "data_quality": data_quality,
        "raw_quotes": quotes,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect a compact A-share morning brief JSON seed from free public market data."
    )
    parser.add_argument("--date", type=validate_date, default=today(), help="Brief date, YYYY-MM-DD.")
    parser.add_argument(
        "--output",
        type=Path,
        help="Output JSON path. Defaults to data/morning-brief-YYYY-MM-DD.json.",
    )
    parser.add_argument("--timeout", type=positive_int, default=12, help="HTTP timeout seconds.")
    parser.add_argument("--retries", type=non_negative_int, default=1, help="Retries per request.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = args.output or Path(f"data/morning-brief-{args.date}.json")
    quotes, errors = collect_quotes(DEFAULT_SYMBOLS, args.timeout, args.retries)
    brief = build_brief(args.date, quotes, errors)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(output))
    return 0


if __name__ == "__main__":
    sys.exit(main())

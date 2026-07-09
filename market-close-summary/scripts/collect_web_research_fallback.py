#!/usr/bin/env python3
"""Collect web-search evidence for an A-share close review fallback.

The output is an evidence bundle for an agent/LLM to read. It is not verified
market data and should not be treated as a data vendor feed.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import time
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.6",
}


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


def non_negative_float(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("value must be a non-negative number") from exc
    if parsed < 0:
        raise argparse.ArgumentTypeError("value must be a non-negative number")
    return parsed


def chinese_date(value: str, include_year: bool = True) -> str:
    parsed = dt.date.fromisoformat(value)
    if include_year:
        return f"{parsed.year}年{parsed.month}月{parsed.day}日"
    return f"{parsed.month}月{parsed.day}日"


def default_queries(date: str) -> list[dict[str, str]]:
    full = chinese_date(date)
    short = chinese_date(date, include_year=False)
    return [
        {
            "purpose": "market_facts",
            "query": f"{full} A股 收盘 上证指数 成交额 涨跌家数",
        },
        {
            "purpose": "close_review",
            "query": f"{full} A股 收评 板块 题材 涨停 跌停",
        },
        {
            "purpose": "turnover_breadth",
            "query": f"{full} 沪深两市 成交额 上涨家数 下跌家数",
        },
        {
            "purpose": "sector_theme",
            "query": f"{full} 东方财富 A股 板块涨幅 概念涨幅",
        },
        {
            "purpose": "media_catalyst",
            "query": f"{full} 财联社 A股收评 主线 题材",
        },
        {
            "purpose": "policy_macro",
            "query": f"{full} 证监会 央行 发改委 政策 A股",
        },
        {
            "purpose": "fresh_indexing",
            "query": f"{short} A股 收盘 收评 成交额 板块",
        },
    ]


def query_item_from_arg(value: str) -> dict[str, str]:
    if "::" in value:
        purpose, query = value.split("::", 1)
        purpose = purpose.strip() or "custom"
        query = query.strip()
        if query:
            return {"purpose": purpose, "query": query}
    return {"purpose": "custom", "query": value}


def request_text(url: str, timeout: int, retries: int) -> str:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        if attempt:
            time.sleep(min(0.8 * attempt, 3.0))
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
                content_type = resp.headers.get("content-type", "")
            encoding = "utf-8"
            match = re.search(r"charset=([\w-]+)", content_type, re.I)
            if match:
                encoding = match.group(1)
            for candidate in [encoding, "utf-8", "gb18030"]:
                try:
                    return raw.decode(candidate, errors="strict")
                except (LookupError, UnicodeDecodeError):
                    continue
            return raw.decode("utf-8", errors="replace")
        except Exception as exc:
            last_error = exc
    raise last_error or RuntimeError("request failed")


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def decode_ddg_url(value: str) -> str:
    parsed = urllib.parse.urlparse(value)
    query = urllib.parse.parse_qs(parsed.query)
    if "uddg" in query and query["uddg"]:
        return query["uddg"][0]
    return value


class DuckDuckGoHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.results: list[dict[str, str]] = []
        self.current: dict[str, str] | None = None
        self.capture: str | None = None
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {key: value or "" for key, value in attrs}
        classes = attr.get("class", "")
        if tag == "a" and "result__a" in classes:
            self._flush_result()
            self.current = {"title": "", "url": decode_ddg_url(attr.get("href", "")), "snippet": ""}
            self.capture = "title"
            self.parts = []
            return
        if "result__snippet" in classes and self.current is not None:
            self.capture = "snippet"
            self.parts = []

    def handle_data(self, data: str) -> None:
        if self.capture:
            self.parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self.capture == "title" and tag == "a" and self.current is not None:
            self.current["title"] = normalize_text("".join(self.parts))
            self.capture = None
            self.parts = []
        elif self.capture == "snippet" and tag in {"a", "div"} and self.current is not None:
            self.current["snippet"] = normalize_text("".join(self.parts))
            self.capture = None
            self.parts = []

    def close(self) -> None:
        super().close()
        self._flush_result()

    def _flush_result(self) -> None:
        if self.current and (self.current.get("title") or self.current.get("url")):
            self.results.append(self.current)
        self.current = None
        self.capture = None
        self.parts = []


def search_duckduckgo(query: str, timeout: int, retries: int, max_results: int) -> list[dict[str, str]]:
    url = "https://duckduckgo.com/html/?" + urllib.parse.urlencode(
        {"q": query, "kl": "cn-zh"}
    )
    text = request_text(url, timeout, retries)
    parser = DuckDuckGoHTMLParser()
    parser.feed(text)
    parser.close()
    return parser.results[:max_results]


def strip_html_to_text(value: str, limit: int) -> dict[str, str]:
    title_match = re.search(r"<title[^>]*>(.*?)</title>", value, re.I | re.S)
    title = normalize_text(title_match.group(1)) if title_match else ""
    meta_match = re.search(
        r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']',
        value,
        re.I | re.S,
    )
    description = normalize_text(meta_match.group(1)) if meta_match else ""
    cleaned = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", value, flags=re.I | re.S)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    text = normalize_text(cleaned)
    if len(text) > limit:
        text = text[: limit - 1].rstrip() + "..."
    return {"title": title, "description": description, "excerpt": text}


def fetch_page_summary(url: str, timeout: int, retries: int, limit: int) -> dict[str, str]:
    text = request_text(url, timeout, retries)
    return strip_html_to_text(text, limit)


def source_label(url: str, title: str) -> str:
    host = urllib.parse.urlparse(url).netloc.lower()
    host = host[4:] if host.startswith("www.") else host
    if "eastmoney" in host:
        return "东方财富"
    if "cls.cn" in host or "cailianpress" in host:
        return "财联社"
    if "10jqka" in host or "ths" in host:
        return "同花顺"
    if "sina" in host:
        return "新浪财经"
    if "qq.com" in host:
        return "腾讯财经"
    if "cninfo" in host:
        return "巨潮资讯"
    if "sse.com.cn" in host:
        return "上交所"
    if "szse.cn" in host:
        return "深交所"
    if host:
        return host
    return title[:24] or "公开网页"


def unique_sources(results: list[dict[str, Any]], limit: int = 8) -> list[str]:
    names: list[str] = []
    for item in results:
        label = source_label(str(item.get("url") or ""), str(item.get("title") or ""))
        if label and label not in names:
            names.append(label)
        if len(names) >= limit:
            break
    return names


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect web-search evidence for an A-share market close fallback."
    )
    parser.add_argument("--date", type=validate_date, default=today(), help="Trading date, YYYY-MM-DD.")
    parser.add_argument(
        "--output",
        help="Output JSON path. Defaults to data/a-share-close-web-YYYY-MM-DD.json.",
    )
    parser.add_argument(
        "--analysis-output",
        help="Optional path for a minimal analysis JSON seed accepted by render_close_report.py.",
    )
    parser.add_argument(
        "--query",
        action="append",
        default=[],
        help="Additional search query. Can be passed multiple times. Use purpose::query to tag results.",
    )
    parser.add_argument(
        "--no-default-queries",
        action="store_true",
        help="Use only explicitly supplied --query values.",
    )
    parser.add_argument("--max-results", type=positive_int, default=5, help="Results per query.")
    parser.add_argument("--timeout", type=positive_int, default=12, help="HTTP timeout seconds.")
    parser.add_argument("--retries", type=non_negative_int, default=1, help="Retries per request.")
    parser.add_argument("--delay", type=non_negative_float, default=0.8, help="Delay between queries.")
    parser.add_argument(
        "--fetch-pages-per-query",
        type=non_negative_int,
        default=0,
        help="Fetch and summarize the first N result pages for each query. Defaults to 0.",
    )
    parser.add_argument(
        "--page-excerpt-chars",
        type=positive_int,
        default=1000,
        help="Maximum characters for fetched page excerpts.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = Path(args.output or f"data/a-share-close-web-{args.date}.json")
    query_items = [] if args.no_default_queries else default_queries(args.date)
    query_items.extend(query_item_from_arg(query) for query in args.query)
    evidence: dict[str, Any] = {
        "date": args.date,
        "retrieved_at": now_local(),
        "data_mode": "搜索补足",
        "search_engine": "DuckDuckGo HTML",
        "queries": [],
        "results": [],
        "errors": [],
        "notes": [
            "This file contains web-search evidence for LLM synthesis, not verified market data.",
            "Cross-check exact index, turnover, breadth, and limit-up/down figures before using them as facts.",
        ],
    }
    seen_urls: set[str] = set()
    for index, item in enumerate(query_items):
        if index:
            time.sleep(args.delay)
        query = item["query"]
        entry: dict[str, Any] = {"purpose": item["purpose"], "query": query, "results": []}
        try:
            results = search_duckduckgo(query, args.timeout, args.retries, args.max_results)
            for result_index, result in enumerate(results):
                result["purpose"] = item["purpose"]
                if args.fetch_pages_per_query and result_index < args.fetch_pages_per_query:
                    try:
                        result["page_summary"] = fetch_page_summary(
                            result.get("url", ""),
                            args.timeout,
                            args.retries,
                            args.page_excerpt_chars,
                        )
                    except Exception as exc:
                        result["page_error"] = str(exc)
                entry["results"].append(result)
                url = result.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    evidence["results"].append(result)
        except Exception as exc:
            error = {"purpose": item["purpose"], "query": query, "message": str(exc)}
            entry["error"] = str(exc)
            evidence["errors"].append(error)
        evidence["queries"].append(entry)
    sources = unique_sources(evidence["results"])
    evidence["analysis_seed"] = {
        "data_mode": "搜索补足",
        "sources": sources or ["公开网页搜索"],
        "source_note": "结构化行情不完整时的公开网页检索证据；精确行情数字仍需交叉验证。",
        "main_line_strength": "待确认",
        "main_line_note": "搜索补足，需结合完整宽度与成交验证",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.analysis_output:
        analysis_output = Path(args.analysis_output)
        analysis_output.parent.mkdir(parents=True, exist_ok=True)
        analysis_output.write_text(
            json.dumps(evidence["analysis_seed"], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    print(str(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

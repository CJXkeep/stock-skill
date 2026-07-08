#!/usr/bin/env python3
"""Collect a compact A-share market-close snapshot from free sources.

The script prefers optional AkShare data when available, then falls back to
Eastmoney public endpoints. It writes a normalized JSON file intended to be
fed into the market-close-summary skill.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


EASTMONEY_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Referer": "https://quote.eastmoney.com/",
}

INDEX_SECIDS = {
    "000001": "上证指数",
    "399001": "深证成指",
    "399006": "创业板指",
    "000688": "科创50",
    "000300": "沪深300",
    "000905": "中证500",
    "000852": "中证1000",
}

CACHE_FILE_PREFIX = "a-share-close-"
CACHE_FILE_SUFFIX = ".json"


def now_local() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today() -> str:
    return dt.date.today().isoformat()


def yyyymmdd(value: str) -> str:
    return value.replace("-", "")


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


def optional_positive_int(value: str) -> int:
    return positive_int(value)


def safe_float(value: Any) -> float | None:
    if value in (None, "-", ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def request_json(url: str, timeout: int, retries: int) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        if attempt:
            time.sleep(min(0.5 * attempt, 2.0))
        try:
            return request_json_once(url, timeout)
        except Exception as exc:
            last_error = exc
    raise last_error or RuntimeError("request failed")


def request_json_once(url: str, timeout: int) -> dict[str, Any]:
    req = urllib.request.Request(url, headers=EASTMONEY_HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("response does not contain JSON object")
    return json.loads(raw[start : end + 1])


def em_url(path: str, params: dict[str, Any]) -> str:
    query = urllib.parse.urlencode(params)
    return f"https://push2.eastmoney.com/api/{path}?{query}"


def empty_snapshot(date: str) -> dict[str, Any]:
    return {
        "date": date,
        "retrieved_at": now_local(),
        "sources": [],
        "errors": [],
        "indexes": [],
        "turnover": {},
        "breadth": {},
        "limit_stats": {},
        "sectors": {"leading": [], "lagging": []},
        "themes": {"active": [], "weak": []},
        "flows": {},
        "intraday_notes": [],
        "catalysts": [],
        "notes": [],
    }


def add_source(snapshot: dict[str, Any], source: str) -> None:
    if source not in snapshot["sources"]:
        snapshot["sources"].append(source)


def add_error(snapshot: dict[str, Any], source: str, exc: Exception) -> None:
    snapshot["errors"].append({"source": source, "message": str(exc)})


def eastmoney_clist(
    *,
    page: int,
    page_size: int,
    sort_field: str,
    sort_order: int,
    fs: str,
    fields: str,
    timeout: int,
    retries: int,
) -> dict[str, Any]:
    url = em_url(
        "qt/clist/get",
        {
            "pn": page,
            "pz": page_size,
            "po": sort_order,
            "np": 1,
            "fltt": 2,
            "invt": 2,
            "fid": sort_field,
            "fs": fs,
            "fields": fields,
        },
    )
    return request_json(url, timeout, retries)


def collect_eastmoney_indexes(
    snapshot: dict[str, Any], timeout: int, retries: int
) -> None:
    secids = "1.000001,0.399001,0.399006,1.000688,1.000300,1.000905,1.000852"
    url = em_url(
        "qt/ulist.np/get",
        {
            "fltt": 2,
            "invt": 2,
            "fields": "f12,f13,f14,f2,f3,f4,f5,f6,f17,f18",
            "secids": secids,
        },
    )
    data = request_json(url, timeout, retries)
    rows = ((data.get("data") or {}).get("diff") or [])
    indexes = []
    for row in rows:
        code = str(row.get("f12") or "")
        indexes.append(
            {
                "code": code,
                "name": INDEX_SECIDS.get(code, row.get("f14")),
                "close": safe_float(row.get("f2")),
                "change_pct": safe_float(row.get("f3")),
                "change": safe_float(row.get("f4")),
                "volume": safe_float(row.get("f5")),
                "amount": safe_float(row.get("f6")),
                "open": safe_float(row.get("f17")),
                "previous_close": safe_float(row.get("f18")),
                "source": "Eastmoney",
            }
        )
    if not indexes:
        raise ValueError("Eastmoney index endpoint returned no rows")
    snapshot["indexes"] = indexes
    add_source(snapshot, "Eastmoney")


def collect_eastmoney_a_stock_breadth(
    snapshot: dict[str, Any],
    timeout: int,
    retries: int,
    max_stocks: int,
    page_delay: float,
) -> None:
    fs = "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048"
    fields = "f12,f14,f2,f3,f6"
    page_size = min(max(max_stocks, 1), 1000)
    rows: list[dict[str, Any]] = []
    total_universe_count: int | None = None
    page = 1

    while len(rows) < max_stocks:
        data = eastmoney_clist(
            page=page,
            page_size=page_size,
            sort_field="f3",
            sort_order=1,
            fs=fs,
            fields=fields,
            timeout=timeout,
            retries=retries,
        )
        payload = data.get("data") or {}
        page_rows = payload.get("diff") or []
        if total_universe_count is None:
            total_number = safe_float(payload.get("total"))
            total_universe_count = int(total_number) if total_number is not None else None
        if not page_rows:
            break
        rows.extend(page_rows)
        target_count = min(total_universe_count or max_stocks, max_stocks)
        if len(rows) >= target_count:
            break
        if total_universe_count is None and len(page_rows) < page_size:
            break
        page += 1
        if page_delay:
            time.sleep(page_delay)

    rows = rows[:max_stocks]
    rising = falling = flat = suspended = 0
    total_amount = 0.0
    amount_count = 0
    for row in rows:
        pct = safe_float(row.get("f3"))
        amount = safe_float(row.get("f6"))
        if pct is None:
            suspended += 1
        elif pct > 0:
            rising += 1
        elif pct < 0:
            falling += 1
        else:
            flat += 1
        if amount is not None:
            total_amount += amount
            amount_count += 1

    is_partial = (
        total_universe_count is not None and len(rows) < total_universe_count
    ) or (total_universe_count is None and len(rows) >= max_stocks)
    snapshot["breadth"] = {
        "rising": rising,
        "falling": falling,
        "flat": flat,
        "suspended_or_missing": suspended,
        "sample_size": len(rows),
        "total_universe_count": total_universe_count,
        "requested_count": max_stocks,
        "returned_count": len(rows),
        "is_partial": is_partial,
        "sample_bias": "sorted_by_change_pct_desc" if is_partial else None,
        "source": "Eastmoney",
    }
    snapshot["turnover"] = {
        "amount_cny": total_amount if amount_count else None,
        "stock_count_used": amount_count,
        "is_partial": is_partial,
        "source": "Eastmoney A-share spot aggregation",
        "note": "Approximate sum over fetched A-share spot rows; verify against exchange or vendor total when precision matters.",
    }
    add_source(snapshot, "Eastmoney")


def board_item(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "code": row.get("f12"),
        "name": row.get("f14"),
        "change_pct": safe_float(row.get("f3")),
        "turnover_rate": safe_float(row.get("f8")),
        "amount": safe_float(row.get("f6")),
        "source": "Eastmoney",
    }


def collect_eastmoney_boards(
    snapshot: dict[str, Any],
    timeout: int,
    retries: int,
    board_type: str,
    target_key: str,
) -> None:
    fs = "m:90+t:2" if board_type == "industry" else "m:90+t:3"
    data = eastmoney_clist(
        page=1,
        page_size=20,
        sort_field="f3",
        sort_order=1,
        fs=fs,
        fields="f12,f14,f3,f6,f8",
        timeout=timeout,
        retries=retries,
    )
    rows = ((data.get("data") or {}).get("diff") or [])
    leading = [board_item(row) for row in rows[:10]]

    lag_data = eastmoney_clist(
        page=1,
        page_size=10,
        sort_field="f3",
        sort_order=0,
        fs=fs,
        fields="f12,f14,f3,f6,f8",
        timeout=timeout,
        retries=retries,
    )
    lag_rows = ((lag_data.get("data") or {}).get("diff") or [])
    weak = [board_item(row) for row in lag_rows[:10]]

    target = snapshot[target_key]
    wrote = False
    if target_key == "sectors":
        if not target["leading"] and leading:
            target["leading"] = leading
            wrote = True
        if not target["lagging"] and weak:
            target["lagging"] = weak
            wrote = True
    else:
        if not target["active"] and leading:
            target["active"] = leading
            wrote = True
        if not target["weak"] and weak:
            target["weak"] = weak
            wrote = True
    if wrote:
        add_source(snapshot, "Eastmoney")


def df_records(df: Any) -> list[dict[str, Any]]:
    if hasattr(df, "to_dict"):
        return df.to_dict("records")
    return []


def first_existing(row: dict[str, Any], names: list[str]) -> Any:
    for name in names:
        if name in row:
            return row[name]
    return None


def collect_akshare(snapshot: dict[str, Any], date: str) -> None:
    try:
        import akshare as ak  # type: ignore
    except Exception as exc:
        raise RuntimeError(f"AkShare is not available: {exc}") from exc

    wrote = False

    try:
        if hasattr(ak, "stock_board_industry_name_em"):
            rows = df_records(ak.stock_board_industry_name_em())
            if rows:
                ordered = sorted(
                    rows,
                    key=lambda r: safe_float(first_existing(r, ["涨跌幅", "涨跌幅%"])) or 0,
                    reverse=True,
                )
                snapshot["sectors"]["leading"] = [
                    {
                        "name": first_existing(r, ["板块名称", "名称"]),
                        "change_pct": safe_float(first_existing(r, ["涨跌幅", "涨跌幅%"])),
                        "source": "AkShare/Eastmoney",
                    }
                    for r in ordered[:10]
                ]
                snapshot["sectors"]["lagging"] = [
                    {
                        "name": first_existing(r, ["板块名称", "名称"]),
                        "change_pct": safe_float(first_existing(r, ["涨跌幅", "涨跌幅%"])),
                        "source": "AkShare/Eastmoney",
                    }
                    for r in ordered[-10:][::-1]
                ]
                wrote = True
    except Exception as exc:
        add_error(snapshot, "AkShare industry boards", exc)

    try:
        if hasattr(ak, "stock_board_concept_name_em"):
            rows = df_records(ak.stock_board_concept_name_em())
            if rows:
                ordered = sorted(
                    rows,
                    key=lambda r: safe_float(first_existing(r, ["涨跌幅", "涨跌幅%"])) or 0,
                    reverse=True,
                )
                snapshot["themes"]["active"] = [
                    {
                        "name": first_existing(r, ["板块名称", "名称"]),
                        "change_pct": safe_float(first_existing(r, ["涨跌幅", "涨跌幅%"])),
                        "source": "AkShare/Eastmoney",
                    }
                    for r in ordered[:10]
                ]
                snapshot["themes"]["weak"] = [
                    {
                        "name": first_existing(r, ["板块名称", "名称"]),
                        "change_pct": safe_float(first_existing(r, ["涨跌幅", "涨跌幅%"])),
                        "source": "AkShare/Eastmoney",
                    }
                    for r in ordered[-10:][::-1]
                ]
                wrote = True
    except Exception as exc:
        add_error(snapshot, "AkShare concept boards", exc)

    try:
        if hasattr(ak, "stock_zt_pool_em"):
            rows = df_records(ak.stock_zt_pool_em(date=yyyymmdd(date)))
            snapshot["limit_stats"]["limit_up_count"] = len(rows)
            snapshot["limit_stats"]["limit_up_source"] = "AkShare/Eastmoney stock_zt_pool_em"
            wrote = True
    except Exception as exc:
        add_error(snapshot, "AkShare limit-up pool", exc)

    try:
        if hasattr(ak, "stock_zt_pool_dtgc_em"):
            rows = df_records(ak.stock_zt_pool_dtgc_em(date=yyyymmdd(date)))
            snapshot["limit_stats"]["limit_down_count"] = len(rows)
            snapshot["limit_stats"]["limit_down_source"] = "AkShare/Eastmoney stock_zt_pool_dtgc_em"
            wrote = True
    except Exception as exc:
        add_error(snapshot, "AkShare limit-down pool", exc)

    if wrote:
        add_source(snapshot, "AkShare")


def write_json(snapshot: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def cache_file_date(path: Path) -> dt.date | None:
    name = path.name
    if not name.startswith(CACHE_FILE_PREFIX) or not name.endswith(CACHE_FILE_SUFFIX):
        return None
    date_part = name[len(CACHE_FILE_PREFIX) : -len(CACHE_FILE_SUFFIX)]
    try:
        return dt.date.fromisoformat(date_part)
    except ValueError:
        return None


def cache_files(output_dir: Path) -> list[tuple[dt.date, Path]]:
    if not output_dir.exists():
        return []
    files = []
    for path in output_dir.glob(f"{CACHE_FILE_PREFIX}*{CACHE_FILE_SUFFIX}"):
        parsed_date = cache_file_date(path)
        if parsed_date is not None and path.is_file():
            files.append((parsed_date, path))
    return files


def cleanup_cache(
    output_dir: Path,
    *,
    retention_days: int | None,
    max_cache_files: int | None,
    dry_run: bool,
) -> dict[str, Any]:
    candidates = cache_files(output_dir)
    to_delete: dict[Path, str] = {}

    if retention_days is not None:
        cutoff = dt.date.today() - dt.timedelta(days=retention_days)
        for file_date, path in candidates:
            if file_date < cutoff:
                to_delete[path] = f"older than {retention_days} days"

    if max_cache_files is not None:
        ordered = sorted(candidates, key=lambda item: item[0], reverse=True)
        for _, path in ordered[max_cache_files:]:
            to_delete.setdefault(path, f"exceeds max cache files {max_cache_files}")

    deleted = []
    for path, reason in sorted(to_delete.items(), key=lambda item: item[0].name):
        deleted.append({"path": str(path), "reason": reason})
        if not dry_run:
            path.unlink()

    return {
        "enabled": retention_days is not None or max_cache_files is not None,
        "dry_run": dry_run,
        "directory": str(output_dir),
        "matched_files": len(candidates),
        "deleted_count": 0 if dry_run else len(deleted),
        "would_delete_count": len(deleted) if dry_run else 0,
        "files": deleted,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect a normalized A-share market close snapshot from free sources."
    )
    parser.add_argument("--date", type=validate_date, default=today(), help="Trading date, YYYY-MM-DD.")
    parser.add_argument(
        "--output",
        help="Output JSON path. Defaults to data/a-share-close-YYYY-MM-DD.json.",
    )
    parser.add_argument(
        "--no-akshare",
        action="store_true",
        help="Skip optional AkShare collection and use public HTTP endpoints only.",
    )
    parser.add_argument("--timeout", type=positive_int, default=12, help="HTTP timeout seconds.")
    parser.add_argument(
        "--retries",
        type=non_negative_int,
        default=2,
        help="Retries per HTTP request after transient free-source failures.",
    )
    parser.add_argument(
        "--page-delay",
        type=non_negative_float,
        default=0.2,
        help="Seconds to wait between paged Eastmoney breadth requests.",
    )
    parser.add_argument(
        "--max-stocks",
        type=positive_int,
        default=6000,
        help="Maximum A-share rows to fetch from Eastmoney for breadth aggregation.",
    )
    parser.add_argument(
        "--retention-days",
        type=optional_positive_int,
        help="Delete cached a-share-close-YYYY-MM-DD.json files older than this many days.",
    )
    parser.add_argument(
        "--max-cache-files",
        type=optional_positive_int,
        help="Keep only the newest N cached a-share-close-YYYY-MM-DD.json files.",
    )
    parser.add_argument(
        "--dry-run-cleanup",
        action="store_true",
        help="Preview cache cleanup without deleting files.",
    )
    parser.add_argument(
        "--cleanup-only",
        action="store_true",
        help="Run cache cleanup and skip market data collection.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = Path(args.output or f"data/a-share-close-{args.date}.json")
    output_dir = output.parent

    if args.cleanup_only:
        summary = cleanup_cache(
            output_dir,
            retention_days=args.retention_days,
            max_cache_files=args.max_cache_files,
            dry_run=args.dry_run_cleanup,
        )
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0

    snapshot = empty_snapshot(args.date)

    if not args.no_akshare:
        try:
            collect_akshare(snapshot, args.date)
        except Exception as exc:
            add_error(snapshot, "AkShare", exc)

    for name, func in [
        (
            "Eastmoney indexes",
            lambda: collect_eastmoney_indexes(snapshot, args.timeout, args.retries),
        ),
        (
            "Eastmoney A-share breadth",
            lambda: collect_eastmoney_a_stock_breadth(
                snapshot, args.timeout, args.retries, args.max_stocks, args.page_delay
            ),
        ),
        (
            "Eastmoney industry boards",
            lambda: collect_eastmoney_boards(
                snapshot, args.timeout, args.retries, "industry", "sectors"
            ),
        ),
        (
            "Eastmoney concept boards",
            lambda: collect_eastmoney_boards(
                snapshot, args.timeout, args.retries, "concept", "themes"
            ),
        ),
    ]:
        try:
            func()
        except Exception as exc:
            add_error(snapshot, name, exc)

    if not snapshot["indexes"]:
        snapshot["notes"].append("Major index data missing; paste or verify index closes before writing a data-backed review.")
    if not snapshot["breadth"]:
        snapshot["notes"].append("Breadth data missing; avoid strong claims about overall market participation.")
    elif snapshot["breadth"].get("is_partial"):
        snapshot["notes"].append("Breadth and aggregated turnover are partial; verify against a total-market source before making strong participation claims.")
        if snapshot["breadth"].get("sample_bias"):
            snapshot["notes"].append("Partial breadth sample is sorted by change percentage and is not representative of the full market.")
    if "limit_down_count" not in snapshot["limit_stats"]:
        snapshot["notes"].append("Limit-down count missing; short-term sentiment assessment is incomplete.")
    if not snapshot["sectors"]["leading"] and not snapshot["themes"]["active"]:
        snapshot["notes"].append("Board/theme data missing; identify main lines manually from another free source.")

    write_json(snapshot, output)
    cleanup_summary = cleanup_cache(
        output_dir,
        retention_days=args.retention_days,
        max_cache_files=args.max_cache_files,
        dry_run=args.dry_run_cleanup,
    )
    if cleanup_summary["enabled"]:
        if output.exists():
            snapshot["cleanup"] = cleanup_summary
            write_json(snapshot, output)
        else:
            print(json.dumps(cleanup_summary, ensure_ascii=False, indent=2))
            return 0
    print(str(output))
    return 0


if __name__ == "__main__":
    sys.exit(main())

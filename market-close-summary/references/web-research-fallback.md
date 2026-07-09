# Web Research Fallback

Use this reference when structured market data is missing, stale, blocked, or too incomplete for a normal data-backed close review.

## Fallback Ladder

1. Run `scripts/collect_a_share_close.py` first when local execution is available.
2. If the snapshot is incomplete, run `scripts/collect_web_research_fallback.py --date YYYY-MM-DD` or search public web sources manually for the missing fields and catalysts.
3. Generate an LLM synthesis context with `scripts/prepare_llm_analysis_context.py` when both snapshot and web evidence are available.
4. If numeric market data is still missing, write a **news-informed narrative review** instead of a full data-backed review. Mark the report as `搜索补足` or `数据不足`, and keep hard numeric claims out of the conclusion.
5. If browsing/search is unavailable in the runtime, ask for pasted data using [a-share-close-framework.md](a-share-close-framework.md).

## Search Targets

Prefer sources that directly publish market facts:

- Major indexes and turnover: Eastmoney quote pages, Sina Finance, Tencent Finance, official exchange/index pages.
- Breadth and limit-up/down: Eastmoney market dashboards, 同花顺/财联社 summaries when public pages are accessible.
- Industry and concept performance: Eastmoney board pages, 同花顺 summaries, public financial portals.
- Catalysts: CSRC, PBOC, NDRC, MOF, MIIT, exchange announcements, CNINFO, company announcements, then reputable media summaries.
- Overseas context: major index closes, USD/CNH, CNY fixing, Treasury yields, commodities, Hong Kong market, offshore China assets.

Use media articles for narrative clues, not as the sole source for exact market-wide numbers unless the article explicitly cites them.

## Query Patterns

Use date-qualified Chinese queries. Examples:

```text
YYYY年M月D日 A股 收盘 上证指数 成交额 涨跌家数
YYYY年M月D日 A股 收评 板块 题材 涨停 跌停
YYYY年M月D日 沪深两市 成交额 上涨家数 下跌家数
YYYY年M月D日 东方财富 A股 板块涨幅 概念涨幅
YYYY年M月D日 财联社 A股收评 主线 题材
YYYY年M月D日 证监会 央行 发改委 政策 A股
```

For current-day post-close work, also search without the year if Chinese financial portals have not indexed the full date yet.

## Included Search Collector

Use the bundled script to produce a portable evidence bundle:

```bash
python market-close-summary/scripts/collect_web_research_fallback.py --date YYYY-MM-DD
```

It writes `data/a-share-close-web-YYYY-MM-DD.json` by default. The file contains query purposes, search result titles, snippets, URLs, errors, and an `analysis_seed` object with `data_mode`, source names, and conservative source notes.

Useful options:

```bash
python market-close-summary/scripts/collect_web_research_fallback.py --date YYYY-MM-DD --query "YYYY年M月D日 A股 机器人 创新药 收评"
python market-close-summary/scripts/collect_web_research_fallback.py --date YYYY-MM-DD --max-results 8
python market-close-summary/scripts/collect_web_research_fallback.py --date YYYY-MM-DD --fetch-pages-per-query 1
python market-close-summary/scripts/collect_web_research_fallback.py --date YYYY-MM-DD --analysis-output data/a-share-close-web-analysis-YYYY-MM-DD.json
```

Treat the search bundle as evidence for LLM synthesis, not as verified market data. If the search engine blocks or returns thin snippets, use the query list in the bundle as a manual browsing checklist.

## LLM Context Pack

After collecting structured data and/or search evidence, create a compact Markdown context for the LLM:

```bash
python market-close-summary/scripts/prepare_llm_analysis_context.py \
  --snapshot data/a-share-close-YYYY-MM-DD.json \
  --web-evidence data/a-share-close-web-YYYY-MM-DD.json \
  --output data/a-share-close-llm-context-YYYY-MM-DD.md
```

If one side is unavailable, omit that argument. The context pack includes:

- structured snapshot facts and gaps;
- web evidence snippets, URLs, and source names;
- a strict `analysis.json` output contract;
- guardrails against invented numbers.

Use this context to produce `analysis.json`, then render:

```bash
python market-close-summary/scripts/render_close_report.py \
  data/a-share-close-YYYY-MM-DD.json \
  --analysis data/a-share-close-analysis-YYYY-MM-DD.json
```

## Evidence Note

Before writing, make a compact evidence note:

```markdown
数据模式：结构化数据 / 搜索补足 / 数据不足
检索时间：
行情事实：
- 指数：
- 成交额：
- 涨跌家数：
- 涨停/跌停：
结构事实：
- 领涨行业/题材：
- 领跌行业/题材：
- 主线持续性证据：
催化线索：
- 政策/宏观：
- 产业/公司：
- 海外/商品/汇率/利率：
缺口与置信度：
- 缺口：
- 置信度：高 / 中 / 低
来源：
- 来源名 URL或页面标题
```

Use the evidence note to create the optional `analysis.json` fields accepted by `scripts/render_close_report.py`.

## LLM Synthesis Rules

- Use the LLM to organize language, causal hierarchy, and tomorrow's checklist; do not use it to invent missing market facts.
- Replace exact missing fields with qualitative wording such as `成交额需补充确认`, `宽度数据未完整取得`, or `题材线索主要来自媒体收评`.
- Separate fact and interpretation:
  - Fact: "媒体收评普遍提到机器人、创新药活跃。"
  - Interpretation: "这更像是事件驱动的结构轮动，主线强度仍需看明日扩散。"
- Use confidence language:
  - High: two or more independent sources agree on key facts.
  - Medium: one reliable source plus consistent cross-market/catalyst evidence.
  - Low: only media narrative is available, or numeric data conflicts.
- Include source names and retrieval time in `数据来源` or the HTML footer.

## Analysis JSON Additions

When search fills narrative gaps, create an analysis JSON like:

```json
{
  "data_mode": "搜索补足",
  "sources": ["东方财富行情中心", "财联社收评", "证监会公告"],
  "source_note": "结构化行情不完整，板块与催化线索来自公开网页检索。",
  "market_temperature": "中性震荡",
  "one_sentence_conclusion": "今日A股更像结构轮动而非全面进攻，结论需等待成交额和宽度数据交叉验证。",
  "market_structure": "指数层面缺少完整交叉验证，公开收评显示活跃方向集中在少数题材。",
  "theme_commentary": "题材线索以机器人、创新药等方向为主，但持续性需要明日前排强度和后排扩散确认。",
  "main_line_strength": "待确认",
  "main_line_note": "搜索补足，缺少完整宽度与成交验证",
  "catalysts": ["政策预期升温", "产业事件催化", "海外风险偏好扰动"],
  "risks": ["缺少完整涨跌家数", "题材扩散证据不足"],
  "tomorrow_observations": ["成交额能否放大并与指数方向一致", "活跃题材前排能否继续强势"]
}
```

Keep `sources` short. Put detailed URLs in the Markdown report or source note when useful.

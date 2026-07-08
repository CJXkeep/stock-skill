# Close Review Report Format

Use this reference when deciding the analysis dimensions or final report format for an A-share market close review.

## Recommended Analysis Dimensions

Keep the daily review stable across days. Use these dimensions in this order:

1. **Market temperature**
   State the day's overall environment: 强势进攻, 修复偏强, 中性震荡, 偏弱防守, or 风险释放.

2. **Index, breadth, and liquidity**
   Compare major index moves with rising/falling stocks, turnover, limit-up/limit-down counts, and whether volume confirms the price move.

3. **Style and structure**
   Separate large-cap versus small/mid-cap, growth versus value, technology versus cyclical/consumer/financial, and main-board versus ChiNext/STAR behavior.

4. **Main line and rotation**
   Identify the leading themes, whether participation is broad, whether leadership persisted into the close, and whether weak themes show risk diffusion.

5. **Sentiment and risk**
   Track limit-up/limit-down, 连板高度,炸板, high-position drawdowns, index divergence, and crowding/positioning stress.

6. **Catalyst attribution**
   Attribute moves with evidence: policy, macro, overseas, commodity/rate/FX, earnings, announcements, or technical/positioning effects.

7. **Tomorrow's observation checklist**
   Convert the review into falsifiable points: turnover threshold, index confirmation/invalidation, theme continuation condition, and risk trigger.

8. **Data quality**
   State data sources, retrieval time, missing fields, partial samples, and cross-check needs.

## Format Recommendation

Use Markdown by default for chat, notes, version control, and long-form reasoning. Use HTML when the user wants a more visual daily report, browser viewing, screenshots, or repeated review archives.

Recommended workflow:

1. Draft the analysis in the fixed Markdown structure.
2. If the user wants a visual report, render the same content into `assets/close-report-template.html`.
3. Do not let HTML change the analytical logic; it is a presentation layer.
4. Use `scripts/render_close_report.py <snapshot.json>` to generate the HTML file. Pass `--analysis analysis.json` when narrative fields are available.

## Markdown Structure

```markdown
# A股收盘复盘｜YYYY-MM-DD

## 一句话结论

【市场温度】。核心判断：...

## 关键数据

| 指标 | 数值 | 解读 |
| --- | --- | --- |
| 上证指数 |  |  |
| 深证成指 |  |  |
| 创业板指 |  |  |
| 两市成交额 |  |  |
| 上涨/下跌家数 |  |  |
| 涨停/跌停 |  |  |

## 市场结构

- 指数与个股：
- 风格分化：
- 成交与流动性：

## 主线与轮动

- 主线：
- 辅线：
- 弱势方向：
- 是否有持续性：

## 异动归因

1. 
2. 
3. 

## 风险信号

- 
- 
- 

## 明日观察

1. 
2. 
3. 
4. 

## 操作环境

当前更适合【进攻/精选结构/防守/等待】。

## 数据质量

- 数据源：
- 抓取时间：
- 缺失字段：
- 需要交叉验证：
```

## HTML Structure

Use [assets/close-report-template.html](../assets/close-report-template.html) for a fixed visual report. Keep it static, self-contained, and printable. The HTML should include:

- top conclusion band;
- market temperature badge;
- key metrics grid;
- index table;
- structure and theme sections;
- risk and tomorrow checklist;
- data quality footer.

Prefer restrained dashboard styling. Avoid decorative landing-page composition; this report is a repeated work surface.

## Optional Analysis JSON

`scripts/render_close_report.py` can render a conservative data-only report from the snapshot alone. To override narrative fields, provide an analysis JSON:

```json
{
  "market_temperature": "偏弱防守",
  "one_sentence_conclusion": "指数承压且结构分化，明日重点看成交额和主线修复。",
  "market_structure": "权重护盘不足，小盘与高弹性方向承压更明显。",
  "theme_commentary": "活跃方向集中在防御和事件驱动，持续性仍需确认。",
  "main_line_strength": "弱",
  "main_line_note": "主线扩散不足",
  "catalysts": ["海外风险偏好回落", "高位题材补跌"],
  "risks": ["跌停数量上升", "成交放大但指数收弱"],
  "tomorrow_observations": ["成交额能否回到万亿以上", "创业板指能否止跌"]
}
```

The renderer uses strict template placeholders. If the HTML template contains a placeholder that the renderer does not know how to fill, rendering fails instead of silently emitting a blank field.

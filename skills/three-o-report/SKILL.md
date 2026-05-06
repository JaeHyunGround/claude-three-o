---
name: three-o-report
description: >
  Generates unified PDF/Markdown reports from Three-O audit results.
  Supports full (3-pillar), single-module (SEO/GEO/AAO), and comparison
  reports with charts and action plans.
  Use when user says "report", "리포트", "보고서", "PDF report",
  "PDF 보고서", "generate report", "리포트 생성".
user-invocable: true
argument-hint: "[full|seo|geo|aao] [--format <pdf|md|json>]"
license: proprietary
metadata:
  author: Jaehyun Ahn
  version: "1.0.0"
  category: three-o
---

# Three-O Report: Unified Report Generation

**Invocation:** `/three-o report [full|seo|geo|aao] [--format <pdf|md|json>]`

## Report Types

| Type | Content | Pages (est.) |
|------|---------|-------------|
| full | All 3 pillars + unified score | 15-25 |
| seo | SEO audit results only | 8-12 |
| geo | GEO analysis results only | 6-10 |
| aao | AAO audit results only | 6-10 |

## Output Formats

| Format | Description | Use Case |
|--------|-------------|----------|
| pdf | Full branded PDF with charts | Client delivery |
| md | Markdown document | Internal review |
| json | Structured data export | Dashboard integration |

## Report Sections (Full)

1. **Executive Summary** — Three-O Score, key findings, top 3 actions
2. **Score Dashboard** — Visual score breakdown per pillar
3. **SEO Analysis** — Technical, content, keywords, schema
4. **GEO Analysis** — Mentions, sentiment, citability, entity
5. **AAO Analysis** — Selectability, conversion, data, rendering
6. **Competitor Comparison** — If competitor data available
7. **Action Plan** — Priority-ordered recommendations with timeline
8. **Appendix** — Raw data, methodology notes

## Data Requirements

Report requires audit data from current session:
- If no audit run yet → prompt user to run audit first
- If partial data → generate partial report with gaps noted
- If full data → generate complete report

## Branding

| Element | Default | Customizable |
|---------|---------|-------------|
| Logo | Three-O logo | Client logo via --logo |
| Colors | Three-O palette | Custom palette via config |
| Header | "Three-O Audit Report" | Custom title via --title |
| Footer | Date + page number | Custom footer text |

## Chart Generation

Uses matplotlib for PDF charts:
- Radar chart: 3-pillar score overview
- Bar charts: dimension breakdowns
- Trend lines: if historical data available
- Gauge: overall Three-O Score

## Output

- PDF: saved to `./reports/[brand]-[date]-[type].pdf`
- MD: saved to `./reports/[brand]-[date]-[type].md`
- JSON: saved to `./reports/[brand]-[date]-[type].json`

## Reference Files

Load on-demand:
- `references/report-templates.md` — Section templates and formatting

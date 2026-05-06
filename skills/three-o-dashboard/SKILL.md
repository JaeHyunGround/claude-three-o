---
name: three-o-dashboard
description: >
  Exports Three-O audit and monitoring data in structured JSON format
  for dashboard consumption. Supports real-time score tracking,
  historical trends, and multi-brand comparison.
  Use when user says "dashboard", "대시보드", "data export",
  "데이터 내보내기", "JSON export", "모니터링 데이터".
user-invocable: true
argument-hint: "[--brands <list>] [--period <days>]"
license: proprietary
metadata:
  author: Jaehyun Ahn
  version: "1.0.0"
  category: three-o
---

# Three-O Dashboard: Data Export

**Invocation:** `/three-o dashboard [--brands <list>] [--period <days>]`

## Purpose

Exports structured data for external dashboard visualization.
Designed to feed into BI tools, custom dashboards, or the Three-O
web platform for ongoing monitoring and client reporting.

## Export Format

All exports in JSON with consistent schema:

```json
{
  "export_date": "2026-05-04T12:00:00Z",
  "version": "1.0.0",
  "brands": [...],
  "scores": {...},
  "trends": [...],
  "alerts": [...]
}
```

## Data Sections

### 1. Current Scores
Latest Three-O scores per brand:
- Overall Three-O Score
- Per-pillar scores (SEO, GEO, AAO)
- Per-dimension scores (33 dimensions)
- Per-platform scores (Google, Naver, ChatGPT, etc.)

### 2. Historical Trends
Score changes over time:
- Daily snapshots (if drift monitoring active)
- Weekly aggregates
- Monthly summaries
- Delta from previous period

### 3. Alerts
Active issues requiring attention:
- Critical score drops
- New competitor appearances
- Platform changes detected
- Expiring content/data

### 4. Action Items
Outstanding optimization tasks:
- Priority-ordered actions
- Status (pending/in-progress/done)
- Expected impact per action
- Assigned timeline

## Multi-Brand Support

For agencies managing multiple brands:
```json
{
  "brands": [
    {"name": "Brand A", "score": 78, "trend": "+3"},
    {"name": "Brand B", "score": 62, "trend": "-2"},
    {"name": "Brand C", "score": 85, "trend": "+1"}
  ]
}
```

## Integration Targets

| Platform | Format | Method |
|----------|--------|--------|
| Custom dashboard | JSON file | Local export |
| Google Sheets | CSV | Export + import |
| Notion | Markdown table | Copy-paste ready |
| Slack | Summary message | Webhook format |
| API endpoint | JSON | POST to configured URL |

## Output Options

| Flag | Effect |
|------|--------|
| --brands | Filter to specific brands |
| --period | Historical data range (days) |
| --format csv | Export as CSV instead of JSON |
| --webhook <url> | POST to external endpoint |
| --compact | Minimal data (scores only) |

## Output Format (Console)

```
Dashboard Export: [brand(s)]
━━━━━━━━━━━━━━━━━━━━━━━━━━
Brands: XX
Period: [start] → [end]

Current Scores:
  [brand]: XX/100 (SEO: XX | GEO: XX | AAO: XX) [trend]
  ...

Active Alerts: XX
  [alert description]
  ...

Exported to: ./exports/dashboard-[date].json
```

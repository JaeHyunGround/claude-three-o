---
name: geo-drift
description: >
  Monitors GEO score changes over time by comparing current mention
  data against stored baselines. Detects visibility gains, losses,
  and sentiment shifts across AI platforms.
  Use when user says "GEO drift", "GEO 변화", "AI visibility change",
  "AI 가시성 변화", "mention tracking", "언급 추적".
user-invocable: true
argument-hint: "<brand> [--period <days>]"
license: proprietary
metadata:
  author: Jaehyun Ahn
  version: "1.0.0"
  category: geo
---

# GEO Drift: AI Visibility Change Detection

**Invocation:** `/three-o geo drift <brand> [--period <days>]`

## Purpose

Tracks how brand visibility in AI platforms changes over time.
Compares current GEO data against stored baselines to detect:
- Score improvements or declines
- New mentions gained or lost
- Sentiment shifts (positive → negative, etc.)
- Competitor movement (new competitors appearing)
- Platform-specific changes

## Data Storage

Baseline data stored in SQLite:
- Location: `~/.config/three-o/geo_baselines.db`
- Table: `geo_snapshots` (brand, timestamp, platform, query, data_json)
- Retention: 365 days default

## Comparison Rules

| Rule | Trigger | Severity |
|------|---------|----------|
| Score drop >10 points | GEO score decreased significantly | Critical |
| Score drop 5-10 points | Moderate decline | Warning |
| Platform loss | Was mentioned, now absent | Critical |
| Position drop | 1st → 3rd or lower | Warning |
| Sentiment shift | Positive → Negative | Critical |
| Sentiment shift | Positive → Neutral | Info |
| New competitor | Competitor now mentioned where wasn't | Warning |
| Brand disappeared | Mentioned before, not now | Critical |
| New mention gained | Not mentioned before, now is | Positive |
| Score gain >10 points | Significant improvement | Positive |

## Drift Score Calculation

```
drift_score = sum(change_severity × change_weight) / total_changes
```

| Severity | Score |
|----------|-------|
| Critical negative | -3 |
| Warning negative | -1 |
| Info | 0 |
| Positive | +2 |

## Period Options

| Period | Comparison |
|--------|-----------|
| 7 (default) | Last 7 days vs previous 7 days |
| 14 | 2-week comparison |
| 30 | Monthly comparison |
| 90 | Quarterly comparison |
| custom | Specify exact date range |

## Output Format

```
GEO Drift Report: [brand]
━━━━━━━━━━━━━━━━━━━━━━━━━━
Period: [start] → [end]
Overall Drift: [+/-XX points] ([improving/declining/stable])

Score Changes:
  Overall GEO:  XX → XX ([+/-]XX)
  ChatGPT:      XX → XX ([+/-]XX)
  Perplexity:   XX → XX ([+/-]XX)
  Gemini:       XX → XX ([+/-]XX)
  Claude:       XX → XX ([+/-]XX)

Key Changes:
  [▲/▼] [description of change] — [severity]
  ...

Alerts:
  [Critical issues requiring immediate attention]

Trend: [improving / declining / stable / volatile]
```

## Reference Files

Load on-demand:
- `references/geo-comparison-rules.md` — Detailed rule specifications

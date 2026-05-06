---
name: seo-keywords
description: >
  Keyword ranking tracker for Google and Naver simultaneously.
  Tracks positions, search volume, competition, and trends.
  Identifies opportunity keywords from competitor gaps.
  Use when user says "keyword tracking", "키워드 추적", "keyword ranking",
  "키워드 순위", "keyword research", "키워드 리서치".
user-invocable: true
argument-hint: "<url or keyword>"
license: proprietary
metadata:
  author: Jaehyun Ahn
  version: "1.0.0"
  category: seo
---

# SEO Keywords: Dual-Engine Keyword Tracking

**Invocation:** `/three-o seo keywords <url or keyword>`

## Features

### Keyword Ranking Tracker
- Track keyword positions on Google and Naver simultaneously
- Daily/weekly position change monitoring
- SERP feature detection (featured snippet, People Also Ask, Naver View tab)
- Position history stored in SQLite for trend analysis

### Keyword Research
- Seed keyword expansion using related searches
- Search volume estimation (Google Keyword Planner + Naver Keyword Tool)
- Competition/difficulty scoring
- Search intent classification (informational, commercial, transactional, navigational)

### Opportunity Detection
- Keywords where site ranks on Google but not Naver (and vice versa)
- Low-competition, high-volume opportunities
- Trending keywords in the industry vertical
- Long-tail keyword suggestions

## Dual-Engine Differences

| Aspect | Google | Naver |
|--------|--------|-------|
| Data source | Google Search Console / DataForSEO | Naver Search Advisor / Naver AD API |
| SERP features | Featured snippets, PAA, knowledge panel | View tab, Blog, Cafe, Knowledge-iN |
| Volume data | Keyword Planner | Naver Keyword Tool (searchad.naver.com) |
| Ranking factors | Backlinks, content, E-E-A-T | Platform ecosystem, recency, engagement |

## Output Format

```
Keyword Report: [target]
━━━━━━━━━━━━━━━━━━━━━━━━━━
Total keywords tracked: XX
Ranking on Google: XX | Ranking on Naver: XX

Top Opportunities:
  [keyword] - Google: #XX, Naver: not ranked, Volume: XXX
  [keyword] - Google: not ranked, Naver: #XX, Volume: XXX

Position Changes (7d):
  ↑ [keyword]: #XX → #XX (+X)
  ↓ [keyword]: #XX → #XX (-X)
```

## Reference Files

Load on-demand:
- `references/naver-ranking-factors.md` — Naver-specific ranking signals
- `references/google-vs-naver-serp.md` — SERP feature comparison

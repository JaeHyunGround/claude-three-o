---
name: seo-drift
description: >
  SEO drift monitoring. Captures baselines, compares current state to
  stored baselines, and tracks changes over time using SQLite storage.
  Detects ranking drops, content changes, technical regressions,
  and schema modifications.
  Use when user says "SEO drift", "SEO 변동", "SEO monitoring",
  "SEO 모니터링", "baseline", "SEO changes", "변동 추적".
user-invocable: true
argument-hint: "[baseline|compare|history] <url>"
license: proprietary
metadata:
  author: Jaehyun Ahn
  version: "1.0.0"
  category: seo
---

# SEO Drift: Change Monitoring

**Invocation:** `/three-o seo drift [command] <url>`

## Sub-Commands

| Command | What it does |
|---------|-------------|
| `/three-o seo drift baseline <url>` | Capture current SEO state as baseline |
| `/three-o seo drift compare <url>` | Compare current state to stored baseline |
| `/three-o seo drift history <url>` | Show drift history over time |

## Baseline Capture

Captures and stores in SQLite (`~/.config/three-o/drift.db`):
- Title tag, meta description, canonical URL
- H1 and heading structure
- Content hash and word count
- Schema types and properties
- robots.txt rules
- Core Web Vitals scores
- Internal link count
- Image count and alt text coverage
- HTTP status code

## Comparison Rules (17 rules)

| # | Rule | Severity | Trigger |
|---|------|----------|---------|
| 1 | Title tag changed | Medium | Content mismatch |
| 2 | Meta description changed | Low | Content mismatch |
| 3 | H1 changed | Medium | Content mismatch |
| 4 | Canonical URL changed | Critical | URL mismatch |
| 5 | Content length dropped >20% | High | Significant content removal |
| 6 | Schema type removed | High | Type missing from baseline |
| 7 | Schema type added | Info | New type detected |
| 8 | robots.txt changed | High | Directive changes |
| 9 | noindex added | Critical | Page deindexed |
| 10 | HTTP status changed | Critical | Non-200 response |
| 11 | LCP degraded >1s | High | Performance regression |
| 12 | INP degraded >100ms | High | Performance regression |
| 13 | CLS degraded >0.05 | Medium | Layout stability regression |
| 14 | Internal links dropped >30% | Medium | Link structure change |
| 15 | Images removed >30% | Medium | Content reduction |
| 16 | Alt text coverage dropped | Low | Accessibility regression |
| 17 | Heading structure changed | Low | Content reorganization |

## Reference Files

Load on-demand:
- `references/comparison-rules.md` — Full rule details with thresholds

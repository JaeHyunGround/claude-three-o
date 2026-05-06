---
name: seo-audit
description: >
  Full website SEO audit with parallel subagent delegation.
  Dual-engine analysis for Google and Naver simultaneously.
  Crawls up to 500 pages, detects Korean business types,
  generates SEO Health Score (0-100) with prioritized action plan.
  Use when user says "SEO audit", "사이트 감사", "SEO 진단",
  "full SEO check", "SEO 전체 분석".
user-invocable: true
argument-hint: "<url>"
license: proprietary
metadata:
  author: Jaehyun Ahn
  version: "1.0.0"
  category: seo
---

# SEO Audit: Full Site Analysis

**Invocation:** `/three-o seo audit <url>`

Comprehensive SEO audit with parallel subagent delegation across Google and Naver.

## Workflow

1. Fetch homepage and detect business type (see `three-o/references/industry-detection.md`)
2. Detect language and search engine priority (Korean → Naver + Google, Other → Google only)
3. Spawn subagents in parallel:
   - **seo-technical**: Crawlability, indexability, security, mobile, CWV
   - **seo-content**: E-E-A-T, readability, content depth, uniqueness
   - **seo-schema**: Schema.org detection, validation, coverage
   - **seo-performance**: Core Web Vitals (LCP, INP, CLS)
   - **seo-visual**: Screenshots, mobile rendering, above-fold content
4. Conditional agents:
   - Korean content detected → spawn **seo-naver** (Search Advisor, Blog, Place)
   - Google API credentials available → use GSC data in seo-technical
   - E-commerce detected → enhanced product schema analysis
   - 30+ location pages → enforce 60% unique content gate
5. Collect all agent results
6. Compute SEO Score (0-100) per scoring methodology
7. Generate prioritized action plan: Critical → High → Medium → Low
8. Offer report: "Generate PDF? Use `/three-o report seo`"

## Output Format

```
SEO Audit Report: [URL]
━━━━━━━━━━━━━━━━━━━━━━━━━━
SEO Score: XX/100
Engine: Google + Naver (or Google only)
Industry: [Detected Type]

Category Scores:
  Technical:  XX/100
  Content:    XX/100
  On-Page:    XX/100
  Schema:     XX/100
  Performance:XX/100
  Naver:      XX/100 (if applicable)

[Priority-ordered findings and recommendations]
```

## Quality Gates

- WARNING at 30+ location pages (enforce 60%+ unique content)
- HARD STOP at 50+ location pages (require user justification)
- Never recommend HowTo schema
- Always use INP for Core Web Vitals, never FID

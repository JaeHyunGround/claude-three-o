---
name: seo-competitor
description: >
  Competitor keyword gap analysis across Google and Naver.
  Identifies keywords where competitors rank but target does not,
  cross-engine gaps, and content opportunity areas.
  Use when user says "competitor analysis", "경쟁사 분석",
  "keyword gap", "키워드 갭", "competitor SEO".
user-invocable: true
argument-hint: "<target-url> <competitor-url>"
license: proprietary
metadata:
  author: Jaehyun Ahn
  version: "1.0.0"
  category: seo
---

# SEO Competitor: Keyword Gap Analysis

**Invocation:** `/three-o seo competitor <target-url> <competitor-url>`

## Analysis Types

### Keyword Gap
- Keywords competitor ranks for but target does not
- Keywords both rank for but competitor outranks target
- Keywords target ranks for but competitor does not (strengths)

### Cross-Engine Gap
- Keywords competitor ranks on Naver but not Google (or vice versa)
- Platform-specific content advantages (Blog, Smart Store presence)

### Content Gap
- Topic areas competitor covers that target does not
- Content depth comparison (word count, E-E-A-T signals)
- Content freshness comparison

### SERP Feature Gap
- Featured snippets competitor owns
- Naver VIEW tab positions competitor holds
- Schema markup advantages

## Workflow

1. Fetch both target and competitor homepages
2. Identify overlapping and unique keywords via search data
3. Compare SERP positions on both Google and Naver
4. Analyze content coverage differences
5. Score competitive position per category
6. Generate opportunity prioritization matrix

## Output Format

```
Competitor Gap Analysis
━━━━━━━━━━━━━━━━━━━━━━
Target: [url1] | Competitor: [url2]

Keyword Gaps (competitor ranks, you don't): XX keywords
  [keyword] - Competitor: Google #X, Naver #X | Volume: XXX
  ...

Your Strengths (you rank, competitor doesn't): XX keywords

Cross-Engine Opportunities:
  [keyword] - You: Google #X only → Naver opportunity
  ...

Content Gaps:
  [topic area] - Competitor has XX pages, you have XX
  ...

Priority Actions:
  1. [High impact, low effort opportunities]
  2. ...
```

## Reference Files

Load on-demand:
- `references/gap-analysis-methodology.md` — Scoring and prioritization framework

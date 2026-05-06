---
name: three-o-competitor
description: >
  Cross-pillar competitor benchmarking. Compares two businesses across
  SEO, GEO, and AAO dimensions to identify gaps and advantages.
  Use when user says "competitor", "경쟁사", "benchmark", "벤치마크",
  "compare sites", "사이트 비교", "competitor analysis", "경쟁 분석".
user-invocable: true
argument-hint: "<url1> <url2> [--depth <quick|full>]"
license: proprietary
metadata:
  author: Jaehyun Ahn
  version: "1.0.0"
  category: three-o
---

# Three-O Competitor: Cross-Pillar Benchmarking

**Invocation:** `/three-o competitor <url1> <url2> [--depth <quick|full>]`

## Purpose

Compares two businesses across all three optimization pillars to
identify competitive gaps, advantages, and strategic opportunities.
Shows where you're winning, losing, and where quick wins exist.

## Analysis Depth

| Depth | Scope | Time |
|-------|-------|------|
| quick | Key metrics per pillar, top-level comparison | 2-3 min |
| full | Complete audit of both sites with detailed breakdown | 8-15 min |

## Comparison Dimensions

### SEO Comparison
| Metric | Site A | Site B | Gap |
|--------|--------|--------|-----|
| Technical score | | | |
| Content quality | | | |
| Schema coverage | | | |
| CWV performance | | | |
| Keyword positions | | | |
| Naver presence | | | |

### GEO Comparison
| Metric | Site A | Site B | Gap |
|--------|--------|--------|-----|
| AI mention rate | | | |
| Mention position | | | |
| Sentiment | | | |
| Entity presence | | | |
| Citability | | | |

### AAO Comparison
| Metric | Site A | Site B | Gap |
|--------|--------|--------|-----|
| Selectability | | | |
| Conversion path | | | |
| Structured data | | | |
| Rendering | | | |
| Entity consistency | | | |

## Gap Identification

For each dimension where Site A trails Site B:
- Quantify the gap (points difference)
- Identify root cause
- Estimate effort to close gap
- Calculate priority score

## Opportunity Matrix

```
                High Impact
                    │
    Quick Wins      │     Strategic
    (do first)     │     (plan for)
────────────────────┼────────────────────
    Low Priority    │     Long-term
    (skip or later) │     (resource-heavy)
                    │
                Low Impact
         Low Effort ──────── High Effort
```

## Output Format

```
Competitor Benchmark: [brand A] vs [brand B]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Overall Three-O Score:
  [brand A]: XX/100
  [brand B]: XX/100
  Gap: [+/-]XX points

Pillar Comparison:
  SEO: [A] XX vs [B] XX — Winner: [brand]
  GEO: [A] XX vs [B] XX — Winner: [brand]
  AAO: [A] XX vs [B] XX — Winner: [brand]

Where You Win:
  [dimension] — You: XX, Competitor: XX (+XX advantage)
  ...

Where You Lose:
  [dimension] — You: XX, Competitor: XX (-XX gap)
  → Fix: [recommended action]
  ...

Quick Win Opportunities:
  1. [action] — Close [X]-point gap with [low] effort
  ...
```

## Reference Files

Load on-demand:
- `references/benchmark-methodology.md` — Comparison methodology and normalization

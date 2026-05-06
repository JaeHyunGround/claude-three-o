---
name: geo-score
description: >
  Computes unified GEO Score (0-100) from mention data, context quality,
  visibility ranking, entity presence, and technical accessibility.
  Use when user says "GEO score", "GEO 점수", "AI visibility score",
  "AI 가시성 점수", "브랜드 노출 점수".
user-invocable: true
argument-hint: "<brand> [--baseline file]"
license: proprietary
metadata:
  author: Jaehyun Ahn
  version: "1.0.0"
  category: geo
---

# GEO Score: AI Visibility Scoring Engine

**Invocation:** `/three-o geo score <brand> [--baseline file]`

## Input Requirements

Requires mention data from `geo-mentions` skill output. Can be:
- Live: triggers `geo-mentions` first if no data exists
- Cached: uses existing mention data from current session
- Baseline: compares against stored baseline file

## Scoring Formula

**GEO Score = MF × CQ × VR × EP × TA** (geometric mean, scaled 0-100)

| Dimension | Weight | Description |
|-----------|--------|-------------|
| MF (Mention Frequency) | 30% | How often brand appears across AI platforms |
| CQ (Context Quality) | 25% | Sentiment and recommendation strength |
| VR (Visibility Ranking) | 20% | Position in AI responses (1st, 2nd, 3rd) |
| EP (Entity Presence) | 15% | Knowledge graph and entity recognition |
| TA (Technical Accessibility) | 10% | AI crawler access, llms.txt, SSR |

## Per-Platform Scoring

Each platform scored independently (0-100), then weighted:
- ChatGPT: 35% (highest user volume)
- Perplexity: 25% (citation-heavy)
- Gemini: 25% (Google ecosystem)
- Claude: 15% (growing market share)

## Industry Adjustments

Applied after base score calculation:
- Healthcare/Clinic: +10% weight on Context Quality (trust signals)
- E-commerce: +5% weight on Entity Presence (product knowledge)
- Education: +10% weight on Mention Frequency (discovery queries)
- Franchise: +5% weight on Visibility Ranking (local mentions)

## Output Format

```
GEO Score Report: [brand]
━━━━━━━━━━━━━━━━━━━━━━━━━━
Overall GEO Score: XX/100

Dimension Scores:
  Mention Frequency (MF):       XX/100
  Context Quality (CQ):         XX/100
  Visibility Ranking (VR):      XX/100
  Entity Presence (EP):         XX/100
  Technical Accessibility (TA): XX/100

Platform Scores:
  ChatGPT:    XX/100
  Perplexity: XX/100
  Gemini:     XX/100
  Claude:     XX/100

Industry: [detected]
Adjustment Applied: [if any]

[If baseline provided: delta comparison]
```

## Reference Files

Load on-demand:
- `references/scoring-formula.md` — Detailed formula with normalization
- `references/benchmark-data.md` — Industry benchmark ranges

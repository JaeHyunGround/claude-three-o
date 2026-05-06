---
name: geo-sentiment
description: >
  Classifies AI platform mention sentiment (positive/negative/neutral)
  and provides content improvement recommendations for negative mentions.
  Use when user says "mention sentiment", "언급 감성", "AI sentiment",
  "AI 감성 분석", "brand perception", "브랜드 인식".
user-invocable: true
argument-hint: "<brand> [--detailed]"
license: proprietary
metadata:
  author: Jaehyun Ahn
  version: "1.0.0"
  category: geo
---

# GEO Sentiment: AI Mention Sentiment Analysis

**Invocation:** `/three-o geo sentiment <brand> [--detailed]`

## Purpose

Analyzes the sentiment and tone of brand mentions across AI platforms.
Goes beyond simple positive/negative classification to identify:
- Recommendation strength (explicit vs passive)
- Trust signals present or absent
- Comparative positioning (better than / worse than)
- Factual accuracy of AI-generated claims

## Sentiment Classification

### Categories

| Category | Score | Description |
|----------|-------|-------------|
| Strong Positive | 1.0 | Explicitly recommended, praised |
| Positive | 0.8 | Mentioned favorably, included in top options |
| Neutral | 0.5 | Mentioned without evaluation |
| Negative | 0.2 | Criticized, warned against, limitations noted |
| Strong Negative | 0.0 | Explicitly advised against |

### Context Signals

For each mention, extract:
- **Recommendation type**: "top pick" / "worth considering" / "one option" / "avoid"
- **Qualifiers**: "best for..." / "if you need..." / "despite..." / "however..."
- **Comparison frame**: Positioned above or below competitors
- **Trust markers**: Citations, stats, specific claims cited

## Analysis Workflow

1. Receive mention data from `geo-mentions` output
2. For each mention, extract surrounding context (±200 chars)
3. Classify sentiment using multi-signal analysis
4. Identify factual claims made about brand
5. Flag inaccurate claims for correction strategy
6. Generate content improvement recommendations

## Content Improvement Triggers

| Signal | Trigger | Recommended Action |
|--------|---------|-------------------|
| Outdated info | AI cites old data | Update website, publish fresh content |
| Missing strengths | Key differentiator not mentioned | Create comparison content |
| Competitor framing | "unlike [brand]..." | Counter-narrative content |
| Generic mention | Listed without detail | Add structured data, unique claims |
| Factual error | Incorrect claim about brand | Correct via authoritative sources |

## Output Format

```
Sentiment Analysis: [brand]
━━━━━━━━━━━━━━━━━━━━━━━━━━━
Overall Sentiment: XX% positive / XX% neutral / XX% negative

Per-Platform Breakdown:
  ChatGPT:    [strong pos: X | pos: X | neutral: X | neg: X]
  Perplexity: [strong pos: X | pos: X | neutral: X | neg: X]
  Gemini:     [strong pos: X | pos: X | neutral: X | neg: X]
  Claude:     [strong pos: X | pos: X | neutral: X | neg: X]

Key Findings:
  Strengths highlighted: [what AI says is good]
  Weaknesses noted: [what AI says is bad/missing]
  Factual errors: [incorrect claims to address]

Improvement Actions:
  1. [Priority action with expected sentiment impact]
  ...
```

## Reference Files

Load on-demand:
- `references/sentiment-model.md` — Classification rules and scoring
- `references/content-improvement-templates.md` — Fix templates by issue type

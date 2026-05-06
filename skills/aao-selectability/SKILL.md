---
name: aao-selectability
description: >
  Scores how likely AI agents are to select/recommend a brand when
  fulfilling user requests. Analyzes signals that drive agent preference.
  Use when user says "selectability", "선택 가능성", "agent preference",
  "에이전트 선호도", "AI agent selection", "에이전트 선택".
user-invocable: true
argument-hint: "<brand> [--competitors <list>]"
license: proprietary
metadata:
  author: Jaehyun Ahn
  version: "1.0.0"
  category: aao
---

# AAO Selectability: Agent Selection Scoring

**Invocation:** `/three-o aao selectability <brand> [--competitors <list>]`

## Purpose

When an AI agent needs to recommend or select a service/product for a user,
it evaluates options based on structured signals. This skill scores how
"selectable" a brand is from an agent's perspective.

## Selectability Signals

| Signal | Weight | Description |
|--------|--------|-------------|
| Structured Data Quality | 25% | Complete, valid Schema.org markup |
| Review/Rating Signals | 20% | Aggregate ratings, review volume |
| Information Completeness | 20% | All key attributes available |
| API/Booking Availability | 15% | Can agent complete action programmatically? |
| Trust Signals | 10% | Certifications, awards, years in business |
| Freshness | 10% | Recently updated content and data |

## Evaluation Process

1. **Crawl target URL** — extract all structured data
2. **Check completeness** — all required fields populated?
3. **Validate ratings** — AggregateRating present, review count
4. **Test actionability** — booking/purchase API available?
5. **Compare vs competitors** — relative advantage scoring
6. **Industry benchmark** — compare to median in category

## Competitor Comparison

If `--competitors` provided, produces relative scoring:
- Score each competitor on same signals
- Rank by overall selectability
- Identify where brand wins/loses vs each competitor
- Highlight quick-win differentiation opportunities

## Agent Decision Simulation

Simulates how an agent would rank options:
```
Query: "Book a [category] in [location]"
Agent evaluates: [brand] vs [competitor1] vs [competitor2]

Decision factors:
  1. Matching criteria (location, category, price range)
  2. Quality signals (ratings, reviews, completeness)
  3. Actionability (can I book/buy directly?)
  4. Trust (established, verified, consistent info)
```

## Output Format

```
Selectability Score: [brand]
━━━━━━━━━━━━━━━━━━━━━━━━━━━
Overall Score: XX/100

Signal Breakdown:
  Structured Data:     XX/100
  Reviews/Ratings:     XX/100
  Info Completeness:   XX/100
  API/Booking:         XX/100
  Trust Signals:       XX/100
  Freshness:           XX/100

[If competitors provided:]
Ranking:
  1. [brand/competitor] — XX/100
  2. [brand/competitor] — XX/100
  ...

Key Gaps vs Top Competitor:
  [signal] — You: XX, Competitor: XX → [action]
  ...
```

## Reference Files

Load on-demand:
- `references/selectability-signals.md` — Detailed signal definitions
- `references/agent-decision-model.md` — How AI agents rank options

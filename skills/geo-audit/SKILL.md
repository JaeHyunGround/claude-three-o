---
name: geo-audit
description: >
  Full GEO analysis across all AI platforms. Aggregates brand mention
  tracking, sentiment analysis, citability scoring, entity presence,
  and llms.txt compliance into a unified GEO Health Score (0-100).
  Use when user says "GEO audit", "GEO 분석", "AI visibility audit",
  "AI 가시성 감사", "AI 노출 전체 분석".
user-invocable: true
argument-hint: "<url or brand>"
license: proprietary
metadata:
  author: Jaehyun Ahn
  version: "1.0.0"
  category: geo
---

# GEO Audit: Full AI Visibility Analysis

**Invocation:** `/three-o geo audit <url or brand>`

## Workflow

1. Extract brand name and primary URL from input
2. Spawn GEO agents in parallel:
   - **geo-mentions**: Probe ChatGPT, Perplexity, Gemini, Claude for brand mentions
   - **geo-citability**: Analyze passage-level citability of website content
   - **geo-entity**: Check entity presence across knowledge graphs
3. After mentions collected, spawn sequentially:
   - **geo-sentiment**: Classify mention sentiment (positive/negative/neutral)
   - **geo-score**: Compute unified GEO Score
4. Additional checks:
   - llms.txt presence and compliance
   - SSR availability for AI crawler access
   - Structured data completeness for AI consumption
5. If existing GEO baseline found → spawn **geo-drift** for comparison
6. Aggregate all results into GEO Health Score (0-100)
7. Generate prioritized action plan
8. Offer report: "Generate PDF? Use `/three-o report geo`"

## Output Format

```
GEO Audit Report: [brand]
━━━━━━━━━━━━━━━━━━━━━━━━━━
GEO Score: XX/100

Per-Platform Scores:
  ChatGPT:    XX/100 (XX mentions in XX queries)
  Perplexity: XX/100 (XX mentions in XX queries)
  Gemini:     XX/100 (XX mentions in XX queries)
  Claude:     XX/100 (XX mentions in XX queries)

Dimension Breakdown:
  Mention Frequency:        XX/100
  Context Quality:          XX/100
  Visibility Ranking:       XX/100
  Entity Presence:          XX/100
  Technical Accessibility:  XX/100

Sentiment: XX% positive / XX% neutral / XX% negative

[Priority-ordered findings and recommendations]
```

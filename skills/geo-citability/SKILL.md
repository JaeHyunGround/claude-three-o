---
name: geo-citability
description: >
  Analyzes website content for AI citability — whether passages are
  structured, factual, and authoritative enough for AI platforms to
  cite as sources. Scores passage-level extractability.
  Use when user says "citability", "인용 가능성", "AI citation",
  "AI 인용 분석", "passage quality", "패시지 품질".
user-invocable: true
argument-hint: "<url> [--depth <1-3>]"
license: proprietary
metadata:
  author: Jaehyun Ahn
  version: "1.0.0"
  category: geo
---

# GEO Citability: Passage-Level AI Citation Analysis

**Invocation:** `/three-o geo citability <url> [--depth <1-3>]`

## Purpose

Evaluates whether website content is structured for AI citation.
AI platforms cite sources that provide:
- Clear, factual statements extractable as standalone passages
- Authoritative tone with supporting evidence
- Structured formatting (lists, tables, definitions)
- Unique data or insights not available elsewhere

## Analysis Scope

| Depth | Pages Analyzed |
|-------|---------------|
| 1 (default) | Target URL only |
| 2 | Target + internal links (max 10) |
| 3 | Target + 2 levels deep (max 30) |

## Citability Scoring

Each page scored on 5 dimensions:

| Dimension | Weight | What It Measures |
|-----------|--------|-----------------|
| Passage Clarity | 25% | Can a sentence/paragraph stand alone as an answer? |
| Factual Density | 25% | Stats, numbers, named entities per passage |
| Structural Format | 20% | Lists, tables, H2/H3 organization |
| Authority Signals | 15% | Author credentials, citations, methodology |
| Uniqueness | 15% | Original data, proprietary insights |

## Passage Extraction Test

For each page, simulate AI extraction:
1. Identify top 5 "citable passages" (sentences AI would quote)
2. Score each passage independently
3. Test if passage answers a common query without additional context
4. Check if passage includes brand name (attribution)

## Citability Anti-Patterns

| Pattern | Problem | Fix |
|---------|---------|-----|
| Wall of text | No clear extractable passage | Add subheadings, break into short paragraphs |
| Vague claims | "We're the best" — no data | Add specific metrics, case study results |
| Image-only data | Charts without text summary | Add text description of key takeaways |
| Gated content | Login required for key info | Make summary available publicly |
| Heavy JavaScript | Content not in HTML source | Implement SSR for key pages |

## Output Format

```
Citability Analysis: [url]
━━━━━━━━━━━━━━━━━━━━━━━━━━
Overall Citability Score: XX/100
Pages Analyzed: XX

Dimension Scores:
  Passage Clarity:   XX/100
  Factual Density:   XX/100
  Structural Format: XX/100
  Authority Signals: XX/100
  Uniqueness:        XX/100

Top Citable Passages:
  1. "[extracted passage]" — Score: XX/100
  2. "[extracted passage]" — Score: XX/100
  ...

Improvement Opportunities:
  [page] — [issue] → [fix]
  ...
```

---
name: geo-context
description: >
  Maps brand queries to AI platform query types and generates optimized
  query sets per industry and intent. Analyzes which query contexts
  trigger brand mentions and which miss.
  Use when user says "query mapping", "쿼리 매핑", "AI query analysis",
  "AI 쿼리 분석", "mention triggers", "언급 트리거".
user-invocable: true
argument-hint: "<brand> --industry <type>"
license: proprietary
metadata:
  author: Jaehyun Ahn
  version: "1.0.0"
  category: geo
---

# GEO Context: Query Mapping & Analysis

**Invocation:** `/three-o geo context <brand> --industry <type>`

## Purpose

Identifies which query contexts (types, intents, formats) trigger
brand mentions on AI platforms, and which contexts represent gaps.
Used to:
1. Generate optimal query sets for brand monitoring
2. Identify content gaps that prevent AI mention
3. Map competitor mention patterns to query types

## Query Type Taxonomy

| Type | Example | AI Behavior |
|------|---------|-------------|
| Recommendation | "best X in Y" | Lists top options |
| Comparison | "A vs B" | Direct head-to-head |
| Review | "X review" | Summarizes opinions |
| How-to | "how to choose X" | Educational, may cite |
| Purchase | "buy X", "X price" | Transactional, product-focused |
| Local | "X near me", "X in [city]" | Location-filtered |
| Evaluation | "is X good" | Opinion synthesis |

## Query Generation Logic

1. Load industry template from `references/query-type-taxonomy.md`
2. Expand template variables: `{brand}`, `{category}`, `{location}`, `{competitor}`
3. Add Korean-language variants for bilingual coverage
4. Classify each query by intent: informational / navigational / transactional
5. Score expected mention likelihood (0-1) based on query type

## Context Gap Analysis

For each query where brand is NOT mentioned:
- Identify why (missing content? weak entity? competitor dominance?)
- Map to actionable fix (content creation, schema addition, etc.)
- Prioritize by query volume × conversion potential

## Output Format

```
Query Context Analysis: [brand]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Industry: [type]
Total Queries Generated: XX
  Recommendation: XX | Comparison: XX | Review: XX
  How-to: XX | Purchase: XX | Local: XX | Evaluation: XX

Mention Trigger Map:
  High trigger:  [query types that consistently mention brand]
  Low trigger:   [query types where brand is absent]

Gap Analysis:
  [query type] — Missing because: [reason]
  → Action: [recommended fix]
```

## Reference Files

Load on-demand:
- `references/query-type-taxonomy.md` — Full taxonomy with Korean variants
- `references/query-mapping-rules.md` — Mapping logic and priority rules

---
name: geo-entity
description: >
  Checks brand entity presence across knowledge graphs (Google, Wikidata,
  Naver), validates sameAs linking, and identifies entity gaps.
  Use when user says "entity check", "엔티티 확인", "knowledge graph",
  "지식 그래프", "entity presence", "엔티티 존재".
user-invocable: true
argument-hint: "<brand>"
license: proprietary
metadata:
  author: Jaehyun Ahn
  version: "1.0.0"
  category: geo
---

# GEO Entity: Knowledge Graph Presence Analysis

**Invocation:** `/three-o geo entity <brand>`

## Purpose

AI platforms rely on knowledge graphs to identify and describe entities.
Strong entity presence leads to:
- More accurate brand mentions in AI responses
- Higher confidence in AI recommendations
- Correct attribute association (location, category, features)
- Better disambiguation from similarly-named entities

## Entity Sources Checked

| Source | Weight | What We Check |
|--------|--------|---------------|
| Google Knowledge Panel | 0.30 | Panel exists, attributes complete |
| Wikidata | 0.25 | Entity ID, properties, sameAs links |
| Naver Knowledge | 0.20 | Naver entity recognition, 지식백과 |
| Schema.org (website) | 0.15 | Organization/LocalBusiness markup |
| Wikipedia | 0.10 | Article or mention in relevant articles |

## Entity Completeness Check

For each source, verify:
- **Existence**: Entity record found (yes/no)
- **Attributes**: Name, description, category, location, URL, logo
- **Freshness**: Last updated date
- **Linking**: sameAs/owl:sameAs connections between sources
- **Accuracy**: Consistent information across sources

## sameAs Linking Audit

Verify cross-reference links:
```
Website (Schema.org) → Wikidata → Wikipedia
    ↓                      ↓
Google KP              Naver Knowledge
    ↓
Social profiles (LinkedIn, Facebook, Instagram, YouTube)
```

Missing links = missed entity consolidation opportunity.

## Entity Gaps & Recommendations

| Gap | Impact | Action |
|-----|--------|--------|
| No Wikidata entry | High | Create entry with basic properties |
| No Knowledge Panel | High | Ensure structured data + citations |
| Missing sameAs on website | Medium | Add to Organization schema |
| Inconsistent name variants | Medium | Standardize across platforms |
| No Naver entity | High (Korea) | Submit to Naver Knowledge |
| Incomplete attributes | Low | Fill in missing properties |

## Output Format

```
Entity Presence Report: [brand]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Entity Score: XX/100

Source Status:
  Google Knowledge Panel: [✓/✗] — Completeness: XX%
  Wikidata:               [✓/✗] — Properties: XX/XX
  Naver Knowledge:        [✓/✗] — Status: [found/not found]
  Schema.org (website):   [✓/✗] — Type: [Organization/LocalBusiness/etc]
  Wikipedia:              [✓/✗] — [article/mention/none]

sameAs Linking:
  [source] → [target]: [✓ linked / ✗ missing]
  ...

Attribute Consistency:
  Name: [consistent/inconsistent] across X sources
  Category: [consistent/inconsistent]
  Location: [consistent/inconsistent]
  URL: [consistent/inconsistent]

Priority Actions:
  1. [action with highest impact]
  ...
```

## Reference Files

Load on-demand:
- `references/entity-sources.md` — API access and check methods
- `references/sameas-linking.md` — Linking best practices and templates

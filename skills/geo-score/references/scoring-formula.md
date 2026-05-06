<!-- Updated: 2026-05-04 -->
# GEO Scoring Formula Details

## Mention Frequency (MF) — 30%

```
MF = (mentions_found / total_queries) × platform_weight_sum × 100
```

Per-platform calculation:
- Count queries where brand is mentioned at least once
- Bonus for multiple mentions within single response (+0.2 per extra mention, max +1.0)
- Penalize generic/vague mentions (-0.3 if brand only in passing)

## Context Quality (CQ) — 25%

```
CQ = avg(sentiment_score × recommendation_strength × accuracy_score)
```

| Factor | Scoring |
|--------|---------|
| Sentiment | Positive: 1.0, Neutral: 0.6, Negative: 0.2 |
| Recommendation | Explicit rec: 1.0, Listed option: 0.7, Mentioned: 0.4 |
| Accuracy | Factually correct: 1.0, Partially correct: 0.5, Incorrect: 0.1 |

## Visibility Ranking (VR) — 20%

```
VR = avg(position_score) across all queries with mentions
```

| Position | Score |
|----------|-------|
| 1st mentioned | 1.0 |
| 2nd mentioned | 0.7 |
| 3rd mentioned | 0.5 |
| 4th+ mentioned | 0.3 |
| Only in list (no emphasis) | 0.2 |

## Entity Presence (EP) — 15%

```
EP = (entity_sources_found / max_sources) × entity_quality
```

Sources checked:
- Google Knowledge Panel (weight: 0.3)
- Wikidata entity (weight: 0.25)
- Naver Knowledge (weight: 0.2)
- Schema.org Organization markup (weight: 0.15)
- Wikipedia mention (weight: 0.1)

Entity quality factors: completeness of attributes, freshness of data, sameAs linking.

## Technical Accessibility (TA) — 10%

```
TA = sum(check_scores) / total_checks
```

| Check | Score |
|-------|-------|
| llms.txt present and valid | 0.25 |
| SSR / pre-rendered content | 0.25 |
| Structured data (JSON-LD) | 0.20 |
| Fast response time (<2s) | 0.15 |
| No bot blocking | 0.15 |

## Normalization

All dimension scores normalized to 0-100 range using:
```
normalized = min(100, max(0, raw_score × 100))
```

Final GEO Score (geometric mean):
```
GEO = (MF^0.30 × CQ^0.25 × VR^0.20 × EP^0.15 × TA^0.10) × 100
```

<!-- Updated: 2026-05-04 -->
# Quality Gates

## Content Length Thresholds

| Page Type | Minimum Words (EN) | Minimum Characters (KO) | Warning Level |
|-----------|--------------------|------------------------|---------------|
| Homepage | 300 | 600 | Medium |
| Product page | 200 | 400 | High |
| Category page | 150 | 300 | Medium |
| Blog / Article | 800 | 1600 | High |
| Location page | 250 | 500 | High |
| About page | 200 | 400 | Low |
| FAQ page | 500 | 1000 | Medium |
| Service page | 300 | 600 | Medium |

## Content Uniqueness

| Scenario | Threshold | Action |
|----------|-----------|--------|
| Duplicate title tags | Any duplicate | Critical |
| Duplicate meta descriptions | Any duplicate | High |
| Body content similarity > 80% | Between pages | High |
| Location pages > 30 | 60%+ unique content required | Warning |
| Location pages > 50 | User justification required | Hard Stop |

## Schema Restrictions

| Schema Type | Status | Notes |
|-------------|--------|-------|
| HowTo | Deprecated | Never recommend (Sept 2023) |
| FAQPage (commercial) | Restricted | No Google rich results (Aug 2023); AI citation benefit only |
| FAQPage (gov/health) | Allowed | Still eligible for Google rich results |
| SpecialAnnouncement | Deprecated | COVID-era, no longer recommended |
| Product | Active | Required for e-commerce AAO |
| LocalBusiness | Active | Required for location-based businesses |
| Organization | Active | Recommended for all |

## Core Web Vitals Thresholds

| Metric | Good | Needs Improvement | Poor |
|--------|------|-------------------|------|
| LCP | <= 2.5s | 2.5s - 4.0s | > 4.0s |
| INP | <= 200ms | 200ms - 500ms | > 500ms |
| CLS | <= 0.1 | 0.1 - 0.25 | > 0.25 |

Always use INP (Interaction to Next Paint). Never reference FID.

## GEO Quality Gates

| Check | Threshold | Priority |
|-------|-----------|----------|
| Zero AI mentions across all platforms | 0 mentions | Critical |
| All mentions negative sentiment | 100% negative | Critical |
| No entity in any knowledge graph | 0 presence | High |
| llms.txt missing | Not found | Medium |
| SSR not available | JS-only rendering | High |

## AAO Quality Gates

| Check | Threshold | Priority |
|-------|-----------|----------|
| No structured data (Schema) | 0 types found | Critical |
| Product feed missing (e-commerce) | No feed detected | Critical |
| JS-only rendering for core content | > 50% content JS-dependent | High |
| Entity inconsistency across sources | > 2 mismatches | High |
| No pricing data available to agents | Price not in structured data | Medium |

## Korean-Specific Gates

| Check | Threshold | Priority |
|-------|-----------|----------|
| Naver Search Advisor not connected | Korean site without NSA | High |
| Naver Blog content not optimized | No blog presence for B2C | Medium |
| Naver Place not claimed | Local business without Place | Critical |
| Smart Store feed incomplete | E-commerce with missing fields | High |

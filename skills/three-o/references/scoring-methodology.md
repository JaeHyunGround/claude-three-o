<!-- Updated: 2026-05-04 -->
# Three-O Scoring Methodology

## Unified Three-O Score (0-100)

```
Three-O Score = (SEO Score × 0.35) + (GEO Score × 0.35) + (AAO Score × 0.30)
```

## SEO Score Breakdown (0-100)

| Category | Weight | Key Metrics |
|----------|--------|-------------|
| Technical SEO | 22% | Crawlability, indexability, HTTPS, canonical, hreflang, mobile |
| Content Quality | 23% | E-E-A-T signals, readability, depth, uniqueness, Korean morphology |
| On-Page SEO | 20% | Title, meta, headings, internal links, keyword placement |
| Schema Markup | 10% | Valid JSON-LD, required properties, type coverage |
| Performance | 10% | LCP, INP, CLS (Core Web Vitals) |
| AI Readiness | 10% | Server rendering, structured data, llms.txt |
| Images | 5% | Alt text, format, size, lazy loading |

## GEO Score Breakdown (0-100)

```
GEO Score = (Mention Frequency × 0.30) + (Context Quality × 0.30)
          + (Visibility Ranking × 0.20) + (Entity Presence × 0.10)
          + (Technical Accessibility × 0.10)
```

| Dimension | Weight | Measurement |
|-----------|--------|-------------|
| Mention Frequency | 30% | How often brand appears in AI responses (per 100 queries) |
| Context Quality | 30% | Positive vs negative vs neutral sentiment ratio |
| Visibility Ranking | 20% | Position in AI response (1st mention, 2nd, 3rd, etc.) |
| Entity Presence | 10% | Presence in knowledge graphs (Wikipedia, Wikidata, Namu Wiki) |
| Technical Accessibility | 10% | llms.txt, SSR, structured data accessibility |

### GEO Score Per Platform

Calculate individual scores for each AI platform:
- ChatGPT GEO Score
- Perplexity GEO Score
- Gemini GEO Score
- Claude GEO Score

Unified GEO Score = weighted average (equal weights unless platform-specific data suggests otherwise).

## AAO Score Breakdown (0-100)

| Category | Weight | Key Metrics |
|----------|--------|-------------|
| Selectability | 30% | Trust signals, authority indicators, comparison positioning |
| Conversion Readiness | 25% | Pricing transparency, CTA clarity, purchase flow completeness |
| Structured Data | 20% | Product feed completeness, Schema coverage, API endpoints |
| Rendering | 15% | SSR vs CSR ratio, JS-free content accessibility |
| Entity Consistency | 10% | Cross-source NAP/brand info consistency |

## Industry-Specific Weight Adjustments

| Industry | SEO Adjust | GEO Adjust | AAO Adjust |
|----------|------------|------------|------------|
| E-commerce (Smart Store) | 0 | 0 | +10% |
| Franchise HQ | 0 | +5% | +5% |
| Academy/Education | 0 | +10% | 0 |
| Clinic/Healthcare | 0 | +10% | 0 |
| Restaurant/F&B | +5% | 0 | 0 |
| SaaS | 0 | +5% | +5% |
| Real Estate | +5% | 0 | +5% |

When adjustments apply, redistribute from other modules proportionally.

## Score Interpretation

| Score Range | Rating | Action |
|-------------|--------|--------|
| 90-100 | Excellent | Maintain and monitor |
| 75-89 | Good | Minor optimizations |
| 60-74 | Fair | Targeted improvements needed |
| 40-59 | Poor | Significant work required |
| 0-39 | Critical | Immediate intervention needed |

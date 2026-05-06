<!-- Updated: 2026-05-04 -->
# Benchmark Methodology

## Normalization

Both sites scored on identical scales (0-100) using same methodology.
Ensures fair comparison regardless of industry size or market position.

### Score Normalization Rules:
- Same audit parameters applied to both sites
- Same query set used for GEO comparison
- Same industry template for AAO evaluation
- Timing: both audits run in same session (minimize temporal variance)

## Comparison Algorithm

### Step 1: Parallel Audit
Run full audit on both sites simultaneously:
- Site A: seo-audit, geo-audit, aao-audit
- Site B: seo-audit, geo-audit, aao-audit

### Step 2: Dimension Alignment
Match dimensions 1:1 for comparison:
- 15 SEO dimensions
- 10 GEO dimensions
- 8 AAO dimensions
- Total: 33 comparison points

### Step 3: Gap Calculation
```
gap = score_A - score_B
relative_gap = gap / max(score_A, score_B) × 100
```

### Step 4: Statistical Significance
Small gaps (< 3 points) marked as "comparable" — not actionable.
Only gaps > 5 points flagged as meaningful differences.

## Gap Prioritization

```
priority = abs(gap) × dimension_weight × closability
```

| Factor | Measurement |
|--------|-------------|
| Gap size | Absolute point difference |
| Dimension weight | How much this dimension affects overall score |
| Closability | How feasible it is to close this gap (0-1) |

### Closability Factors:
- Technical fix needed → High closability (0.8-1.0)
- Content creation needed → Medium closability (0.5-0.7)
- Entity/authority building → Low closability (0.2-0.4)
- Market position dependent → Very low (0.1-0.2)

## Competitive Intelligence Extraction

Beyond scores, extract:
- What structured data competitor has that you don't
- Which AI platforms mention competitor but not you
- Competitor's conversion path advantages
- Competitor's content topics you haven't covered
- Competitor's entity connections you're missing

## Reporting Bias Prevention

To ensure objectivity:
- Never assume Site A is "better" without data
- Present both strengths and weaknesses for each site
- Acknowledge areas where comparison is not meaningful
- Flag areas where data confidence is low
- Separate facts from estimates

## Korean Market Considerations

Additional comparison points for Korean market:
- Naver Blog presence (quality, frequency)
- Naver Place completeness (vs competitor)
- Korean content depth (자연스러운 한국어)
- Local review volume (Naver, Kakao, Google combined)
- Naver Smart Store ranking (if e-commerce)

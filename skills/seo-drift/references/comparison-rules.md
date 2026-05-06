<!-- Updated: 2026-05-04 -->
# SEO Drift Comparison Rules

## Severity Levels

| Level | Meaning | Response Time |
|-------|---------|---------------|
| Critical | Immediate SEO impact likely | Same day |
| High | Significant impact within days | Within 3 days |
| Medium | Moderate impact over weeks | Within 2 weeks |
| Low | Minor or informational | Next sprint |
| Info | No negative impact, FYI only | No action needed |

## Detailed Rule Specifications

### Critical Rules

**Rule 4: Canonical URL changed**
- Compare: `baseline.canonical` vs `current.canonical`
- Trigger: Any mismatch
- Impact: Can cause deindexing or duplicate content
- Action: Verify intentional change, check redirect chain

**Rule 9: noindex added**
- Compare: meta robots tag and X-Robots-Tag header
- Trigger: noindex present when baseline had index
- Impact: Page will be deindexed
- Action: Immediate removal unless intentional

**Rule 10: HTTP status changed**
- Compare: `baseline.status` vs `current.status`
- Trigger: Non-200 response (especially 404, 500, 301)
- Impact: Broken page or unintended redirect
- Action: Fix immediately, check server logs

### High Rules

**Rule 5: Content length dropped >20%**
- Compare: character count (Korean) or word count (English)
- Trigger: Current < baseline × 0.80
- Impact: Thin content risk, ranking drop
- Action: Review content changes, restore if accidental

**Rule 6: Schema type removed**
- Compare: Set of `@type` values
- Trigger: Type in baseline not found in current
- Impact: Rich result loss
- Action: Re-add schema markup

**Rule 8: robots.txt changed**
- Compare: Full robots.txt content hash
- Trigger: Content mismatch
- Impact: Crawl access changes
- Action: Review changes, ensure intended

**Rule 11/12: CWV degraded**
- Compare: LCP delta >1s or INP delta >100ms
- Trigger: Exceeds threshold
- Impact: User experience and ranking factor
- Action: Performance audit and optimization

## Drift Score

Calculate overall drift severity:
```
Drift Score = sum(rule_severity_weight × triggered_count)

Critical = 10 points each
High = 5 points each
Medium = 2 points each
Low = 1 point each
Info = 0 points

0-5:   Stable (green)
6-15:  Minor drift (yellow)
16-30: Significant drift (orange)
31+:   Critical drift (red)
```

---
name: aao-data
description: >
  Audits structured data integration for AI agent consumption.
  Checks Schema.org coverage, product feeds, API availability,
  and data quality for agent-driven discovery and action.
  Use when user says "structured data audit", "구조화 데이터",
  "schema audit", "스키마 감사", "data integration", "데이터 통합".
user-invocable: true
argument-hint: "<url> [--feed-check]"
license: proprietary
metadata:
  author: Jaehyun Ahn
  version: "1.0.0"
  category: aao
---

# AAO Data: Structured Data Integration Audit

**Invocation:** `/three-o aao data <url> [--feed-check]`

## Purpose

AI agents consume structured data to understand businesses, products,
and services. This skill audits how well a website's structured data
serves agent needs — beyond SEO schema validation, focusing on
completeness for agent decision-making.

## Audit Scope

### 1. Schema.org Coverage (30%)
- All key page types have JSON-LD
- Correct @types selected for business
- Required and recommended properties present
- Nested entities properly linked

### 2. Data Completeness (25%)
- All agent-decision fields populated
- Price/availability current
- Contact/action info accessible
- Hours, location, service area defined

### 3. Data Freshness (20%)
- dateModified present and recent
- Prices match actual (spot check)
- Hours/availability current
- Products in stock status accurate

### 4. Feed Integration (15%)
- Google Merchant Center feed (if e-commerce)
- Naver EP feed (if Korean e-commerce)
- Product data consistency with website
- Feed update frequency

### 5. API Availability (10%)
- OpenAPI spec present
- Booking/reservation API
- Product/inventory API
- Pricing API (real-time)

## Page Type Requirements

| Page Type | Required Schema | Agent-Critical Properties |
|-----------|----------------|--------------------------|
| Homepage | Organization | name, url, sameAs, contactPoint |
| Product | Product + Offer | price, availability, sku, image |
| Service | Service | provider, areaServed, offers |
| Location | LocalBusiness | address, geo, openingHours |
| Event | Event | startDate, location, offers |
| Person | Person (staff) | jobTitle, worksFor |
| FAQ | FAQPage | mainEntity (gov/health only) |
| Review | Review | author, datePublished, reviewRating |

## Output Format

```
Structured Data Audit: [url]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Overall Data Score: XX/100

Dimension Scores:
  Schema Coverage:     XX/100
  Data Completeness:   XX/100
  Data Freshness:      XX/100
  Feed Integration:    XX/100
  API Availability:    XX/100

Pages Audited: XX
  With Schema: XX (XX%)
  Correct Type: XX (XX%)
  Complete: XX (XX%)

Missing Critical Data:
  [page] — Missing: [property list]
  ...

Feed Status:
  Google Merchant: [active/missing/stale]
  Naver EP: [active/missing/stale]

Recommendations:
  1. [priority action]
  ...
```

## Reference Files

Load on-demand:
- `references/schema-requirements.md` — Required schema per page type
- `references/feed-specifications.md` — Feed format requirements

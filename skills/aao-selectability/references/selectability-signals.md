<!-- Updated: 2026-05-04 -->
# Selectability Signal Definitions

## Signal 1: Structured Data Quality (25%)

### What agents look for:
- Schema.org JSON-LD on key pages
- Correct @type for business (LocalBusiness, Restaurant, MedicalBusiness, etc.)
- All recommended properties populated
- No validation errors

### Scoring:
| Criteria | Points |
|----------|--------|
| JSON-LD present | +20 |
| Correct @type | +15 |
| Name, URL, description | +15 |
| Address/geo complete | +15 |
| Opening hours | +10 |
| Price range / offers | +15 |
| No validation errors | +10 |

## Signal 2: Review/Rating Signals (20%)

### What agents look for:
- AggregateRating in structured data
- Minimum review count (threshold: 10+)
- Rating value (4.0+ preferred)
- Recency of reviews (within 6 months)
- Multi-platform consistency (Google, Naver, etc.)

### Scoring:
| Criteria | Points |
|----------|--------|
| AggregateRating present | +20 |
| Rating >= 4.0 | +20 |
| Review count >= 50 | +20 |
| Reviews within 3 months | +20 |
| Cross-platform consistent | +20 |

## Signal 3: Information Completeness (20%)

### Required attributes by industry:

**Restaurant:** menu, price range, cuisine type, hours, reservation method
**Clinic:** specialties, doctors, insurance accepted, hours, booking
**Academy:** courses, pricing, schedule, instructors, certifications
**E-commerce:** products, prices, shipping, returns, stock status
**SaaS:** features, pricing tiers, free trial, integrations, support

### Scoring:
- Each missing required attribute: -15 points
- Each optional attribute present: +5 points (max +20)

## Signal 4: API/Booking Availability (15%)

### Levels:
| Level | Score | Description |
|-------|-------|-------------|
| Direct API | 100 | Agent can transact programmatically |
| Booking widget | 70 | Embeddable booking (Calendly, Tock, etc.) |
| Online form | 50 | Agent can fill and submit |
| Phone/email only | 20 | Agent must hand off to human |
| No action possible | 0 | Dead end |

## Signal 5: Trust Signals (10%)

- Years in business (from foundingDate)
- Certifications / awards mentioned
- Professional associations
- Media mentions / press coverage
- Government registrations (사업자등록)

## Signal 6: Freshness (10%)

- dateModified within 30 days: 100
- dateModified within 90 days: 70
- dateModified within 180 days: 40
- Older or missing: 10

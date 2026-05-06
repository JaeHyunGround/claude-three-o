---
name: seo-schema
description: >
  Schema.org structured data detection, validation, and generation in JSON-LD.
  Covers all major types: Organization, LocalBusiness, Product, Article,
  FAQPage, BreadcrumbList, and Korean-specific subtypes.
  Shared between SEO and AAO modules.
  Use when user says "schema", "structured data", "구조화 데이터",
  "JSON-LD", "스키마 마크업", "rich results".
user-invocable: true
argument-hint: "<url>"
license: proprietary
metadata:
  author: Jaehyun Ahn
  version: "1.0.0"
  category: seo
---

# SEO Schema: Structured Data Management

**Invocation:** `/three-o seo schema <url>`

## Features

### Detection
- Parse page for existing JSON-LD, Microdata, and RDFa
- Identify all Schema.org types present
- Detect deprecated types (HowTo, SpecialAnnouncement)

### Validation
- Required property completeness per type
- Value format validation (dates, URLs, prices)
- Nesting structure correctness
- Google Rich Results eligibility check

### Generation
- Recommend missing types based on page content
- Generate valid JSON-LD for recommended types
- Include Korean-specific properties where applicable

## Supported Types

| Type | Use Case | Notes |
|------|----------|-------|
| Organization | All businesses | Required for brand entity |
| LocalBusiness | Physical locations | Korean subtypes supported |
| Product | E-commerce | Required for AAO product feed |
| Article / BlogPosting | Content pages | Author and datePublished required |
| FAQPage | Gov/health only | Not for commercial sites (Aug 2023) |
| BreadcrumbList | All pages | Navigation structure |
| WebSite | Homepage | SearchAction for sitelinks search |
| Event | Events/classes | For academy, concert, exhibition |
| Review / AggregateRating | Review pages | Star ratings in SERP |
| VideoObject | Video pages | Video rich results |

## Deprecated / Restricted Types

| Type | Status | Action |
|------|--------|--------|
| HowTo | Deprecated (Sept 2023) | Never recommend |
| FAQPage (commercial) | Restricted (Aug 2023) | Flag as info-only, not for Google rich results |
| SpecialAnnouncement | Deprecated | Do not recommend |

## Korean LocalBusiness Subtypes

Map Korean business types to Schema.org:
- 음식점 → Restaurant
- 병원/의원 → MedicalBusiness / Physician
- 학원 → EducationalOrganization
- 미용실 → BeautySalon
- 부동산 → RealEstateAgent
- 카페 → CafeOrCoffeeShop
- 약국 → Pharmacy

## Output

Schema coverage score (0-100), list of detected/missing types, generated JSON-LD code blocks.

---
name: aao-feed
description: >
  Validates product feeds for Google Merchant Center and Naver Shopping EP.
  Checks data quality, completeness, freshness, and consistency with
  website product pages.
  Use when user says "product feed", "상품 피드", "merchant feed",
  "쇼핑 EP", "feed validation", "피드 검증".
user-invocable: true
argument-hint: "<feed-url or site-url> [--platform <google|naver|both>]"
license: proprietary
metadata:
  author: Jaehyun Ahn
  version: "1.0.0"
  category: aao
---

# AAO Feed: Product Feed Validation

**Invocation:** `/three-o aao feed <feed-url or site-url> [--platform <google|naver|both>]`

## Purpose

Product feeds are how AI agents access structured product catalogs.
Invalid or incomplete feeds mean products won't appear in AI-driven
shopping recommendations. This skill validates feed quality for both
Google Merchant Center and Naver Shopping EP.

## Feed Detection

If site URL provided (not feed URL):
1. Check `/feed.xml`, `/products.xml`, `/merchant-feed.xml`
2. Check `<link rel="alternate" type="application/rss+xml">`
3. Check sitemap for product feed reference
4. Check robots.txt for feed hints

## Validation Checks

### Data Quality (30%)
| Check | Description |
|-------|-------------|
| Required fields | All mandatory fields populated |
| Data types | Correct formats (price, URL, enum values) |
| Character limits | Within platform max lengths |
| Encoding | UTF-8, special characters handled |
| No HTML in text | Plain text in title/description |

### Completeness (25%)
| Check | Description |
|-------|-------------|
| Product coverage | % of site products in feed |
| Image availability | All products have valid images |
| Category mapping | Correct taxonomy applied |
| Variant handling | Color/size variants properly grouped |
| Optional fields | Recommended fields populated |

### Freshness (25%)
| Check | Description |
|-------|-------------|
| Last modified | Feed updated within 24 hours |
| Price accuracy | Feed prices match website |
| Stock accuracy | Availability status current |
| New products | Recently added products included |
| Removed products | Discontinued items removed |

### Platform Compliance (20%)
| Check | Description |
|-------|-------------|
| Google requirements | Meets Merchant Center specs |
| Naver EP format | Matches Naver EP specification |
| Error-free parsing | No XML/TSV parse errors |
| Schema validation | Passes platform validator |

## Cross-Check: Feed vs Website

For a sample of products (10-20), verify:
- Price matches between feed and product page
- Availability status matches
- Title/description consistent
- Image URLs resolve correctly
- Product URL accessible and correct

## Output Format

```
Product Feed Validation: [url]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Feed Score: XX/100
Platform: [Google/Naver/Both]

Feed Statistics:
  Total products: XX
  Valid: XX (XX%)
  Errors: XX
  Warnings: XX

Dimension Scores:
  Data Quality:        XX/100
  Completeness:        XX/100
  Freshness:           XX/100
  Platform Compliance: XX/100

Critical Errors:
  [product_id] — [error description]
  ...

Website Consistency:
  Checked: XX products
  Matches: XX (XX%)
  Mismatches: XX

Recommendations:
  1. [priority fix]
  ...
```

## Reference Files

Load on-demand:
- `references/google-merchant-spec.md` — Google feed field requirements
- `references/naver-ep-spec.md` — Naver EP feed format details

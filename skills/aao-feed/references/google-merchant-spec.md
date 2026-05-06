<!-- Updated: 2026-05-04 -->
# Google Merchant Center Feed Specification

## Required Fields (All Products)

| Field | Format | Max Length | Notes |
|-------|--------|-----------|-------|
| id | String | 50 | Unique across feed |
| title | String | 150 | Clear, descriptive |
| description | String | 5000 | No HTML tags |
| link | URL | 2000 | Product page URL |
| image_link | URL | 2000 | Min 100x100px |
| availability | Enum | — | in_stock / out_of_stock / preorder / backorder |
| price | Number + Currency | — | "29900 KRW" format |
| brand | String | 70 | Required for most categories |
| condition | Enum | — | new / refurbished / used |

## Category-Specific Required Fields

### Apparel
| Field | Format |
|-------|--------|
| gender | male / female / unisex |
| age_group | newborn / infant / toddler / kids / adult |
| color | String |
| size | String |

### Electronics
| Field | Format |
|-------|--------|
| gtin | 8/12/13/14 digits |
| mpn | String (if no gtin) |

## Recommended Fields

| Field | Description | Impact |
|-------|-------------|--------|
| additional_image_link | Up to 10 extra images | Higher engagement |
| sale_price | Discounted price | Shows savings |
| sale_price_effective_date | Sale period | Time urgency |
| google_product_category | Google taxonomy | Better matching |
| product_type | Custom category | Reporting |
| shipping | Shipping details | Purchase clarity |
| shipping_weight | For calculated shipping | Accuracy |
| return_policy_label | Return info | Trust signal |
| loyalty_points | Points earned | Korean market |

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| Missing price | Price field empty | Add price to all products |
| Invalid availability | Typo in enum value | Use exact enum strings |
| Image too small | Below 100x100 | Use larger product images |
| Duplicate ID | Same id for variants | Use unique IDs per variant |
| HTML in description | Markup in text field | Strip all HTML tags |
| Currency mismatch | KRW vs USD confusion | Match target country currency |
| Expired sale price | Past effective date | Remove expired sales |

## Feed Submission

- Format: XML (RSS 2.0), TSV, or Google Sheets
- Update: Minimum daily (every 30 days max)
- Size limit: 2GB uncompressed
- Compression: gzip supported
- Encoding: UTF-8

## Korean Market Notes

- Currency: KRW (no decimals)
- Shipping: Consider "도서산간" (island/mountain areas)
- Size: Korean sizing system where applicable
- Brand: Include Korean name if different from English

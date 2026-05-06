<!-- Updated: 2026-05-04 -->
# Product Feed Specifications

## Google Merchant Center Feed

### Required Fields:
| Field | Description | Format |
|-------|-------------|--------|
| id | Unique product ID | String (max 50) |
| title | Product title | String (max 150) |
| description | Product description | String (max 5000) |
| link | Product page URL | URL |
| image_link | Primary image | URL |
| availability | Stock status | in_stock / out_of_stock / preorder |
| price | Product price | Number + currency (e.g., "29900 KRW") |
| brand | Brand name | String |
| condition | Product condition | new / refurbished / used |

### Recommended Fields:
| Field | Description |
|-------|-------------|
| gtin | Global Trade Item Number |
| mpn | Manufacturer Part Number |
| google_product_category | Google taxonomy ID |
| product_type | Custom category path |
| additional_image_link | Extra images |
| sale_price | Discounted price |
| shipping | Shipping details |
| return_policy | Return policy info |

### Feed Format:
- XML (RSS 2.0 with Google namespace)
- TSV (tab-separated values)
- Update frequency: minimum daily

## Naver EP Feed (쇼핑 EP)

### Required Fields:
| Field | Description | Format |
|-------|-------------|--------|
| id | 상품 고유 ID | String |
| title | 상품명 | String (max 100) |
| price_pc | PC 판매가 | Number |
| price_mobile | 모바일 판매가 | Number |
| normal_price | 정상가 | Number |
| link | 상품 URL | URL |
| image_link | 대표 이미지 | URL |
| category_name1-4 | 카테고리 경로 | String |
| naver_category | 네이버 카테고리 ID | Number |
| condition | 상품 상태 | 새상품/중고 |
| import_flag | 수입 여부 | Y/N |

### Naver-Specific Fields:
| Field | Description |
|-------|-------------|
| card_event | 카드 혜택 |
| interest_free_event | 무이자 할부 |
| point_event | 포인트 적립 |
| delivery_fee | 배송비 |
| review_count | 리뷰 수 |
| seller_grade | 판매자 등급 |

### Feed Format:
- TSV (EP file format)
- XML (optional)
- Update: minimum every 6 hours for price/stock

## Feed Quality Checks

| Check | Pass Criteria |
|-------|--------------|
| Field completeness | All required fields populated |
| Price accuracy | Feed price matches website (±1%) |
| Availability sync | Feed status matches website |
| Image accessibility | All image URLs return 200 |
| URL validity | All product links accessible |
| Category mapping | Correct taxonomy assigned |
| Update frequency | Feed refreshed within 24h |
| Duplicate check | No duplicate product IDs |

## Feed-Website Consistency

Agent-critical: feed data must match website data.
Mismatches confuse agents and reduce trust.

| Mismatch Type | Severity | Agent Impact |
|---------------|----------|-------------|
| Price differs | Critical | Agent quotes wrong price |
| Stock wrong | Critical | Agent recommends unavailable |
| Title differs | Medium | Agent confusion in comparison |
| Image missing | Low | Reduced presentation quality |

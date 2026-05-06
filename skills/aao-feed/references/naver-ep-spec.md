<!-- Updated: 2026-05-04 -->
# Naver Shopping EP Feed Specification

## EP File Format

- Encoding: UTF-8 (with BOM optional)
- Format: TSV (tab-separated values)
- Line ending: CRLF or LF
- Header row: Required (field names)
- Update frequency: Every 6 hours minimum for price/stock

## Required Fields

| Field | Korean | Format | Notes |
|-------|--------|--------|-------|
| id | 상품ID | String | Unique identifier |
| title | 상품명 | String (100) | No special chars spam |
| price_pc | PC 판매가 | Integer | KRW, no commas |
| price_mobile | 모바일 판매가 | Integer | KRW, no commas |
| normal_price | 정상가 | Integer | Before discount |
| link | 상품URL | URL | Full absolute URL |
| image_link | 이미지URL | URL | Min 200x200px |
| category_name1 | 대분류 | String | Top category |
| category_name2 | 중분류 | String | Sub category |
| naver_category | 네이버 카테고리 | Integer | Naver category ID |
| condition | 상품상태 | Enum | 새상품/중고/리퍼 |
| import_flag | 수입여부 | Enum | Y/N |

## Recommended Fields

| Field | Korean | Description |
|-------|--------|-------------|
| category_name3 | 소분류 | Level 3 category |
| category_name4 | 세분류 | Level 4 category |
| brand | 브랜드 | Brand name |
| maker | 제조사 | Manufacturer |
| model_name | 모델명 | Model number |
| origin | 원산지 | Country of origin |
| delivery_fee | 배송비 | Shipping cost (integer) |
| delivery_type | 배송방법 | 택배/직접배송/무료 |
| interest_free_event | 무이자 할부 | Installment info |
| point_event | 포인트 | Point accumulation |
| extra_image_link | 추가이미지 | Additional images (pipe-separated) |
| review_count | 리뷰수 | Number of reviews |
| seller_grade | 판매자등급 | Seller tier |
| min_purchase_qty | 최소구매수량 | Minimum order |
| option_detail | 옵션상세 | Color/size options |

## Title Rules (Naver-Specific)

### Allowed:
- Product name + key attributes
- Brand + model + specification

### Prohibited:
- Excessive special characters (★, ♥, etc.)
- Keyword stuffing
- Superlatives without basis ("최고", "1위")
- Misleading discount claims
- Seller name in title
- Category name repeated

### Character limit: 100 characters (Korean counts as 1 char)

## Category Mapping

Naver uses its own product taxonomy (~12,000 categories).
- Find category: `https://shopping.naver.com/category/`
- API: Naver Commerce API category search
- Must use leaf-level category ID (most specific)

## Common Rejection Reasons

| Reason | Korean | Fix |
|--------|--------|-----|
| Price mismatch | 가격 불일치 | Sync feed with website |
| Out of stock | 품절 상품 | Remove or mark unavailable |
| Invalid image | 이미지 오류 | Use valid, accessible image URL |
| Wrong category | 카테고리 불일치 | Map to correct Naver category |
| Title violation | 상품명 위반 | Remove special chars, keyword spam |
| Duplicate product | 중복 상품 | Remove duplicate entries |
| Adult content unmarked | 성인상품 미표시 | Add adult flag if applicable |

## Naver EP vs Google Merchant Differences

| Aspect | Naver EP | Google Merchant |
|--------|----------|----------------|
| Format | TSV primary | XML/TSV/Sheets |
| Currency | KRW only (integer) | Multi-currency |
| Mobile price | Separate field | Same as desktop |
| Category | Naver taxonomy | Google taxonomy |
| Update | 6-hour minimum | Daily minimum |
| Encoding | UTF-8 | UTF-8 |
| Validation | Strict on title rules | Strict on data types |

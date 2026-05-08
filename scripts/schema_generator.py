"""Schema.org JSON-LD auto-generator for Three-O platform.

Detects page industry, extracts structured data from HTML content,
selects the appropriate template, and outputs ready-to-paste JSON-LD.
"""

import argparse
import json
import os
import re
import sys

from validate_url import validate_url
from fetch_page import fetch_page
from aao_selectability import detect_industry

SCHEMA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "schema")

INDUSTRY_TEMPLATE_MAP = {
    "restaurant": "restaurant.json",
    "ecommerce": "product.json",
    "clinic": "clinic.json",
    "hotel": "hotel.json",
    "education": "course.json",
    "saas": "software.json",
    "general": "local-business.json",
}

PHONE_PATTERN = re.compile(
    r'(?:tel:|href=["\']tel:)?'
    r'(0\d{1,2}[-.\s]?\d{3,4}[-.\s]?\d{4}'
    r'|\+82[-.\s]?\d{1,2}[-.\s]?\d{3,4}[-.\s]?\d{4})',
    re.IGNORECASE,
)

PRICE_PATTERN = re.compile(
    r'(\d{1,3}(?:[,.]?\d{3})+)\s*(?:원|₩|KRW|won)',
    re.IGNORECASE,
)

ADDRESS_PATTERN = re.compile(
    r'((?:서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주)'
    r'(?:특별시|광역시|특별자치시|도|특별자치도)?'
    r'\s*.{2,30}?'
    r'(?:\d{1,5}(?:[-번]\s*(?:길|로))?.{0,20}?))',
)

POSTAL_CODE_PATTERN = re.compile(r'\b(\d{5})\b')

EMAIL_PATTERN = re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+')

TIME_PATTERN = re.compile(
    r'(\d{1,2}:\d{2})\s*[-~]\s*(\d{1,2}:\d{2})'
)

RATING_PATTERN = re.compile(
    r'(\d(?:\.\d)?)\s*/\s*5|'
    r'(?:평점|rating|별점)\s*[:：]?\s*(\d(?:\.\d)?)|'
    r'(\d(?:\.\d)?)\s*(?:점(?![가-힣])|stars?)',
    re.IGNORECASE,
)

REVIEW_COUNT_PATTERN = re.compile(
    r'(?:리뷰|review|후기|평가)\s*[:：]?\s*(\d[\d,]*)|'
    r'(\d[\d,]*)\s*(?:개의?\s*)?(?:리뷰|review|후기|평가)',
    re.IGNORECASE,
)

SOCIAL_PATTERNS = {
    "instagram": re.compile(r'https?://(?:www\.)?instagram\.com/[\w.]+/?', re.IGNORECASE),
    "youtube": re.compile(r'https?://(?:www\.)?youtube\.com/(?:@|channel/)[\w-]+/?', re.IGNORECASE),
    "naver_blog": re.compile(r'https?://blog\.naver\.com/[\w-]+/?', re.IGNORECASE),
    "facebook": re.compile(r'https?://(?:www\.)?facebook\.com/[\w.-]+/?', re.IGNORECASE),
    "twitter": re.compile(r'https?://(?:www\.)?(?:twitter|x)\.com/[\w]+/?', re.IGNORECASE),
    "linkedin": re.compile(r'https?://(?:www\.)?linkedin\.com/(?:company|in)/[\w-]+/?', re.IGNORECASE),
}


def load_template(template_name: str) -> dict:
    """Load a schema template from the schema directory."""
    path = os.path.join(SCHEMA_DIR, template_name)
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_title(html: str) -> str:
    """Extract page title."""
    match = re.search(r'<title[^>]*>(.*?)</title>', html, re.DOTALL | re.IGNORECASE)
    if match:
        title = match.group(1).strip()
        title = re.sub(r'\s*[-|–—]\s*.*$', '', title)
        return title
    og = re.search(r'<meta[^>]*property=["\']og:title["\'][^>]*content=["\']([^"\']+)', html, re.IGNORECASE)
    if og:
        return og.group(1).strip()
    h1 = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL | re.IGNORECASE)
    if h1:
        return re.sub(r'<[^>]+>', '', h1.group(1)).strip()
    return ""


def extract_description(html: str) -> str:
    """Extract meta description."""
    match = re.search(
        r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)',
        html, re.IGNORECASE,
    )
    if match:
        return match.group(1).strip()
    og = re.search(
        r'<meta[^>]*property=["\']og:description["\'][^>]*content=["\']([^"\']+)',
        html, re.IGNORECASE,
    )
    if og:
        return og.group(1).strip()
    return ""


def extract_image(html: str) -> str:
    """Extract primary image URL."""
    og = re.search(
        r'<meta[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)',
        html, re.IGNORECASE,
    )
    if og:
        return og.group(1).strip()
    img = re.search(r'<img[^>]*src=["\']([^"\']+)', html, re.IGNORECASE)
    if img:
        return img.group(1).strip()
    return ""


def extract_phone(html: str) -> str:
    """Extract phone number."""
    text = re.sub(r'<[^>]+>', ' ', html)
    match = PHONE_PATTERN.search(text)
    if match:
        return match.group(1) if match.group(1) else match.group(0)
    return ""


def extract_prices(html: str) -> list:
    """Extract price values from page."""
    text = re.sub(r'<[^>]+>', ' ', html)
    matches = PRICE_PATTERN.findall(text)
    prices = []
    for m in matches:
        try:
            prices.append(int(m.replace(",", "").replace(".", "")))
        except ValueError:
            continue
    return sorted(set(prices))


def extract_address(html: str) -> dict:
    """Extract address components."""
    text = re.sub(r'<[^>]+>', ' ', html)
    result = {"street": "", "city": "", "region": "", "postal_code": ""}

    match = ADDRESS_PATTERN.search(text)
    if match:
        full_addr = match.group(1).strip()
        region_match = re.match(
            r'(서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주)'
            r'(?:특별시|광역시|특별자치시|도|특별자치도)?',
            full_addr,
        )
        if region_match:
            result["region"] = region_match.group(0)
            rest = full_addr[region_match.end():].strip()
            city_match = re.match(r'(\S+?[시군구])', rest)
            if city_match:
                result["city"] = city_match.group(1)
                result["street"] = rest[city_match.end():].strip()
            else:
                result["street"] = rest
        else:
            result["street"] = full_addr

    postal = POSTAL_CODE_PATTERN.search(text)
    if postal:
        result["postal_code"] = postal.group(1)

    return result


def extract_hours(html: str) -> tuple:
    """Extract opening/closing hours. Returns (open_time, close_time)."""
    text = re.sub(r'<[^>]+>', ' ', html)
    match = TIME_PATTERN.search(text)
    if match:
        return match.group(1), match.group(2)
    return "", ""


def extract_rating(html: str) -> tuple:
    """Extract rating value and review count. Returns (rating, review_count)."""
    text = re.sub(r'<[^>]+>', ' ', html)

    rating = ""
    match = RATING_PATTERN.search(text)
    if match:
        rating = next((g for g in match.groups() if g), "")

    review_count = ""
    match = REVIEW_COUNT_PATTERN.search(text)
    if match:
        raw = next((g for g in match.groups() if g), "")
        review_count = raw.replace(",", "")

    return rating, review_count


def extract_social_links(html: str) -> list:
    """Extract social media profile URLs."""
    links = []
    for _platform, pattern in SOCIAL_PATTERNS.items():
        matches = pattern.findall(html)
        links.extend(matches)
    return list(dict.fromkeys(links))


def extract_cuisine(html: str) -> str:
    """Extract cuisine type for restaurants."""
    text_lower = html.lower()
    cuisine_map = {
        "한식": "Korean", "일식": "Japanese", "중식": "Chinese",
        "양식": "Western", "이탈리안": "Italian", "프렌치": "French",
        "태국": "Thai", "베트남": "Vietnamese", "인도": "Indian",
        "멕시칸": "Mexican", "피자": "Pizza", "치킨": "Chicken",
        "카페": "Cafe", "베이커리": "Bakery", "디저트": "Dessert",
        "korean": "Korean", "japanese": "Japanese", "chinese": "Chinese",
        "italian": "Italian", "french": "French", "thai": "Thai",
    }
    for keyword, cuisine in cuisine_map.items():
        if keyword in text_lower:
            return cuisine
    return ""


def extract_specialty(html: str) -> str:
    """Extract medical specialty for clinics."""
    text_lower = html.lower()
    specialty_map = {
        "치과": "Dentistry", "피부과": "Dermatology", "성형외과": "PlasticSurgery",
        "안과": "Ophthalmology", "이비인후과": "Otolaryngology",
        "정형외과": "Orthopedics", "내과": "InternalMedicine",
        "소아과": "Pediatrics", "산부인과": "ObstetricsGynecology",
        "한의원": "TraditionalKoreanMedicine", "정신과": "Psychiatry",
        "비뇨기과": "Urology", "신경외과": "Neurosurgery",
    }
    for keyword, spec in specialty_map.items():
        if keyword in text_lower:
            return spec
    return ""


def _price_range_label(prices: list) -> str:
    """Convert price list to price range label."""
    if not prices:
        return ""
    low = min(prices)
    if low < 10000:
        return "₩"
    if low < 30000:
        return "₩₩"
    if low < 100000:
        return "₩₩₩"
    return "₩₩₩₩"


def extract_page_data(html: str, url: str) -> dict:
    """Extract all available structured data from page HTML."""
    prices = extract_prices(html)
    rating, review_count = extract_rating(html)
    open_time, close_time = extract_hours(html)
    address = extract_address(html)

    return {
        "name": extract_title(html),
        "url": url,
        "description": extract_description(html),
        "image": extract_image(html),
        "phone": extract_phone(html),
        "prices": prices,
        "price_range": _price_range_label(prices),
        "address": address,
        "rating": rating,
        "review_count": review_count,
        "open_time": open_time,
        "close_time": close_time,
        "social_links": extract_social_links(html),
        "cuisine": extract_cuisine(html),
        "specialty": extract_specialty(html),
    }


def fill_template(template: dict, data: dict, industry: str) -> dict:
    """Fill a schema template with extracted page data."""
    result = json.loads(json.dumps(template))
    raw = json.dumps(result, ensure_ascii=False)

    field_mapping = _build_field_mapping(data, industry)

    for placeholder, value in field_mapping.items():
        raw = raw.replace("{{" + placeholder + "}}", str(value))

    result = json.loads(raw)
    _clean_unfilled(result)
    _fill_same_as(result, data.get("social_links", []))

    return result


def _build_field_mapping(data: dict, industry: str) -> dict:
    """Build placeholder-to-value mapping based on industry."""
    addr = data.get("address", {})
    prices = data.get("prices", [])

    common = {
        "website_url": data.get("url", ""),
        "description": data.get("description", ""),
        "image_url": data.get("image", ""),
        "phone": data.get("phone", ""),
        "street": addr.get("street", ""),
        "city": addr.get("city", ""),
        "region": addr.get("region", ""),
        "postal_code": addr.get("postal_code", ""),
        "rating": data.get("rating", ""),
        "review_count": data.get("review_count", ""),
        "price_range": data.get("price_range", ""),
        "weekday_open": data.get("open_time", ""),
        "weekday_close": data.get("close_time", ""),
        "weekend_open": data.get("open_time", ""),
        "weekend_close": data.get("close_time", ""),
        "latitude": "",
        "longitude": "",
    }

    industry_fields = {
        "restaurant": {
            "restaurant_name": data.get("name", ""),
            "cuisine_type": data.get("cuisine", ""),
            "menu_url": data.get("url", "") + "/menu" if data.get("url") else "",
            "reservation_url": data.get("url", ""),
        },
        "ecommerce": {
            "product_name": data.get("name", ""),
            "product_url": data.get("url", ""),
            "brand_name": "",
            "seller_name": "",
            "sku": "",
            "price": str(prices[0]) if prices else "",
        },
        "clinic": {
            "clinic_name": data.get("name", ""),
            "specialty": data.get("specialty", ""),
            "reservation_url": data.get("url", ""),
        },
        "hotel": {
            "hotel_name": data.get("name", ""),
            "star_rating": "",
            "checkin_time": "15:00",
            "checkout_time": "11:00",
            "room_count": "",
            "booking_url": data.get("url", ""),
        },
        "education": {
            "course_name": data.get("name", ""),
            "provider_name": "",
            "provider_url": data.get("url", ""),
            "instructor_name": "",
            "level": "Beginner",
            "price": str(prices[0]) if prices else "",
            "enrollment_url": data.get("url", ""),
        },
        "saas": {
            "app_name": data.get("name", ""),
            "category": "BusinessApplication",
            "low_price": str(min(prices)) if prices else "",
            "high_price": str(max(prices)) if prices else "",
            "plan_count": str(len(prices)) if prices else "",
            "trial_url": data.get("url", ""),
            "company_name": "",
            "company_url": data.get("url", ""),
        },
        "general": {
            "business_name": data.get("name", ""),
            "booking_url": data.get("url", ""),
        },
    }

    mapping = {**common, **industry_fields.get(industry, {})}
    return mapping


def _clean_unfilled(obj):
    """Remove fields that still contain unfilled {{placeholders}} or empty values."""
    if isinstance(obj, dict):
        keys_to_remove = []
        for key, value in obj.items():
            if isinstance(value, str) and (
                value.startswith("{{") or value == ""
            ):
                keys_to_remove.append(key)
            elif isinstance(value, (dict, list)):
                _clean_unfilled(value)
                if isinstance(value, dict) and not any(
                    v for k, v in value.items() if k != "@type"
                ):
                    keys_to_remove.append(key)
        for key in keys_to_remove:
            del obj[key]
    elif isinstance(obj, list):
        i = 0
        while i < len(obj):
            item = obj[i]
            if isinstance(item, str) and (item.startswith("{{") or item == ""):
                obj.pop(i)
            else:
                _clean_unfilled(item)
                i += 1


def _fill_same_as(obj: dict, social_links: list):
    """Fill sameAs with discovered social links."""
    if "sameAs" in obj:
        if social_links:
            obj["sameAs"] = social_links
        else:
            del obj["sameAs"]


def generate_schema(html: str, url: str, industry_override: str = "") -> dict:
    """Generate Schema.org JSON-LD from page HTML.

    Args:
        html: Page HTML content.
        url: Page URL.
        industry_override: Force a specific industry instead of auto-detecting.

    Returns:
        dict with keys: success, industry, template, schema, extracted_fields,
        coverage, suggestions.
    """
    industry = industry_override if industry_override else detect_industry(html)
    template_name = INDUSTRY_TEMPLATE_MAP.get(industry, "local-business.json")
    template = load_template(template_name)

    if not template:
        return {
            "success": False,
            "error": f"Template not found: {template_name}",
        }

    data = extract_page_data(html, url)
    schema = fill_template(template, data, industry)

    total_fields = _count_template_fields(template)
    filled_fields = _count_filled_fields(schema)
    coverage = round(filled_fields / max(total_fields, 1) * 100, 1)

    suggestions = _generate_suggestions(data, industry, coverage)

    return {
        "success": True,
        "industry": industry,
        "template": template_name,
        "schema": schema,
        "extracted_fields": filled_fields,
        "total_fields": total_fields,
        "coverage": coverage,
        "suggestions": suggestions,
    }


def _count_template_fields(template: dict, _depth: int = 0) -> int:
    """Count fillable fields in template (those with {{placeholder}})."""
    count = 0
    if _depth > 10:
        return count
    for _key, value in template.items():
        if isinstance(value, str) and "{{" in value:
            count += 1
        elif isinstance(value, dict):
            count += _count_template_fields(value, _depth + 1)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    count += _count_template_fields(item, _depth + 1)
    return count


def _count_filled_fields(schema: dict, _depth: int = 0) -> int:
    """Count non-empty value fields (excluding @type, @context)."""
    count = 0
    if _depth > 10:
        return count
    for key, value in schema.items():
        if key.startswith("@"):
            continue
        if isinstance(value, str) and value and not value.startswith("{{"):
            count += 1
        elif isinstance(value, bool):
            count += 1
        elif isinstance(value, (int, float)):
            count += 1
        elif isinstance(value, dict):
            count += _count_filled_fields(value, _depth + 1)
        elif isinstance(value, list) and value:
            count += 1
    return count


def _generate_suggestions(data: dict, industry: str, coverage: float) -> list:
    """Generate improvement suggestions based on missing data."""
    suggestions = []

    if not data.get("phone"):
        suggestions.append({
            "field": "telephone",
            "message": "전화번호를 페이지에 표시하면 스키마에 자동 포함됩니다",
            "impact": "high",
        })

    if not data.get("rating"):
        suggestions.append({
            "field": "aggregateRating",
            "message": "리뷰/평점 데이터가 없습니다. 리뷰 시스템을 추가하세요",
            "impact": "high",
        })

    addr = data.get("address", {})
    if not addr.get("street"):
        suggestions.append({
            "field": "address",
            "message": "주소 정보가 감지되지 않았습니다. 구조화된 형식으로 표시하세요",
            "impact": "high" if industry in ("restaurant", "clinic", "hotel") else "medium",
        })

    if not data.get("description"):
        suggestions.append({
            "field": "description",
            "message": "meta description이 없습니다. 80-160자 설명을 추가하세요",
            "impact": "medium",
        })

    if not data.get("image"):
        suggestions.append({
            "field": "image",
            "message": "OG 이미지가 없습니다. 대표 이미지를 설정하세요",
            "impact": "medium",
        })

    if not data.get("social_links"):
        suggestions.append({
            "field": "sameAs",
            "message": "소셜 미디어 링크가 없습니다. SNS 프로필을 연결하세요",
            "impact": "low",
        })

    if industry == "restaurant" and not data.get("cuisine"):
        suggestions.append({
            "field": "servesCuisine",
            "message": "요리 유형이 감지되지 않았습니다. '한식', '일식' 등을 표시하세요",
            "impact": "medium",
        })

    if industry == "clinic" and not data.get("specialty"):
        suggestions.append({
            "field": "medicalSpecialty",
            "message": "진료과목이 감지되지 않았습니다. '치과', '피부과' 등을 표시하세요",
            "impact": "high",
        })

    if coverage < 50:
        suggestions.append({
            "field": "_overall",
            "message": f"스키마 커버리지 {coverage}% — 페이지에 더 많은 구조화 정보를 추가하세요",
            "impact": "high",
        })

    return suggestions


def format_jsonld_output(schema: dict) -> str:
    """Format schema as embeddable <script> tag."""
    json_str = json.dumps(schema, indent=2, ensure_ascii=False)
    return f'<script type="application/ld+json">\n{json_str}\n</script>'


def format_report(result: dict) -> str:
    """Format generation result as readable report."""
    if not result.get("success"):
        return f"Error: {result.get('error', 'Unknown error')}"

    lines = [
        f"Industry: {result['industry']}",
        f"Template: {result['template']}",
        f"Coverage: {result['coverage']}% ({result['extracted_fields']}/{result['total_fields']} fields)",
        "",
        "=== Generated JSON-LD ===",
        format_jsonld_output(result["schema"]),
    ]

    if result.get("suggestions"):
        lines.append("")
        lines.append("=== Suggestions ===")
        for s in result["suggestions"]:
            icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(s["impact"], "⚪")
            lines.append(f"  {icon} [{s['field']}] {s['message']}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Schema.org JSON-LD auto-generator")
    parser.add_argument("url", help="URL to generate schema for")
    parser.add_argument("--industry", default="", help="Override industry detection")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--script-tag", action="store_true", help="Output as <script> tag only")
    args = parser.parse_args()

    validation = validate_url(args.url)
    if not validation["valid"]:
        print(f"Error: {validation['error']}", file=sys.stderr)
        sys.exit(1)

    page = fetch_page(args.url)
    if not page["success"]:
        print(f"Error: {page['error']}", file=sys.stderr)
        sys.exit(1)

    result = generate_schema(page["html"], args.url, args.industry)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif args.script_tag:
        if result["success"]:
            print(format_jsonld_output(result["schema"]))
        else:
            print(f"Error: {result.get('error')}", file=sys.stderr)
            sys.exit(1)
    else:
        print(format_report(result))


if __name__ == "__main__":
    main()

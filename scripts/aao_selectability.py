"""Agent selectability scoring script for Three-O platform.

Scores how likely AI agents (shopping assistants, booking agents, recommendation
engines) are to select and recommend a business/page. Uses signal correlation,
industry-aware weighting, and cross-validation between structured data and
actual page content.
"""

import argparse
import json
import re
import sys

from validate_url import validate_url
from fetch_page import fetch_page


BASE_WEIGHTS = {
    "structured_data": 0.25,
    "reviews_ratings": 0.20,
    "info_completeness": 0.20,
    "api_booking": 0.15,
    "trust_signals": 0.10,
    "freshness": 0.10,
}

INDUSTRY_WEIGHT_ADJUSTMENTS = {
    "restaurant": {"reviews_ratings": +0.08, "info_completeness": +0.05, "api_booking": -0.08, "freshness": -0.05},
    "ecommerce": {"api_booking": +0.10, "structured_data": +0.05, "reviews_ratings": -0.05, "freshness": -0.10},
    "clinic": {"trust_signals": +0.10, "info_completeness": +0.05, "api_booking": -0.10, "freshness": -0.05},
    "hotel": {"api_booking": +0.12, "reviews_ratings": +0.05, "trust_signals": -0.07, "freshness": -0.10},
    "education": {"info_completeness": +0.08, "trust_signals": +0.07, "api_booking": -0.10, "freshness": -0.05},
    "saas": {"api_booking": +0.10, "structured_data": +0.05, "reviews_ratings": -0.10, "freshness": -0.05},
    "agency": {"trust_signals": +0.08, "info_completeness": +0.07, "reviews_ratings": -0.10, "freshness": -0.05},
    "realestate": {"info_completeness": +0.08, "structured_data": +0.05, "api_booking": -0.08, "freshness": -0.05},
    "franchise": {"structured_data": +0.08, "info_completeness": +0.05, "api_booking": -0.08, "freshness": -0.05},
}

CORRELATION_BONUSES = [
    (["structured_data", "reviews_ratings"], 8, "Schema + reviews = verified social proof"),
    (["structured_data", "api_booking"], 10, "Schema + actions = agent-executable"),
    (["info_completeness", "structured_data"], 6, "Complete info backed by schema"),
    (["reviews_ratings", "trust_signals"], 5, "Reviews + trust = credible business"),
    (["api_booking", "freshness"], 4, "Active booking + fresh = operational"),
]

CORRELATION_PENALTIES = [
    (["structured_data", "info_completeness"], -8, "Schema claims data not found on page"),
    (["reviews_ratings", "trust_signals"], -5, "Reviews present but no trust signals"),
]

INDUSTRY_SIGNALS = {
    "restaurant": [r"(menu|메뉴|맛집|음식점|restaurant|cafe|카페|배달|reservation|예약)", r"(맛|요리|셰프|chef|food|dining)"],
    "ecommerce": [r"(cart|장바구니|buy|구매|shop|상품|product|price|가격|배송|shipping|결제)", r"(할인|sale|coupon|쿠폰)"],
    "clinic": [r"(진료|병원|의원|clinic|doctor|의사|치료|treatment|수술|surgery|예약)", r"(건강|health|medical|진단)"],
    "hotel": [r"(hotel|호텔|숙소|accommodation|room|객실|check-?in|체크인|booking|예약)", r"(숙박|리조트|resort|펜션)"],
    "education": [r"(학원|academy|course|수업|강의|lecture|수강|enrollment|등록)", r"(교육|학습|learning|강사|instructor)"],
    "saas": [r"(pricing|plan|subscribe|subscription|api|dashboard|trial|무료체험)", r"(enterprise|team|integration|연동)"],
    "agency": [
        r"(대행사|에이전시|광고대행|마케팅대행|종합광고|종합대행|홍보대행)",
        r"(포트폴리오|portfolio|case[\s-]?study|사례|캠페인|campaign|크리에이티브|creative)",
        r"(media\s*planning|미디어\s*플래닝|branding|브랜딩|IMC|PR|퍼포먼스\s*마케팅)",
        r"(클라이언트|client|광고주|our\s*work|our\s*team)",
    ],
    "realestate": [r"(매물|부동산|분양|아파트|오피스텔|real\s*estate|property|listing)", r"(평형|평수|시세|임대|전세|월세|매매)"],
    "franchise": [r"(가맹|프랜차이즈|franchise|체인|지점|branch|매장\s*안내|store\s*locator)", r"(가맹점|창업|본사|headquarters)"],
}

AGENCY_CONTEXT_PATTERNS = [
    r"(클라이언트|client|광고주)",
    r"(포트폴리오|portfolio|our\s*works?)",
    r"(대행|agency|에이전시)",
    r"(캠페인\s*사례|project|프로젝트)",
    r"(솔루션|solution|서비스\s*소개|service)",
]


def detect_industry(html: str) -> str:
    """Detect business industry from page content with disambiguation."""
    text_lower = html.lower()
    scores = {}
    for industry, patterns in INDUSTRY_SIGNALS.items():
        match_count = sum(len(re.findall(p, text_lower)) for p in patterns)
        if match_count > 0:
            scores[industry] = match_count

    if not scores:
        return "general"

    agency_score = scores.get("agency", 0)
    non_agency = {k: v for k, v in scores.items() if k != "agency"}
    industries_detected = sum(1 for v in non_agency.values() if v >= 2)

    if agency_score > 0:
        context_hits = sum(len(re.findall(p, text_lower)) for p in AGENCY_CONTEXT_PATTERNS)
        if context_hits >= 3:
            scores["agency"] = agency_score + context_hits * 2
        if industries_detected >= 3:
            scores["agency"] = scores.get("agency", 0) + industries_detected * 5

    return max(scores, key=scores.get)


def get_industry_weights(industry: str) -> dict:
    """Get dimension weights adjusted for detected industry."""
    weights = dict(BASE_WEIGHTS)
    if industry in INDUSTRY_WEIGHT_ADJUSTMENTS:
        adj = INDUSTRY_WEIGHT_ADJUSTMENTS[industry]
        for dim, delta in adj.items():
            weights[dim] = max(0.05, weights[dim] + delta)
        total = sum(weights.values())
        weights = {k: v / total for k, v in weights.items()}
    return weights


def score_structured_data(html: str) -> dict:
    """Score quality and completeness of structured data with cross-validation."""
    score = 0.0
    signals = []
    schema_claims = {}

    ld_blocks = re.findall(
        r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
        html, re.DOTALL | re.IGNORECASE
    )

    if not ld_blocks:
        return {"score": 0, "signals": ["No JSON-LD structured data found"], "claims": {}}

    score += 20
    signals.append(f"{len(ld_blocks)} JSON-LD block(s) found")

    actionable_types = {"Product", "Service", "LocalBusiness", "Restaurant",
                        "Organization", "Store", "MedicalBusiness", "Hotel",
                        "Course", "Event", "SoftwareApplication"}
    informational_types = {"Article", "WebPage", "BlogPosting", "FAQPage", "BreadcrumbList"}

    for block in ld_blocks:
        try:
            data = json.loads(block.strip())
            if isinstance(data, list):
                data = data[0] if data else {}
            schema_type = data.get("@type", "")

            if schema_type in actionable_types:
                score += 20
                signals.append(f"Actionable entity type: {schema_type}")
            elif schema_type in informational_types:
                score += 8
                signals.append(f"Informational type: {schema_type}")

            field_score = 0
            field_count = 0
            for field in ["name", "description", "url", "image", "logo",
                          "address", "location", "telephone", "email",
                          "priceRange", "offers", "openingHoursSpecification",
                          "openingHours", "aggregateRating", "review"]:
                if data.get(field):
                    field_score += 1
                    schema_claims[field] = data.get(field)
            field_count = field_score
            if field_count >= 8:
                score += 25
                signals.append(f"Rich schema ({field_count} fields populated)")
            elif field_count >= 5:
                score += 15
                signals.append(f"Moderate schema ({field_count} fields)")
            elif field_count >= 3:
                score += 8

            if data.get("potentialAction") or data.get("action"):
                score += 12
                signals.append("Schema.org Action defined (agent-executable)")

            if data.get("offers"):
                offers = data["offers"]
                if isinstance(offers, dict) and offers.get("price"):
                    score += 8
                elif isinstance(offers, list) and len(offers) > 0:
                    score += 8

        except (json.JSONDecodeError, IndexError, TypeError):
            continue

    verified = _cross_validate_schema(html, schema_claims)
    if verified["match_ratio"] >= 0.7:
        score += 10
        signals.append(f"Schema claims verified on page ({verified['match_ratio']:.0%} match)")
    elif verified["match_ratio"] < 0.3 and schema_claims:
        score -= 10
        signals.append(f"Schema claims poorly verified ({verified['match_ratio']:.0%} match)")

    return {"score": min(100, max(0, round(score))), "signals": signals, "claims": schema_claims}


def _cross_validate_schema(html: str, claims: dict) -> dict:
    """Verify schema claims against actual page content."""
    if not claims:
        return {"match_ratio": 0.5, "verified": [], "unverified": []}

    text = re.sub(r'<[^>]+>', ' ', html).lower()
    verified = []
    unverified = []

    for field, value in claims.items():
        if isinstance(value, str) and len(value) > 3:
            check_val = value.lower()[:50]
            if check_val in text:
                verified.append(field)
            else:
                unverified.append(field)
        elif isinstance(value, dict):
            verified.append(field)

    total = len(verified) + len(unverified)
    ratio = len(verified) / max(total, 1)
    return {"match_ratio": ratio, "verified": verified, "unverified": unverified}


def score_reviews_ratings(html: str) -> dict:
    """Score review and rating signals with volume/quality weighting."""
    score = 0.0
    signals = []

    rating_match = re.search(r'"ratingValue"\s*:\s*"?(\d+\.?\d*)"?', html)
    review_count_match = re.search(r'"reviewCount"\s*:\s*"?(\d+)"?', html)
    rating_count_match = re.search(r'"ratingCount"\s*:\s*"?(\d+)"?', html)
    best_rating_match = re.search(r'"bestRating"\s*:\s*"?(\d+\.?\d*)"?', html)

    best_rating = float(best_rating_match.group(1)) if best_rating_match else 5.0

    if rating_match:
        rating = float(rating_match.group(1))
        normalized_rating = rating / best_rating
        if normalized_rating >= 0.8:
            score += 35
            signals.append(f"Rating: {rating}/{best_rating:.0f} (excellent)")
        elif normalized_rating >= 0.7:
            score += 25
            signals.append(f"Rating: {rating}/{best_rating:.0f} (good)")
        elif normalized_rating >= 0.6:
            score += 15
            signals.append(f"Rating: {rating}/{best_rating:.0f} (average)")
        else:
            score += 5
            signals.append(f"Rating: {rating}/{best_rating:.0f} (below average)")
    else:
        visible_rating = re.search(r'(\d\.\d)\s*/\s*5|★\s*(\d\.\d)|평점\s*(\d\.\d)', html)
        if visible_rating:
            val = float(next(g for g in visible_rating.groups() if g))
            score += 20
            signals.append(f"Visible rating: {val} (no schema markup)")

    if review_count_match:
        count = int(review_count_match.group(1))
        if count >= 100:
            score += 25
            signals.append(f"Reviews: {count} (high volume)")
        elif count >= 30:
            score += 18
            signals.append(f"Reviews: {count} (moderate volume)")
        elif count >= 10:
            score += 12
            signals.append(f"Reviews: {count}")
        else:
            score += 6
            signals.append(f"Reviews: {count} (low volume)")
    elif rating_count_match:
        count = int(rating_count_match.group(1))
        score += min(15, count // 5)
        signals.append(f"Rating count: {count}")

    if 'AggregateRating' in html:
        score += 10
        signals.append("AggregateRating schema present")

    individual_reviews = re.findall(r'"@type"\s*:\s*"Review"', html, re.IGNORECASE)
    if len(individual_reviews) >= 3:
        score += 10
        signals.append(f"{len(individual_reviews)} individual Review schema items")
    elif len(individual_reviews) > 0:
        score += 5

    visible_reviews = len(re.findall(r'(리뷰|후기|review|testimonial)', html, re.IGNORECASE))
    if visible_reviews >= 3 and not rating_match:
        score += 10
        signals.append("Review content present but missing schema markup")

    if not signals:
        signals.append("No review/rating data found")

    return {"score": min(100, max(0, round(score))), "signals": signals}


def score_info_completeness(html: str) -> dict:
    """Score information completeness with quality weighting per field."""
    score = 0.0
    signals = []
    checks = {}

    title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
    h1_match = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.IGNORECASE | re.DOTALL)
    if title_match and len(re.sub(r'<[^>]+>', '', title_match.group(1)).strip()) > 5:
        score += 12
        checks["name/title"] = True
    elif h1_match:
        score += 8
        checks["name/title"] = True
    else:
        checks["name/title"] = False

    desc_match = re.search(r'name="description"\s+content="([^"]*)"', html, re.IGNORECASE)
    if desc_match:
        desc_len = len(desc_match.group(1))
        if desc_len >= 80:
            score += 12
            checks["description"] = True
        elif desc_len >= 30:
            score += 7
            checks["description"] = True
        else:
            score += 3
            checks["description"] = True
            signals.append("Description too short for agent extraction")
    else:
        checks["description"] = False

    addr_patterns = [
        r'\d{5}',  # Korean postal code
        r'\d+-\d+\s+[가-힣]',  # Korean address format
        r'(서울|부산|대구|인천|광주|대전|울산|경기|강원|충북|충남|전북|전남|경북|경남|제주)',
        r'(street|road|avenue|blvd|suite)\s+\d',
        r'"streetAddress"',
    ]
    addr_found = sum(1 for p in addr_patterns if re.search(p, html, re.IGNORECASE))
    if addr_found >= 2:
        score += 14
        checks["address"] = True
        signals.append("Structured address found")
    elif addr_found >= 1:
        score += 8
        checks["address"] = True
    else:
        addr_generic = bool(re.search(r'(address|주소|location|위치)', html, re.IGNORECASE))
        if addr_generic:
            score += 4
            checks["address"] = True
        else:
            checks["address"] = False

    phone_patterns = [
        r'0\d{1,2}[-.\s]?\d{3,4}[-.\s]?\d{4}',  # Korean phone
        r'\+82[-.\s]?\d',
        r'tel:\+?\d',
        r'"telephone"',
    ]
    phone_found = any(re.search(p, html, re.IGNORECASE) for p in phone_patterns)
    if phone_found:
        score += 10
        checks["phone"] = True
    else:
        checks["phone"] = False

    hours_structured = bool(re.search(r'"openingHoursSpecification"|"openingHours"', html))
    hours_visible = bool(re.search(r'(\d{1,2}:\d{2}\s*[-~]\s*\d{1,2}:\d{2}|영업시간|운영시간|business hours)', html, re.IGNORECASE))
    if hours_structured:
        score += 14
        checks["hours"] = True
        signals.append("Operating hours in structured data")
    elif hours_visible:
        score += 8
        checks["hours"] = True
    else:
        checks["hours"] = False

    price_patterns = [
        r'(\d{1,3}(,\d{3})+)\s*원',
        r'₩\s*\d',
        r'\$\s*\d+\.\d{2}',
        r'"price"\s*:\s*"?\d',
        r'"priceRange"',
    ]
    price_found = sum(1 for p in price_patterns if re.search(p, html))
    if price_found >= 2:
        score += 14
        checks["pricing"] = True
        signals.append("Clear pricing data found")
    elif price_found >= 1:
        score += 8
        checks["pricing"] = True
    else:
        checks["pricing"] = False

    images = re.findall(r'<img[^>]*>', html, re.IGNORECASE)
    img_with_alt = sum(1 for img in images if re.search(r'alt="[^"]+"', img))
    if len(images) >= 5 and img_with_alt >= 3:
        score += 12
        checks["images"] = True
        signals.append(f"{len(images)} images, {img_with_alt} with alt text")
    elif len(images) >= 3:
        score += 7
        checks["images"] = True
    elif len(images) > 0:
        score += 3
        checks["images"] = True
    else:
        checks["images"] = False

    category_found = bool(re.search(r'(category|카테고리|업종|분류|"@type")', html, re.IGNORECASE))
    if category_found:
        score += 8
        checks["category"] = True
    else:
        checks["category"] = False

    sum(1 for v in checks.values() if v)
    missing = [k for k, v in checks.items() if not v]
    if missing:
        signals.append(f"Missing: {', '.join(missing)}")

    return {"score": min(100, max(0, round(score))), "signals": signals, "checks": checks}


def score_api_booking(html: str) -> dict:
    """Score programmatic action availability for AI agents."""
    score = 0.0
    signals = []

    schema_actions = re.findall(r'"@type"\s*:\s*"(OrderAction|ReserveAction|BuyAction|SearchAction|ViewAction)"', html, re.IGNORECASE)
    if schema_actions:
        score += 25
        signals.append(f"Schema.org actions: {', '.join(set(schema_actions))}")

    if re.search(r'"potentialAction"', html):
        score += 10
        signals.append("potentialAction defined")

    booking_cta = re.findall(r'(book\s*now|reserve|예약하기|예약|바로예약)', html, re.IGNORECASE)
    if len(booking_cta) >= 2:
        score += 18
        signals.append(f"Strong booking CTAs ({len(booking_cta)} instances)")
    elif booking_cta:
        score += 10
        signals.append("Booking CTA found")

    purchase_cta = re.findall(r'(add to cart|장바구니|구매하기|buy now|purchase|결제하기|바로구매)', html, re.IGNORECASE)
    if len(purchase_cta) >= 2:
        score += 18
        signals.append(f"Purchase CTAs ({len(purchase_cta)} instances)")
    elif purchase_cta:
        score += 10
        signals.append("Purchase option found")

    api_signals = []
    if re.search(r'(/api/v\d|/api/|swagger|openapi|graphql)', html, re.IGNORECASE):
        api_signals.append("API endpoint")
    if re.search(r'(webhook|callback|integration)', html, re.IGNORECASE):
        api_signals.append("integration hook")
    if api_signals:
        score += 15
        signals.append(f"Programmatic access: {', '.join(api_signals)}")

    form_actions = re.findall(r'<form[^>]*action="([^"]*)"', html, re.IGNORECASE)
    if form_actions:
        score += 8
        signals.append(f"{len(form_actions)} form action(s)")

    deep_links = bool(re.search(r'(intent://|market://|itms-apps://|app-link)', html, re.IGNORECASE))
    if deep_links:
        score += 6
        signals.append("App deep linking available")

    if not signals:
        score = 10
        signals.append("No programmatic action paths detected")

    return {"score": min(100, max(0, round(score))), "signals": signals}


def score_trust_signals(html: str) -> dict:
    """Score trust and authority signals with credibility tiers."""
    score = 10.0
    signals = []

    official_certs = re.findall(r'(ISO\s*\d{4,5}|HACCP|GMP|FDA|CE마크|KC인증|정부인증|공인)', html, re.IGNORECASE)
    generic_certs = re.findall(r'(certification|인증|certified|자격증)', html, re.IGNORECASE)
    if official_certs:
        score += 20
        signals.append(f"Official certifications: {', '.join(set(official_certs[:3]))}")
    elif generic_certs:
        score += 10
        signals.append("Certification mentions (unspecific)")

    specific_awards = re.findall(r'(20\d{2}\s*(?:년\s*)?(?:수상|선정|대상|대회|award))', html, re.IGNORECASE)
    generic_awards = re.findall(r'(award|수상|선정|best\s+\w+)', html, re.IGNORECASE)
    if specific_awards:
        score += 15
        signals.append(f"Dated awards ({len(specific_awards)} mentions)")
    elif generic_awards:
        score += 8
        signals.append("Award mentions")

    year_match = re.search(r'(since\s*\d{4}|설립\s*\d{4}|(\d{4})\s*년\s*설립|founded\s*(?:in\s*)?\d{4})', html, re.IGNORECASE)
    if year_match:
        score += 12
        signals.append(f"Established date: {year_match.group(0).strip()}")
    elif re.search(r'(\d+\s*년\s*이상|\d+\s*years)', html, re.IGNORECASE):
        score += 8
        signals.append("Business longevity mentioned")

    partner_brands = re.findall(r'(삼성|LG|네이버|카카오|Google|Microsoft|Amazon|Apple)', html)
    generic_partners = re.findall(r'(partner|제휴|affiliated|협력사)', html, re.IGNORECASE)
    if partner_brands:
        score += 12
        signals.append(f"Named partners: {', '.join(set(partner_brands[:3]))}")
    elif generic_partners:
        score += 6
        signals.append("Partnership mentions")

    legal_pages = 0
    if re.search(r'(privacy\s*policy|개인정보\s*처리방침|개인정보\s*보호)', html, re.IGNORECASE):
        legal_pages += 1
    if re.search(r'(terms\s*(of|&)\s*(service|use)|이용약관)', html, re.IGNORECASE):
        legal_pages += 1
    if re.search(r'(refund|환불|취소\s*정책|return\s*policy)', html, re.IGNORECASE):
        legal_pages += 1
    if legal_pages >= 2:
        score += 12
        signals.append(f"Legal framework ({legal_pages} policy pages)")
    elif legal_pages == 1:
        score += 6

    biz_reg = bool(re.search(r'(사업자\s*등록\s*번호|사업자번호|\d{3}-\d{2}-\d{5})', html))
    if biz_reg:
        score += 10
        signals.append("Business registration number visible")

    ssl = bool(re.search(r'(https://|ssl|보안결제|PG사|secure)', html, re.IGNORECASE))
    if ssl:
        score += 5

    if not signals:
        signals.append("Minimal trust signals detected")

    return {"score": min(100, max(0, round(score))), "signals": signals}


def score_freshness(html: str, elapsed: float) -> dict:
    """Score content freshness with recency weighting."""
    score = 15.0
    signals = []

    dates_2026 = re.findall(r'2026[-./]\d{1,2}[-./]\d{1,2}', html)
    dates_2025 = re.findall(r'2025[-./]\d{1,2}[-./]\d{1,2}', html)
    dates_2024 = re.findall(r'2024[-./]\d{1,2}[-./]\d{1,2}', html)

    if dates_2026:
        score += 30
        signals.append(f"Current year dates ({len(dates_2026)} instances)")
    elif dates_2025:
        score += 20
        signals.append(f"Previous year dates ({len(dates_2025)} instances)")
    elif dates_2024:
        score += 10
        signals.append("2024 dates found (aging content)")

    modified_meta = re.search(r'(last-modified|modified|dateModified)\s*[:="]\s*(202[4-6])', html, re.IGNORECASE)
    if modified_meta:
        score += 12
        signals.append(f"Last-modified metadata: {modified_meta.group(2)}")
    elif re.search(r'(updated|modified|수정일|업데이트)', html, re.IGNORECASE):
        score += 7
        signals.append("Update indicators (no specific date)")

    if elapsed > 0:
        if elapsed < 0.5:
            score += 12
            signals.append(f"Excellent response time ({elapsed*1000:.0f}ms)")
        elif elapsed < 1.0:
            score += 8
            signals.append(f"Good response time ({elapsed*1000:.0f}ms)")
        elif elapsed < 2.0:
            score += 4
        elif elapsed > 5.0:
            score -= 5
            signals.append(f"Slow response ({elapsed:.1f}s) — may indicate unmaintained site")

    if re.search(r'(copyright|©)\s*2026', html, re.IGNORECASE):
        score += 10
        signals.append("Current year copyright")
    elif re.search(r'(copyright|©)\s*2025', html, re.IGNORECASE):
        score += 5

    dynamic_signals = 0
    if re.search(r'(최신|new|latest|방금|today|오늘)', html, re.IGNORECASE):
        dynamic_signals += 1
    if re.search(r'(실시간|live|real-?time)', html, re.IGNORECASE):
        dynamic_signals += 1
    if re.search(r'(재고|stock|available|남은\s*\d)', html, re.IGNORECASE):
        dynamic_signals += 1
    if dynamic_signals >= 2:
        score += 10
        signals.append("Dynamic/live content indicators")
    elif dynamic_signals == 1:
        score += 5

    if not signals:
        signals.append("No freshness signals detected")

    return {"score": min(100, max(0, round(score))), "signals": signals}


def _compute_correlation_bonus(dimensions: dict) -> dict:
    """Compute bonus/penalty from signal correlations."""
    bonus = 0.0
    applied = []

    for (dims, value, reason) in CORRELATION_BONUSES:
        threshold = 50
        if all(dimensions[d]["score"] >= threshold for d in dims):
            bonus += value
            applied.append({"type": "bonus", "value": value, "reason": reason})

    for (dims, value, reason) in CORRELATION_PENALTIES:
        high_dim, low_dim = dims[0], dims[1]
        if dimensions[high_dim]["score"] >= 60 and dimensions[low_dim]["score"] < 30:
            bonus += value
            applied.append({"type": "penalty", "value": value, "reason": reason})

    return {"bonus": round(bonus, 1), "applied": applied}


def analyze_selectability(url: str) -> dict:
    """Full selectability analysis with industry detection and signal correlation."""
    validation = validate_url(url)
    if not validation["valid"]:
        return {"success": False, "error": validation["error"]}

    result = fetch_page(url)
    if not result["success"]:
        return {"success": False, "error": result["error"]}

    html = result["html"]
    elapsed = result.get("elapsed_seconds", 0)

    industry = detect_industry(html)
    weights = get_industry_weights(industry)

    dimensions = {
        "structured_data": score_structured_data(html),
        "reviews_ratings": score_reviews_ratings(html),
        "info_completeness": score_info_completeness(html),
        "api_booking": score_api_booking(html),
        "trust_signals": score_trust_signals(html),
        "freshness": score_freshness(html, elapsed),
    }

    base_score = sum(
        dimensions[k]["score"] * weights[k]
        for k in weights
    )

    correlation = _compute_correlation_bonus(dimensions)
    overall = max(0, min(100, round(base_score + correlation["bonus"], 1)))

    issues = []
    for dim_name, dim_data in dimensions.items():
        if dim_data["score"] < 30:
            issues.append({"severity": "high", "message": f"Low {dim_name.replace('_', ' ')}: {dim_data['score']}/100"})
        elif dim_data["score"] < 50:
            issues.append({"severity": "medium", "message": f"Moderate {dim_name.replace('_', ' ')}: {dim_data['score']}/100"})

    if industry != "general":
        low_priority_dims = [d for d, adj in INDUSTRY_WEIGHT_ADJUSTMENTS.get(industry, {}).items() if adj > 0.05]
        for dim in low_priority_dims:
            if dimensions.get(dim, {}).get("score", 0) < 40:
                issues.append({"severity": "high", "message": f"Critical for {industry}: {dim.replace('_', ' ')} needs improvement"})

    return {
        "success": True,
        "url": url,
        "score": overall,
        "industry_detected": industry,
        "weights_applied": {k: round(v, 3) for k, v in weights.items()},
        "dimensions": {k: {"score": v["score"], "signals": v["signals"]} for k, v in dimensions.items()},
        "correlation": correlation,
        "issues": issues,
    }


def main():
    parser = argparse.ArgumentParser(description="Agent selectability scoring")
    parser.add_argument("url", help="URL to analyze")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    result = analyze_selectability(args.url)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result["success"]:
            print(f"Selectability Score: {result['score']}/100")
            print(f"Industry Detected: {result['industry_detected']}")
            print("\nDimension Scores:")
            for dim, data in result["dimensions"].items():
                weight = result["weights_applied"].get(dim, 0)
                bar = "█" * int(data["score"] / 10) + "░" * (10 - int(data["score"] / 10))
                print(f"  {dim.replace('_', ' ').title():25s} {bar} {data['score']:3.0f} (w:{weight:.0%})")
            if result["correlation"]["applied"]:
                print("\nSignal Correlations:")
                for c in result["correlation"]["applied"]:
                    prefix = "+" if c["value"] > 0 else ""
                    print(f"  {prefix}{c['value']:.0f} {c['reason']}")
            if result["issues"]:
                print("\nIssues:")
                for issue in result["issues"]:
                    print(f"  [{issue['severity'].upper()}] {issue['message']}")
        else:
            print(f"Error: {result['error']}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()

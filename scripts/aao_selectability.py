"""Agent selectability scoring script for Three-O platform."""

import argparse
import json
import re
import sys

from validate_url import validate_url
from fetch_page import fetch_page


SELECTABILITY_WEIGHTS = {
    "structured_data": 0.25,
    "reviews_ratings": 0.20,
    "info_completeness": 0.20,
    "api_booking": 0.15,
    "trust_signals": 0.10,
    "freshness": 0.10,
}


def score_structured_data(html: str) -> dict:
    """Score quality and completeness of structured data."""
    score = 0.0
    signals = []

    ld_blocks = re.findall(
        r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
        html, re.DOTALL | re.IGNORECASE
    )

    if not ld_blocks:
        return {"score": 0, "signals": ["No JSON-LD structured data found"]}

    score += 30
    signals.append(f"{len(ld_blocks)} JSON-LD block(s) found")

    for block in ld_blocks:
        try:
            data = json.loads(block.strip())
            if isinstance(data, list):
                data = data[0] if data else {}
            schema_type = data.get("@type", "")

            if schema_type in ["Product", "Service", "LocalBusiness", "Restaurant",
                               "Organization", "Store", "MedicalBusiness"]:
                score += 20
                signals.append(f"Business entity type: {schema_type}")

            if data.get("name"):
                score += 5
            if data.get("description"):
                score += 5
            if data.get("url"):
                score += 5
            if data.get("image") or data.get("logo"):
                score += 5
            if data.get("address") or data.get("location"):
                score += 5
            if data.get("telephone") or data.get("email"):
                score += 5
            if data.get("priceRange") or data.get("offers"):
                score += 10
                signals.append("Pricing information available")
            if data.get("openingHoursSpecification") or data.get("openingHours"):
                score += 10
                signals.append("Operating hours specified")
        except (json.JSONDecodeError, IndexError, TypeError):
            continue

    return {"score": min(100, round(score)), "signals": signals}


def score_reviews_ratings(html: str) -> dict:
    """Score review and rating signals."""
    score = 0.0
    signals = []

    rating_match = re.search(r'"ratingValue"\s*:\s*"?(\d+\.?\d*)"?', html)
    review_count_match = re.search(r'"reviewCount"\s*:\s*"?(\d+)"?', html)
    rating_count_match = re.search(r'"ratingCount"\s*:\s*"?(\d+)"?', html)

    if rating_match:
        rating = float(rating_match.group(1))
        score += 30
        signals.append(f"Rating: {rating}")
        if rating >= 4.0:
            score += 20
        elif rating >= 3.5:
            score += 10

    if review_count_match:
        count = int(review_count_match.group(1))
        score += 20
        signals.append(f"Reviews: {count}")
        if count >= 50:
            score += 15
        elif count >= 10:
            score += 10
    elif rating_count_match:
        count = int(rating_count_match.group(1))
        score += 15
        signals.append(f"Ratings: {count}")

    if 'AggregateRating' in html:
        score += 15
        signals.append("AggregateRating schema present")

    if not signals:
        signals.append("No review/rating data found")

    return {"score": min(100, round(score)), "signals": signals}


def score_info_completeness(html: str) -> dict:
    """Score information completeness for agent consumption."""
    score = 0.0
    signals = []

    checks = {
        "name/title": bool(re.search(r'<(title|h1)[^>]*>', html, re.IGNORECASE)),
        "description": 'name="description"' in html.lower(),
        "address": bool(re.search(r'(address|주소|location)', html, re.IGNORECASE)),
        "phone": bool(re.search(r'(tel:|phone|전화|☎)', html, re.IGNORECASE)),
        "hours": bool(re.search(r'(hours|영업시간|운영시간|openingHours)', html, re.IGNORECASE)),
        "pricing": bool(re.search(r'(price|가격|요금|₩|\$|원)', html, re.IGNORECASE)),
        "images": bool(re.search(r'<img[^>]*>', html, re.IGNORECASE)),
        "category": bool(re.search(r'(category|카테고리|업종)', html, re.IGNORECASE)),
    }

    filled = sum(1 for v in checks.values() if v)
    score = round((filled / len(checks)) * 100)

    for field, present in checks.items():
        if present:
            signals.append(f"{field}: present")
        else:
            signals.append(f"{field}: missing")

    return {"score": score, "signals": signals, "checks": checks}


def score_api_booking(html: str) -> dict:
    """Score API and booking availability."""
    score = 20.0
    signals = []

    if re.search(r'(book|reserve|예약|booking)', html, re.IGNORECASE):
        score += 20
        signals.append("Booking/reservation option found")

    if re.search(r'(add to cart|장바구니|구매|buy now|purchase)', html, re.IGNORECASE):
        score += 20
        signals.append("Purchase option found")

    if re.search(r'(api|/api/|swagger|graphql)', html, re.IGNORECASE):
        score += 25
        signals.append("API endpoint detected")

    if re.search(r'(potentialAction|OrderAction|ReserveAction)', html, re.IGNORECASE):
        score += 15
        signals.append("Schema.org action type defined")

    if not signals:
        signals.append("No programmatic action paths detected")

    return {"score": min(100, round(score)), "signals": signals}


def score_trust_signals(html: str) -> dict:
    """Score trust and authority signals."""
    score = 20.0
    signals = []

    if re.search(r'(certification|인증|certified|공인)', html, re.IGNORECASE):
        score += 20
        signals.append("Certifications mentioned")
    if re.search(r'(award|수상|선정)', html, re.IGNORECASE):
        score += 15
        signals.append("Awards mentioned")
    if re.search(r'(since|설립|years|년 이상)', html, re.IGNORECASE):
        score += 15
        signals.append("Business history/longevity")
    if re.search(r'(partner|제휴|affiliated)', html, re.IGNORECASE):
        score += 10
        signals.append("Partnership signals")
    if re.search(r'(ssl|https|보안)', html, re.IGNORECASE) or 'https' in html[:100]:
        score += 10
        signals.append("Security indicators")
    if re.search(r'(privacy|개인정보|이용약관)', html, re.IGNORECASE):
        score += 10
        signals.append("Privacy/terms present")

    return {"score": min(100, round(score)), "signals": signals}


def score_freshness(html: str, elapsed: float) -> dict:
    """Score content freshness."""
    score = 30.0
    signals = []

    date_patterns = re.findall(r'202[4-6][-./]\d{1,2}[-./]\d{1,2}', html)
    if date_patterns:
        score += 30
        signals.append(f"Recent dates found: {date_patterns[0]}")

    if re.search(r'(updated|modified|수정일|업데이트)', html, re.IGNORECASE):
        score += 20
        signals.append("Update/modification indicators")

    if elapsed < 1.0:
        score += 10
        signals.append(f"Fast response ({elapsed*1000:.0f}ms)")
    elif elapsed < 3.0:
        score += 5

    if re.search(r'(copyright|©)\s*202[4-6]', html, re.IGNORECASE):
        score += 10
        signals.append("Current year copyright")

    return {"score": min(100, round(score)), "signals": signals}


def analyze_selectability(url: str) -> dict:
    """Full selectability analysis."""
    validation = validate_url(url)
    if not validation["valid"]:
        return {"success": False, "error": validation["error"]}

    result = fetch_page(url)
    if not result["success"]:
        return {"success": False, "error": result["error"]}

    html = result["html"]
    elapsed = result.get("elapsed_seconds", 0)

    dimensions = {
        "structured_data": score_structured_data(html),
        "reviews_ratings": score_reviews_ratings(html),
        "info_completeness": score_info_completeness(html),
        "api_booking": score_api_booking(html),
        "trust_signals": score_trust_signals(html),
        "freshness": score_freshness(html, elapsed),
    }

    overall = round(sum(
        dimensions[k]["score"] * SELECTABILITY_WEIGHTS[k]
        for k in SELECTABILITY_WEIGHTS
    ), 1)

    issues = []
    for dim_name, dim_data in dimensions.items():
        if dim_data["score"] < 30:
            issues.append({"severity": "high", "message": f"Low {dim_name.replace('_', ' ')}: {dim_data['score']}/100"})
        elif dim_data["score"] < 50:
            issues.append({"severity": "medium", "message": f"Moderate {dim_name.replace('_', ' ')}: {dim_data['score']}/100"})

    return {
        "success": True,
        "url": url,
        "score": overall,
        "dimensions": {k: {"score": v["score"], "signals": v["signals"]} for k, v in dimensions.items()},
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
            print(f"\nDimension Scores:")
            for dim, data in result["dimensions"].items():
                bar = "█" * int(data["score"] / 10) + "░" * (10 - int(data["score"] / 10))
                print(f"  {dim.replace('_', ' ').title():25s} {bar} {data['score']}")
            for issue in result["issues"]:
                print(f"  [{issue['severity'].upper()}] {issue['message']}")
        else:
            print(f"Error: {result['error']}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()

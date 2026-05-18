"""Agent scenario testing script for Three-O platform."""

import argparse
import json
import re
import sys
from typing import Optional

from validate_url import validate_url
from fetch_page import fetch_page


SCENARIO_TEMPLATES = {
    "restaurant": [
        {"query": "Book a table at {brand}", "intent": "reservation", "required_data": ["openingHours", "telephone", "address", "menu"]},
        {"query": "What's on the menu at {brand}", "intent": "information", "required_data": ["menu", "servesCuisine", "priceRange"]},
        {"query": "How to get to {brand}", "intent": "navigation", "required_data": ["address", "geo"]},
        {"query": "Is {brand} open now", "intent": "hours", "required_data": ["openingHoursSpecification"]},
    ],
    "ecommerce": [
        {"query": "Buy {product} from {brand}", "intent": "purchase", "required_data": ["offers", "price", "availability"]},
        {"query": "Compare {product} prices at {brand}", "intent": "comparison", "required_data": ["offers", "price", "sku"]},
        {"query": "Track my order from {brand}", "intent": "tracking", "required_data": ["potentialAction"]},
        {"query": "Return policy at {brand}", "intent": "information", "required_data": ["hasMerchantReturnPolicy"]},
    ],
    "service": [
        {"query": "Book an appointment at {brand}", "intent": "booking", "required_data": ["telephone", "openingHours", "areaServed"]},
        {"query": "How much does {brand} charge", "intent": "pricing", "required_data": ["offers", "priceRange"]},
        {"query": "Reviews for {brand}", "intent": "reviews", "required_data": ["aggregateRating", "review"]},
        {"query": "Contact {brand}", "intent": "contact", "required_data": ["telephone", "email", "contactPoint"]},
    ],
    "healthcare": [
        {"query": "Book a consultation at {brand}", "intent": "booking", "required_data": ["telephone", "openingHours", "medicalSpecialty"]},
        {"query": "What services does {brand} offer", "intent": "information", "required_data": ["medicalSpecialty", "availableService"]},
        {"query": "Is {brand} accepting new patients", "intent": "availability", "required_data": ["openingHours", "telephone"]},
        {"query": "Where is {brand} located", "intent": "navigation", "required_data": ["address", "geo"]},
    ],
}


def get_scenarios(industry: str, brand: str) -> list:
    """Get scenario templates for the given industry."""
    template = SCENARIO_TEMPLATES.get(industry, SCENARIO_TEMPLATES["service"])
    scenarios = []
    for tmpl in template:
        scenario = {
            "query": tmpl["query"].replace("{brand}", brand).replace("{product}", "product"),
            "intent": tmpl["intent"],
            "required_data": tmpl["required_data"],
        }
        scenarios.append(scenario)
    return scenarios


def extract_available_data(html: str) -> set:
    """Extract available structured data fields from HTML."""
    available = set()

    blocks = re.findall(
        r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
        html, re.DOTALL | re.IGNORECASE
    )

    for block in blocks:
        try:
            data = json.loads(block.strip())
            if isinstance(data, list):
                for item in data:
                    available.update(_extract_keys(item))
            else:
                available.update(_extract_keys(data))
        except (json.JSONDecodeError, TypeError):
            continue

    if re.search(r'href="tel:', html):
        available.add("telephone")
    if re.search(r'(address|주소)', html, re.IGNORECASE):
        available.add("address")
    if re.search(r'(menu|메뉴)', html, re.IGNORECASE):
        available.add("menu")
    if re.search(r'(price|가격|₩|\$|원)', html, re.IGNORECASE):
        available.add("price")
        available.add("priceRange")

    return available


def _extract_keys(data, prefix=""):
    """Recursively extract all keys from a JSON structure."""
    keys = set()
    if isinstance(data, dict):
        for key, value in data.items():
            if not key.startswith("@"):
                keys.add(key)
                if isinstance(value, dict):
                    keys.update(_extract_keys(value, key))
    return keys


def evaluate_scenario(scenario: dict, available_data: set) -> dict:
    """Evaluate if a scenario can be fulfilled."""
    required = set(scenario["required_data"])
    matched = required & available_data
    missing = required - available_data

    if not missing:
        status = "fulfillable"
        score = 100
    elif len(matched) >= len(required) * 0.5:
        status = "partial"
        score = round(len(matched) / len(required) * 100)
    else:
        status = "not_fulfillable"
        score = round(len(matched) / len(required) * 100)

    return {
        "query": scenario["query"],
        "intent": scenario["intent"],
        "status": status,
        "score": score,
        "required": list(required),
        "available": list(matched),
        "missing": list(missing),
    }


def run_scenario_test(url: str, brand: str, industry: Optional[str] = None) -> dict:
    """Run full scenario test."""
    validation = validate_url(url)
    if not validation["valid"]:
        return {"success": False, "error": validation["error"]}

    result = fetch_page(url)
    if not result["success"]:
        return {"success": False, "error": result["error"]}

    html = result["html"]
    available_data = extract_available_data(html)
    detected_industry = industry or _detect_industry(html)
    scenarios = get_scenarios(detected_industry, brand)

    results = []
    for scenario in scenarios:
        evaluation = evaluate_scenario(scenario, available_data)
        results.append(evaluation)

    fulfillable = sum(1 for r in results if r["status"] == "fulfillable")
    partial = sum(1 for r in results if r["status"] == "partial")
    avg_score = round(sum(r["score"] for r in results) / max(len(results), 1), 1)

    issues = []
    for r in results:
        if r["status"] == "not_fulfillable":
            issues.append({
                "severity": "high",
                "message": f"Cannot fulfill: \"{r['query']}\" — missing: {', '.join(r['missing'])}",
            })
        elif r["status"] == "partial":
            issues.append({
                "severity": "medium",
                "message": f"Partial: \"{r['query']}\" — missing: {', '.join(r['missing'])}",
            })

    return {
        "success": True,
        "url": url,
        "brand": brand,
        "industry": detected_industry,
        "score": avg_score,
        "scenarios_tested": len(results),
        "fulfillable": fulfillable,
        "partial": partial,
        "not_fulfillable": len(results) - fulfillable - partial,
        "available_data_fields": sorted(list(available_data))[:30],
        "results": results,
        "issues": issues,
    }


def _detect_industry(html: str) -> str:
    """Detect industry from HTML content."""
    html_lower = html.lower()
    if any(kw in html_lower for kw in ["menu", "restaurant", "메뉴", "예약", "cuisine", "음식"]):
        return "restaurant"
    if any(kw in html_lower for kw in ["cart", "checkout", "장바구니", "구매", "product", "상품"]):
        return "ecommerce"
    if any(kw in html_lower for kw in ["clinic", "hospital", "진료", "병원", "의원", "medical"]):
        return "healthcare"
    return "service"


def main():
    parser = argparse.ArgumentParser(description="Agent scenario testing")
    parser.add_argument("url", help="URL to test")
    parser.add_argument("brand", help="Brand name")
    parser.add_argument("--industry", choices=list(SCENARIO_TEMPLATES.keys()), help="Industry type")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    result = run_scenario_test(args.url, args.brand, args.industry)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result["success"]:
            print(f"Scenario Test: {args.brand} ({result['industry']})")
            print(f"Score: {result['score']}/100")
            print(f"Results: {result['fulfillable']} fulfillable / {result['partial']} partial / {result['not_fulfillable']} failed")
            print("\nScenario Results:")
            for r in result["results"]:
                icon = "✓" if r["status"] == "fulfillable" else "~" if r["status"] == "partial" else "✗"
                print(f"  {icon} [{r['score']:3d}] {r['query']}")
                if r["missing"]:
                    print(f"         missing: {', '.join(r['missing'])}")
        else:
            print(f"Error: {result['error']}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()

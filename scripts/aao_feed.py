"""Product feed validation script for Three-O platform."""

import argparse
import json
import re
import sys
from urllib.parse import urlparse

from validate_url import validate_url
from fetch_page import fetch_page


GOOGLE_REQUIRED = ["id", "title", "description", "link", "image_link",
                   "price", "availability", "condition", "brand"]

NAVER_REQUIRED = ["id", "title", "price_pc", "link", "image_link",
                  "category1", "shipping"]

FEED_WEIGHTS = {
    "data_quality": 0.30,
    "completeness": 0.25,
    "freshness": 0.25,
    "platform_compliance": 0.20,
}


def detect_feed(url: str) -> dict:
    """Detect product feed from site URL."""
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    feed_paths = [
        "/feed.xml", "/products.xml", "/merchant-feed.xml",
        "/product-feed.xml", "/shopping-feed.xml",
        "/sitemap-products.xml", "/feed/products",
    ]

    for path in feed_paths:
        feed_url = base + path
        result = fetch_page(feed_url)
        if result["success"] and result.get("status_code") == 200:
            content = result.get("html", "")
            if "<item" in content or "<entry" in content or "<product" in content:
                return {"found": True, "url": feed_url, "content": content}

    return {"found": False}


def parse_product_feed(content: str) -> dict:
    """Parse product feed XML content."""
    items = re.findall(r'<item>(.*?)</item>', content, re.DOTALL | re.IGNORECASE)
    if not items:
        items = re.findall(r'<entry>(.*?)</entry>', content, re.DOTALL | re.IGNORECASE)
    if not items:
        items = re.findall(r'<product>(.*?)</product>', content, re.DOTALL | re.IGNORECASE)

    products = []
    for item in items[:100]:
        product = {}
        fields = re.findall(r'<(g:)?(\w+)>(.*?)</\1?\2>', item, re.DOTALL)
        for _, field_name, value in fields:
            product[field_name.lower()] = value.strip()

        if not product:
            simple_fields = re.findall(r'<(\w+)>(.*?)</\1>', item, re.DOTALL)
            for name, value in simple_fields:
                product[name.lower()] = value.strip()

        if product:
            products.append(product)

    return {
        "total_items": len(items),
        "parsed_sample": len(products),
        "products": products[:20],
    }


def validate_data_quality(products: list) -> dict:
    """Validate data quality of products."""
    if not products:
        return {"score": 0, "issues": ["No products to validate"]}

    issues = []
    total_checks = 0
    passed_checks = 0

    for i, product in enumerate(products[:20]):
        total_checks += 1
        if product.get("title") and len(product["title"]) > 5:
            passed_checks += 1
        else:
            issues.append(f"Product {i+1}: missing or short title")

        total_checks += 1
        if product.get("link") and product["link"].startswith("http"):
            passed_checks += 1
        else:
            issues.append(f"Product {i+1}: invalid or missing link")

        total_checks += 1
        price = product.get("price") or product.get("price_pc") or product.get("sale_price")
        if price and re.search(r'\d', str(price)):
            passed_checks += 1
        else:
            issues.append(f"Product {i+1}: missing or invalid price")

        total_checks += 1
        img = product.get("image_link") or product.get("image")
        if img and img.startswith("http"):
            passed_checks += 1

    score = round((passed_checks / max(total_checks, 1)) * 100)
    return {"score": score, "issues": issues[:10], "checked": len(products[:20])}


def check_completeness(products: list, platform: str) -> dict:
    """Check field completeness against platform requirements."""
    required = GOOGLE_REQUIRED if platform == "google" else NAVER_REQUIRED

    if not products:
        return {"score": 0, "missing_fields": required, "coverage": {}}

    coverage = {}
    for field in required:
        present = sum(1 for p in products if p.get(field))
        coverage[field] = round(present / len(products) * 100)

    avg_coverage = round(sum(coverage.values()) / max(len(coverage), 1))
    missing = [f for f, pct in coverage.items() if pct < 50]

    return {
        "score": avg_coverage,
        "coverage": coverage,
        "missing_fields": missing,
        "platform": platform,
    }


def check_freshness(content: str) -> dict:
    """Check feed freshness indicators."""
    score = 30
    signals = []

    date_patterns = re.findall(r'202[4-6]-\d{2}-\d{2}', content)
    if date_patterns:
        score += 40
        signals.append(f"Recent dates found (e.g., {date_patterns[0]})")

    if re.search(r'<lastBuildDate>', content):
        score += 15
        signals.append("lastBuildDate present")

    if re.search(r'<pubDate>', content):
        score += 15
        signals.append("pubDate present")

    return {"score": min(100, score), "signals": signals}


def validate_feed(url: str, platform: str = "google") -> dict:
    """Full product feed validation."""
    validation = validate_url(url)
    if not validation["valid"]:
        return {"success": False, "error": validation["error"]}

    if url.endswith(".xml") or "/feed" in url:
        result = fetch_page(url)
        if result["success"] and result.get("status_code") == 200:
            feed_data = {"found": True, "url": url, "content": result["html"]}
        else:
            feed_data = {"found": False}
    else:
        feed_data = detect_feed(url)

    if not feed_data["found"]:
        return {
            "success": True,
            "url": url,
            "feed_found": False,
            "score": 0,
            "issues": [{"severity": "critical", "message": "No product feed found"}],
        }

    parsed = parse_product_feed(feed_data["content"])
    quality = validate_data_quality(parsed["products"])
    completeness = check_completeness(parsed["products"], platform)
    freshness = check_freshness(feed_data["content"])

    compliance_score = round((quality["score"] + completeness["score"]) / 2)

    overall = round(
        quality["score"] * FEED_WEIGHTS["data_quality"] +
        completeness["score"] * FEED_WEIGHTS["completeness"] +
        freshness["score"] * FEED_WEIGHTS["freshness"] +
        compliance_score * FEED_WEIGHTS["platform_compliance"],
        1
    )

    issues = []
    if quality["score"] < 50:
        issues.append({"severity": "high", "message": f"Data quality issues in {len(quality['issues'])} products"})
    if completeness["missing_fields"]:
        issues.append({"severity": "medium", "message": f"Missing required fields: {', '.join(completeness['missing_fields'][:5])}"})
    if freshness["score"] < 50:
        issues.append({"severity": "medium", "message": "Feed may be stale — no recent date indicators"})
    if parsed["total_items"] == 0:
        issues.append({"severity": "critical", "message": "Feed contains no products"})

    return {
        "success": True,
        "url": url,
        "feed_found": True,
        "feed_url": feed_data["url"],
        "score": overall,
        "platform": platform,
        "statistics": {
            "total_products": parsed["total_items"],
            "sample_validated": parsed["parsed_sample"],
        },
        "dimensions": {
            "data_quality": quality["score"],
            "completeness": completeness["score"],
            "freshness": freshness["score"],
            "platform_compliance": compliance_score,
        },
        "field_coverage": completeness.get("coverage", {}),
        "issues": issues,
    }


def main():
    parser = argparse.ArgumentParser(description="Product feed validation")
    parser.add_argument("url", help="Feed URL or site URL")
    parser.add_argument("--platform", choices=["google", "naver", "both"], default="google", help="Target platform")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    result = validate_feed(args.url, args.platform)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result.get("feed_found"):
            print(f"Feed Score: {result['score']}/100 ({args.platform})")
            print(f"Products: {result['statistics']['total_products']}")
            print(f"\nDimension Scores:")
            for dim, score in result["dimensions"].items():
                bar = "█" * int(score / 10) + "░" * (10 - int(score / 10))
                print(f"  {dim.replace('_', ' ').title():25s} {bar} {score}")
        else:
            print("✗ No product feed found")
        for issue in result.get("issues", []):
            print(f"  [{issue['severity'].upper()}] {issue['message']}")


if __name__ == "__main__":
    main()

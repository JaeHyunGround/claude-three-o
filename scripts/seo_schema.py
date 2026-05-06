"""Schema.org structured data detection and validation for Three-O platform."""

import argparse
import json
import re
import sys

from validate_url import validate_url
from fetch_page import fetch_page


def extract_jsonld(html: str) -> list:
    """Extract JSON-LD blocks from HTML."""
    pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
    matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
    results = []
    for match in matches:
        try:
            data = json.loads(match.strip())
            if isinstance(data, list):
                results.extend(data)
            else:
                results.append(data)
        except json.JSONDecodeError:
            results.append({"_error": "Invalid JSON", "_raw": match[:200]})
    return results


def validate_schema(schema: dict) -> dict:
    """Validate a single Schema.org entity."""
    schema_type = schema.get("@type", "Unknown")
    issues = []

    required_fields = {
        "Organization": ["name", "url"],
        "LocalBusiness": ["name", "address", "telephone"],
        "Restaurant": ["name", "address", "telephone", "servesCuisine"],
        "Product": ["name", "offers"],
        "Article": ["headline", "author", "datePublished"],
        "BlogPosting": ["headline", "author", "datePublished"],
        "FAQPage": ["mainEntity"],
        "Service": ["name", "provider"],
        "Person": ["name"],
        "Event": ["name", "startDate", "location"],
    }

    recommended_fields = {
        "Organization": ["logo", "sameAs", "contactPoint", "description"],
        "LocalBusiness": ["openingHoursSpecification", "geo", "priceRange", "aggregateRating"],
        "Product": ["image", "description", "sku", "brand", "aggregateRating"],
    }

    reqs = required_fields.get(schema_type, ["name"])
    for field in reqs:
        if field not in schema:
            issues.append({"severity": "high", "message": f"Missing required: {field}"})

    recs = recommended_fields.get(schema_type, [])
    missing_recommended = [f for f in recs if f not in schema]

    deprecated_check = []
    if schema_type == "HowTo":
        deprecated_check.append("HowTo schema deprecated (Sept 2023)")
    if schema_type == "FAQPage":
        deprecated_check.append("FAQPage restricted to gov/health sites (Aug 2023)")

    completeness = len([f for f in reqs if f in schema]) / max(len(reqs), 1) * 100

    return {
        "type": schema_type,
        "valid": len(issues) == 0 and len(deprecated_check) == 0,
        "completeness": round(completeness, 1),
        "issues": issues,
        "missing_recommended": missing_recommended,
        "deprecated_warnings": deprecated_check,
    }


def analyze_schema(url: str) -> dict:
    """Run schema analysis on URL."""
    validation = validate_url(url)
    if not validation["valid"]:
        return {"success": False, "error": validation["error"]}

    result = fetch_page(url)
    if not result["success"]:
        return {"success": False, "error": result["error"]}

    schemas = extract_jsonld(result["html"])
    validations = [validate_schema(s) for s in schemas if "@type" in s]

    has_microdata = 'itemscope' in result["html"]
    has_rdfa = 'typeof=' in result["html"]

    score = 0
    if schemas:
        valid_count = sum(1 for v in validations if v["valid"])
        avg_completeness = sum(v["completeness"] for v in validations) / max(len(validations), 1)
        score = int(min(100, (valid_count / max(len(validations), 1)) * 50 + avg_completeness * 0.5))

    return {
        "success": True,
        "url": url,
        "score": score,
        "jsonld_count": len(schemas),
        "schemas": validations,
        "has_microdata": has_microdata,
        "has_rdfa": has_rdfa,
        "types_found": [v["type"] for v in validations],
    }


def main():
    parser = argparse.ArgumentParser(description="Schema.org structured data analysis")
    parser.add_argument("url", help="URL to analyze")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    result = analyze_schema(args.url)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result["success"]:
            print(f"Schema Score: {result['score']}/100")
            print(f"JSON-LD blocks: {result['jsonld_count']}")
            print(f"Types: {', '.join(result['types_found']) or 'None'}")
            for v in result["schemas"]:
                status = "✓" if v["valid"] else "✗"
                print(f"  {status} {v['type']} — Completeness: {v['completeness']}%")
        else:
            print(f"Error: {result['error']}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()

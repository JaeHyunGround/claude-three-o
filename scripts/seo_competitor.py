"""SEO competitor gap analysis script for Three-O platform."""

import argparse
import json
import sys

from validate_url import validate_url
from fetch_page import fetch_page


def extract_page_keywords(html: str) -> set:
    """Extract likely target keywords from page meta and headings."""
    import re
    keywords = set()

    title_match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if title_match:
        keywords.update(title_match.group(1).lower().split())

    meta_match = re.search(r'name="description"\s+content="([^"]*)"', html, re.IGNORECASE)
    if not meta_match:
        meta_match = re.search(r'content="([^"]*)"\s+name="description"', html, re.IGNORECASE)
    if meta_match:
        keywords.update(meta_match.group(1).lower().split())

    headings = re.findall(r"<h[1-3][^>]*>(.*?)</h[1-3]>", html, re.IGNORECASE | re.DOTALL)
    for h in headings:
        clean = re.sub(r"<[^>]+>", "", h)
        keywords.update(clean.lower().split())

    stop_words = {"the", "a", "an", "is", "are", "was", "were", "in", "on", "at", "to", "for", "of", "and", "or"}
    keywords = {k for k in keywords if len(k) > 2 and k not in stop_words}
    return keywords


def compare_sites(url_a: str, url_b: str) -> dict:
    """Compare two URLs for SEO competitive gaps."""
    val_a = validate_url(url_a)
    val_b = validate_url(url_b)
    if not val_a["valid"]:
        return {"success": False, "error": f"URL A invalid: {val_a['error']}"}
    if not val_b["valid"]:
        return {"success": False, "error": f"URL B invalid: {val_b['error']}"}

    result_a = fetch_page(url_a)
    result_b = fetch_page(url_b)

    if not result_a["success"]:
        return {"success": False, "error": f"Cannot fetch URL A: {result_a['error']}"}
    if not result_b["success"]:
        return {"success": False, "error": f"Cannot fetch URL B: {result_b['error']}"}

    keywords_a = extract_page_keywords(result_a["html"])
    keywords_b = extract_page_keywords(result_b["html"])

    only_a = keywords_a - keywords_b
    only_b = keywords_b - keywords_a
    shared = keywords_a & keywords_b

    schema_a = 'application/ld+json' in result_a["html"]
    schema_b = 'application/ld+json' in result_b["html"]

    return {
        "success": True,
        "url_a": url_a,
        "url_b": url_b,
        "keywords_a_count": len(keywords_a),
        "keywords_b_count": len(keywords_b),
        "shared_keywords": len(shared),
        "only_in_a": sorted(list(only_a))[:20],
        "only_in_b": sorted(list(only_b))[:20],
        "gaps_for_a": sorted(list(only_b))[:10],
        "advantages_for_a": sorted(list(only_a))[:10],
        "schema_comparison": {"a_has_schema": schema_a, "b_has_schema": schema_b},
        "response_time": {
            "a": result_a.get("elapsed_seconds"),
            "b": result_b.get("elapsed_seconds"),
        },
    }


def main():
    parser = argparse.ArgumentParser(description="SEO competitor gap analysis")
    parser.add_argument("url_a", help="Your URL")
    parser.add_argument("url_b", help="Competitor URL")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    result = compare_sites(args.url_a, args.url_b)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result["success"]:
            print(f"Competitor Analysis: {args.url_a} vs {args.url_b}")
            print(f"Keywords — You: {result['keywords_a_count']} | Competitor: {result['keywords_b_count']} | Shared: {result['shared_keywords']}")
            print(f"\nGaps (competitor has, you don't):")
            for kw in result["gaps_for_a"][:5]:
                print(f"  → {kw}")
            print(f"\nAdvantages (you have, competitor doesn't):")
            for kw in result["advantages_for_a"][:5]:
                print(f"  ✓ {kw}")
        else:
            print(f"Error: {result['error']}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()

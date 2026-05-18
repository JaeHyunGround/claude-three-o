"""Keyword tracking script for Three-O platform (Google + Naver)."""

import argparse
import json
import sys


def check_keyword_in_content(html: str, keyword: str) -> dict:
    """Check keyword presence and placement in page content."""
    html_lower = html.lower()
    keyword_lower = keyword.lower()

    in_title = keyword_lower in (html_lower.split("<title>")[1].split("</title>")[0] if "<title>" in html_lower else "")
    in_h1 = keyword_lower in (html_lower.split("<h1")[1].split("</h1>")[0] if "<h1" in html_lower else "")
    in_meta = keyword_lower in (html_lower.split('name="description"')[0][-500:] if 'name="description"' in html_lower else "")

    import re
    body_text = re.sub(r"<[^>]+>", " ", html_lower)
    occurrences = body_text.count(keyword_lower)
    word_count = len(body_text.split())
    density = (occurrences / max(word_count, 1)) * 100

    return {
        "keyword": keyword,
        "in_title": in_title,
        "in_h1": in_h1,
        "in_meta_description": in_meta,
        "occurrences": occurrences,
        "density_percent": round(density, 2),
        "density_status": "optimal" if 0.5 <= density <= 2.5 else "low" if density < 0.5 else "high",
    }


def generate_keyword_variants(keyword: str) -> list:
    """Generate Korean keyword variants with common suffixes."""
    variants = [keyword]
    korean_suffixes = ["추천", "비교", "후기", "가격", "순위", "방법"]
    for suffix in korean_suffixes:
        variants.append(f"{keyword} {suffix}")
    return variants


def analyze_keywords(url: str, keywords: list) -> dict:
    """Analyze keyword optimization for given URL."""
    from validate_url import validate_url
    from fetch_page import fetch_page

    validation = validate_url(url)
    if not validation["valid"]:
        return {"success": False, "error": validation["error"]}

    result = fetch_page(url)
    if not result["success"]:
        return {"success": False, "error": result["error"]}

    html = result["html"]
    keyword_results = []
    for kw in keywords:
        analysis = check_keyword_in_content(html, kw)
        keyword_results.append(analysis)

    optimized = sum(1 for r in keyword_results if r["in_title"] or r["in_h1"])
    score = int(min(100, (optimized / max(len(keywords), 1)) * 60 + 40))

    return {
        "success": True,
        "url": url,
        "score": score,
        "keywords_analyzed": len(keywords),
        "keywords_optimized": optimized,
        "results": keyword_results,
    }


def main():
    parser = argparse.ArgumentParser(description="Keyword analysis for Three-O")
    parser.add_argument("url", help="URL to analyze")
    parser.add_argument("--keywords", nargs="+", required=True, help="Keywords to check")
    parser.add_argument("--variants", action="store_true", help="Generate Korean variants")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    keywords = args.keywords
    if args.variants:
        expanded = []
        for kw in keywords:
            expanded.extend(generate_keyword_variants(kw))
        keywords = expanded

    result = analyze_keywords(args.url, keywords)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result["success"]:
            print(f"Keyword Score: {result['score']}/100")
            print(f"Analyzed: {result['keywords_analyzed']} | Optimized: {result['keywords_optimized']}")
            for r in result["results"]:
                status = "✓" if r["in_title"] or r["in_h1"] else "✗"
                print(f"  {status} \"{r['keyword']}\" — density: {r['density_percent']}% ({r['density_status']})")
        else:
            print(f"Error: {result['error']}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()

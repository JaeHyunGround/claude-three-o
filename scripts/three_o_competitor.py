"""Cross-pillar competitor benchmarking script for Three-O platform."""

import argparse
import json
import sys
from typing import Optional

from validate_url import validate_url
from fetch_page import fetch_page


def quick_seo_score(html: str, elapsed: float) -> dict:
    """Quick SEO score estimation from HTML."""
    import re

    score = 50
    signals = {}

    has_title = bool(re.search(r'<title>.+</title>', html, re.IGNORECASE))
    has_desc = 'name="description"' in html.lower()
    has_h1 = bool(re.search(r'<h1', html, re.IGNORECASE))
    has_schema = 'application/ld+json' in html
    has_canonical = 'rel="canonical"' in html

    signals["title"] = has_title
    signals["meta_desc"] = has_desc
    signals["h1"] = has_h1
    signals["schema"] = has_schema
    signals["canonical"] = has_canonical

    score += sum(10 for v in signals.values() if v)

    if elapsed < 1.0:
        score += 10
    elif elapsed > 3.0:
        score -= 10

    return {"score": min(100, max(0, score)), "signals": signals}


def quick_geo_score(html: str) -> dict:
    """Quick GEO score estimation from HTML."""
    import re

    score = 30
    signals = {}

    signals["structured_data"] = 'application/ld+json' in html
    signals["same_as"] = '"sameAs"' in html
    signals["author"] = bool(re.search(r'(author|byline|작성자)', html, re.IGNORECASE))
    signals["factual"] = bool(re.search(r'\d+[\d,.%]*', re.sub(r'<[^>]+>', '', html[:3000])))

    text = re.sub(r'<[^>]+>', '', html)
    word_count = len(text.split())
    signals["content_depth"] = word_count > 500

    score += sum(14 for v in signals.values() if v)

    return {"score": min(100, max(0, score)), "signals": signals}


def quick_aao_score(html: str) -> dict:
    """Quick AAO score estimation from HTML."""
    import re

    score = 30
    signals = {}

    signals["schema"] = 'application/ld+json' in html
    signals["ratings"] = '"ratingValue"' in html or '"aggregateRating"' in html
    signals["action"] = bool(re.search(r'(potentialAction|OrderAction|ReserveAction)', html))
    signals["booking"] = bool(re.search(r'(book|reserve|buy|예약|구매)', html, re.IGNORECASE))
    signals["semantic_html"] = bool(re.search(r'<(main|article|section)[^>]*>', html, re.IGNORECASE))

    score += sum(14 for v in signals.values() if v)

    return {"score": min(100, max(0, score)), "signals": signals}


def analyze_single_competitor(url: str) -> dict:
    """Analyze a single competitor URL across all pillars."""
    validation = validate_url(url)
    if not validation["valid"]:
        return {"url": url, "success": False, "error": validation["error"]}

    result = fetch_page(url)
    if not result["success"]:
        return {"url": url, "success": False, "error": result["error"]}

    html = result["html"]
    elapsed = result.get("elapsed_seconds", 0)

    seo = quick_seo_score(html, elapsed)
    geo = quick_geo_score(html)
    aao = quick_aao_score(html)

    three_o = round(seo["score"] * 0.35 + geo["score"] * 0.35 + aao["score"] * 0.30, 1)

    return {
        "url": url,
        "success": True,
        "three_o_score": three_o,
        "seo": seo,
        "geo": geo,
        "aao": aao,
        "response_time": round(elapsed, 2),
    }


def compare_competitors(urls: list) -> dict:
    """Compare multiple competitors across all pillars."""
    results = []
    for url in urls:
        analysis = analyze_single_competitor(url)
        results.append(analysis)

    successful = [r for r in results if r.get("success")]
    if not successful:
        return {"success": False, "error": "No URLs could be analyzed"}

    successful.sort(key=lambda x: x["three_o_score"], reverse=True)

    leader = successful[0]
    gaps = []
    if len(successful) >= 2:
        target = successful[0]
        others = successful[1:]
        for other in others:
            for pillar in ["seo", "geo", "aao"]:
                delta = target[pillar]["score"] - other[pillar]["score"]
                if abs(delta) > 10:
                    direction = "leads" if delta > 0 else "trails"
                    gaps.append({
                        "url": other["url"],
                        "pillar": pillar.upper(),
                        "delta": round(delta),
                        "direction": direction,
                    })

    return {
        "success": True,
        "competitors_analyzed": len(successful),
        "rankings": [
            {
                "rank": i + 1,
                "url": r["url"],
                "three_o_score": r["three_o_score"],
                "seo": r["seo"]["score"],
                "geo": r["geo"]["score"],
                "aao": r["aao"]["score"],
            }
            for i, r in enumerate(successful)
        ],
        "leader": leader["url"],
        "gaps": gaps[:10],
        "detail": results,
    }


def main():
    parser = argparse.ArgumentParser(description="Cross-pillar competitor benchmarking")
    parser.add_argument("urls", nargs="+", help="URLs to compare (space-separated)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    result = compare_competitors(args.urls)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result["success"]:
            print(f"Competitor Benchmark ({result['competitors_analyzed']} sites)")
            print(f"\n{'Rank':<5} {'URL':<40} {'Three-O':>8} {'SEO':>5} {'GEO':>5} {'AAO':>5}")
            print("-" * 70)
            for r in result["rankings"]:
                url_short = r["url"][:38]
                print(f"{r['rank']:<5} {url_short:<40} {r['three_o_score']:>7.1f} {r['seo']:>5} {r['geo']:>5} {r['aao']:>5}")
            if result["gaps"]:
                print(f"\nNotable Gaps:")
                for gap in result["gaps"][:5]:
                    print(f"  {gap['url'][:30]} {gap['direction']} by {abs(gap['delta'])} in {gap['pillar']}")
        else:
            print(f"Error: {result['error']}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()

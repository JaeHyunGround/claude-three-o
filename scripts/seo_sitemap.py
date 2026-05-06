"""Sitemap validation script for Three-O platform."""

import argparse
import json
import re
import sys
from urllib.parse import urlparse

from validate_url import validate_url
from fetch_page import fetch_page


def fetch_sitemap(url: str) -> dict:
    """Fetch and parse sitemap XML."""
    parsed = urlparse(url)
    sitemap_urls = [
        f"{parsed.scheme}://{parsed.netloc}/sitemap.xml",
        f"{parsed.scheme}://{parsed.netloc}/sitemap_index.xml",
        f"{parsed.scheme}://{parsed.netloc}/sitemap/sitemap.xml",
    ]

    for sitemap_url in sitemap_urls:
        result = fetch_page(sitemap_url)
        if result["success"] and result.get("status_code") == 200 and "<urlset" in result.get("html", ""):
            return {"found": True, "url": sitemap_url, "content": result["html"]}
        if result["success"] and "<sitemapindex" in result.get("html", ""):
            return {"found": True, "url": sitemap_url, "content": result["html"], "is_index": True}

    return {"found": False}


def parse_sitemap(content: str) -> dict:
    """Parse sitemap XML content."""
    urls = re.findall(r"<loc>(.*?)</loc>", content)
    lastmods = re.findall(r"<lastmod>(.*?)</lastmod>", content)
    priorities = re.findall(r"<priority>(.*?)</priority>", content)
    changefreqs = re.findall(r"<changefreq>(.*?)</changefreq>", content)

    is_index = "<sitemapindex" in content
    child_sitemaps = []
    if is_index:
        child_sitemaps = urls
        urls = []

    return {
        "is_index": is_index,
        "url_count": len(urls),
        "child_sitemaps": child_sitemaps,
        "has_lastmod": len(lastmods) > 0,
        "lastmod_coverage": round(len(lastmods) / max(len(urls), 1), 2),
        "has_priority": len(priorities) > 0,
        "has_changefreq": len(changefreqs) > 0,
        "sample_urls": urls[:10],
    }


def validate_sitemap(url: str) -> dict:
    """Full sitemap validation."""
    validation = validate_url(url)
    if not validation["valid"]:
        return {"success": False, "error": validation["error"]}

    sitemap_result = fetch_sitemap(url)
    if not sitemap_result["found"]:
        return {
            "success": True,
            "url": url,
            "sitemap_found": False,
            "score": 0,
            "issues": [{"severity": "high", "message": "No sitemap.xml found"}],
        }

    parsed = parse_sitemap(sitemap_result["content"])

    issues = []
    if parsed["url_count"] == 0 and not parsed["is_index"]:
        issues.append({"severity": "high", "message": "Sitemap is empty (no URLs)"})
    if parsed["url_count"] > 50000:
        issues.append({"severity": "medium", "message": f"Sitemap exceeds 50,000 URL limit ({parsed['url_count']})"})
    if not parsed["has_lastmod"]:
        issues.append({"severity": "medium", "message": "Missing lastmod dates"})
    elif parsed["lastmod_coverage"] < 0.8:
        issues.append({"severity": "low", "message": f"lastmod only on {parsed['lastmod_coverage']:.0%} of URLs"})

    score = 100
    if not sitemap_result["found"]:
        score = 0
    else:
        score -= sum(20 if i["severity"] == "high" else 10 if i["severity"] == "medium" else 5 for i in issues)
    score = max(0, min(100, score))

    return {
        "success": True,
        "url": url,
        "sitemap_found": True,
        "sitemap_url": sitemap_result["url"],
        "score": score,
        "parsed": parsed,
        "issues": issues,
    }


def main():
    parser = argparse.ArgumentParser(description="Sitemap validation")
    parser.add_argument("url", help="Site URL to check sitemap")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    result = validate_sitemap(args.url)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result["sitemap_found"]:
            print(f"Sitemap Score: {result['score']}/100")
            print(f"Location: {result['sitemap_url']}")
            p = result["parsed"]
            print(f"URLs: {p['url_count']} | Index: {'Yes' if p['is_index'] else 'No'}")
            print(f"lastmod: {'✓' if p['has_lastmod'] else '✗'} | priority: {'✓' if p['has_priority'] else '✗'}")
        else:
            print("✗ No sitemap.xml found")
        for issue in result.get("issues", []):
            print(f"  [{issue['severity'].upper()}] {issue['message']}")


if __name__ == "__main__":
    main()

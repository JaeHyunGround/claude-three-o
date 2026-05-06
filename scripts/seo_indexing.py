"""Indexing and crawl management script for Three-O platform."""

import argparse
import json
import re
import sys
from urllib.parse import urljoin, urlparse

from validate_url import validate_url
from fetch_page import fetch_page


def check_robots_txt(url: str) -> dict:
    """Fetch and analyze robots.txt."""
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    result = fetch_page(robots_url)
    if not result["success"] or result.get("status_code") != 200:
        return {"exists": False, "url": robots_url}

    content = result["html"]
    sitemaps = re.findall(r"Sitemap:\s*(.+)", content, re.IGNORECASE)
    disallow_all = "Disallow: /" in content and "Disallow: / " not in content

    return {
        "exists": True,
        "url": robots_url,
        "sitemaps_declared": sitemaps,
        "disallow_all_detected": disallow_all,
        "size_bytes": len(content),
    }


def check_sitemap(url: str) -> dict:
    """Fetch and validate sitemap.xml."""
    parsed = urlparse(url)
    sitemap_url = f"{parsed.scheme}://{parsed.netloc}/sitemap.xml"

    result = fetch_page(sitemap_url)
    if not result["success"] or result.get("status_code") != 200:
        return {"exists": False, "url": sitemap_url}

    content = result["html"]
    urls = re.findall(r"<loc>(.*?)</loc>", content)
    is_index = "<sitemapindex" in content

    return {
        "exists": True,
        "url": sitemap_url,
        "is_sitemap_index": is_index,
        "url_count": len(urls),
        "sample_urls": urls[:5],
        "has_lastmod": "<lastmod>" in content,
    }


def check_indexnow(url: str) -> dict:
    """Check IndexNow key presence."""
    parsed = urlparse(url)
    key_patterns = [
        f"{parsed.scheme}://{parsed.netloc}/indexnow-key.txt",
        f"{parsed.scheme}://{parsed.netloc}/.well-known/indexnow-key.txt",
    ]

    for key_url in key_patterns:
        result = fetch_page(key_url)
        if result["success"] and result.get("status_code") == 200:
            return {"configured": True, "key_url": key_url}

    return {"configured": False}


def check_meta_robots(html: str) -> dict:
    """Check meta robots directives."""
    noindex = bool(re.search(r'name="robots"[^>]*content="[^"]*noindex', html, re.IGNORECASE))
    nofollow = bool(re.search(r'name="robots"[^>]*content="[^"]*nofollow', html, re.IGNORECASE))
    canonical = re.search(r'rel="canonical"[^>]*href="([^"]*)"', html, re.IGNORECASE)

    return {
        "noindex": noindex,
        "nofollow": nofollow,
        "canonical": canonical.group(1) if canonical else None,
    }


def analyze_indexing(url: str) -> dict:
    """Run indexing analysis."""
    validation = validate_url(url)
    if not validation["valid"]:
        return {"success": False, "error": validation["error"]}

    result = fetch_page(url)
    if not result["success"]:
        return {"success": False, "error": result["error"]}

    robots = check_robots_txt(url)
    sitemap = check_sitemap(url)
    indexnow = check_indexnow(url)
    meta = check_meta_robots(result["html"])

    issues = []
    if not robots["exists"]:
        issues.append({"severity": "medium", "message": "No robots.txt found"})
    if not sitemap["exists"]:
        issues.append({"severity": "high", "message": "No sitemap.xml found"})
    elif not sitemap["has_lastmod"]:
        issues.append({"severity": "low", "message": "Sitemap missing lastmod dates"})
    if meta["noindex"]:
        issues.append({"severity": "critical", "message": "Page has noindex directive"})
    if not indexnow["configured"]:
        issues.append({"severity": "low", "message": "IndexNow not configured"})

    score = 100 - sum(25 if i["severity"] == "critical" else 15 if i["severity"] == "high" else 5 for i in issues)
    score = max(0, min(100, score))

    return {
        "success": True,
        "url": url,
        "score": score,
        "robots_txt": robots,
        "sitemap": sitemap,
        "indexnow": indexnow,
        "meta_robots": meta,
        "issues": issues,
    }


def main():
    parser = argparse.ArgumentParser(description="Indexing and crawl analysis")
    parser.add_argument("url", help="URL to analyze")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    result = analyze_indexing(args.url)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result["success"]:
            print(f"Indexing Score: {result['score']}/100")
            print(f"robots.txt: {'✓' if result['robots_txt']['exists'] else '✗'}")
            print(f"sitemap.xml: {'✓' if result['sitemap']['exists'] else '✗'} ({result['sitemap'].get('url_count', 0)} URLs)")
            print(f"IndexNow: {'✓' if result['indexnow']['configured'] else '✗'}")
            for issue in result["issues"]:
                print(f"  [{issue['severity'].upper()}] {issue['message']}")
        else:
            print(f"Error: {result['error']}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()

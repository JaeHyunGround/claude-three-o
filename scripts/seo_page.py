"""Single-page SEO analysis script for Three-O platform."""

import argparse
import json
import re
import sys

from validate_url import validate_url
from fetch_page import fetch_page


def analyze_title(html: str) -> dict:
    """Analyze title tag."""
    match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if not match:
        return {"present": False, "text": None, "length": 0}

    title = match.group(1).strip()
    korean_chars = len(re.findall(r"[가-힯]", title))
    return {
        "present": True,
        "text": title,
        "length": len(title),
        "korean_chars": korean_chars,
        "too_long": korean_chars > 30 if korean_chars > 0 else len(title) > 60,
    }


def analyze_meta_description(html: str) -> dict:
    """Analyze meta description."""
    match = re.search(r'name="description"\s+content="([^"]*)"', html, re.IGNORECASE)
    if not match:
        match = re.search(r'content="([^"]*)"\s+name="description"', html, re.IGNORECASE)
    if not match:
        return {"present": False, "text": None, "length": 0}

    desc = match.group(1).strip()
    korean_chars = len(re.findall(r"[가-힯]", desc))
    return {
        "present": True,
        "text": desc,
        "length": len(desc),
        "korean_chars": korean_chars,
        "too_long": korean_chars > 80 if korean_chars > 0 else len(desc) > 160,
    }


def analyze_images(html: str) -> dict:
    """Analyze image optimization."""
    images = re.findall(r'<img[^>]*>', html, re.IGNORECASE)
    with_alt = sum(1 for img in images if 'alt=' in img and 'alt=""' not in img)
    return {
        "total": len(images),
        "with_alt": with_alt,
        "missing_alt": len(images) - with_alt,
        "alt_ratio": round(with_alt / max(len(images), 1), 2),
    }


def analyze_links(html: str, url: str) -> dict:
    """Analyze internal and external links."""
    from urllib.parse import urlparse
    parsed = urlparse(url)
    domain = parsed.netloc

    all_links = re.findall(r'href="([^"]*)"', html)
    internal = sum(1 for lk in all_links if domain in lk or lk.startswith("/"))
    external = sum(1 for lk in all_links if lk.startswith("http") and domain not in lk)

    return {
        "total": len(all_links),
        "internal": internal,
        "external": external,
    }


def analyze_single_page(url: str) -> dict:
    """Run comprehensive single-page analysis."""
    validation = validate_url(url)
    if not validation["valid"]:
        return {"success": False, "error": validation["error"]}

    result = fetch_page(url)
    if not result["success"]:
        return {"success": False, "error": result["error"]}

    html = result["html"]
    title = analyze_title(html)
    meta_desc = analyze_meta_description(html)
    images = analyze_images(html)
    links = analyze_links(html, url)

    h1_count = len(re.findall(r"<h1[^>]*>", html, re.IGNORECASE))
    has_schema = "application/ld+json" in html
    has_canonical = 'rel="canonical"' in html

    issues = []
    if not title["present"]:
        issues.append({"severity": "critical", "message": "Missing title tag"})
    elif title.get("too_long"):
        issues.append({"severity": "medium", "message": "Title too long for SERP display"})
    if not meta_desc["present"]:
        issues.append({"severity": "high", "message": "Missing meta description"})
    elif meta_desc.get("too_long"):
        issues.append({"severity": "low", "message": "Meta description may be truncated"})
    if h1_count == 0:
        issues.append({"severity": "critical", "message": "Missing H1 tag"})
    elif h1_count > 1:
        issues.append({"severity": "medium", "message": f"Multiple H1 tags ({h1_count})"})
    if images["missing_alt"] > 0:
        issues.append({"severity": "medium", "message": f"{images['missing_alt']} images missing alt text"})
    if not has_schema:
        issues.append({"severity": "medium", "message": "No JSON-LD structured data found"})
    if not has_canonical:
        issues.append({"severity": "medium", "message": "Missing canonical tag"})

    score = 100 - sum(25 if i["severity"] == "critical" else 10 if i["severity"] == "high" else 5 for i in issues)
    score = max(0, min(100, score))

    return {
        "success": True,
        "url": url,
        "score": score,
        "title": title,
        "meta_description": meta_desc,
        "h1_count": h1_count,
        "images": images,
        "links": links,
        "has_schema": has_schema,
        "has_canonical": has_canonical,
        "response_time": result.get("elapsed_seconds"),
        "issues": issues,
    }


def main():
    parser = argparse.ArgumentParser(description="Single-page SEO analysis")
    parser.add_argument("url", help="URL to analyze")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    result = analyze_single_page(args.url)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result["success"]:
            print(f"Page SEO Score: {result['score']}/100")
            print(f"Title: {'✓' if result['title']['present'] else '✗'} | Meta: {'✓' if result['meta_description']['present'] else '✗'} | Schema: {'✓' if result['has_schema'] else '✗'}")
            print(f"Images: {result['images']['total']} (alt: {result['images']['with_alt']})")
            print(f"Links: {result['links']['internal']} internal, {result['links']['external']} external")
            for issue in result["issues"]:
                print(f"  [{issue['severity'].upper()}] {issue['message']}")
        else:
            print(f"Error: {result['error']}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()

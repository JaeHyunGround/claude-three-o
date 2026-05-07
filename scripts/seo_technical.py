"""Technical SEO analysis script for Three-O platform."""

import argparse
import json
import re
import sys
from typing import Optional

from validate_url import validate_url
from fetch_page import fetch_page


def analyze_meta_tags(html: str) -> dict:
    """Extract and analyze meta tags from HTML."""
    from html.parser import HTMLParser

    tags = {}

    class MetaParser(HTMLParser):
        def handle_starttag(self, tag, attrs):
            if tag == "meta":
                attrs_dict = dict(attrs)
                name = attrs_dict.get("name", attrs_dict.get("property", ""))
                content = attrs_dict.get("content", "")
                if name:
                    tags[name] = content
            elif tag == "title":
                self.in_title = True
            elif tag == "link":
                attrs_dict = dict(attrs)
                if attrs_dict.get("rel") == "canonical":
                    tags["canonical"] = attrs_dict.get("href", "")

        def handle_data(self, data):
            if getattr(self, "in_title", False):
                tags["title"] = data.strip()
                self.in_title = False

    parser = MetaParser()
    parser.feed(html)
    return tags


def evaluate_meta_quality(meta: dict, url: str) -> dict:
    """Evaluate the quality of meta tags, not just their existence."""
    quality = {"score": 0, "checks": [], "issues": []}
    total_weight = 0
    weighted_score = 0

    title = meta.get("title", "")
    title_weight = 20
    total_weight += title_weight
    if title:
        title_len = len(title)
        if 30 <= title_len <= 60:
            weighted_score += title_weight
            quality["checks"].append({"tag": "title", "status": "optimal", "value": title_len, "detail": f"{title_len} chars (ideal: 30-60)"})
        elif 20 <= title_len < 30 or 60 < title_len <= 70:
            weighted_score += title_weight * 0.7
            quality["checks"].append({"tag": "title", "status": "acceptable", "value": title_len, "detail": f"{title_len} chars (slightly off)"})
        else:
            weighted_score += title_weight * 0.3
            quality["issues"].append({"severity": "medium", "message": f"Title length {title_len} chars (ideal: 30-60)"})
    else:
        quality["issues"].append({"severity": "critical", "message": "Missing title tag"})

    desc = meta.get("description", "")
    desc_weight = 15
    total_weight += desc_weight
    if desc:
        desc_len = len(desc)
        if 120 <= desc_len <= 160:
            weighted_score += desc_weight
            quality["checks"].append({"tag": "description", "status": "optimal", "value": desc_len, "detail": f"{desc_len} chars (ideal: 120-160)"})
        elif 80 <= desc_len < 120 or 160 < desc_len <= 200:
            weighted_score += desc_weight * 0.7
            quality["checks"].append({"tag": "description", "status": "acceptable", "value": desc_len, "detail": f"{desc_len} chars"})
        else:
            weighted_score += desc_weight * 0.3
            quality["issues"].append({"severity": "low", "message": f"Description length {desc_len} chars (ideal: 120-160)"})
        if title and desc == title:
            weighted_score -= desc_weight * 0.3
            quality["issues"].append({"severity": "medium", "message": "Description duplicates title"})
    else:
        quality["issues"].append({"severity": "high", "message": "Missing meta description"})

    canonical = meta.get("canonical", "")
    canon_weight = 10
    total_weight += canon_weight
    if canonical:
        if canonical.startswith("http"):
            weighted_score += canon_weight
            if canonical.startswith("http://") and url.startswith("https://"):
                weighted_score -= canon_weight * 0.4
                quality["issues"].append({"severity": "medium", "message": "Canonical uses HTTP but page is HTTPS"})
        else:
            weighted_score += canon_weight * 0.5
            quality["issues"].append({"severity": "low", "message": "Canonical is relative URL (absolute recommended)"})
    else:
        quality["issues"].append({"severity": "medium", "message": "Missing canonical tag"})

    og_tags = ["og:title", "og:description", "og:image", "og:url"]
    og_weight = 10
    total_weight += og_weight
    og_present = sum(1 for t in og_tags if meta.get(t))
    og_ratio = og_present / len(og_tags)
    weighted_score += og_weight * og_ratio
    if og_ratio < 1.0:
        missing = [t for t in og_tags if not meta.get(t)]
        quality["issues"].append({"severity": "low", "message": f"Missing OG tags: {', '.join(missing)}"})

    twitter_tags = ["twitter:card", "twitter:title", "twitter:description"]
    tw_weight = 5
    total_weight += tw_weight
    tw_present = sum(1 for t in twitter_tags if meta.get(t))
    weighted_score += tw_weight * (tw_present / len(twitter_tags))

    quality["score"] = round((weighted_score / max(total_weight, 1)) * 100, 1)
    return quality


def analyze_heading_structure(html: str) -> dict:
    """Analyze heading hierarchy and H1 usage."""
    h1s = re.findall(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL | re.IGNORECASE)
    h2s = re.findall(r'<h2[^>]*>(.*?)</h2>', html, re.DOTALL | re.IGNORECASE)
    h3s = re.findall(r'<h3[^>]*>(.*?)</h3>', html, re.DOTALL | re.IGNORECASE)

    h1_clean = [re.sub(r'<[^>]+>', '', h).strip() for h in h1s]
    issues = []

    if len(h1s) == 0:
        issues.append({"severity": "high", "category": "structure", "message": "Missing H1 tag"})
    elif len(h1s) > 1:
        issues.append({"severity": "medium", "category": "structure", "message": f"Multiple H1 tags ({len(h1s)}) — use only one"})

    if len(h2s) == 0 and len(h3s) > 0:
        issues.append({"severity": "medium", "category": "structure", "message": "H3 used without H2 — broken heading hierarchy"})

    return {
        "h1_count": len(h1s),
        "h2_count": len(h2s),
        "h3_count": len(h3s),
        "h1_text": h1_clean[:3],
        "hierarchy_valid": len(h1s) == 1 and (len(h2s) > 0 or len(h3s) == 0),
        "issues": issues,
    }


def analyze_images(html: str) -> dict:
    """Analyze image alt text coverage."""
    images = re.findall(r'<img[^>]*>', html, re.IGNORECASE)
    total = len(images)
    with_alt = sum(1 for img in images if re.search(r'alt="[^"]+"|alt=\'[^\']+\'', img, re.IGNORECASE))
    empty_alt = sum(1 for img in images if re.search(r'alt=""|alt=\'\'', img, re.IGNORECASE))
    missing_alt = total - with_alt - empty_alt

    issues = []
    if total > 0 and missing_alt > 0:
        issues.append({"severity": "medium", "category": "accessibility", "message": f"{missing_alt}/{total} images missing alt text"})

    coverage = round((with_alt / max(total, 1)) * 100, 1)
    return {"total": total, "with_alt": with_alt, "missing_alt": missing_alt, "coverage": coverage, "issues": issues}


def analyze_links(html: str, url: str) -> dict:
    """Analyze internal vs external link distribution."""
    domain = url.split('/')[2] if len(url.split('/')) > 2 else ""
    all_links = re.findall(r'<a[^>]+href="([^"]*)"', html, re.IGNORECASE)

    internal = 0
    external = 0
    for link in all_links:
        if link.startswith('#') or link.startswith('javascript'):
            continue
        if link.startswith('/') or domain in link:
            internal += 1
        elif link.startswith('http'):
            external += 1

    return {"internal": internal, "external": external, "total": internal + external}


def check_https(url: str) -> dict:
    """Check HTTPS and security headers."""
    result = fetch_page(url, user_agent="default")
    if not result["success"]:
        return {"https": False, "error": result["error"]}

    headers = result.get("headers", {})
    return {
        "https": url.startswith("https"),
        "hsts": "strict-transport-security" in headers,
        "x_content_type": "x-content-type-options" in headers,
        "x_frame": "x-frame-options" in headers,
        "csp": "content-security-policy" in headers,
    }


def check_mobile(html: str) -> dict:
    """Check mobile optimization signals."""
    has_viewport = 'name="viewport"' in html or "name='viewport'" in html
    has_responsive = "@media" in html or 'rel="stylesheet"' in html
    return {
        "viewport_meta": has_viewport,
        "responsive_signals": has_responsive,
    }


def analyze_technical(url: str) -> dict:
    """Run full technical SEO analysis."""
    validation = validate_url(url)
    if not validation["valid"]:
        return {"success": False, "error": validation["error"]}

    result = fetch_page(url)
    if not result["success"]:
        return {"success": False, "error": result["error"]}

    html = result["html"]
    meta = analyze_meta_tags(html)
    meta_quality = evaluate_meta_quality(meta, url)
    security = check_https(url)
    mobile = check_mobile(html)
    headings = analyze_heading_structure(html)
    images = analyze_images(html)
    links = analyze_links(html, url)

    issues = []
    issues.extend(meta_quality["issues"])
    issues.extend(headings["issues"])
    issues.extend(images["issues"])

    if not security.get("https"):
        issues.append({"severity": "critical", "category": "security", "message": "Not using HTTPS"})
    if not security.get("hsts"):
        issues.append({"severity": "medium", "category": "security", "message": "Missing HSTS header"})
    if not security.get("x_content_type"):
        issues.append({"severity": "low", "category": "security", "message": "Missing X-Content-Type-Options header"})
    if not security.get("x_frame"):
        issues.append({"severity": "low", "category": "security", "message": "Missing X-Frame-Options header"})
    if not mobile.get("viewport_meta"):
        issues.append({"severity": "critical", "category": "mobile", "message": "Missing viewport meta tag"})

    elapsed = result.get("elapsed_seconds", 0)
    if elapsed and elapsed > 3.0:
        issues.append({"severity": "high", "category": "performance", "message": f"Slow response time: {elapsed:.1f}s (target: <1s)"})
    elif elapsed and elapsed > 1.0:
        issues.append({"severity": "medium", "category": "performance", "message": f"Response time {elapsed:.1f}s (target: <1s)"})

    has_lang = bool(re.search(r'<html[^>]+lang=', html, re.IGNORECASE))
    if not has_lang:
        issues.append({"severity": "low", "category": "indexability", "message": "Missing lang attribute on <html>"})

    section_scores = {
        "meta_quality": meta_quality["score"],
        "security": round((sum([security.get("https", False), security.get("hsts", False),
                                security.get("x_content_type", False), security.get("x_frame", False),
                                security.get("csp", False)]) / 5) * 100, 1),
        "mobile": round((sum([mobile.get("viewport_meta", False), mobile.get("responsive_signals", False)]) / 2) * 100, 1),
        "headings": 100.0 if headings["hierarchy_valid"] else 50.0,
        "images": images["coverage"],
        "performance": 100.0 if (elapsed or 0) < 0.5 else 80.0 if (elapsed or 0) < 1.0 else 50.0 if (elapsed or 0) < 3.0 else 20.0,
    }

    weights = {"meta_quality": 0.30, "security": 0.15, "mobile": 0.15, "headings": 0.15, "images": 0.10, "performance": 0.15}
    score = round(sum(section_scores[k] * weights[k] for k in weights), 1)

    return {
        "success": True,
        "url": url,
        "score": score,
        "section_scores": section_scores,
        "meta_tags": meta,
        "meta_quality": meta_quality["checks"],
        "security": security,
        "mobile": mobile,
        "headings": headings,
        "images": {"total": images["total"], "with_alt": images["with_alt"], "coverage": images["coverage"]},
        "links": links,
        "issues": issues,
        "response_time": elapsed,
    }


def main():
    parser = argparse.ArgumentParser(description="Technical SEO analysis")
    parser.add_argument("url", help="URL to analyze")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    result = analyze_technical(args.url)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result["success"]:
            print(f"Technical SEO Score: {result['score']}/100")
            print(f"Issues found: {len(result['issues'])}")
            for issue in result["issues"]:
                print(f"  [{issue['severity'].upper()}] {issue['message']}")
        else:
            print(f"Error: {result['error']}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()

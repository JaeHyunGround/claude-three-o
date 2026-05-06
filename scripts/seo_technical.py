"""Technical SEO analysis script for Three-O platform."""

import argparse
import json
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
    security = check_https(url)
    mobile = check_mobile(html)

    issues = []
    if not meta.get("title"):
        issues.append({"severity": "critical", "category": "indexability", "message": "Missing title tag"})
    if not meta.get("description"):
        issues.append({"severity": "high", "category": "indexability", "message": "Missing meta description"})
    if not meta.get("canonical"):
        issues.append({"severity": "medium", "category": "indexability", "message": "Missing canonical tag"})
    if not security.get("https"):
        issues.append({"severity": "critical", "category": "security", "message": "Not using HTTPS"})
    if not security.get("hsts"):
        issues.append({"severity": "medium", "category": "security", "message": "Missing HSTS header"})
    if not mobile.get("viewport_meta"):
        issues.append({"severity": "critical", "category": "mobile", "message": "Missing viewport meta tag"})

    score = 100 - (sum(25 if i["severity"] == "critical" else 10 if i["severity"] == "high" else 5 for i in issues))
    score = max(0, min(100, score))

    return {
        "success": True,
        "url": url,
        "score": score,
        "meta_tags": meta,
        "security": security,
        "mobile": mobile,
        "issues": issues,
        "response_time": result.get("elapsed_seconds"),
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

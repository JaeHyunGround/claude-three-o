"""Naver-specific SEO analysis script for Three-O platform."""

import argparse
import json
import re
import sys

from validate_url import validate_url
from fetch_page import fetch_page


def check_naver_verification(html: str) -> dict:
    """Check for Naver site verification meta tag."""
    match = re.search(r'name="naver-site-verification"\s+content="([^"]*)"', html, re.IGNORECASE)
    if not match:
        match = re.search(r'content="([^"]*)"\s+name="naver-site-verification"', html, re.IGNORECASE)
    return {
        "present": match is not None,
        "code": match.group(1) if match else None,
    }


def check_open_graph(html: str) -> dict:
    """Check Open Graph tags (Naver uses these heavily)."""
    og_tags = {}
    patterns = re.findall(r'property="(og:[^"]+)"\s+content="([^"]*)"', html, re.IGNORECASE)
    patterns += re.findall(r'content="([^"]*)"\s+property="(og:[^"]+)"', html, re.IGNORECASE)

    for match in patterns:
        if match[0].startswith("og:"):
            og_tags[match[0]] = match[1]
        else:
            og_tags[match[1]] = match[0]

    required = ["og:title", "og:description", "og:image", "og:url"]
    missing = [tag for tag in required if tag not in og_tags]

    return {
        "tags_found": og_tags,
        "count": len(og_tags),
        "missing_required": missing,
        "complete": len(missing) == 0,
    }


def check_naver_bot_access(url: str) -> dict:
    """Check if Naver's Yeti bot can access the site."""
    from urllib.parse import urlparse
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    result = fetch_page(robots_url)
    if not result["success"]:
        return {"accessible": True, "robots_txt": False, "note": "No robots.txt found"}

    content = result["html"].lower()
    yeti_blocked = False

    lines = content.split("\n")
    current_agent = ""
    for line in lines:
        line = line.strip()
        if line.startswith("user-agent:"):
            current_agent = line.split(":", 1)[1].strip()
        elif line.startswith("disallow:") and current_agent in ("*", "yeti"):
            path = line.split(":", 1)[1].strip()
            if path == "/":
                yeti_blocked = True

    return {
        "accessible": not yeti_blocked,
        "robots_txt": True,
        "yeti_blocked": yeti_blocked,
    }


def analyze_naver_seo(url: str) -> dict:
    """Run Naver-specific SEO analysis."""
    validation = validate_url(url)
    if not validation["valid"]:
        return {"success": False, "error": validation["error"]}

    result = fetch_page(url)
    if not result["success"]:
        return {"success": False, "error": result["error"]}

    html = result["html"]
    verification = check_naver_verification(html)
    og = check_open_graph(html)
    bot_access = check_naver_bot_access(url)

    issues = []
    if not verification["present"]:
        issues.append({"severity": "high", "message": "Missing naver-site-verification meta tag"})
    if not og["complete"]:
        for tag in og["missing_required"]:
            issues.append({"severity": "medium", "message": f"Missing {tag} (Naver uses OG tags)"})
    if not bot_access["accessible"]:
        issues.append({"severity": "critical", "message": "Naver Yeti bot is blocked in robots.txt"})

    score = 100 - sum(25 if i["severity"] == "critical" else 15 if i["severity"] == "high" else 5 for i in issues)
    score = max(0, min(100, score))

    return {
        "success": True,
        "url": url,
        "score": score,
        "naver_verification": verification,
        "open_graph": og,
        "bot_access": bot_access,
        "issues": issues,
    }


def main():
    parser = argparse.ArgumentParser(description="Naver SEO analysis")
    parser.add_argument("url", help="URL to analyze")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    result = analyze_naver_seo(args.url)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result["success"]:
            print(f"Naver SEO Score: {result['score']}/100")
            print(f"Verification: {'✓' if result['naver_verification']['present'] else '✗'}")
            print(f"Open Graph: {'✓ Complete' if result['open_graph']['complete'] else '✗ Incomplete'}")
            print(f"Yeti access: {'✓' if result['bot_access']['accessible'] else '✗ BLOCKED'}")
            for issue in result["issues"]:
                print(f"  [{issue['severity'].upper()}] {issue['message']}")
        else:
            print(f"Error: {result['error']}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()

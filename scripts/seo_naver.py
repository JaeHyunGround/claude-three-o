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

    image_ok = False
    image_width = 0
    image_height = 0
    if "og:image" in og_tags:
        w = og_tags.get("og:image:width", "")
        h = og_tags.get("og:image:height", "")
        if w.isdigit() and h.isdigit():
            image_width = int(w)
            image_height = int(h)
            image_ok = image_width >= 200 and image_height >= 200
        else:
            image_ok = None

    return {
        "tags_found": og_tags,
        "count": len(og_tags),
        "missing_required": missing,
        "complete": len(missing) == 0,
        "image_dimensions": {"width": image_width, "height": image_height, "valid": image_ok},
    }


def check_naver_bot_access(url: str) -> dict:
    """Check if Naver's Yeti bot can access the site."""
    from urllib.parse import urlparse
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    result = fetch_page(robots_url)
    if not result["success"]:
        return {"accessible": True, "robots_txt": False, "crawl_delay": None, "note": "No robots.txt found"}

    content = result["html"].lower()
    yeti_blocked = False
    crawl_delay = None

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
        elif line.startswith("crawl-delay:") and current_agent in ("*", "yeti"):
            try:
                crawl_delay = int(line.split(":", 1)[1].strip())
            except ValueError:
                pass

    return {
        "accessible": not yeti_blocked,
        "robots_txt": True,
        "yeti_blocked": yeti_blocked,
        "crawl_delay": crawl_delay,
    }


def check_x_robots_tag(headers: dict) -> dict:
    """Check X-Robots-Tag header for Naver/Yeti directives."""
    x_robots = headers.get("x-robots-tag", "")
    if not x_robots:
        x_robots = headers.get("X-Robots-Tag", "")

    has_noindex = False
    has_nofollow = False
    yeti_specific = False

    if x_robots:
        lower = x_robots.lower()
        if "yeti" in lower or "all" in lower.split(":")[0] if ":" in lower else True:
            has_noindex = "noindex" in lower
            has_nofollow = "nofollow" in lower
            yeti_specific = "yeti" in lower

    return {
        "present": bool(x_robots),
        "value": x_robots,
        "noindex": has_noindex,
        "nofollow": has_nofollow,
        "yeti_specific": yeti_specific,
    }


def check_meta_description_korean(html: str) -> dict:
    """Check meta description length for Naver (truncates at ~77 Korean chars)."""
    match = re.search(r'name="description"\s+content="([^"]*)"', html, re.IGNORECASE)
    if not match:
        match = re.search(r'content="([^"]*)"\s+name="description"', html, re.IGNORECASE)

    if not match:
        return {"present": False, "length": 0, "korean_chars": 0, "optimal": False}

    desc = match.group(1)
    korean_chars = len(re.findall(r"[가-힯]", desc))
    total_chars = len(desc)
    is_korean = korean_chars > total_chars * 0.3

    if is_korean:
        optimal = 40 <= total_chars <= 77
    else:
        optimal = 50 <= total_chars <= 160

    return {
        "present": True,
        "text": desc,
        "length": total_chars,
        "korean_chars": korean_chars,
        "is_korean": is_korean,
        "optimal": optimal,
        "truncated_by_naver": is_korean and total_chars > 77,
    }


def check_naver_ecosystem(html: str) -> dict:
    """Detect links to Naver ecosystem (Blog, Place, Smart Store, Cafe)."""
    ecosystem = {
        "blog": bool(re.search(r'href="[^"]*blog\.naver\.com', html, re.IGNORECASE)),
        "place": bool(re.search(r'href="[^"]*(?:place\.naver\.com|naver\.me/[a-zA-Z0-9])', html, re.IGNORECASE)),
        "smartstore": bool(re.search(r'href="[^"]*smartstore\.naver\.com', html, re.IGNORECASE)),
        "cafe": bool(re.search(r'href="[^"]*cafe\.naver\.com', html, re.IGNORECASE)),
        "map": bool(re.search(r'href="[^"]*map\.naver\.com', html, re.IGNORECASE)),
    }
    linked_count = sum(1 for v in ecosystem.values() if v)
    return {"links": ecosystem, "linked_count": linked_count}


def check_mobile_viewport(html: str) -> dict:
    """Check mobile viewport meta tag (Naver prioritizes mobile-friendly)."""
    match = re.search(r'name="viewport"\s+content="([^"]*)"', html, re.IGNORECASE)
    if not match:
        match = re.search(r'content="([^"]*)"\s+name="viewport"', html, re.IGNORECASE)

    if not match:
        return {"present": False, "content": None, "mobile_friendly": False}

    content = match.group(1)
    has_width = "width=device-width" in content
    has_initial = "initial-scale" in content

    return {
        "present": True,
        "content": content,
        "mobile_friendly": has_width and has_initial,
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
    headers = result.get("headers", {})

    verification = check_naver_verification(html)
    og = check_open_graph(html)
    bot_access = check_naver_bot_access(url)
    x_robots = check_x_robots_tag(headers)
    meta_desc = check_meta_description_korean(html)
    ecosystem = check_naver_ecosystem(html)
    viewport = check_mobile_viewport(html)

    issues = []
    if not verification["present"]:
        issues.append({"severity": "high", "message": "Missing naver-site-verification meta tag"})
    if not og["complete"]:
        for tag in og["missing_required"]:
            issues.append({"severity": "medium", "message": f"Missing {tag} (Naver uses OG tags)"})
    if og.get("image_dimensions", {}).get("valid") is False:
        w = og["image_dimensions"]["width"]
        h = og["image_dimensions"]["height"]
        issues.append({"severity": "medium", "message": f"og:image too small ({w}x{h}), Naver requires min 200x200"})
    if not bot_access["accessible"]:
        issues.append({"severity": "critical", "message": "Naver Yeti bot is blocked in robots.txt"})
    if bot_access.get("crawl_delay") and bot_access["crawl_delay"] > 10:
        issues.append({"severity": "medium", "message": f"High crawl-delay ({bot_access['crawl_delay']}s) slows Naver indexing"})
    if x_robots["noindex"]:
        issues.append({"severity": "critical", "message": "X-Robots-Tag contains noindex (blocks Naver indexing)"})
    if not meta_desc["present"]:
        issues.append({"severity": "high", "message": "Missing meta description"})
    elif meta_desc.get("truncated_by_naver"):
        issues.append({"severity": "low", "message": f"Meta description ({meta_desc['length']} chars) will be truncated by Naver (max ~77 Korean chars)"})
    if not viewport["mobile_friendly"]:
        issues.append({"severity": "medium", "message": "Missing mobile viewport (Naver prioritizes mobile-friendly pages)"})

    score = 100 - sum(25 if i["severity"] == "critical" else 15 if i["severity"] == "high" else 5 for i in issues)
    score = max(0, min(100, score))

    return {
        "success": True,
        "url": url,
        "score": score,
        "naver_verification": verification,
        "open_graph": og,
        "bot_access": bot_access,
        "x_robots_tag": x_robots,
        "meta_description": meta_desc,
        "naver_ecosystem": ecosystem,
        "mobile_viewport": viewport,
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

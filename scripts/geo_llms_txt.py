"""llms.txt validation and generation script for Three-O platform."""

import argparse
import json
import re
from urllib.parse import urlparse

from validate_url import validate_url
from fetch_page import fetch_page


LLMS_TXT_SPEC = {
    "title": {"required": True, "pattern": r'^# .+', "description": "Site title as H1"},
    "description": {"required": True, "pattern": r'^> .+', "description": "One-line description as blockquote"},
    "sections": {"required": True, "pattern": r'^## .+', "description": "At least one section"},
    "links": {"required": True, "pattern": r'- \[.+\]\(.+\)', "description": "Markdown links"},
}


def fetch_llms_txt(url: str) -> dict:
    """Try to fetch llms.txt from standard locations."""
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    locations = [
        f"{base}/llms.txt",
        f"{base}/.well-known/llms.txt",
    ]

    for loc in locations:
        result = fetch_page(loc)
        if result["success"] and result.get("status_code") == 200:
            content = result.get("html", "")
            if content.strip() and ("<html" not in content.lower()[:100]):
                return {"found": True, "location": loc, "content": content}

    return {"found": False}


def fetch_llms_full_txt(url: str) -> dict:
    """Check for llms-full.txt."""
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    loc = f"{base}/llms-full.txt"

    result = fetch_page(loc)
    if result["success"] and result.get("status_code") == 200:
        content = result.get("html", "")
        if content.strip() and ("<html" not in content.lower()[:100]):
            return {"found": True, "location": loc, "size_bytes": len(content.encode())}

    return {"found": False}


def validate_llms_txt_content(content: str) -> dict:
    """Validate llms.txt content against spec."""
    lines = content.split("\n")
    checks = {}

    has_title = any(re.match(r'^# .+', line) for line in lines)
    checks["title"] = {"present": has_title, "required": True}

    has_description = any(re.match(r'^> .+', line) for line in lines)
    checks["description"] = {"present": has_description, "required": True}

    sections = [line for line in lines if re.match(r'^## .+', line)]
    checks["sections"] = {"present": len(sections) > 0, "count": len(sections), "required": True}

    links = re.findall(r'- \[([^\]]+)\]\(([^)]+)\)', content)
    checks["links"] = {"present": len(links) > 0, "count": len(links), "required": True}

    has_metadata = any(re.match(r'^(Contact|Updated|Frequency):', line) for line in lines)
    checks["metadata"] = {"present": has_metadata, "required": False}

    total_required = sum(1 for c in checks.values() if c["required"])
    passed_required = sum(1 for c in checks.values() if c["required"] and c["present"])
    compliance_score = round((passed_required / max(total_required, 1)) * 70, 1)

    if has_metadata:
        compliance_score += 10
    if len(links) >= 5:
        compliance_score += 10
    if len(sections) >= 3:
        compliance_score += 10

    compliance_score = min(100.0, compliance_score)

    return {
        "checks": checks,
        "compliance_score": compliance_score,
        "sections": sections,
        "links": [{"text": text, "url": href} for text, href in links[:20]],
        "line_count": len(lines),
    }


def check_link_accessibility(links: list) -> dict:
    """Check if linked pages are accessible."""
    accessible = 0
    broken = 0
    checked = []

    for link in links[:10]:
        url = link.get("url", "")
        if not url.startswith("http"):
            continue
        result = fetch_page(url)
        status = "accessible" if result["success"] else "broken"
        if result["success"]:
            accessible += 1
        else:
            broken += 1
        checked.append({"url": url, "text": link.get("text", ""), "status": status})

    return {
        "total_checked": len(checked),
        "accessible": accessible,
        "broken": broken,
        "results": checked,
    }


def generate_llms_txt_proposal(url: str, html: str) -> str:
    """Generate a llms.txt proposal from site content."""
    parsed = urlparse(url)
    domain = parsed.netloc

    title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
    title = title_match.group(1).strip() if title_match else domain

    desc_match = re.search(r'name="description"\s+content="([^"]*)"', html, re.IGNORECASE)
    if not desc_match:
        desc_match = re.search(r'content="([^"]*)"\s+name="description"', html, re.IGNORECASE)
    description = desc_match.group(1).strip() if desc_match else f"Official website of {domain}"

    nav_links = re.findall(r'<a[^>]*href="(/[^"]*)"[^>]*>(.*?)</a>', html, re.IGNORECASE)
    pages = []
    seen = set()
    for href, text in nav_links:
        clean_text = re.sub(r'<[^>]+>', '', text).strip()
        if clean_text and href not in seen and len(clean_text) < 50:
            pages.append({"url": f"{parsed.scheme}://{domain}{href}", "text": clean_text})
            seen.add(href)
        if len(pages) >= 15:
            break

    proposal = f"# {title}\n\n"
    proposal += f"> {description}\n\n"
    proposal += "## Main Pages\n\n"
    for page in pages:
        proposal += f"- [{page['text']}]({page['url']})\n"

    if not pages:
        proposal += f"- [Homepage]({url})\n"

    return proposal


def analyze_llms_txt(url: str) -> dict:
    """Full llms.txt analysis."""
    validation = validate_url(url)
    if not validation["valid"]:
        return {"success": False, "error": validation["error"]}

    llms_result = fetch_llms_txt(url)
    llms_full = fetch_llms_full_txt(url)

    if llms_result["found"]:
        content_validation = validate_llms_txt_content(llms_result["content"])
        score = content_validation["compliance_score"]

        issues = []
        for check_name, check_info in content_validation["checks"].items():
            if check_info["required"] and not check_info["present"]:
                issues.append({"severity": "high", "message": f"Missing required field: {check_name}"})

        if content_validation["checks"]["links"]["count"] < 5:
            issues.append({"severity": "medium", "message": "Too few links — add more key pages"})

        return {
            "success": True,
            "url": url,
            "status": "present",
            "location": llms_result["location"],
            "score": score,
            "validation": content_validation,
            "llms_full_txt": llms_full,
            "issues": issues,
        }
    else:
        page_result = fetch_page(url)
        proposal = ""
        if page_result["success"]:
            proposal = generate_llms_txt_proposal(url, page_result["html"])

        return {
            "success": True,
            "url": url,
            "status": "missing",
            "score": 0,
            "llms_full_txt": llms_full,
            "issues": [{"severity": "low", "message": "No llms.txt found. Note: Google officially states llms.txt is NOT required for Google AI search (AI Overviews/AI Mode). May still help non-Google AI platforms (ChatGPT, Perplexity, Claude)."}],
            "proposal": proposal,
        }


def main():
    parser = argparse.ArgumentParser(description="llms.txt validation and generation")
    parser.add_argument("url", help="Site URL to check")
    parser.add_argument("--generate", action="store_true", help="Generate proposal if missing")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    result = analyze_llms_txt(args.url)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result["status"] == "present":
            print("llms.txt: Present ✓")
            print(f"Location: {result['location']}")
            print(f"Compliance Score: {result['score']}/100")
            v = result["validation"]
            for check_name, info in v["checks"].items():
                icon = "✓" if info["present"] else "✗"
                print(f"  {icon} {check_name}")
        else:
            print("llms.txt: Missing ✗")
            if result.get("proposal") and args.generate:
                print("\n--- Generated Proposal ---\n")
                print(result["proposal"])
        for issue in result.get("issues", []):
            print(f"  [{issue['severity'].upper()}] {issue['message']}")


if __name__ == "__main__":
    main()

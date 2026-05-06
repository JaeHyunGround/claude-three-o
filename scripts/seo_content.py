"""Content quality analysis script for Three-O platform."""

import argparse
import json
import re
import sys

from validate_url import validate_url
from fetch_page import fetch_page


def extract_text_content(html: str) -> str:
    """Strip HTML tags and extract text content."""
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def count_headings(html: str) -> dict:
    """Count heading tags by level."""
    counts = {}
    for level in range(1, 7):
        pattern = f"<h{level}[^>]*>"
        counts[f"h{level}"] = len(re.findall(pattern, html, re.IGNORECASE))
    return counts


def analyze_korean_content(text: str) -> dict:
    """Analyze Korean-specific content metrics."""
    korean_chars = len(re.findall(r"[가-힯]", text))
    total_chars = len(text)
    korean_ratio = korean_chars / max(total_chars, 1)
    return {
        "korean_chars": korean_chars,
        "total_chars": total_chars,
        "korean_ratio": round(korean_ratio, 3),
        "is_korean_content": korean_ratio > 0.3,
    }


def check_eeat_signals(html: str) -> dict:
    """Check E-E-A-T (Experience, Expertise, Authoritativeness, Trust) signals."""
    signals = {
        "author_present": bool(re.search(r'(author|writer|by\s)', html, re.IGNORECASE)),
        "date_present": bool(re.search(r'(datePublished|dateModified|published|updated)', html, re.IGNORECASE)),
        "citations": len(re.findall(r'<a[^>]+href="https?://[^"]*"[^>]*>', html)),
        "about_page_linked": bool(re.search(r'href="[^"]*about[^"]*"', html, re.IGNORECASE)),
        "contact_linked": bool(re.search(r'href="[^"]*contact[^"]*"', html, re.IGNORECASE)),
    }
    score = sum([
        20 if signals["author_present"] else 0,
        20 if signals["date_present"] else 0,
        min(20, signals["citations"] * 4),
        20 if signals["about_page_linked"] else 0,
        20 if signals["contact_linked"] else 0,
    ])
    signals["score"] = min(100, score)
    return signals


def analyze_content(url: str) -> dict:
    """Run content quality analysis."""
    validation = validate_url(url)
    if not validation["valid"]:
        return {"success": False, "error": validation["error"]}

    result = fetch_page(url)
    if not result["success"]:
        return {"success": False, "error": result["error"]}

    html = result["html"]
    text = extract_text_content(html)
    headings = count_headings(html)
    korean = analyze_korean_content(text)
    eeat = check_eeat_signals(html)

    word_count = len(text.split())
    issues = []

    if word_count < 300:
        issues.append({"severity": "high", "message": f"Thin content: {word_count} words (min 300)"})
    if headings.get("h1", 0) == 0:
        issues.append({"severity": "critical", "message": "Missing H1 tag"})
    if headings.get("h1", 0) > 1:
        issues.append({"severity": "medium", "message": f"Multiple H1 tags ({headings['h1']})"})
    if eeat["score"] < 40:
        issues.append({"severity": "high", "message": f"Weak E-E-A-T signals (score: {eeat['score']})"})

    score = min(100, max(0, 50 + (word_count // 100) + eeat["score"] // 5 - len(issues) * 10))

    return {
        "success": True,
        "url": url,
        "score": score,
        "word_count": word_count,
        "headings": headings,
        "korean_analysis": korean,
        "eeat": eeat,
        "issues": issues,
    }


def main():
    parser = argparse.ArgumentParser(description="Content quality analysis")
    parser.add_argument("url", help="URL to analyze")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    result = analyze_content(args.url)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result["success"]:
            print(f"Content Score: {result['score']}/100")
            print(f"Word count: {result['word_count']}")
            print(f"E-E-A-T score: {result['eeat']['score']}/100")
            print(f"Korean content: {'Yes' if result['korean_analysis']['is_korean_content'] else 'No'}")
            for issue in result["issues"]:
                print(f"  [{issue['severity'].upper()}] {issue['message']}")
        else:
            print(f"Error: {result['error']}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()

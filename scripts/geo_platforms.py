"""Platform-specific AI optimization analysis script for Three-O platform."""

import argparse
import json
import re
import sys
from typing import Optional

from validate_url import validate_url
from fetch_page import fetch_page


PLATFORM_CONFIGS = {
    "chatgpt": {
        "name": "ChatGPT",
        "provider": "OpenAI",
        "crawler": "GPTBot",
        "factors": ["citability", "structured_data", "authority", "freshness"],
    },
    "perplexity": {
        "name": "Perplexity",
        "provider": "Perplexity AI",
        "crawler": "PerplexityBot",
        "factors": ["source_quality", "citation_format", "factual_density", "recency"],
    },
    "gemini": {
        "name": "Gemini",
        "provider": "Google",
        "crawler": "Google-Extended",
        "factors": ["e_e_a_t", "structured_data", "knowledge_graph", "freshness"],
    },
    "claude": {
        "name": "Claude",
        "provider": "Anthropic",
        "crawler": "Anthropic-AI",
        "factors": ["content_depth", "accuracy", "structured_format", "authority"],
    },
}


def analyze_for_chatgpt(html: str, url: str) -> dict:
    """Analyze content optimization for ChatGPT citation."""
    score = 50.0
    signals = []

    has_structured = 'application/ld+json' in html
    if has_structured:
        score += 15
        signals.append("JSON-LD structured data present")

    paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', html, re.DOTALL | re.IGNORECASE)
    short_clear = sum(1 for p in paragraphs if 50 < len(re.sub(r'<[^>]+>', '', p)) < 300)
    if short_clear > 3:
        score += 10
        signals.append(f"{short_clear} clear, citable paragraphs found")

    lists = len(re.findall(r'<[ou]l[^>]*>', html, re.IGNORECASE))
    if lists > 0:
        score += 5
        signals.append(f"{lists} structured lists")

    headings = len(re.findall(r'<h[2-4][^>]*>', html, re.IGNORECASE))
    if headings >= 3:
        score += 10
        signals.append(f"{headings} sub-headings for content organization")

    has_dates = bool(re.search(r'(published|modified|updated|date)', html, re.IGNORECASE))
    if has_dates:
        score += 10
        signals.append("Date/freshness signals present")

    return {"score": min(100, round(score, 1)), "signals": signals}


def analyze_for_perplexity(html: str, url: str) -> dict:
    """Analyze content optimization for Perplexity citation."""
    score = 50.0
    signals = []

    numbers = len(re.findall(r'\d+[\d,.%]*', re.sub(r'<[^>]+>', '', html)))
    if numbers > 10:
        score += 15
        signals.append(f"High factual density ({numbers} data points)")
    elif numbers > 5:
        score += 8

    sources = len(re.findall(r'(source|reference|출처|참고)', html, re.IGNORECASE))
    if sources > 0:
        score += 10
        signals.append("Source attribution present")

    has_author = bool(re.search(r'(author|byline|작성자)', html, re.IGNORECASE))
    if has_author:
        score += 10
        signals.append("Author attribution found")

    meta_desc = re.search(r'name="description"\s+content="([^"]*)"', html, re.IGNORECASE)
    if meta_desc and len(meta_desc.group(1)) > 50:
        score += 10
        signals.append("Quality meta description for snippet")

    canonical = 'rel="canonical"' in html
    if canonical:
        score += 5
        signals.append("Canonical URL set")

    return {"score": min(100, round(score, 1)), "signals": signals}


def analyze_for_gemini(html: str, url: str) -> dict:
    """Analyze content optimization for Google Gemini/AI Overview."""
    score = 50.0
    signals = []

    has_schema = 'application/ld+json' in html
    if has_schema:
        score += 15
        signals.append("JSON-LD structured data (E-E-A-T signal)")

    has_author = bool(re.search(r'(author|expert|credential|Ph\.?D|박사|전문가)', html, re.IGNORECASE))
    if has_author:
        score += 10
        signals.append("Authority/expertise signals detected")

    tables = len(re.findall(r'<table[^>]*>', html, re.IGNORECASE))
    if tables > 0:
        score += 10
        signals.append(f"{tables} data tables (structured content)")

    faq_pattern = re.findall(r'<(details|summary|dt)[^>]*>', html, re.IGNORECASE)
    if faq_pattern:
        score += 5
        signals.append("FAQ-style content structure")

    word_count = len(re.sub(r'<[^>]+>', '', html).split())
    if word_count > 1000:
        score += 10
        signals.append(f"Comprehensive content ({word_count} words)")

    return {"score": min(100, round(score, 1)), "signals": signals}


def analyze_for_claude(html: str, url: str) -> dict:
    """Analyze content optimization for Claude citation."""
    score = 50.0
    signals = []

    text = re.sub(r'<[^>]+>', '', html)
    paragraphs = [p.strip() for p in text.split('\n\n') if len(p.strip()) > 100]
    if len(paragraphs) > 5:
        score += 15
        signals.append(f"Deep content depth ({len(paragraphs)} substantial paragraphs)")

    definitions = len(re.findall(r'<(dfn|abbr|dt|dd)[^>]*>', html, re.IGNORECASE))
    if definitions > 0:
        score += 5
        signals.append("Definition/terminology markup")

    has_accuracy = bool(re.search(r'(data|study|research|survey|연구|조사|통계)', html, re.IGNORECASE))
    if has_accuracy:
        score += 10
        signals.append("Research/data-backed content")

    headings = re.findall(r'<h[2-4][^>]*>(.*?)</h[2-4]>', html, re.IGNORECASE)
    if len(headings) >= 4:
        score += 10
        signals.append(f"Well-structured hierarchy ({len(headings)} sections)")

    code_blocks = len(re.findall(r'<(pre|code)[^>]*>', html, re.IGNORECASE))
    if code_blocks > 0:
        score += 10
        signals.append("Technical content with code examples")

    return {"score": min(100, round(score, 1)), "signals": signals}


PLATFORM_ANALYZERS = {
    "chatgpt": analyze_for_chatgpt,
    "perplexity": analyze_for_perplexity,
    "gemini": analyze_for_gemini,
    "claude": analyze_for_claude,
}


def analyze_platforms(url: str, platforms: Optional[list] = None) -> dict:
    """Analyze URL optimization for specific AI platforms."""
    validation = validate_url(url)
    if not validation["valid"]:
        return {"success": False, "error": validation["error"]}

    result = fetch_page(url)
    if not result["success"]:
        return {"success": False, "error": result["error"]}

    html = result["html"]
    target_platforms = platforms or list(PLATFORM_CONFIGS.keys())

    platform_results = {}
    for platform in target_platforms:
        if platform in PLATFORM_ANALYZERS:
            analysis = PLATFORM_ANALYZERS[platform](html, url)
            platform_results[platform] = {
                "name": PLATFORM_CONFIGS[platform]["name"],
                "score": analysis["score"],
                "signals": analysis["signals"],
            }

    scores = [pr["score"] for pr in platform_results.values()]
    avg_score = round(sum(scores) / max(len(scores), 1), 1)

    best = max(platform_results, key=lambda p: platform_results[p]["score"]) if platform_results else None
    worst = min(platform_results, key=lambda p: platform_results[p]["score"]) if platform_results else None

    issues = []
    for platform, pr in platform_results.items():
        if pr["score"] < 40:
            issues.append({"severity": "high", "message": f"Low optimization for {pr['name']}: {pr['score']}/100"})
        elif pr["score"] < 60:
            issues.append({"severity": "medium", "message": f"Moderate optimization for {pr['name']}: {pr['score']}/100"})

    return {
        "success": True,
        "url": url,
        "avg_score": avg_score,
        "best_platform": best,
        "worst_platform": worst,
        "platforms": platform_results,
        "issues": issues,
    }


def main():
    parser = argparse.ArgumentParser(description="Platform-specific AI optimization analysis")
    parser.add_argument("url", help="URL to analyze")
    parser.add_argument("--platform", choices=list(PLATFORM_CONFIGS.keys()), help="Analyze specific platform")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    platforms = [args.platform] if args.platform else None
    result = analyze_platforms(args.url, platforms)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result["success"]:
            print(f"Platform Optimization Score: {result['avg_score']}/100")
            print(f"\nPlatform Breakdown:")
            for platform, pr in result["platforms"].items():
                bar = "█" * int(pr["score"] / 10) + "░" * (10 - int(pr["score"] / 10))
                print(f"  {pr['name']:15s} {bar} {pr['score']:.0f}")
                for signal in pr["signals"]:
                    print(f"    + {signal}")
            for issue in result["issues"]:
                print(f"  [{issue['severity'].upper()}] {issue['message']}")
        else:
            print(f"Error: {result['error']}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()

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
    """Analyze content optimization for ChatGPT citation.
    ChatGPT prefers: clear definitions, structured data, concise paragraphs, freshness."""
    score = 30.0
    signals = []

    has_structured = 'application/ld+json' in html
    if has_structured:
        score += 12
        signals.append("JSON-LD structured data present")

    paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', html, re.DOTALL | re.IGNORECASE)
    clean_paras = [re.sub(r'<[^>]+>', '', p).strip() for p in paragraphs]

    short_clear = sum(1 for p in clean_paras if 80 < len(p) < 300)
    if short_clear >= 5:
        score += 12
        signals.append(f"{short_clear} concise, citable paragraphs (80-300 chars)")
    elif short_clear >= 3:
        score += 7

    definition_count = sum(1 for p in clean_paras
                          if re.search(r'(는|은|이란|란)\s+.{10,}(이다|입니다|합니다)', p)
                          or re.search(r'\b(is a|is the|refers to|means)\b', p, re.IGNORECASE))
    if definition_count >= 3:
        score += 15
        signals.append(f"{definition_count} definition-style sentences (high citation probability)")
    elif definition_count >= 1:
        score += 8
        signals.append(f"{definition_count} definition-style sentence found")

    lists = len(re.findall(r'<[ou]l[^>]*>', html, re.IGNORECASE))
    if lists >= 2:
        score += 8
        signals.append(f"{lists} structured lists")
    elif lists > 0:
        score += 4

    headings = len(re.findall(r'<h[2-4][^>]*>', html, re.IGNORECASE))
    if headings >= 5:
        score += 10
        signals.append(f"{headings} sub-headings (strong content hierarchy)")
    elif headings >= 3:
        score += 6

    has_dates = bool(re.search(r'(published|modified|updated|date|2024|2025|2026)', html, re.IGNORECASE))
    if has_dates:
        score += 8
        signals.append("Freshness signals present")

    has_faq = bool(re.search(r'(FAQ|자주\s*묻는|질문과\s*답)', html, re.IGNORECASE))
    if has_faq:
        score += 5
        signals.append("FAQ-style content (high Q&A citation potential)")

    return {"score": min(100, round(score, 1)), "signals": signals}


def analyze_for_perplexity(html: str, url: str) -> dict:
    """Analyze content optimization for Perplexity citation.
    Perplexity prefers: source-attributed facts, high data density, recency, citations."""
    score = 25.0
    signals = []

    text = re.sub(r'<[^>]+>', '', html)
    numbers = re.findall(r'\d+[\d,.%]*', text)
    if len(numbers) > 20:
        score += 18
        signals.append(f"Very high factual density ({len(numbers)} data points)")
    elif len(numbers) > 10:
        score += 12
        signals.append(f"Good factual density ({len(numbers)} data points)")
    elif len(numbers) > 5:
        score += 6

    sources = len(re.findall(r'(source|reference|citation|출처|참고|참조|인용)', html, re.IGNORECASE))
    if sources >= 3:
        score += 15
        signals.append(f"{sources} source attributions (Perplexity heavily favors sourced content)")
    elif sources > 0:
        score += 8
        signals.append("Source attribution present")

    has_author = bool(re.search(r'(author|byline|작성자|기자|편집)', html, re.IGNORECASE))
    if has_author:
        score += 10
        signals.append("Author attribution found")

    date_recent = bool(re.search(r'(2025|2026)', html))
    if date_recent:
        score += 12
        signals.append("Recent date signals (Perplexity prioritizes recency)")
    elif re.search(r'(2024)', html):
        score += 6

    meta_desc = re.search(r'name="description"\s+content="([^"]*)"', html, re.IGNORECASE)
    if meta_desc and len(meta_desc.group(1)) > 80:
        score += 8
        signals.append("Rich meta description for snippet extraction")
    elif meta_desc and len(meta_desc.group(1)) > 50:
        score += 4

    links_out = len(re.findall(r'<a[^>]+href="https?://(?!.*' + re.escape(url.split('/')[2]) + ')', html, re.IGNORECASE))
    if links_out >= 3:
        score += 7
        signals.append(f"{links_out} outbound references (cross-verification signal)")

    canonical = 'rel="canonical"' in html
    if canonical:
        score += 5
        signals.append("Canonical URL set")

    return {"score": min(100, round(score, 1)), "signals": signals}


def analyze_for_gemini(html: str, url: str) -> dict:
    """Analyze content optimization for Google Gemini/AI Overview.
    Gemini prefers: E-E-A-T, structured data, knowledge graph presence, comprehensive depth."""
    score = 25.0
    signals = []

    has_schema = 'application/ld+json' in html
    if has_schema:
        score += 14
        signals.append("JSON-LD structured data (E-E-A-T signal)")

    eeat_signals = 0
    if re.search(r'(author|written by|작성자|기자)', html, re.IGNORECASE):
        eeat_signals += 1
    if re.search(r'(expert|Ph\.?D|professor|박사|전문가|자격)', html, re.IGNORECASE):
        eeat_signals += 1
    if re.search(r'(years? of experience|경력|경험|실무)', html, re.IGNORECASE):
        eeat_signals += 1
    if re.search(r'(award|certified|인증|수상)', html, re.IGNORECASE):
        eeat_signals += 1
    if eeat_signals >= 3:
        score += 16
        signals.append(f"Strong E-E-A-T signals ({eeat_signals} indicators)")
    elif eeat_signals >= 1:
        score += eeat_signals * 5
        signals.append(f"E-E-A-T signals detected ({eeat_signals} indicators)")

    tables = len(re.findall(r'<table[^>]*>', html, re.IGNORECASE))
    if tables >= 2:
        score += 12
        signals.append(f"{tables} data tables (Gemini favors tabular data)")
    elif tables > 0:
        score += 6

    comparison = bool(re.search(r'(vs\.?|versus|비교|차이점|장단점|pros|cons)', html, re.IGNORECASE))
    if comparison:
        score += 8
        signals.append("Comparison content (high AI Overview selection rate)")

    word_count = len(re.sub(r'<[^>]+>', '', html).split())
    if word_count > 2000:
        score += 12
        signals.append(f"Comprehensive depth ({word_count} words)")
    elif word_count > 1000:
        score += 7

    same_as = len(re.findall(r'sameAs', html, re.IGNORECASE))
    if same_as > 0:
        score += 8
        signals.append("sameAs links (knowledge graph connectivity)")

    return {"score": min(100, round(score, 1)), "signals": signals}


def analyze_for_claude(html: str, url: str) -> dict:
    """Analyze content optimization for Claude citation.
    Claude prefers: depth, accuracy, nuance, structured format, data-backed claims."""
    score = 25.0
    signals = []

    text = re.sub(r'<[^>]+>', '', html)
    paragraphs = [p.strip() for p in text.split('\n\n') if len(p.strip()) > 100]
    if len(paragraphs) > 10:
        score += 15
        signals.append(f"Deep content depth ({len(paragraphs)} substantial paragraphs)")
    elif len(paragraphs) > 5:
        score += 9

    data_claims = len(re.findall(r'\d+[\d,.]*\s*(?:%|원|달러|명|건|억|만|배)', text))
    if data_claims >= 5:
        score += 14
        signals.append(f"{data_claims} data-backed claims (Claude prioritizes verifiable info)")
    elif data_claims >= 2:
        score += 7

    nuance_words = re.findall(r'(however|although|반면|그러나|다만|한편|nevertheless|on the other hand)', text, re.IGNORECASE)
    if len(nuance_words) >= 3:
        score += 10
        signals.append("Nuanced reasoning (multiple perspectives)")
    elif len(nuance_words) >= 1:
        score += 5

    headings = re.findall(r'<h[2-4][^>]*>(.*?)</h[2-4]>', html, re.IGNORECASE)
    if len(headings) >= 6:
        score += 12
        signals.append(f"Strong content hierarchy ({len(headings)} sections)")
    elif len(headings) >= 3:
        score += 6

    has_research = bool(re.search(r'(study|research|survey|paper|연구|조사|통계|논문)', html, re.IGNORECASE))
    if has_research:
        score += 10
        signals.append("Research/data-backed content")

    code_blocks = len(re.findall(r'<(pre|code)[^>]*>', html, re.IGNORECASE))
    if code_blocks > 0:
        score += 8
        signals.append("Technical content with code examples")

    definitions = len(re.findall(r'<(dfn|abbr|dt|dd)[^>]*>', html, re.IGNORECASE))
    if definitions > 0:
        score += 6
        signals.append("Definition/terminology markup")

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

"""Agent rendering analysis script for Three-O platform."""

import argparse
import json
import re
import sys

from validate_url import validate_url
from fetch_page import fetch_page


def check_ssr_content(html: str) -> dict:
    """Check if meaningful content is server-side rendered."""
    body_match = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL | re.IGNORECASE)
    body = body_match.group(1) if body_match else html

    no_script = re.sub(r'<script[^>]*>.*?</script>', '', body, flags=re.DOTALL | re.IGNORECASE)
    no_style = re.sub(r'<style[^>]*>.*?</style>', '', no_script, flags=re.DOTALL | re.IGNORECASE)
    text_only = re.sub(r'<[^>]+>', '', no_style).strip()
    word_count = len(text_only.split())

    headings = len(re.findall(r'<h[1-6][^>]*>.+?</h[1-6]>', html, re.IGNORECASE | re.DOTALL))
    paragraphs = len(re.findall(r'<p[^>]*>.{20,}</p>', html, re.IGNORECASE | re.DOTALL))
    links = len(re.findall(r'<a[^>]*href=', html, re.IGNORECASE))

    has_content = word_count > 100 and (headings > 0 or paragraphs > 2)

    return {
        "has_ssr_content": has_content,
        "word_count": word_count,
        "headings": headings,
        "paragraphs": paragraphs,
        "links": links,
        "score": min(100, word_count // 5 + headings * 5 + paragraphs * 3) if has_content else max(10, word_count // 10),
    }


def check_js_dependency(html: str) -> dict:
    """Analyze JavaScript dependency for content rendering."""
    external_scripts = len(re.findall(r'<script[^>]*src=', html, re.IGNORECASE))
    inline_scripts = len(re.findall(r'<script(?![^>]*src=)[^>]*>', html, re.IGNORECASE))
    total_scripts = external_scripts + inline_scripts

    frameworks = []
    if re.search(r'(__NEXT_DATA__|_next/)', html):
        frameworks.append("Next.js")
    if re.search(r'(__NUXT__|_nuxt/)', html):
        frameworks.append("Nuxt.js")
    if re.search(r'(ng-app|ng-controller|angular)', html, re.IGNORECASE):
        frameworks.append("Angular")
    if re.search(r'(data-reactroot|__REACT|react-app)', html, re.IGNORECASE):
        frameworks.append("React")
    if re.search(r'data-v-[a-f0-9]', html):
        frameworks.append("Vue.js")
    if re.search(r'(svelte|__svelte)', html, re.IGNORECASE):
        frameworks.append("Svelte")

    empty_root = bool(re.search(r'<div\s+id="(app|root|__next)">\s*</div>', html))
    heavy_js = total_scripts > 15

    dependency_level = "low"
    if empty_root:
        dependency_level = "critical"
    elif heavy_js and not frameworks:
        dependency_level = "high"
    elif frameworks:
        dependency_level = "moderate" if not empty_root else "critical"

    return {
        "external_scripts": external_scripts,
        "inline_scripts": inline_scripts,
        "total_scripts": total_scripts,
        "frameworks": frameworks,
        "empty_root": empty_root,
        "dependency_level": dependency_level,
    }


def check_semantic_html(html: str) -> dict:
    """Check semantic HTML structure for agent parsing."""
    score = 0
    signals = []

    semantic_tags = {
        "header": (r'<header[^>]*>', 10),
        "nav": (r'<nav[^>]*>', 10),
        "main": (r'<main[^>]*>', 15),
        "article": (r'<article[^>]*>', 10),
        "section": (r'<section[^>]*>', 5),
        "footer": (r'<footer[^>]*>', 5),
        "aside": (r'<aside[^>]*>', 5),
    }

    for tag, (pattern, points) in semantic_tags.items():
        if re.search(pattern, html, re.IGNORECASE):
            score += points
            signals.append(f"<{tag}> present")

    aria_count = len(re.findall(r'aria-\w+="', html))
    if aria_count > 5:
        score += 15
        signals.append(f"ARIA attributes ({aria_count})")
    elif aria_count > 0:
        score += 5

    roles = len(re.findall(r'role="(main|navigation|banner|contentinfo|search)"', html, re.IGNORECASE))
    if roles > 0:
        score += 10
        signals.append(f"Landmark roles ({roles})")

    lang_attr = bool(re.search(r'<html[^>]*lang="', html, re.IGNORECASE))
    if lang_attr:
        score += 5
        signals.append("Language attribute set")

    return {"score": min(100, score), "signals": signals}


def check_meta_accessibility(html: str) -> dict:
    """Check meta tag accessibility for agents."""
    score = 0
    signals = []

    if re.search(r'<title>[^<]+</title>', html, re.IGNORECASE):
        score += 15
        signals.append("Title tag present")
    if re.search(r'name="description"', html, re.IGNORECASE):
        score += 15
        signals.append("Meta description present")
    if re.search(r'rel="canonical"', html, re.IGNORECASE):
        score += 10
        signals.append("Canonical URL set")
    if re.search(r'property="og:', html, re.IGNORECASE):
        score += 10
        signals.append("Open Graph tags present")
    if re.search(r'charset="?utf-8"?', html, re.IGNORECASE):
        score += 10
        signals.append("UTF-8 encoding declared")
    if re.search(r'name="viewport"', html, re.IGNORECASE):
        score += 10
        signals.append("Viewport meta tag")

    has_schema = 'application/ld+json' in html
    if has_schema:
        score += 30
        signals.append("JSON-LD structured data")

    return {"score": min(100, score), "signals": signals}


def analyze_rendering(url: str) -> dict:
    """Full rendering analysis for AI agents."""
    validation = validate_url(url)
    if not validation["valid"]:
        return {"success": False, "error": validation["error"]}

    result = fetch_page(url)
    if not result["success"]:
        return {"success": False, "error": result["error"]}

    html = result["html"]
    ssr = check_ssr_content(html)
    js_dep = check_js_dependency(html)
    semantic = check_semantic_html(html)
    meta = check_meta_accessibility(html)

    overall = round(
        ssr["score"] * 0.35 +
        semantic["score"] * 0.25 +
        meta["score"] * 0.25 +
        (100 - min(100, js_dep["total_scripts"] * 5)) * 0.15,
        1
    )

    issues = []
    if not ssr["has_ssr_content"]:
        issues.append({"severity": "critical", "message": "Content requires JavaScript rendering — invisible to most AI agents"})
    if js_dep["empty_root"]:
        issues.append({"severity": "critical", "message": "Empty root div detected — SPA without SSR"})
    if js_dep["dependency_level"] == "critical":
        issues.append({"severity": "high", "message": f"Critical JS dependency ({', '.join(js_dep['frameworks'])})"})
    if semantic["score"] < 30:
        issues.append({"severity": "medium", "message": "Poor semantic HTML structure"})
    if meta["score"] < 50:
        issues.append({"severity": "medium", "message": "Incomplete meta accessibility signals"})

    return {
        "success": True,
        "url": url,
        "score": overall,
        "ssr": ssr,
        "js_dependency": js_dep,
        "semantic_html": semantic,
        "meta_accessibility": meta,
        "issues": issues,
    }


def main():
    parser = argparse.ArgumentParser(description="Agent rendering analysis")
    parser.add_argument("url", help="URL to analyze")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    result = analyze_rendering(args.url)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result["success"]:
            print(f"Rendering Score: {result['score']}/100")
            print(f"SSR: {'✓' if result['ssr']['has_ssr_content'] else '✗'} ({result['ssr']['word_count']} words)")
            print(f"JS Dependency: {result['js_dependency']['dependency_level']} ({result['js_dependency']['total_scripts']} scripts)")
            if result["js_dependency"]["frameworks"]:
                print(f"Frameworks: {', '.join(result['js_dependency']['frameworks'])}")
            print(f"Semantic HTML: {result['semantic_html']['score']}/100")
            print(f"Meta Access: {result['meta_accessibility']['score']}/100")
            for issue in result["issues"]:
                print(f"  [{issue['severity'].upper()}] {issue['message']}")
        else:
            print(f"Error: {result['error']}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()

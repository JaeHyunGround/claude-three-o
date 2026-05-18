"""Technical accessibility analysis for AI crawlers. Three-O platform."""

import argparse
import json
import re
import sys
from urllib.parse import urlparse

from validate_url import validate_url
from fetch_page import fetch_page


AI_CRAWLERS = {
    "GPTBot": {"provider": "OpenAI", "ua": "GPTBot"},
    "Anthropic-AI": {"provider": "Anthropic", "ua": "anthropic-ai"},
    "Google-Extended": {"provider": "Google", "ua": "Google-Extended"},
    "PerplexityBot": {"provider": "Perplexity", "ua": "PerplexityBot"},
    "Yeti": {"provider": "Naver", "ua": "Yeti"},
}


def check_robots_for_ai(url: str) -> dict:
    """Check robots.txt for AI crawler access."""
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    result = fetch_page(robots_url)
    if not result["success"] or result.get("status_code") != 200:
        return {"exists": False, "crawler_status": {c: "allowed (no robots.txt)" for c in AI_CRAWLERS}}

    content = result.get("html", "")
    crawler_status = {}

    for crawler, info in AI_CRAWLERS.items():
        blocked = False
        lines = content.split("\n")
        current_agent = None

        for line in lines:
            line = line.strip()
            if line.lower().startswith("user-agent:"):
                current_agent = line.split(":", 1)[1].strip()
            elif line.lower().startswith("disallow:") and current_agent:
                path = line.split(":", 1)[1].strip()
                if (current_agent.lower() == crawler.lower() or current_agent == "*") and path == "/":
                    if current_agent.lower() == crawler.lower():
                        blocked = True

        crawler_status[crawler] = {
            "status": "blocked" if blocked else "allowed",
            "provider": info["provider"],
        }

    return {"exists": True, "crawler_status": crawler_status}


def check_ssr_rendering(html: str) -> dict:
    """Check if content is server-side rendered (accessible to AI crawlers)."""
    body_match = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL | re.IGNORECASE)
    body_content = body_match.group(1) if body_match else html

    text_content = re.sub(r'<script[^>]*>.*?</script>', '', body_content, flags=re.DOTALL | re.IGNORECASE)
    text_content = re.sub(r'<style[^>]*>.*?</style>', '', text_content, flags=re.DOTALL | re.IGNORECASE)
    text_content = re.sub(r'<[^>]+>', '', text_content)
    text_content = text_content.strip()

    word_count = len(text_content.split())
    has_content = word_count > 50

    js_frameworks = []
    if re.search(r'__NEXT_DATA__|_next/', html):
        js_frameworks.append("Next.js")
    if re.search(r'__NUXT__|_nuxt/', html):
        js_frameworks.append("Nuxt.js")
    if re.search(r'ng-app|ng-controller', html):
        js_frameworks.append("Angular")
    if re.search(r'data-reactroot|__REACT', html):
        js_frameworks.append("React")
    if re.search(r'data-v-[a-f0-9]', html):
        js_frameworks.append("Vue.js")

    spa_indicators = [
        '<div id="app"></div>' in html,
        '<div id="root"></div>' in html,
        not has_content and len(js_frameworks) > 0,
    ]
    likely_spa = any(spa_indicators)

    return {
        "has_ssr_content": has_content,
        "word_count": word_count,
        "js_frameworks": js_frameworks,
        "likely_spa": likely_spa,
        "ssr_status": "good" if has_content else "poor" if likely_spa else "unknown",
    }


def check_response_performance(elapsed: float) -> dict:
    """Check response time for AI crawler accessibility."""
    ttfb_ms = round(elapsed * 1000)
    if ttfb_ms < 500:
        status = "fast"
    elif ttfb_ms < 1500:
        status = "acceptable"
    elif ttfb_ms < 3000:
        status = "slow"
    else:
        status = "very_slow"

    return {"ttfb_ms": ttfb_ms, "status": status}


def check_captcha_detection(html: str) -> dict:
    """Check for CAPTCHA or bot detection mechanisms."""
    captcha_signals = [
        re.search(r'recaptcha|hcaptcha|captcha', html, re.IGNORECASE),
        re.search(r'challenge-platform|cf-browser-verification', html, re.IGNORECASE),
        re.search(r'bot-detection|anti-bot', html, re.IGNORECASE),
    ]

    detected = [bool(s) for s in captcha_signals]
    has_captcha = any(detected)

    return {
        "has_captcha": has_captcha,
        "recaptcha": bool(captcha_signals[0]),
        "cloudflare_challenge": bool(captcha_signals[1]),
        "bot_detection": bool(captcha_signals[2]),
    }


def analyze_technical_accessibility(url: str) -> dict:
    """Full technical accessibility analysis for AI crawlers."""
    validation = validate_url(url)
    if not validation["valid"]:
        return {"success": False, "error": validation["error"]}

    robots_check = check_robots_for_ai(url)

    page_result = fetch_page(url)
    if not page_result["success"]:
        return {"success": False, "error": page_result["error"]}

    html = page_result["html"]
    ssr_check = check_ssr_rendering(html)
    perf_check = check_response_performance(page_result["elapsed_seconds"])
    captcha_check = check_captcha_detection(html)

    has_llms_txt = False
    parsed = urlparse(url)
    llms_result = fetch_page(f"{parsed.scheme}://{parsed.netloc}/llms.txt")
    if llms_result["success"] and llms_result.get("status_code") == 200:
        content = llms_result.get("html", "")
        if content.strip() and "<html" not in content.lower()[:100]:
            has_llms_txt = True

    score = 50.0
    issues = []

    blocked_crawlers = [c for c, info in robots_check.get("crawler_status", {}).items() if info.get("status") == "blocked"]
    if blocked_crawlers:
        score -= len(blocked_crawlers) * 8
        issues.append({"severity": "high", "message": f"AI crawlers blocked: {', '.join(blocked_crawlers)}"})
    else:
        score += 15

    if ssr_check["has_ssr_content"]:
        score += 15
    else:
        issues.append({"severity": "high", "message": "Content not available in HTML source (SPA without SSR)"})

    if perf_check["status"] in ["fast", "acceptable"]:
        score += 5
    elif perf_check["status"] == "very_slow":
        score -= 10
        issues.append({"severity": "medium", "message": f"Very slow response: {perf_check['ttfb_ms']}ms"})

    if captcha_check["has_captcha"]:
        score -= 15
        issues.append({"severity": "high", "message": "CAPTCHA/bot detection may block AI crawlers"})

    if has_llms_txt:
        score += 15
    else:
        issues.append({"severity": "medium", "message": "No llms.txt — AI crawlers lack content guide"})

    score = max(0, min(100, round(score, 1)))

    return {
        "success": True,
        "url": url,
        "score": score,
        "robots": robots_check,
        "ssr": ssr_check,
        "performance": perf_check,
        "captcha": captcha_check,
        "has_llms_txt": has_llms_txt,
        "issues": issues,
    }


def main():
    parser = argparse.ArgumentParser(description="Technical accessibility analysis for AI crawlers")
    parser.add_argument("url", help="URL to analyze")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    result = analyze_technical_accessibility(args.url)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result["success"]:
            print(f"Technical Accessibility Score: {result['score']}/100")
            print("\nAI Crawler Access:")
            for crawler, info in result["robots"].get("crawler_status", {}).items():
                icon = "✓" if info.get("status") == "allowed" else "✗"
                print(f"  {icon} {crawler} ({info.get('provider', '')}): {info.get('status', '')}")
            print(f"\nSSR: {'✓' if result['ssr']['has_ssr_content'] else '✗'} | TTFB: {result['performance']['ttfb_ms']}ms | llms.txt: {'✓' if result['has_llms_txt'] else '✗'}")
            for issue in result["issues"]:
                print(f"  [{issue['severity'].upper()}] {issue['message']}")
        else:
            print(f"Error: {result['error']}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()

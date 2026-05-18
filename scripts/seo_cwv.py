"""Core Web Vitals analysis script for Three-O platform. Uses INP (never FID)."""

import argparse
import json
import re
import sys

from validate_url import validate_url
from fetch_page import fetch_page

CWV_THRESHOLDS = {
    "LCP": {"good": 2500, "needs_improvement": 4000},
    "INP": {"good": 200, "needs_improvement": 500},
    "CLS": {"good": 0.1, "needs_improvement": 0.25},
}


def estimate_performance_from_html(html: str, elapsed: float) -> dict:
    """Estimate performance signals from HTML structure and response time."""
    resource_count = len(re.findall(r'<(script|link|img)[^>]*src', html, re.IGNORECASE))
    inline_styles = len(re.findall(r'<style[^>]*>', html, re.IGNORECASE))
    external_scripts = len(re.findall(r'<script[^>]*src=', html, re.IGNORECASE))
    inline_scripts = len(re.findall(r'<script(?![^>]*src=)[^>]*>', html, re.IGNORECASE))
    images = len(re.findall(r'<img[^>]*>', html, re.IGNORECASE))
    lazy_images = len(re.findall(r'loading="lazy"', html, re.IGNORECASE))

    has_preconnect = 'rel="preconnect"' in html
    has_preload = 'rel="preload"' in html
    has_async_scripts = 'async' in html or 'defer' in html

    estimated_lcp = elapsed * 1000 + (external_scripts * 100) + (images * 50)
    estimated_cls_risk = "low" if inline_styles == 0 and images == lazy_images else "medium" if images > lazy_images else "high"

    return {
        "ttfb_ms": round(elapsed * 1000),
        "estimated_lcp_ms": round(estimated_lcp),
        "cls_risk": estimated_cls_risk,
        "resource_count": resource_count,
        "external_scripts": external_scripts,
        "inline_scripts": inline_scripts,
        "images": images,
        "lazy_loaded_images": lazy_images,
        "has_preconnect": has_preconnect,
        "has_preload": has_preload,
        "has_async_defer": has_async_scripts,
    }


def classify_metric(metric: str, value: float) -> str:
    """Classify CWV metric as good/needs-improvement/poor."""
    thresholds = CWV_THRESHOLDS.get(metric)
    if not thresholds:
        return "unknown"
    if value <= thresholds["good"]:
        return "good"
    elif value <= thresholds["needs_improvement"]:
        return "needs_improvement"
    return "poor"


def analyze_cwv(url: str) -> dict:
    """Analyze Core Web Vitals indicators."""
    validation = validate_url(url)
    if not validation["valid"]:
        return {"success": False, "error": validation["error"]}

    result = fetch_page(url)
    if not result["success"]:
        return {"success": False, "error": result["error"]}

    perf = estimate_performance_from_html(result["html"], result["elapsed_seconds"])

    lcp_status = classify_metric("LCP", perf["estimated_lcp_ms"])

    issues = []
    if perf["ttfb_ms"] > 800:
        issues.append({"severity": "high", "message": f"Slow TTFB: {perf['ttfb_ms']}ms (target: <800ms)"})
    if perf["estimated_lcp_ms"] > CWV_THRESHOLDS["LCP"]["good"]:
        issues.append({"severity": "high", "message": f"LCP estimated at {perf['estimated_lcp_ms']}ms (target: <2500ms)"})
    if perf["external_scripts"] > 10:
        issues.append({"severity": "medium", "message": f"Too many external scripts: {perf['external_scripts']}"})
    if not perf["has_async_defer"] and perf["external_scripts"] > 3:
        issues.append({"severity": "medium", "message": "Scripts missing async/defer attributes"})
    if perf["images"] > 0 and perf["lazy_loaded_images"] == 0:
        issues.append({"severity": "medium", "message": "No images use lazy loading"})
    if perf["cls_risk"] == "high":
        issues.append({"severity": "medium", "message": "High CLS risk (images without dimensions/lazy)"})
    if not perf["has_preconnect"]:
        issues.append({"severity": "low", "message": "No preconnect hints for third-party origins"})

    score = 100 - sum(15 if i["severity"] == "high" else 8 if i["severity"] == "medium" else 3 for i in issues)
    score = max(0, min(100, score))

    return {
        "success": True,
        "url": url,
        "score": score,
        "performance": perf,
        "cwv_estimates": {
            "LCP": {"value_ms": perf["estimated_lcp_ms"], "status": lcp_status},
            "INP": {"value_ms": None, "status": "requires_field_data", "note": "INP requires real user data (CrUX)"},
            "CLS": {"risk": perf["cls_risk"], "note": "Estimated from HTML structure"},
        },
        "issues": issues,
    }


def main():
    parser = argparse.ArgumentParser(description="Core Web Vitals analysis (INP, not FID)")
    parser.add_argument("url", help="URL to analyze")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    result = analyze_cwv(args.url)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result["success"]:
            print(f"CWV Score: {result['score']}/100")
            print(f"TTFB: {result['performance']['ttfb_ms']}ms")
            print(f"LCP (est.): {result['cwv_estimates']['LCP']['value_ms']}ms [{result['cwv_estimates']['LCP']['status']}]")
            print("INP: Requires field data (CrUX API)")
            print(f"CLS risk: {result['cwv_estimates']['CLS']['risk']}")
            for issue in result["issues"]:
                print(f"  [{issue['severity'].upper()}] {issue['message']}")
        else:
            print(f"Error: {result['error']}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()

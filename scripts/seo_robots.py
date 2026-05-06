"""robots.txt analysis script for Three-O platform."""

import argparse
import json
import re
import sys
from urllib.parse import urlparse

from validate_url import validate_url
from fetch_page import fetch_page

AI_BOTS = {
    "GPTBot": "OpenAI (ChatGPT)",
    "Anthropic-AI": "Anthropic (Claude)",
    "Google-Extended": "Google (Gemini AI training)",
    "PerplexityBot": "Perplexity",
    "Yeti": "Naver",
    "Googlebot": "Google Search",
    "Bingbot": "Bing Search",
}


def parse_robots_txt(content: str) -> list:
    """Parse robots.txt into structured rules."""
    rules = []
    current_agent = None

    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("#") or not line:
            continue

        if line.lower().startswith("user-agent:"):
            current_agent = line.split(":", 1)[1].strip()
        elif line.lower().startswith("disallow:") and current_agent:
            path = line.split(":", 1)[1].strip()
            rules.append({"agent": current_agent, "directive": "disallow", "path": path})
        elif line.lower().startswith("allow:") and current_agent:
            path = line.split(":", 1)[1].strip()
            rules.append({"agent": current_agent, "directive": "allow", "path": path})
        elif line.lower().startswith("sitemap:"):
            rules.append({"agent": None, "directive": "sitemap", "path": line.split(":", 1)[1].strip()})

    return rules


def check_bot_access(rules: list, bot_name: str) -> str:
    """Determine if a specific bot is blocked."""
    bot_rules = [r for r in rules if r["agent"] and (r["agent"].lower() == bot_name.lower() or r["agent"] == "*")]
    specific_rules = [r for r in rules if r["agent"] and r["agent"].lower() == bot_name.lower()]

    if specific_rules:
        for rule in specific_rules:
            if rule["directive"] == "disallow" and rule["path"] == "/":
                return "blocked"
            if rule["directive"] == "disallow" and rule["path"]:
                return "partial"
        return "allowed"

    wildcard_rules = [r for r in rules if r["agent"] == "*"]
    for rule in wildcard_rules:
        if rule["directive"] == "disallow" and rule["path"] == "/":
            return "blocked"
    return "allowed"


def analyze_robots(url: str) -> dict:
    """Analyze robots.txt for the given URL."""
    validation = validate_url(url)
    if not validation["valid"]:
        return {"success": False, "error": validation["error"]}

    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    result = fetch_page(robots_url)
    if not result["success"] or result.get("status_code") != 200:
        return {
            "success": True,
            "url": robots_url,
            "exists": False,
            "score": 50,
            "issues": [{"severity": "medium", "message": "No robots.txt found"}],
            "bot_access": {bot: "allowed (no robots.txt)" for bot in AI_BOTS},
        }

    content = result["html"]
    rules = parse_robots_txt(content)
    sitemaps = [r["path"] for r in rules if r["directive"] == "sitemap"]

    bot_access = {}
    for bot_name, description in AI_BOTS.items():
        status = check_bot_access(rules, bot_name)
        bot_access[bot_name] = {"status": status, "description": description}

    issues = []
    blocked_ai = [b for b, info in bot_access.items() if info["status"] == "blocked" and b in ["GPTBot", "Anthropic-AI", "Google-Extended", "PerplexityBot"]]
    if blocked_ai:
        issues.append({"severity": "warning", "message": f"AI bots blocked: {', '.join(blocked_ai)}"})
    if not sitemaps:
        issues.append({"severity": "low", "message": "No Sitemap directive in robots.txt"})
    if bot_access.get("Googlebot", {}).get("status") == "blocked":
        issues.append({"severity": "critical", "message": "Googlebot is blocked!"})

    score = 100 - len(blocked_ai) * 10 - (25 if bot_access.get("Googlebot", {}).get("status") == "blocked" else 0)
    score = max(0, min(100, score))

    return {
        "success": True,
        "url": robots_url,
        "exists": True,
        "score": score,
        "rules_count": len(rules),
        "sitemaps": sitemaps,
        "bot_access": bot_access,
        "issues": issues,
    }


def main():
    parser = argparse.ArgumentParser(description="robots.txt analysis")
    parser.add_argument("url", help="Site URL to check robots.txt")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    result = analyze_robots(args.url)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result["exists"]:
            print(f"robots.txt Score: {result['score']}/100")
            print(f"Rules: {result['rules_count']} | Sitemaps: {len(result['sitemaps'])}")
            print("\nBot Access:")
            for bot, info in result["bot_access"].items():
                status_icon = "✓" if info["status"] == "allowed" else "✗" if info["status"] == "blocked" else "~"
                print(f"  {status_icon} {bot} ({info['description']}): {info['status']}")
        else:
            print("✗ No robots.txt found")
        for issue in result.get("issues", []):
            print(f"  [{issue['severity'].upper()}] {issue['message']}")


if __name__ == "__main__":
    main()

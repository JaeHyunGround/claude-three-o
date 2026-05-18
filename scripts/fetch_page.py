"""Web page fetcher with SSR comparison for Three-O platform."""

import argparse
import json
import sys
import time

import httpx

from validate_url import validate_url


DEFAULT_TIMEOUT = 15
USER_AGENTS = {
    "default": "Three-O/1.0 (SEO+GEO+AAO Audit Bot)",
    "googlebot": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "gptbot": "Mozilla/5.0 AppleWebKit/537.36 (compatible; GPTBot/1.0; +https://openai.com/gptbot)",
    "anthropic": "Mozilla/5.0 (compatible; Anthropic-AI/1.0)",
    "perplexity": "Mozilla/5.0 (compatible; PerplexityBot/1.0)",
}


def fetch_page(url: str, user_agent: str = "default", timeout: int = DEFAULT_TIMEOUT) -> dict:
    """Fetch a page and return status, headers, and content."""
    validation = validate_url(url)
    if not validation["valid"]:
        return {"success": False, "error": validation["error"]}

    ua = USER_AGENTS.get(user_agent, user_agent)
    headers = {"User-Agent": ua, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}

    try:
        start = time.time()
        with httpx.Client(follow_redirects=True, timeout=timeout) as client:
            response = client.get(url, headers=headers)
        elapsed = time.time() - start

        return {
            "success": True,
            "url": str(response.url),
            "status_code": response.status_code,
            "content_type": response.headers.get("content-type", ""),
            "content_length": len(response.text),
            "elapsed_seconds": round(elapsed, 3),
            "headers": dict(response.headers),
            "html": response.text,
            "redirects": [str(r.url) for r in response.history],
        }
    except httpx.TimeoutException:
        return {"success": False, "error": f"Timeout after {timeout}s"}
    except httpx.RequestError as e:
        return {"success": False, "error": str(e)}


def fetch_with_bot_comparison(url: str) -> dict:
    """Fetch page with multiple bot user-agents to detect blocking."""
    results = {}
    for bot_name in ["default", "googlebot", "gptbot", "anthropic", "perplexity"]:
        result = fetch_page(url, user_agent=bot_name)
        results[bot_name] = {
            "status": result.get("status_code"),
            "blocked": result.get("status_code", 0) in (403, 429, 503),
            "content_length": result.get("content_length", 0),
        }
    return results


def main():
    parser = argparse.ArgumentParser(description="Fetch web page for Three-O analysis")
    parser.add_argument("url", help="URL to fetch")
    parser.add_argument("--ua", default="default", choices=list(USER_AGENTS.keys()), help="User-Agent to use")
    parser.add_argument("--bot-check", action="store_true", help="Test multiple bot user-agents")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Timeout in seconds")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--no-body", action="store_true", help="Exclude HTML body from output")
    args = parser.parse_args()

    if args.bot_check:
        results = fetch_with_bot_comparison(args.url)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for bot, data in results.items():
                status = "BLOCKED" if data["blocked"] else "OK"
                print(f"  {bot}: {data['status']} ({status}) — {data['content_length']} bytes")
        return

    result = fetch_page(args.url, user_agent=args.ua, timeout=args.timeout)

    if args.no_body and "html" in result:
        del result["html"]

    if args.json:
        if "html" in result and len(result["html"]) > 10000:
            result["html"] = result["html"][:10000] + "... [truncated]"
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result["success"]:
            print(f"✓ {result['status_code']} — {result['content_length']} bytes in {result['elapsed_seconds']}s")
        else:
            print(f"✗ Error: {result['error']}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()

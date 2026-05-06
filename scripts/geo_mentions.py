"""AI brand mention tracking script for Three-O platform."""

import argparse
import json
import sys
from typing import Optional

from config import load_config, get_api_key


AI_PLATFORMS = {
    "chatgpt": {"name": "ChatGPT", "provider": "OpenAI"},
    "perplexity": {"name": "Perplexity", "provider": "Perplexity AI"},
    "gemini": {"name": "Gemini", "provider": "Google"},
    "claude": {"name": "Claude", "provider": "Anthropic"},
}

QUERY_TEMPLATES = {
    "recommendation": "best {category} in {location}",
    "comparison": "{brand} vs {competitor}",
    "review": "{brand} review",
    "purchase": "buy {product} from {brand}",
    "general": "{category} recommendations {location}",
}


def generate_queries(brand: str, industry: Optional[str] = None, location: Optional[str] = None) -> list:
    """Generate probe queries based on brand and industry."""
    queries = []
    category = industry or "service"
    loc = location or "Korea"

    queries.append(f"best {category} in {loc}")
    queries.append(f"{brand} review")
    queries.append(f"{category} recommendations")
    queries.append(f"top {category} companies")
    queries.append(f"{brand} vs competitors")
    queries.append(f"is {brand} good")
    queries.append(f"{category} comparison {loc}")
    queries.append(f"recommended {category} providers")
    queries.append(f"{brand} pros and cons")
    queries.append(f"best {category} services 2024")

    return queries


def analyze_mention(response_text: str, brand: str) -> dict:
    """Analyze a single AI response for brand mentions."""
    brand_lower = brand.lower()
    text_lower = response_text.lower()

    mentioned = brand_lower in text_lower
    if not mentioned:
        return {
            "mentioned": False,
            "position": None,
            "context": None,
            "recommended": False,
        }

    position = text_lower.index(brand_lower)
    total_length = len(text_lower)
    relative_position = round(position / max(total_length, 1), 2)

    if relative_position < 0.2:
        position_label = "first"
    elif relative_position < 0.5:
        position_label = "early"
    else:
        position_label = "late"

    start = max(0, position - 100)
    end = min(len(response_text), position + len(brand) + 100)
    context = response_text[start:end].strip()

    recommend_keywords = ["recommend", "best", "top", "leading", "excellent", "추천", "최고"]
    recommended = any(kw in text_lower[max(0, position - 50):position + len(brand) + 50] for kw in recommend_keywords)

    return {
        "mentioned": True,
        "position": position_label,
        "relative_position": relative_position,
        "context": context,
        "recommended": recommended,
    }


def probe_platform(platform: str, queries: list, brand: str, config: dict) -> dict:
    """Probe a single AI platform with queries (requires API keys)."""
    results = []
    mentioned_count = 0

    api_key = get_api_key(config, platform)
    if not api_key:
        return {
            "platform": platform,
            "status": "no_api_key",
            "message": f"No API key configured for {AI_PLATFORMS[platform]['name']}",
            "results": [],
        }

    for query in queries:
        results.append({
            "query": query,
            "status": "requires_api_call",
            "note": f"Configure {platform} API key to probe",
        })

    return {
        "platform": platform,
        "platform_name": AI_PLATFORMS[platform]["name"],
        "status": "configured" if api_key else "no_api_key",
        "queries_count": len(queries),
        "results": results,
    }


def calculate_mention_frequency(platform_results: list) -> float:
    """Calculate overall mention frequency score (0-100)."""
    if not platform_results:
        return 0.0

    total_queries = 0
    total_mentions = 0

    for pr in platform_results:
        for r in pr.get("results", []):
            if r.get("status") == "probed":
                total_queries += 1
                if r.get("mentioned"):
                    total_mentions += 1

    if total_queries == 0:
        return 0.0
    return round((total_mentions / total_queries) * 100, 1)


def run_mention_tracking(brand: str, industry: Optional[str] = None,
                         location: Optional[str] = None,
                         queries_file: Optional[str] = None) -> dict:
    """Run brand mention tracking across AI platforms."""
    config = load_config()

    if queries_file:
        from pathlib import Path
        queries = [q.strip() for q in Path(queries_file).read_text().splitlines() if q.strip()]
    else:
        queries = generate_queries(brand, industry, location)

    platform_results = []
    for platform in AI_PLATFORMS:
        result = probe_platform(platform, queries, brand, config)
        platform_results.append(result)

    configured_platforms = [p for p in platform_results if p["status"] == "configured"]
    unconfigured_platforms = [p for p in platform_results if p["status"] == "no_api_key"]

    mf_score = calculate_mention_frequency(platform_results)

    return {
        "success": True,
        "brand": brand,
        "industry": industry,
        "location": location,
        "queries_used": len(queries),
        "platforms": {
            "total": len(AI_PLATFORMS),
            "configured": len(configured_platforms),
            "unconfigured": len(unconfigured_platforms),
        },
        "mention_frequency_score": mf_score,
        "platform_results": platform_results,
        "queries": queries,
    }


def main():
    parser = argparse.ArgumentParser(description="AI brand mention tracking")
    parser.add_argument("brand", help="Brand name to track")
    parser.add_argument("--industry", help="Industry/category")
    parser.add_argument("--location", help="Target location")
    parser.add_argument("--queries", help="Path to queries file")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    result = run_mention_tracking(args.brand, args.industry, args.location, args.queries)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"Brand Mention Tracking: {args.brand}")
        print(f"Queries: {result['queries_used']} | Platforms: {result['platforms']['configured']}/{result['platforms']['total']} configured")
        print(f"Mention Frequency Score: {result['mention_frequency_score']}/100")
        print("\nPlatform Status:")
        for pr in result["platform_results"]:
            icon = "✓" if pr["status"] == "configured" else "✗"
            print(f"  {icon} {pr['platform_name']}: {pr['status']}")
        if result["platforms"]["unconfigured"] > 0:
            print(f"\n  Configure API keys via: three-o setup")


if __name__ == "__main__":
    main()

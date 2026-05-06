"""Visibility ranking analysis script for Three-O platform."""

import argparse
import json
import sys
from typing import Optional

from config import load_config, get_api_key


AI_PLATFORMS = ["chatgpt", "perplexity", "gemini", "claude"]

POSITION_SCORES = {
    "first": 100,
    "second": 80,
    "third": 60,
    "mentioned": 40,
    "not_mentioned": 0,
}


def classify_position(text: str, brand: str) -> str:
    """Classify brand mention position in AI response."""
    brand_lower = brand.lower()
    text_lower = text.lower()

    if brand_lower not in text_lower:
        return "not_mentioned"

    pos = text_lower.index(brand_lower)
    total = len(text_lower)
    ratio = pos / max(total, 1)

    lines = text_lower[:pos].count("\n")
    numbered = False
    for i, line in enumerate(text_lower.split("\n")):
        if brand_lower in line:
            numbered = i
            break

    if ratio < 0.15 or lines < 2:
        return "first"
    elif ratio < 0.30 or lines < 5:
        return "second"
    elif ratio < 0.50:
        return "third"
    return "mentioned"


def calculate_visibility_score(position_data: list) -> dict:
    """Calculate overall visibility ranking score from position data."""
    if not position_data:
        return {"score": 0.0, "avg_position": "not_mentioned", "platform_breakdown": {}}

    platform_scores = {}
    for entry in position_data:
        platform = entry.get("platform", "unknown")
        position = entry.get("position", "not_mentioned")
        score = POSITION_SCORES.get(position, 0)

        if platform not in platform_scores:
            platform_scores[platform] = []
        platform_scores[platform].append(score)

    platform_avg = {}
    for platform, scores in platform_scores.items():
        platform_avg[platform] = round(sum(scores) / len(scores), 1)

    overall = round(sum(platform_avg.values()) / max(len(platform_avg), 1), 1)

    best_platform = max(platform_avg, key=platform_avg.get) if platform_avg else None
    worst_platform = min(platform_avg, key=platform_avg.get) if platform_avg else None

    return {
        "score": overall,
        "platform_scores": platform_avg,
        "best_platform": best_platform,
        "worst_platform": worst_platform,
        "total_queries": len(position_data),
    }


def analyze_visibility_from_mentions(brand: str, mention_data: list) -> dict:
    """Analyze visibility ranking from collected mention data."""
    position_data = []

    for mention in mention_data:
        text = mention.get("text", "")
        platform = mention.get("platform", "unknown")
        query = mention.get("query", "")

        position = classify_position(text, brand)
        position_data.append({
            "platform": platform,
            "query": query,
            "position": position,
            "score": POSITION_SCORES.get(position, 0),
        })

    vr = calculate_visibility_score(position_data)

    position_distribution = {"first": 0, "second": 0, "third": 0, "mentioned": 0, "not_mentioned": 0}
    for entry in position_data:
        pos = entry["position"]
        if pos in position_distribution:
            position_distribution[pos] += 1

    issues = []
    if vr["score"] < 30:
        issues.append({"severity": "high", "message": "Very low visibility — brand rarely appears in top positions"})
    elif vr["score"] < 50:
        issues.append({"severity": "medium", "message": "Moderate visibility — brand appears but not in leading positions"})

    if position_distribution["not_mentioned"] > len(position_data) * 0.5:
        issues.append({"severity": "high", "message": f"Brand not mentioned in {position_distribution['not_mentioned']}/{len(position_data)} queries"})

    if vr.get("worst_platform") and vr["platform_scores"].get(vr["worst_platform"], 0) < 20:
        issues.append({"severity": "medium", "message": f"Very low visibility on {vr['worst_platform']}"})

    return {
        "success": True,
        "brand": brand,
        "score": vr["score"],
        "platform_scores": vr.get("platform_scores", {}),
        "best_platform": vr.get("best_platform"),
        "worst_platform": vr.get("worst_platform"),
        "position_distribution": position_distribution,
        "total_queries": len(position_data),
        "details": position_data[:30],
        "issues": issues,
    }


def main():
    parser = argparse.ArgumentParser(description="AI visibility ranking analysis")
    parser.add_argument("brand", help="Brand name")
    parser.add_argument("--input", help="JSON file with mention data")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    if args.input:
        from pathlib import Path
        mentions = json.loads(Path(args.input).read_text())
    else:
        mentions = []

    result = analyze_visibility_from_mentions(args.brand, mentions)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"Visibility Ranking: {args.brand}")
        print(f"VR Score: {result['score']}/100")
        if result["platform_scores"]:
            print(f"\nPlatform Scores:")
            for p, s in result["platform_scores"].items():
                bar = "█" * int(s / 10) + "░" * (10 - int(s / 10))
                print(f"  {p:15s} {bar} {s:.1f}")
        dist = result["position_distribution"]
        print(f"\nPositions: 1st={dist['first']} 2nd={dist['second']} 3rd={dist['third']} mention={dist['mentioned']} none={dist['not_mentioned']}")
        for issue in result["issues"]:
            print(f"  [{issue['severity'].upper()}] {issue['message']}")


if __name__ == "__main__":
    main()

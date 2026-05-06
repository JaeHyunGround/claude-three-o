"""Context quality analysis script for Three-O platform."""

import argparse
import json
import re
import sys
from typing import Optional


CONTEXT_SIGNALS = {
    "positive": ["recommend", "best", "top", "leading", "excellent", "trusted",
                 "reliable", "innovative", "popular", "preferred",
                 "추천", "최고", "우수", "신뢰", "혁신"],
    "negative": ["avoid", "worst", "poor", "unreliable", "expensive", "outdated",
                 "complaint", "issue", "problem", "scam",
                 "피하", "최악", "불만", "문제", "사기"],
    "neutral": ["offers", "provides", "located", "founded", "available",
                "operates", "established", "known for",
                "제공", "위치", "설립", "운영"],
}

ACCURACY_INDICATORS = {
    "factual": ["founded in", "located at", "employees", "revenue", "since",
                "headquarters", "CEO", "established"],
    "opinion": ["I think", "arguably", "some say", "might be", "could be",
                "perhaps", "reportedly"],
    "outdated": ["was", "used to", "formerly", "previously", "no longer"],
}


def analyze_context_quality(text: str, brand: str) -> dict:
    """Analyze the quality of context surrounding a brand mention."""
    text_lower = text.lower()
    brand_lower = brand.lower()

    if brand_lower not in text_lower:
        return {"has_mention": False, "score": 0}

    pos = text_lower.index(brand_lower)
    window_start = max(0, pos - 200)
    window_end = min(len(text), pos + len(brand) + 200)
    context_window = text[window_start:window_end]
    context_lower = context_window.lower()

    sentiment_scores = {"positive": 0, "negative": 0, "neutral": 0}
    for sentiment, keywords in CONTEXT_SIGNALS.items():
        for kw in keywords:
            if kw in context_lower:
                sentiment_scores[sentiment] += 1

    if sentiment_scores["positive"] > sentiment_scores["negative"]:
        sentiment = "positive"
    elif sentiment_scores["negative"] > sentiment_scores["positive"]:
        sentiment = "negative"
    else:
        sentiment = "neutral"

    factual_count = sum(1 for ind in ACCURACY_INDICATORS["factual"] if ind.lower() in context_lower)
    opinion_count = sum(1 for ind in ACCURACY_INDICATORS["opinion"] if ind.lower() in context_lower)
    outdated_count = sum(1 for ind in ACCURACY_INDICATORS["outdated"] if ind.lower() in context_lower)

    if factual_count > opinion_count:
        accuracy_type = "factual"
    elif opinion_count > 0:
        accuracy_type = "opinion-based"
    else:
        accuracy_type = "descriptive"

    detail_score = min(100, len(context_window.split()) * 2)
    sentiment_score = 80 if sentiment == "positive" else 50 if sentiment == "neutral" else 20
    accuracy_score = 90 if accuracy_type == "factual" else 60 if accuracy_type == "descriptive" else 40
    freshness_score = 100 - (outdated_count * 30)

    cq_score = round(
        detail_score * 0.25 +
        sentiment_score * 0.30 +
        accuracy_score * 0.25 +
        max(0, freshness_score) * 0.20,
        1
    )

    return {
        "has_mention": True,
        "score": cq_score,
        "sentiment": sentiment,
        "sentiment_scores": sentiment_scores,
        "accuracy_type": accuracy_type,
        "factual_indicators": factual_count,
        "opinion_indicators": opinion_count,
        "outdated_indicators": outdated_count,
        "context_length_words": len(context_window.split()),
        "context_excerpt": context_window[:200],
        "breakdown": {
            "detail": detail_score,
            "sentiment": sentiment_score,
            "accuracy": accuracy_score,
            "freshness": max(0, freshness_score),
        },
    }


def analyze_multiple_contexts(mentions: list, brand: str) -> dict:
    """Analyze context quality across multiple mentions."""
    if not mentions:
        return {"success": True, "brand": brand, "total_mentions": 0, "avg_score": 0}

    analyses = []
    for mention in mentions:
        analysis = analyze_context_quality(mention.get("text", ""), brand)
        if analysis["has_mention"]:
            analysis["platform"] = mention.get("platform", "unknown")
            analysis["query"] = mention.get("query", "")
            analyses.append(analysis)

    if not analyses:
        return {"success": True, "brand": brand, "total_mentions": 0, "avg_score": 0}

    avg_score = round(sum(a["score"] for a in analyses) / len(analyses), 1)
    sentiments = {"positive": 0, "negative": 0, "neutral": 0}
    for a in analyses:
        sentiments[a["sentiment"]] += 1

    dominant_sentiment = max(sentiments, key=sentiments.get)

    return {
        "success": True,
        "brand": brand,
        "total_mentions": len(analyses),
        "avg_score": avg_score,
        "dominant_sentiment": dominant_sentiment,
        "sentiment_distribution": sentiments,
        "analyses": analyses,
    }


def main():
    parser = argparse.ArgumentParser(description="Context quality analysis for AI brand mentions")
    parser.add_argument("brand", help="Brand name")
    parser.add_argument("--text", help="Text to analyze (single mention)")
    parser.add_argument("--input", help="JSON file with multiple mentions")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    if args.input:
        from pathlib import Path
        mentions = json.loads(Path(args.input).read_text())
        result = analyze_multiple_contexts(mentions, args.brand)
    elif args.text:
        result = analyze_context_quality(args.text, args.brand)
        result["success"] = True
        result["brand"] = args.brand
    else:
        print("Error: Provide --text or --input", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if "avg_score" in result:
            print(f"Context Quality: {args.brand}")
            print(f"Mentions Analyzed: {result['total_mentions']}")
            print(f"Average CQ Score: {result['avg_score']}/100")
            print(f"Dominant Sentiment: {result.get('dominant_sentiment', 'N/A')}")
        else:
            print(f"Context Quality: {args.brand}")
            print(f"Score: {result.get('score', 0)}/100")
            print(f"Sentiment: {result.get('sentiment', 'N/A')}")
            print(f"Accuracy: {result.get('accuracy_type', 'N/A')}")


if __name__ == "__main__":
    main()

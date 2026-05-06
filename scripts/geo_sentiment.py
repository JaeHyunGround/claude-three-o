"""Sentiment analysis script for AI-generated brand mentions. Three-O platform."""

import argparse
import json
import re
import sys
from typing import Optional


SENTIMENT_LEXICON_EN = {
    "positive": {
        "excellent": 0.9, "outstanding": 0.9, "recommend": 0.8, "best": 0.8,
        "top": 0.7, "leading": 0.7, "innovative": 0.7, "trusted": 0.8,
        "reliable": 0.7, "popular": 0.6, "good": 0.6, "great": 0.7,
        "preferred": 0.7, "award": 0.7, "quality": 0.6, "premium": 0.6,
    },
    "negative": {
        "worst": -0.9, "avoid": -0.8, "poor": -0.7, "unreliable": -0.8,
        "expensive": -0.4, "complaint": -0.6, "issue": -0.4, "problem": -0.5,
        "outdated": -0.5, "slow": -0.4, "limited": -0.3, "lacking": -0.5,
        "controversial": -0.4, "criticized": -0.5, "decline": -0.5,
    },
}

SENTIMENT_LEXICON_KO = {
    "positive": {
        "추천": 0.8, "최고": 0.9, "우수": 0.8, "신뢰": 0.7,
        "혁신": 0.7, "인기": 0.6, "우수한": 0.7, "훌륭": 0.8,
        "만족": 0.7, "편리": 0.6, "빠른": 0.5, "정확": 0.6,
    },
    "negative": {
        "최악": -0.9, "불만": -0.7, "피하": -0.8, "문제": -0.5,
        "비싼": -0.4, "느린": -0.4, "불편": -0.5, "부족": -0.5,
        "실망": -0.6, "후회": -0.7, "사기": -0.9,
    },
}


def compute_sentiment_score(text: str) -> dict:
    """Compute sentiment score from text using lexicon-based approach."""
    text_lower = text.lower()
    words = re.findall(r'\b\w+\b', text_lower)
    korean_tokens = re.findall(r'[가-힣]+', text)

    positive_hits = []
    negative_hits = []
    total_score = 0.0

    for word in words:
        if word in SENTIMENT_LEXICON_EN["positive"]:
            score = SENTIMENT_LEXICON_EN["positive"][word]
            positive_hits.append({"word": word, "score": score})
            total_score += score
        elif word in SENTIMENT_LEXICON_EN["negative"]:
            score = SENTIMENT_LEXICON_EN["negative"][word]
            negative_hits.append({"word": word, "score": score})
            total_score += score

    for token in korean_tokens:
        for kw, score in SENTIMENT_LEXICON_KO["positive"].items():
            if kw in token:
                positive_hits.append({"word": kw, "score": score})
                total_score += score
        for kw, score in SENTIMENT_LEXICON_KO["negative"].items():
            if kw in token:
                negative_hits.append({"word": kw, "score": score})
                total_score += score

    hit_count = len(positive_hits) + len(negative_hits)
    if hit_count == 0:
        normalized = 0.0
    else:
        normalized = total_score / hit_count

    if normalized > 0.2:
        label = "positive"
    elif normalized < -0.2:
        label = "negative"
    else:
        label = "neutral"

    score_0_100 = round(max(0, min(100, (normalized + 1) * 50)), 1)

    return {
        "label": label,
        "raw_score": round(total_score, 3),
        "normalized": round(normalized, 3),
        "score_0_100": score_0_100,
        "positive_signals": len(positive_hits),
        "negative_signals": len(negative_hits),
        "positive_hits": positive_hits[:5],
        "negative_hits": negative_hits[:5],
    }


def analyze_brand_sentiment(brand: str, mentions: list) -> dict:
    """Analyze sentiment across multiple brand mentions."""
    if not mentions:
        return {
            "success": True,
            "brand": brand,
            "total_mentions": 0,
            "overall_sentiment": "unknown",
            "score": 50.0,
        }

    analyses = []
    for mention in mentions:
        text = mention.get("text", "")
        if brand.lower() not in text.lower():
            continue
        sentiment = compute_sentiment_score(text)
        sentiment["platform"] = mention.get("platform", "unknown")
        sentiment["query"] = mention.get("query", "")
        analyses.append(sentiment)

    if not analyses:
        return {
            "success": True,
            "brand": brand,
            "total_mentions": 0,
            "overall_sentiment": "unknown",
            "score": 50.0,
        }

    avg_score = round(sum(a["score_0_100"] for a in analyses) / len(analyses), 1)
    labels = {"positive": 0, "negative": 0, "neutral": 0}
    for a in analyses:
        labels[a["label"]] += 1

    overall = max(labels, key=labels.get)

    platform_sentiment = {}
    for a in analyses:
        p = a["platform"]
        if p not in platform_sentiment:
            platform_sentiment[p] = []
        platform_sentiment[p].append(a["score_0_100"])

    platform_avg = {
        p: round(sum(scores) / len(scores), 1)
        for p, scores in platform_sentiment.items()
    }

    return {
        "success": True,
        "brand": brand,
        "total_mentions": len(analyses),
        "overall_sentiment": overall,
        "score": avg_score,
        "label_distribution": labels,
        "platform_scores": platform_avg,
        "analyses": analyses[:20],
    }


def main():
    parser = argparse.ArgumentParser(description="AI brand mention sentiment analysis")
    parser.add_argument("brand", help="Brand name")
    parser.add_argument("--text", help="Single text to analyze")
    parser.add_argument("--input", help="JSON file with mentions")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    if args.input:
        from pathlib import Path
        mentions = json.loads(Path(args.input).read_text())
        result = analyze_brand_sentiment(args.brand, mentions)
    elif args.text:
        sentiment = compute_sentiment_score(args.text)
        result = {"success": True, "brand": args.brand, "sentiment": sentiment}
    else:
        print("Error: Provide --text or --input", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if "overall_sentiment" in result:
            print(f"Sentiment Analysis: {args.brand}")
            print(f"Overall: {result['overall_sentiment']} ({result['score']}/100)")
            print(f"Mentions: {result['total_mentions']}")
            dist = result.get("label_distribution", {})
            print(f"Distribution: +{dist.get('positive', 0)} / ~{dist.get('neutral', 0)} / -{dist.get('negative', 0)}")
            if result.get("platform_scores"):
                print("Platform Scores:")
                for p, s in result["platform_scores"].items():
                    print(f"  {p}: {s}/100")
        else:
            s = result["sentiment"]
            print(f"Sentiment: {s['label']} ({s['score_0_100']}/100)")


if __name__ == "__main__":
    main()

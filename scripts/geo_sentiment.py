"""Sentiment analysis script for AI-generated brand mentions. Three-O platform."""

import argparse
import json
import math
import re
import sys


SENTIMENT_WEIGHTS = {
    "polarity_strength": 0.30,
    "consistency": 0.25,
    "coverage": 0.20,
    "platform_alignment": 0.15,
    "signal_diversity": 0.10,
}

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

    unique_words = set(h["word"] for h in positive_hits + negative_hits)

    return {
        "label": label,
        "raw_score": round(total_score, 3),
        "normalized": round(normalized, 3),
        "score_0_100": score_0_100,
        "positive_signals": len(positive_hits),
        "negative_signals": len(negative_hits),
        "positive_hits": positive_hits[:5],
        "negative_hits": negative_hits[:5],
        "unique_words": list(unique_words),
    }


def _score_polarity_strength(analyses: list) -> float:
    """Average absolute intensity of detected sentiment signals (0-100)."""
    if not analyses:
        return 0.0
    intensities = []
    for a in analyses:
        hits = a.get("positive_hits", []) + a.get("negative_hits", [])
        for h in hits:
            intensities.append(abs(h["score"]))
    if not intensities:
        return 0.0
    avg_intensity = sum(intensities) / len(intensities)
    return round(min(100, avg_intensity * 100), 1)


def _score_consistency(analyses: list) -> float:
    """How consistent is sentiment across mentions (0-100). Low variance = high."""
    if len(analyses) < 2:
        return 100.0 if analyses else 0.0
    scores = [a["score_0_100"] for a in analyses]
    mean = sum(scores) / len(scores)
    variance = sum((s - mean) ** 2 for s in scores) / len(scores)
    std_dev = math.sqrt(variance)
    return round(max(0, min(100, 100 - std_dev * 2)), 1)


def _score_coverage(analyses: list, total_input: int) -> float:
    """Percentage of mentions with detectable sentiment signals (0-100)."""
    if total_input == 0:
        return 0.0
    with_signals = sum(
        1 for a in analyses
        if a.get("positive_signals", 0) + a.get("negative_signals", 0) > 0
    )
    return round(min(100, (with_signals / total_input) * 100), 1)


def _score_platform_alignment(analyses: list) -> float:
    """Cross-platform sentiment consistency (0-100)."""
    platform_scores = {}
    for a in analyses:
        p = a.get("platform", "unknown")
        if p not in platform_scores:
            platform_scores[p] = []
        platform_scores[p].append(a["score_0_100"])

    if len(platform_scores) < 2:
        return 100.0 if platform_scores else 0.0

    platform_avgs = [sum(v) / len(v) for v in platform_scores.values()]
    mean = sum(platform_avgs) / len(platform_avgs)
    variance = sum((a - mean) ** 2 for a in platform_avgs) / len(platform_avgs)
    std_dev = math.sqrt(variance)
    return round(max(0, min(100, 100 - std_dev * 2.5)), 1)


def _score_signal_diversity(analyses: list) -> float:
    """Variety of sentiment signals detected (0-100)."""
    if not analyses:
        return 0.0
    all_words = set()
    total_hits = 0
    for a in analyses:
        all_words.update(a.get("unique_words", []))
        total_hits += a.get("positive_signals", 0) + a.get("negative_signals", 0)
    if total_hits == 0:
        return 0.0
    total_lexicon = len(SENTIMENT_LEXICON_EN["positive"]) + len(SENTIMENT_LEXICON_EN["negative"]) + \
        len(SENTIMENT_LEXICON_KO["positive"]) + len(SENTIMENT_LEXICON_KO["negative"])
    lexicon_coverage = len(all_words) / total_lexicon
    return round(min(100, lexicon_coverage * 200), 1)


def analyze_brand_sentiment(brand: str, mentions: list) -> dict:
    """Analyze sentiment across multiple brand mentions with 5-dimension scoring."""
    if not mentions:
        return {
            "success": True,
            "brand": brand,
            "total_mentions": 0,
            "overall_sentiment": "unknown",
            "score": 50.0,
            "dimensions": {k: 0.0 for k in SENTIMENT_WEIGHTS},
            "confidence": 0.0,
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
            "dimensions": {k: 0.0 for k in SENTIMENT_WEIGHTS},
            "confidence": 0.0,
        }

    dim_scores = {
        "polarity_strength": _score_polarity_strength(analyses),
        "consistency": _score_consistency(analyses),
        "coverage": _score_coverage(analyses, len(mentions)),
        "platform_alignment": _score_platform_alignment(analyses),
        "signal_diversity": _score_signal_diversity(analyses),
    }

    overall = round(
        sum(dim_scores[k] * SENTIMENT_WEIGHTS[k] for k in SENTIMENT_WEIGHTS), 1
    )

    labels = {"positive": 0, "negative": 0, "neutral": 0}
    for a in analyses:
        labels[a["label"]] += 1
    overall_label = max(labels, key=labels.get)

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

    data_points = min(len(analyses), 20)
    platforms_seen = len(platform_sentiment)
    confidence = round(min(1.0, (data_points / 10) * 0.5 + (platforms_seen / 4) * 0.3 + 0.2), 2)

    return {
        "success": True,
        "brand": brand,
        "total_mentions": len(analyses),
        "overall_sentiment": overall_label,
        "score": overall,
        "dimensions": dim_scores,
        "label_distribution": labels,
        "platform_scores": platform_avg,
        "confidence": confidence,
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
        if "dimensions" in result:
            print(f"Sentiment Analysis: {args.brand}")
            print(f"Overall: {result['overall_sentiment']} ({result['score']}/100)")
            print(f"Mentions: {result['total_mentions']} (confidence: {result['confidence']})")
            print("\nDimensions:")
            for dim, val in result["dimensions"].items():
                weight = SENTIMENT_WEIGHTS[dim]
                print(f"  {dim}: {val}/100 (x{weight})")
            dist = result.get("label_distribution", {})
            print(f"\nDistribution: +{dist.get('positive', 0)} / ~{dist.get('neutral', 0)} / -{dist.get('negative', 0)}")
            if result.get("platform_scores"):
                print("Platform Scores:")
                for p, s in result["platform_scores"].items():
                    print(f"  {p}: {s}/100")
        else:
            s = result["sentiment"]
            print(f"Sentiment: {s['label']} ({s['score_0_100']}/100)")


if __name__ == "__main__":
    main()

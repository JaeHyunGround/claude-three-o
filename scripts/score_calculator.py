"""Three-O score computation utilities. Calculates pillar and unified scores.

Scoring precision features:
- Partial GEO scoring: skips unavailable dimensions, redistributes weights
- Confidence scoring: tracks data availability per computation
- Pillar balance penalty: imbalanced profiles penalized via harmonic blend
- Industry-aware weight adjustment at both Three-O and pillar levels
"""

import argparse
import json
import math
import sys
from typing import Dict, Optional

PILLAR_WEIGHTS = {"seo": 0.35, "geo": 0.35, "aao": 0.30}

INDUSTRY_ADJUSTMENTS = {
    "restaurant": {"seo": 0.05, "geo": 0.0, "aao": 0.0},
    "clinic": {"seo": 0.0, "geo": 0.10, "aao": 0.0},
    "academy": {"seo": 0.0, "geo": 0.10, "aao": 0.0},
    "ecommerce": {"seo": 0.0, "geo": 0.0, "aao": 0.10},
    "franchise": {"seo": 0.0, "geo": 0.05, "aao": 0.05},
    "saas": {"seo": 0.0, "geo": 0.0, "aao": 0.05},
    "agency": {"seo": 0.05, "geo": 0.0, "aao": 0.0},
    "realestate": {"seo": 0.05, "geo": 0.0, "aao": 0.0},
    "hotel": {"seo": 0.0, "geo": 0.0, "aao": 0.10},
    "education": {"seo": 0.0, "geo": 0.10, "aao": 0.0},
}

GEO_DIMENSION_WEIGHTS = {"mf": 0.30, "cq": 0.25, "vr": 0.20, "ep": 0.15, "ta": 0.10}

GRADES = [
    (90, "A+"), (80, "A"), (70, "B+"), (60, "B"),
    (50, "C+"), (40, "C"), (30, "D"), (0, "F"),
]

BALANCE_PENALTY_WEIGHT = 0.15


def get_grade(score: float) -> str:
    for threshold, grade in GRADES:
        if score >= threshold:
            return grade
    return "F"


def _balance_penalty(scores: list) -> float:
    """Compute penalty for imbalanced pillar scores.
    Uses coefficient of variation: std_dev / mean.
    Returns a penalty multiplier between 0.85 and 1.0."""
    valid = [s for s in scores if s > 0]
    if len(valid) < 2:
        return 1.0
    mean = sum(valid) / len(valid)
    if mean < 1:
        return 1.0
    variance = sum((s - mean) ** 2 for s in valid) / len(valid)
    cv = math.sqrt(variance) / mean
    penalty = max(0.85, 1.0 - cv * BALANCE_PENALTY_WEIGHT)
    return penalty


def compute_three_o_score(seo: float, geo: float, aao: float, industry: Optional[str] = None) -> dict:
    """Compute unified Three-O score with balance penalty and industry adjustment."""
    weights = dict(PILLAR_WEIGHTS)

    if industry and industry in INDUSTRY_ADJUSTMENTS:
        adj = INDUSTRY_ADJUSTMENTS[industry]
        total_adj = sum(adj.values())
        for pillar in weights:
            weights[pillar] += adj[pillar] - (total_adj / 3)

    total_weight = sum(weights.values())
    weights = {k: v / total_weight for k, v in weights.items()}

    weighted_avg = seo * weights["seo"] + geo * weights["geo"] + aao * weights["aao"]

    pillar_scores = [s for s in [seo, geo, aao] if s > 0]
    penalty = _balance_penalty(pillar_scores)
    score = weighted_avg * penalty
    score = max(0, min(100, score))

    available = sum(1 for s in [seo, geo, aao] if s > 0)
    confidence = round(available / 3, 2)

    return {
        "three_o_score": round(score, 1),
        "grade": get_grade(score),
        "pillars": {"seo": round(seo, 1), "geo": round(geo, 1), "aao": round(aao, 1)},
        "weights_applied": {k: round(v, 3) for k, v in weights.items()},
        "balance_penalty": round(penalty, 3),
        "confidence": confidence,
        "industry": industry,
    }


def compute_geo_score(mf: float, cq: float, vr: float, ep: float, ta: float) -> dict:
    """Compute GEO score using weighted geometric mean with partial dimension support.
    Dimensions with score 0 are treated as unavailable and their weight is redistributed."""
    dimensions = {"mf": mf, "cq": cq, "vr": vr, "ep": ep, "ta": ta}

    available = {k: v for k, v in dimensions.items() if v > 0}
    unavailable = [k for k, v in dimensions.items() if v <= 0]

    if not available:
        return {
            "geo_score": 0.0,
            "grade": "F",
            "dimensions": {k: round(v, 1) for k, v in dimensions.items()},
            "confidence": 0.0,
            "partial": True,
        }

    active_weights = {k: GEO_DIMENSION_WEIGHTS[k] for k in available}
    total_active = sum(active_weights.values())
    normalized_weights = {k: w / total_active for k, w in active_weights.items()}

    normalized_scores = {k: max(0.01, min(1.0, v / 100)) for k, v in available.items()}

    log_score = sum(normalized_weights[k] * math.log(normalized_scores[k]) for k in available)
    geo_score = math.exp(log_score) * 100
    geo_score = max(0, min(100, geo_score))

    confidence = round(sum(GEO_DIMENSION_WEIGHTS[k] for k in available), 2)

    return {
        "geo_score": round(geo_score, 1),
        "grade": get_grade(geo_score),
        "dimensions": {k: round(v, 1) for k, v in dimensions.items()},
        "confidence": confidence,
        "partial": len(unavailable) > 0,
        "unavailable_dimensions": unavailable,
    }


PLATFORMS = ["chatgpt", "perplexity", "gemini", "claude"]


def compute_platform_geo_scores(platform_data: dict) -> dict:
    """Compute GEO score per AI platform with confidence tracking.

    platform_data: {
        "chatgpt": {"mf": 60, "cq": 70, "vr": 50, "ep": 40, "ta": 80},
        "perplexity": {...}, ...
    }
    Returns per-platform GEO scores + overall breakdown.
    """
    platform_scores = {}
    for platform in PLATFORMS:
        dims = platform_data.get(platform, {})
        mf = dims.get("mf", 0)
        cq = dims.get("cq", 0)
        vr = dims.get("vr", 0)
        ep = dims.get("ep", 0)
        ta = dims.get("ta", 0)

        result = compute_geo_score(mf, cq, vr, ep, ta)
        platform_scores[platform] = {
            "geo_score": result["geo_score"],
            "grade": result["grade"],
            "confidence": result.get("confidence", 1.0),
            "dimensions": {"mf": mf, "cq": cq, "vr": vr, "ep": ep, "ta": ta},
        }

    scores = [ps["geo_score"] for ps in platform_scores.values() if ps["geo_score"] > 0]
    overall = round(sum(scores) / max(len(scores), 1), 1)
    best = max(platform_scores, key=lambda p: platform_scores[p]["geo_score"]) if scores else None
    worst = min(platform_scores, key=lambda p: platform_scores[p]["geo_score"]) if scores else None

    avg_confidence = round(
        sum(ps.get("confidence", 0) for ps in platform_scores.values()) / max(len(platform_scores), 1), 2
    )

    return {
        "overall_geo_score": overall,
        "overall_grade": get_grade(overall),
        "confidence": avg_confidence,
        "platforms": platform_scores,
        "best_platform": best,
        "worst_platform": worst,
    }


def main():
    parser = argparse.ArgumentParser(description="Three-O score calculator")
    sub = parser.add_subparsers(dest="command")

    three_o = sub.add_parser("three-o", help="Compute unified Three-O score")
    three_o.add_argument("--seo", type=float, required=True, help="SEO score (0-100)")
    three_o.add_argument("--geo", type=float, required=True, help="GEO score (0-100)")
    three_o.add_argument("--aao", type=float, required=True, help="AAO score (0-100)")
    three_o.add_argument("--industry", choices=list(INDUSTRY_ADJUSTMENTS.keys()), help="Industry type")
    three_o.add_argument("--json", action="store_true", help="Output as JSON")

    geo = sub.add_parser("geo", help="Compute GEO score")
    geo.add_argument("--mf", type=float, required=True, help="Mention Frequency (0-100)")
    geo.add_argument("--cq", type=float, required=True, help="Context Quality (0-100)")
    geo.add_argument("--vr", type=float, required=True, help="Visibility Ranking (0-100)")
    geo.add_argument("--ep", type=float, required=True, help="Entity Presence (0-100)")
    geo.add_argument("--ta", type=float, required=True, help="Technical Accessibility (0-100)")
    geo.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if args.command == "three-o":
        result = compute_three_o_score(args.seo, args.geo, args.aao, args.industry)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Three-O Score: {result['three_o_score']}/100 ({result['grade']})")
            print(f"  SEO: {result['pillars']['seo']} (weight: {result['weights_applied']['seo']:.1%})")
            print(f"  GEO: {result['pillars']['geo']} (weight: {result['weights_applied']['geo']:.1%})")
            print(f"  AAO: {result['pillars']['aao']} (weight: {result['weights_applied']['aao']:.1%})")
            if result['balance_penalty'] < 1.0:
                print(f"  Balance penalty: {result['balance_penalty']:.1%} (imbalanced pillars)")
            print(f"  Confidence: {result['confidence']:.0%}")

    elif args.command == "geo":
        result = compute_geo_score(args.mf, args.cq, args.vr, args.ep, args.ta)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"GEO Score: {result['geo_score']}/100 ({result['grade']})")
            for dim, val in result["dimensions"].items():
                status = " [unavailable]" if dim in result.get("unavailable_dimensions", []) else ""
                print(f"  {dim.upper()}: {val}{status}")
            print(f"  Confidence: {result['confidence']:.0%}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()

"""Three-O score computation utilities. Calculates pillar and unified scores."""

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
}

GEO_DIMENSION_WEIGHTS = {"mf": 0.30, "cq": 0.25, "vr": 0.20, "ep": 0.15, "ta": 0.10}

GRADES = [
    (90, "A+"), (80, "A"), (70, "B+"), (60, "B"),
    (50, "C+"), (40, "C"), (30, "D"), (0, "F"),
]


def get_grade(score: float) -> str:
    for threshold, grade in GRADES:
        if score >= threshold:
            return grade
    return "F"


def compute_three_o_score(seo: float, geo: float, aao: float, industry: Optional[str] = None) -> dict:
    """Compute unified Three-O score with optional industry adjustment."""
    weights = dict(PILLAR_WEIGHTS)

    if industry and industry in INDUSTRY_ADJUSTMENTS:
        adj = INDUSTRY_ADJUSTMENTS[industry]
        total_adj = sum(adj.values())
        for pillar in weights:
            weights[pillar] += adj[pillar] - (total_adj / 3)

    total_weight = sum(weights.values())
    weights = {k: v / total_weight for k, v in weights.items()}

    score = seo * weights["seo"] + geo * weights["geo"] + aao * weights["aao"]
    score = max(0, min(100, score))

    return {
        "three_o_score": round(score, 1),
        "grade": get_grade(score),
        "pillars": {"seo": round(seo, 1), "geo": round(geo, 1), "aao": round(aao, 1)},
        "weights_applied": {k: round(v, 3) for k, v in weights.items()},
        "industry": industry,
    }


def compute_geo_score(mf: float, cq: float, vr: float, ep: float, ta: float) -> dict:
    """Compute GEO score using weighted geometric mean."""
    dimensions = {"mf": mf, "cq": cq, "vr": vr, "ep": ep, "ta": ta}
    normalized = {k: max(0.01, min(1.0, v / 100)) for k, v in dimensions.items()}

    log_score = sum(GEO_DIMENSION_WEIGHTS[k] * math.log(normalized[k]) for k in normalized)
    geo_score = math.exp(log_score) * 100
    geo_score = max(0, min(100, geo_score))

    return {
        "geo_score": round(geo_score, 1),
        "grade": get_grade(geo_score),
        "dimensions": {k: round(v, 1) for k, v in dimensions.items()},
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

    elif args.command == "geo":
        result = compute_geo_score(args.mf, args.cq, args.vr, args.ep, args.ta)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"GEO Score: {result['geo_score']}/100 ({result['grade']})")
            for dim, val in result["dimensions"].items():
                print(f"  {dim.upper()}: {val}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()

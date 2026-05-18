"""GEO score calculation script for Three-O platform."""

import argparse
import json

from score_calculator import compute_geo_score


GEO_DIMENSIONS = {
    "mf": {"name": "Mention Frequency", "weight": 0.30, "description": "How often brand is mentioned across AI platforms"},
    "cq": {"name": "Context Quality", "weight": 0.25, "description": "Quality and accuracy of brand mention context"},
    "vr": {"name": "Visibility Ranking", "weight": 0.20, "description": "Position ranking in AI-generated responses"},
    "ep": {"name": "Entity Presence", "weight": 0.15, "description": "Presence in knowledge graphs and entity databases"},
    "ta": {"name": "Technical Accessibility", "weight": 0.10, "description": "AI crawler accessibility (llms.txt, robots.txt)"},
}


def interpret_geo_score(score: float) -> dict:
    """Provide interpretation and recommendations based on GEO score."""
    if score >= 80:
        level = "excellent"
        summary = "Strong AI visibility across platforms"
        priority = "Maintain current strategy, optimize for new platforms"
    elif score >= 60:
        level = "good"
        summary = "Good AI visibility with room for improvement"
        priority = "Focus on underperforming dimensions"
    elif score >= 40:
        level = "moderate"
        summary = "Moderate AI visibility, significant gaps exist"
        priority = "Build entity presence and improve citability"
    elif score >= 20:
        level = "low"
        summary = "Low AI visibility, brand rarely mentioned"
        priority = "Create foundational content and establish entity presence"
    else:
        level = "minimal"
        summary = "Minimal AI visibility, brand essentially invisible to AI"
        priority = "Start with llms.txt and structured data basics"

    return {"level": level, "summary": summary, "priority": priority}


def identify_weakest_dimensions(scores: dict) -> list:
    """Identify dimensions needing most improvement."""
    dimension_scores = [
        ("mf", scores.get("mf", 0)),
        ("cq", scores.get("cq", 0)),
        ("vr", scores.get("vr", 0)),
        ("ep", scores.get("ep", 0)),
        ("ta", scores.get("ta", 0)),
    ]
    sorted_dims = sorted(dimension_scores, key=lambda x: x[1])
    weakest = []
    for dim_key, dim_score in sorted_dims[:3]:
        dim_info = GEO_DIMENSIONS[dim_key]
        weakest.append({
            "dimension": dim_key,
            "name": dim_info["name"],
            "score": dim_score,
            "weight": dim_info["weight"],
            "impact": round(dim_info["weight"] * (100 - dim_score), 1),
        })
    return weakest


def calculate_geo_score(mf: float, cq: float, vr: float, ep: float, ta: float) -> dict:
    """Calculate GEO score with full analysis."""
    result = compute_geo_score(mf, cq, vr, ep, ta)

    scores = {"mf": mf, "cq": cq, "vr": vr, "ep": ep, "ta": ta}
    interpretation = interpret_geo_score(result["geo_score"])
    weakest = identify_weakest_dimensions(scores)

    return {
        "success": True,
        "score": result["geo_score"],
        "grade": result["grade"],
        "dimensions": {
            key: {
                "name": GEO_DIMENSIONS[key]["name"],
                "score": scores[key],
                "weight": GEO_DIMENSIONS[key]["weight"],
                "weighted_contribution": round(scores[key] * GEO_DIMENSIONS[key]["weight"], 1),
            }
            for key in GEO_DIMENSIONS
        },
        "interpretation": interpretation,
        "weakest_dimensions": weakest,
        "formula": "geometric_mean(MF^0.30 × CQ^0.25 × VR^0.20 × EP^0.15 × TA^0.10)",
    }


def main():
    parser = argparse.ArgumentParser(description="GEO score calculation")
    parser.add_argument("--mf", type=float, required=True, help="Mention Frequency score (0-100)")
    parser.add_argument("--cq", type=float, required=True, help="Context Quality score (0-100)")
    parser.add_argument("--vr", type=float, required=True, help="Visibility Ranking score (0-100)")
    parser.add_argument("--ep", type=float, required=True, help="Entity Presence score (0-100)")
    parser.add_argument("--ta", type=float, required=True, help="Technical Accessibility score (0-100)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    result = calculate_geo_score(args.mf, args.cq, args.vr, args.ep, args.ta)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"GEO Score: {result['score']}/100 ({result['grade']})")
        print(f"Level: {result['interpretation']['level']}")
        print("\nDimension Scores:")
        for key, dim in result["dimensions"].items():
            bar = "█" * int(dim["score"] / 10) + "░" * (10 - int(dim["score"] / 10))
            print(f"  {dim['name']:25s} {bar} {dim['score']:5.1f} (×{dim['weight']})")
        print(f"\nPriority: {result['interpretation']['priority']}")
        if result["weakest_dimensions"]:
            print("\nFocus Areas:")
            for w in result["weakest_dimensions"]:
                print(f"  - {w['name']}: {w['score']:.0f}/100 (impact: {w['impact']:.1f})")


if __name__ == "__main__":
    main()

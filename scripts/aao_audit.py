"""Full AAO audit orchestrator script for Three-O platform."""

import argparse
import json
import sys
from typing import Optional

from validate_url import validate_url


AAO_DIMENSIONS = {
    "selectability": {"weight": 0.25, "name": "Agent Selectability"},
    "conversion": {"weight": 0.20, "name": "Conversion Readiness"},
    "structured_data": {"weight": 0.20, "name": "Structured Data"},
    "rendering": {"weight": 0.15, "name": "Agent Rendering"},
    "entity": {"weight": 0.10, "name": "Entity Consistency"},
    "scenario": {"weight": 0.10, "name": "Scenario Fulfillment"},
}


def run_aao_audit(url: str, brand: Optional[str] = None,
                  industry: Optional[str] = None) -> dict:
    """Run comprehensive AAO audit."""
    validation = validate_url(url)
    if not validation["valid"]:
        return {"success": False, "error": validation["error"]}

    brand_name = brand or url.split("//")[-1].split("/")[0].replace("www.", "").split(".")[0]
    dimension_results = {}

    try:
        from aao_selectability import analyze_selectability
        sel = analyze_selectability(url)
        if sel.get("success"):
            dimension_results["selectability"] = {
                "score": sel["score"],
                "issues": sel.get("issues", []),
            }
    except Exception as e:
        dimension_results["selectability"] = {"score": 0, "error": str(e)}

    try:
        from aao_conversion import analyze_conversion
        conv = analyze_conversion(url)
        if conv.get("success"):
            dimension_results["conversion"] = {
                "score": conv["score"],
                "flow_type": conv.get("flow_type"),
                "completion_rate": conv.get("estimated_completion_rate"),
                "issues": conv.get("issues", []),
            }
    except Exception as e:
        dimension_results["conversion"] = {"score": 0, "error": str(e)}

    try:
        from aao_data import analyze_structured_data
        data = analyze_structured_data(url)
        if data.get("success"):
            dimension_results["structured_data"] = {
                "score": data["score"],
                "schema_count": data.get("json_ld", {}).get("count", 0),
                "has_actions": data.get("actions", {}).get("has_actions", False),
                "issues": data.get("issues", []),
            }
    except Exception as e:
        dimension_results["structured_data"] = {"score": 0, "error": str(e)}

    try:
        from aao_rendering import analyze_rendering
        rend = analyze_rendering(url)
        if rend.get("success"):
            dimension_results["rendering"] = {
                "score": rend["score"],
                "has_ssr": rend.get("ssr", {}).get("has_ssr_content", False),
                "js_dependency": rend.get("js_dependency", {}).get("dependency_level"),
                "issues": rend.get("issues", []),
            }
    except Exception as e:
        dimension_results["rendering"] = {"score": 0, "error": str(e)}

    try:
        from aao_entity import analyze_entity_consistency
        ent = analyze_entity_consistency(url)
        if ent.get("success"):
            dimension_results["entity"] = {
                "score": ent["score"],
                "nap_consistency": ent.get("nap_consistency", {}).get("consistency_rate", 0),
                "issues": ent.get("issues", []),
            }
    except Exception as e:
        dimension_results["entity"] = {"score": 0, "error": str(e)}

    try:
        from aao_scenario import run_scenario_test
        scen = run_scenario_test(url, brand_name, industry)
        if scen.get("success"):
            dimension_results["scenario"] = {
                "score": scen["score"],
                "fulfillable": scen.get("fulfillable", 0),
                "total": scen.get("scenarios_tested", 0),
                "industry": scen.get("industry"),
                "issues": scen.get("issues", []),
            }
    except Exception as e:
        dimension_results["scenario"] = {"score": 0, "error": str(e)}

    overall = round(sum(
        dimension_results.get(dim, {}).get("score", 0) * info["weight"]
        for dim, info in AAO_DIMENSIONS.items()
    ), 1)

    if overall >= 80:
        grade = "A"
    elif overall >= 70:
        grade = "B+"
    elif overall >= 60:
        grade = "B"
    elif overall >= 50:
        grade = "C+"
    elif overall >= 40:
        grade = "C"
    else:
        grade = "D"

    all_issues = []
    for dim_name, dim_data in dimension_results.items():
        for issue in dim_data.get("issues", []):
            issue["dimension"] = dim_name
            all_issues.append(issue)

    all_issues.sort(key=lambda x: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(x.get("severity", "low"), 4))

    return {
        "success": True,
        "url": url,
        "brand": brand_name,
        "industry": industry,
        "aao_score": overall,
        "grade": grade,
        "dimensions": {
            dim: {
                "name": info["name"],
                "weight": info["weight"],
                "score": dimension_results.get(dim, {}).get("score", 0),
            }
            for dim, info in AAO_DIMENSIONS.items()
        },
        "detail": dimension_results,
        "issues": all_issues,
        "recommendations": _generate_recommendations(dimension_results),
    }


def _generate_recommendations(dimensions: dict) -> list:
    """Generate prioritized recommendations."""
    recs = []

    sd = dimensions.get("structured_data", {})
    if sd.get("score", 0) < 40:
        recs.append({
            "priority": "high",
            "area": "Structured Data",
            "action": "Add comprehensive JSON-LD schema with Organization/LocalBusiness type and potentialAction",
        })

    sel = dimensions.get("selectability", {})
    if sel.get("score", 0) < 50:
        recs.append({
            "priority": "high",
            "area": "Selectability",
            "action": "Add aggregate ratings, complete business info, and booking/purchase actions",
        })

    rend = dimensions.get("rendering", {})
    if rend.get("score", 0) < 40:
        recs.append({
            "priority": "high",
            "area": "Rendering",
            "action": "Implement SSR or pre-rendering for key content pages",
        })

    conv = dimensions.get("conversion", {})
    if conv.get("score", 0) < 50:
        recs.append({
            "priority": "medium",
            "area": "Conversion",
            "action": "Simplify conversion flow, add guest checkout, remove CAPTCHA from booking flow",
        })

    ent = dimensions.get("entity", {})
    if ent.get("score", 0) < 50:
        recs.append({
            "priority": "medium",
            "area": "Entity Consistency",
            "action": "Ensure NAP consistency and add sameAs links across all platforms",
        })

    return recs


def main():
    parser = argparse.ArgumentParser(description="Full AAO audit")
    parser.add_argument("url", help="URL to audit")
    parser.add_argument("--brand", help="Brand name")
    parser.add_argument("--industry", help="Industry vertical")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    result = run_aao_audit(args.url, args.brand, args.industry)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result["success"]:
            print(f"AAO Audit: {result['brand']}")
            print(f"AAO Score: {result['aao_score']}/100 ({result['grade']})")
            print(f"\nDimension Scores:")
            for dim, data in result["dimensions"].items():
                bar = "█" * int(data["score"] / 10) + "░" * (10 - int(data["score"] / 10))
                print(f"  {data['name']:25s} {bar} {data['score']:5.1f} (×{data['weight']})")
            if result["issues"]:
                print(f"\nTop Issues:")
                for issue in result["issues"][:8]:
                    print(f"  [{issue['severity'].upper()}] {issue['message']}")
            if result["recommendations"]:
                print(f"\nRecommendations:")
                for rec in result["recommendations"]:
                    print(f"  [{rec['priority'].upper()}] {rec['area']}: {rec['action']}")
        else:
            print(f"Error: {result['error']}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()

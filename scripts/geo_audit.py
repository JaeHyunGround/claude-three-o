"""Full GEO audit orchestrator script for Three-O platform."""

import argparse
import json
import sys
from typing import Optional

from validate_url import validate_url
from score_calculator import compute_geo_score, compute_platform_geo_scores, PLATFORMS


def run_geo_audit(brand: str, url: Optional[str] = None,
                  industry: Optional[str] = None) -> dict:
    """Run comprehensive GEO audit combining all dimensions."""
    dimension_results = {}

    if url:
        validation = validate_url(url)
        if not validation["valid"]:
            return {"success": False, "error": validation["error"]}

        try:
            from geo_citability import analyze_citability
            cit_result = analyze_citability(url)
            if cit_result.get("success"):
                dimension_results["citability"] = {
                    "score": cit_result["score"],
                    "passages": cit_result.get("total_passages", 0),
                    "issues": cit_result.get("issues", []),
                }
        except Exception as e:
            dimension_results["citability"] = {"score": 0, "error": str(e)}

        try:
            from geo_entity import estimate_entity_presence
            ent_result = estimate_entity_presence(brand, url)
            if ent_result.get("success"):
                dimension_results["entity"] = {
                    "score": ent_result["score"],
                    "confirmed_sources": ent_result.get("confirmed_sources", 0),
                    "issues": ent_result.get("issues", []),
                }
        except Exception as e:
            dimension_results["entity"] = {"score": 0, "error": str(e)}

        try:
            from geo_llms_txt import analyze_llms_txt
            llms_result = analyze_llms_txt(url)
            if llms_result.get("success"):
                dimension_results["llms_txt"] = {
                    "status": llms_result.get("status"),
                    "score": llms_result.get("score", 0),
                    "issues": llms_result.get("issues", []),
                }
        except Exception as e:
            dimension_results["llms_txt"] = {"score": 0, "error": str(e)}

        try:
            from geo_technical import analyze_technical_accessibility
            tech_result = analyze_technical_accessibility(url)
            if tech_result.get("success"):
                dimension_results["technical"] = {
                    "score": tech_result["score"],
                    "has_llms_txt": tech_result.get("has_llms_txt", False),
                    "ssr_status": tech_result.get("ssr", {}).get("ssr_status"),
                    "issues": tech_result.get("issues", []),
                }
        except Exception as e:
            dimension_results["technical"] = {"score": 0, "error": str(e)}

        try:
            from geo_platforms import analyze_platforms
            plat_result = analyze_platforms(url)
            if plat_result.get("success"):
                dimension_results["platforms"] = {
                    "avg_score": plat_result.get("avg_score", 0),
                    "best_platform": plat_result.get("best_platform"),
                    "worst_platform": plat_result.get("worst_platform"),
                    "scores": {p: info["score"] for p, info in plat_result.get("platforms", {}).items()},
                    "issues": plat_result.get("issues", []),
                }
        except Exception as e:
            dimension_results["platforms"] = {"avg_score": 0, "error": str(e)}

    mf_score = 0.0
    cq_score = dimension_results.get("citability", {}).get("score", 0)
    vr_score = 0.0
    ep_score = dimension_results.get("entity", {}).get("score", 0)
    ta_score = dimension_results.get("technical", {}).get("score", 0)

    platform_scores_raw = dimension_results.get("platforms", {}).get("scores", {})
    if dimension_results.get("platforms", {}).get("avg_score"):
        cq_score = round((cq_score + dimension_results["platforms"]["avg_score"]) / 2, 1)

    geo_result = compute_geo_score(mf_score, cq_score, vr_score, ep_score, ta_score)

    platform_data = {}
    for p in PLATFORMS:
        p_platform_score = platform_scores_raw.get(p, 0)
        platform_data[p] = {
            "mf": mf_score,
            "cq": p_platform_score if p_platform_score else cq_score,
            "vr": vr_score,
            "ep": ep_score,
            "ta": ta_score,
        }
    platform_geo = compute_platform_geo_scores(platform_data)

    all_issues = []
    for dim_name, dim_data in dimension_results.items():
        for issue in dim_data.get("issues", []):
            issue["dimension"] = dim_name
            all_issues.append(issue)

    all_issues.sort(key=lambda x: {"critical": 0, "high": 1, "medium": 2, "warning": 3, "low": 4}.get(x.get("severity", "low"), 5))

    if mf_score == 0:
        all_issues.insert(0, {
            "severity": "info",
            "dimension": "mentions",
            "message": "Mention Frequency requires API keys — configure via 'three-o setup'",
        })
    if vr_score == 0:
        all_issues.insert(0, {
            "severity": "info",
            "dimension": "visibility",
            "message": "Visibility Ranking requires API probing — configure platform API keys",
        })

    return {
        "success": True,
        "brand": brand,
        "url": url,
        "industry": industry,
        "geo_score": geo_result["geo_score"],
        "geo_grade": geo_result["grade"],
        "dimensions": {
            "mf": {"score": mf_score, "name": "Mention Frequency", "status": "requires_api"},
            "cq": {"score": cq_score, "name": "Context Quality"},
            "vr": {"score": vr_score, "name": "Visibility Ranking", "status": "requires_api"},
            "ep": {"score": ep_score, "name": "Entity Presence"},
            "ta": {"score": ta_score, "name": "Technical Accessibility"},
        },
        "platform_breakdown": platform_geo["platforms"],
        "best_platform": platform_geo["best_platform"],
        "worst_platform": platform_geo["worst_platform"],
        "detail": dimension_results,
        "issues": all_issues,
        "recommendations": generate_recommendations(dimension_results, geo_result["geo_score"]),
    }


def generate_recommendations(dimensions: dict, overall_score: float) -> list:
    """Generate prioritized recommendations."""
    recs = []

    tech = dimensions.get("technical", {})
    if tech.get("score", 0) < 50:
        recs.append({
            "priority": "high",
            "area": "Technical Accessibility",
            "action": "Ensure AI crawlers are not blocked in robots.txt and content is server-side rendered",
        })

    entity = dimensions.get("entity", {})
    if entity.get("score", 0) < 50:
        recs.append({
            "priority": "high",
            "area": "Entity Presence",
            "action": "Add Organization schema with sameAs links, create Wikidata entry",
        })

    citability = dimensions.get("citability", {})
    if citability.get("score", 0) < 50:
        recs.append({
            "priority": "medium",
            "area": "Citability",
            "action": "Restructure content into clear, extractable passages with facts and data",
        })

    llms = dimensions.get("llms_txt", {})
    if llms.get("status") == "missing":
        recs.append({
            "priority": "medium",
            "area": "llms.txt",
            "action": "Create and publish llms.txt to guide AI crawlers",
        })

    if overall_score < 30:
        recs.append({
            "priority": "high",
            "area": "Overall",
            "action": "Start with technical foundations: SSR, structured data, and llms.txt before content optimization",
        })

    return recs


def main():
    parser = argparse.ArgumentParser(description="Full GEO audit")
    parser.add_argument("brand", help="Brand name")
    parser.add_argument("--url", help="Brand website URL")
    parser.add_argument("--industry", help="Industry vertical")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    result = run_geo_audit(args.brand, args.url, args.industry)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result["success"]:
            print(f"GEO Audit: {args.brand}")
            print(f"GEO Score: {result['geo_score']}/100 ({result['geo_grade']})")
            print(f"\nDimension Scores:")
            for key, dim in result["dimensions"].items():
                status = f" [{dim['status']}]" if dim.get("status") else ""
                bar = "█" * int(dim["score"] / 10) + "░" * (10 - int(dim["score"] / 10))
                print(f"  {dim['name']:25s} {bar} {dim['score']:5.1f}{status}")
            pb = result.get("platform_breakdown", {})
            if pb:
                print(f"\nPlatform GEO Breakdown:")
                for p, pdata in pb.items():
                    s = pdata["geo_score"]
                    bar = "█" * int(s / 10) + "░" * (10 - int(s / 10))
                    print(f"  {p:15s} {bar} {s:5.1f} ({pdata['grade']})")
                if result.get("best_platform"):
                    print(f"  Best:  {result['best_platform']}  |  Worst: {result['worst_platform']}")
            if result["issues"]:
                print(f"\nIssues ({len(result['issues'])}):")
                for issue in result["issues"][:10]:
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

"""Strategic optimization plan generator for Three-O platform."""

import argparse
import json
import sys
from typing import Optional


INDUSTRY_PRIORITIES = {
    "restaurant": {
        "focus": ["Naver Place optimization", "Menu schema", "Booking flow", "AI mentions"],
        "seo_weight": 0.40,
        "geo_weight": 0.30,
        "aao_weight": 0.30,
    },
    "ecommerce": {
        "focus": ["Product feed", "Smart Store sync", "Purchase flow", "Price visibility"],
        "seo_weight": 0.30,
        "geo_weight": 0.30,
        "aao_weight": 0.40,
    },
    "franchise": {
        "focus": ["Multi-location schema", "Brand consistency", "Local SEO", "AI brand presence"],
        "seo_weight": 0.30,
        "geo_weight": 0.35,
        "aao_weight": 0.35,
    },
    "academy": {
        "focus": ["Course schema", "Review collection", "AI brand visibility", "Content depth"],
        "seo_weight": 0.30,
        "geo_weight": 0.40,
        "aao_weight": 0.30,
    },
    "clinic": {
        "focus": ["MedicalBusiness schema", "Trust signals", "AI authority", "Booking flow"],
        "seo_weight": 0.30,
        "geo_weight": 0.40,
        "aao_weight": 0.30,
    },
    "service": {
        "focus": ["Service schema", "Review signals", "AI citability", "Contact flow"],
        "seo_weight": 0.35,
        "geo_weight": 0.35,
        "aao_weight": 0.30,
    },
}

TIMELINE_TEMPLATE = {
    "week_1_2": {
        "phase": "Foundation",
        "tasks": [],
    },
    "week_3_4": {
        "phase": "Technical Optimization",
        "tasks": [],
    },
    "month_2": {
        "phase": "Content & Visibility",
        "tasks": [],
    },
    "month_3": {
        "phase": "Agent Optimization",
        "tasks": [],
    },
    "ongoing": {
        "phase": "Monitoring & Iteration",
        "tasks": [],
    },
}


def generate_plan_from_audit(audit_data: dict, industry: Optional[str] = None) -> dict:
    """Generate optimization plan from audit results."""
    detected_industry = industry or "service"
    industry_config = INDUSTRY_PRIORITIES.get(detected_industry, INDUSTRY_PRIORITIES["service"])

    seo_score = audit_data.get("seo", {}).get("score", 50)
    geo_score = audit_data.get("geo", {}).get("score", 50)
    aao_score = audit_data.get("aao", {}).get("score", 50)

    all_issues = []
    for pillar in ["seo", "geo", "aao"]:
        for issue in audit_data.get(pillar, {}).get("issues", []):
            issue["pillar"] = pillar
            all_issues.append(issue)

    severity_map = {"critical": 0, "high": 1, "medium": 2, "warning": 3, "low": 4, "info": 5}
    all_issues.sort(key=lambda x: severity_map.get(x.get("severity", "low"), 5))

    timeline = _build_timeline(all_issues, seo_score, geo_score, aao_score, industry_config)

    weakest = min(
        [("SEO", seo_score), ("GEO", geo_score), ("AAO", aao_score)],
        key=lambda x: x[1]
    )

    goals = []
    if seo_score < 60:
        goals.append({"pillar": "SEO", "current": seo_score, "target": min(80, seo_score + 20), "timeline": "3 months"})
    if geo_score < 60:
        goals.append({"pillar": "GEO", "current": geo_score, "target": min(80, geo_score + 20), "timeline": "3 months"})
    if aao_score < 60:
        goals.append({"pillar": "AAO", "current": aao_score, "target": min(80, aao_score + 20), "timeline": "3 months"})

    return {
        "success": True,
        "industry": detected_industry,
        "industry_focus": industry_config["focus"],
        "current_scores": {"seo": seo_score, "geo": geo_score, "aao": aao_score},
        "weakest_pillar": weakest[0],
        "goals": goals,
        "timeline": timeline,
        "total_issues": len(all_issues),
        "critical_issues": sum(1 for i in all_issues if i.get("severity") in ["critical", "high"]),
    }


def _build_timeline(issues: list, seo: float, geo: float, aao: float, config: dict) -> dict:
    """Build implementation timeline from issues."""
    timeline = {
        "week_1_2": {
            "phase": "Foundation",
            "tasks": [],
        },
        "week_3_4": {
            "phase": "Technical Optimization",
            "tasks": [],
        },
        "month_2": {
            "phase": "Content & Visibility",
            "tasks": [],
        },
        "month_3": {
            "phase": "Agent Optimization",
            "tasks": [],
        },
        "ongoing": {
            "phase": "Monitoring & Iteration",
            "tasks": ["Run weekly drift checks", "Monitor AI mention changes", "Update structured data as needed"],
        },
    }

    for issue in issues:
        severity = issue.get("severity", "low")
        pillar = issue.get("pillar", "")
        message = issue.get("message", "")

        if severity in ["critical", "high"]:
            if pillar == "seo" or "technical" in message.lower():
                timeline["week_1_2"]["tasks"].append(f"[{pillar.upper()}] {message}")
            else:
                timeline["week_3_4"]["tasks"].append(f"[{pillar.upper()}] {message}")
        elif severity == "medium":
            if pillar == "geo":
                timeline["month_2"]["tasks"].append(f"[GEO] {message}")
            elif pillar == "aao":
                timeline["month_3"]["tasks"].append(f"[AAO] {message}")
            else:
                timeline["week_3_4"]["tasks"].append(f"[{pillar.upper()}] {message}")

    for phase in timeline.values():
        phase["tasks"] = phase["tasks"][:8]

    return timeline


def generate_plan_from_scores(seo: float, geo: float, aao: float,
                              industry: Optional[str] = None,
                              brand: Optional[str] = None) -> dict:
    """Generate a basic plan from scores without full audit data."""
    audit_data = {
        "seo": {"score": seo, "issues": []},
        "geo": {"score": geo, "issues": []},
        "aao": {"score": aao, "issues": []},
    }

    if seo < 50:
        audit_data["seo"]["issues"].extend([
            {"severity": "high", "message": "Technical SEO foundations need improvement"},
            {"severity": "medium", "message": "Content optimization required"},
        ])
    if geo < 50:
        audit_data["geo"]["issues"].extend([
            {"severity": "high", "message": "AI visibility is low — establish entity presence"},
            {"severity": "medium", "message": "Create llms.txt and optimize for citability"},
        ])
    if aao < 50:
        audit_data["aao"]["issues"].extend([
            {"severity": "high", "message": "Structured data incomplete for agent consumption"},
            {"severity": "medium", "message": "Conversion flow needs agent optimization"},
        ])

    return generate_plan_from_audit(audit_data, industry)


def main():
    parser = argparse.ArgumentParser(description="Three-O strategic plan generation")
    parser.add_argument("--input", help="Audit data JSON file")
    parser.add_argument("--seo", type=float, help="SEO score")
    parser.add_argument("--geo", type=float, help="GEO score")
    parser.add_argument("--aao", type=float, help="AAO score")
    parser.add_argument("--industry", choices=list(INDUSTRY_PRIORITIES.keys()), help="Industry type")
    parser.add_argument("--brand", help="Brand name")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    if args.input:
        from pathlib import Path
        data = json.loads(Path(args.input).read_text())
        result = generate_plan_from_audit(data, args.industry)
    elif args.seo is not None and args.geo is not None and args.aao is not None:
        result = generate_plan_from_scores(args.seo, args.geo, args.aao, args.industry, args.brand)
    else:
        print("Error: Provide --input or --seo/--geo/--aao scores", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"Three-O Optimization Plan ({result['industry']})")
        print(f"Focus: {', '.join(result['industry_focus'])}")
        print(f"\nCurrent: SEO={result['current_scores']['seo']:.0f} GEO={result['current_scores']['geo']:.0f} AAO={result['current_scores']['aao']:.0f}")
        print(f"Weakest: {result['weakest_pillar']} | Critical Issues: {result['critical_issues']}")
        if result["goals"]:
            print(f"\nGoals:")
            for g in result["goals"]:
                print(f"  {g['pillar']}: {g['current']:.0f} → {g['target']:.0f} ({g['timeline']})")
        print(f"\nTimeline:")
        for phase_key, phase in result["timeline"].items():
            if phase["tasks"]:
                print(f"\n  {phase_key.replace('_', ' ').title()} — {phase['phase']}")
                for task in phase["tasks"][:5]:
                    print(f"    - {task}")


if __name__ == "__main__":
    main()

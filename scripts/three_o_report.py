"""Unified report generation script for Three-O platform."""

import argparse
import json
import os
from datetime import datetime

from config import VERSION
from recommendations import generate_recommendations, format_recommendations_md


REPORT_SECTIONS = {
    "full": ["executive_summary", "score_dashboard", "seo", "geo", "aao", "recommendations", "action_plan"],
    "seo": ["executive_summary", "seo"],
    "geo": ["executive_summary", "geo"],
    "aao": ["executive_summary", "aao"],
}


def generate_executive_summary(data: dict) -> str:
    """Generate executive summary section with key insights."""
    brand = data.get("brand", "Unknown")
    score = data.get("three_o_score", {})

    lines = [
        f"# Three-O Audit Report: {brand}",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## Executive Summary",
        "",
        f"**Three-O Score: {score.get('score', 'N/A')}/100 ({score.get('grade', 'N/A')})**",
        "",
    ]

    pillar_scores = score.get("pillars", {})
    if pillar_scores:
        lines.append("| Pillar | Score | Weight |")
        lines.append("|--------|-------|--------|")
        for pillar, info in pillar_scores.items():
            lines.append(f"| {pillar.upper()} | {info.get('score', 'N/A')}/100 | {info.get('weight', 'N/A')} |")
        lines.append("")

    insights = _generate_insights(data)
    if insights:
        lines.append("### Key Insights")
        lines.append("")
        for insight in insights:
            lines.append(f"- {insight}")
        lines.append("")

    top_issues = data.get("top_issues", [])
    if top_issues:
        lines.append("### Top Priority Actions")
        lines.append("")
        for i, issue in enumerate(top_issues[:3], 1):
            lines.append(f"{i}. **[{issue.get('severity', '').upper()}]** {issue.get('message', '')}")
        lines.append("")

    rec_data = generate_recommendations(data)
    if rec_data.get("quick_wins"):
        lines.append("### Quick Wins Available")
        lines.append("")
        for qw in rec_data["quick_wins"][:3]:
            lines.append(f"- **{qw['title']}** (effort: {qw['effort_estimate']}, impact: {qw['impact_estimate']})")
        lines.append("")

    return "\n".join(lines)


def _generate_insights(data: dict) -> list:
    """Generate key insights from audit data."""
    insights = []

    seo_score = data.get("seo", {}).get("score", 0)
    geo_score = data.get("geo", {}).get("score", 0)
    aao_score = data.get("aao", {}).get("score", 0)
    scores = {"SEO": seo_score, "GEO": geo_score, "AAO": aao_score}

    if seo_score and geo_score and aao_score:
        weakest = min(scores, key=scores.get)
        strongest = max(scores, key=scores.get)
        gap = scores[strongest] - scores[weakest]
        if gap > 20:
            insights.append(f"**Imbalanced profile**: {strongest} ({scores[strongest]:.0f}) significantly outperforms {weakest} ({scores[weakest]:.0f}). Focus on {weakest} for balanced visibility.")
        elif gap < 10 and scores[weakest] >= 60:
            insights.append("**Well-balanced** across all pillars. Fine-tune individual dimensions.")

    industry = data.get("aao", {}).get("industry_detected", "general")
    if industry != "general":
        insights.append(f"**Industry detected: {industry.title()}** — scoring weights automatically adjusted for this sector.")

    geo_data = data.get("geo", {})
    best_platform = geo_data.get("best_platform")
    worst_platform = geo_data.get("worst_platform")
    if best_platform and worst_platform and best_platform != worst_platform:
        insights.append(f"**Platform gap**: Best on {best_platform.capitalize()}, weakest on {worst_platform.capitalize()}. Optimize content for {worst_platform.capitalize()}'s preferences.")

    correlation = data.get("aao", {}).get("correlation", {})
    bonuses = [c for c in correlation.get("applied", []) if c.get("value", 0) > 0]
    penalties = [c for c in correlation.get("applied", []) if c.get("value", 0) < 0]
    if bonuses:
        insights.append(f"**{len(bonuses)} synergy bonus(es)** detected across AAO dimensions.")
    if penalties:
        insights.append(f"**{len(penalties)} signal conflict(s)** found — addressing these will unlock additional points.")

    return insights


def generate_pillar_section(pillar: str, data: dict) -> str:
    """Generate a pillar-specific report section."""
    pillar_data = data.get(pillar, {})
    if not pillar_data:
        return f"\n## {pillar.upper()} Analysis\n\nNo data available. Run `/three-o {pillar} audit` first.\n"

    lines = [
        f"## {pillar.upper()} Analysis",
        "",
        f"**Score: {pillar_data.get('score', 'N/A')}/100**",
        "",
    ]

    dimensions = pillar_data.get("dimensions", {})
    if dimensions:
        lines.append("### Dimension Breakdown")
        lines.append("")
        lines.append("| Dimension | Score |")
        lines.append("|-----------|-------|")
        for dim_name, dim_data in dimensions.items():
            score = dim_data if isinstance(dim_data, (int, float)) else dim_data.get("score", "N/A")
            lines.append(f"| {dim_name.replace('_', ' ').title()} | {score}/100 |")
        lines.append("")

    if pillar == "geo":
        platform_breakdown = pillar_data.get("platform_breakdown", {})
        if platform_breakdown:
            lines.append("### Platform GEO Scores")
            lines.append("")
            lines.append("| Platform | GEO Score | Grade |")
            lines.append("|----------|-----------|-------|")
            for p_name, p_data in platform_breakdown.items():
                p_score = p_data.get("geo_score", 0) if isinstance(p_data, dict) else p_data
                p_grade = p_data.get("grade", "-") if isinstance(p_data, dict) else "-"
                lines.append(f"| {p_name.capitalize()} | {p_score}/100 | {p_grade} |")
            lines.append("")

        platform_citability = pillar_data.get("platform_citability", {})
        if platform_citability:
            lines.append("### Platform Citability")
            lines.append("")
            for p_name, p_score in platform_citability.items():
                bar = "█" * int(p_score / 10) + "░" * (10 - int(p_score / 10))
                lines.append(f"- **{p_name.capitalize()}**: {bar} {p_score:.0f}/100")
            lines.append("")

    if pillar == "aao":
        industry = pillar_data.get("industry_detected", "")
        if industry and industry != "general":
            lines.append(f"### Industry Detected: {industry.title()}")
            lines.append("")
            weights = pillar_data.get("weights_applied", {})
            if weights:
                lines.append("Adjusted weights for this industry:")
                lines.append("")
                for dim, w in weights.items():
                    lines.append(f"- {dim.replace('_', ' ').title()}: {w:.0%}")
                lines.append("")

        correlation = pillar_data.get("correlation", {})
        if correlation and correlation.get("applied"):
            lines.append("### Signal Correlations")
            lines.append("")
            for c in correlation["applied"]:
                prefix = "+" if c["value"] > 0 else ""
                lines.append(f"- {prefix}{c['value']:.0f} pts: {c['reason']}")
            lines.append("")

    issues = pillar_data.get("issues", [])
    if issues:
        lines.append("### Issues Found")
        lines.append("")
        for issue in issues[:10]:
            severity = issue.get("severity", "info").upper()
            lines.append(f"- **[{severity}]** {issue.get('message', '')}")
        lines.append("")

    return "\n".join(lines)


def generate_action_plan(data: dict) -> str:
    """Generate prioritized action plan."""
    lines = [
        "## Action Plan",
        "",
        "### Priority Matrix",
        "",
        "| Priority | Area | Action | Impact |",
        "|----------|------|--------|--------|",
    ]

    all_issues = []
    for pillar in ["seo", "geo", "aao"]:
        pillar_data = data.get(pillar, {})
        for issue in pillar_data.get("issues", []):
            issue["pillar"] = pillar.upper()
            all_issues.append(issue)

    severity_order = {"critical": 0, "high": 1, "medium": 2, "warning": 3, "low": 4}
    all_issues.sort(key=lambda x: severity_order.get(x.get("severity", "low"), 5))

    for issue in all_issues[:15]:
        priority = "P0" if issue.get("severity") in ["critical"] else "P1" if issue.get("severity") == "high" else "P2"
        impact = "High" if issue.get("severity") in ["critical", "high"] else "Medium"
        lines.append(f"| {priority} | {issue.get('pillar', '')} | {issue.get('message', '')} | {impact} |")

    lines.append("")
    return "\n".join(lines)


def generate_report(data: dict, report_type: str = "full",
                    output_format: str = "md") -> dict:
    """Generate complete report."""
    sections = REPORT_SECTIONS.get(report_type, REPORT_SECTIONS["full"])

    if output_format == "json":
        return {
            "success": True,
            "format": "json",
            "report_type": report_type,
            "data": data,
        }

    content_parts = []

    if "executive_summary" in sections:
        content_parts.append(generate_executive_summary(data))

    if "score_dashboard" in sections:
        content_parts.append("## Score Dashboard\n")
        score = data.get("three_o_score", {})
        for pillar in ["seo", "geo", "aao"]:
            p_score = score.get("pillars", {}).get(pillar, {}).get("score", 0)
            bar = "█" * int(p_score / 5) + "░" * (20 - int(p_score / 5))
            content_parts.append(f"{pillar.upper():4s} {bar} {p_score}/100\n")
        content_parts.append("")

    for pillar in ["seo", "geo", "aao"]:
        if pillar in sections:
            content_parts.append(generate_pillar_section(pillar, data))

    if "recommendations" in sections:
        rec_data = generate_recommendations(data)
        content_parts.append(format_recommendations_md(rec_data))

    if "action_plan" in sections:
        content_parts.append(generate_action_plan(data))

    content_parts.append(f"\n---\n*Report generated by Three-O v{VERSION} | {datetime.now().strftime('%Y-%m-%d')}*\n")

    md_content = "\n".join(content_parts)

    return {
        "success": True,
        "format": output_format,
        "report_type": report_type,
        "content": md_content,
        "sections": sections,
    }


def save_report(report: dict, brand: str, report_type: str, output_format: str) -> str:
    """Save report to file."""
    reports_dir = os.path.join(os.getcwd(), "reports")
    os.makedirs(reports_dir, exist_ok=True)

    date_str = datetime.now().strftime("%Y%m%d")
    filename = f"{brand}-{date_str}-{report_type}.{output_format}"
    filepath = os.path.join(reports_dir, filename)

    if output_format == "json":
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report.get("data", report), f, indent=2, ensure_ascii=False)
    else:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report.get("content", ""))

    return filepath


def main():
    parser = argparse.ArgumentParser(description="Three-O unified report generation")
    parser.add_argument("type", choices=["full", "seo", "geo", "aao"], default="full", nargs="?", help="Report type")
    parser.add_argument("--input", help="Audit data JSON file")
    parser.add_argument("--brand", default="unknown", help="Brand name")
    parser.add_argument("--format", choices=["md", "json", "pdf"], default="md", help="Output format")
    parser.add_argument("--output", help="Output file path (for PDF)")
    parser.add_argument("--audience", choices=["developer", "business"], default="developer",
                        help="Report audience: developer (technical) or business (plain language)")
    parser.add_argument("--save", action="store_true", help="Save to file")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    if args.input:
        from pathlib import Path
        data = json.loads(Path(args.input).read_text())
    else:
        data = {"brand": args.brand, "three_o_score": {"score": 0, "grade": "N/A", "pillars": {}}}

    output_format = "json" if args.json else args.format

    if output_format == "pdf":
        from report_pdf import generate_pdf_report
        output_path = generate_pdf_report(data, args.output if hasattr(args, "output") else None, args.audience)
        print(f"PDF report saved: {output_path}")
        return

    report = generate_report(data, args.type, output_format)

    if args.save:
        filepath = save_report(report, args.brand, args.type, output_format)
        print(f"Report saved: {filepath}")
    elif args.json or output_format == "json":
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(report.get("content", ""))


if __name__ == "__main__":
    main()

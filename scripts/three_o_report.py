"""Unified report generation script for Three-O platform."""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Optional

from score_calculator import compute_three_o_score


REPORT_SECTIONS = {
    "full": ["executive_summary", "score_dashboard", "seo", "geo", "aao", "competitor", "action_plan"],
    "seo": ["executive_summary", "seo"],
    "geo": ["executive_summary", "geo"],
    "aao": ["executive_summary", "aao"],
}


def generate_executive_summary(data: dict) -> str:
    """Generate executive summary section."""
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

    top_issues = data.get("top_issues", [])
    if top_issues:
        lines.append("### Top Priority Actions")
        lines.append("")
        for i, issue in enumerate(top_issues[:3], 1):
            lines.append(f"{i}. **[{issue.get('severity', '').upper()}]** {issue.get('message', '')}")
        lines.append("")

    return "\n".join(lines)


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

    if "action_plan" in sections:
        content_parts.append(generate_action_plan(data))

    content_parts.append(f"\n---\n*Report generated by Three-O v1.0.0 | {datetime.now().strftime('%Y-%m-%d')}*\n")

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
        output_path = generate_pdf_report(data, args.output if hasattr(args, "output") else None)
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

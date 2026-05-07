"""Actionable recommendation engine for Three-O platform.

Generates prioritized, industry-aware recommendations based on audit data,
signal correlations, and score patterns. Recommendations include estimated
effort, expected impact, and specific implementation steps.
"""

import json
import sys
from typing import Optional


EFFORT_LEVELS = {"low": "< 1 hour", "medium": "1-4 hours", "high": "1-2 days", "major": "1+ week"}
IMPACT_LEVELS = {"low": "+2-5 pts", "medium": "+5-10 pts", "high": "+10-20 pts", "critical": "+15-30 pts"}

RECOMMENDATION_CATALOG = {
    "seo": {
        "add_meta_description": {
            "condition": lambda d: "Missing meta description" in str(d.get("issues", [])),
            "title": "Add meta description (120-160 chars)",
            "detail": "Write a compelling description that summarizes the page content. Include primary keyword naturally.",
            "effort": "low",
            "impact": "medium",
        },
        "fix_title_length": {
            "condition": lambda d: "Title length" in str(d.get("issues", [])),
            "title": "Optimize title tag length to 30-60 characters",
            "detail": "Shorten or expand the title to fit SERP display. Front-load the primary keyword.",
            "effort": "low",
            "impact": "medium",
        },
        "add_canonical": {
            "condition": lambda d: "Missing canonical" in str(d.get("issues", [])),
            "title": "Add canonical URL tag",
            "detail": "Set <link rel='canonical'> with absolute HTTPS URL to prevent duplicate content issues.",
            "effort": "low",
            "impact": "low",
        },
        "fix_heading_hierarchy": {
            "condition": lambda d: "H1" in str(d.get("issues", [])) or "heading" in str(d.get("issues", [])).lower(),
            "title": "Fix heading hierarchy (single H1, proper H2-H3 nesting)",
            "detail": "Ensure exactly one H1 that matches the page topic. Use H2 for sections, H3 for subsections.",
            "effort": "low",
            "impact": "low",
        },
        "add_hsts": {
            "condition": lambda d: "HSTS" in str(d.get("issues", [])),
            "title": "Enable HSTS header",
            "detail": "Add Strict-Transport-Security header to force HTTPS. Set max-age to at least 31536000.",
            "effort": "medium",
            "impact": "low",
        },
        "add_viewport": {
            "condition": lambda d: "viewport" in str(d.get("issues", [])).lower(),
            "title": "Add viewport meta tag for mobile",
            "detail": "Add <meta name='viewport' content='width=device-width, initial-scale=1'>",
            "effort": "low",
            "impact": "high",
        },
        "improve_images": {
            "condition": lambda d: "images missing alt" in str(d.get("issues", [])).lower(),
            "title": "Add alt text to all images",
            "detail": "Write descriptive alt text for every content image. Decorative images get alt=''.",
            "effort": "medium",
            "impact": "low",
        },
    },
    "geo": {
        "add_definition_sentences": {
            "condition": lambda d: d.get("score", 100) < 60,
            "title": "Add definition-style sentences for AI citation",
            "detail": "Write clear 'X is Y' sentences in opening paragraphs. AI models cite these most frequently.",
            "effort": "medium",
            "impact": "high",
        },
        "improve_data_density": {
            "condition": lambda d: "factual density" in str(d.get("issues", [])).lower() or d.get("dimensions", {}).get("factual_density", {}).get("score", 100) < 50,
            "title": "Increase factual density with specific numbers and data",
            "detail": "Add statistics, dates, specific metrics. Perplexity and Claude strongly favor data-backed claims.",
            "effort": "medium",
            "impact": "high",
        },
        "add_source_attribution": {
            "condition": lambda d: d.get("score", 100) < 55,
            "title": "Add source attributions and references",
            "detail": "Cite specific studies, reports, or official sources. Perplexity weights sourced content 1.4x.",
            "effort": "medium",
            "impact": "medium",
        },
        "improve_content_structure": {
            "condition": lambda d: "structure" in str(d.get("issues", [])).lower(),
            "title": "Improve content structure with headings and lists",
            "detail": "Add H2/H3 hierarchy, bulleted lists, tables. ChatGPT favors well-structured content for citation.",
            "effort": "medium",
            "impact": "medium",
        },
        "add_eeat_signals": {
            "condition": lambda d: d.get("platforms", {}).get("gemini", {}).get("score", 100) < 50,
            "title": "Strengthen E-E-A-T signals for Gemini",
            "detail": "Add author credentials, publication dates, expert citations, certifications. Gemini weights E-E-A-T heavily.",
            "effort": "high",
            "impact": "high",
        },
        "add_llms_txt": {
            "condition": lambda d: True,
            "title": "Create and publish llms.txt file",
            "detail": "Add /llms.txt with brand summary, key facts, and preferred citation format for AI crawlers.",
            "effort": "low",
            "impact": "medium",
        },
    },
    "aao": {
        "add_json_ld": {
            "condition": lambda d: d.get("dimensions", {}).get("structured_data", {}).get("score", 100) < 30,
            "title": "Add JSON-LD structured data with business entity",
            "detail": "Add Schema.org markup matching your business type (LocalBusiness, Product, Service). Include name, address, hours, pricing.",
            "effort": "medium",
            "impact": "critical",
        },
        "add_schema_actions": {
            "condition": lambda d: d.get("dimensions", {}).get("api_booking", {}).get("score", 100) < 40,
            "title": "Add Schema.org potentialAction for agent execution",
            "detail": "Define OrderAction, ReserveAction, or SearchAction in schema so AI agents can trigger actions programmatically.",
            "effort": "high",
            "impact": "high",
        },
        "collect_reviews": {
            "condition": lambda d: d.get("dimensions", {}).get("reviews_ratings", {}).get("score", 100) < 30,
            "title": "Implement review collection and schema markup",
            "detail": "Add AggregateRating and individual Review schema. Aim for 30+ reviews with 4.0+ rating for agent selection.",
            "effort": "major",
            "impact": "high",
        },
        "complete_business_info": {
            "condition": lambda d: d.get("dimensions", {}).get("info_completeness", {}).get("score", 100) < 50,
            "title": "Complete all business information fields",
            "detail": "Ensure all 8 fields are present: name, description, address, phone, hours, pricing, images, category.",
            "effort": "medium",
            "impact": "medium",
        },
        "add_trust_signals": {
            "condition": lambda d: d.get("dimensions", {}).get("trust_signals", {}).get("score", 100) < 40,
            "title": "Add trust signals (certifications, business registration, legal pages)",
            "detail": "Display business registration number, add privacy policy/terms, mention certifications and awards with dates.",
            "effort": "medium",
            "impact": "medium",
        },
        "improve_freshness": {
            "condition": lambda d: d.get("dimensions", {}).get("freshness", {}).get("score", 100) < 40,
            "title": "Add freshness indicators (dates, last-modified, dynamic content)",
            "detail": "Show recent dates, add dateModified metadata, display real-time availability or stock. Signals active business.",
            "effort": "low",
            "impact": "low",
        },
    },
}

INDUSTRY_RECOMMENDATIONS = {
    "restaurant": [
        {"title": "Add Menu schema with prices", "detail": "Use Schema.org Menu type with MenuItem and price. AI agents use this for recommendation and comparison.", "effort": "medium", "impact": "high"},
        {"title": "Enable online reservation (Naver/Kakao)", "detail": "Connect booking API so agents can make reservations. Add ReserveAction to schema.", "effort": "high", "impact": "critical"},
        {"title": "Optimize for Naver Place", "detail": "Ensure NAP consistency, add food category keywords, upload high-quality food photos.", "effort": "medium", "impact": "high"},
    ],
    "ecommerce": [
        {"title": "Add Product schema with offers", "detail": "Include price, availability, condition, brand. AI shopping agents use this directly.", "effort": "medium", "impact": "critical"},
        {"title": "Implement product feed (Naver EP / Google Merchant)", "detail": "Structured product feed enables AI comparison shopping and direct linking.", "effort": "high", "impact": "high"},
        {"title": "Add purchase flow CTAs", "detail": "Clear add-to-cart, buy-now buttons that agents can identify. Include OrderAction schema.", "effort": "low", "impact": "medium"},
    ],
    "clinic": [
        {"title": "Add MedicalBusiness schema", "detail": "Include specialties, physicians, accepted insurance, opening hours. Critical for health AI agents.", "effort": "medium", "impact": "critical"},
        {"title": "Build trust with credentials", "detail": "Display doctor profiles, certifications, hospital affiliations, years of experience.", "effort": "medium", "impact": "high"},
        {"title": "Add appointment booking schema", "detail": "ReserveAction with available slots. Health agents prioritize bookable clinics.", "effort": "high", "impact": "high"},
    ],
    "hotel": [
        {"title": "Add Hotel/LodgingBusiness schema", "detail": "Include room types, amenities, check-in/out times, star rating. Travel agents parse this directly.", "effort": "medium", "impact": "critical"},
        {"title": "Enable real-time availability", "detail": "Show live room availability and pricing. Booking agents strongly prefer real-time data.", "effort": "major", "impact": "high"},
    ],
    "education": [
        {"title": "Add Course schema", "detail": "Include course name, description, instructor, duration, price. Education agents use this for matching.", "effort": "medium", "impact": "high"},
        {"title": "Add instructor credentials", "detail": "Display teacher qualifications, experience, certifications. E-E-A-T signals critical for education.", "effort": "medium", "impact": "medium"},
    ],
    "saas": [
        {"title": "Add SoftwareApplication schema", "detail": "Include pricing plans, features, operating system, ratings. B2B agents compare on structured specs.", "effort": "medium", "impact": "high"},
        {"title": "Publish API documentation", "detail": "Expose integration capabilities. Agent platforms favor SaaS with documented APIs.", "effort": "high", "impact": "medium"},
    ],
}


def generate_recommendations(audit_data: dict, max_items: int = 10) -> dict:
    """Generate prioritized recommendations from audit data."""
    recommendations = []

    for pillar in ["seo", "geo", "aao"]:
        pillar_data = audit_data.get(pillar, {})
        if not pillar_data:
            continue

        catalog = RECOMMENDATION_CATALOG.get(pillar, {})
        for rec_id, rec in catalog.items():
            try:
                if rec["condition"](pillar_data):
                    recommendations.append({
                        "id": f"{pillar}_{rec_id}",
                        "pillar": pillar.upper(),
                        "title": rec["title"],
                        "detail": rec["detail"],
                        "effort": rec["effort"],
                        "effort_estimate": EFFORT_LEVELS[rec["effort"]],
                        "impact": rec["impact"],
                        "impact_estimate": IMPACT_LEVELS[rec["impact"]],
                    })
            except (KeyError, TypeError):
                continue

    industry = audit_data.get("aao", {}).get("industry_detected", "general")
    if industry in INDUSTRY_RECOMMENDATIONS:
        for rec in INDUSTRY_RECOMMENDATIONS[industry]:
            recommendations.append({
                "id": f"industry_{industry}_{rec['title'][:20].replace(' ', '_').lower()}",
                "pillar": "INDUSTRY",
                "title": f"[{industry.title()}] {rec['title']}",
                "detail": rec["detail"],
                "effort": rec["effort"],
                "effort_estimate": EFFORT_LEVELS[rec["effort"]],
                "impact": rec["impact"],
                "impact_estimate": IMPACT_LEVELS[rec["impact"]],
            })

    impact_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    effort_order = {"low": 0, "medium": 1, "high": 2, "major": 3}
    recommendations.sort(key=lambda r: (impact_order.get(r["impact"], 9), effort_order.get(r["effort"], 9)))

    quick_wins = [r for r in recommendations if r["effort"] in ["low", "medium"] and r["impact"] in ["high", "critical"]]
    strategic = [r for r in recommendations if r["effort"] in ["high", "major"] and r["impact"] in ["high", "critical"]]
    maintenance = [r for r in recommendations if r not in quick_wins and r not in strategic]

    return {
        "success": True,
        "industry": industry,
        "total": len(recommendations),
        "recommendations": recommendations[:max_items],
        "quick_wins": quick_wins[:5],
        "strategic": strategic[:5],
        "maintenance": maintenance[:5],
    }


def format_recommendations_md(rec_data: dict) -> str:
    """Format recommendations as markdown."""
    lines = ["## Recommendations", ""]

    if rec_data.get("quick_wins"):
        lines.append("### Quick Wins (High impact, Low effort)")
        lines.append("")
        for i, r in enumerate(rec_data["quick_wins"], 1):
            lines.append(f"**{i}. {r['title']}**")
            lines.append(f"   {r['detail']}")
            lines.append(f"   Effort: {r['effort_estimate']} | Impact: {r['impact_estimate']}")
            lines.append("")

    if rec_data.get("strategic"):
        lines.append("### Strategic Investments (High impact, Higher effort)")
        lines.append("")
        for i, r in enumerate(rec_data["strategic"], 1):
            lines.append(f"**{i}. {r['title']}**")
            lines.append(f"   {r['detail']}")
            lines.append(f"   Effort: {r['effort_estimate']} | Impact: {r['impact_estimate']}")
            lines.append("")

    if rec_data.get("maintenance"):
        lines.append("### Maintenance & Polish")
        lines.append("")
        for i, r in enumerate(rec_data["maintenance"][:3], 1):
            lines.append(f"{i}. {r['title']} ({r['effort_estimate']})")
        lines.append("")

    return "\n".join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Three-O recommendation engine")
    parser.add_argument("--input", required=True, help="Audit data JSON file")
    parser.add_argument("--max", type=int, default=10, help="Max recommendations")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    from pathlib import Path
    data = json.loads(Path(args.input).read_text())
    result = generate_recommendations(data, args.max)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(format_recommendations_md(result))


if __name__ == "__main__":
    main()

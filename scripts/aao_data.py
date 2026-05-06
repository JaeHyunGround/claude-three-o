"""Structured data push analysis script for Three-O platform."""

import argparse
import json
import re
import sys

from validate_url import validate_url
from fetch_page import fetch_page


AGENT_REQUIRED_FIELDS = {
    "LocalBusiness": ["name", "address", "telephone", "openingHoursSpecification",
                      "geo", "url", "image", "priceRange"],
    "Restaurant": ["name", "address", "telephone", "openingHoursSpecification",
                   "geo", "url", "image", "servesCuisine", "menu"],
    "Product": ["name", "description", "image", "offers", "sku", "brand"],
    "Service": ["name", "description", "provider", "areaServed", "offers"],
    "Organization": ["name", "url", "logo", "description", "sameAs", "contactPoint"],
    "MedicalBusiness": ["name", "address", "telephone", "medicalSpecialty",
                        "openingHoursSpecification"],
    "EducationalOrganization": ["name", "address", "url", "description"],
}

ACTION_SCHEMAS = {
    "book": "ReserveAction",
    "buy": "BuyAction",
    "order": "OrderAction",
    "search": "SearchAction",
}


def extract_structured_data(html: str) -> list:
    """Extract all JSON-LD blocks from HTML."""
    blocks = re.findall(
        r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
        html, re.DOTALL | re.IGNORECASE
    )

    parsed = []
    for block in blocks:
        try:
            data = json.loads(block.strip())
            if isinstance(data, list):
                parsed.extend(data)
            else:
                parsed.append(data)
        except json.JSONDecodeError:
            continue

    return parsed


def audit_schema_completeness(schemas: list) -> dict:
    """Audit structured data completeness for agent consumption."""
    results = []

    for schema in schemas:
        schema_type = schema.get("@type", "Unknown")
        if isinstance(schema_type, list):
            schema_type = schema_type[0]

        required = AGENT_REQUIRED_FIELDS.get(schema_type, [])
        present = []
        missing = []

        for field in required:
            if schema.get(field):
                present.append(field)
            else:
                missing.append(field)

        completeness = round(len(present) / max(len(required), 1) * 100)

        has_action = False
        if schema.get("potentialAction"):
            has_action = True

        results.append({
            "type": schema_type,
            "completeness": completeness,
            "present_fields": present,
            "missing_fields": missing,
            "has_action": has_action,
            "total_properties": len([k for k in schema.keys() if not k.startswith("@")]),
        })

    return {"schemas": results, "count": len(results)}


def check_microdata(html: str) -> dict:
    """Check for Microdata markup."""
    itemscopes = re.findall(r'itemscope[^>]*itemtype="([^"]*)"', html, re.IGNORECASE)
    return {
        "found": len(itemscopes) > 0,
        "types": itemscopes[:10],
        "count": len(itemscopes),
    }


def check_rdfa(html: str) -> dict:
    """Check for RDFa markup."""
    typeof = re.findall(r'typeof="([^"]*)"', html, re.IGNORECASE)
    return {
        "found": len(typeof) > 0,
        "types": typeof[:10],
        "count": len(typeof),
    }


def check_action_availability(schemas: list) -> dict:
    """Check if Schema.org actions are defined."""
    actions = []
    for schema in schemas:
        potential = schema.get("potentialAction", [])
        if isinstance(potential, dict):
            potential = [potential]
        for action in potential:
            action_type = action.get("@type", "Unknown")
            target = action.get("target", {})
            if isinstance(target, str):
                target = {"urlTemplate": target}
            actions.append({
                "type": action_type,
                "target": target.get("urlTemplate", target.get("url", "")),
            })

    return {
        "has_actions": len(actions) > 0,
        "actions": actions,
        "count": len(actions),
    }


def analyze_structured_data(url: str) -> dict:
    """Full structured data analysis for agent optimization."""
    validation = validate_url(url)
    if not validation["valid"]:
        return {"success": False, "error": validation["error"]}

    result = fetch_page(url)
    if not result["success"]:
        return {"success": False, "error": result["error"]}

    html = result["html"]
    schemas = extract_structured_data(html)
    audit = audit_schema_completeness(schemas)
    microdata = check_microdata(html)
    rdfa = check_rdfa(html)
    actions = check_action_availability(schemas)

    score = 20.0
    issues = []

    if not schemas:
        issues.append({"severity": "critical", "message": "No JSON-LD structured data found"})
    else:
        score += 20
        avg_completeness = sum(s["completeness"] for s in audit["schemas"]) / len(audit["schemas"])
        score += avg_completeness * 0.3

        for s in audit["schemas"]:
            if s["missing_fields"]:
                issues.append({
                    "severity": "medium",
                    "message": f"{s['type']}: missing {', '.join(s['missing_fields'][:3])}",
                })

    if actions["has_actions"]:
        score += 15
    else:
        issues.append({"severity": "medium", "message": "No Schema.org actions defined (ReserveAction, BuyAction, etc.)"})

    if microdata["found"]:
        score += 5
    if rdfa["found"]:
        score += 5

    score = max(0, min(100, round(score, 1)))

    return {
        "success": True,
        "url": url,
        "score": score,
        "json_ld": audit,
        "microdata": microdata,
        "rdfa": rdfa,
        "actions": actions,
        "issues": issues,
    }


def main():
    parser = argparse.ArgumentParser(description="Structured data push analysis for agents")
    parser.add_argument("url", help="URL to analyze")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    result = analyze_structured_data(args.url)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result["success"]:
            print(f"Structured Data Score: {result['score']}/100")
            print(f"JSON-LD: {result['json_ld']['count']} blocks | Microdata: {result['microdata']['count']} | RDFa: {result['rdfa']['count']}")
            if result["json_ld"]["schemas"]:
                print(f"\nSchema Types:")
                for s in result["json_ld"]["schemas"]:
                    print(f"  {s['type']}: {s['completeness']}% complete ({s['total_properties']} properties)")
            if result["actions"]["has_actions"]:
                print(f"\nActions: {result['actions']['count']}")
                for a in result["actions"]["actions"]:
                    print(f"  {a['type']}: {a['target'][:60]}")
            for issue in result["issues"]:
                print(f"  [{issue['severity'].upper()}] {issue['message']}")
        else:
            print(f"Error: {result['error']}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()

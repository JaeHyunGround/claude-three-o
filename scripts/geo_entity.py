"""Knowledge graph entity presence analysis script for Three-O platform."""

import argparse
import json
import re
import sys
from typing import Optional

from validate_url import validate_url
from fetch_page import fetch_page


ENTITY_SOURCES = {
    "google_kp": {"name": "Google Knowledge Panel", "weight": 0.30},
    "wikidata": {"name": "Wikidata", "weight": 0.25},
    "naver": {"name": "Naver Knowledge", "weight": 0.20},
    "schema_org": {"name": "Schema.org (website)", "weight": 0.15},
    "wikipedia": {"name": "Wikipedia", "weight": 0.10},
}

REQUIRED_ATTRIBUTES = ["name", "description", "url", "category", "location", "logo"]


def check_schema_org_entity(html: str) -> dict:
    """Check Organization/LocalBusiness schema on website."""
    ld_json_blocks = re.findall(
        r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
        html, re.DOTALL | re.IGNORECASE
    )

    entity_data = {
        "found": False,
        "type": None,
        "attributes": {},
        "same_as": [],
        "completeness": 0,
    }

    for block in ld_json_blocks:
        try:
            data = json.loads(block.strip())
            if isinstance(data, list):
                data = data[0] if data else {}

            entity_type = data.get("@type", "")
            if entity_type in ["Organization", "LocalBusiness", "Corporation",
                               "Restaurant", "MedicalBusiness", "EducationalOrganization",
                               "Store", "ProfessionalService"]:
                entity_data["found"] = True
                entity_data["type"] = entity_type
                entity_data["attributes"] = {
                    "name": data.get("name"),
                    "description": data.get("description"),
                    "url": data.get("url"),
                    "logo": data.get("logo"),
                    "address": data.get("address"),
                    "telephone": data.get("telephone"),
                }
                entity_data["same_as"] = data.get("sameAs", [])
                if isinstance(entity_data["same_as"], str):
                    entity_data["same_as"] = [entity_data["same_as"]]

                filled = sum(1 for v in entity_data["attributes"].values() if v)
                entity_data["completeness"] = round(filled / len(entity_data["attributes"]) * 100)
                break
        except (json.JSONDecodeError, IndexError, TypeError):
            continue

    return entity_data


def check_same_as_links(same_as_urls: list) -> dict:
    """Analyze sameAs links for cross-platform entity linking."""
    platforms = {
        "wikidata": {"pattern": r"wikidata\.org", "found": False},
        "wikipedia": {"pattern": r"wikipedia\.org", "found": False},
        "linkedin": {"pattern": r"linkedin\.com", "found": False},
        "facebook": {"pattern": r"facebook\.com|fb\.com", "found": False},
        "instagram": {"pattern": r"instagram\.com", "found": False},
        "youtube": {"pattern": r"youtube\.com", "found": False},
        "naver": {"pattern": r"naver\.com", "found": False},
        "twitter": {"pattern": r"twitter\.com|x\.com", "found": False},
    }

    for url in same_as_urls:
        for platform, info in platforms.items():
            if re.search(info["pattern"], url, re.IGNORECASE):
                info["found"] = True
                info["url"] = url

    linked_count = sum(1 for p in platforms.values() if p["found"])
    return {
        "total_links": len(same_as_urls),
        "platforms_linked": linked_count,
        "platforms": {k: {"linked": v["found"], "url": v.get("url")} for k, v in platforms.items()},
    }


def estimate_entity_presence(brand: str, url: Optional[str] = None) -> dict:
    """Estimate entity presence across knowledge sources."""
    source_results = {}

    if url:
        validation = validate_url(url)
        if not validation["valid"]:
            return {"success": False, "error": validation["error"]}

        result = fetch_page(url)
        if result["success"]:
            schema_check = check_schema_org_entity(result["html"])
            source_results["schema_org"] = {
                "status": "found" if schema_check["found"] else "not_found",
                "type": schema_check["type"],
                "completeness": schema_check["completeness"],
                "same_as": schema_check["same_as"],
            }

            same_as_analysis = check_same_as_links(schema_check["same_as"])
            source_results["schema_org"]["linking"] = same_as_analysis

            source_results["wikidata"] = {
                "status": "linked" if same_as_analysis["platforms"].get("wikidata", {}).get("linked") else "check_required",
                "note": "Verify via Wikidata API for full property check",
            }
            source_results["wikipedia"] = {
                "status": "linked" if same_as_analysis["platforms"].get("wikipedia", {}).get("linked") else "check_required",
            }
        else:
            source_results["schema_org"] = {"status": "fetch_failed", "error": result["error"]}

    source_results.setdefault("google_kp", {
        "status": "check_required",
        "note": "Search '[brand]' on Google to verify Knowledge Panel",
    })
    source_results.setdefault("naver", {
        "status": "check_required",
        "note": "Search '[brand]' on Naver to verify entity recognition",
    })
    source_results.setdefault("wikidata", source_results.get("wikidata", {
        "status": "check_required",
        "note": "Search on wikidata.org",
    }))
    source_results.setdefault("wikipedia", source_results.get("wikipedia", {
        "status": "check_required",
    }))

    confirmed = sum(1 for s in source_results.values() if s.get("status") in ["found", "linked"])
    total = len(ENTITY_SOURCES)
    base_score = round((confirmed / total) * 60, 1)

    schema_bonus = 0
    if source_results.get("schema_org", {}).get("status") == "found":
        completeness = source_results["schema_org"].get("completeness", 0)
        schema_bonus = round(completeness * 0.4, 1)

    score = round(min(100, base_score + schema_bonus), 1)

    issues = []
    if source_results.get("schema_org", {}).get("status") != "found":
        issues.append({"severity": "high", "message": "No Organization/LocalBusiness schema found on website"})
    elif source_results["schema_org"].get("completeness", 0) < 60:
        issues.append({"severity": "medium", "message": "Schema.org entity data is incomplete"})

    same_as = source_results.get("schema_org", {}).get("same_as", [])
    if not same_as:
        issues.append({"severity": "high", "message": "No sameAs links — entity not connected across platforms"})
    elif len(same_as) < 3:
        issues.append({"severity": "medium", "message": f"Only {len(same_as)} sameAs links — add more platform connections"})

    if source_results.get("wikidata", {}).get("status") != "linked":
        issues.append({"severity": "medium", "message": "No Wikidata link — create or link entity"})
    if source_results.get("naver", {}).get("status") != "found":
        issues.append({"severity": "medium", "message": "Naver entity status unknown — verify manually"})

    return {
        "success": True,
        "brand": brand,
        "url": url,
        "score": score,
        "sources": source_results,
        "confirmed_sources": confirmed,
        "total_sources": total,
        "issues": issues,
    }


def main():
    parser = argparse.ArgumentParser(description="Knowledge graph entity presence analysis")
    parser.add_argument("brand", help="Brand name")
    parser.add_argument("--url", help="Brand website URL for schema analysis")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    result = estimate_entity_presence(args.brand, args.url)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result["success"]:
            print(f"Entity Presence: {args.brand}")
            print(f"Score: {result['score']}/100")
            print(f"Confirmed Sources: {result['confirmed_sources']}/{result['total_sources']}")
            print(f"\nSource Status:")
            for key, info in result["sources"].items():
                icon = "✓" if info.get("status") in ["found", "linked"] else "?" if info.get("status") == "check_required" else "✗"
                name = ENTITY_SOURCES.get(key, {}).get("name", key)
                print(f"  {icon} {name}: {info.get('status', 'unknown')}")
            for issue in result["issues"]:
                print(f"  [{issue['severity'].upper()}] {issue['message']}")
        else:
            print(f"Error: {result['error']}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()

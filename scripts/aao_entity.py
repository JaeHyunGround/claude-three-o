"""Agent entity consistency analysis script for Three-O platform."""

import argparse
import json
import re
import sys

from validate_url import validate_url
from fetch_page import fetch_page


ENTITY_FIELDS = ["name", "address", "telephone", "url", "description",
                 "category", "image", "openingHours", "priceRange"]


def extract_entity_from_schema(html: str) -> dict:
    """Extract entity information from JSON-LD structured data."""
    blocks = re.findall(
        r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
        html, re.DOTALL | re.IGNORECASE
    )

    for block in blocks:
        try:
            data = json.loads(block.strip())
            if isinstance(data, list):
                data = data[0] if data else {}
            entity_type = data.get("@type", "")
            if isinstance(entity_type, list):
                entity_type = entity_type[0]
            if entity_type in ["Organization", "LocalBusiness", "Restaurant",
                               "Store", "Corporation", "MedicalBusiness",
                               "EducationalOrganization", "ProfessionalService"]:
                return {
                    "source": "json-ld",
                    "type": entity_type,
                    "name": data.get("name"),
                    "address": _flatten_address(data.get("address")),
                    "telephone": data.get("telephone"),
                    "url": data.get("url"),
                    "description": data.get("description"),
                    "image": data.get("image"),
                    "sameAs": data.get("sameAs", []),
                }
        except (json.JSONDecodeError, IndexError, TypeError):
            continue

    return {"source": None}


def _flatten_address(addr) -> str:
    """Flatten PostalAddress to string."""
    if isinstance(addr, str):
        return addr
    if isinstance(addr, dict):
        parts = [addr.get("streetAddress", ""), addr.get("addressLocality", ""),
                 addr.get("addressRegion", ""), addr.get("postalCode", ""),
                 addr.get("addressCountry", "")]
        return " ".join(p for p in parts if p).strip()
    return ""


def extract_entity_from_html(html: str) -> dict:
    """Extract entity signals from HTML meta/content."""
    entity = {"source": "html"}

    title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
    if title_match:
        entity["name"] = title_match.group(1).strip().split(" - ")[0].split(" | ")[0]

    desc_match = re.search(r'name="description"\s+content="([^"]*)"', html, re.IGNORECASE)
    if desc_match:
        entity["description"] = desc_match.group(1)

    og_name = re.search(r'property="og:site_name"\s+content="([^"]*)"', html, re.IGNORECASE)
    if og_name:
        entity["og_name"] = og_name.group(1)

    tel_match = re.search(r'href="tel:([^"]+)"', html)
    if tel_match:
        entity["telephone"] = tel_match.group(1)

    canonical = re.search(r'rel="canonical"\s+href="([^"]*)"', html, re.IGNORECASE)
    if canonical:
        entity["url"] = canonical.group(1)

    return entity


def check_nap_consistency(schema_entity: dict, html_entity: dict) -> dict:
    """Check Name, Address, Phone consistency across sources."""
    checks = {}

    schema_name = (schema_entity.get("name") or "").strip().lower()
    html_name = (html_entity.get("name") or "").strip().lower()
    og_name = (html_entity.get("og_name") or "").strip().lower()

    names = [n for n in [schema_name, html_name, og_name] if n]
    if len(names) >= 2:
        all_match = len(set(names)) == 1
        checks["name"] = {
            "consistent": all_match,
            "values": {"schema": schema_name, "title": html_name, "og": og_name},
        }
    elif names:
        checks["name"] = {"consistent": True, "values": {"found": names[0]}}
    else:
        checks["name"] = {"consistent": False, "values": {}, "missing": True}

    schema_tel = (schema_entity.get("telephone") or "").replace("-", "").replace(" ", "")
    html_tel = (html_entity.get("telephone") or "").replace("-", "").replace(" ", "")

    if schema_tel and html_tel:
        checks["phone"] = {
            "consistent": schema_tel == html_tel,
            "values": {"schema": schema_entity.get("telephone"), "html": html_entity.get("telephone")},
        }
    elif schema_tel or html_tel:
        checks["phone"] = {"consistent": True, "values": {"found": schema_tel or html_tel}}
    else:
        checks["phone"] = {"consistent": False, "missing": True}

    schema_url = (schema_entity.get("url") or "").rstrip("/")
    html_url = (html_entity.get("url") or "").rstrip("/")

    if schema_url and html_url:
        checks["url"] = {
            "consistent": schema_url == html_url,
            "values": {"schema": schema_url, "canonical": html_url},
        }

    consistent_count = sum(1 for c in checks.values() if c.get("consistent"))
    total = len(checks)

    return {
        "checks": checks,
        "consistent_count": consistent_count,
        "total_checks": total,
        "consistency_rate": round(consistent_count / max(total, 1) * 100),
    }


def analyze_entity_consistency(url: str) -> dict:
    """Full entity consistency analysis."""
    validation = validate_url(url)
    if not validation["valid"]:
        return {"success": False, "error": validation["error"]}

    result = fetch_page(url)
    if not result["success"]:
        return {"success": False, "error": result["error"]}

    html = result["html"]
    schema_entity = extract_entity_from_schema(html)
    html_entity = extract_entity_from_html(html)

    nap = check_nap_consistency(schema_entity, html_entity)

    same_as = schema_entity.get("sameAs", [])
    if isinstance(same_as, str):
        same_as = [same_as]

    score = 20.0
    issues = []

    if schema_entity.get("source") == "json-ld":
        score += 25
        filled = sum(1 for f in ENTITY_FIELDS if schema_entity.get(f))
        score += (filled / len(ENTITY_FIELDS)) * 25
    else:
        issues.append({"severity": "high", "message": "No entity schema (Organization/LocalBusiness) found"})

    score += nap["consistency_rate"] * 0.2

    if same_as:
        score += min(10, len(same_as) * 2)
    else:
        issues.append({"severity": "medium", "message": "No sameAs links for cross-platform entity linking"})

    for check_name, check_data in nap["checks"].items():
        if check_data.get("missing"):
            issues.append({"severity": "medium", "message": f"{check_name.title()} not found in any source"})
        elif not check_data.get("consistent"):
            issues.append({"severity": "high", "message": f"Inconsistent {check_name} across sources"})

    score = max(0, min(100, round(score, 1)))

    return {
        "success": True,
        "url": url,
        "score": score,
        "schema_entity": schema_entity,
        "nap_consistency": nap,
        "same_as_links": same_as,
        "issues": issues,
    }


def main():
    parser = argparse.ArgumentParser(description="Agent entity consistency analysis")
    parser.add_argument("url", help="URL to analyze")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    result = analyze_entity_consistency(args.url)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result["success"]:
            print(f"Entity Consistency Score: {result['score']}/100")
            nap = result["nap_consistency"]
            print(f"NAP Consistency: {nap['consistency_rate']}% ({nap['consistent_count']}/{nap['total_checks']})")
            print(f"sameAs Links: {len(result['same_as_links'])}")
            if result["schema_entity"].get("type"):
                print(f"Schema Type: {result['schema_entity']['type']}")
            for issue in result["issues"]:
                print(f"  [{issue['severity'].upper()}] {issue['message']}")
        else:
            print(f"Error: {result['error']}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()

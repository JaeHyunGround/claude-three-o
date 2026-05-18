"""Knowledge graph entity presence analysis script for Three-O platform.

Scores entity presence across four dimensions:
- Schema Presence: Organization/LocalBusiness schema with type-aware attribute scoring
- Connection Strength: sameAs link quality with tiered platform weighting
- Attribute Completeness: per-entity-type required/optional field coverage
- Disambiguation: unique identifiers, qualifiers, and entity clarity signals
"""

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

ENTITY_WEIGHTS = {
    "schema_presence": 0.30,
    "connection_strength": 0.25,
    "attribute_completeness": 0.25,
    "disambiguation": 0.20,
}

PLATFORM_TIERS = {
    "tier1_knowledge": {
        "wikidata": r"wikidata\.org",
        "wikipedia": r"wikipedia\.org",
        "dbpedia": r"dbpedia\.org",
    },
    "tier2_authority": {
        "linkedin": r"linkedin\.com",
        "crunchbase": r"crunchbase\.com",
        "google_business": r"business\.google\.com|g\.co",
        "naver_place": r"naver\.com/(?:my)?place|map\.naver\.com",
        "naver_blog": r"blog\.naver\.com",
    },
    "tier3_social": {
        "facebook": r"facebook\.com|fb\.com",
        "instagram": r"instagram\.com",
        "youtube": r"youtube\.com",
        "twitter": r"twitter\.com|x\.com",
        "tiktok": r"tiktok\.com",
        "github": r"github\.com",
    },
}

ENTITY_TYPES = [
    "Organization", "LocalBusiness", "Corporation", "Restaurant",
    "MedicalBusiness", "EducationalOrganization", "Store",
    "ProfessionalService", "Hotel", "SportsOrganization",
    "GovernmentOrganization", "NGO",
]

CORE_ATTRIBUTES = ["name", "description", "url"]

TYPE_ATTRIBUTES = {
    "Organization": ["logo", "address", "telephone", "email", "foundingDate", "founder", "numberOfEmployees"],
    "LocalBusiness": ["logo", "address", "telephone", "openingHours", "priceRange", "geo", "areaServed"],
    "Corporation": ["logo", "address", "telephone", "foundingDate", "founder", "tickerSymbol", "numberOfEmployees"],
    "Restaurant": ["logo", "address", "telephone", "openingHours", "priceRange", "servesCuisine", "menu", "acceptsReservations"],
    "MedicalBusiness": ["logo", "address", "telephone", "openingHours", "medicalSpecialty", "availableService"],
    "EducationalOrganization": ["logo", "address", "telephone", "email", "foundingDate"],
    "Store": ["logo", "address", "telephone", "openingHours", "priceRange", "paymentAccepted"],
    "ProfessionalService": ["logo", "address", "telephone", "openingHours", "areaServed", "priceRange"],
    "Hotel": ["logo", "address", "telephone", "checkinTime", "checkoutTime", "starRating", "priceRange", "amenityFeature"],
}

DEFAULT_TYPE_ATTRIBUTES = ["logo", "address", "telephone"]


def extract_text_content(html: str) -> str:
    """Strip HTML tags and extract text content."""
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_ld_json(html: str) -> list:
    """Extract all JSON-LD blocks from HTML."""
    blocks = re.findall(
        r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
        html, re.DOTALL | re.IGNORECASE
    )
    results = []
    for block in blocks:
        try:
            data = json.loads(block.strip())
            if isinstance(data, list):
                results.extend(data)
            elif isinstance(data, dict):
                graph = data.get("@graph", [])
                if graph:
                    results.extend(graph)
                else:
                    results.append(data)
        except (json.JSONDecodeError, TypeError):
            continue
    return results


def find_entity_schema(ld_items: list) -> Optional[dict]:
    """Find the primary entity schema from JSON-LD items."""
    for item in ld_items:
        entity_type = item.get("@type", "")
        if isinstance(entity_type, list):
            entity_type = entity_type[0] if entity_type else ""
        if entity_type in ENTITY_TYPES:
            return item
    return None


def score_schema_presence(html: str) -> dict:
    """Score the presence and quality of entity schema markup."""
    ld_items = extract_ld_json(html)
    entity = find_entity_schema(ld_items)

    if not entity:
        return {
            "score": 0.0,
            "found": False,
            "type": None,
            "attributes": {},
            "same_as": [],
            "raw_data": {},
        }

    entity_type = entity.get("@type", "")
    if isinstance(entity_type, list):
        entity_type = entity_type[0]

    attrs = {}
    all_keys = set(CORE_ATTRIBUTES + TYPE_ATTRIBUTES.get(entity_type, DEFAULT_TYPE_ATTRIBUTES))
    for key in all_keys:
        val = entity.get(key)
        if val and val != "" and val != []:
            if isinstance(val, dict):
                attrs[key] = "structured"
            elif isinstance(val, list):
                attrs[key] = f"{len(val)} items"
            else:
                attrs[key] = str(val)[:80]
        else:
            attrs[key] = None

    same_as = entity.get("sameAs", [])
    if isinstance(same_as, str):
        same_as = [same_as]

    filled = sum(1 for v in attrs.values() if v is not None)
    total = len(attrs)
    completeness = round(filled / max(total, 1) * 100)

    score = 20.0
    score += min(30, completeness * 0.3)

    if entity_type in ENTITY_TYPES[:4]:
        score += 10
    elif entity_type in ENTITY_TYPES:
        score += 5

    if same_as:
        score += min(20, len(same_as) * 5)

    if entity.get("@id"):
        score += 10

    has_nested = any(isinstance(entity.get(k), dict) for k in ["address", "geo", "founder", "logo"])
    if has_nested:
        score += 10

    return {
        "score": round(min(100.0, score), 1),
        "found": True,
        "type": entity_type,
        "attributes": attrs,
        "same_as": same_as,
        "completeness": completeness,
        "has_id": bool(entity.get("@id")),
        "has_nested_objects": has_nested,
        "raw_data": entity,
    }


def score_connection_strength(same_as_urls: list) -> dict:
    """Score entity connection strength across platforms with tiered weighting."""
    tier_results = {}
    all_platforms = {}

    for tier_name, platforms in PLATFORM_TIERS.items():
        tier_results[tier_name] = {"linked": 0, "total": len(platforms), "platforms": {}}
        for platform, pattern in platforms.items():
            found = False
            matched_url = None
            for url in same_as_urls:
                if re.search(pattern, url, re.IGNORECASE):
                    found = True
                    matched_url = url
                    break
            tier_results[tier_name]["platforms"][platform] = {
                "linked": found,
                "url": matched_url,
            }
            all_platforms[platform] = {"linked": found, "url": matched_url, "tier": tier_name}
            if found:
                tier_results[tier_name]["linked"] += 1

    score = 10.0

    t1 = tier_results["tier1_knowledge"]
    score += min(35, t1["linked"] * 18)

    t2 = tier_results["tier2_authority"]
    score += min(25, t2["linked"] * 8)

    t3 = tier_results["tier3_social"]
    score += min(20, t3["linked"] * 5)

    total_linked = sum(1 for p in all_platforms.values() if p["linked"])
    if total_linked >= 5:
        score += 10

    url_quality_issues = []
    for url in same_as_urls:
        if not url.startswith("https://"):
            url_quality_issues.append(f"Non-HTTPS sameAs: {url[:60]}")

    unrecognized = []
    for url in same_as_urls:
        recognized = False
        for platforms in PLATFORM_TIERS.values():
            for pattern in platforms.values():
                if re.search(pattern, url, re.IGNORECASE):
                    recognized = True
                    break
            if recognized:
                break
        if not recognized:
            unrecognized.append(url)

    return {
        "score": round(min(100.0, score), 1),
        "total_links": len(same_as_urls),
        "total_linked_platforms": total_linked,
        "tiers": tier_results,
        "platforms": all_platforms,
        "url_quality_issues": url_quality_issues,
        "unrecognized_urls": unrecognized,
    }


def score_attribute_completeness(entity_data: dict, html: str) -> dict:
    """Score entity attribute completeness with quality assessment."""
    if not entity_data.get("found"):
        text = extract_text_content(html)
        fallback = _detect_attributes_from_html(html, text)
        fallback_filled = sum(1 for v in fallback.values() if v)
        return {
            "score": round(min(30.0, fallback_filled * 5), 1),
            "source": "html_fallback",
            "schema_attributes": {},
            "html_attributes": fallback,
            "missing_critical": list(CORE_ATTRIBUTES),
            "quality_notes": [],
        }

    entity_type = entity_data.get("type", "Organization")
    required = CORE_ATTRIBUTES.copy()
    type_attrs = TYPE_ATTRIBUTES.get(entity_type, DEFAULT_TYPE_ATTRIBUTES)
    all_expected = required + type_attrs

    attrs = entity_data.get("attributes", {})
    raw = entity_data.get("raw_data", {})

    filled_required = sum(1 for a in required if attrs.get(a) is not None)
    filled_type = sum(1 for a in type_attrs if attrs.get(a) is not None)
    total_filled = filled_required + filled_type

    score = 15.0

    score += min(35, (filled_required / max(len(required), 1)) * 35)
    score += min(30, (filled_type / max(len(type_attrs), 1)) * 30)

    quality_notes = []

    name = raw.get("name", "")
    if name and len(name) < 2:
        quality_notes.append("Entity name too short")
    elif name and len(name) > 100:
        quality_notes.append("Entity name too long")

    desc = raw.get("description", "")
    if desc and len(desc) < 20:
        quality_notes.append("Description too short (< 20 chars)")
        score -= 5
    elif desc and len(desc) >= 50:
        score += 5

    addr = raw.get("address")
    if isinstance(addr, dict) and addr.get("streetAddress") and addr.get("addressLocality"):
        score += 5
        quality_notes.append("Structured address (good)")
    elif isinstance(addr, str) and len(addr) > 10:
        quality_notes.append("Address is string — structured PostalAddress preferred")

    if raw.get("geo") and isinstance(raw.get("geo"), dict):
        score += 5
        quality_notes.append("GeoCoordinates present (good)")

    missing_critical = [a for a in required if attrs.get(a) is None]
    missing_type = [a for a in type_attrs if attrs.get(a) is None]

    text = extract_text_content(html)
    html_attrs = _detect_attributes_from_html(html, text)

    recoverable = [a for a in missing_type if html_attrs.get(a)]
    if recoverable:
        score += min(5, len(recoverable) * 2)

    return {
        "score": round(min(100.0, score), 1),
        "source": "schema",
        "entity_type": entity_type,
        "expected_attributes": all_expected,
        "filled": total_filled,
        "total": len(all_expected),
        "schema_attributes": {k: v for k, v in attrs.items() if v is not None},
        "html_attributes": html_attrs,
        "missing_critical": missing_critical,
        "missing_type_specific": missing_type,
        "recoverable_from_html": recoverable,
        "quality_notes": quality_notes,
    }


def _detect_attributes_from_html(html: str, text: str) -> dict:
    """Detect entity attributes from raw HTML when schema is missing."""
    attrs = {}

    phone = re.search(r'(?:tel:|href="tel:)([0-9\-+() ]{8,})', html)
    if not phone:
        phone = re.search(r'(\d{2,4}[-.)]\d{3,4}[-.)]\d{4})', text)
    attrs["telephone"] = bool(phone)

    email = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
    attrs["email"] = bool(email)

    addr_ko = re.search(
        r'(?:서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주)',
        text
    )
    addr_en = re.search(r'(?:address|주소)', html, re.IGNORECASE)
    attrs["address"] = bool(addr_ko or addr_en)

    hours = re.search(r'(?:영업시간|운영시간|진료시간|open|hours)', html, re.IGNORECASE)
    attrs["openingHours"] = bool(hours)

    logo = re.search(r'<(?:img|link)[^>]*(?:logo|brand|symbol)', html, re.IGNORECASE)
    attrs["logo"] = bool(logo)

    name_tag = re.search(r'<(?:title|h1)[^>]*>([^<]+)', html, re.IGNORECASE)
    attrs["name"] = bool(name_tag)

    desc_meta = re.search(r'<meta[^>]*name="description"[^>]*content="([^"]+)"', html, re.IGNORECASE)
    attrs["description"] = bool(desc_meta)

    return attrs


def score_disambiguation(brand: str, html: str) -> dict:
    """Score entity disambiguation clarity."""
    text = extract_text_content(html)
    score = 15.0
    signals = {}

    brand_lower = brand.lower()
    brand_mentions = len(re.findall(re.escape(brand_lower), text.lower()))
    signals["brand_mentions"] = min(brand_mentions, 30)
    if brand_mentions >= 5:
        score += 10
    elif brand_mentions >= 2:
        score += 5

    reg_patterns = [
        r'사업자\s*(?:등록\s*)?번호\s*[:：]?\s*[\d\-]+',
        r'business\s*(?:registration)?\s*(?:no|number)\s*[:：]?\s*[\d\-]+',
        r'법인\s*등록\s*번호',
    ]
    has_registration = any(re.search(p, text, re.IGNORECASE) for p in reg_patterns)
    signals["business_registration"] = has_registration
    if has_registration:
        score += 12

    founder_patterns = [
        r'(?:대표|대표자|CEO|창업자|설립자)\s*[:：]?\s*\S+',
        r'(?:founded by|CEO|founder)\s*[:：]?\s*\S+',
    ]
    has_founder = any(re.search(p, text, re.IGNORECASE) for p in founder_patterns)
    signals["founder_ceo"] = has_founder
    if has_founder:
        score += 8

    year_patterns = [
        r'(?:설립|창립|개업|since)\s*[:：]?\s*(?:19|20)\d{2}',
        r'(?:founded|established|since)\s*[:：]?\s*(?:19|20)\d{2}',
    ]
    has_founding = any(re.search(p, text, re.IGNORECASE) for p in year_patterns)
    signals["founding_year"] = has_founding
    if has_founding:
        score += 8

    industry_patterns = [
        r'(?:업종|업태|산업|분야)\s*[:：]?\s*\S+',
        r'(?:industry|sector|field)\s*[:：]?\s*\S+',
    ]
    has_industry = any(re.search(p, text, re.IGNORECASE) for p in industry_patterns)
    signals["industry_qualifier"] = has_industry
    if has_industry:
        score += 8

    location_qualifier = bool(re.search(
        r'(?:서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|제주)',
        text
    ))
    signals["location_qualifier"] = location_qualifier
    if location_qualifier:
        score += 7

    ld_items = extract_ld_json(html)
    entity = find_entity_schema(ld_items)
    if entity:
        if entity.get("@id"):
            signals["schema_id"] = True
            score += 10
        if entity.get("identifier"):
            signals["schema_identifier"] = True
            score += 8
        if entity.get("legalName"):
            signals["legal_name"] = True
            score += 7
        if entity.get("taxID") or entity.get("vatID"):
            signals["tax_id"] = True
            score += 7

    common_words = {"서비스", "마켓", "shop", "store", "studio", "lab", "tech", "plus", "pro"}
    brand_words = set(brand_lower.split())
    generic_overlap = brand_words & common_words
    signals["has_generic_name_parts"] = len(generic_overlap) > 0
    if generic_overlap:
        score -= 5

    return {
        "score": round(min(100.0, max(0.0, score)), 1),
        "signals": signals,
        "brand": brand,
    }


def analyze_entity_html(html: str, brand: str, url: str = "") -> dict:
    """Run full entity analysis on raw HTML."""
    schema = score_schema_presence(html)
    connection = score_connection_strength(schema["same_as"])
    completeness = score_attribute_completeness(schema, html)
    disambiguation = score_disambiguation(brand, html)

    overall = round(
        schema["score"] * ENTITY_WEIGHTS["schema_presence"]
        + connection["score"] * ENTITY_WEIGHTS["connection_strength"]
        + completeness["score"] * ENTITY_WEIGHTS["attribute_completeness"]
        + disambiguation["score"] * ENTITY_WEIGHTS["disambiguation"],
        1,
    )

    issues = []

    if not schema["found"]:
        issues.append({"severity": "critical", "dimension": "schema_presence",
                        "message": "Organization/LocalBusiness 스키마 없음 — 엔티티 인식 불가"})
    elif schema["completeness"] < 50:
        issues.append({"severity": "high", "dimension": "schema_presence",
                        "message": f"스키마 완성도 {schema['completeness']}% — 50% 이상 권장"})

    if connection["total_links"] == 0:
        issues.append({"severity": "critical", "dimension": "connection_strength",
                        "message": "sameAs 링크 없음 — 플랫폼 간 엔티티 연결 필요"})
    else:
        t1 = connection["tiers"]["tier1_knowledge"]
        if t1["linked"] == 0:
            issues.append({"severity": "high", "dimension": "connection_strength",
                            "message": "Wikidata/Wikipedia 연결 없음 — 지식 그래프 연결 필요"})
        if connection["total_linked_platforms"] < 3:
            issues.append({"severity": "medium", "dimension": "connection_strength",
                            "message": f"연결 플랫폼 {connection['total_linked_platforms']}개 — 3개 이상 권장"})

    if completeness.get("missing_critical"):
        issues.append({"severity": "high", "dimension": "attribute_completeness",
                        "message": f"필수 속성 누락: {', '.join(completeness['missing_critical'])}"})
    if completeness.get("recoverable_from_html"):
        issues.append({"severity": "medium", "dimension": "attribute_completeness",
                        "message": f"HTML에서 복구 가능: {', '.join(completeness['recoverable_from_html'])}"})

    if disambiguation["score"] < 30:
        issues.append({"severity": "high", "dimension": "disambiguation",
                        "message": "엔티티 구별 신호 약함 — 사업자번호, 설립연도, 대표자 추가 권장"})

    issues.sort(key=lambda x: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(x["severity"], 4))

    weakest = min(ENTITY_WEIGHTS, key=lambda k: {
        "schema_presence": schema["score"],
        "connection_strength": connection["score"],
        "attribute_completeness": completeness["score"],
        "disambiguation": disambiguation["score"],
    }[k])

    return {
        "success": True,
        "brand": brand,
        "url": url,
        "score": overall,
        "dimensions": {
            "schema_presence": schema["score"],
            "connection_strength": connection["score"],
            "attribute_completeness": completeness["score"],
            "disambiguation": disambiguation["score"],
        },
        "weakest_dimension": weakest,
        "schema": schema,
        "connection": connection,
        "completeness": completeness,
        "disambiguation": disambiguation,
        "issues": issues,
    }


def estimate_entity_presence(brand: str, url: Optional[str] = None) -> dict:
    """Estimate entity presence across knowledge sources."""

    if url:
        validation = validate_url(url)
        if not validation["valid"]:
            return {"success": False, "error": validation["error"]}

        result = fetch_page(url)
        if result["success"]:
            analysis = analyze_entity_html(result["html"], brand, url)
            analysis["sources"] = _build_source_status(analysis)
            return analysis
        else:
            return {"success": False, "error": result["error"]}

    return {
        "success": True,
        "brand": brand,
        "url": None,
        "score": 0,
        "dimensions": {k: 0 for k in ENTITY_WEIGHTS},
        "issues": [{"severity": "high", "dimension": "schema_presence",
                     "message": "URL 미제공 — 웹사이트 분석 불가"}],
        "sources": {k: {"status": "check_required", "note": f"Search '{brand}' to verify"}
                    for k in ENTITY_SOURCES},
    }


def _build_source_status(analysis: dict) -> dict:
    """Build source status from analysis results for backward compatibility."""
    schema = analysis.get("schema", {})
    connection = analysis.get("connection", {})
    platforms = connection.get("platforms", {})

    sources = {}
    sources["schema_org"] = {
        "status": "found" if schema.get("found") else "not_found",
        "type": schema.get("type"),
        "completeness": schema.get("completeness", 0),
    }
    sources["wikidata"] = {
        "status": "linked" if platforms.get("wikidata", {}).get("linked") else "check_required",
    }
    sources["wikipedia"] = {
        "status": "linked" if platforms.get("wikipedia", {}).get("linked") else "check_required",
    }
    sources["google_kp"] = {"status": "check_required", "note": "Verify via Google Search"}
    sources["naver"] = {"status": "check_required", "note": "Verify via Naver Search"}

    return sources


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
            dims = result.get("dimensions", {})
            if dims:
                print("\nDimensions:")
                print(f"  Schema Presence:        {dims.get('schema_presence', 0):5.1f}/100")
                print(f"  Connection Strength:    {dims.get('connection_strength', 0):5.1f}/100")
                print(f"  Attribute Completeness: {dims.get('attribute_completeness', 0):5.1f}/100")
                print(f"  Disambiguation:         {dims.get('disambiguation', 0):5.1f}/100")
                print(f"  Weakest: {result.get('weakest_dimension', 'N/A')}")
            for issue in result.get("issues", []):
                sev = issue.get("severity", "info")
                print(f"  [{sev.upper()}] {issue['message']}")
        else:
            print(f"Error: {result['error']}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()

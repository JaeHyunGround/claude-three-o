"""Tests for knowledge graph entity presence analysis."""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from geo_entity import (
    extract_ld_json,
    find_entity_schema,
    score_schema_presence,
    score_connection_strength,
    score_attribute_completeness,
    score_disambiguation,
    analyze_entity_html,
    _detect_attributes_from_html,
    _build_source_status,
    ENTITY_WEIGHTS,
    ENTITY_TYPES,
    PLATFORM_TIERS,
    CORE_ATTRIBUTES,
    TYPE_ATTRIBUTES,
)


EMPTY_HTML = "<html><body></body></html>"

MINIMAL_ORG_HTML = """
<html><body>
<script type="application/ld+json">
{"@type": "Organization", "name": "TestCo", "url": "https://testco.com"}
</script>
<h1>TestCo</h1>
</body></html>
"""

RICH_ORG_HTML = """
<html><body>
<script type="application/ld+json">
{
    "@type": "Organization",
    "@id": "https://skyventures.com/#org",
    "name": "Sky Ventures",
    "description": "디지털 마케팅 컨설팅 기업으로 SEO, GEO, AAO 통합 최적화를 제공합니다.",
    "url": "https://skyventures.com",
    "logo": {"@type": "ImageObject", "url": "https://skyventures.com/logo.png"},
    "address": {
        "@type": "PostalAddress",
        "streetAddress": "테헤란로 123",
        "addressLocality": "서울특별시 강남구",
        "postalCode": "06123"
    },
    "telephone": "+82-2-1234-5678",
    "email": "info@skyventures.com",
    "foundingDate": "2020-01-15",
    "founder": {"@type": "Person", "name": "홍길동"},
    "legalName": "스카이벤처스 주식회사",
    "taxID": "123-45-67890",
    "identifier": "BIZ-2020-001",
    "sameAs": [
        "https://www.wikidata.org/wiki/Q12345",
        "https://en.wikipedia.org/wiki/Sky_Ventures",
        "https://www.linkedin.com/company/skyventures",
        "https://www.facebook.com/skyventures",
        "https://www.instagram.com/skyventures",
        "https://www.youtube.com/skyventures",
        "https://blog.naver.com/skyventures"
    ],
    "numberOfEmployees": "50"
}
</script>
<h1>Sky Ventures - 디지털 마케팅 전문 기업</h1>
<p>대표: 홍길동 (CEO)</p>
<p>설립: 2020년</p>
<p>사업자 등록번호: 123-45-67890</p>
<p>서울특별시 강남구 테헤란로 123</p>
<p>업종: 디지털 마케팅</p>
<p>Sky Ventures는 검색엔진 최적화 분야의 선두 기업입니다.</p>
<p>Sky Ventures의 Three-O 시스템은 업계 최고의 솔루션입니다.</p>
</body></html>
"""

RESTAURANT_HTML = """
<html><body>
<script type="application/ld+json">
{
    "@type": "Restaurant",
    "name": "맛있는 식당",
    "description": "한식 전문 레스토랑",
    "url": "https://tasty.kr",
    "address": {"@type": "PostalAddress", "addressLocality": "서울"},
    "telephone": "02-123-4567",
    "openingHours": "Mo-Fr 11:00-22:00",
    "priceRange": "$$",
    "servesCuisine": "한식",
    "menu": "https://tasty.kr/menu",
    "sameAs": ["https://www.instagram.com/tasty"]
}
</script>
<h1>맛있는 식당</h1>
</body></html>
"""

NO_SCHEMA_HTML = """
<html><head>
<meta name="description" content="A business without schema markup">
</head><body>
<h1>TestBrand</h1>
<p>연락처: 02-123-4567</p>
<p>서울특별시 강남구</p>
<p>영업시간: 09:00-18:00</p>
<img src="/images/logo.png" alt="TestBrand Logo">
<p>info@testbrand.com</p>
</body></html>
"""

GRAPH_HTML = """
<html><body>
<script type="application/ld+json">
{
    "@context": "https://schema.org",
    "@graph": [
        {"@type": "WebSite", "name": "Site"},
        {"@type": "Organization", "name": "GraphOrg", "url": "https://graph.org"}
    ]
}
</script>
</body></html>
"""

LIST_SCHEMA_HTML = """
<html><body>
<script type="application/ld+json">
[
    {"@type": "Organization", "name": "ListOrg", "url": "https://list.org"},
    {"@type": "WebPage", "name": "Page"}
]
</script>
</body></html>
"""

GENERIC_NAME_HTML = """
<html><body>
<script type="application/ld+json">
{"@type": "Organization", "name": "Tech Shop Store", "url": "https://techshop.com"}
</script>
<h1>Tech Shop Store</h1>
</body></html>
"""


class TestExtractLdJson(unittest.TestCase):
    def test_single_object(self):
        items = extract_ld_json(MINIMAL_ORG_HTML)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["@type"], "Organization")

    def test_graph_format(self):
        items = extract_ld_json(GRAPH_HTML)
        self.assertEqual(len(items), 2)
        types = [i.get("@type") for i in items]
        self.assertIn("Organization", types)
        self.assertIn("WebSite", types)

    def test_list_format(self):
        items = extract_ld_json(LIST_SCHEMA_HTML)
        self.assertEqual(len(items), 2)

    def test_empty_html(self):
        items = extract_ld_json(EMPTY_HTML)
        self.assertEqual(len(items), 0)

    def test_invalid_json(self):
        html = '<script type="application/ld+json">{invalid json}</script>'
        items = extract_ld_json(html)
        self.assertEqual(len(items), 0)

    def test_multiple_blocks(self):
        html = """
        <script type="application/ld+json">{"@type": "Organization", "name": "A"}</script>
        <script type="application/ld+json">{"@type": "WebPage", "name": "B"}</script>
        """
        items = extract_ld_json(html)
        self.assertEqual(len(items), 2)


class TestFindEntitySchema(unittest.TestCase):
    def test_finds_organization(self):
        items = [{"@type": "WebPage"}, {"@type": "Organization", "name": "X"}]
        entity = find_entity_schema(items)
        self.assertIsNotNone(entity)
        self.assertEqual(entity["@type"], "Organization")

    def test_finds_restaurant(self):
        items = [{"@type": "Restaurant", "name": "Food"}]
        entity = find_entity_schema(items)
        self.assertEqual(entity["@type"], "Restaurant")

    def test_no_entity(self):
        items = [{"@type": "WebPage"}, {"@type": "BreadcrumbList"}]
        entity = find_entity_schema(items)
        self.assertIsNone(entity)

    def test_empty_list(self):
        self.assertIsNone(find_entity_schema([]))

    def test_list_type(self):
        items = [{"@type": ["Organization", "LocalBusiness"], "name": "X"}]
        entity = find_entity_schema(items)
        self.assertIsNotNone(entity)

    def test_all_entity_types(self):
        for et in ENTITY_TYPES:
            items = [{"@type": et, "name": "Test"}]
            entity = find_entity_schema(items)
            self.assertIsNotNone(entity, f"{et} should be recognized")


class TestScoreSchemaPresence(unittest.TestCase):
    def test_no_schema(self):
        result = score_schema_presence(EMPTY_HTML)
        self.assertEqual(result["score"], 0.0)
        self.assertFalse(result["found"])

    def test_minimal_schema(self):
        result = score_schema_presence(MINIMAL_ORG_HTML)
        self.assertTrue(result["found"])
        self.assertGreater(result["score"], 20)
        self.assertEqual(result["type"], "Organization")

    def test_rich_schema(self):
        result = score_schema_presence(RICH_ORG_HTML)
        self.assertTrue(result["found"])
        self.assertGreater(result["score"], 70)
        self.assertTrue(result["has_id"])
        self.assertTrue(result["has_nested_objects"])
        self.assertGreater(result["completeness"], 60)

    def test_same_as_extracted(self):
        result = score_schema_presence(RICH_ORG_HTML)
        self.assertGreater(len(result["same_as"]), 3)

    def test_restaurant_type(self):
        result = score_schema_presence(RESTAURANT_HTML)
        self.assertTrue(result["found"])
        self.assertEqual(result["type"], "Restaurant")

    def test_attributes_filled(self):
        result = score_schema_presence(RICH_ORG_HTML)
        filled = {k: v for k, v in result["attributes"].items() if v is not None}
        self.assertIn("name", filled)
        self.assertIn("url", filled)
        self.assertIn("description", filled)

    def test_score_capped(self):
        result = score_schema_presence(RICH_ORG_HTML)
        self.assertLessEqual(result["score"], 100)

    def test_graph_format_extraction(self):
        result = score_schema_presence(GRAPH_HTML)
        self.assertTrue(result["found"])
        self.assertEqual(result["type"], "Organization")


class TestScoreConnectionStrength(unittest.TestCase):
    def test_no_links(self):
        result = score_connection_strength([])
        self.assertEqual(result["total_links"], 0)
        self.assertEqual(result["total_linked_platforms"], 0)
        self.assertLess(result["score"], 20)

    def test_tier1_high_score(self):
        urls = [
            "https://www.wikidata.org/wiki/Q12345",
            "https://en.wikipedia.org/wiki/TestCo",
        ]
        result = score_connection_strength(urls)
        t1 = result["tiers"]["tier1_knowledge"]
        self.assertEqual(t1["linked"], 2)
        self.assertGreater(result["score"], 40)

    def test_tier2_medium_score(self):
        urls = [
            "https://www.linkedin.com/company/test",
            "https://blog.naver.com/test",
        ]
        result = score_connection_strength(urls)
        t2 = result["tiers"]["tier2_authority"]
        self.assertGreater(t2["linked"], 0)

    def test_tier3_social(self):
        urls = [
            "https://www.facebook.com/test",
            "https://www.instagram.com/test",
            "https://www.youtube.com/test",
        ]
        result = score_connection_strength(urls)
        t3 = result["tiers"]["tier3_social"]
        self.assertEqual(t3["linked"], 3)

    def test_many_links_bonus(self):
        urls = [
            "https://www.wikidata.org/wiki/Q1",
            "https://en.wikipedia.org/wiki/T",
            "https://www.linkedin.com/company/t",
            "https://www.facebook.com/t",
            "https://www.instagram.com/t",
        ]
        result = score_connection_strength(urls)
        self.assertGreater(result["score"], 60)

    def test_unrecognized_urls(self):
        urls = ["https://custom-platform.com/entity/123"]
        result = score_connection_strength(urls)
        self.assertEqual(len(result["unrecognized_urls"]), 1)

    def test_http_quality_issue(self):
        urls = ["http://www.linkedin.com/company/test"]
        result = score_connection_strength(urls)
        self.assertGreater(len(result["url_quality_issues"]), 0)

    def test_twitter_x_both_work(self):
        for domain in ["https://twitter.com/test", "https://x.com/test"]:
            result = score_connection_strength([domain])
            twitter = result["platforms"].get("twitter", {})
            self.assertTrue(twitter["linked"], f"{domain} should match twitter")

    def test_score_capped(self):
        urls = [f"https://wikidata.org/wiki/Q{i}" for i in range(20)]
        result = score_connection_strength(urls)
        self.assertLessEqual(result["score"], 100)


class TestScoreAttributeCompleteness(unittest.TestCase):
    def test_no_schema_fallback(self):
        entity = {"found": False}
        result = score_attribute_completeness(entity, NO_SCHEMA_HTML)
        self.assertEqual(result["source"], "html_fallback")
        self.assertGreater(result["score"], 0)
        self.assertIn("telephone", result["html_attributes"])

    def test_rich_schema_high_score(self):
        schema = score_schema_presence(RICH_ORG_HTML)
        result = score_attribute_completeness(schema, RICH_ORG_HTML)
        self.assertEqual(result["source"], "schema")
        self.assertGreater(result["score"], 60)
        self.assertEqual(len(result["missing_critical"]), 0)

    def test_minimal_schema_missing_attrs(self):
        schema = score_schema_presence(MINIMAL_ORG_HTML)
        result = score_attribute_completeness(schema, MINIMAL_ORG_HTML)
        self.assertGreater(len(result["missing_type_specific"]), 0)

    def test_restaurant_type_attrs(self):
        schema = score_schema_presence(RESTAURANT_HTML)
        result = score_attribute_completeness(schema, RESTAURANT_HTML)
        self.assertEqual(result["entity_type"], "Restaurant")
        self.assertIn("servesCuisine", result["expected_attributes"])

    def test_structured_address_bonus(self):
        schema = score_schema_presence(RICH_ORG_HTML)
        result = score_attribute_completeness(schema, RICH_ORG_HTML)
        notes = " ".join(result["quality_notes"])
        self.assertIn("Structured address", notes)

    def test_description_quality(self):
        schema = score_schema_presence(RICH_ORG_HTML)
        result = score_attribute_completeness(schema, RICH_ORG_HTML)
        self.assertIn("description", result["schema_attributes"])

    def test_score_range(self):
        for html in [EMPTY_HTML, MINIMAL_ORG_HTML, RICH_ORG_HTML]:
            schema = score_schema_presence(html)
            result = score_attribute_completeness(schema, html)
            self.assertGreaterEqual(result["score"], 0)
            self.assertLessEqual(result["score"], 100)


class TestDetectAttributesFromHtml(unittest.TestCase):
    def test_phone_detection(self):
        from geo_entity import extract_text_content
        text = extract_text_content(NO_SCHEMA_HTML)
        attrs = _detect_attributes_from_html(NO_SCHEMA_HTML, text)
        self.assertTrue(attrs["telephone"])

    def test_email_detection(self):
        from geo_entity import extract_text_content
        text = extract_text_content(NO_SCHEMA_HTML)
        attrs = _detect_attributes_from_html(NO_SCHEMA_HTML, text)
        self.assertTrue(attrs["email"])

    def test_address_korean(self):
        from geo_entity import extract_text_content
        text = extract_text_content(NO_SCHEMA_HTML)
        attrs = _detect_attributes_from_html(NO_SCHEMA_HTML, text)
        self.assertTrue(attrs["address"])

    def test_logo_detection(self):
        from geo_entity import extract_text_content
        text = extract_text_content(NO_SCHEMA_HTML)
        attrs = _detect_attributes_from_html(NO_SCHEMA_HTML, text)
        self.assertTrue(attrs["logo"])

    def test_hours_detection(self):
        from geo_entity import extract_text_content
        text = extract_text_content(NO_SCHEMA_HTML)
        attrs = _detect_attributes_from_html(NO_SCHEMA_HTML, text)
        self.assertTrue(attrs["openingHours"])

    def test_empty_html(self):
        from geo_entity import extract_text_content
        text = extract_text_content(EMPTY_HTML)
        attrs = _detect_attributes_from_html(EMPTY_HTML, text)
        self.assertFalse(attrs["telephone"])
        self.assertFalse(attrs["email"])


class TestScoreDisambiguation(unittest.TestCase):
    def test_rich_signals_high_score(self):
        result = score_disambiguation("Sky Ventures", RICH_ORG_HTML)
        self.assertGreater(result["score"], 60)
        self.assertTrue(result["signals"]["business_registration"])
        self.assertTrue(result["signals"]["founder_ceo"])
        self.assertTrue(result["signals"]["founding_year"])

    def test_empty_html_low_score(self):
        result = score_disambiguation("TestCo", EMPTY_HTML)
        self.assertLess(result["score"], 30)

    def test_brand_mentions(self):
        result = score_disambiguation("Sky Ventures", RICH_ORG_HTML)
        self.assertGreater(result["signals"]["brand_mentions"], 0)

    def test_location_qualifier(self):
        result = score_disambiguation("Sky Ventures", RICH_ORG_HTML)
        self.assertTrue(result["signals"]["location_qualifier"])

    def test_industry_qualifier(self):
        result = score_disambiguation("Sky Ventures", RICH_ORG_HTML)
        self.assertTrue(result["signals"]["industry_qualifier"])

    def test_schema_id_bonus(self):
        result = score_disambiguation("Sky Ventures", RICH_ORG_HTML)
        self.assertTrue(result["signals"].get("schema_id"))

    def test_legal_name_bonus(self):
        result = score_disambiguation("Sky Ventures", RICH_ORG_HTML)
        self.assertTrue(result["signals"].get("legal_name"))

    def test_tax_id_bonus(self):
        result = score_disambiguation("Sky Ventures", RICH_ORG_HTML)
        self.assertTrue(result["signals"].get("tax_id"))

    def test_generic_name_penalty(self):
        result = score_disambiguation("Tech Shop Store", GENERIC_NAME_HTML)
        self.assertTrue(result["signals"]["has_generic_name_parts"])

    def test_score_range(self):
        for html, brand in [(EMPTY_HTML, "X"), (RICH_ORG_HTML, "Sky Ventures")]:
            result = score_disambiguation(brand, html)
            self.assertGreaterEqual(result["score"], 0)
            self.assertLessEqual(result["score"], 100)


class TestAnalyzeEntityHtml(unittest.TestCase):
    def test_success(self):
        result = analyze_entity_html(RICH_ORG_HTML, "Sky Ventures", "https://skyventures.com")
        self.assertTrue(result["success"])

    def test_all_fields(self):
        result = analyze_entity_html(MINIMAL_ORG_HTML, "TestCo", "https://testco.com")
        self.assertIn("score", result)
        self.assertIn("dimensions", result)
        self.assertIn("weakest_dimension", result)
        self.assertIn("schema", result)
        self.assertIn("connection", result)
        self.assertIn("completeness", result)
        self.assertIn("disambiguation", result)
        self.assertIn("issues", result)

    def test_dimensions_present(self):
        result = analyze_entity_html(RICH_ORG_HTML, "Sky Ventures")
        dims = result["dimensions"]
        self.assertIn("schema_presence", dims)
        self.assertIn("connection_strength", dims)
        self.assertIn("attribute_completeness", dims)
        self.assertIn("disambiguation", dims)

    def test_rich_page_high_score(self):
        result = analyze_entity_html(RICH_ORG_HTML, "Sky Ventures", "https://skyventures.com")
        self.assertGreater(result["score"], 50)

    def test_empty_page_low_score(self):
        result = analyze_entity_html(EMPTY_HTML, "Unknown", "https://example.com")
        self.assertLess(result["score"], 20)

    def test_no_schema_critical_issue(self):
        result = analyze_entity_html(EMPTY_HTML, "TestBrand")
        critical = [i for i in result["issues"] if i["severity"] == "critical"]
        self.assertGreater(len(critical), 0)

    def test_issues_sorted_by_severity(self):
        result = analyze_entity_html(MINIMAL_ORG_HTML, "TestCo")
        if len(result["issues"]) >= 2:
            severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            for i in range(len(result["issues"]) - 1):
                s1 = severity_order.get(result["issues"][i]["severity"], 4)
                s2 = severity_order.get(result["issues"][i + 1]["severity"], 4)
                self.assertLessEqual(s1, s2)

    def test_weakest_dimension(self):
        result = analyze_entity_html(MINIMAL_ORG_HTML, "TestCo")
        self.assertIn(result["weakest_dimension"], ENTITY_WEIGHTS.keys())

    def test_score_formula(self):
        result = analyze_entity_html(RICH_ORG_HTML, "Sky Ventures")
        dims = result["dimensions"]
        expected = round(
            dims["schema_presence"] * ENTITY_WEIGHTS["schema_presence"]
            + dims["connection_strength"] * ENTITY_WEIGHTS["connection_strength"]
            + dims["attribute_completeness"] * ENTITY_WEIGHTS["attribute_completeness"]
            + dims["disambiguation"] * ENTITY_WEIGHTS["disambiguation"],
            1,
        )
        self.assertAlmostEqual(result["score"], expected, places=0)

    def test_no_schema_html_with_attrs(self):
        result = analyze_entity_html(NO_SCHEMA_HTML, "TestBrand")
        self.assertGreater(result["completeness"]["score"], 0)

    def test_restaurant_entity(self):
        result = analyze_entity_html(RESTAURANT_HTML, "맛있는 식당")
        self.assertEqual(result["schema"]["type"], "Restaurant")

    def test_score_range(self):
        for html, brand in [(EMPTY_HTML, "X"), (RICH_ORG_HTML, "Sky Ventures"), (RESTAURANT_HTML, "맛있는 식당")]:
            result = analyze_entity_html(html, brand)
            self.assertGreaterEqual(result["score"], 0)
            self.assertLessEqual(result["score"], 100)
            for dim_score in result["dimensions"].values():
                self.assertGreaterEqual(dim_score, 0)
                self.assertLessEqual(dim_score, 100)


class TestBuildSourceStatus(unittest.TestCase):
    def test_backward_compat(self):
        analysis = analyze_entity_html(RICH_ORG_HTML, "Sky Ventures", "https://skyventures.com")
        sources = _build_source_status(analysis)
        self.assertIn("schema_org", sources)
        self.assertIn("wikidata", sources)
        self.assertIn("wikipedia", sources)
        self.assertIn("google_kp", sources)
        self.assertIn("naver", sources)

    def test_schema_found_status(self):
        analysis = analyze_entity_html(RICH_ORG_HTML, "Sky Ventures")
        sources = _build_source_status(analysis)
        self.assertEqual(sources["schema_org"]["status"], "found")

    def test_wikidata_linked(self):
        analysis = analyze_entity_html(RICH_ORG_HTML, "Sky Ventures")
        sources = _build_source_status(analysis)
        self.assertEqual(sources["wikidata"]["status"], "linked")

    def test_no_schema_not_found(self):
        analysis = analyze_entity_html(EMPTY_HTML, "X")
        sources = _build_source_status(analysis)
        self.assertEqual(sources["schema_org"]["status"], "not_found")


class TestEntityWeights(unittest.TestCase):
    def test_weights_sum_to_one(self):
        total = sum(ENTITY_WEIGHTS.values())
        self.assertAlmostEqual(total, 1.0, places=5)

    def test_four_dimensions(self):
        self.assertEqual(len(ENTITY_WEIGHTS), 4)

    def test_all_entity_types_have_attrs(self):
        for et in TYPE_ATTRIBUTES:
            self.assertIn(et, ENTITY_TYPES)

    def test_core_attributes(self):
        self.assertEqual(len(CORE_ATTRIBUTES), 3)
        self.assertIn("name", CORE_ATTRIBUTES)
        self.assertIn("description", CORE_ATTRIBUTES)
        self.assertIn("url", CORE_ATTRIBUTES)


class TestEdgeCases(unittest.TestCase):
    def test_same_as_string_not_list(self):
        html = """
        <script type="application/ld+json">
        {"@type": "Organization", "name": "Test", "sameAs": "https://linkedin.com/company/test"}
        </script>
        """
        result = score_schema_presence(html)
        self.assertIsInstance(result["same_as"], list)
        self.assertEqual(len(result["same_as"]), 1)

    def test_empty_same_as(self):
        result = score_connection_strength([])
        self.assertEqual(result["score"], 10.0)

    def test_multiple_entity_types_first_wins(self):
        html = """
        <script type="application/ld+json">{"@type": "Restaurant", "name": "A"}</script>
        <script type="application/ld+json">{"@type": "Organization", "name": "B"}</script>
        """
        items = extract_ld_json(html)
        entity = find_entity_schema(items)
        self.assertEqual(entity["@type"], "Restaurant")

    def test_special_chars_in_brand(self):
        result = score_disambiguation("Test & Co. (주)", RICH_ORG_HTML)
        self.assertGreaterEqual(result["score"], 0)

    def test_very_long_html(self):
        html = "<html><body>" + "<p>content</p>" * 1000
        html += '<script type="application/ld+json">{"@type":"Organization","name":"Big"}</script>'
        html += "</body></html>"
        result = analyze_entity_html(html, "Big")
        self.assertTrue(result["success"])


if __name__ == "__main__":
    unittest.main()

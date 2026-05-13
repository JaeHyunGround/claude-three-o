"""Tests for aao_entity.py — entity consistency analysis."""

import sys
import os
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from aao_entity import (
    extract_entity_from_schema, _flatten_address,
    extract_entity_from_html, check_nap_consistency,
    analyze_entity_consistency, ENTITY_FIELDS,
)


class TestEntityFields(unittest.TestCase):

    def test_count(self):
        self.assertEqual(len(ENTITY_FIELDS), 9)

    def test_has_name(self):
        self.assertIn("name", ENTITY_FIELDS)

    def test_has_address(self):
        self.assertIn("address", ENTITY_FIELDS)

    def test_has_telephone(self):
        self.assertIn("telephone", ENTITY_FIELDS)


class TestFlattenAddress(unittest.TestCase):

    def test_string_passthrough(self):
        self.assertEqual(_flatten_address("123 Main St"), "123 Main St")

    def test_dict_flattened(self):
        addr = {"streetAddress": "123 Main", "addressLocality": "Seoul", "postalCode": "06100"}
        result = _flatten_address(addr)
        self.assertIn("123 Main", result)
        self.assertIn("Seoul", result)
        self.assertIn("06100", result)

    def test_none_returns_empty(self):
        self.assertEqual(_flatten_address(None), "")

    def test_empty_dict(self):
        self.assertEqual(_flatten_address({}), "")

    def test_partial_dict(self):
        addr = {"addressLocality": "Gangnam"}
        result = _flatten_address(addr)
        self.assertEqual(result, "Gangnam")


class TestExtractEntityFromSchema(unittest.TestCase):

    def _html(self, json_ld):
        import json
        return f'<html><head><script type="application/ld+json">{json.dumps(json_ld)}</script></head></html>'

    def test_organization(self):
        html = self._html({"@type": "Organization", "name": "Acme"})
        result = extract_entity_from_schema(html)
        self.assertEqual(result["source"], "json-ld")
        self.assertEqual(result["name"], "Acme")
        self.assertEqual(result["type"], "Organization")

    def test_local_business(self):
        html = self._html({"@type": "LocalBusiness", "name": "Cafe", "telephone": "010-1234"})
        result = extract_entity_from_schema(html)
        self.assertEqual(result["type"], "LocalBusiness")
        self.assertEqual(result["telephone"], "010-1234")

    def test_restaurant(self):
        html = self._html({"@type": "Restaurant", "name": "Sushi Place"})
        result = extract_entity_from_schema(html)
        self.assertEqual(result["type"], "Restaurant")

    def test_list_type(self):
        html = self._html({"@type": ["LocalBusiness", "Restaurant"], "name": "Multi"})
        result = extract_entity_from_schema(html)
        self.assertEqual(result["type"], "LocalBusiness")

    def test_array_wrapper(self):
        import json
        ld = json.dumps([{"@type": "Organization", "name": "InArray"}])
        html = f'<html><head><script type="application/ld+json">{ld}</script></head></html>'
        result = extract_entity_from_schema(html)
        self.assertEqual(result["name"], "InArray")

    def test_no_entity_type(self):
        html = self._html({"@type": "WebPage", "name": "Just a Page"})
        result = extract_entity_from_schema(html)
        self.assertIsNone(result.get("source") if result.get("source") != "json-ld" else None)

    def test_no_json_ld(self):
        result = extract_entity_from_schema("<html><body>Hello</body></html>")
        self.assertIsNone(result["source"])

    def test_invalid_json(self):
        html = '<html><head><script type="application/ld+json">{invalid}</script></head></html>'
        result = extract_entity_from_schema(html)
        self.assertIsNone(result["source"])

    def test_address_dict_flattened(self):
        html = self._html({
            "@type": "LocalBusiness", "name": "Shop",
            "address": {"streetAddress": "123 St", "addressLocality": "Seoul"},
        })
        result = extract_entity_from_schema(html)
        self.assertIn("Seoul", result["address"])

    def test_same_as_list(self):
        html = self._html({
            "@type": "Organization", "name": "Brand",
            "sameAs": ["https://twitter.com/brand", "https://facebook.com/brand"],
        })
        result = extract_entity_from_schema(html)
        self.assertEqual(len(result["sameAs"]), 2)

    def test_same_as_empty_default(self):
        html = self._html({"@type": "Organization", "name": "NoSocial"})
        result = extract_entity_from_schema(html)
        self.assertEqual(result["sameAs"], [])

    def test_medical_business(self):
        html = self._html({"@type": "MedicalBusiness", "name": "Clinic"})
        result = extract_entity_from_schema(html)
        self.assertEqual(result["type"], "MedicalBusiness")

    def test_store(self):
        html = self._html({"@type": "Store", "name": "Shop"})
        result = extract_entity_from_schema(html)
        self.assertEqual(result["type"], "Store")

    def test_multiple_ld_blocks_picks_entity(self):
        import json
        block1 = json.dumps({"@type": "WebPage", "name": "Page"})
        block2 = json.dumps({"@type": "Organization", "name": "TheOrg"})
        html = (
            f'<html><head>'
            f'<script type="application/ld+json">{block1}</script>'
            f'<script type="application/ld+json">{block2}</script>'
            f'</head></html>'
        )
        result = extract_entity_from_schema(html)
        self.assertEqual(result["name"], "TheOrg")


class TestExtractEntityFromHtml(unittest.TestCase):

    def test_title_extraction(self):
        html = '<html><head><title>My Brand - Homepage</title></head></html>'
        result = extract_entity_from_html(html)
        self.assertEqual(result["name"], "My Brand")

    def test_title_pipe_separator(self):
        html = '<html><head><title>Brand Name | Services</title></head></html>'
        result = extract_entity_from_html(html)
        self.assertEqual(result["name"], "Brand Name")

    def test_description_meta(self):
        html = '<html><head><meta name="description" content="Best service in Seoul"></head></html>'
        result = extract_entity_from_html(html)
        self.assertEqual(result["description"], "Best service in Seoul")

    def test_og_site_name(self):
        html = '<html><head><meta property="og:site_name" content="BrandOG"></head></html>'
        result = extract_entity_from_html(html)
        self.assertEqual(result["og_name"], "BrandOG")

    def test_telephone(self):
        html = '<html><body><a href="tel:+821012345678">Call us</a></body></html>'
        result = extract_entity_from_html(html)
        self.assertEqual(result["telephone"], "+821012345678")

    def test_canonical_url(self):
        html = '<html><head><link rel="canonical" href="https://example.com/page"></head></html>'
        result = extract_entity_from_html(html)
        self.assertEqual(result["url"], "https://example.com/page")

    def test_empty_html(self):
        result = extract_entity_from_html("<html></html>")
        self.assertEqual(result["source"], "html")
        self.assertNotIn("name", result)

    def test_all_fields_present(self):
        html = (
            '<html><head>'
            '<title>Brand - Home</title>'
            '<meta name="description" content="Desc">'
            '<meta property="og:site_name" content="Brand">'
            '<link rel="canonical" href="https://brand.com">'
            '</head><body><a href="tel:010-1234">Call</a></body></html>'
        )
        result = extract_entity_from_html(html)
        self.assertEqual(result["name"], "Brand")
        self.assertEqual(result["description"], "Desc")
        self.assertEqual(result["og_name"], "Brand")
        self.assertEqual(result["url"], "https://brand.com")
        self.assertEqual(result["telephone"], "010-1234")


class TestCheckNapConsistency(unittest.TestCase):

    def test_all_consistent(self):
        schema = {"name": "Brand", "telephone": "010-1234-5678", "url": "https://brand.com"}
        html = {"name": "Brand", "og_name": "Brand", "telephone": "010-1234-5678", "url": "https://brand.com"}
        result = check_nap_consistency(schema, html)
        self.assertEqual(result["consistency_rate"], 100)

    def test_name_inconsistent(self):
        schema = {"name": "Brand A"}
        html = {"name": "Brand B", "og_name": "Brand C"}
        result = check_nap_consistency(schema, html)
        self.assertFalse(result["checks"]["name"]["consistent"])

    def test_name_missing(self):
        result = check_nap_consistency({}, {})
        self.assertFalse(result["checks"]["name"]["consistent"])
        self.assertTrue(result["checks"]["name"].get("missing"))

    def test_phone_consistent_ignores_formatting(self):
        schema = {"telephone": "010-1234-5678"}
        html = {"telephone": "01012345678"}
        result = check_nap_consistency(schema, html)
        self.assertTrue(result["checks"]["phone"]["consistent"])

    def test_phone_inconsistent(self):
        schema = {"telephone": "010-1234-5678"}
        html = {"telephone": "02-999-8888"}
        result = check_nap_consistency(schema, html)
        self.assertFalse(result["checks"]["phone"]["consistent"])

    def test_phone_missing(self):
        result = check_nap_consistency({}, {})
        self.assertTrue(result["checks"]["phone"].get("missing"))

    def test_phone_single_source(self):
        result = check_nap_consistency({"telephone": "010-1234"}, {})
        self.assertTrue(result["checks"]["phone"]["consistent"])

    def test_url_consistent(self):
        schema = {"url": "https://brand.com/"}
        html = {"url": "https://brand.com"}
        result = check_nap_consistency(schema, html)
        self.assertTrue(result["checks"]["url"]["consistent"])

    def test_url_inconsistent(self):
        schema = {"url": "https://brand.com"}
        html = {"url": "https://other.com"}
        result = check_nap_consistency(schema, html)
        self.assertFalse(result["checks"]["url"]["consistent"])

    def test_url_not_checked_if_only_one(self):
        result = check_nap_consistency({"url": "https://a.com"}, {})
        self.assertNotIn("url", result["checks"])

    def test_single_name_considered_consistent(self):
        result = check_nap_consistency({"name": "Solo"}, {})
        self.assertTrue(result["checks"]["name"]["consistent"])

    def test_consistency_rate_calculation(self):
        schema = {"name": "A", "telephone": "111", "url": "https://a.com"}
        html = {"name": "B", "og_name": "C", "telephone": "222", "url": "https://b.com"}
        result = check_nap_consistency(schema, html)
        self.assertEqual(result["total_checks"], 3)
        self.assertEqual(result["consistent_count"], 0)
        self.assertEqual(result["consistency_rate"], 0)

    def test_case_insensitive_name(self):
        schema = {"name": "BRAND"}
        html = {"name": "brand", "og_name": "Brand"}
        result = check_nap_consistency(schema, html)
        self.assertTrue(result["checks"]["name"]["consistent"])


class TestAnalyzeEntityConsistency(unittest.TestCase):

    def _org_html(self, **kwargs):
        import json
        ld = {"@type": "Organization", "name": "TestBrand", "telephone": "010-1234",
              "url": "https://test.com", "description": "A test brand",
              "sameAs": ["https://twitter.com/test"]}
        ld.update(kwargs)
        ld_str = json.dumps(ld)
        return (
            f'<html><head>'
            f'<title>TestBrand - Home</title>'
            f'<meta name="description" content="A test brand">'
            f'<meta property="og:site_name" content="TestBrand">'
            f'<link rel="canonical" href="https://test.com">'
            f'<script type="application/ld+json">{ld_str}</script>'
            f'</head><body><a href="tel:010-1234">Call</a></body></html>'
        )

    @patch("aao_entity.validate_url", return_value={"valid": False, "error": "bad"})
    def test_invalid_url(self, mock_val):
        result = analyze_entity_consistency("bad")
        self.assertFalse(result["success"])

    @patch("aao_entity.validate_url", return_value={"valid": True})
    @patch("aao_entity.fetch_page", return_value={"success": False, "error": "timeout"})
    def test_fetch_failure(self, mock_fetch, mock_val):
        result = analyze_entity_consistency("https://test.com")
        self.assertFalse(result["success"])

    @patch("aao_entity.validate_url", return_value={"valid": True})
    @patch("aao_entity.fetch_page")
    def test_full_entity_high_score(self, mock_fetch, mock_val):
        mock_fetch.return_value = {"success": True, "html": self._org_html()}
        result = analyze_entity_consistency("https://test.com")
        self.assertTrue(result["success"])
        self.assertGreater(result["score"], 60)

    @patch("aao_entity.validate_url", return_value={"valid": True})
    @patch("aao_entity.fetch_page")
    def test_no_schema_low_score(self, mock_fetch, mock_val):
        html = '<html><head><title>Brand</title></head><body>Hello</body></html>'
        mock_fetch.return_value = {"success": True, "html": html}
        result = analyze_entity_consistency("https://test.com")
        self.assertTrue(result["success"])
        self.assertLess(result["score"], 50)
        issues = [i["message"] for i in result["issues"]]
        self.assertTrue(any("No entity schema" in i for i in issues))

    @patch("aao_entity.validate_url", return_value={"valid": True})
    @patch("aao_entity.fetch_page")
    def test_same_as_adds_score(self, mock_fetch, mock_val):
        html_with = self._org_html(sameAs=["https://fb.com", "https://tw.com", "https://ig.com"])
        mock_fetch.return_value = {"success": True, "html": html_with}
        result_with = analyze_entity_consistency("https://test.com")

        html_without = self._org_html(sameAs=[])
        mock_fetch.return_value = {"success": True, "html": html_without}
        result_without = analyze_entity_consistency("https://test.com")

        self.assertGreater(result_with["score"], result_without["score"])

    @patch("aao_entity.validate_url", return_value={"valid": True})
    @patch("aao_entity.fetch_page")
    def test_same_as_string_normalized(self, mock_fetch, mock_val):
        import json
        ld = json.dumps({"@type": "Organization", "name": "X", "sameAs": "https://single.com"})
        html = f'<html><head><script type="application/ld+json">{ld}</script></head></html>'
        mock_fetch.return_value = {"success": True, "html": html}
        result = analyze_entity_consistency("https://test.com")
        self.assertEqual(result["same_as_links"], ["https://single.com"])

    @patch("aao_entity.validate_url", return_value={"valid": True})
    @patch("aao_entity.fetch_page")
    def test_nap_consistency_in_result(self, mock_fetch, mock_val):
        mock_fetch.return_value = {"success": True, "html": self._org_html()}
        result = analyze_entity_consistency("https://test.com")
        self.assertIn("nap_consistency", result)
        self.assertIn("checks", result["nap_consistency"])

    @patch("aao_entity.validate_url", return_value={"valid": True})
    @patch("aao_entity.fetch_page")
    def test_inconsistent_name_issue(self, mock_fetch, mock_val):
        import json
        ld = json.dumps({"@type": "Organization", "name": "DifferentBrand"})
        html = (
            f'<html><head><title>OriginalBrand - Home</title>'
            f'<meta property="og:site_name" content="YetAnother">'
            f'<script type="application/ld+json">{ld}</script>'
            f'</head></html>'
        )
        mock_fetch.return_value = {"success": True, "html": html}
        result = analyze_entity_consistency("https://test.com")
        issues = [i["message"] for i in result["issues"]]
        self.assertTrue(any("Inconsistent name" in i for i in issues))

    @patch("aao_entity.validate_url", return_value={"valid": True})
    @patch("aao_entity.fetch_page")
    def test_score_clamped_0_100(self, mock_fetch, mock_val):
        mock_fetch.return_value = {"success": True, "html": self._org_html()}
        result = analyze_entity_consistency("https://test.com")
        self.assertGreaterEqual(result["score"], 0)
        self.assertLessEqual(result["score"], 100)

    @patch("aao_entity.validate_url", return_value={"valid": True})
    @patch("aao_entity.fetch_page")
    def test_no_same_as_issue(self, mock_fetch, mock_val):
        html = self._org_html(sameAs=[])
        mock_fetch.return_value = {"success": True, "html": html}
        result = analyze_entity_consistency("https://test.com")
        issues = [i["message"] for i in result["issues"]]
        self.assertTrue(any("sameAs" in i for i in issues))

    @patch("aao_entity.validate_url", return_value={"valid": True})
    @patch("aao_entity.fetch_page")
    def test_schema_entity_in_result(self, mock_fetch, mock_val):
        mock_fetch.return_value = {"success": True, "html": self._org_html()}
        result = analyze_entity_consistency("https://test.com")
        self.assertIn("schema_entity", result)
        self.assertEqual(result["schema_entity"]["source"], "json-ld")


if __name__ == "__main__":
    unittest.main()

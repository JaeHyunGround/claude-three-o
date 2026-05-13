"""Tests for seo_schema.py — Schema.org structured data detection and validation."""

import sys
import os
import json
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from seo_schema import (
    extract_jsonld,
    validate_schema,
    analyze_schema,
)


class TestExtractJsonld(unittest.TestCase):

    def test_no_jsonld(self):
        html = '<html><body>No schema</body></html>'
        self.assertEqual(extract_jsonld(html), [])

    def test_single_block(self):
        schema = {"@type": "Organization", "name": "Test"}
        html = f'<script type="application/ld+json">{json.dumps(schema)}</script>'
        result = extract_jsonld(html)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "Test")

    def test_multiple_blocks(self):
        s1 = json.dumps({"@type": "Organization", "name": "A"})
        s2 = json.dumps({"@type": "Product", "name": "B"})
        html = f'<script type="application/ld+json">{s1}</script><script type="application/ld+json">{s2}</script>'
        result = extract_jsonld(html)
        self.assertEqual(len(result), 2)

    def test_array_jsonld(self):
        schemas = [{"@type": "Organization", "name": "A"}, {"@type": "Product", "name": "B"}]
        html = f'<script type="application/ld+json">{json.dumps(schemas)}</script>'
        result = extract_jsonld(html)
        self.assertEqual(len(result), 2)

    def test_invalid_json(self):
        html = '<script type="application/ld+json">{invalid json</script>'
        result = extract_jsonld(html)
        self.assertEqual(len(result), 1)
        self.assertIn("_error", result[0])

    def test_single_quotes_type(self):
        schema = json.dumps({"@type": "Organization", "name": "Test"})
        html = f"<script type='application/ld+json'>{schema}</script>"
        result = extract_jsonld(html)
        self.assertEqual(len(result), 1)

    def test_multiline_json(self):
        schema = '{\n  "@type": "Organization",\n  "name": "Test"\n}'
        html = f'<script type="application/ld+json">\n{schema}\n</script>'
        result = extract_jsonld(html)
        self.assertEqual(len(result), 1)


class TestValidateSchema(unittest.TestCase):

    def test_valid_organization(self):
        schema = {"@type": "Organization", "name": "Test", "url": "https://x.com"}
        result = validate_schema(schema)
        self.assertTrue(result["valid"])
        self.assertEqual(result["completeness"], 100.0)

    def test_incomplete_organization(self):
        schema = {"@type": "Organization", "name": "Test"}
        result = validate_schema(schema)
        self.assertFalse(result["valid"])
        self.assertLess(result["completeness"], 100)

    def test_valid_product(self):
        schema = {"@type": "Product", "name": "Widget", "offers": {}}
        result = validate_schema(schema)
        self.assertTrue(result["valid"])

    def test_missing_product_offers(self):
        schema = {"@type": "Product", "name": "Widget"}
        result = validate_schema(schema)
        self.assertFalse(result["valid"])

    def test_article_required_fields(self):
        schema = {"@type": "Article", "headline": "T", "author": "A", "datePublished": "2024-01-01"}
        result = validate_schema(schema)
        self.assertTrue(result["valid"])

    def test_localbusiness_required(self):
        schema = {"@type": "LocalBusiness", "name": "Shop", "address": {}, "telephone": "123"}
        result = validate_schema(schema)
        self.assertTrue(result["valid"])

    def test_howto_deprecated(self):
        schema = {"@type": "HowTo", "name": "Steps"}
        result = validate_schema(schema)
        self.assertFalse(result["valid"])
        self.assertGreater(len(result["deprecated_warnings"]), 0)

    def test_faqpage_restricted(self):
        schema = {"@type": "FAQPage", "mainEntity": []}
        result = validate_schema(schema)
        self.assertFalse(result["valid"])
        self.assertTrue(any("gov/health" in w for w in result["deprecated_warnings"]))

    def test_unknown_type(self):
        schema = {"@type": "CustomThing", "name": "X"}
        result = validate_schema(schema)
        self.assertTrue(result["valid"])

    def test_missing_recommended_fields(self):
        schema = {"@type": "Organization", "name": "Test", "url": "https://x.com"}
        result = validate_schema(schema)
        self.assertGreater(len(result["missing_recommended"]), 0)

    def test_restaurant_required(self):
        schema = {"@type": "Restaurant", "name": "R", "address": {}, "telephone": "1", "servesCuisine": "Italian"}
        result = validate_schema(schema)
        self.assertTrue(result["valid"])

    def test_event_required(self):
        schema = {"@type": "Event", "name": "E", "startDate": "2024-01-01", "location": {}}
        result = validate_schema(schema)
        self.assertTrue(result["valid"])

    def test_type_in_result(self):
        schema = {"@type": "Product", "name": "P", "offers": {}}
        result = validate_schema(schema)
        self.assertEqual(result["type"], "Product")


class TestAnalyzeSchema(unittest.TestCase):

    @patch("seo_schema.validate_url", return_value={"valid": False, "error": "bad"})
    def test_invalid_url(self, mock_val):
        result = analyze_schema("bad")
        self.assertFalse(result["success"])

    @patch("seo_schema.validate_url", return_value={"valid": True})
    @patch("seo_schema.fetch_page", return_value={"success": False, "error": "timeout"})
    def test_fetch_failure(self, mock_fetch, mock_val):
        result = analyze_schema("https://x.com")
        self.assertFalse(result["success"])

    @patch("seo_schema.validate_url", return_value={"valid": True})
    @patch("seo_schema.fetch_page")
    def test_no_schema(self, mock_fetch, mock_val):
        mock_fetch.return_value = {"success": True, "html": "<html></html>"}
        result = analyze_schema("https://x.com")
        self.assertTrue(result["success"])
        self.assertEqual(result["score"], 0)
        self.assertEqual(result["jsonld_count"], 0)

    @patch("seo_schema.validate_url", return_value={"valid": True})
    @patch("seo_schema.fetch_page")
    def test_with_valid_schema(self, mock_fetch, mock_val):
        schema = json.dumps({"@type": "Organization", "name": "Test", "url": "https://x.com"})
        html = f'<script type="application/ld+json">{schema}</script>'
        mock_fetch.return_value = {"success": True, "html": html}
        result = analyze_schema("https://x.com")
        self.assertTrue(result["success"])
        self.assertGreater(result["score"], 0)
        self.assertEqual(result["jsonld_count"], 1)
        self.assertIn("Organization", result["types_found"])

    @patch("seo_schema.validate_url", return_value={"valid": True})
    @patch("seo_schema.fetch_page")
    def test_microdata_detected(self, mock_fetch, mock_val):
        html = '<div itemscope itemtype="http://schema.org/Product"><span itemprop="name">P</span></div>'
        mock_fetch.return_value = {"success": True, "html": html}
        result = analyze_schema("https://x.com")
        self.assertTrue(result["has_microdata"])

    @patch("seo_schema.validate_url", return_value={"valid": True})
    @patch("seo_schema.fetch_page")
    def test_rdfa_detected(self, mock_fetch, mock_val):
        html = '<div typeof="schema:Product"><span property="name">P</span></div>'
        mock_fetch.return_value = {"success": True, "html": html}
        result = analyze_schema("https://x.com")
        self.assertTrue(result["has_rdfa"])

    @patch("seo_schema.validate_url", return_value={"valid": True})
    @patch("seo_schema.fetch_page")
    def test_result_keys(self, mock_fetch, mock_val):
        mock_fetch.return_value = {"success": True, "html": "<html></html>"}
        result = analyze_schema("https://x.com")
        for key in ["success", "url", "score", "jsonld_count", "schemas", "has_microdata", "has_rdfa", "types_found"]:
            self.assertIn(key, result)

    @patch("seo_schema.validate_url", return_value={"valid": True})
    @patch("seo_schema.fetch_page")
    def test_score_capped_at_100(self, mock_fetch, mock_val):
        schema = json.dumps({"@type": "Organization", "name": "T", "url": "U"})
        html = f'<script type="application/ld+json">{schema}</script>'
        mock_fetch.return_value = {"success": True, "html": html}
        result = analyze_schema("https://x.com")
        self.assertLessEqual(result["score"], 100)


if __name__ == "__main__":
    unittest.main()

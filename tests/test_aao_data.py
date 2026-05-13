"""Tests for aao_data.py — structured data push analysis."""

import sys
import os
import json
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from aao_data import (
    extract_structured_data, audit_schema_completeness,
    check_microdata, check_rdfa, check_action_availability,
    analyze_structured_data, AGENT_REQUIRED_FIELDS, ACTION_SCHEMAS,
)


class TestConstants(unittest.TestCase):

    def test_agent_required_fields_types(self):
        expected = {"LocalBusiness", "Restaurant", "Product", "Service",
                    "Organization", "MedicalBusiness", "EducationalOrganization"}
        self.assertEqual(set(AGENT_REQUIRED_FIELDS.keys()), expected)

    def test_all_fields_are_lists(self):
        for t, fields in AGENT_REQUIRED_FIELDS.items():
            self.assertIsInstance(fields, list, f"{t} fields not a list")
            self.assertGreater(len(fields), 0, f"{t} has no required fields")

    def test_action_schemas(self):
        self.assertEqual(set(ACTION_SCHEMAS.keys()), {"book", "buy", "order", "search"})


class TestExtractStructuredData(unittest.TestCase):

    def _html(self, *ld_items):
        scripts = ""
        for item in ld_items:
            scripts += f'<script type="application/ld+json">{json.dumps(item)}</script>'
        return f"<html><head>{scripts}</head></html>"

    def test_single_block(self):
        html = self._html({"@type": "Organization", "name": "Test"})
        result = extract_structured_data(html)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "Test")

    def test_multiple_blocks(self):
        html = self._html({"@type": "Organization"}, {"@type": "WebPage"})
        result = extract_structured_data(html)
        self.assertEqual(len(result), 2)

    def test_array_block(self):
        html = self._html([{"@type": "Org"}, {"@type": "Page"}])
        result = extract_structured_data(html)
        self.assertEqual(len(result), 2)

    def test_no_json_ld(self):
        result = extract_structured_data("<html><body>Hello</body></html>")
        self.assertEqual(len(result), 0)

    def test_invalid_json_skipped(self):
        html = '<html><head><script type="application/ld+json">{bad json}</script></head></html>'
        result = extract_structured_data(html)
        self.assertEqual(len(result), 0)

    def test_mixed_valid_invalid(self):
        html = (
            '<html><head>'
            '<script type="application/ld+json">{"@type":"Org"}</script>'
            '<script type="application/ld+json">{broken}</script>'
            '</head></html>'
        )
        result = extract_structured_data(html)
        self.assertEqual(len(result), 1)


class TestAuditSchemaCompleteness(unittest.TestCase):

    def test_full_local_business(self):
        schema = {
            "@type": "LocalBusiness", "name": "Shop", "address": "123 St",
            "telephone": "010", "openingHoursSpecification": "Mon-Fri",
            "geo": {"lat": 37}, "url": "https://x.com", "image": "img.jpg",
            "priceRange": "$$",
        }
        result = audit_schema_completeness([schema])
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["schemas"][0]["completeness"], 100)
        self.assertEqual(len(result["schemas"][0]["missing_fields"]), 0)

    def test_partial_local_business(self):
        schema = {"@type": "LocalBusiness", "name": "Shop"}
        result = audit_schema_completeness([schema])
        self.assertLess(result["schemas"][0]["completeness"], 100)
        self.assertGreater(len(result["schemas"][0]["missing_fields"]), 0)

    def test_unknown_type_no_required(self):
        schema = {"@type": "WebPage", "name": "Page"}
        result = audit_schema_completeness([schema])
        self.assertEqual(result["schemas"][0]["completeness"], 0)
        self.assertEqual(len(result["schemas"][0]["missing_fields"]), 0)

    def test_list_type(self):
        schema = {"@type": ["Restaurant", "FoodEstablishment"], "name": "Food"}
        result = audit_schema_completeness([schema])
        self.assertEqual(result["schemas"][0]["type"], "Restaurant")

    def test_with_action(self):
        schema = {"@type": "Organization", "potentialAction": {"@type": "SearchAction"}}
        result = audit_schema_completeness([schema])
        self.assertTrue(result["schemas"][0]["has_action"])

    def test_without_action(self):
        schema = {"@type": "Organization", "name": "X"}
        result = audit_schema_completeness([schema])
        self.assertFalse(result["schemas"][0]["has_action"])

    def test_empty_list(self):
        result = audit_schema_completeness([])
        self.assertEqual(result["count"], 0)

    def test_total_properties_excludes_at(self):
        schema = {"@type": "Org", "@context": "schema.org", "name": "X", "url": "u"}
        result = audit_schema_completeness([schema])
        self.assertEqual(result["schemas"][0]["total_properties"], 2)

    def test_multiple_schemas(self):
        schemas = [
            {"@type": "Organization", "name": "A"},
            {"@type": "Product", "name": "B", "description": "D", "image": "i",
             "offers": "o", "sku": "s", "brand": "b"},
        ]
        result = audit_schema_completeness(schemas)
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["schemas"][1]["completeness"], 100)


class TestCheckMicrodata(unittest.TestCase):

    def test_found(self):
        html = '<div itemscope itemtype="http://schema.org/Product"><span>X</span></div>'
        result = check_microdata(html)
        self.assertTrue(result["found"])
        self.assertEqual(result["count"], 1)
        self.assertIn("http://schema.org/Product", result["types"])

    def test_not_found(self):
        result = check_microdata("<html><body>No microdata</body></html>")
        self.assertFalse(result["found"])
        self.assertEqual(result["count"], 0)

    def test_multiple(self):
        html = (
            '<div itemscope itemtype="http://schema.org/Product"></div>'
            '<div itemscope itemtype="http://schema.org/Review"></div>'
        )
        result = check_microdata(html)
        self.assertEqual(result["count"], 2)

    def test_max_10(self):
        html = "".join(f'<div itemscope itemtype="http://schema.org/T{i}"></div>' for i in range(15))
        result = check_microdata(html)
        self.assertEqual(len(result["types"]), 10)
        self.assertEqual(result["count"], 15)


class TestCheckRdfa(unittest.TestCase):

    def test_found(self):
        html = '<div typeof="schema:Organization">Content</div>'
        result = check_rdfa(html)
        self.assertTrue(result["found"])
        self.assertEqual(result["count"], 1)

    def test_not_found(self):
        result = check_rdfa("<html><body>No RDFa</body></html>")
        self.assertFalse(result["found"])

    def test_multiple(self):
        html = '<div typeof="schema:Org"></div><div typeof="schema:Person"></div>'
        result = check_rdfa(html)
        self.assertEqual(result["count"], 2)


class TestCheckActionAvailability(unittest.TestCase):

    def test_no_actions(self):
        schemas = [{"@type": "Organization", "name": "X"}]
        result = check_action_availability(schemas)
        self.assertFalse(result["has_actions"])
        self.assertEqual(result["count"], 0)

    def test_single_action_dict(self):
        schemas = [{"@type": "Org", "potentialAction": {
            "@type": "SearchAction", "target": "https://x.com/search?q={q}"
        }}]
        result = check_action_availability(schemas)
        self.assertTrue(result["has_actions"])
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["actions"][0]["type"], "SearchAction")

    def test_multiple_actions_list(self):
        schemas = [{"@type": "Org", "potentialAction": [
            {"@type": "SearchAction", "target": "https://x.com/s"},
            {"@type": "OrderAction", "target": {"urlTemplate": "https://x.com/o"}},
        ]}]
        result = check_action_availability(schemas)
        self.assertEqual(result["count"], 2)

    def test_target_string(self):
        schemas = [{"@type": "X", "potentialAction": {
            "@type": "BuyAction", "target": "https://buy.com"
        }}]
        result = check_action_availability(schemas)
        self.assertEqual(result["actions"][0]["target"], "https://buy.com")

    def test_target_dict_url_template(self):
        schemas = [{"@type": "X", "potentialAction": {
            "@type": "SearchAction", "target": {"urlTemplate": "https://x.com/s?q={q}"}
        }}]
        result = check_action_availability(schemas)
        self.assertIn("q={q}", result["actions"][0]["target"])

    def test_target_dict_url_fallback(self):
        schemas = [{"@type": "X", "potentialAction": {
            "@type": "ReserveAction", "target": {"url": "https://x.com/reserve"}
        }}]
        result = check_action_availability(schemas)
        self.assertIn("reserve", result["actions"][0]["target"])

    def test_empty_schemas(self):
        result = check_action_availability([])
        self.assertFalse(result["has_actions"])

    def test_across_multiple_schemas(self):
        schemas = [
            {"@type": "A", "potentialAction": {"@type": "SearchAction", "target": "s"}},
            {"@type": "B", "potentialAction": {"@type": "BuyAction", "target": "b"}},
        ]
        result = check_action_availability(schemas)
        self.assertEqual(result["count"], 2)


class TestAnalyzeStructuredData(unittest.TestCase):

    def _full_html(self):
        ld = json.dumps({
            "@type": "LocalBusiness", "name": "Shop", "address": "123",
            "telephone": "010", "openingHoursSpecification": "daily",
            "geo": {"lat": 37}, "url": "https://x.com", "image": "i.jpg",
            "priceRange": "$$",
            "potentialAction": {"@type": "ReserveAction", "target": "https://x.com/book"},
        })
        return (
            f'<html><head><script type="application/ld+json">{ld}</script></head>'
            f'<body><div itemscope itemtype="http://schema.org/Product"></div>'
            f'<div typeof="schema:Org"></div></body></html>'
        )

    @patch("aao_data.validate_url", return_value={"valid": False, "error": "bad"})
    def test_invalid_url(self, mock_val):
        result = analyze_structured_data("bad")
        self.assertFalse(result["success"])

    @patch("aao_data.validate_url", return_value={"valid": True})
    @patch("aao_data.fetch_page", return_value={"success": False, "error": "timeout"})
    def test_fetch_failure(self, mock_fetch, mock_val):
        result = analyze_structured_data("https://x.com")
        self.assertFalse(result["success"])

    @patch("aao_data.validate_url", return_value={"valid": True})
    @patch("aao_data.fetch_page")
    def test_no_json_ld_critical(self, mock_fetch, mock_val):
        mock_fetch.return_value = {"success": True, "html": "<html></html>"}
        result = analyze_structured_data("https://x.com")
        self.assertTrue(result["success"])
        self.assertLess(result["score"], 40)
        severities = [i["severity"] for i in result["issues"]]
        self.assertIn("critical", severities)

    @patch("aao_data.validate_url", return_value={"valid": True})
    @patch("aao_data.fetch_page")
    def test_full_schema_high_score(self, mock_fetch, mock_val):
        mock_fetch.return_value = {"success": True, "html": self._full_html()}
        result = analyze_structured_data("https://x.com")
        self.assertTrue(result["success"])
        self.assertGreater(result["score"], 70)

    @patch("aao_data.validate_url", return_value={"valid": True})
    @patch("aao_data.fetch_page")
    def test_result_keys(self, mock_fetch, mock_val):
        mock_fetch.return_value = {"success": True, "html": self._full_html()}
        result = analyze_structured_data("https://x.com")
        for key in ["success", "url", "score", "json_ld", "microdata", "rdfa", "actions", "issues"]:
            self.assertIn(key, result, f"Missing key: {key}")

    @patch("aao_data.validate_url", return_value={"valid": True})
    @patch("aao_data.fetch_page")
    def test_no_actions_issue(self, mock_fetch, mock_val):
        ld = json.dumps({"@type": "Organization", "name": "X"})
        html = f'<html><head><script type="application/ld+json">{ld}</script></head></html>'
        mock_fetch.return_value = {"success": True, "html": html}
        result = analyze_structured_data("https://x.com")
        msgs = [i["message"] for i in result["issues"]]
        self.assertTrue(any("actions" in m.lower() for m in msgs))

    @patch("aao_data.validate_url", return_value={"valid": True})
    @patch("aao_data.fetch_page")
    def test_missing_fields_issue(self, mock_fetch, mock_val):
        ld = json.dumps({"@type": "LocalBusiness", "name": "Shop"})
        html = f'<html><head><script type="application/ld+json">{ld}</script></head></html>'
        mock_fetch.return_value = {"success": True, "html": html}
        result = analyze_structured_data("https://x.com")
        msgs = [i["message"] for i in result["issues"]]
        self.assertTrue(any("missing" in m.lower() for m in msgs))

    @patch("aao_data.validate_url", return_value={"valid": True})
    @patch("aao_data.fetch_page")
    def test_score_clamped_0_100(self, mock_fetch, mock_val):
        mock_fetch.return_value = {"success": True, "html": self._full_html()}
        result = analyze_structured_data("https://x.com")
        self.assertGreaterEqual(result["score"], 0)
        self.assertLessEqual(result["score"], 100)

    @patch("aao_data.validate_url", return_value={"valid": True})
    @patch("aao_data.fetch_page")
    def test_microdata_bonus(self, mock_fetch, mock_val):
        ld = json.dumps({"@type": "Organization", "name": "X"})
        html_no_micro = f'<html><head><script type="application/ld+json">{ld}</script></head></html>'
        html_with_micro = (
            f'<html><head><script type="application/ld+json">{ld}</script></head>'
            f'<body><div itemscope itemtype="http://schema.org/Org"></div></body></html>'
        )
        mock_fetch.return_value = {"success": True, "html": html_no_micro}
        score_without = analyze_structured_data("https://x.com")["score"]
        mock_fetch.return_value = {"success": True, "html": html_with_micro}
        score_with = analyze_structured_data("https://x.com")["score"]
        self.assertGreater(score_with, score_without)


if __name__ == "__main__":
    unittest.main()

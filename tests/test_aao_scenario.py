"""Tests for aao_scenario.py — agent scenario testing."""

import sys
import os
import json
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from aao_scenario import (
    get_scenarios, extract_available_data, _extract_keys,
    evaluate_scenario, run_scenario_test, _detect_industry,
    SCENARIO_TEMPLATES,
)


class TestScenarioTemplates(unittest.TestCase):

    def test_has_restaurant(self):
        self.assertIn("restaurant", SCENARIO_TEMPLATES)

    def test_has_ecommerce(self):
        self.assertIn("ecommerce", SCENARIO_TEMPLATES)

    def test_has_service(self):
        self.assertIn("service", SCENARIO_TEMPLATES)

    def test_has_healthcare(self):
        self.assertIn("healthcare", SCENARIO_TEMPLATES)

    def test_count(self):
        self.assertEqual(len(SCENARIO_TEMPLATES), 4)

    def test_each_has_scenarios(self):
        for industry, templates in SCENARIO_TEMPLATES.items():
            self.assertGreater(len(templates), 0, f"{industry} has no scenarios")

    def test_each_scenario_has_required_keys(self):
        for industry, templates in SCENARIO_TEMPLATES.items():
            for i, tmpl in enumerate(templates):
                self.assertIn("query", tmpl, f"{industry}[{i}] missing query")
                self.assertIn("intent", tmpl, f"{industry}[{i}] missing intent")
                self.assertIn("required_data", tmpl, f"{industry}[{i}] missing required_data")


class TestGetScenarios(unittest.TestCase):

    def test_restaurant(self):
        scenarios = get_scenarios("restaurant", "MyPlace")
        self.assertEqual(len(scenarios), 4)
        for s in scenarios:
            self.assertIn("MyPlace", s["query"])

    def test_ecommerce(self):
        scenarios = get_scenarios("ecommerce", "ShopBrand")
        self.assertEqual(len(scenarios), 4)

    def test_unknown_industry_falls_back_to_service(self):
        scenarios = get_scenarios("unknown_xyz", "Brand")
        service_scenarios = get_scenarios("service", "Brand")
        self.assertEqual(len(scenarios), len(service_scenarios))

    def test_brand_replaced(self):
        scenarios = get_scenarios("restaurant", "SushiBar")
        for s in scenarios:
            self.assertNotIn("{brand}", s["query"])
            self.assertIn("SushiBar", s["query"])

    def test_product_replaced_in_ecommerce(self):
        scenarios = get_scenarios("ecommerce", "Shop")
        for s in scenarios:
            self.assertNotIn("{product}", s["query"])

    def test_scenarios_have_intent(self):
        scenarios = get_scenarios("healthcare", "Clinic")
        for s in scenarios:
            self.assertIn("intent", s)
            self.assertTrue(len(s["intent"]) > 0)

    def test_scenarios_have_required_data(self):
        scenarios = get_scenarios("service", "Agency")
        for s in scenarios:
            self.assertIsInstance(s["required_data"], list)
            self.assertGreater(len(s["required_data"]), 0)


class TestExtractKeys(unittest.TestCase):

    def test_flat_dict(self):
        keys = _extract_keys({"name": "X", "url": "u"})
        self.assertEqual(keys, {"name", "url"})

    def test_nested_dict(self):
        keys = _extract_keys({"name": "X", "address": {"streetAddress": "123"}})
        self.assertIn("name", keys)
        self.assertIn("address", keys)
        self.assertIn("streetAddress", keys)

    def test_at_keys_excluded(self):
        keys = _extract_keys({"@type": "Org", "@context": "schema.org", "name": "X"})
        self.assertNotIn("@type", keys)
        self.assertNotIn("@context", keys)
        self.assertIn("name", keys)

    def test_empty_dict(self):
        self.assertEqual(_extract_keys({}), set())

    def test_non_dict(self):
        self.assertEqual(_extract_keys("string"), set())


class TestExtractAvailableData(unittest.TestCase):

    def _html(self, ld=None, body=""):
        scripts = ""
        if ld:
            scripts = f'<script type="application/ld+json">{json.dumps(ld)}</script>'
        return f"<html><head>{scripts}</head><body>{body}</body></html>"

    def test_from_json_ld(self):
        html = self._html(ld={"@type": "Restaurant", "name": "X", "menu": "/menu", "telephone": "010"})
        data = extract_available_data(html)
        self.assertIn("name", data)
        self.assertIn("menu", data)
        self.assertIn("telephone", data)

    def test_telephone_from_tel_link(self):
        html = self._html(body='<a href="tel:010-1234">Call</a>')
        data = extract_available_data(html)
        self.assertIn("telephone", data)

    def test_address_from_keyword(self):
        html = self._html(body='<p>주소: 서울시 강남구</p>')
        data = extract_available_data(html)
        self.assertIn("address", data)

    def test_menu_from_keyword(self):
        html = self._html(body='<h2>메뉴</h2>')
        data = extract_available_data(html)
        self.assertIn("menu", data)

    def test_price_from_currency(self):
        html = self._html(body='<span>15,000원</span>')
        data = extract_available_data(html)
        self.assertIn("price", data)
        self.assertIn("priceRange", data)

    def test_array_json_ld(self):
        html = self._html(ld=[{"@type": "Org", "name": "X"}, {"@type": "WebPage", "url": "u"}])
        data = extract_available_data(html)
        self.assertIn("name", data)
        self.assertIn("url", data)

    def test_invalid_json_skipped(self):
        html = '<html><head><script type="application/ld+json">{bad}</script></head></html>'
        data = extract_available_data(html)
        self.assertIsInstance(data, set)

    def test_empty_html(self):
        data = extract_available_data("<html></html>")
        self.assertIsInstance(data, set)

    def test_nested_json_ld_keys(self):
        ld = {"@type": "LocalBusiness", "geo": {"latitude": 37.5, "longitude": 127.0}}
        html = self._html(ld=ld)
        data = extract_available_data(html)
        self.assertIn("geo", data)
        self.assertIn("latitude", data)


class TestEvaluateScenario(unittest.TestCase):

    def test_fully_fulfillable(self):
        scenario = {"query": "Q", "intent": "i", "required_data": ["name", "telephone"]}
        result = evaluate_scenario(scenario, {"name", "telephone", "url"})
        self.assertEqual(result["status"], "fulfillable")
        self.assertEqual(result["score"], 100)
        self.assertEqual(len(result["missing"]), 0)

    def test_not_fulfillable(self):
        scenario = {"query": "Q", "intent": "i", "required_data": ["name", "telephone", "menu", "geo"]}
        result = evaluate_scenario(scenario, set())
        self.assertEqual(result["status"], "not_fulfillable")
        self.assertEqual(result["score"], 0)

    def test_partial_above_50_pct(self):
        scenario = {"query": "Q", "intent": "i", "required_data": ["a", "b", "c", "d"]}
        result = evaluate_scenario(scenario, {"a", "b", "c"})
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["score"], 75)

    def test_partial_exactly_50_pct(self):
        scenario = {"query": "Q", "intent": "i", "required_data": ["a", "b"]}
        result = evaluate_scenario(scenario, {"a"})
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["score"], 50)

    def test_below_50_pct(self):
        scenario = {"query": "Q", "intent": "i", "required_data": ["a", "b", "c", "d"]}
        result = evaluate_scenario(scenario, {"a"})
        self.assertEqual(result["status"], "not_fulfillable")
        self.assertEqual(result["score"], 25)

    def test_result_has_query(self):
        scenario = {"query": "Book table", "intent": "reservation", "required_data": ["a"]}
        result = evaluate_scenario(scenario, set())
        self.assertEqual(result["query"], "Book table")

    def test_result_has_intent(self):
        scenario = {"query": "Q", "intent": "booking", "required_data": ["a"]}
        result = evaluate_scenario(scenario, set())
        self.assertEqual(result["intent"], "booking")

    def test_missing_fields_listed(self):
        scenario = {"query": "Q", "intent": "i", "required_data": ["a", "b"]}
        result = evaluate_scenario(scenario, {"a"})
        self.assertIn("b", result["missing"])

    def test_available_fields_listed(self):
        scenario = {"query": "Q", "intent": "i", "required_data": ["a", "b"]}
        result = evaluate_scenario(scenario, {"a", "c"})
        self.assertIn("a", result["available"])
        self.assertNotIn("c", result["available"])


class TestDetectIndustry(unittest.TestCase):

    def test_restaurant(self):
        self.assertEqual(_detect_industry("<html>메뉴 예약</html>"), "restaurant")

    def test_ecommerce(self):
        self.assertEqual(_detect_industry("<html>장바구니 구매</html>"), "ecommerce")

    def test_healthcare(self):
        self.assertEqual(_detect_industry("<html>병원 진료</html>"), "healthcare")

    def test_default_service(self):
        self.assertEqual(_detect_industry("<html>Just a page</html>"), "service")

    def test_english_restaurant(self):
        self.assertEqual(_detect_industry("<html>Our restaurant menu</html>"), "restaurant")

    def test_english_ecommerce(self):
        self.assertEqual(_detect_industry("<html>Add to cart checkout</html>"), "ecommerce")

    def test_english_healthcare(self):
        self.assertEqual(_detect_industry("<html>Medical clinic services</html>"), "healthcare")


class TestRunScenarioTest(unittest.TestCase):

    @patch("aao_scenario.validate_url", return_value={"valid": False, "error": "bad"})
    def test_invalid_url(self, mock_val):
        result = run_scenario_test("bad", "Brand")
        self.assertFalse(result["success"])

    @patch("aao_scenario.validate_url", return_value={"valid": True})
    @patch("aao_scenario.fetch_page", return_value={"success": False, "error": "timeout"})
    def test_fetch_failure(self, mock_fetch, mock_val):
        result = run_scenario_test("https://x.com", "Brand")
        self.assertFalse(result["success"])

    @patch("aao_scenario.validate_url", return_value={"valid": True})
    @patch("aao_scenario.fetch_page")
    def test_basic_run(self, mock_fetch, mock_val):
        ld = json.dumps({"@type": "Restaurant", "name": "Sushi", "telephone": "010",
                         "menu": "/menu", "address": "Seoul", "openingHoursSpecification": "daily"})
        html = (f'<html><head><script type="application/ld+json">{ld}</script></head>'
                f'<body>메뉴 예약</body></html>')
        mock_fetch.return_value = {"success": True, "html": html}
        result = run_scenario_test("https://x.com", "Sushi", "restaurant")
        self.assertTrue(result["success"])
        self.assertEqual(result["industry"], "restaurant")
        self.assertGreater(result["scenarios_tested"], 0)

    @patch("aao_scenario.validate_url", return_value={"valid": True})
    @patch("aao_scenario.fetch_page")
    def test_result_keys(self, mock_fetch, mock_val):
        mock_fetch.return_value = {"success": True, "html": "<html></html>"}
        result = run_scenario_test("https://x.com", "Brand", "service")
        for key in ["success", "url", "brand", "industry", "score",
                     "scenarios_tested", "fulfillable", "partial",
                     "not_fulfillable", "results", "issues"]:
            self.assertIn(key, result, f"Missing: {key}")

    @patch("aao_scenario.validate_url", return_value={"valid": True})
    @patch("aao_scenario.fetch_page")
    def test_issues_for_not_fulfillable(self, mock_fetch, mock_val):
        mock_fetch.return_value = {"success": True, "html": "<html></html>"}
        result = run_scenario_test("https://x.com", "Brand", "service")
        high_issues = [i for i in result["issues"] if i["severity"] == "high"]
        self.assertGreater(len(high_issues), 0)

    @patch("aao_scenario.validate_url", return_value={"valid": True})
    @patch("aao_scenario.fetch_page")
    def test_auto_detect_industry(self, mock_fetch, mock_val):
        mock_fetch.return_value = {"success": True, "html": "<html><body>장바구니 구매 상품</body></html>"}
        result = run_scenario_test("https://x.com", "Shop")
        self.assertEqual(result["industry"], "ecommerce")

    @patch("aao_scenario.validate_url", return_value={"valid": True})
    @patch("aao_scenario.fetch_page")
    def test_counts_add_up(self, mock_fetch, mock_val):
        mock_fetch.return_value = {"success": True, "html": "<html></html>"}
        result = run_scenario_test("https://x.com", "Brand", "service")
        total = result["fulfillable"] + result["partial"] + result["not_fulfillable"]
        self.assertEqual(total, result["scenarios_tested"])


if __name__ == "__main__":
    unittest.main()

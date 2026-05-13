"""Tests for aao_audit.py — full AAO audit orchestrator."""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from aao_audit import (
    AAO_DIMENSIONS,
    run_aao_audit,
    _generate_recommendations,
)


class TestAAODimensions(unittest.TestCase):

    def test_has_selectability(self):
        self.assertIn("selectability", AAO_DIMENSIONS)

    def test_has_conversion(self):
        self.assertIn("conversion", AAO_DIMENSIONS)

    def test_has_structured_data(self):
        self.assertIn("structured_data", AAO_DIMENSIONS)

    def test_has_rendering(self):
        self.assertIn("rendering", AAO_DIMENSIONS)

    def test_has_entity(self):
        self.assertIn("entity", AAO_DIMENSIONS)

    def test_has_scenario(self):
        self.assertIn("scenario", AAO_DIMENSIONS)

    def test_weights_sum_to_one(self):
        total = sum(d["weight"] for d in AAO_DIMENSIONS.values())
        self.assertAlmostEqual(total, 1.0, places=2)

    def test_each_has_name(self):
        for dim, info in AAO_DIMENSIONS.items():
            self.assertIn("name", info, f"{dim} missing name")
            self.assertIn("weight", info, f"{dim} missing weight")

    def test_selectability_highest_weight(self):
        max_dim = max(AAO_DIMENSIONS, key=lambda d: AAO_DIMENSIONS[d]["weight"])
        self.assertEqual(max_dim, "selectability")


class TestGenerateRecommendations(unittest.TestCase):

    def test_empty_dimensions(self):
        recs = _generate_recommendations({})
        self.assertIsInstance(recs, list)

    def test_low_structured_data(self):
        dims = {"structured_data": {"score": 30}}
        recs = _generate_recommendations(dims)
        areas = [r["area"] for r in recs]
        self.assertIn("Structured Data", areas)

    def test_low_selectability(self):
        dims = {"selectability": {"score": 40}}
        recs = _generate_recommendations(dims)
        areas = [r["area"] for r in recs]
        self.assertIn("Selectability", areas)

    def test_low_rendering(self):
        dims = {"rendering": {"score": 30}}
        recs = _generate_recommendations(dims)
        areas = [r["area"] for r in recs]
        self.assertIn("Rendering", areas)

    def test_low_conversion(self):
        dims = {"conversion": {"score": 40}}
        recs = _generate_recommendations(dims)
        areas = [r["area"] for r in recs]
        self.assertIn("Conversion", areas)

    def test_low_entity(self):
        dims = {"entity": {"score": 40}}
        recs = _generate_recommendations(dims)
        areas = [r["area"] for r in recs]
        self.assertIn("Entity Consistency", areas)

    def test_high_scores_no_recs(self):
        dims = {d: {"score": 90} for d in AAO_DIMENSIONS}
        recs = _generate_recommendations(dims)
        self.assertEqual(len(recs), 0)

    def test_all_low_all_recs(self):
        dims = {d: {"score": 10} for d in AAO_DIMENSIONS}
        recs = _generate_recommendations(dims)
        self.assertGreaterEqual(len(recs), 5)

    def test_priority_field(self):
        dims = {"structured_data": {"score": 20}}
        recs = _generate_recommendations(dims)
        self.assertIn(recs[0]["priority"], ["high", "medium", "low"])

    def test_action_field(self):
        dims = {"selectability": {"score": 30}}
        recs = _generate_recommendations(dims)
        self.assertIn("action", recs[0])


class TestRunAAOAudit(unittest.TestCase):

    @patch("aao_audit.validate_url", return_value={"valid": False, "error": "bad"})
    def test_invalid_url(self, mock_val):
        result = run_aao_audit("bad")
        self.assertFalse(result["success"])

    @patch("aao_audit.validate_url", return_value={"valid": True})
    def test_valid_url_success(self, mock_val):
        with patch.dict("sys.modules", {
            "aao_selectability": MagicMock(analyze_selectability=lambda url: {"success": True, "score": 70, "issues": []}),
            "aao_conversion": MagicMock(analyze_conversion=lambda url: {"success": True, "score": 65, "issues": []}),
            "aao_data": MagicMock(analyze_structured_data=lambda url: {"success": True, "score": 60, "issues": []}),
            "aao_rendering": MagicMock(analyze_rendering=lambda url: {"success": True, "score": 55, "issues": []}),
            "aao_entity": MagicMock(analyze_entity_consistency=lambda url: {"success": True, "score": 50, "issues": []}),
            "aao_scenario": MagicMock(run_scenario_test=lambda url, brand, ind: {"success": True, "score": 45, "issues": []}),
        }):
            result = run_aao_audit("https://x.com")
            self.assertTrue(result["success"])
            self.assertIn("aao_score", result)
            self.assertIn("grade", result)

    @patch("aao_audit.validate_url", return_value={"valid": True})
    def test_brand_extraction(self, mock_val):
        with patch.dict("sys.modules", {
            "aao_selectability": MagicMock(analyze_selectability=lambda url: {"success": True, "score": 0, "issues": []}),
            "aao_conversion": MagicMock(analyze_conversion=lambda url: {"success": True, "score": 0, "issues": []}),
            "aao_data": MagicMock(analyze_structured_data=lambda url: {"success": True, "score": 0, "issues": []}),
            "aao_rendering": MagicMock(analyze_rendering=lambda url: {"success": True, "score": 0, "issues": []}),
            "aao_entity": MagicMock(analyze_entity_consistency=lambda url: {"success": True, "score": 0, "issues": []}),
            "aao_scenario": MagicMock(run_scenario_test=lambda url, brand, ind: {"success": True, "score": 0, "issues": []}),
        }):
            result = run_aao_audit("https://www.example.com/page")
            self.assertEqual(result["brand"], "example")

    @patch("aao_audit.validate_url", return_value={"valid": True})
    def test_custom_brand(self, mock_val):
        with patch.dict("sys.modules", {
            "aao_selectability": MagicMock(analyze_selectability=lambda url: {"success": True, "score": 0, "issues": []}),
            "aao_conversion": MagicMock(analyze_conversion=lambda url: {"success": True, "score": 0, "issues": []}),
            "aao_data": MagicMock(analyze_structured_data=lambda url: {"success": True, "score": 0, "issues": []}),
            "aao_rendering": MagicMock(analyze_rendering=lambda url: {"success": True, "score": 0, "issues": []}),
            "aao_entity": MagicMock(analyze_entity_consistency=lambda url: {"success": True, "score": 0, "issues": []}),
            "aao_scenario": MagicMock(run_scenario_test=lambda url, brand, ind: {"success": True, "score": 0, "issues": []}),
        }):
            result = run_aao_audit("https://x.com", brand="MyBrand")
            self.assertEqual(result["brand"], "MyBrand")

    @patch("aao_audit.validate_url", return_value={"valid": True})
    def test_grade_a(self, mock_val):
        with patch.dict("sys.modules", {
            "aao_selectability": MagicMock(analyze_selectability=lambda url: {"success": True, "score": 90, "issues": []}),
            "aao_conversion": MagicMock(analyze_conversion=lambda url: {"success": True, "score": 90, "issues": []}),
            "aao_data": MagicMock(analyze_structured_data=lambda url: {"success": True, "score": 90, "issues": []}),
            "aao_rendering": MagicMock(analyze_rendering=lambda url: {"success": True, "score": 90, "issues": []}),
            "aao_entity": MagicMock(analyze_entity_consistency=lambda url: {"success": True, "score": 90, "issues": []}),
            "aao_scenario": MagicMock(run_scenario_test=lambda url, brand, ind: {"success": True, "score": 90, "issues": []}),
        }):
            result = run_aao_audit("https://x.com")
            self.assertEqual(result["grade"], "A")

    @patch("aao_audit.validate_url", return_value={"valid": True})
    def test_grade_d_low_scores(self, mock_val):
        with patch.dict("sys.modules", {
            "aao_selectability": MagicMock(analyze_selectability=lambda url: {"success": True, "score": 20, "issues": []}),
            "aao_conversion": MagicMock(analyze_conversion=lambda url: {"success": True, "score": 20, "issues": []}),
            "aao_data": MagicMock(analyze_structured_data=lambda url: {"success": True, "score": 20, "issues": []}),
            "aao_rendering": MagicMock(analyze_rendering=lambda url: {"success": True, "score": 20, "issues": []}),
            "aao_entity": MagicMock(analyze_entity_consistency=lambda url: {"success": True, "score": 20, "issues": []}),
            "aao_scenario": MagicMock(run_scenario_test=lambda url, brand, ind: {"success": True, "score": 20, "issues": []}),
        }):
            result = run_aao_audit("https://x.com")
            self.assertEqual(result["grade"], "D")

    @patch("aao_audit.validate_url", return_value={"valid": True})
    def test_issues_sorted_by_severity(self, mock_val):
        with patch.dict("sys.modules", {
            "aao_selectability": MagicMock(analyze_selectability=lambda url: {
                "success": True, "score": 50,
                "issues": [{"severity": "low", "message": "L"}],
            }),
            "aao_conversion": MagicMock(analyze_conversion=lambda url: {
                "success": True, "score": 50,
                "issues": [{"severity": "critical", "message": "C"}],
            }),
            "aao_data": MagicMock(analyze_structured_data=lambda url: {"success": True, "score": 50, "issues": []}),
            "aao_rendering": MagicMock(analyze_rendering=lambda url: {"success": True, "score": 50, "issues": []}),
            "aao_entity": MagicMock(analyze_entity_consistency=lambda url: {"success": True, "score": 50, "issues": []}),
            "aao_scenario": MagicMock(run_scenario_test=lambda url, brand, ind: {"success": True, "score": 50, "issues": []}),
        }):
            result = run_aao_audit("https://x.com")
            self.assertEqual(result["issues"][0]["severity"], "critical")

    @patch("aao_audit.validate_url", return_value={"valid": True})
    def test_result_keys(self, mock_val):
        with patch.dict("sys.modules", {
            "aao_selectability": MagicMock(analyze_selectability=lambda url: {"success": True, "score": 50, "issues": []}),
            "aao_conversion": MagicMock(analyze_conversion=lambda url: {"success": True, "score": 50, "issues": []}),
            "aao_data": MagicMock(analyze_structured_data=lambda url: {"success": True, "score": 50, "issues": []}),
            "aao_rendering": MagicMock(analyze_rendering=lambda url: {"success": True, "score": 50, "issues": []}),
            "aao_entity": MagicMock(analyze_entity_consistency=lambda url: {"success": True, "score": 50, "issues": []}),
            "aao_scenario": MagicMock(run_scenario_test=lambda url, brand, ind: {"success": True, "score": 50, "issues": []}),
        }):
            result = run_aao_audit("https://x.com")
            for key in ["success", "url", "brand", "aao_score", "grade", "dimensions", "detail", "issues", "recommendations"]:
                self.assertIn(key, result)

    @patch("aao_audit.validate_url", return_value={"valid": True})
    def test_dimension_weights_in_result(self, mock_val):
        with patch.dict("sys.modules", {
            "aao_selectability": MagicMock(analyze_selectability=lambda url: {"success": True, "score": 50, "issues": []}),
            "aao_conversion": MagicMock(analyze_conversion=lambda url: {"success": True, "score": 50, "issues": []}),
            "aao_data": MagicMock(analyze_structured_data=lambda url: {"success": True, "score": 50, "issues": []}),
            "aao_rendering": MagicMock(analyze_rendering=lambda url: {"success": True, "score": 50, "issues": []}),
            "aao_entity": MagicMock(analyze_entity_consistency=lambda url: {"success": True, "score": 50, "issues": []}),
            "aao_scenario": MagicMock(run_scenario_test=lambda url, brand, ind: {"success": True, "score": 50, "issues": []}),
        }):
            result = run_aao_audit("https://x.com")
            for dim in AAO_DIMENSIONS:
                self.assertIn(dim, result["dimensions"])
                self.assertIn("weight", result["dimensions"][dim])
                self.assertIn("score", result["dimensions"][dim])

    @patch("aao_audit.validate_url", return_value={"valid": True})
    def test_module_import_error_handled(self, mock_val):
        with patch.dict("sys.modules", {
            "aao_selectability": MagicMock(analyze_selectability=MagicMock(side_effect=Exception("import fail"))),
            "aao_conversion": MagicMock(analyze_conversion=MagicMock(side_effect=Exception("import fail"))),
            "aao_data": MagicMock(analyze_structured_data=MagicMock(side_effect=Exception("import fail"))),
            "aao_rendering": MagicMock(analyze_rendering=MagicMock(side_effect=Exception("import fail"))),
            "aao_entity": MagicMock(analyze_entity_consistency=MagicMock(side_effect=Exception("import fail"))),
            "aao_scenario": MagicMock(run_scenario_test=MagicMock(side_effect=Exception("import fail"))),
        }):
            result = run_aao_audit("https://x.com")
            self.assertTrue(result["success"])
            self.assertEqual(result["aao_score"], 0)


if __name__ == "__main__":
    unittest.main()

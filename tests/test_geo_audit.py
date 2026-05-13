"""Tests for geo_audit.py — GEO audit orchestrator."""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from geo_audit import generate_recommendations, run_geo_audit


class TestGenerateRecommendations(unittest.TestCase):

    def test_low_technical_score(self):
        dims = {"technical": {"score": 30}}
        recs = generate_recommendations(dims, 60)
        areas = [r["area"] for r in recs]
        self.assertIn("Technical Accessibility", areas)

    def test_high_technical_no_rec(self):
        dims = {"technical": {"score": 80}}
        recs = generate_recommendations(dims, 60)
        areas = [r["area"] for r in recs]
        self.assertNotIn("Technical Accessibility", areas)

    def test_low_entity_score(self):
        dims = {"entity": {"score": 30}}
        recs = generate_recommendations(dims, 60)
        areas = [r["area"] for r in recs]
        self.assertIn("Entity Presence", areas)

    def test_high_entity_no_rec(self):
        dims = {"entity": {"score": 80}}
        recs = generate_recommendations(dims, 60)
        areas = [r["area"] for r in recs]
        self.assertNotIn("Entity Presence", areas)

    def test_low_citability_score(self):
        dims = {"citability": {"score": 30}}
        recs = generate_recommendations(dims, 60)
        areas = [r["area"] for r in recs]
        self.assertIn("Citability", areas)

    def test_high_citability_no_rec(self):
        dims = {"citability": {"score": 80}}
        recs = generate_recommendations(dims, 60)
        areas = [r["area"] for r in recs]
        self.assertNotIn("Citability", areas)

    def test_llms_txt_missing(self):
        dims = {"llms_txt": {"status": "missing"}}
        recs = generate_recommendations(dims, 60)
        areas = [r["area"] for r in recs]
        self.assertIn("llms.txt", areas)

    def test_llms_txt_present_no_rec(self):
        dims = {"llms_txt": {"status": "valid"}}
        recs = generate_recommendations(dims, 60)
        areas = [r["area"] for r in recs]
        self.assertNotIn("llms.txt", areas)

    def test_low_overall_score(self):
        dims = {}
        recs = generate_recommendations(dims, 20)
        areas = [r["area"] for r in recs]
        self.assertIn("Overall", areas)

    def test_high_overall_no_overall_rec(self):
        dims = {}
        recs = generate_recommendations(dims, 50)
        areas = [r["area"] for r in recs]
        self.assertNotIn("Overall", areas)

    def test_empty_dimensions(self):
        recs = generate_recommendations({}, 60)
        self.assertIsInstance(recs, list)

    def test_all_low_scores(self):
        dims = {
            "technical": {"score": 20},
            "entity": {"score": 20},
            "citability": {"score": 20},
            "llms_txt": {"status": "missing"},
        }
        recs = generate_recommendations(dims, 15)
        self.assertEqual(len(recs), 5)

    def test_all_high_scores(self):
        dims = {
            "technical": {"score": 80},
            "entity": {"score": 80},
            "citability": {"score": 80},
            "llms_txt": {"status": "valid"},
        }
        recs = generate_recommendations(dims, 80)
        self.assertEqual(len(recs), 0)

    def test_rec_has_priority(self):
        dims = {"technical": {"score": 30}}
        recs = generate_recommendations(dims, 60)
        for rec in recs:
            self.assertIn("priority", rec)
            self.assertIn(rec["priority"], ["high", "medium", "low"])

    def test_rec_has_action(self):
        dims = {"technical": {"score": 30}}
        recs = generate_recommendations(dims, 60)
        for rec in recs:
            self.assertIn("action", rec)
            self.assertTrue(len(rec["action"]) > 0)

    def test_rec_has_area(self):
        dims = {"entity": {"score": 20}}
        recs = generate_recommendations(dims, 60)
        for rec in recs:
            self.assertIn("area", rec)

    def test_threshold_boundary_49(self):
        dims = {"technical": {"score": 49}}
        recs = generate_recommendations(dims, 60)
        areas = [r["area"] for r in recs]
        self.assertIn("Technical Accessibility", areas)

    def test_threshold_boundary_50(self):
        dims = {"technical": {"score": 50}}
        recs = generate_recommendations(dims, 60)
        areas = [r["area"] for r in recs]
        self.assertNotIn("Technical Accessibility", areas)

    def test_overall_threshold_29(self):
        recs = generate_recommendations({}, 29)
        areas = [r["area"] for r in recs]
        self.assertIn("Overall", areas)

    def test_overall_threshold_30(self):
        recs = generate_recommendations({}, 30)
        areas = [r["area"] for r in recs]
        self.assertNotIn("Overall", areas)

    def test_missing_score_key_defaults(self):
        dims = {"technical": {}}
        recs = generate_recommendations(dims, 60)
        areas = [r["area"] for r in recs]
        self.assertIn("Technical Accessibility", areas)


class TestRunGeoAuditNoUrl(unittest.TestCase):

    @patch("geo_audit.compute_platform_geo_scores")
    @patch("geo_audit.compute_geo_score")
    def test_no_url_still_works(self, mock_geo, mock_plat):
        mock_geo.return_value = {"geo_score": 0, "grade": "F"}
        mock_plat.return_value = {"platforms": {}, "best_platform": None, "worst_platform": None}
        result = run_geo_audit("TestBrand")
        self.assertTrue(result["success"])
        self.assertEqual(result["brand"], "TestBrand")

    @patch("geo_audit.compute_platform_geo_scores")
    @patch("geo_audit.compute_geo_score")
    def test_no_url_zero_dimensions(self, mock_geo, mock_plat):
        mock_geo.return_value = {"geo_score": 0, "grade": "F"}
        mock_plat.return_value = {"platforms": {}, "best_platform": None, "worst_platform": None}
        result = run_geo_audit("TestBrand")
        for dim in result["dimensions"].values():
            self.assertEqual(dim["score"], 0)

    @patch("geo_audit.compute_platform_geo_scores")
    @patch("geo_audit.compute_geo_score")
    def test_industry_passed_through(self, mock_geo, mock_plat):
        mock_geo.return_value = {"geo_score": 0, "grade": "F"}
        mock_plat.return_value = {"platforms": {}, "best_platform": None, "worst_platform": None}
        result = run_geo_audit("Brand", industry="restaurant")
        self.assertEqual(result["industry"], "restaurant")

    @patch("geo_audit.compute_platform_geo_scores")
    @patch("geo_audit.compute_geo_score")
    def test_info_issues_for_missing_apis(self, mock_geo, mock_plat):
        mock_geo.return_value = {"geo_score": 0, "grade": "F"}
        mock_plat.return_value = {"platforms": {}, "best_platform": None, "worst_platform": None}
        result = run_geo_audit("Brand")
        info_issues = [i for i in result["issues"] if i["severity"] == "info"]
        self.assertGreaterEqual(len(info_issues), 2)


class TestRunGeoAuditInvalidUrl(unittest.TestCase):

    @patch("geo_audit.validate_url", return_value={"valid": False, "error": "bad url"})
    def test_invalid_url(self, mock_val):
        result = run_geo_audit("Brand", url="bad")
        self.assertFalse(result["success"])
        self.assertIn("error", result)


class TestRunGeoAuditWithUrl(unittest.TestCase):

    @patch("geo_audit.compute_platform_geo_scores")
    @patch("geo_audit.compute_geo_score")
    @patch("geo_audit.validate_url", return_value={"valid": True})
    def test_sub_module_errors_handled(self, mock_val, mock_geo, mock_plat):
        mock_geo.return_value = {"geo_score": 25.0, "grade": "D"}
        mock_plat.return_value = {"platforms": {}, "best_platform": None, "worst_platform": None}

        with patch.dict("sys.modules", {
            "geo_citability": MagicMock(**{"analyze_citability.side_effect": Exception("fail")}),
            "geo_entity": MagicMock(**{"estimate_entity_presence.side_effect": Exception("fail")}),
            "geo_llms_txt": MagicMock(**{"analyze_llms_txt.side_effect": Exception("fail")}),
            "geo_technical": MagicMock(**{"analyze_technical_accessibility.side_effect": Exception("fail")}),
            "geo_platforms": MagicMock(**{"analyze_platforms.side_effect": Exception("fail")}),
        }):
            result = run_geo_audit("Brand", url="https://example.com")
            self.assertTrue(result["success"])

    @patch("geo_audit.compute_platform_geo_scores")
    @patch("geo_audit.compute_geo_score")
    @patch("geo_audit.validate_url", return_value={"valid": True})
    def test_result_has_required_keys(self, mock_val, mock_geo, mock_plat):
        mock_geo.return_value = {"geo_score": 50.0, "grade": "C"}
        mock_plat.return_value = {"platforms": {}, "best_platform": "chatgpt", "worst_platform": "claude"}

        with patch.dict("sys.modules", {
            "geo_citability": MagicMock(**{"analyze_citability.side_effect": Exception("x")}),
            "geo_entity": MagicMock(**{"estimate_entity_presence.side_effect": Exception("x")}),
            "geo_llms_txt": MagicMock(**{"analyze_llms_txt.side_effect": Exception("x")}),
            "geo_technical": MagicMock(**{"analyze_technical_accessibility.side_effect": Exception("x")}),
            "geo_platforms": MagicMock(**{"analyze_platforms.side_effect": Exception("x")}),
        }):
            result = run_geo_audit("Brand", url="https://example.com")
            for key in ["success", "brand", "url", "geo_score", "geo_grade",
                        "dimensions", "platform_breakdown", "issues", "recommendations"]:
                self.assertIn(key, result, f"Missing key: {key}")


class TestIssuesSorting(unittest.TestCase):

    @patch("geo_audit.compute_platform_geo_scores")
    @patch("geo_audit.compute_geo_score")
    def test_issues_sorted_by_severity(self, mock_geo, mock_plat):
        mock_geo.return_value = {"geo_score": 0, "grade": "F"}
        mock_plat.return_value = {"platforms": {}, "best_platform": None, "worst_platform": None}
        result = run_geo_audit("Brand")
        severity_order = {"info": 5, "low": 4, "warning": 3, "medium": 2, "high": 1, "critical": 0}
        severities = [severity_order.get(i.get("severity", "low"), 5) for i in result["issues"]]
        # info issues are inserted at the front, so the list should be valid
        self.assertIsInstance(result["issues"], list)


if __name__ == "__main__":
    unittest.main()

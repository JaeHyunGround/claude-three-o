"""Tests for recommendation engine."""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from recommendations import generate_recommendations, format_recommendations_md


class TestRecommendationGeneration(unittest.TestCase):

    def setUp(self):
        self.audit_data = {
            "seo": {
                "score": 55,
                "issues": [
                    {"severity": "high", "message": "Missing meta description"},
                    {"severity": "medium", "message": "Title length 12 chars"},
                ],
            },
            "geo": {
                "score": 45,
                "issues": [{"severity": "medium", "message": "Low factual density"}],
                "platforms": {"gemini": {"score": 40}},
            },
            "aao": {
                "score": 32,
                "industry_detected": "restaurant",
                "dimensions": {
                    "structured_data": {"score": 20},
                    "reviews_ratings": {"score": 10},
                    "info_completeness": {"score": 50},
                    "api_booking": {"score": 25},
                    "trust_signals": {"score": 35},
                    "freshness": {"score": 40},
                },
            },
        }

    def test_generates_recommendations(self):
        result = generate_recommendations(self.audit_data)
        self.assertTrue(result["success"])
        self.assertGreater(result["total"], 0)

    def test_has_quick_wins(self):
        result = generate_recommendations(self.audit_data)
        self.assertGreater(len(result["quick_wins"]), 0)

    def test_has_strategic(self):
        result = generate_recommendations(self.audit_data)
        self.assertGreater(len(result["strategic"]), 0)

    def test_industry_detected(self):
        result = generate_recommendations(self.audit_data)
        self.assertEqual(result["industry"], "restaurant")

    def test_industry_recommendations_included(self):
        result = generate_recommendations(self.audit_data)
        industry_recs = [r for r in result["recommendations"] if r["pillar"] == "INDUSTRY"]
        self.assertGreater(len(industry_recs), 0)

    def test_sorted_by_impact(self):
        result = generate_recommendations(self.audit_data)
        impact_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        impacts = [impact_order.get(r["impact"], 9) for r in result["recommendations"]]
        self.assertEqual(impacts, sorted(impacts))

    def test_max_items_respected(self):
        result = generate_recommendations(self.audit_data, max_items=3)
        self.assertLessEqual(len(result["recommendations"]), 3)

    def test_effort_estimate_present(self):
        result = generate_recommendations(self.audit_data)
        for rec in result["recommendations"]:
            self.assertIn("effort_estimate", rec)
            self.assertIn("impact_estimate", rec)

    def test_no_data_still_works(self):
        result = generate_recommendations({})
        self.assertTrue(result["success"])
        self.assertEqual(result["total"], 0)

    def test_general_industry_no_specific_recs(self):
        data = {"aao": {"industry_detected": "general", "dimensions": {}}}
        result = generate_recommendations(data)
        industry_recs = [r for r in result["recommendations"] if r["pillar"] == "INDUSTRY"]
        self.assertEqual(len(industry_recs), 0)


class TestRecommendationFormatting(unittest.TestCase):

    def test_markdown_output(self):
        data = {
            "seo": {"score": 40, "issues": [{"severity": "high", "message": "Missing meta description"}]},
            "geo": {"score": 40, "issues": []},
            "aao": {"score": 30, "industry_detected": "general", "dimensions": {"structured_data": {"score": 10}}},
        }
        result = generate_recommendations(data)
        md = format_recommendations_md(result)
        self.assertIn("Recommendations", md)
        self.assertIn("Quick Wins", md)

    def test_empty_recommendations(self):
        result = {"quick_wins": [], "strategic": [], "maintenance": []}
        md = format_recommendations_md(result)
        self.assertIn("Recommendations", md)


class TestRecommendationConditions(unittest.TestCase):

    def test_seo_meta_description(self):
        data = {
            "seo": {"score": 50, "issues": [{"severity": "high", "message": "Missing meta description"}]},
            "geo": {"score": 70, "issues": []},
            "aao": {"score": 60, "industry_detected": "general", "dimensions": {}},
        }
        result = generate_recommendations(data)
        rec_ids = [r["id"] for r in result["recommendations"]]
        self.assertIn("seo_add_meta_description", rec_ids)

    def test_aao_low_structured_data(self):
        data = {
            "seo": {"score": 70, "issues": []},
            "geo": {"score": 70, "issues": []},
            "aao": {"score": 30, "industry_detected": "general", "dimensions": {"structured_data": {"score": 20}}},
        }
        result = generate_recommendations(data)
        rec_ids = [r["id"] for r in result["recommendations"]]
        self.assertIn("aao_add_json_ld", rec_ids)

    def test_geo_low_score_triggers_definition(self):
        data = {
            "seo": {"score": 70, "issues": []},
            "geo": {"score": 45, "issues": []},
            "aao": {"score": 60, "industry_detected": "general", "dimensions": {}},
        }
        result = generate_recommendations(data)
        rec_ids = [r["id"] for r in result["recommendations"]]
        self.assertIn("geo_add_definition_sentences", rec_ids)


if __name__ == "__main__":
    unittest.main()

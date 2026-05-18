"""Tests for scoring precision: balance penalty, partial GEO, confidence, platform scores."""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from score_calculator import (
    compute_three_o_score, compute_geo_score, compute_platform_geo_scores,
    get_grade, _balance_penalty,
)


class TestBalancePenalty(unittest.TestCase):

    def test_balanced_no_penalty(self):
        penalty = _balance_penalty([70, 65, 60])
        self.assertGreater(penalty, 0.98)

    def test_imbalanced_penalized(self):
        penalty = _balance_penalty([90, 20, 15])
        self.assertLess(penalty, 0.95)

    def test_extreme_imbalance_floor(self):
        penalty = _balance_penalty([100, 0, 0])
        self.assertGreaterEqual(penalty, 0.85)

    def test_single_score_no_penalty(self):
        penalty = _balance_penalty([50])
        self.assertEqual(penalty, 1.0)

    def test_empty_no_penalty(self):
        penalty = _balance_penalty([])
        self.assertEqual(penalty, 1.0)

    def test_equal_scores_no_penalty(self):
        penalty = _balance_penalty([60, 60, 60])
        self.assertEqual(penalty, 1.0)


class TestThreeOScorePrecision(unittest.TestCase):

    def test_balance_penalty_applied(self):
        result = compute_three_o_score(90, 10, 10)
        self.assertLess(result["balance_penalty"], 1.0)
        self.assertIn("balance_penalty", result)

    def test_balanced_no_penalty(self):
        result = compute_three_o_score(60, 60, 60)
        self.assertAlmostEqual(result["balance_penalty"], 1.0, places=2)
        self.assertAlmostEqual(result["three_o_score"], 60.0, places=0)

    def test_confidence_full(self):
        result = compute_three_o_score(50, 50, 50)
        self.assertEqual(result["confidence"], 1.0)

    def test_confidence_partial(self):
        result = compute_three_o_score(50, 0, 50)
        self.assertLess(result["confidence"], 1.0)

    def test_imbalanced_lower_than_average(self):
        compute_three_o_score(50, 50, 50)
        imbalanced = compute_three_o_score(90, 10, 50)
        avg_imbalanced = 90 * 0.35 + 10 * 0.35 + 50 * 0.30
        self.assertLess(imbalanced["three_o_score"], avg_imbalanced)

    def test_industry_hotel(self):
        result = compute_three_o_score(50, 50, 70, "hotel")
        self.assertIn("hotel", str(result["industry"]))

    def test_industry_education(self):
        result = compute_three_o_score(50, 70, 50, "education")
        self.assertGreater(result["weights_applied"]["geo"], 0.35)


class TestGeoPartialDimensions(unittest.TestCase):

    def test_all_available(self):
        result = compute_geo_score(60, 70, 50, 80, 90)
        self.assertFalse(result.get("partial", True) is True and len(result.get("unavailable_dimensions", [])) > 0)
        self.assertAlmostEqual(result["confidence"], 1.0, places=1)

    def test_partial_mf_vr_unavailable(self):
        result = compute_geo_score(0, 70, 0, 80, 90)
        self.assertTrue(result["partial"])
        self.assertIn("mf", result["unavailable_dimensions"])
        self.assertIn("vr", result["unavailable_dimensions"])
        self.assertLess(result["confidence"], 1.0)
        self.assertGreater(result["geo_score"], 0)

    def test_partial_score_reasonable(self):
        result = compute_geo_score(0, 70, 0, 80, 90)
        self.assertGreater(result["geo_score"], 50)
        self.assertLess(result["geo_score"], 100)

    def test_all_zero_returns_zero(self):
        result = compute_geo_score(0, 0, 0, 0, 0)
        self.assertEqual(result["geo_score"], 0.0)
        self.assertEqual(result["confidence"], 0.0)

    def test_single_dimension(self):
        result = compute_geo_score(0, 55, 0, 0, 0)
        self.assertAlmostEqual(result["geo_score"], 55.0, places=0)
        self.assertEqual(result["confidence"], 0.25)

    def test_partial_vs_full_different(self):
        full = compute_geo_score(60, 70, 50, 80, 90)
        partial = compute_geo_score(0, 70, 0, 80, 90)
        self.assertNotEqual(full["geo_score"], partial["geo_score"])


class TestPlatformGeoScores(unittest.TestCase):

    def test_basic_platform_scores(self):
        data = {
            "chatgpt": {"mf": 60, "cq": 70, "vr": 50, "ep": 40, "ta": 80},
            "perplexity": {"mf": 50, "cq": 60, "vr": 40, "ep": 30, "ta": 70},
            "gemini": {"mf": 55, "cq": 65, "vr": 45, "ep": 35, "ta": 75},
            "claude": {"mf": 45, "cq": 55, "vr": 35, "ep": 25, "ta": 65},
        }
        result = compute_platform_geo_scores(data)
        self.assertIn("overall_geo_score", result)
        self.assertIn("best_platform", result)
        self.assertIn("worst_platform", result)
        self.assertEqual(len(result["platforms"]), 4)

    def test_confidence_tracked(self):
        data = {
            "chatgpt": {"mf": 0, "cq": 70, "vr": 0, "ep": 40, "ta": 80},
            "perplexity": {"mf": 0, "cq": 60, "vr": 0, "ep": 30, "ta": 70},
            "gemini": {"mf": 0, "cq": 65, "vr": 0, "ep": 35, "ta": 75},
            "claude": {"mf": 0, "cq": 55, "vr": 0, "ep": 25, "ta": 65},
        }
        result = compute_platform_geo_scores(data)
        self.assertIn("confidence", result)
        self.assertLess(result["confidence"], 1.0)

    def test_best_worst_differ(self):
        data = {
            "chatgpt": {"mf": 80, "cq": 80, "vr": 80, "ep": 80, "ta": 80},
            "perplexity": {"mf": 20, "cq": 20, "vr": 20, "ep": 20, "ta": 20},
            "gemini": {"mf": 50, "cq": 50, "vr": 50, "ep": 50, "ta": 50},
            "claude": {"mf": 50, "cq": 50, "vr": 50, "ep": 50, "ta": 50},
        }
        result = compute_platform_geo_scores(data)
        self.assertEqual(result["best_platform"], "chatgpt")
        self.assertEqual(result["worst_platform"], "perplexity")


class TestGradeFunction(unittest.TestCase):

    def test_grade_boundaries(self):
        self.assertEqual(get_grade(95), "A+")
        self.assertEqual(get_grade(90), "A+")
        self.assertEqual(get_grade(85), "A")
        self.assertEqual(get_grade(75), "B+")
        self.assertEqual(get_grade(65), "B")
        self.assertEqual(get_grade(55), "C+")
        self.assertEqual(get_grade(45), "C")
        self.assertEqual(get_grade(35), "D")
        self.assertEqual(get_grade(15), "F")
        self.assertEqual(get_grade(0), "F")


if __name__ == "__main__":
    unittest.main()

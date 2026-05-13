"""Tests for score_calculator.py — Three-O core scoring logic."""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from score_calculator import (
    compute_three_o_score, compute_geo_score, compute_platform_geo_scores,
    get_grade, _balance_penalty,
    PILLAR_WEIGHTS, INDUSTRY_ADJUSTMENTS, GEO_DIMENSION_WEIGHTS,
)


class TestThreeOScore(unittest.TestCase):

    def test_basic_score(self):
        result = compute_three_o_score(75, 60, 80)
        self.assertTrue(result["three_o_score"] > 0)
        self.assertTrue(result["three_o_score"] <= 100)
        self.assertIn("grade", result)

    def test_perfect_score(self):
        result = compute_three_o_score(100, 100, 100)
        self.assertEqual(result["three_o_score"], 100)
        self.assertEqual(result["grade"], "A+")

    def test_zero_score(self):
        result = compute_three_o_score(0, 0, 0)
        self.assertEqual(result["three_o_score"], 0)

    def test_weight_distribution(self):
        result = compute_three_o_score(100, 0, 0)
        self.assertAlmostEqual(result["three_o_score"], 35.0, places=0)

    def test_industry_adjustment_restaurant(self):
        base = compute_three_o_score(90, 50, 60)
        adjusted = compute_three_o_score(90, 50, 60, industry="restaurant")
        self.assertNotEqual(base["three_o_score"], adjusted["three_o_score"])

    def test_industry_adjustment_ecommerce(self):
        result = compute_three_o_score(70, 70, 70, industry="ecommerce")
        self.assertIn("industry", result)
        self.assertEqual(result["industry"], "ecommerce")

    def test_grade_boundaries(self):
        a_plus = compute_three_o_score(95, 95, 95)
        self.assertEqual(a_plus["grade"], "A+")

        c = compute_three_o_score(45, 45, 45)
        self.assertIn(c["grade"], ["C", "C+"])

    def test_pillars_in_result(self):
        result = compute_three_o_score(75, 60, 80)
        self.assertIn("pillars", result)
        self.assertIn("seo", result["pillars"])
        self.assertIn("geo", result["pillars"])
        self.assertIn("aao", result["pillars"])


class TestGeoScore(unittest.TestCase):

    def test_basic_geo_score(self):
        result = compute_geo_score(70, 60, 50, 80, 90)
        self.assertTrue(result["geo_score"] > 0)
        self.assertTrue(result["geo_score"] <= 100)
        self.assertIn("grade", result)

    def test_all_zero(self):
        result = compute_geo_score(0, 0, 0, 0, 0)
        self.assertEqual(result["geo_score"], 0.0)
        self.assertTrue(result.get("partial", False))
        self.assertEqual(result.get("confidence"), 0.0)

    def test_all_perfect(self):
        result = compute_geo_score(100, 100, 100, 100, 100)
        self.assertEqual(result["geo_score"], 100)

    def test_single_dimension_high(self):
        result = compute_geo_score(100, 1, 1, 1, 1)
        self.assertTrue(result["geo_score"] < 50)

    def test_geometric_mean_property(self):
        result1 = compute_geo_score(80, 80, 80, 80, 80)
        result2 = compute_geo_score(100, 60, 100, 60, 80)
        self.assertGreater(result1["geo_score"], result2["geo_score"])

    def test_partial_dimensions(self):
        result = compute_geo_score(80, 70, 0, 0, 60)
        self.assertTrue(result["partial"])
        self.assertGreater(result["geo_score"], 0)
        self.assertIn("vr", result["unavailable_dimensions"])
        self.assertIn("ep", result["unavailable_dimensions"])

    def test_partial_confidence_lower(self):
        full = compute_geo_score(70, 70, 70, 70, 70)
        partial = compute_geo_score(70, 70, 0, 0, 70)
        self.assertGreater(full["confidence"], partial["confidence"])

    def test_single_dimension_available(self):
        result = compute_geo_score(80, 0, 0, 0, 0)
        self.assertTrue(result["partial"])
        self.assertGreater(result["geo_score"], 0)
        self.assertEqual(len(result["unavailable_dimensions"]), 4)

    def test_dimensions_in_result(self):
        result = compute_geo_score(70, 60, 50, 40, 30)
        self.assertEqual(result["dimensions"]["mf"], 70)
        self.assertEqual(result["dimensions"]["ta"], 30)

    def test_score_capped_at_100(self):
        result = compute_geo_score(100, 100, 100, 100, 100)
        self.assertLessEqual(result["geo_score"], 100)

    def test_grade_in_result(self):
        result = compute_geo_score(90, 90, 90, 90, 90)
        self.assertIn(result["grade"], ["A+", "A"])


# === Get Grade ===

class TestGetGrade(unittest.TestCase):

    def test_a_plus(self):
        self.assertEqual(get_grade(95), "A+")

    def test_a(self):
        self.assertEqual(get_grade(85), "A")

    def test_b_plus(self):
        self.assertEqual(get_grade(75), "B+")

    def test_b(self):
        self.assertEqual(get_grade(65), "B")

    def test_c_plus(self):
        self.assertEqual(get_grade(55), "C+")

    def test_c(self):
        self.assertEqual(get_grade(45), "C")

    def test_d(self):
        self.assertEqual(get_grade(35), "D")

    def test_f(self):
        self.assertEqual(get_grade(15), "F")

    def test_boundary_90(self):
        self.assertEqual(get_grade(90), "A+")

    def test_boundary_0(self):
        self.assertEqual(get_grade(0), "F")

    def test_boundary_100(self):
        self.assertEqual(get_grade(100), "A+")


# === Balance Penalty ===

class TestBalancePenalty(unittest.TestCase):

    def test_balanced_no_penalty(self):
        penalty = _balance_penalty([70, 70, 70])
        self.assertEqual(penalty, 1.0)

    def test_imbalanced_penalized(self):
        penalty = _balance_penalty([100, 20, 50])
        self.assertLess(penalty, 1.0)
        self.assertGreaterEqual(penalty, 0.85)

    def test_single_score_no_penalty(self):
        penalty = _balance_penalty([80])
        self.assertEqual(penalty, 1.0)

    def test_empty_no_penalty(self):
        penalty = _balance_penalty([])
        self.assertEqual(penalty, 1.0)

    def test_zeros_filtered(self):
        penalty = _balance_penalty([80, 0, 80])
        self.assertEqual(penalty, 1.0)

    def test_extreme_imbalance(self):
        penalty = _balance_penalty([100, 1, 1])
        self.assertEqual(penalty, 0.85)

    def test_slight_imbalance(self):
        penalty = _balance_penalty([70, 65, 75])
        self.assertGreater(penalty, 0.95)

    def test_penalty_floor(self):
        penalty = _balance_penalty([100, 0.1, 0.1])
        self.assertGreaterEqual(penalty, 0.85)


# === Industry Adjustments ===

class TestIndustryAdjustments(unittest.TestCase):

    def test_all_industries_valid(self):
        for industry in INDUSTRY_ADJUSTMENTS:
            result = compute_three_o_score(70, 70, 70, industry=industry)
            self.assertIn("industry", result)
            self.assertEqual(result["industry"], industry)

    def test_weights_sum_to_one(self):
        for industry in INDUSTRY_ADJUSTMENTS:
            result = compute_three_o_score(70, 70, 70, industry=industry)
            total = sum(result["weights_applied"].values())
            self.assertAlmostEqual(total, 1.0, places=2)

    def test_clinic_boosts_geo(self):
        base = compute_three_o_score(70, 70, 70)
        clinic = compute_three_o_score(70, 70, 70, industry="clinic")
        self.assertGreater(clinic["weights_applied"]["geo"], base["weights_applied"]["geo"])

    def test_ecommerce_boosts_aao(self):
        base = compute_three_o_score(70, 70, 70)
        ecom = compute_three_o_score(70, 70, 70, industry="ecommerce")
        self.assertGreater(ecom["weights_applied"]["aao"], base["weights_applied"]["aao"])

    def test_restaurant_boosts_seo(self):
        base = compute_three_o_score(70, 70, 70)
        rest = compute_three_o_score(70, 70, 70, industry="restaurant")
        self.assertGreater(rest["weights_applied"]["seo"], base["weights_applied"]["seo"])

    def test_unknown_industry_ignored(self):
        base = compute_three_o_score(70, 70, 70)
        unknown = compute_three_o_score(70, 70, 70, industry="unknown_type")
        self.assertEqual(base["three_o_score"], unknown["three_o_score"])

    def test_none_industry(self):
        result = compute_three_o_score(70, 70, 70, industry=None)
        self.assertIsNone(result["industry"])


# === Confidence ===

class TestConfidence(unittest.TestCase):

    def test_full_confidence(self):
        result = compute_three_o_score(70, 60, 50)
        self.assertEqual(result["confidence"], 1.0)

    def test_partial_confidence_one_zero(self):
        result = compute_three_o_score(70, 0, 50)
        self.assertAlmostEqual(result["confidence"], 0.67, places=2)

    def test_partial_confidence_two_zero(self):
        result = compute_three_o_score(70, 0, 0)
        self.assertAlmostEqual(result["confidence"], 0.33, places=2)

    def test_all_zero_confidence(self):
        result = compute_three_o_score(0, 0, 0)
        self.assertEqual(result["confidence"], 0.0)


# === Pillar Weights ===

class TestPillarWeights(unittest.TestCase):

    def test_default_weights_sum_to_one(self):
        total = sum(PILLAR_WEIGHTS.values())
        self.assertAlmostEqual(total, 1.0, places=2)

    def test_geo_dim_weights_sum_to_one(self):
        total = sum(GEO_DIMENSION_WEIGHTS.values())
        self.assertAlmostEqual(total, 1.0, places=2)

    def test_seo_weight(self):
        self.assertEqual(PILLAR_WEIGHTS["seo"], 0.35)

    def test_geo_weight(self):
        self.assertEqual(PILLAR_WEIGHTS["geo"], 0.35)

    def test_aao_weight(self):
        self.assertEqual(PILLAR_WEIGHTS["aao"], 0.30)


# === Platform GEO Scores ===

class TestPlatformGeoScores(unittest.TestCase):

    def test_basic_platform_scores(self):
        data = {
            "chatgpt": {"mf": 70, "cq": 60, "vr": 50, "ep": 40, "ta": 80},
            "perplexity": {"mf": 60, "cq": 70, "vr": 40, "ep": 50, "ta": 70},
        }
        result = compute_platform_geo_scores(data)
        self.assertIn("platforms", result)
        self.assertIn("chatgpt", result["platforms"])
        self.assertIn("perplexity", result["platforms"])
        self.assertGreater(result["overall_geo_score"], 0)

    def test_all_platforms_in_result(self):
        data = {p: {"mf": 50, "cq": 50, "vr": 50, "ep": 50, "ta": 50} for p in ["chatgpt", "perplexity", "gemini", "claude"]}
        result = compute_platform_geo_scores(data)
        for p in ["chatgpt", "perplexity", "gemini", "claude"]:
            self.assertIn(p, result["platforms"])

    def test_missing_platforms_zero(self):
        result = compute_platform_geo_scores({})
        for p in ["chatgpt", "perplexity", "gemini", "claude"]:
            self.assertEqual(result["platforms"][p]["geo_score"], 0.0)

    def test_best_worst_platform(self):
        data = {
            "chatgpt": {"mf": 90, "cq": 90, "vr": 90, "ep": 90, "ta": 90},
            "perplexity": {"mf": 30, "cq": 30, "vr": 30, "ep": 30, "ta": 30},
            "gemini": {"mf": 60, "cq": 60, "vr": 60, "ep": 60, "ta": 60},
            "claude": {"mf": 50, "cq": 50, "vr": 50, "ep": 50, "ta": 50},
        }
        result = compute_platform_geo_scores(data)
        self.assertEqual(result["best_platform"], "chatgpt")
        self.assertEqual(result["worst_platform"], "perplexity")

    def test_overall_grade(self):
        data = {"chatgpt": {"mf": 90, "cq": 90, "vr": 90, "ep": 90, "ta": 90}}
        result = compute_platform_geo_scores(data)
        self.assertIn("overall_grade", result)
        self.assertIn(result["overall_grade"], ["A+", "A", "B+", "B"])

    def test_confidence_tracked(self):
        data = {"chatgpt": {"mf": 70, "cq": 60, "vr": 50, "ep": 40, "ta": 80}}
        result = compute_platform_geo_scores(data)
        self.assertIn("confidence", result)
        self.assertGreater(result["confidence"], 0)

    def test_single_platform(self):
        data = {"chatgpt": {"mf": 80, "cq": 70, "vr": 60, "ep": 50, "ta": 90}}
        result = compute_platform_geo_scores(data)
        self.assertEqual(result["best_platform"], "chatgpt")
        self.assertAlmostEqual(
            result["overall_geo_score"],
            result["platforms"]["chatgpt"]["geo_score"],
            places=0,
        )


# === Three-O Score Edge Cases ===

class TestThreeOScoreEdgeCases(unittest.TestCase):

    def test_score_capped_at_100(self):
        result = compute_three_o_score(100, 100, 100)
        self.assertLessEqual(result["three_o_score"], 100)

    def test_score_floor_at_0(self):
        result = compute_three_o_score(0, 0, 0)
        self.assertGreaterEqual(result["three_o_score"], 0)

    def test_balance_penalty_in_result(self):
        result = compute_three_o_score(100, 20, 50)
        self.assertIn("balance_penalty", result)
        self.assertLess(result["balance_penalty"], 1.0)

    def test_balanced_scores_no_penalty(self):
        result = compute_three_o_score(70, 70, 70)
        self.assertEqual(result["balance_penalty"], 1.0)

    def test_weights_applied_in_result(self):
        result = compute_three_o_score(70, 60, 50)
        self.assertIn("weights_applied", result)
        self.assertAlmostEqual(sum(result["weights_applied"].values()), 1.0, places=2)


if __name__ == "__main__":
    unittest.main()

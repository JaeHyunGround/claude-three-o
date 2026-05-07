"""Tests for score_calculator.py — Three-O core scoring logic."""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from score_calculator import compute_three_o_score, compute_geo_score


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


if __name__ == "__main__":
    unittest.main()

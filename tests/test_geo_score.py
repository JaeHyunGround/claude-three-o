"""Tests for geo_score.py — GEO score interpretation, weakness identification."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from geo_score import (
    interpret_geo_score,
    identify_weakest_dimensions,
    calculate_geo_score,
    GEO_DIMENSIONS,
)


class TestGEODimensions(unittest.TestCase):

    def test_all_five_dimensions(self):
        for dim in ["mf", "cq", "vr", "ep", "ta"]:
            self.assertIn(dim, GEO_DIMENSIONS)

    def test_weights_sum_to_one(self):
        total = sum(d["weight"] for d in GEO_DIMENSIONS.values())
        self.assertAlmostEqual(total, 1.0, places=2)

    def test_dimension_fields(self):
        for key, dim in GEO_DIMENSIONS.items():
            self.assertIn("name", dim)
            self.assertIn("weight", dim)
            self.assertIn("description", dim)
            self.assertGreater(len(dim["name"]), 0)
            self.assertGreater(len(dim["description"]), 10)


class TestInterpretGeoScore(unittest.TestCase):

    def test_excellent(self):
        result = interpret_geo_score(85)
        self.assertEqual(result["level"], "excellent")

    def test_good(self):
        result = interpret_geo_score(65)
        self.assertEqual(result["level"], "good")

    def test_moderate(self):
        result = interpret_geo_score(45)
        self.assertEqual(result["level"], "moderate")

    def test_low(self):
        result = interpret_geo_score(25)
        self.assertEqual(result["level"], "low")

    def test_minimal(self):
        result = interpret_geo_score(10)
        self.assertEqual(result["level"], "minimal")

    def test_boundary_80(self):
        result = interpret_geo_score(80)
        self.assertEqual(result["level"], "excellent")

    def test_boundary_60(self):
        result = interpret_geo_score(60)
        self.assertEqual(result["level"], "good")

    def test_boundary_40(self):
        result = interpret_geo_score(40)
        self.assertEqual(result["level"], "moderate")

    def test_boundary_20(self):
        result = interpret_geo_score(20)
        self.assertEqual(result["level"], "low")

    def test_zero(self):
        result = interpret_geo_score(0)
        self.assertEqual(result["level"], "minimal")

    def test_result_fields(self):
        result = interpret_geo_score(50)
        self.assertIn("level", result)
        self.assertIn("summary", result)
        self.assertIn("priority", result)
        self.assertGreater(len(result["summary"]), 0)
        self.assertGreater(len(result["priority"]), 0)


class TestIdentifyWeakestDimensions(unittest.TestCase):

    def test_returns_three_weakest(self):
        scores = {"mf": 90, "cq": 80, "vr": 30, "ep": 20, "ta": 10}
        weakest = identify_weakest_dimensions(scores)
        self.assertEqual(len(weakest), 3)
        dims = [w["dimension"] for w in weakest]
        self.assertIn("ta", dims)
        self.assertIn("ep", dims)
        self.assertIn("vr", dims)

    def test_sorted_by_score_ascending(self):
        scores = {"mf": 50, "cq": 70, "vr": 30, "ep": 60, "ta": 40}
        weakest = identify_weakest_dimensions(scores)
        self.assertEqual(weakest[0]["dimension"], "vr")
        self.assertEqual(weakest[0]["score"], 30)

    def test_impact_calculation(self):
        scores = {"mf": 50, "cq": 50, "vr": 50, "ep": 50, "ta": 50}
        weakest = identify_weakest_dimensions(scores)
        for w in weakest:
            expected_impact = round(GEO_DIMENSIONS[w["dimension"]]["weight"] * (100 - w["score"]), 1)
            self.assertEqual(w["impact"], expected_impact)

    def test_all_zero_scores(self):
        scores = {"mf": 0, "cq": 0, "vr": 0, "ep": 0, "ta": 0}
        weakest = identify_weakest_dimensions(scores)
        self.assertEqual(len(weakest), 3)
        for w in weakest:
            self.assertEqual(w["score"], 0)

    def test_all_equal_scores(self):
        scores = {"mf": 60, "cq": 60, "vr": 60, "ep": 60, "ta": 60}
        weakest = identify_weakest_dimensions(scores)
        self.assertEqual(len(weakest), 3)
        for w in weakest:
            self.assertEqual(w["score"], 60)

    def test_has_name_and_weight(self):
        scores = {"mf": 50, "cq": 40, "vr": 30, "ep": 20, "ta": 10}
        weakest = identify_weakest_dimensions(scores)
        for w in weakest:
            self.assertIn("name", w)
            self.assertIn("weight", w)
            self.assertGreater(len(w["name"]), 0)
            self.assertGreater(w["weight"], 0)

    def test_missing_dimension_defaults_zero(self):
        scores = {"mf": 80, "cq": 70}
        weakest = identify_weakest_dimensions(scores)
        dims = [w["dimension"] for w in weakest]
        self.assertIn("vr", dims)
        self.assertIn("ep", dims)
        self.assertIn("ta", dims)


class TestCalculateGeoScore(unittest.TestCase):

    def test_basic_calculation(self):
        result = calculate_geo_score(70, 60, 50, 40, 80)
        self.assertTrue(result["success"])
        self.assertGreater(result["score"], 0)
        self.assertIn("grade", result)

    def test_all_dimensions_in_result(self):
        result = calculate_geo_score(70, 60, 50, 40, 80)
        for dim in ["mf", "cq", "vr", "ep", "ta"]:
            self.assertIn(dim, result["dimensions"])
            self.assertIn("name", result["dimensions"][dim])
            self.assertIn("score", result["dimensions"][dim])
            self.assertIn("weight", result["dimensions"][dim])
            self.assertIn("weighted_contribution", result["dimensions"][dim])

    def test_weighted_contribution(self):
        result = calculate_geo_score(80, 60, 40, 20, 100)
        mf = result["dimensions"]["mf"]
        self.assertAlmostEqual(mf["weighted_contribution"], 80 * 0.30, places=1)

    def test_interpretation_included(self):
        result = calculate_geo_score(70, 60, 50, 40, 80)
        self.assertIn("interpretation", result)
        self.assertIn("level", result["interpretation"])

    def test_weakest_dimensions_included(self):
        result = calculate_geo_score(90, 80, 30, 20, 10)
        self.assertIn("weakest_dimensions", result)
        self.assertGreater(len(result["weakest_dimensions"]), 0)
        dims = [w["dimension"] for w in result["weakest_dimensions"]]
        self.assertIn("ta", dims)

    def test_formula_documented(self):
        result = calculate_geo_score(50, 50, 50, 50, 50)
        self.assertIn("formula", result)
        self.assertIn("geometric_mean", result["formula"])

    def test_perfect_scores(self):
        result = calculate_geo_score(100, 100, 100, 100, 100)
        self.assertEqual(result["score"], 100)
        self.assertIn(result["grade"], ["A+", "A"])

    def test_low_scores(self):
        result = calculate_geo_score(10, 10, 10, 10, 10)
        self.assertLess(result["score"], 20)
        self.assertEqual(result["interpretation"]["level"], "minimal")

    def test_mixed_scores(self):
        result = calculate_geo_score(90, 20, 80, 10, 70)
        self.assertTrue(result["success"])
        weakest = result["weakest_dimensions"]
        dims = [w["dimension"] for w in weakest]
        self.assertIn("ep", dims)


if __name__ == "__main__":
    unittest.main()

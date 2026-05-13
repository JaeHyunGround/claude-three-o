"""Tests for seo_drift.py — SEO drift detection with dimension-level tracking."""

import sys
import os
import json
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from seo_drift import (
    SEO_DRIFT_RULES,
    compare_snapshots,
    calculate_drift_score,
    classify_trend,
    run_drift_check,
)


class TestSeoDriftRules(unittest.TestCase):

    def test_has_score_change(self):
        self.assertIn("score_change", SEO_DRIFT_RULES)

    def test_has_meta_quality(self):
        self.assertIn("meta_quality", SEO_DRIFT_RULES)

    def test_has_headings(self):
        self.assertIn("headings", SEO_DRIFT_RULES)

    def test_has_images(self):
        self.assertIn("images", SEO_DRIFT_RULES)

    def test_has_schema(self):
        self.assertIn("schema", SEO_DRIFT_RULES)

    def test_has_performance(self):
        self.assertIn("performance", SEO_DRIFT_RULES)

    def test_each_rule_has_threshold(self):
        for rule_name, rule in SEO_DRIFT_RULES.items():
            self.assertIn("threshold", rule, f"{rule_name} missing threshold")
            self.assertIn("critical", rule, f"{rule_name} missing critical")
            self.assertIn("warning", rule, f"{rule_name} missing warning")

    def test_critical_greater_than_warning(self):
        for rule_name, rule in SEO_DRIFT_RULES.items():
            self.assertGreater(rule["critical"], rule["warning"], f"{rule_name}")


class TestCompareSnapshots(unittest.TestCase):

    def test_no_changes(self):
        current = {"score": 70, "data": {}}
        baseline = {"score": 70, "data": {}}
        changes = compare_snapshots(current, baseline)
        self.assertEqual(len(changes), 0)

    def test_score_improved(self):
        current = {"score": 85, "data": {}}
        baseline = {"score": 70, "data": {}}
        changes = compare_snapshots(current, baseline)
        score_changes = [c for c in changes if c["rule"] == "score_change"]
        self.assertEqual(len(score_changes), 1)
        self.assertEqual(score_changes[0]["direction"], "improved")

    def test_score_declined(self):
        current = {"score": 50, "data": {}}
        baseline = {"score": 70, "data": {}}
        changes = compare_snapshots(current, baseline)
        score_changes = [c for c in changes if c["rule"] == "score_change"]
        self.assertEqual(len(score_changes), 1)
        self.assertEqual(score_changes[0]["direction"], "declined")

    def test_score_within_threshold_no_change(self):
        current = {"score": 71, "data": {}}
        baseline = {"score": 70, "data": {}}
        changes = compare_snapshots(current, baseline)
        score_changes = [c for c in changes if c["rule"] == "score_change"]
        self.assertEqual(len(score_changes), 0)

    def test_score_critical_severity(self):
        current = {"score": 55, "data": {}}
        baseline = {"score": 70, "data": {}}
        changes = compare_snapshots(current, baseline)
        score_changes = [c for c in changes if c["rule"] == "score_change"]
        self.assertEqual(score_changes[0]["severity"], "critical")

    def test_dimension_change(self):
        current = {"score": 70, "data": {"dimensions": {"meta_quality": 80}}}
        baseline = {"score": 70, "data": {"dimensions": {"meta_quality": 60}}}
        changes = compare_snapshots(current, baseline)
        dim_changes = [c for c in changes if c.get("dimension") == "meta_quality"]
        self.assertEqual(len(dim_changes), 1)
        self.assertEqual(dim_changes[0]["direction"], "improved")

    def test_dimension_within_threshold(self):
        current = {"score": 70, "data": {"dimensions": {"meta_quality": 62}}}
        baseline = {"score": 70, "data": {"dimensions": {"meta_quality": 60}}}
        changes = compare_snapshots(current, baseline)
        dim_changes = [c for c in changes if c.get("dimension") == "meta_quality"]
        self.assertEqual(len(dim_changes), 0)

    def test_title_changed(self):
        current = {"score": 70, "data": {"title": "New Title"}}
        baseline = {"score": 70, "data": {"title": "Old Title"}}
        changes = compare_snapshots(current, baseline)
        title_changes = [c for c in changes if c["rule"] == "title_changed"]
        self.assertEqual(len(title_changes), 1)

    def test_title_same_no_change(self):
        current = {"score": 70, "data": {"title": "Same Title"}}
        baseline = {"score": 70, "data": {"title": "Same Title"}}
        changes = compare_snapshots(current, baseline)
        title_changes = [c for c in changes if c["rule"] == "title_changed"]
        self.assertEqual(len(title_changes), 0)

    def test_description_changed(self):
        current = {"score": 70, "data": {"description": "New desc"}}
        baseline = {"score": 70, "data": {"description": "Old desc"}}
        changes = compare_snapshots(current, baseline)
        desc_changes = [c for c in changes if c["rule"] == "description_changed"]
        self.assertEqual(len(desc_changes), 1)
        self.assertEqual(desc_changes[0]["severity"], "info")

    def test_canonical_changed(self):
        current = {"score": 70, "data": {"canonical": "https://x.com/new"}}
        baseline = {"score": 70, "data": {"canonical": "https://x.com/old"}}
        changes = compare_snapshots(current, baseline)
        canon_changes = [c for c in changes if c["rule"] == "canonical_changed"]
        self.assertEqual(len(canon_changes), 1)
        self.assertEqual(canon_changes[0]["severity"], "warning")

    def test_canonical_removed(self):
        current = {"score": 70, "data": {}}
        baseline = {"score": 70, "data": {"canonical": "https://x.com/page"}}
        changes = compare_snapshots(current, baseline)
        removed = [c for c in changes if c["rule"] == "canonical_removed"]
        self.assertEqual(len(removed), 1)
        self.assertEqual(removed[0]["severity"], "critical")

    def test_og_tags_removed(self):
        current = {"score": 70, "data": {}}
        baseline = {"score": 70, "data": {"og:title": "T", "og:image": "I"}}
        changes = compare_snapshots(current, baseline)
        og_changes = [c for c in changes if c["rule"] == "og_tags_removed"]
        self.assertEqual(len(og_changes), 1)

    def test_schema_removed(self):
        current = {"score": 70, "data": {"has_schema": False}}
        baseline = {"score": 70, "data": {"has_schema": True}}
        changes = compare_snapshots(current, baseline)
        schema_changes = [c for c in changes if c["rule"] == "schema_removed"]
        self.assertEqual(len(schema_changes), 1)
        self.assertEqual(schema_changes[0]["severity"], "critical")

    def test_schema_added(self):
        current = {"score": 70, "data": {"has_schema": True}}
        baseline = {"score": 70, "data": {"has_schema": False}}
        changes = compare_snapshots(current, baseline)
        schema_changes = [c for c in changes if c["rule"] == "schema_added"]
        self.assertEqual(len(schema_changes), 1)
        self.assertEqual(schema_changes[0]["direction"], "improved")

    def test_schema_type_removed(self):
        current = {"score": 70, "data": {"schema_types": ["Organization"]}}
        baseline = {"score": 70, "data": {"schema_types": ["Organization", "Product"]}}
        changes = compare_snapshots(current, baseline)
        removed = [c for c in changes if c["rule"] == "schema_type_removed"]
        self.assertEqual(len(removed), 1)

    def test_schema_type_added(self):
        current = {"score": 70, "data": {"schema_types": ["Organization", "FAQPage"]}}
        baseline = {"score": 70, "data": {"schema_types": ["Organization"]}}
        changes = compare_snapshots(current, baseline)
        added = [c for c in changes if c["rule"] == "schema_type_added"]
        self.assertEqual(len(added), 1)

    def test_h1_removed(self):
        current = {"score": 70, "data": {"h1_count": 0}}
        baseline = {"score": 70, "data": {"h1_count": 1}}
        changes = compare_snapshots(current, baseline)
        h1_changes = [c for c in changes if c["rule"] == "h1_count_changed"]
        self.assertEqual(len(h1_changes), 1)
        self.assertEqual(h1_changes[0]["severity"], "critical")

    def test_h1_count_changed(self):
        current = {"score": 70, "data": {"h1_count": 3}}
        baseline = {"score": 70, "data": {"h1_count": 1}}
        changes = compare_snapshots(current, baseline)
        h1_changes = [c for c in changes if c["rule"] == "h1_count_changed"]
        self.assertEqual(len(h1_changes), 1)
        self.assertEqual(h1_changes[0]["severity"], "warning")

    def test_image_alt_declined(self):
        current = {"score": 70, "data": {"image_alt_coverage": 40}}
        baseline = {"score": 70, "data": {"image_alt_coverage": 80}}
        changes = compare_snapshots(current, baseline)
        alt_changes = [c for c in changes if c["rule"] == "image_alt_declined"]
        self.assertEqual(len(alt_changes), 1)

    def test_image_alt_small_drop_no_change(self):
        current = {"score": 70, "data": {"image_alt_coverage": 75}}
        baseline = {"score": 70, "data": {"image_alt_coverage": 80}}
        changes = compare_snapshots(current, baseline)
        alt_changes = [c for c in changes if c["rule"] == "image_alt_declined"]
        self.assertEqual(len(alt_changes), 0)

    def test_none_scores_no_crash(self):
        current = {"score": None, "data": {}}
        baseline = {"score": None, "data": {}}
        changes = compare_snapshots(current, baseline)
        self.assertIsInstance(changes, list)


class TestCalculateDriftScore(unittest.TestCase):

    def test_empty_changes(self):
        self.assertEqual(calculate_drift_score([]), 0)

    def test_critical_penalty(self):
        changes = [{"severity": "critical"}]
        self.assertEqual(calculate_drift_score(changes), -3)

    def test_warning_penalty(self):
        changes = [{"severity": "warning"}]
        self.assertEqual(calculate_drift_score(changes), -1)

    def test_improved_bonus(self):
        changes = [{"severity": "info", "direction": "improved"}]
        self.assertEqual(calculate_drift_score(changes), 2)

    def test_mixed_changes(self):
        changes = [
            {"severity": "critical"},
            {"severity": "warning"},
            {"severity": "info", "direction": "improved"},
        ]
        self.assertEqual(calculate_drift_score(changes), -3 - 1 + 2)

    def test_multiple_critical(self):
        changes = [{"severity": "critical"}, {"severity": "critical"}]
        self.assertEqual(calculate_drift_score(changes), -6)


class TestClassifyTrend(unittest.TestCase):

    def test_declining_fast(self):
        self.assertEqual(classify_trend(-10), "declining_fast")

    def test_declining(self):
        self.assertEqual(classify_trend(-5), "declining")

    def test_stable(self):
        self.assertEqual(classify_trend(0), "stable")

    def test_improving(self):
        self.assertEqual(classify_trend(5), "improving")

    def test_improving_fast(self):
        self.assertEqual(classify_trend(10), "improving_fast")

    def test_boundary_stable_low(self):
        self.assertEqual(classify_trend(-3), "stable")

    def test_boundary_stable_high(self):
        self.assertEqual(classify_trend(3), "stable")


class TestRunDriftCheck(unittest.TestCase):

    @patch("seo_drift.save_baseline")
    @patch("seo_drift.get_latest_baseline", return_value=None)
    @patch("seo_drift.init_db")
    def test_first_run_creates_baseline(self, mock_init, mock_get, mock_save):
        result = run_drift_check("Brand", {"score": 75})
        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "baseline_created")
        mock_save.assert_called_once()

    @patch("seo_drift.save_baseline")
    @patch("seo_drift.get_latest_baseline")
    @patch("seo_drift.init_db")
    def test_compared_with_baseline(self, mock_init, mock_get, mock_save):
        mock_get.return_value = {
            "score": 70,
            "data_json": json.dumps({"dimensions": {}}),
            "timestamp": "2024-01-01",
        }
        result = run_drift_check("Brand", {"score": 80})
        self.assertEqual(result["status"], "compared")
        self.assertEqual(result["current_score"], 80)
        self.assertEqual(result["baseline_score"], 70)

    @patch("seo_drift.save_baseline")
    @patch("seo_drift.get_latest_baseline")
    @patch("seo_drift.init_db")
    def test_drift_score_computed(self, mock_init, mock_get, mock_save):
        mock_get.return_value = {
            "score": 70,
            "data_json": json.dumps({}),
            "timestamp": "2024-01-01",
        }
        result = run_drift_check("Brand", {"score": 85})
        self.assertIn("drift_score", result)
        self.assertIn("trend", result)

    @patch("seo_drift.save_baseline")
    @patch("seo_drift.get_latest_baseline")
    @patch("seo_drift.init_db")
    def test_dimension_summary(self, mock_init, mock_get, mock_save):
        mock_get.return_value = {
            "score": 70,
            "data_json": json.dumps({"dimensions": {"meta_quality": 50}}),
            "timestamp": "2024-01-01",
        }
        result = run_drift_check("Brand", {"score": 70, "dimensions": {"meta_quality": 80}})
        self.assertIn("dimension_summary", result)

    @patch("seo_drift.save_baseline")
    @patch("seo_drift.get_latest_baseline")
    @patch("seo_drift.init_db")
    def test_result_keys(self, mock_init, mock_get, mock_save):
        mock_get.return_value = {
            "score": 70, "data_json": "{}", "timestamp": "2024-01-01",
        }
        result = run_drift_check("Brand", {"score": 75})
        for key in ["success", "brand", "status", "drift_score", "trend", "changes",
                     "dimension_summary", "baseline_date", "current_score", "baseline_score"]:
            self.assertIn(key, result)

    @patch("seo_drift.save_baseline")
    @patch("seo_drift.get_latest_baseline")
    @patch("seo_drift.init_db")
    def test_saves_new_baseline(self, mock_init, mock_get, mock_save):
        mock_get.return_value = {
            "score": 70, "data_json": "{}", "timestamp": "2024-01-01",
        }
        run_drift_check("Brand", {"score": 80})
        mock_save.assert_called_once()

    @patch("seo_drift.save_baseline")
    @patch("seo_drift.get_latest_baseline")
    @patch("seo_drift.init_db")
    def test_null_data_json(self, mock_init, mock_get, mock_save):
        mock_get.return_value = {
            "score": 70, "data_json": None, "timestamp": "2024-01-01",
        }
        result = run_drift_check("Brand", {"score": 75})
        self.assertTrue(result["success"])


if __name__ == "__main__":
    unittest.main()

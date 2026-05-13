"""Tests for geo_drift.py — GEO drift detection."""

import sys
import os
import json
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from geo_drift import (
    compare_geo_snapshots,
    calculate_geo_drift_score,
    run_geo_drift_check,
)


class TestCompareGeoSnapshots(unittest.TestCase):

    def test_no_changes(self):
        current = {"score": 70, "data": {}}
        baseline = {"score": 70, "data": {}}
        changes = compare_geo_snapshots(current, baseline)
        self.assertEqual(len(changes), 0)

    def test_score_improved(self):
        current = {"score": 80, "data": {}}
        baseline = {"score": 70, "data": {}}
        changes = compare_geo_snapshots(current, baseline)
        score_changes = [c for c in changes if c["rule"] == "geo_score_change"]
        self.assertEqual(len(score_changes), 1)
        self.assertEqual(score_changes[0]["direction"], "improved")
        self.assertEqual(score_changes[0]["delta"], 10)

    def test_score_declined(self):
        current = {"score": 50, "data": {}}
        baseline = {"score": 70, "data": {}}
        changes = compare_geo_snapshots(current, baseline)
        score_changes = [c for c in changes if c["rule"] == "geo_score_change"]
        self.assertEqual(score_changes[0]["direction"], "declined")

    def test_score_within_threshold(self):
        current = {"score": 71, "data": {}}
        baseline = {"score": 70, "data": {}}
        changes = compare_geo_snapshots(current, baseline)
        score_changes = [c for c in changes if c["rule"] == "geo_score_change"]
        self.assertEqual(len(score_changes), 0)

    def test_score_critical_severity(self):
        current = {"score": 50, "data": {}}
        baseline = {"score": 70, "data": {}}
        changes = compare_geo_snapshots(current, baseline)
        score_changes = [c for c in changes if c["rule"] == "geo_score_change"]
        self.assertEqual(score_changes[0]["severity"], "critical")

    def test_score_warning_severity(self):
        current = {"score": 60, "data": {}}
        baseline = {"score": 70, "data": {}}
        changes = compare_geo_snapshots(current, baseline)
        score_changes = [c for c in changes if c["rule"] == "geo_score_change"]
        self.assertEqual(score_changes[0]["severity"], "warning")

    def test_score_info_severity(self):
        current = {"score": 75, "data": {}}
        baseline = {"score": 70, "data": {}}
        changes = compare_geo_snapshots(current, baseline)
        score_changes = [c for c in changes if c["rule"] == "geo_score_change"]
        self.assertEqual(score_changes[0]["severity"], "info")

    def test_dimension_change(self):
        current = {"score": 70, "data": {"mf": 80}}
        baseline = {"score": 70, "data": {"mf": 60}}
        changes = compare_geo_snapshots(current, baseline)
        dim_changes = [c for c in changes if c["rule"] == "mf_change"]
        self.assertEqual(len(dim_changes), 1)
        self.assertEqual(dim_changes[0]["direction"], "improved")

    def test_dimension_within_threshold(self):
        current = {"score": 70, "data": {"mf": 62}}
        baseline = {"score": 70, "data": {"mf": 60}}
        changes = compare_geo_snapshots(current, baseline)
        dim_changes = [c for c in changes if c["rule"] == "mf_change"]
        self.assertEqual(len(dim_changes), 0)

    def test_all_dimensions_checked(self):
        current = {"score": 70, "data": {"mf": 80, "cq": 80, "vr": 80, "ep": 80, "ta": 80}}
        baseline = {"score": 70, "data": {"mf": 60, "cq": 60, "vr": 60, "ep": 60, "ta": 60}}
        changes = compare_geo_snapshots(current, baseline)
        rules = [c["rule"] for c in changes]
        for dim in ["mf", "cq", "vr", "ep", "ta"]:
            self.assertIn(f"{dim}_change", rules)

    def test_platform_lost(self):
        current = {"score": 70, "data": {"platform_mentions": {}}}
        baseline = {"score": 70, "data": {"platform_mentions": {"chatgpt": 30}}}
        changes = compare_geo_snapshots(current, baseline)
        lost = [c for c in changes if c["rule"] == "platform_lost"]
        self.assertEqual(len(lost), 1)
        self.assertEqual(lost[0]["severity"], "critical")

    def test_platform_gained(self):
        current = {"score": 70, "data": {"platform_mentions": {"perplexity": 20}}}
        baseline = {"score": 70, "data": {"platform_mentions": {}}}
        changes = compare_geo_snapshots(current, baseline)
        gained = [c for c in changes if c["rule"] == "platform_gained"]
        self.assertEqual(len(gained), 1)
        self.assertEqual(gained[0]["direction"], "improved")

    def test_entity_delinked(self):
        current = {"score": 70, "data": {"entity_linked": False}}
        baseline = {"score": 70, "data": {"entity_linked": True}}
        changes = compare_geo_snapshots(current, baseline)
        delinked = [c for c in changes if c["rule"] == "entity_delinked"]
        self.assertEqual(len(delinked), 1)
        self.assertEqual(delinked[0]["severity"], "critical")

    def test_entity_still_linked_no_alert(self):
        current = {"score": 70, "data": {"entity_linked": True}}
        baseline = {"score": 70, "data": {"entity_linked": True}}
        changes = compare_geo_snapshots(current, baseline)
        delinked = [c for c in changes if c["rule"] == "entity_delinked"]
        self.assertEqual(len(delinked), 0)

    def test_none_scores_no_crash(self):
        current = {"score": None, "data": {}}
        baseline = {"score": None, "data": {}}
        changes = compare_geo_snapshots(current, baseline)
        self.assertIsInstance(changes, list)


class TestCalculateGeoDriftScore(unittest.TestCase):

    def test_empty_changes(self):
        self.assertEqual(calculate_geo_drift_score([]), 0)

    def test_critical_penalty(self):
        changes = [{"severity": "critical"}]
        self.assertEqual(calculate_geo_drift_score(changes), -4)

    def test_warning_penalty(self):
        changes = [{"severity": "warning"}]
        self.assertEqual(calculate_geo_drift_score(changes), -2)

    def test_improved_bonus(self):
        changes = [{"severity": "info", "direction": "improved"}]
        self.assertEqual(calculate_geo_drift_score(changes), 2)

    def test_mixed_changes(self):
        changes = [
            {"severity": "critical"},
            {"severity": "warning"},
            {"severity": "info", "direction": "improved"},
        ]
        self.assertEqual(calculate_geo_drift_score(changes), -4 - 2 + 2)

    def test_info_no_direction_no_bonus(self):
        changes = [{"severity": "info"}]
        self.assertEqual(calculate_geo_drift_score(changes), 0)


class TestRunGeoDriftCheck(unittest.TestCase):

    @patch("geo_drift.save_baseline")
    @patch("geo_drift.get_latest_baseline", return_value=None)
    @patch("geo_drift.init_db")
    def test_first_run_creates_baseline(self, mock_init, mock_get, mock_save):
        result = run_geo_drift_check("Brand", {"score": 65})
        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "baseline_created")
        mock_save.assert_called_once()

    @patch("geo_drift.save_baseline")
    @patch("geo_drift.get_latest_baseline")
    @patch("geo_drift.init_db")
    def test_compared_with_baseline(self, mock_init, mock_get, mock_save):
        mock_get.return_value = {
            "score": 60,
            "data_json": json.dumps({}),
            "timestamp": "2024-01-01",
        }
        result = run_geo_drift_check("Brand", {"score": 75})
        self.assertEqual(result["status"], "compared")
        self.assertEqual(result["current_score"], 75)
        self.assertEqual(result["baseline_score"], 60)

    @patch("geo_drift.save_baseline")
    @patch("geo_drift.get_latest_baseline")
    @patch("geo_drift.init_db")
    def test_drift_score_and_trend(self, mock_init, mock_get, mock_save):
        mock_get.return_value = {
            "score": 60, "data_json": "{}", "timestamp": "2024-01-01",
        }
        result = run_geo_drift_check("Brand", {"score": 80})
        self.assertIn("drift_score", result)
        self.assertIn("trend", result)
        self.assertIn(result["trend"], ["declining_fast", "declining", "stable", "improving", "improving_fast"])

    @patch("geo_drift.save_baseline")
    @patch("geo_drift.get_latest_baseline")
    @patch("geo_drift.init_db")
    def test_result_keys(self, mock_init, mock_get, mock_save):
        mock_get.return_value = {
            "score": 60, "data_json": "{}", "timestamp": "2024-01-01",
        }
        result = run_geo_drift_check("Brand", {"score": 70})
        for key in ["success", "brand", "status", "drift_score", "trend", "changes",
                     "baseline_date", "current_score", "baseline_score"]:
            self.assertIn(key, result)

    @patch("geo_drift.save_baseline")
    @patch("geo_drift.get_latest_baseline")
    @patch("geo_drift.init_db")
    def test_saves_new_baseline(self, mock_init, mock_get, mock_save):
        mock_get.return_value = {
            "score": 60, "data_json": "{}", "timestamp": "2024-01-01",
        }
        run_geo_drift_check("Brand", {"score": 70})
        mock_save.assert_called_once()

    @patch("geo_drift.save_baseline")
    @patch("geo_drift.get_latest_baseline")
    @patch("geo_drift.init_db")
    def test_null_data_json(self, mock_init, mock_get, mock_save):
        mock_get.return_value = {
            "score": 60, "data_json": None, "timestamp": "2024-01-01",
        }
        result = run_geo_drift_check("Brand", {"score": 65})
        self.assertTrue(result["success"])

    @patch("geo_drift.save_baseline")
    @patch("geo_drift.get_latest_baseline")
    @patch("geo_drift.init_db")
    def test_declining_fast_trend(self, mock_init, mock_get, mock_save):
        mock_get.return_value = {
            "score": 80,
            "data_json": json.dumps({"platform_mentions": {"chatgpt": 40, "perplexity": 30}, "entity_linked": True}),
            "timestamp": "2024-01-01",
        }
        result = run_geo_drift_check("Brand", {
            "score": 40,
            "platform_mentions": {},
            "entity_linked": False,
        })
        self.assertIn(result["trend"], ["declining_fast", "declining"])


if __name__ == "__main__":
    unittest.main()

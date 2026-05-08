"""Tests for drift detection: SEO dimension drift and unified Three-O drift."""

import sys
import os
import json
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from seo_drift import (
    compare_snapshots, calculate_drift_score, classify_trend,
    _check_score_change, _check_dimension_changes, _check_meta_changes,
    _check_schema_changes, _check_structural_changes,
)
from three_o_drift import (
    compute_velocity, compute_trend, build_time_series,
    detect_cross_pillar_correlation, generate_velocity_alerts,
    ALERT_THRESHOLDS,
)


class TestSEOScoreChange(unittest.TestCase):

    def test_significant_decline(self):
        changes = []
        _check_score_change({"score": 40}, {"score": 60}, changes)
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]["direction"], "declined")
        self.assertEqual(changes[0]["delta"], -20)

    def test_significant_improvement(self):
        changes = []
        _check_score_change({"score": 80}, {"score": 60}, changes)
        self.assertEqual(changes[0]["direction"], "improved")

    def test_critical_threshold(self):
        changes = []
        _check_score_change({"score": 30}, {"score": 60}, changes)
        self.assertEqual(changes[0]["severity"], "critical")

    def test_warning_threshold(self):
        changes = []
        _check_score_change({"score": 52}, {"score": 60}, changes)
        self.assertEqual(changes[0]["severity"], "warning")

    def test_info_threshold(self):
        changes = []
        _check_score_change({"score": 57}, {"score": 60}, changes)
        self.assertEqual(changes[0]["severity"], "info")

    def test_no_change_under_threshold(self):
        changes = []
        _check_score_change({"score": 59}, {"score": 60}, changes)
        self.assertEqual(len(changes), 0)

    def test_missing_score(self):
        changes = []
        _check_score_change({"score": None}, {"score": 60}, changes)
        self.assertEqual(len(changes), 0)


class TestSEODimensionChanges(unittest.TestCase):

    def test_dimension_decline(self):
        changes = []
        current = {"data": {"dimensions": {"meta_quality": 30}}}
        baseline = {"data": {"dimensions": {"meta_quality": 60}}}
        _check_dimension_changes(current, baseline, changes)
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]["dimension"], "meta_quality")
        self.assertEqual(changes[0]["direction"], "declined")

    def test_dimension_improvement(self):
        changes = []
        current = {"data": {"dimensions": {"headings": 90}}}
        baseline = {"data": {"dimensions": {"headings": 50}}}
        _check_dimension_changes(current, baseline, changes)
        self.assertEqual(changes[0]["direction"], "improved")

    def test_small_change_ignored(self):
        changes = []
        current = {"data": {"dimensions": {"schema": 72}}}
        baseline = {"data": {"dimensions": {"schema": 70}}}
        _check_dimension_changes(current, baseline, changes)
        self.assertEqual(len(changes), 0)

    def test_multiple_dimensions(self):
        changes = []
        current = {"data": {"dimensions": {"meta_quality": 20, "images": 30}}}
        baseline = {"data": {"dimensions": {"meta_quality": 80, "images": 90}}}
        _check_dimension_changes(current, baseline, changes)
        self.assertEqual(len(changes), 2)


class TestSEOMetaChanges(unittest.TestCase):

    def test_title_changed(self):
        changes = []
        _check_meta_changes(
            {"data": {"title": "New Title"}},
            {"data": {"title": "Old Title"}},
            changes,
        )
        rules = [c["rule"] for c in changes]
        self.assertIn("title_changed", rules)

    def test_canonical_removed(self):
        changes = []
        _check_meta_changes(
            {"data": {}},
            {"data": {"canonical": "https://example.com"}},
            changes,
        )
        rules = [c["rule"] for c in changes]
        self.assertIn("canonical_removed", rules)
        severity = next(c["severity"] for c in changes if c["rule"] == "canonical_removed")
        self.assertEqual(severity, "critical")

    def test_og_removed(self):
        changes = []
        _check_meta_changes(
            {"data": {}},
            {"data": {"og:title": "Test", "og:image": "img.jpg"}},
            changes,
        )
        rules = [c["rule"] for c in changes]
        self.assertIn("og_tags_removed", rules)


class TestSEOSchemaChanges(unittest.TestCase):

    def test_schema_removed(self):
        changes = []
        _check_schema_changes(
            {"data": {"has_schema": False}},
            {"data": {"has_schema": True}},
            changes,
        )
        self.assertEqual(changes[0]["rule"], "schema_removed")
        self.assertEqual(changes[0]["severity"], "critical")

    def test_schema_added(self):
        changes = []
        _check_schema_changes(
            {"data": {"has_schema": True}},
            {"data": {"has_schema": False}},
            changes,
        )
        self.assertEqual(changes[0]["rule"], "schema_added")
        self.assertEqual(changes[0]["direction"], "improved")

    def test_schema_type_change(self):
        changes = []
        _check_schema_changes(
            {"data": {"schema_types": ["Organization"]}},
            {"data": {"schema_types": ["Organization", "Product"]}},
            changes,
        )
        rules = [c["rule"] for c in changes]
        self.assertIn("schema_type_removed", rules)


class TestSEOStructuralChanges(unittest.TestCase):

    def test_h1_removed(self):
        changes = []
        _check_structural_changes(
            {"data": {"h1_count": 0}},
            {"data": {"h1_count": 1}},
            changes,
        )
        self.assertEqual(changes[0]["severity"], "critical")

    def test_image_alt_decline(self):
        changes = []
        _check_structural_changes(
            {"data": {"image_alt_coverage": 30}},
            {"data": {"image_alt_coverage": 90}},
            changes,
        )
        rules = [c["rule"] for c in changes]
        self.assertIn("image_alt_declined", rules)


class TestDriftScore(unittest.TestCase):

    def test_critical_penalized(self):
        changes = [{"severity": "critical"}]
        self.assertEqual(calculate_drift_score(changes), -3)

    def test_warning_penalized(self):
        changes = [{"severity": "warning"}]
        self.assertEqual(calculate_drift_score(changes), -1)

    def test_improvement_rewarded(self):
        changes = [{"severity": "info", "direction": "improved"}]
        self.assertEqual(calculate_drift_score(changes), 2)

    def test_mixed_changes(self):
        changes = [
            {"severity": "critical"},
            {"severity": "info", "direction": "improved"},
        ]
        self.assertEqual(calculate_drift_score(changes), -1)


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


class TestCompareSnapshots(unittest.TestCase):

    def test_full_comparison(self):
        current = {
            "score": 40,
            "data": {
                "title": "New",
                "has_schema": False,
                "dimensions": {"meta_quality": 30},
                "h1_count": 0,
            },
        }
        baseline = {
            "score": 70,
            "data": {
                "title": "Old",
                "has_schema": True,
                "dimensions": {"meta_quality": 80},
                "h1_count": 1,
            },
        }
        changes = compare_snapshots(current, baseline)
        self.assertGreater(len(changes), 3)
        rules = [c["rule"] for c in changes]
        self.assertIn("score_change", rules)
        self.assertIn("schema_removed", rules)
        self.assertIn("title_changed", rules)


# === Unified Three-O Drift Tests ===

class TestComputeVelocity(unittest.TestCase):

    def test_declining_velocity(self):
        history = [
            {"score": 50, "data_json": "{}"},
            {"score": 55, "data_json": "{}"},
            {"score": 60, "data_json": "{}"},
            {"score": 70, "data_json": "{}"},
        ]
        vel = compute_velocity(history)
        self.assertLess(vel["velocity"], 0)
        self.assertEqual(vel["direction"], "declining")

    def test_improving_velocity(self):
        history = [
            {"score": 80, "data_json": "{}"},
            {"score": 70, "data_json": "{}"},
            {"score": 60, "data_json": "{}"},
        ]
        vel = compute_velocity(history)
        self.assertGreater(vel["velocity"], 0)
        self.assertEqual(vel["direction"], "improving")

    def test_stable_velocity(self):
        history = [
            {"score": 60, "data_json": "{}"},
            {"score": 60, "data_json": "{}"},
            {"score": 60, "data_json": "{}"},
        ]
        vel = compute_velocity(history)
        self.assertEqual(vel["velocity"], 0.0)
        self.assertEqual(vel["direction"], "stable")

    def test_insufficient_data(self):
        vel = compute_velocity([{"score": 60, "data_json": "{}"}])
        self.assertEqual(vel["direction"], "insufficient_data")

    def test_empty_history(self):
        vel = compute_velocity([])
        self.assertEqual(vel["direction"], "insufficient_data")

    def test_data_points_count(self):
        history = [{"score": s, "data_json": "{}"} for s in [80, 70, 60, 50]]
        vel = compute_velocity(history)
        self.assertEqual(vel["data_points"], 4)


class TestComputeTrend(unittest.TestCase):

    def test_consistent_up(self):
        history = [{"score": s} for s in [90, 80, 70, 60, 50]]
        trend = compute_trend(history)
        self.assertEqual(trend["trend"], "consistent_up")
        self.assertEqual(trend["total_change"], 40)

    def test_consistent_down(self):
        history = [{"score": s} for s in [30, 40, 50, 60, 70]]
        trend = compute_trend(history)
        self.assertEqual(trend["trend"], "consistent_down")
        self.assertEqual(trend["total_change"], -40)

    def test_flat(self):
        history = [{"score": 60}, {"score": 60}, {"score": 60}]
        trend = compute_trend(history)
        self.assertIn(trend["trend"], ["flat", "stable"])

    def test_no_data(self):
        trend = compute_trend([])
        self.assertEqual(trend["trend"], "no_data")

    def test_score_range(self):
        history = [{"score": s} for s in [80, 40, 60]]
        trend = compute_trend(history)
        self.assertEqual(trend["score_range"], [40, 80])

    def test_two_points_up(self):
        history = [{"score": 70}, {"score": 50}]
        trend = compute_trend(history)
        self.assertEqual(trend["trend"], "up")


class TestBuildTimeSeries(unittest.TestCase):

    def test_series_order(self):
        history = [
            {"timestamp": "2026-05-03", "score": 70, "data_json": '{"dimensions": {"meta": 60}}'},
            {"timestamp": "2026-05-01", "score": 60, "data_json": '{"dimensions": {"meta": 50}}'},
        ]
        series = build_time_series(history)
        self.assertEqual(series[0]["timestamp"], "2026-05-01")
        self.assertEqual(series[1]["timestamp"], "2026-05-03")

    def test_dimensions_included(self):
        history = [{"timestamp": "2026-05-01", "score": 60, "data_json": '{"dimensions": {"meta": 50}}'}]
        series = build_time_series(history)
        self.assertEqual(series[0]["dimensions"]["meta"], 50)

    def test_empty_data_json(self):
        history = [{"timestamp": "2026-05-01", "score": 60, "data_json": None}]
        series = build_time_series(history)
        self.assertEqual(series[0]["dimensions"], {})


class TestCrossPillarCorrelation(unittest.TestCase):

    def test_multi_pillar_decline(self):
        trends = {
            "seo": {"trend": "down", "latest": 40},
            "geo": {"trend": "consistent_down", "latest": 35},
            "aao": {"trend": "flat", "latest": 60},
        }
        alerts = detect_cross_pillar_correlation(trends)
        types = [a["type"] for a in alerts]
        self.assertIn("multi_pillar_decline", types)

    def test_seo_only_decline(self):
        trends = {
            "seo": {"trend": "down", "latest": 40},
            "geo": {"trend": "flat", "latest": 65},
            "aao": {"trend": "up", "latest": 70},
        }
        alerts = detect_cross_pillar_correlation(trends)
        types = [a["type"] for a in alerts]
        self.assertIn("seo_only_decline", types)

    def test_geo_only_decline(self):
        trends = {
            "seo": {"trend": "flat", "latest": 70},
            "geo": {"trend": "consistent_down", "latest": 30},
            "aao": {"trend": "flat", "latest": 60},
        }
        alerts = detect_cross_pillar_correlation(trends)
        types = [a["type"] for a in alerts]
        self.assertIn("geo_only_decline", types)

    def test_pillar_divergence(self):
        trends = {
            "seo": {"trend": "up", "latest": 90},
            "geo": {"trend": "down", "latest": 30},
            "aao": {"trend": "flat", "latest": 60},
        }
        alerts = detect_cross_pillar_correlation(trends)
        types = [a["type"] for a in alerts]
        self.assertIn("pillar_divergence", types)

    def test_all_stable_no_alerts(self):
        trends = {
            "seo": {"trend": "flat", "latest": 60},
            "geo": {"trend": "flat", "latest": 58},
            "aao": {"trend": "flat", "latest": 62},
        }
        alerts = detect_cross_pillar_correlation(trends)
        self.assertEqual(len(alerts), 0)


class TestVelocityAlerts(unittest.TestCase):

    def test_critical_velocity(self):
        velocities = {
            "seo": {"velocity": -5.0, "direction": "declining"},
        }
        alerts = generate_velocity_alerts(velocities)
        self.assertEqual(alerts[0]["severity"], "critical")

    def test_warning_velocity(self):
        velocities = {
            "geo": {"velocity": -1.5, "direction": "declining"},
        }
        alerts = generate_velocity_alerts(velocities)
        self.assertEqual(alerts[0]["severity"], "warning")

    def test_positive_velocity(self):
        velocities = {
            "aao": {"velocity": 4.0, "direction": "improving"},
        }
        alerts = generate_velocity_alerts(velocities)
        self.assertEqual(alerts[0]["severity"], "info")

    def test_stable_no_alert(self):
        velocities = {
            "seo": {"velocity": 0.5, "direction": "stable"},
        }
        alerts = generate_velocity_alerts(velocities)
        self.assertEqual(len(alerts), 0)


if __name__ == "__main__":
    unittest.main()

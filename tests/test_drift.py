"""Tests for drift detection: SEO dimension drift and unified Three-O drift."""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from seo_drift import (
    compare_snapshots, calculate_drift_score, classify_trend,
    _check_score_change, _check_dimension_changes, _check_meta_changes,
    _check_schema_changes, _check_structural_changes,
)
from geo_drift import (
    compare_geo_snapshots, calculate_geo_drift_score,
)
from three_o_drift import (
    compute_velocity, compute_trend, build_time_series,
    detect_cross_pillar_correlation, generate_velocity_alerts,
    format_drift_report,
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


# === GEO Drift Tests ===

class TestGEOScoreChange(unittest.TestCase):

    def test_significant_decline(self):
        current = {"score": 40, "data": {}}
        baseline = {"score": 60, "data": {}}
        changes = compare_geo_snapshots(current, baseline)
        score_changes = [c for c in changes if c["rule"] == "geo_score_change"]
        self.assertEqual(len(score_changes), 1)
        self.assertEqual(score_changes[0]["direction"], "declined")
        self.assertEqual(score_changes[0]["delta"], -20)

    def test_significant_improvement(self):
        current = {"score": 80, "data": {}}
        baseline = {"score": 55, "data": {}}
        changes = compare_geo_snapshots(current, baseline)
        score_changes = [c for c in changes if c["rule"] == "geo_score_change"]
        self.assertEqual(score_changes[0]["direction"], "improved")

    def test_critical_threshold(self):
        current = {"score": 30, "data": {}}
        baseline = {"score": 60, "data": {}}
        changes = compare_geo_snapshots(current, baseline)
        score_changes = [c for c in changes if c["rule"] == "geo_score_change"]
        self.assertEqual(score_changes[0]["severity"], "critical")

    def test_warning_threshold(self):
        current = {"score": 50, "data": {}}
        baseline = {"score": 60, "data": {}}
        changes = compare_geo_snapshots(current, baseline)
        score_changes = [c for c in changes if c["rule"] == "geo_score_change"]
        self.assertEqual(score_changes[0]["severity"], "warning")

    def test_info_threshold(self):
        current = {"score": 55, "data": {}}
        baseline = {"score": 60, "data": {}}
        changes = compare_geo_snapshots(current, baseline)
        score_changes = [c for c in changes if c["rule"] == "geo_score_change"]
        self.assertEqual(score_changes[0]["severity"], "info")

    def test_small_change_ignored(self):
        current = {"score": 59, "data": {}}
        baseline = {"score": 60, "data": {}}
        changes = compare_geo_snapshots(current, baseline)
        score_changes = [c for c in changes if c["rule"] == "geo_score_change"]
        self.assertEqual(len(score_changes), 0)

    def test_missing_scores(self):
        changes = compare_geo_snapshots({"data": {}}, {"data": {}})
        score_changes = [c for c in changes if c["rule"] == "geo_score_change"]
        self.assertEqual(len(score_changes), 0)


class TestGEODimensionChanges(unittest.TestCase):

    def test_dimension_decline(self):
        current = {"score": 50, "data": {"mf": 30}}
        baseline = {"score": 50, "data": {"mf": 60}}
        changes = compare_geo_snapshots(current, baseline)
        dim_changes = [c for c in changes if c["rule"] == "mf_change"]
        self.assertEqual(len(dim_changes), 1)
        self.assertEqual(dim_changes[0]["direction"], "declined")

    def test_dimension_improvement(self):
        current = {"score": 50, "data": {"cq": 80}}
        baseline = {"score": 50, "data": {"cq": 40}}
        changes = compare_geo_snapshots(current, baseline)
        dim_changes = [c for c in changes if c["rule"] == "cq_change"]
        self.assertEqual(dim_changes[0]["direction"], "improved")

    def test_small_dimension_change_ignored(self):
        current = {"score": 50, "data": {"vr": 62}}
        baseline = {"score": 50, "data": {"vr": 60}}
        changes = compare_geo_snapshots(current, baseline)
        dim_changes = [c for c in changes if c["rule"] == "vr_change"]
        self.assertEqual(len(dim_changes), 0)

    def test_warning_severity_large_change(self):
        current = {"score": 50, "data": {"ep": 30}}
        baseline = {"score": 50, "data": {"ep": 70}}
        changes = compare_geo_snapshots(current, baseline)
        dim_changes = [c for c in changes if c["rule"] == "ep_change"]
        self.assertEqual(dim_changes[0]["severity"], "warning")

    def test_multiple_dimensions(self):
        current = {"score": 50, "data": {"mf": 20, "cq": 25, "ta": 30}}
        baseline = {"score": 50, "data": {"mf": 70, "cq": 80, "ta": 85}}
        changes = compare_geo_snapshots(current, baseline)
        dim_rules = [c["rule"] for c in changes if "_change" in c["rule"] and c["rule"] != "geo_score_change"]
        self.assertEqual(len(dim_rules), 3)

    def test_missing_dimension_in_current(self):
        current = {"score": 50, "data": {}}
        baseline = {"score": 50, "data": {"mf": 70}}
        changes = compare_geo_snapshots(current, baseline)
        dim_changes = [c for c in changes if c["rule"] == "mf_change"]
        self.assertEqual(len(dim_changes), 0)


class TestGEOPlatformChanges(unittest.TestCase):

    def test_platform_lost(self):
        current = {"score": 50, "data": {"platform_mentions": {"chatgpt": 0}}}
        baseline = {"score": 50, "data": {"platform_mentions": {"chatgpt": 30}}}
        changes = compare_geo_snapshots(current, baseline)
        platform_changes = [c for c in changes if c["rule"] == "platform_lost"]
        self.assertEqual(len(platform_changes), 1)
        self.assertEqual(platform_changes[0]["severity"], "critical")

    def test_platform_gained(self):
        current = {"score": 50, "data": {"platform_mentions": {"perplexity": 25}}}
        baseline = {"score": 50, "data": {"platform_mentions": {"perplexity": 0}}}
        changes = compare_geo_snapshots(current, baseline)
        platform_changes = [c for c in changes if c["rule"] == "platform_gained"]
        self.assertEqual(len(platform_changes), 1)
        self.assertEqual(platform_changes[0]["direction"], "improved")

    def test_platform_disappeared(self):
        current = {"score": 50, "data": {"platform_mentions": {}}}
        baseline = {"score": 50, "data": {"platform_mentions": {"gemini": 15}}}
        changes = compare_geo_snapshots(current, baseline)
        platform_changes = [c for c in changes if c["rule"] == "platform_lost"]
        self.assertEqual(len(platform_changes), 1)

    def test_new_platform_appeared(self):
        current = {"score": 50, "data": {"platform_mentions": {"claude": 10}}}
        baseline = {"score": 50, "data": {"platform_mentions": {}}}
        changes = compare_geo_snapshots(current, baseline)
        platform_changes = [c for c in changes if c["rule"] == "platform_gained"]
        self.assertEqual(len(platform_changes), 1)

    def test_stable_platforms_no_change(self):
        current = {"score": 50, "data": {"platform_mentions": {"chatgpt": 30}}}
        baseline = {"score": 50, "data": {"platform_mentions": {"chatgpt": 35}}}
        changes = compare_geo_snapshots(current, baseline)
        platform_changes = [c for c in changes if c["rule"] in ("platform_lost", "platform_gained")]
        self.assertEqual(len(platform_changes), 0)


class TestGEOEntityChanges(unittest.TestCase):

    def test_entity_delinked(self):
        current = {"score": 50, "data": {"entity_linked": False}}
        baseline = {"score": 50, "data": {"entity_linked": True}}
        changes = compare_geo_snapshots(current, baseline)
        entity_changes = [c for c in changes if c["rule"] == "entity_delinked"]
        self.assertEqual(len(entity_changes), 1)
        self.assertEqual(entity_changes[0]["severity"], "critical")

    def test_entity_still_linked(self):
        current = {"score": 50, "data": {"entity_linked": True}}
        baseline = {"score": 50, "data": {"entity_linked": True}}
        changes = compare_geo_snapshots(current, baseline)
        entity_changes = [c for c in changes if c["rule"] == "entity_delinked"]
        self.assertEqual(len(entity_changes), 0)

    def test_no_entity_data(self):
        current = {"score": 50, "data": {}}
        baseline = {"score": 50, "data": {}}
        changes = compare_geo_snapshots(current, baseline)
        entity_changes = [c for c in changes if c["rule"] == "entity_delinked"]
        self.assertEqual(len(entity_changes), 0)


class TestGEODriftScore(unittest.TestCase):

    def test_critical_penalized(self):
        changes = [{"severity": "critical"}]
        self.assertEqual(calculate_geo_drift_score(changes), -4)

    def test_warning_penalized(self):
        changes = [{"severity": "warning"}]
        self.assertEqual(calculate_geo_drift_score(changes), -2)

    def test_improvement_rewarded(self):
        changes = [{"severity": "info", "direction": "improved"}]
        self.assertEqual(calculate_geo_drift_score(changes), 2)

    def test_mixed_changes(self):
        changes = [
            {"severity": "critical"},
            {"severity": "warning"},
            {"severity": "info", "direction": "improved"},
        ]
        self.assertEqual(calculate_geo_drift_score(changes), -4)

    def test_empty_changes(self):
        self.assertEqual(calculate_geo_drift_score([]), 0)


class TestCompareGeoSnapshotsFull(unittest.TestCase):

    def test_full_decline_scenario(self):
        current = {
            "score": 30,
            "data": {
                "mf": 20, "cq": 25,
                "platform_mentions": {"chatgpt": 0},
                "entity_linked": False,
            },
        }
        baseline = {
            "score": 70,
            "data": {
                "mf": 70, "cq": 80,
                "platform_mentions": {"chatgpt": 40},
                "entity_linked": True,
            },
        }
        changes = compare_geo_snapshots(current, baseline)
        rules = [c["rule"] for c in changes]
        self.assertIn("geo_score_change", rules)
        self.assertIn("platform_lost", rules)
        self.assertIn("entity_delinked", rules)
        self.assertGreater(len(changes), 4)

    def test_full_improvement_scenario(self):
        current = {
            "score": 80,
            "data": {
                "mf": 75, "cq": 80,
                "platform_mentions": {"chatgpt": 30, "perplexity": 20},
                "entity_linked": True,
            },
        }
        baseline = {
            "score": 40,
            "data": {
                "mf": 30, "cq": 35,
                "platform_mentions": {"chatgpt": 30},
                "entity_linked": True,
            },
        }
        changes = compare_geo_snapshots(current, baseline)
        improved = [c for c in changes if c.get("direction") == "improved"]
        self.assertGreater(len(improved), 0)

    def test_empty_data(self):
        changes = compare_geo_snapshots({"data": {}}, {"data": {}})
        self.assertEqual(len(changes), 0)


# === Format Drift Report Tests ===

class TestFormatDriftReport(unittest.TestCase):

    def test_basic_report(self):
        result = {
            "success": True,
            "brand": "TestBrand",
            "overall_status": "stable",
            "velocities": {
                "seo": {"velocity": 0.5, "direction": "stable"},
                "geo": {"velocity": -0.3, "direction": "stable"},
                "aao": {"velocity": 1.2, "direction": "improving"},
            },
            "trends": {
                "seo": {"trend": "flat", "latest": 65, "total_change": 0},
                "geo": {"trend": "flat", "latest": 55, "total_change": -2},
                "aao": {"trend": "up", "latest": 70, "total_change": 5},
            },
            "alerts": [],
            "history_depth": {"seo": 5, "geo": 5, "aao": 3},
        }
        report = format_drift_report(result)
        self.assertIn("TestBrand", report)
        self.assertIn("STABLE", report)
        self.assertIn("SEO", report)
        self.assertIn("GEO", report)
        self.assertIn("AAO", report)

    def test_report_with_alerts(self):
        result = {
            "success": True,
            "brand": "AlertBrand",
            "overall_status": "critical",
            "velocities": {
                "seo": {"velocity": -5.0, "direction": "declining"},
                "geo": {"velocity": -4.0, "direction": "declining"},
                "aao": {"velocity": 0.0, "direction": "stable"},
            },
            "trends": {
                "seo": {"trend": "consistent_down", "latest": 30, "total_change": -20},
                "geo": {"trend": "down", "latest": 35, "total_change": -15},
                "aao": {"trend": "flat", "latest": 50, "total_change": 0},
            },
            "alerts": [
                {"severity": "critical", "message": "복수 pillar 동시 하락"},
                {"severity": "warning", "message": "SEO 속도 하락"},
            ],
            "history_depth": {"seo": 8, "geo": 6, "aao": 4},
        }
        report = format_drift_report(result)
        self.assertIn("CRITICAL", report)
        self.assertIn("Alerts (2)", report)
        self.assertIn("복수 pillar", report)

    def test_error_report(self):
        result = {"success": False, "error": "DB not found"}
        report = format_drift_report(result)
        self.assertIn("Error", report)
        self.assertIn("DB not found", report)

    def test_history_depth_displayed(self):
        result = {
            "success": True,
            "brand": "X",
            "overall_status": "stable",
            "velocities": {p: {"velocity": 0, "direction": "stable"} for p in ["seo", "geo", "aao"]},
            "trends": {p: {"trend": "flat", "latest": 50, "total_change": 0} for p in ["seo", "geo", "aao"]},
            "alerts": [],
            "history_depth": {"seo": 10, "geo": 7, "aao": 3},
        }
        report = format_drift_report(result)
        self.assertIn("SEO=10", report)
        self.assertIn("GEO=7", report)
        self.assertIn("AAO=3", report)


# === Velocity Edge Cases ===

class TestVelocityEdgeCases(unittest.TestCase):

    def test_two_point_history(self):
        history = [{"score": 70, "data_json": "{}"}, {"score": 60, "data_json": "{}"}]
        vel = compute_velocity(history)
        self.assertGreater(vel["velocity"], 0)
        self.assertEqual(vel["data_points"], 2)
        self.assertEqual(vel["acceleration"], 0.0)

    def test_null_scores_filtered(self):
        history = [
            {"score": 70, "data_json": "{}"},
            {"score": None, "data_json": "{}"},
            {"score": 60, "data_json": "{}"},
        ]
        vel = compute_velocity(history)
        self.assertEqual(vel["data_points"], 2)

    def test_all_null_scores(self):
        history = [{"score": None, "data_json": "{}"}, {"score": None, "data_json": "{}"}]
        vel = compute_velocity(history)
        self.assertEqual(vel["direction"], "insufficient_data")


class TestTrendEdgeCases(unittest.TestCase):

    def test_volatile_trend(self):
        history = [{"score": s} for s in [65, 50, 70, 45, 60]]
        trend = compute_trend(history)
        self.assertIn(trend["trend"], ["volatile", "up", "down", "flat"])

    def test_all_same_scores(self):
        history = [{"score": 50} for _ in range(5)]
        trend = compute_trend(history)
        self.assertEqual(trend["trend"], "flat")
        self.assertEqual(trend["total_change"], 0)

    def test_single_point(self):
        history = [{"score": 60}]
        trend = compute_trend(history)
        self.assertEqual(trend["total_change"], 0)

    def test_two_points_down(self):
        history = [{"score": 40}, {"score": 70}]
        trend = compute_trend(history)
        self.assertEqual(trend["trend"], "down")


# === Cross-Pillar Edge Cases ===

class TestCrossPillarEdgeCases(unittest.TestCase):

    def test_aao_only_decline(self):
        trends = {
            "seo": {"trend": "flat", "latest": 70},
            "geo": {"trend": "up", "latest": 65},
            "aao": {"trend": "down", "latest": 40},
        }
        alerts = detect_cross_pillar_correlation(trends)
        types = [a["type"] for a in alerts]
        self.assertIn("aao_only_decline", types)

    def test_all_improving(self):
        trends = {
            "seo": {"trend": "consistent_up", "latest": 80},
            "geo": {"trend": "up", "latest": 75},
            "aao": {"trend": "up", "latest": 70},
        }
        alerts = detect_cross_pillar_correlation(trends)
        decline_alerts = [a for a in alerts if "decline" in a["type"]]
        self.assertEqual(len(decline_alerts), 0)

    def test_no_divergence_close_scores(self):
        trends = {
            "seo": {"trend": "flat", "latest": 60},
            "geo": {"trend": "flat", "latest": 62},
            "aao": {"trend": "flat", "latest": 58},
        }
        alerts = detect_cross_pillar_correlation(trends)
        div_alerts = [a for a in alerts if a["type"] == "pillar_divergence"]
        self.assertEqual(len(div_alerts), 0)

    def test_missing_latest_scores(self):
        trends = {
            "seo": {"trend": "flat"},
            "geo": {"trend": "flat"},
            "aao": {"trend": "flat"},
        }
        alerts = detect_cross_pillar_correlation(trends)
        div_alerts = [a for a in alerts if a["type"] == "pillar_divergence"]
        self.assertEqual(len(div_alerts), 0)

    def test_three_pillar_decline(self):
        trends = {
            "seo": {"trend": "down", "latest": 30},
            "geo": {"trend": "consistent_down", "latest": 25},
            "aao": {"trend": "down", "latest": 20},
        }
        alerts = detect_cross_pillar_correlation(trends)
        types = [a["type"] for a in alerts]
        self.assertIn("multi_pillar_decline", types)


if __name__ == "__main__":
    unittest.main()

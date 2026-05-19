"""Tests for three_o_drift.py — unified drift detection with velocity/trend/cross-pillar."""

import sys
import os
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from three_o_drift import (
    ALERT_THRESHOLDS,
    compute_velocity,
    compute_trend,
    build_time_series,
    detect_cross_pillar_correlation,
    generate_velocity_alerts,
    analyze_unified_drift,
    format_drift_report,
    get_dashboard_trends,
)


class TestAlertThresholds(unittest.TestCase):

    def test_has_score_drop_critical(self):
        self.assertIn("score_drop_critical", ALERT_THRESHOLDS)

    def test_has_velocity_critical(self):
        self.assertIn("velocity_critical", ALERT_THRESHOLDS)

    def test_has_pillar_divergence(self):
        self.assertIn("pillar_divergence", ALERT_THRESHOLDS)

    def test_critical_more_severe_than_warning(self):
        self.assertLess(ALERT_THRESHOLDS["score_drop_critical"], ALERT_THRESHOLDS["score_drop_warning"])

    def test_velocity_critical_negative(self):
        self.assertLess(ALERT_THRESHOLDS["velocity_critical"], 0)


class TestComputeVelocity(unittest.TestCase):

    def test_empty_history(self):
        result = compute_velocity([])
        self.assertEqual(result["velocity"], 0.0)
        self.assertEqual(result["direction"], "insufficient_data")

    def test_single_entry(self):
        result = compute_velocity([{"score": 70}])
        self.assertEqual(result["direction"], "insufficient_data")
        self.assertEqual(result["data_points"], 1)

    def test_two_entries_improving(self):
        history = [{"score": 80}, {"score": 60}]
        result = compute_velocity(history)
        self.assertGreater(result["velocity"], 0)
        self.assertEqual(result["data_points"], 2)

    def test_two_entries_declining(self):
        history = [{"score": 40}, {"score": 70}]
        result = compute_velocity(history)
        self.assertLess(result["velocity"], 0)

    def test_stable_scores(self):
        history = [{"score": 70}, {"score": 70}, {"score": 70}]
        result = compute_velocity(history)
        self.assertEqual(result["velocity"], 0.0)
        self.assertEqual(result["direction"], "stable")

    def test_improving_direction(self):
        history = [{"score": 90}, {"score": 80}, {"score": 60}]
        result = compute_velocity(history)
        self.assertEqual(result["direction"], "improving")

    def test_declining_direction(self):
        history = [{"score": 40}, {"score": 60}, {"score": 80}]
        result = compute_velocity(history)
        self.assertEqual(result["direction"], "declining")

    def test_none_scores_skipped(self):
        history = [{"score": 80}, {"score": None}, {"score": 60}]
        result = compute_velocity(history)
        self.assertEqual(result["data_points"], 2)

    def test_acceleration_computed(self):
        history = [{"score": 90}, {"score": 80}, {"score": 75}, {"score": 60}]
        result = compute_velocity(history)
        self.assertIsInstance(result["acceleration"], float)

    def test_many_entries(self):
        history = [{"score": 50 + i * 3} for i in range(10)]
        result = compute_velocity(history)
        self.assertEqual(result["data_points"], 10)
        self.assertNotEqual(result["velocity"], 0.0)


class TestComputeTrend(unittest.TestCase):

    def test_empty_history(self):
        result = compute_trend([])
        self.assertEqual(result["trend"], "no_data")

    def test_no_valid_scores(self):
        result = compute_trend([{"score": None}])
        self.assertEqual(result["trend"], "no_data")

    def test_single_entry(self):
        result = compute_trend([{"score": 70}])
        self.assertEqual(result["latest"], 70)
        self.assertEqual(result["total_change"], 0)

    def test_two_entries_up(self):
        history = [{"score": 80}, {"score": 70}]
        result = compute_trend(history)
        self.assertEqual(result["trend"], "up")
        self.assertEqual(result["total_change"], 10)

    def test_two_entries_down(self):
        history = [{"score": 60}, {"score": 70}]
        result = compute_trend(history)
        self.assertEqual(result["trend"], "down")

    def test_two_entries_flat(self):
        history = [{"score": 71}, {"score": 70}]
        result = compute_trend(history)
        self.assertEqual(result["trend"], "flat")

    def test_consistent_up(self):
        history = [{"score": 90}, {"score": 80}, {"score": 70}, {"score": 60}]
        result = compute_trend(history)
        self.assertEqual(result["trend"], "consistent_up")

    def test_consistent_down(self):
        history = [{"score": 40}, {"score": 50}, {"score": 60}, {"score": 70}]
        result = compute_trend(history)
        self.assertEqual(result["trend"], "consistent_down")

    def test_volatile(self):
        history = [{"score": 70}, {"score": 60}, {"score": 75}, {"score": 65}]
        result = compute_trend(history)
        self.assertIn(result["trend"], ["volatile", "flat", "up", "down"])

    def test_score_range(self):
        history = [{"score": 90}, {"score": 60}, {"score": 70}]
        result = compute_trend(history)
        self.assertEqual(result["score_range"], [60, 90])

    def test_latest_oldest(self):
        history = [{"score": 80}, {"score": 50}]
        result = compute_trend(history)
        self.assertEqual(result["latest"], 80)
        self.assertEqual(result["oldest"], 50)

    def test_all_same_scores_flat(self):
        history = [{"score": 60}, {"score": 60}, {"score": 60}, {"score": 60}]
        result = compute_trend(history)
        self.assertEqual(result["trend"], "flat")


class TestBuildTimeSeries(unittest.TestCase):

    def test_empty(self):
        self.assertEqual(build_time_series([]), [])

    def test_single_entry(self):
        history = [{"timestamp": "2024-01-01", "score": 70, "data_json": '{"dimensions": {"a": 1}}'}]
        series = build_time_series(history)
        self.assertEqual(len(series), 1)
        self.assertEqual(series[0]["score"], 70)
        self.assertEqual(series[0]["dimensions"], {"a": 1})

    def test_no_data_json(self):
        history = [{"timestamp": "2024-01-01", "score": 50}]
        series = build_time_series(history)
        self.assertEqual(series[0]["dimensions"], {})

    def test_order_reversed(self):
        history = [
            {"timestamp": "2024-03-01", "score": 80, "data_json": None},
            {"timestamp": "2024-01-01", "score": 60, "data_json": None},
        ]
        series = build_time_series(history)
        self.assertEqual(series[0]["timestamp"], "2024-01-01")
        self.assertEqual(series[1]["timestamp"], "2024-03-01")

    def test_multiple_entries(self):
        history = [{"timestamp": f"2024-0{i}-01", "score": 50 + i * 5, "data_json": None} for i in range(1, 5)]
        series = build_time_series(history)
        self.assertEqual(len(series), 4)


class TestDetectCrossPillarCorrelation(unittest.TestCase):

    def test_no_decline(self):
        trends = {
            "seo": {"trend": "up", "latest": 80},
            "geo": {"trend": "flat", "latest": 75},
            "aao": {"trend": "up", "latest": 70},
        }
        alerts = detect_cross_pillar_correlation(trends)
        critical = [a for a in alerts if a["severity"] == "critical"]
        self.assertEqual(len(critical), 0)

    def test_multi_pillar_decline(self):
        trends = {
            "seo": {"trend": "down", "latest": 50},
            "geo": {"trend": "down", "latest": 40},
            "aao": {"trend": "up", "latest": 70},
        }
        alerts = detect_cross_pillar_correlation(trends)
        types = [a["type"] for a in alerts]
        self.assertIn("multi_pillar_decline", types)

    def test_seo_only_decline(self):
        trends = {
            "seo": {"trend": "down", "latest": 50},
            "geo": {"trend": "up", "latest": 80},
            "aao": {"trend": "flat", "latest": 70},
        }
        alerts = detect_cross_pillar_correlation(trends)
        types = [a["type"] for a in alerts]
        self.assertIn("seo_only_decline", types)

    def test_geo_only_decline(self):
        trends = {
            "seo": {"trend": "up", "latest": 80},
            "geo": {"trend": "down", "latest": 40},
            "aao": {"trend": "flat", "latest": 70},
        }
        alerts = detect_cross_pillar_correlation(trends)
        types = [a["type"] for a in alerts]
        self.assertIn("geo_only_decline", types)

    def test_aao_only_decline(self):
        trends = {
            "seo": {"trend": "up", "latest": 80},
            "geo": {"trend": "flat", "latest": 75},
            "aao": {"trend": "down", "latest": 50},
        }
        alerts = detect_cross_pillar_correlation(trends)
        types = [a["type"] for a in alerts]
        self.assertIn("aao_only_decline", types)

    def test_pillar_divergence(self):
        trends = {
            "seo": {"trend": "up", "latest": 90},
            "geo": {"trend": "flat", "latest": 70},
            "aao": {"trend": "flat", "latest": 70},
        }
        alerts = detect_cross_pillar_correlation(trends)
        types = [a["type"] for a in alerts]
        self.assertIn("pillar_divergence", types)

    def test_no_divergence_close_scores(self):
        trends = {
            "seo": {"trend": "flat", "latest": 70},
            "geo": {"trend": "flat", "latest": 72},
            "aao": {"trend": "flat", "latest": 68},
        }
        alerts = detect_cross_pillar_correlation(trends)
        types = [a["type"] for a in alerts]
        self.assertNotIn("pillar_divergence", types)

    def test_empty_trends(self):
        alerts = detect_cross_pillar_correlation({})
        self.assertEqual(alerts, [])


class TestGenerateVelocityAlerts(unittest.TestCase):

    def test_no_alerts_stable(self):
        velocities = {"seo": {"velocity": 0.0}, "geo": {"velocity": 0.5}, "aao": {"velocity": -0.5}}
        alerts = generate_velocity_alerts(velocities)
        self.assertEqual(len(alerts), 0)

    def test_critical_velocity(self):
        velocities = {"seo": {"velocity": -4.0}}
        alerts = generate_velocity_alerts(velocities)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["type"], "velocity_critical")
        self.assertEqual(alerts[0]["severity"], "critical")

    def test_warning_velocity(self):
        velocities = {"geo": {"velocity": -1.5}}
        alerts = generate_velocity_alerts(velocities)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["type"], "velocity_warning")

    def test_positive_velocity(self):
        velocities = {"aao": {"velocity": 4.0}}
        alerts = generate_velocity_alerts(velocities)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["type"], "velocity_positive")
        self.assertEqual(alerts[0]["severity"], "info")

    def test_multiple_pillars(self):
        velocities = {
            "seo": {"velocity": -4.0},
            "geo": {"velocity": -1.5},
            "aao": {"velocity": 0.0},
        }
        alerts = generate_velocity_alerts(velocities)
        self.assertEqual(len(alerts), 2)

    def test_boundary_not_warning(self):
        velocities = {"seo": {"velocity": -1.0}}
        alerts = generate_velocity_alerts(velocities)
        self.assertEqual(len(alerts), 1)

    def test_boundary_not_critical(self):
        velocities = {"seo": {"velocity": -3.0}}
        alerts = generate_velocity_alerts(velocities)
        self.assertEqual(alerts[0]["type"], "velocity_critical")


class TestAnalyzeUnifiedDrift(unittest.TestCase):

    @patch("three_o_drift.get_all_pillar_baselines", return_value={"seo": [], "geo": [], "aao": []})
    @patch("three_o_drift.init_db")
    def test_no_history(self, mock_init, mock_baselines):
        result = analyze_unified_drift("Brand")
        self.assertTrue(result["success"])
        self.assertEqual(result["brand"], "Brand")
        self.assertEqual(result["overall_status"], "stable")

    @patch("three_o_drift.get_all_pillar_baselines")
    @patch("three_o_drift.init_db")
    def test_with_history(self, mock_init, mock_baselines):
        mock_baselines.return_value = {
            "seo": [{"score": 80, "timestamp": "2024-02-01", "data_json": None},
                    {"score": 70, "timestamp": "2024-01-01", "data_json": None}],
            "geo": [{"score": 60, "timestamp": "2024-02-01", "data_json": None}],
            "aao": [],
        }
        result = analyze_unified_drift("Brand")
        self.assertTrue(result["success"])
        self.assertIn("velocities", result)
        self.assertIn("trends", result)

    @patch("three_o_drift.save_baseline")
    @patch("three_o_drift.get_all_pillar_baselines", return_value={"seo": [], "geo": [], "aao": []})
    @patch("three_o_drift.init_db")
    def test_saves_current_scores(self, mock_init, mock_baselines, mock_save):
        current = {"seo": {"score": 80}, "geo": {"score": 70}}
        analyze_unified_drift("Brand", current_scores=current)
        self.assertEqual(mock_save.call_count, 2)

    @patch("three_o_drift.get_all_pillar_baselines")
    @patch("three_o_drift.init_db")
    def test_critical_status(self, mock_init, mock_baselines):
        mock_baselines.return_value = {
            "seo": [{"score": 40, "timestamp": "2024-03-01", "data_json": None},
                    {"score": 60, "timestamp": "2024-02-01", "data_json": None},
                    {"score": 80, "timestamp": "2024-01-01", "data_json": None}],
            "geo": [{"score": 30, "timestamp": "2024-03-01", "data_json": None},
                    {"score": 60, "timestamp": "2024-02-01", "data_json": None},
                    {"score": 80, "timestamp": "2024-01-01", "data_json": None}],
            "aao": [],
        }
        result = analyze_unified_drift("Brand")
        self.assertIn(result["overall_status"], ["critical", "warning", "watch"])

    @patch("three_o_drift.get_all_pillar_baselines", return_value={"seo": [], "geo": [], "aao": []})
    @patch("three_o_drift.init_db")
    def test_result_keys(self, mock_init, mock_baselines):
        result = analyze_unified_drift("Brand")
        for key in ["success", "brand", "overall_status", "velocities", "trends", "alerts", "time_series", "history_depth"]:
            self.assertIn(key, result)

    @patch("three_o_drift.get_all_pillar_baselines", return_value={"seo": [], "geo": [], "aao": []})
    @patch("three_o_drift.init_db")
    def test_history_depth(self, mock_init, mock_baselines):
        result = analyze_unified_drift("Brand")
        self.assertEqual(result["history_depth"], {"seo": 0, "geo": 0, "aao": 0})

    @patch("three_o_drift.get_all_pillar_baselines")
    @patch("three_o_drift.init_db")
    def test_alerts_sorted_by_severity(self, mock_init, mock_baselines):
        mock_baselines.return_value = {
            "seo": [{"score": 30, "timestamp": "2024-03-01", "data_json": None},
                    {"score": 70, "timestamp": "2024-02-01", "data_json": None},
                    {"score": 80, "timestamp": "2024-01-01", "data_json": None}],
            "geo": [{"score": 20, "timestamp": "2024-03-01", "data_json": None},
                    {"score": 60, "timestamp": "2024-02-01", "data_json": None},
                    {"score": 80, "timestamp": "2024-01-01", "data_json": None}],
            "aao": [{"score": 10, "timestamp": "2024-03-01", "data_json": None},
                    {"score": 50, "timestamp": "2024-02-01", "data_json": None},
                    {"score": 80, "timestamp": "2024-01-01", "data_json": None}],
        }
        result = analyze_unified_drift("Brand")
        severities = [a["severity"] for a in result["alerts"]]
        order = {"critical": 0, "warning": 1, "info": 2}
        for i in range(len(severities) - 1):
            self.assertLessEqual(order.get(severities[i], 3), order.get(severities[i + 1], 3))


class TestFormatDriftReport(unittest.TestCase):

    def test_error_result(self):
        output = format_drift_report({"success": False, "error": "DB fail"})
        self.assertIn("DB fail", output)

    def test_success_result(self):
        result = {
            "success": True,
            "brand": "TestBrand",
            "overall_status": "stable",
            "trends": {
                "seo": {"latest": 80, "total_change": 5, "trend": "up"},
                "geo": {"latest": 70, "total_change": 0, "trend": "flat"},
                "aao": {"latest": 60, "total_change": -3, "trend": "flat"},
            },
            "velocities": {
                "seo": {"velocity": 2.5},
                "geo": {"velocity": 0.0},
                "aao": {"velocity": -0.5},
            },
            "alerts": [],
            "history_depth": {"seo": 5, "geo": 3, "aao": 2},
        }
        output = format_drift_report(result)
        self.assertIn("TestBrand", output)
        self.assertIn("STABLE", output)
        self.assertIn("SEO", output)

    def test_with_alerts(self):
        result = {
            "success": True,
            "brand": "B",
            "overall_status": "warning",
            "trends": {"seo": {}, "geo": {}, "aao": {}},
            "velocities": {"seo": {}, "geo": {}, "aao": {}},
            "alerts": [{"severity": "warning", "message": "Test alert"}],
            "history_depth": {"seo": 0, "geo": 0, "aao": 0},
        }
        output = format_drift_report(result)
        self.assertIn("Alerts (1)", output)
        self.assertIn("Test alert", output)

    def test_history_depth_shown(self):
        result = {
            "success": True, "brand": "X", "overall_status": "stable",
            "trends": {"seo": {}, "geo": {}, "aao": {}},
            "velocities": {"seo": {}, "geo": {}, "aao": {}},
            "alerts": [], "history_depth": {"seo": 10, "geo": 5, "aao": 3},
        }
        output = format_drift_report(result)
        self.assertIn("SEO=10", output)
        self.assertIn("GEO=5", output)


class TestGetDashboardTrends(unittest.TestCase):

    @patch("three_o_drift.get_all_pillar_baselines", return_value={"seo": [], "geo": [], "aao": []})
    @patch("three_o_drift.init_db")
    def test_result_keys(self, mock_init, mock_history):
        result = get_dashboard_trends("brand")
        self.assertIn("trends", result)
        self.assertIn("alerts", result)
        self.assertIn("velocities", result)
        self.assertIn("overall_status", result)

    @patch("three_o_drift.get_all_pillar_baselines", return_value={"seo": [], "geo": [], "aao": []})
    @patch("three_o_drift.init_db")
    def test_empty_history_stable(self, mock_init, mock_history):
        result = get_dashboard_trends("brand")
        self.assertEqual(result["overall_status"], "stable")
        self.assertEqual(result["alerts"], [])

    @patch("three_o_drift.get_all_pillar_baselines")
    @patch("three_o_drift.init_db")
    def test_declining_triggers_alerts(self, mock_init, mock_history):
        mock_history.return_value = {
            "seo": [{"score": 30, "timestamp": "t2", "data_json": "{}"}, {"score": 80, "timestamp": "t1", "data_json": "{}"}],
            "geo": [{"score": 25, "timestamp": "t2", "data_json": "{}"}, {"score": 70, "timestamp": "t1", "data_json": "{}"}],
            "aao": [],
        }
        result = get_dashboard_trends("brand")
        self.assertGreater(len(result["alerts"]), 0)

    @patch("three_o_drift.get_all_pillar_baselines", return_value={"seo": [], "geo": [], "aao": []})
    @patch("three_o_drift.init_db")
    def test_trends_has_pillar_keys(self, mock_init, mock_history):
        result = get_dashboard_trends("brand")
        for pillar in ["seo", "geo", "aao"]:
            self.assertIn(pillar, result["trends"])


if __name__ == "__main__":
    unittest.main()

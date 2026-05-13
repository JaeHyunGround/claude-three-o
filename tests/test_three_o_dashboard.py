"""Tests for three_o_dashboard.py — dashboard data export."""

import sys
import os
import json
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from three_o_dashboard import (
    get_brand_dashboard, export_dashboard, DASHBOARD_METRICS,
)


class TestDashboardMetrics(unittest.TestCase):

    def test_has_overview(self):
        self.assertIn("overview", DASHBOARD_METRICS)

    def test_has_seo(self):
        self.assertIn("seo", DASHBOARD_METRICS)

    def test_has_geo(self):
        self.assertIn("geo", DASHBOARD_METRICS)

    def test_has_aao(self):
        self.assertIn("aao", DASHBOARD_METRICS)

    def test_overview_has_three_o_score(self):
        self.assertIn("three_o_score", DASHBOARD_METRICS["overview"])

    def test_all_metrics_are_lists(self):
        for key, metrics in DASHBOARD_METRICS.items():
            self.assertIsInstance(metrics, list, f"{key} metrics not a list")
            self.assertGreater(len(metrics), 0)


class TestGetBrandDashboard(unittest.TestCase):

    @patch("three_o_dashboard.get_latest_baseline")
    @patch("three_o_dashboard.init_db")
    def test_no_data(self, mock_init, mock_baseline):
        mock_baseline.return_value = None
        result = get_brand_dashboard("TestBrand")
        self.assertEqual(result["brand"], "TestBrand")
        self.assertIsNone(result["three_o_score"])
        self.assertEqual(result["data_completeness"], 0)

    @patch("three_o_dashboard.get_latest_baseline")
    @patch("three_o_dashboard.init_db")
    def test_full_data(self, mock_init, mock_baseline):
        def baseline_side(brand, pillar):
            return {
                "score": {"seo": 70, "geo": 60, "aao": 50}[pillar],
                "timestamp": "2024-01-01T00:00:00",
                "data_json": json.dumps({"detail": pillar}),
            }
        mock_baseline.side_effect = baseline_side
        result = get_brand_dashboard("Brand")
        self.assertIsNotNone(result["three_o_score"])
        expected = round(70 * 0.35 + 60 * 0.35 + 50 * 0.30, 1)
        self.assertEqual(result["three_o_score"], expected)
        self.assertEqual(result["data_completeness"], 100)

    @patch("three_o_dashboard.get_latest_baseline")
    @patch("three_o_dashboard.init_db")
    def test_partial_data(self, mock_init, mock_baseline):
        def baseline_side(brand, pillar):
            if pillar == "seo":
                return {"score": 80, "timestamp": "2024-01-01", "data_json": "{}"}
            return None
        mock_baseline.side_effect = baseline_side
        result = get_brand_dashboard("Brand")
        self.assertIsNone(result["three_o_score"])
        self.assertEqual(result["data_completeness"], 33)

    @patch("three_o_dashboard.get_latest_baseline")
    @patch("three_o_dashboard.init_db")
    def test_pillars_structure(self, mock_init, mock_baseline):
        mock_baseline.return_value = None
        result = get_brand_dashboard("Brand")
        for pillar in ["seo", "geo", "aao"]:
            self.assertIn(pillar, result["pillars"])
            self.assertIn("score", result["pillars"][pillar])
            self.assertIn("last_updated", result["pillars"][pillar])
            self.assertIn("data", result["pillars"][pillar])

    @patch("three_o_dashboard.get_latest_baseline")
    @patch("three_o_dashboard.init_db")
    def test_generated_at_present(self, mock_init, mock_baseline):
        mock_baseline.return_value = None
        result = get_brand_dashboard("Brand")
        self.assertIn("generated_at", result)

    @patch("three_o_dashboard.get_latest_baseline")
    @patch("three_o_dashboard.init_db")
    def test_data_json_parsed(self, mock_init, mock_baseline):
        mock_baseline.return_value = {
            "score": 70, "timestamp": "2024-01-01",
            "data_json": json.dumps({"key": "value"}),
        }
        result = get_brand_dashboard("Brand")
        self.assertEqual(result["pillars"]["seo"]["data"], {"key": "value"})

    @patch("three_o_dashboard.get_latest_baseline")
    @patch("three_o_dashboard.init_db")
    def test_null_data_json(self, mock_init, mock_baseline):
        mock_baseline.return_value = {
            "score": 50, "timestamp": "2024-01-01", "data_json": None,
        }
        result = get_brand_dashboard("Brand")
        self.assertEqual(result["pillars"]["seo"]["data"], {})


class TestExportDashboard(unittest.TestCase):

    @patch("three_o_dashboard.get_trend_data", return_value=[])
    @patch("three_o_dashboard.get_latest_baseline", return_value=None)
    @patch("three_o_dashboard.init_db")
    def test_json_format(self, mock_init, mock_baseline, mock_trend):
        result = export_dashboard("Brand", "json")
        self.assertTrue(result["success"])
        self.assertIn("dashboard", result)
        self.assertNotIn("csv_export", result["dashboard"])

    @patch("three_o_dashboard.get_trend_data", return_value=[])
    @patch("three_o_dashboard.get_latest_baseline")
    @patch("three_o_dashboard.init_db")
    def test_csv_format(self, mock_init, mock_baseline, mock_trend):
        def baseline_side(brand, pillar):
            return {"score": 70, "timestamp": "2024-01-01", "data_json": "{}"}
        mock_baseline.side_effect = baseline_side
        result = export_dashboard("Brand", "csv")
        csv = result["dashboard"]["csv_export"]
        self.assertIn("pillar,score,last_updated", csv)
        self.assertIn("seo,70,", csv)

    @patch("three_o_dashboard.get_trend_data")
    @patch("three_o_dashboard.get_latest_baseline", return_value=None)
    @patch("three_o_dashboard.init_db")
    def test_trends_included(self, mock_init, mock_baseline, mock_trend):
        mock_trend.return_value = [{"score": 50, "date": "2024-01-01"}]
        result = export_dashboard("Brand")
        self.assertIn("trends", result["dashboard"])

    @patch("three_o_dashboard.get_trend_data", return_value=[])
    @patch("three_o_dashboard.get_latest_baseline", return_value=None)
    @patch("three_o_dashboard.init_db")
    def test_csv_empty_scores(self, mock_init, mock_baseline, mock_trend):
        result = export_dashboard("Brand", "csv")
        csv = result["dashboard"]["csv_export"]
        self.assertIn("seo,,", csv)

    @patch("three_o_dashboard.get_trend_data", return_value=[])
    @patch("three_o_dashboard.get_latest_baseline", return_value=None)
    @patch("three_o_dashboard.init_db")
    def test_success_flag(self, mock_init, mock_baseline, mock_trend):
        result = export_dashboard("Brand")
        self.assertTrue(result["success"])


if __name__ == "__main__":
    unittest.main()

"""Tests for three_o_report.py — unified report generation."""

import sys
import os
import json
import tempfile
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from three_o_report import (
    REPORT_SECTIONS,
    generate_executive_summary,
    _generate_insights,
    generate_pillar_section,
    generate_action_plan,
    generate_report,
    save_report,
)


class TestReportSections(unittest.TestCase):

    def test_full_has_all_sections(self):
        self.assertIn("executive_summary", REPORT_SECTIONS["full"])
        self.assertIn("seo", REPORT_SECTIONS["full"])
        self.assertIn("geo", REPORT_SECTIONS["full"])
        self.assertIn("aao", REPORT_SECTIONS["full"])
        self.assertIn("recommendations", REPORT_SECTIONS["full"])

    def test_seo_only_sections(self):
        self.assertIn("seo", REPORT_SECTIONS["seo"])
        self.assertNotIn("geo", REPORT_SECTIONS["seo"])

    def test_geo_only_sections(self):
        self.assertIn("geo", REPORT_SECTIONS["geo"])
        self.assertNotIn("seo", REPORT_SECTIONS["geo"])

    def test_aao_only_sections(self):
        self.assertIn("aao", REPORT_SECTIONS["aao"])
        self.assertNotIn("seo", REPORT_SECTIONS["aao"])

    def test_all_types_have_executive_summary(self):
        for rtype in REPORT_SECTIONS:
            self.assertIn("executive_summary", REPORT_SECTIONS[rtype])


class TestGenerateInsights(unittest.TestCase):

    def test_empty_data(self):
        insights = _generate_insights({})
        self.assertIsInstance(insights, list)

    def test_imbalanced_profile(self):
        data = {"seo": {"score": 90}, "geo": {"score": 60}, "aao": {"score": 50}}
        insights = _generate_insights(data)
        text = " ".join(insights)
        self.assertIn("Imbalanced", text)

    def test_balanced_profile(self):
        data = {"seo": {"score": 70}, "geo": {"score": 65}, "aao": {"score": 68}}
        insights = _generate_insights(data)
        text = " ".join(insights)
        self.assertIn("Well-balanced", text)

    def test_industry_detected(self):
        data = {"aao": {"industry_detected": "restaurant", "score": 50}, "seo": {"score": 50}, "geo": {"score": 50}}
        insights = _generate_insights(data)
        text = " ".join(insights)
        self.assertIn("Restaurant", text)

    def test_general_industry_no_insight(self):
        data = {"aao": {"industry_detected": "general"}}
        insights = _generate_insights(data)
        text = " ".join(insights)
        self.assertNotIn("Industry detected", text)

    def test_platform_gap(self):
        data = {"geo": {"best_platform": "chatgpt", "worst_platform": "gemini"}, "seo": {"score": 0}, "aao": {"score": 0}}
        insights = _generate_insights(data)
        text = " ".join(insights)
        self.assertIn("Platform gap", text)

    def test_synergy_bonuses(self):
        data = {
            "aao": {"correlation": {"applied": [{"value": 5, "reason": "bonus"}]}},
            "seo": {"score": 0}, "geo": {"score": 0},
        }
        insights = _generate_insights(data)
        text = " ".join(insights)
        self.assertIn("synergy bonus", text)

    def test_signal_conflicts(self):
        data = {
            "aao": {"correlation": {"applied": [{"value": -3, "reason": "conflict"}]}},
            "seo": {"score": 0}, "geo": {"score": 0},
        }
        insights = _generate_insights(data)
        text = " ".join(insights)
        self.assertIn("signal conflict", text)


class TestGenerateExecutiveSummary(unittest.TestCase):

    @patch("three_o_report.generate_recommendations", return_value={"quick_wins": []})
    def test_contains_brand(self, mock_rec):
        data = {"brand": "MyBrand", "three_o_score": {"score": 75, "grade": "B"}}
        output = generate_executive_summary(data)
        self.assertIn("MyBrand", output)

    @patch("three_o_report.generate_recommendations", return_value={"quick_wins": []})
    def test_contains_score(self, mock_rec):
        data = {"brand": "X", "three_o_score": {"score": 85, "grade": "A", "pillars": {}}}
        output = generate_executive_summary(data)
        self.assertIn("85", output)

    @patch("three_o_report.generate_recommendations", return_value={"quick_wins": []})
    def test_pillar_table(self, mock_rec):
        data = {
            "brand": "X",
            "three_o_score": {
                "score": 70, "grade": "B",
                "pillars": {"seo": {"score": 80, "weight": 0.35}},
            },
        }
        output = generate_executive_summary(data)
        self.assertIn("SEO", output)
        self.assertIn("80", output)

    @patch("three_o_report.generate_recommendations", return_value={
        "quick_wins": [{"title": "Fix meta", "effort_estimate": "low", "impact_estimate": "high"}]
    })
    def test_quick_wins(self, mock_rec):
        data = {"brand": "X", "three_o_score": {"score": 50, "grade": "C"}}
        output = generate_executive_summary(data)
        self.assertIn("Fix meta", output)

    @patch("three_o_report.generate_recommendations", return_value={"quick_wins": []})
    def test_top_issues(self, mock_rec):
        data = {
            "brand": "X", "three_o_score": {"score": 50, "grade": "C"},
            "top_issues": [{"severity": "critical", "message": "Broken indexing"}],
        }
        output = generate_executive_summary(data)
        self.assertIn("Broken indexing", output)


class TestGeneratePillarSection(unittest.TestCase):

    def test_no_data(self):
        output = generate_pillar_section("seo", {})
        self.assertIn("No data available", output)

    def test_score_displayed(self):
        data = {"seo": {"score": 85}}
        output = generate_pillar_section("seo", data)
        self.assertIn("85", output)

    def test_dimensions_table(self):
        data = {"seo": {"score": 70, "dimensions": {"technical": 80, "content": 60}}}
        output = generate_pillar_section("seo", data)
        self.assertIn("Technical", output)
        self.assertIn("Content", output)

    def test_geo_platform_breakdown(self):
        data = {"geo": {"score": 65, "platform_breakdown": {"chatgpt": {"geo_score": 70, "grade": "B"}}}}
        output = generate_pillar_section("geo", data)
        self.assertIn("Chatgpt", output)
        self.assertIn("70", output)

    def test_geo_citability(self):
        data = {"geo": {"score": 60, "platform_citability": {"perplexity": 80}}}
        output = generate_pillar_section("geo", data)
        self.assertIn("Perplexity", output)

    def test_aao_industry(self):
        data = {"aao": {"score": 55, "industry_detected": "restaurant", "weights_applied": {"selectability": 0.4}}}
        output = generate_pillar_section("aao", data)
        self.assertIn("Restaurant", output)

    def test_aao_correlation(self):
        data = {"aao": {"score": 60, "correlation": {"applied": [{"value": 5, "reason": "Synergy"}]}}}
        output = generate_pillar_section("aao", data)
        self.assertIn("Synergy", output)

    def test_issues_listed(self):
        data = {"seo": {"score": 50, "issues": [{"severity": "high", "message": "Missing schema"}]}}
        output = generate_pillar_section("seo", data)
        self.assertIn("Missing schema", output)

    def test_issues_max_10(self):
        issues = [{"severity": "low", "message": f"Issue {i}"} for i in range(15)]
        data = {"seo": {"score": 30, "issues": issues}}
        output = generate_pillar_section("seo", data)
        self.assertIn("Issue 9", output)
        self.assertNotIn("Issue 10", output)


class TestGenerateActionPlan(unittest.TestCase):

    def test_empty_data(self):
        output = generate_action_plan({})
        self.assertIn("Action Plan", output)

    def test_issues_sorted_by_severity(self):
        data = {
            "seo": {"issues": [{"severity": "low", "message": "Low issue"}]},
            "geo": {"issues": [{"severity": "critical", "message": "Critical issue"}]},
        }
        output = generate_action_plan(data)
        crit_pos = output.find("Critical issue")
        low_pos = output.find("Low issue")
        self.assertLess(crit_pos, low_pos)

    def test_priority_labels(self):
        data = {
            "seo": {"issues": [
                {"severity": "critical", "message": "C1"},
                {"severity": "high", "message": "H1"},
                {"severity": "medium", "message": "M1"},
            ]},
        }
        output = generate_action_plan(data)
        self.assertIn("P0", output)
        self.assertIn("P1", output)
        self.assertIn("P2", output)

    def test_max_15_issues(self):
        issues = [{"severity": "low", "message": f"Issue {i}"} for i in range(20)]
        data = {"seo": {"issues": issues}}
        output = generate_action_plan(data)
        self.assertIn("Issue 14", output)
        self.assertNotIn("Issue 15", output)

    def test_all_pillars_combined(self):
        data = {
            "seo": {"issues": [{"severity": "high", "message": "SEO issue"}]},
            "geo": {"issues": [{"severity": "high", "message": "GEO issue"}]},
            "aao": {"issues": [{"severity": "high", "message": "AAO issue"}]},
        }
        output = generate_action_plan(data)
        self.assertIn("SEO issue", output)
        self.assertIn("GEO issue", output)
        self.assertIn("AAO issue", output)


class TestGenerateReport(unittest.TestCase):

    def test_json_format(self):
        data = {"brand": "X", "three_o_score": {"score": 50, "grade": "C", "pillars": {}}}
        result = generate_report(data, "full", "json")
        self.assertTrue(result["success"])
        self.assertEqual(result["format"], "json")
        self.assertIn("data", result)

    @patch("three_o_report.generate_recommendations", return_value={"quick_wins": [], "recommendations": []})
    @patch("three_o_report.format_recommendations_md", return_value="## Recommendations\n")
    def test_md_format_full(self, mock_fmt, mock_rec):
        data = {"brand": "X", "three_o_score": {"score": 50, "grade": "C", "pillars": {}}}
        result = generate_report(data, "full", "md")
        self.assertTrue(result["success"])
        self.assertEqual(result["format"], "md")
        self.assertIn("content", result)
        self.assertIn("sections", result)

    @patch("three_o_report.generate_recommendations", return_value={"quick_wins": []})
    def test_seo_only(self, mock_rec):
        data = {"brand": "X", "three_o_score": {"score": 50, "grade": "C", "pillars": {}}, "seo": {"score": 60}}
        result = generate_report(data, "seo", "md")
        self.assertIn("seo", result["sections"])
        self.assertNotIn("geo", result["sections"])

    def test_unknown_type_defaults_full(self):
        data = {"brand": "X", "three_o_score": {"score": 50, "grade": "C", "pillars": {}}}
        result = generate_report(data, "unknown", "json")
        self.assertEqual(result["report_type"], "unknown")

    @patch("three_o_report.generate_recommendations", return_value={"quick_wins": [], "recommendations": []})
    @patch("three_o_report.format_recommendations_md", return_value="")
    def test_report_footer(self, mock_fmt, mock_rec):
        data = {"brand": "X", "three_o_score": {"score": 50, "grade": "C", "pillars": {}}}
        result = generate_report(data, "full", "md")
        self.assertIn("Three-O v1.0.0", result["content"])


class TestSaveReport(unittest.TestCase):

    def test_save_md(self):
        report = {"content": "# Test Report\nHello"}
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("three_o_report.os.getcwd", return_value=tmpdir):
                filepath = save_report(report, "brand", "full", "md")
                self.assertTrue(filepath.endswith(".md"))
                self.assertTrue(os.path.exists(filepath))
                with open(filepath, "r") as f:
                    self.assertIn("Test Report", f.read())

    def test_save_json(self):
        report = {"data": {"brand": "X", "score": 70}}
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("three_o_report.os.getcwd", return_value=tmpdir):
                filepath = save_report(report, "brand", "full", "json")
                self.assertTrue(filepath.endswith(".json"))
                self.assertTrue(os.path.exists(filepath))

    def test_creates_reports_dir(self):
        report = {"content": "test"}
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("three_o_report.os.getcwd", return_value=tmpdir):
                save_report(report, "b", "full", "md")
                self.assertTrue(os.path.isdir(os.path.join(tmpdir, "reports")))

    def test_filename_format(self):
        report = {"content": "test"}
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("three_o_report.os.getcwd", return_value=tmpdir):
                filepath = save_report(report, "mybrand", "seo", "md")
                basename = os.path.basename(filepath)
                self.assertIn("mybrand", basename)
                self.assertIn("seo", basename)


if __name__ == "__main__":
    unittest.main()

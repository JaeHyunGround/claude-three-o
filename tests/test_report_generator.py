"""Tests for report_generator.py — report generation (MD/JSON)."""

import sys
import os
import json
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from report_generator import (
    generate_markdown_report,
    generate_json_report,
    save_report,
    get_reports_dir,
)


class TestGenerateMarkdownReport(unittest.TestCase):

    def _data(self, **overrides):
        base = {
            "brand": "TestBrand",
            "three_o_score": 75,
            "grade": "B+",
            "pillars": {"seo": 80, "geo": 70, "aao": 60},
            "weights_applied": {"seo": 0.35, "geo": 0.35, "aao": 0.30},
            "findings": [],
            "actions": [],
        }
        base.update(overrides)
        return base

    def test_contains_brand(self):
        md = generate_markdown_report(self._data())
        self.assertIn("TestBrand", md)

    def test_contains_score(self):
        md = generate_markdown_report(self._data())
        self.assertIn("75/100", md)

    def test_contains_grade(self):
        md = generate_markdown_report(self._data())
        self.assertIn("B+", md)

    def test_pillar_table(self):
        md = generate_markdown_report(self._data())
        self.assertIn("SEO", md)
        self.assertIn("GEO", md)
        self.assertIn("AAO", md)

    def test_findings_listed(self):
        data = self._data(findings=[
            {"severity": "critical", "description": "Broken indexing"},
            {"severity": "low", "description": "Minor issue"},
        ])
        md = generate_markdown_report(data)
        self.assertIn("Broken indexing", md)
        self.assertIn("CRITICAL", md)

    def test_findings_max_10(self):
        findings = [{"severity": "low", "description": f"F{i}"} for i in range(15)]
        md = generate_markdown_report(self._data(findings=findings))
        self.assertIn("F9", md)
        self.assertNotIn("F10", md)

    def test_actions_listed(self):
        data = self._data(actions=[
            {"description": "Add schema", "impact": "High"},
        ])
        md = generate_markdown_report(data)
        self.assertIn("Add schema", md)
        self.assertIn("High", md)

    def test_footer(self):
        md = generate_markdown_report(self._data())
        from config import VERSION
        self.assertIn(f"Three-O Platform v{VERSION}", md)

    def test_empty_data(self):
        md = generate_markdown_report({})
        self.assertIn("Unknown", md)
        self.assertIn("0/100", md)

    def test_weights_formatted(self):
        md = generate_markdown_report(self._data())
        self.assertIn("35.0%", md)


class TestGenerateJsonReport(unittest.TestCase):

    def test_valid_json(self):
        data = {"three_o_score": 80, "grade": "A", "pillars": {}, "findings": []}
        output = generate_json_report(data)
        parsed = json.loads(output)
        self.assertIn("meta", parsed)
        self.assertIn("scores", parsed)

    def test_meta_fields(self):
        output = generate_json_report({})
        parsed = json.loads(output)
        from config import VERSION
        self.assertEqual(parsed["meta"]["version"], VERSION)
        self.assertEqual(parsed["meta"]["platform"], "Three-O")
        self.assertIn("generated_at", parsed["meta"])

    def test_scores_included(self):
        data = {"three_o_score": 65, "grade": "B"}
        parsed = json.loads(generate_json_report(data))
        self.assertEqual(parsed["scores"]["three_o_score"], 65)
        self.assertEqual(parsed["scores"]["grade"], "B")

    def test_findings_passed_through(self):
        data = {"findings": [{"severity": "high", "description": "Test"}]}
        parsed = json.loads(generate_json_report(data))
        self.assertEqual(len(parsed["findings"]), 1)

    def test_industry_included(self):
        data = {"industry": "restaurant"}
        parsed = json.loads(generate_json_report(data))
        self.assertEqual(parsed["industry"], "restaurant")


class TestSaveReport(unittest.TestCase):

    def test_save_md(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("report_generator.get_reports_dir", return_value=__import__("pathlib").Path(tmpdir)):
                path = save_report("# Report", "brand", "full", "md")
                self.assertTrue(path.exists())
                self.assertEqual(path.read_text(), "# Report")

    def test_save_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("report_generator.get_reports_dir", return_value=__import__("pathlib").Path(tmpdir)):
                path = save_report('{"a":1}', "brand", "seo", "json")
                self.assertTrue(path.exists())
                self.assertTrue(str(path).endswith(".json"))

    def test_filename_contains_brand(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("report_generator.get_reports_dir", return_value=__import__("pathlib").Path(tmpdir)):
                path = save_report("test", "mybrand", "full", "md")
                self.assertIn("mybrand", path.name)

    def test_filename_contains_type(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("report_generator.get_reports_dir", return_value=__import__("pathlib").Path(tmpdir)):
                path = save_report("test", "b", "geo", "md")
                self.assertIn("geo", path.name)


class TestGetReportsDir(unittest.TestCase):

    def test_returns_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("report_generator.Path.cwd", return_value=__import__("pathlib").Path(tmpdir)):
                reports = get_reports_dir()
                self.assertTrue(reports.exists())
                self.assertTrue(reports.is_dir())


if __name__ == "__main__":
    unittest.main()

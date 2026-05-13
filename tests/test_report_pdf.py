"""Tests for report_pdf.py — developer and business audience modes."""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from report_pdf import (
    ThreeOPDF,
    generate_pdf_report,
    _score_to_grade,
    _translate_issue,
    _dim_label,
    DIMENSION_LABELS_BIZ,
    PILLAR_LABELS_BIZ,
    PILLAR_DESCRIPTIONS_BIZ,
    SEVERITY_LABELS_BIZ,
    ISSUE_IMPACT_MAP,
)


SAMPLE_AUDIT_DATA = {
    "brand": "TestBrand",
    "three_o_score": {
        "score": 62.5,
        "grade": "B",
        "pillars": {
            "seo": {"score": 71.0},
            "geo": {"score": 55.0},
            "aao": {"score": 58.0},
        },
    },
    "top_issues": [
        {"severity": "critical", "message": "Missing meta description"},
        {"severity": "high", "message": "No structured data found"},
        {"severity": "medium", "message": "Images missing alt text"},
    ],
    "seo": {
        "score": 71.0,
        "dimensions": {
            "meta_quality": 80,
            "security": 60,
            "mobile": 90,
            "performance": 55,
        },
        "issues": [
            {"severity": "high", "message": "Missing meta description"},
            {"severity": "medium", "message": "Title length too short"},
            {"severity": "low", "message": "Missing Open Graph tags"},
        ],
    },
    "geo": {
        "score": 55.0,
        "dimensions": {
            "polarity_strength": 65,
            "consistency": 70,
            "coverage": 40,
            "platform_alignment": 50,
            "signal_diversity": 30,
        },
        "platform_breakdown": {
            "chatgpt": {"geo_score": 60},
            "perplexity": {"geo_score": 50},
            "gemini": {"geo_score": 55},
        },
        "issues": [
            {"severity": "medium", "message": "Low AI mention frequency"},
            {"severity": "low", "message": "Missing citation patterns"},
        ],
    },
    "aao": {
        "score": 58.0,
        "industry_detected": "agency",
        "dimensions": {
            "structured_data": {"score": 30},
            "reviews_ratings": {"score": 20},
            "info_completeness": {"score": 75},
            "trust_signals": {"score": 60},
            "freshness": {"score": 50},
            "api_booking": {"score": 40},
        },
        "issues": [
            {"severity": "critical", "message": "No schema markup found"},
            {"severity": "high", "message": "No reviews or ratings detected"},
            {"severity": "medium", "message": "Missing booking functionality"},
        ],
    },
}


class TestScoreToGrade(unittest.TestCase):

    def test_a_plus(self):
        grade, text = _score_to_grade(95)
        self.assertEqual(grade, "A+")
        self.assertEqual(text, "매우 우수")

    def test_a(self):
        grade, _ = _score_to_grade(85)
        self.assertEqual(grade, "A")

    def test_b_plus(self):
        grade, _ = _score_to_grade(75)
        self.assertEqual(grade, "B+")

    def test_b(self):
        grade, _ = _score_to_grade(65)
        self.assertEqual(grade, "B")

    def test_c(self):
        grade, text = _score_to_grade(55)
        self.assertEqual(grade, "C")
        self.assertEqual(text, "개선 필요")

    def test_d(self):
        grade, _ = _score_to_grade(45)
        self.assertEqual(grade, "D")

    def test_f(self):
        grade, text = _score_to_grade(30)
        self.assertEqual(grade, "F")
        self.assertEqual(text, "심각한 개선 필요")

    def test_boundary_90(self):
        grade, _ = _score_to_grade(90)
        self.assertEqual(grade, "A+")

    def test_boundary_0(self):
        grade, _ = _score_to_grade(0)
        self.assertEqual(grade, "F")


class TestTranslateIssue(unittest.TestCase):

    def test_meta_description(self):
        result = _translate_issue("Missing meta description")
        self.assertIn("검색 결과", result)

    def test_schema(self):
        result = _translate_issue("No schema markup found")
        self.assertIn("AI", result)

    def test_viewport(self):
        result = _translate_issue("Missing viewport meta tag")
        self.assertIn("모바일", result)

    def test_ssl(self):
        result = _translate_issue("SSL certificate missing")
        self.assertIn("보안", result)

    def test_alt_text(self):
        result = _translate_issue("Images missing alt text")
        self.assertIn("이미지", result)

    def test_unknown_passes_through(self):
        msg = "Some completely unknown technical issue XYZ123"
        result = _translate_issue(msg)
        self.assertEqual(result, msg)

    def test_case_insensitive(self):
        result = _translate_issue("MISSING META DESCRIPTION tag")
        self.assertIn("검색 결과", result)

    def test_open_graph(self):
        result = _translate_issue("Missing Open Graph tags")
        self.assertIn("SNS", result)

    def test_review(self):
        result = _translate_issue("No reviews found")
        self.assertIn("리뷰", result)

    def test_booking(self):
        result = _translate_issue("Missing booking functionality")
        self.assertIn("예약", result)


class TestDimLabel(unittest.TestCase):

    def test_known_dimension(self):
        self.assertEqual(_dim_label("polarity_strength"), "브랜드 인식 강도")

    def test_meta_quality(self):
        self.assertEqual(_dim_label("meta_quality"), "검색결과 노출 품질")

    def test_unknown_dimension(self):
        result = _dim_label("some_unknown_dim")
        self.assertEqual(result, "Some Unknown Dim")

    def test_all_labels_are_strings(self):
        for k, v in DIMENSION_LABELS_BIZ.items():
            self.assertIsInstance(v, str, f"{k} label should be string")
            self.assertGreater(len(v), 0, f"{k} label should not be empty")


class TestBusinessLabels(unittest.TestCase):

    def test_all_pillars_have_labels(self):
        for p in ["seo", "geo", "aao"]:
            self.assertIn(p, PILLAR_LABELS_BIZ)
            self.assertIn(p, PILLAR_DESCRIPTIONS_BIZ)

    def test_all_severities_have_labels(self):
        for s in ["critical", "high", "medium", "warning", "low"]:
            self.assertIn(s, SEVERITY_LABELS_BIZ)

    def test_pillar_descriptions_nonempty(self):
        for p, desc in PILLAR_DESCRIPTIONS_BIZ.items():
            self.assertGreater(len(desc), 20, f"{p} description too short")

    def test_issue_map_nonempty(self):
        self.assertGreater(len(ISSUE_IMPACT_MAP), 10)
        for pattern, translation in ISSUE_IMPACT_MAP.items():
            self.assertGreater(len(translation), 5)


class TestGeneratePDFDeveloper(unittest.TestCase):

    def test_developer_report_creates_file(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = f.name
        try:
            result = generate_pdf_report(SAMPLE_AUDIT_DATA, path, audience="developer")
            self.assertEqual(result, path)
            self.assertTrue(os.path.exists(path))
            self.assertGreater(os.path.getsize(path), 1000)
        finally:
            os.unlink(path)

    def test_developer_default_audience(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = f.name
        try:
            result = generate_pdf_report(SAMPLE_AUDIT_DATA, path)
            self.assertTrue(os.path.exists(path))
        finally:
            os.unlink(path)

    def test_developer_filename_suffix(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data = {**SAMPLE_AUDIT_DATA, "brand": "DevTest"}
            result = generate_pdf_report(data, os.path.join(tmpdir, "test-dev.pdf"), "developer")
            self.assertIn("test-dev", result)


class TestGeneratePDFBusiness(unittest.TestCase):

    def test_business_report_creates_file(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = f.name
        try:
            result = generate_pdf_report(SAMPLE_AUDIT_DATA, path, audience="business")
            self.assertEqual(result, path)
            self.assertTrue(os.path.exists(path))
            self.assertGreater(os.path.getsize(path), 1000)
        finally:
            os.unlink(path)

    def test_business_larger_than_empty(self):
        minimal = {"brand": "X", "three_o_score": {"score": 0, "grade": "F", "pillars": {}}}
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = f.name
        try:
            generate_pdf_report(minimal, path, "business")
            self.assertGreater(os.path.getsize(path), 500)
        finally:
            os.unlink(path)

    def test_business_with_all_pillars(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = f.name
        try:
            generate_pdf_report(SAMPLE_AUDIT_DATA, path, "business")
            size = os.path.getsize(path)
            self.assertGreater(size, 3000)
        finally:
            os.unlink(path)

    def test_business_auto_filename_suffix(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                data = {**SAMPLE_AUDIT_DATA, "brand": "BizTest"}
                result = generate_pdf_report(data, audience="business")
                self.assertIn("business", result)
                self.assertTrue(os.path.exists(result))
            finally:
                os.chdir(original_cwd)


class TestGeneratePDFEdgeCases(unittest.TestCase):

    def test_empty_issues(self):
        data = {
            **SAMPLE_AUDIT_DATA,
            "top_issues": [],
            "seo": {"score": 80, "dimensions": {}, "issues": []},
            "geo": {"score": 70, "dimensions": {}, "issues": []},
            "aao": {"score": 60, "dimensions": {}, "issues": []},
        }
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = f.name
        try:
            generate_pdf_report(data, path, "business")
            self.assertTrue(os.path.exists(path))
        finally:
            os.unlink(path)

    def test_missing_pillar_data(self):
        data = {
            "brand": "Partial",
            "three_o_score": {"score": 40, "grade": "D", "pillars": {"seo": {"score": 40}}},
            "seo": {"score": 40, "dimensions": {"performance": 30}, "issues": []},
        }
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = f.name
        try:
            generate_pdf_report(data, path, "business")
            self.assertTrue(os.path.exists(path))
            generate_pdf_report(data, path, "developer")
            self.assertTrue(os.path.exists(path))
        finally:
            os.unlink(path)

    def test_numeric_dimension_values(self):
        data = {
            "brand": "NumDim",
            "three_o_score": {"score": 50, "grade": "C", "pillars": {}},
            "seo": {"score": 50, "dimensions": {"mobile": 80, "security": 60}, "issues": []},
        }
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = f.name
        try:
            generate_pdf_report(data, path, "business")
            self.assertTrue(os.path.exists(path))
        finally:
            os.unlink(path)

    def test_dict_dimension_values(self):
        data = {
            "brand": "DictDim",
            "three_o_score": {"score": 50, "grade": "C", "pillars": {}},
            "seo": {
                "score": 50,
                "dimensions": {"mobile": {"score": 80, "details": {}}},
                "issues": [],
            },
        }
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = f.name
        try:
            generate_pdf_report(data, path, "business")
            self.assertTrue(os.path.exists(path))
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()

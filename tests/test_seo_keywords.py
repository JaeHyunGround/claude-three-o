"""Tests for seo_keywords.py — keyword tracking (Google + Naver)."""

import sys
import os
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from seo_keywords import (
    check_keyword_in_content,
    generate_keyword_variants,
    analyze_keywords,
)


class TestCheckKeywordInContent(unittest.TestCase):

    def test_in_title(self):
        html = '<html><head><title>Best Coffee Shop</title></head><body></body></html>'
        result = check_keyword_in_content(html, "coffee")
        self.assertTrue(result["in_title"])

    def test_not_in_title(self):
        html = '<html><head><title>Home Page</title></head><body></body></html>'
        result = check_keyword_in_content(html, "coffee")
        self.assertFalse(result["in_title"])

    def test_in_h1(self):
        html = '<html><body><h1>Coffee Shop Guide</h1></body></html>'
        result = check_keyword_in_content(html, "coffee")
        self.assertTrue(result["in_h1"])

    def test_not_in_h1(self):
        html = '<html><body><h1>Welcome</h1></body></html>'
        result = check_keyword_in_content(html, "coffee")
        self.assertFalse(result["in_h1"])

    def test_occurrences_counted(self):
        html = '<html><body>coffee is great. I love coffee. Best coffee ever.</body></html>'
        result = check_keyword_in_content(html, "coffee")
        self.assertEqual(result["occurrences"], 3)

    def test_density_percent(self):
        html = '<html><body>coffee coffee coffee word word word word word word word</body></html>'
        result = check_keyword_in_content(html, "coffee")
        self.assertGreater(result["density_percent"], 0)

    def test_density_optimal(self):
        words = " ".join(["word"] * 90 + ["coffee"] * 10)
        html = f'<html><body>{words}</body></html>'
        result = check_keyword_in_content(html, "coffee")
        self.assertIn(result["density_status"], ["optimal", "high"])

    def test_density_low(self):
        words = " ".join(["word"] * 999 + ["coffee"])
        html = f'<html><body>{words}</body></html>'
        result = check_keyword_in_content(html, "coffee")
        self.assertEqual(result["density_status"], "low")

    def test_case_insensitive(self):
        html = '<html><head><title>COFFEE SHOP</title></head><body></body></html>'
        result = check_keyword_in_content(html, "coffee")
        self.assertTrue(result["in_title"])

    def test_keyword_field_preserved(self):
        result = check_keyword_in_content("<html></html>", "myKeyword")
        self.assertEqual(result["keyword"], "myKeyword")


class TestGenerateKeywordVariants(unittest.TestCase):

    def test_base_keyword_included(self):
        variants = generate_keyword_variants("카페")
        self.assertIn("카페", variants)

    def test_korean_suffixes_added(self):
        variants = generate_keyword_variants("카페")
        self.assertIn("카페 추천", variants)
        self.assertIn("카페 가격", variants)
        self.assertIn("카페 후기", variants)

    def test_variant_count(self):
        variants = generate_keyword_variants("test")
        self.assertEqual(len(variants), 7)

    def test_english_keyword(self):
        variants = generate_keyword_variants("coffee")
        self.assertIn("coffee", variants)
        self.assertIn("coffee 추천", variants)


class TestAnalyzeKeywords(unittest.TestCase):

    @patch("validate_url.validate_url", return_value={"valid": False, "error": "bad"})
    def test_invalid_url(self, mock_val):
        result = analyze_keywords("bad", ["kw"])
        self.assertFalse(result["success"])

    @patch("validate_url.validate_url", return_value={"valid": True})
    @patch("fetch_page.fetch_page", return_value={"success": False, "error": "timeout"})
    def test_fetch_failure(self, mock_fetch, mock_val):
        result = analyze_keywords("https://x.com", ["kw"])
        self.assertFalse(result["success"])

    @patch("validate_url.validate_url", return_value={"valid": True})
    @patch("fetch_page.fetch_page")
    def test_successful_analysis(self, mock_fetch, mock_val):
        html = '<html><head><title>Coffee Shop</title></head><body>Best coffee in town</body></html>'
        mock_fetch.return_value = {"success": True, "html": html}
        result = analyze_keywords("https://x.com", ["coffee"])
        self.assertTrue(result["success"])
        self.assertEqual(result["keywords_analyzed"], 1)
        self.assertGreater(result["keywords_optimized"], 0)

    @patch("validate_url.validate_url", return_value={"valid": True})
    @patch("fetch_page.fetch_page")
    def test_multiple_keywords(self, mock_fetch, mock_val):
        html = '<html><head><title>Coffee Tea</title></head><body></body></html>'
        mock_fetch.return_value = {"success": True, "html": html}
        result = analyze_keywords("https://x.com", ["coffee", "tea", "juice"])
        self.assertEqual(result["keywords_analyzed"], 3)
        self.assertEqual(len(result["results"]), 3)

    @patch("validate_url.validate_url", return_value={"valid": True})
    @patch("fetch_page.fetch_page")
    def test_score_computed(self, mock_fetch, mock_val):
        mock_fetch.return_value = {"success": True, "html": "<html><head><title>Test</title></head><body></body></html>"}
        result = analyze_keywords("https://x.com", ["test"])
        self.assertIn("score", result)
        self.assertGreaterEqual(result["score"], 0)
        self.assertLessEqual(result["score"], 100)

    @patch("validate_url.validate_url", return_value={"valid": True})
    @patch("fetch_page.fetch_page")
    def test_result_keys(self, mock_fetch, mock_val):
        mock_fetch.return_value = {"success": True, "html": "<html></html>"}
        result = analyze_keywords("https://x.com", ["kw"])
        for key in ["success", "url", "score", "keywords_analyzed", "keywords_optimized", "results"]:
            self.assertIn(key, result)


if __name__ == "__main__":
    unittest.main()

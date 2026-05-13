"""Tests for seo_competitor.py — SEO competitor gap analysis."""

import sys
import os
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from seo_competitor import extract_page_keywords, compare_sites


class TestExtractPageKeywords(unittest.TestCase):

    def test_from_title(self):
        html = '<html><head><title>Best Coffee Shop in Seoul</title></head></html>'
        kws = extract_page_keywords(html)
        self.assertIn("coffee", kws)
        self.assertIn("shop", kws)
        self.assertIn("seoul", kws)

    def test_from_meta_description(self):
        html = '<meta name="description" content="Premium organic coffee beans delivered fresh">'
        kws = extract_page_keywords(html)
        self.assertIn("premium", kws)
        self.assertIn("organic", kws)

    def test_from_meta_reversed_attrs(self):
        html = '<meta content="Korean restaurant reviews" name="description">'
        kws = extract_page_keywords(html)
        self.assertIn("korean", kws)
        self.assertIn("restaurant", kws)

    def test_from_headings(self):
        html = '<h1>Welcome to Our Store</h1><h2>About Quality Products</h2>'
        kws = extract_page_keywords(html)
        self.assertIn("welcome", kws)
        self.assertIn("quality", kws)

    def test_stop_words_removed(self):
        html = '<title>The Best of the World</title>'
        kws = extract_page_keywords(html)
        self.assertNotIn("the", kws)
        self.assertNotIn("of", kws)

    def test_short_words_removed(self):
        html = '<title>Go to it now</title>'
        kws = extract_page_keywords(html)
        self.assertNotIn("go", kws)
        self.assertNotIn("to", kws)

    def test_empty_html(self):
        kws = extract_page_keywords('<html></html>')
        self.assertIsInstance(kws, set)

    def test_returns_set(self):
        kws = extract_page_keywords('<title>test test test</title>')
        self.assertIsInstance(kws, set)


class TestCompareSites(unittest.TestCase):

    @patch("seo_competitor.validate_url", return_value={"valid": False, "error": "bad"})
    def test_invalid_url_a(self, mock_val):
        result = compare_sites("bad", "https://b.com")
        self.assertFalse(result["success"])
        self.assertIn("URL A", result["error"])

    @patch("seo_competitor.validate_url", side_effect=[{"valid": True}, {"valid": False, "error": "bad"}])
    def test_invalid_url_b(self, mock_val):
        result = compare_sites("https://a.com", "bad")
        self.assertFalse(result["success"])
        self.assertIn("URL B", result["error"])

    @patch("seo_competitor.validate_url", return_value={"valid": True})
    @patch("seo_competitor.fetch_page")
    def test_fetch_failure_a(self, mock_fetch, mock_val):
        mock_fetch.side_effect = [
            {"success": False, "error": "timeout"},
            {"success": True, "html": "<html></html>"},
        ]
        result = compare_sites("https://a.com", "https://b.com")
        self.assertFalse(result["success"])

    @patch("seo_competitor.validate_url", return_value={"valid": True})
    @patch("seo_competitor.fetch_page")
    def test_successful_comparison(self, mock_fetch, mock_val):
        mock_fetch.side_effect = [
            {"success": True, "html": "<title>Coffee Shop Seoul</title>", "elapsed_seconds": 0.5},
            {"success": True, "html": "<title>Tea House Seoul</title>", "elapsed_seconds": 0.3},
        ]
        result = compare_sites("https://a.com", "https://b.com")
        self.assertTrue(result["success"])
        self.assertIn("shared_keywords", result)
        self.assertIn("only_in_a", result)
        self.assertIn("only_in_b", result)
        self.assertGreater(result["shared_keywords"], 0)

    @patch("seo_competitor.validate_url", return_value={"valid": True})
    @patch("seo_competitor.fetch_page")
    def test_gaps_and_advantages(self, mock_fetch, mock_val):
        mock_fetch.side_effect = [
            {"success": True, "html": "<title>Alpha Beta</title>", "elapsed_seconds": 0.1},
            {"success": True, "html": "<title>Beta Gamma</title>", "elapsed_seconds": 0.1},
        ]
        result = compare_sites("https://a.com", "https://b.com")
        self.assertIn("gaps_for_a", result)
        self.assertIn("advantages_for_a", result)

    @patch("seo_competitor.validate_url", return_value={"valid": True})
    @patch("seo_competitor.fetch_page")
    def test_schema_comparison(self, mock_fetch, mock_val):
        mock_fetch.side_effect = [
            {"success": True, "html": '<script type="application/ld+json">{}</script>', "elapsed_seconds": 0.1},
            {"success": True, "html": "<html></html>", "elapsed_seconds": 0.1},
        ]
        result = compare_sites("https://a.com", "https://b.com")
        self.assertTrue(result["schema_comparison"]["a_has_schema"])
        self.assertFalse(result["schema_comparison"]["b_has_schema"])

    @patch("seo_competitor.validate_url", return_value={"valid": True})
    @patch("seo_competitor.fetch_page")
    def test_result_keys(self, mock_fetch, mock_val):
        mock_fetch.return_value = {"success": True, "html": "<html></html>", "elapsed_seconds": 0.1}
        result = compare_sites("https://a.com", "https://b.com")
        for key in ["success", "url_a", "url_b", "keywords_a_count", "keywords_b_count",
                     "shared_keywords", "gaps_for_a", "advantages_for_a", "schema_comparison", "response_time"]:
            self.assertIn(key, result)


if __name__ == "__main__":
    unittest.main()

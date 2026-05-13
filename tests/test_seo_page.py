"""Tests for seo_page.py — single-page SEO analysis."""

import sys
import os
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from seo_page import (
    analyze_title, analyze_meta_description, analyze_images,
    analyze_links, analyze_single_page,
)


class TestAnalyzeTitle(unittest.TestCase):

    def test_present(self):
        result = analyze_title("<html><head><title>My Page Title</title></head></html>")
        self.assertTrue(result["present"])
        self.assertEqual(result["text"], "My Page Title")

    def test_missing(self):
        result = analyze_title("<html><head></head></html>")
        self.assertFalse(result["present"])
        self.assertIsNone(result["text"])
        self.assertEqual(result["length"], 0)

    def test_length(self):
        result = analyze_title("<title>Hello World</title>")
        self.assertEqual(result["length"], 11)

    def test_korean_chars(self):
        result = analyze_title("<title>서울 맛집 추천</title>")
        self.assertGreater(result["korean_chars"], 0)

    def test_too_long_english(self):
        long_title = "A" * 65
        result = analyze_title(f"<title>{long_title}</title>")
        self.assertTrue(result["too_long"])

    def test_not_too_long_english(self):
        result = analyze_title("<title>Short Title</title>")
        self.assertFalse(result["too_long"])

    def test_too_long_korean(self):
        long_kr = "가" * 35
        result = analyze_title(f"<title>{long_kr}</title>")
        self.assertTrue(result["too_long"])

    def test_not_too_long_korean(self):
        result = analyze_title("<title>서울 맛집</title>")
        self.assertFalse(result["too_long"])

    def test_whitespace_stripped(self):
        result = analyze_title("<title>  Spaced Title  </title>")
        self.assertEqual(result["text"], "Spaced Title")

    def test_case_insensitive(self):
        result = analyze_title("<TITLE>Upper Case</TITLE>")
        self.assertTrue(result["present"])


class TestAnalyzeMetaDescription(unittest.TestCase):

    def test_present(self):
        html = '<meta name="description" content="A great description">'
        result = analyze_meta_description(html)
        self.assertTrue(result["present"])
        self.assertEqual(result["text"], "A great description")

    def test_missing(self):
        result = analyze_meta_description("<html><head></head></html>")
        self.assertFalse(result["present"])

    def test_reversed_attribute_order(self):
        html = '<meta content="Reversed order" name="description">'
        result = analyze_meta_description(html)
        self.assertTrue(result["present"])
        self.assertEqual(result["text"], "Reversed order")

    def test_too_long_english(self):
        long_desc = "A" * 170
        html = f'<meta name="description" content="{long_desc}">'
        result = analyze_meta_description(html)
        self.assertTrue(result["too_long"])

    def test_not_too_long_english(self):
        html = '<meta name="description" content="Short description for the page.">'
        result = analyze_meta_description(html)
        self.assertFalse(result["too_long"])

    def test_too_long_korean(self):
        long_kr = "가" * 85
        html = f'<meta name="description" content="{long_kr}">'
        result = analyze_meta_description(html)
        self.assertTrue(result["too_long"])

    def test_korean_chars_counted(self):
        html = '<meta name="description" content="서울 최고의 맛집 정보">'
        result = analyze_meta_description(html)
        self.assertGreater(result["korean_chars"], 0)

    def test_length(self):
        html = '<meta name="description" content="Exactly this.">'
        result = analyze_meta_description(html)
        self.assertEqual(result["length"], len("Exactly this."))


class TestAnalyzeImages(unittest.TestCase):

    def test_no_images(self):
        result = analyze_images("<html><body>No images</body></html>")
        self.assertEqual(result["total"], 0)
        self.assertEqual(result["missing_alt"], 0)

    def test_with_alt(self):
        html = '<img src="a.jpg" alt="Photo"><img src="b.jpg" alt="Logo">'
        result = analyze_images(html)
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["with_alt"], 2)
        self.assertEqual(result["missing_alt"], 0)

    def test_missing_alt(self):
        html = '<img src="a.jpg"><img src="b.jpg" alt="OK">'
        result = analyze_images(html)
        self.assertEqual(result["missing_alt"], 1)
        self.assertEqual(result["with_alt"], 1)

    def test_empty_alt_counted_as_missing(self):
        html = '<img src="a.jpg" alt="">'
        result = analyze_images(html)
        self.assertEqual(result["missing_alt"], 1)

    def test_alt_ratio(self):
        html = '<img src="a.jpg" alt="X"><img src="b.jpg">'
        result = analyze_images(html)
        self.assertEqual(result["alt_ratio"], 0.5)

    def test_alt_ratio_no_images(self):
        result = analyze_images("<html></html>")
        self.assertEqual(result["alt_ratio"], 0)


class TestAnalyzeLinks(unittest.TestCase):

    def test_internal_links(self):
        html = '<a href="/about">About</a><a href="https://example.com/page">Page</a>'
        result = analyze_links(html, "https://example.com")
        self.assertEqual(result["internal"], 2)

    def test_external_links(self):
        html = '<a href="https://other.com/page">Other</a>'
        result = analyze_links(html, "https://example.com")
        self.assertEqual(result["external"], 1)

    def test_mixed_links(self):
        html = '<a href="/about">A</a><a href="https://other.com">B</a><a href="https://example.com/c">C</a>'
        result = analyze_links(html, "https://example.com")
        self.assertEqual(result["internal"], 2)
        self.assertEqual(result["external"], 1)
        self.assertEqual(result["total"], 3)

    def test_no_links(self):
        result = analyze_links("<html><body>No links</body></html>", "https://example.com")
        self.assertEqual(result["total"], 0)

    def test_relative_counted_internal(self):
        html = '<a href="/page1">P1</a><a href="/page2">P2</a>'
        result = analyze_links(html, "https://example.com")
        self.assertEqual(result["internal"], 2)


class TestAnalyzeSinglePage(unittest.TestCase):

    def _full_html(self):
        return (
            '<html><head>'
            '<title>Test Page Title</title>'
            '<meta name="description" content="A good description for testing.">'
            '<link rel="canonical" href="https://example.com/page">'
            '<script type="application/ld+json">{"@type":"WebPage"}</script>'
            '</head><body>'
            '<h1>Main Heading</h1>'
            '<img src="a.jpg" alt="Photo">'
            '<a href="/about">About</a>'
            '</body></html>'
        )

    @patch("seo_page.validate_url", return_value={"valid": False, "error": "bad"})
    def test_invalid_url(self, mock_val):
        result = analyze_single_page("bad")
        self.assertFalse(result["success"])

    @patch("seo_page.validate_url", return_value={"valid": True})
    @patch("seo_page.fetch_page", return_value={"success": False, "error": "timeout"})
    def test_fetch_failure(self, mock_fetch, mock_val):
        result = analyze_single_page("https://x.com")
        self.assertFalse(result["success"])

    @patch("seo_page.validate_url", return_value={"valid": True})
    @patch("seo_page.fetch_page")
    def test_perfect_page(self, mock_fetch, mock_val):
        mock_fetch.return_value = {"success": True, "html": self._full_html(), "elapsed_seconds": 0.3}
        result = analyze_single_page("https://example.com/page")
        self.assertTrue(result["success"])
        self.assertEqual(result["score"], 100)
        self.assertEqual(len(result["issues"]), 0)

    @patch("seo_page.validate_url", return_value={"valid": True})
    @patch("seo_page.fetch_page")
    def test_missing_title_critical(self, mock_fetch, mock_val):
        html = '<html><head></head><body><h1>H1</h1></body></html>'
        mock_fetch.return_value = {"success": True, "html": html, "elapsed_seconds": 0.3}
        result = analyze_single_page("https://x.com")
        issues = [i["message"] for i in result["issues"]]
        self.assertTrue(any("title" in i.lower() for i in issues))
        self.assertLess(result["score"], 100)

    @patch("seo_page.validate_url", return_value={"valid": True})
    @patch("seo_page.fetch_page")
    def test_missing_h1_critical(self, mock_fetch, mock_val):
        html = '<html><head><title>T</title></head><body><h2>Sub</h2></body></html>'
        mock_fetch.return_value = {"success": True, "html": html, "elapsed_seconds": 0.3}
        result = analyze_single_page("https://x.com")
        issues = [i["message"] for i in result["issues"]]
        self.assertTrue(any("H1" in i for i in issues))

    @patch("seo_page.validate_url", return_value={"valid": True})
    @patch("seo_page.fetch_page")
    def test_multiple_h1(self, mock_fetch, mock_val):
        html = '<html><head><title>T</title></head><body><h1>A</h1><h1>B</h1></body></html>'
        mock_fetch.return_value = {"success": True, "html": html, "elapsed_seconds": 0.3}
        result = analyze_single_page("https://x.com")
        self.assertEqual(result["h1_count"], 2)
        issues = [i["message"] for i in result["issues"]]
        self.assertTrue(any("Multiple H1" in i for i in issues))

    @patch("seo_page.validate_url", return_value={"valid": True})
    @patch("seo_page.fetch_page")
    def test_missing_meta_desc(self, mock_fetch, mock_val):
        html = '<html><head><title>T</title></head><body><h1>H</h1></body></html>'
        mock_fetch.return_value = {"success": True, "html": html, "elapsed_seconds": 0.3}
        result = analyze_single_page("https://x.com")
        issues = [i["message"] for i in result["issues"]]
        self.assertTrue(any("meta description" in i.lower() for i in issues))

    @patch("seo_page.validate_url", return_value={"valid": True})
    @patch("seo_page.fetch_page")
    def test_missing_schema(self, mock_fetch, mock_val):
        html = '<html><head><title>T</title></head><body><h1>H</h1></body></html>'
        mock_fetch.return_value = {"success": True, "html": html, "elapsed_seconds": 0.3}
        result = analyze_single_page("https://x.com")
        self.assertFalse(result["has_schema"])

    @patch("seo_page.validate_url", return_value={"valid": True})
    @patch("seo_page.fetch_page")
    def test_missing_canonical(self, mock_fetch, mock_val):
        html = '<html><head><title>T</title></head><body><h1>H</h1></body></html>'
        mock_fetch.return_value = {"success": True, "html": html, "elapsed_seconds": 0.3}
        result = analyze_single_page("https://x.com")
        self.assertFalse(result["has_canonical"])

    @patch("seo_page.validate_url", return_value={"valid": True})
    @patch("seo_page.fetch_page")
    def test_result_keys(self, mock_fetch, mock_val):
        mock_fetch.return_value = {"success": True, "html": self._full_html(), "elapsed_seconds": 0.3}
        result = analyze_single_page("https://example.com")
        for key in ["success", "url", "score", "title", "meta_description",
                     "h1_count", "images", "links", "has_schema", "has_canonical", "issues"]:
            self.assertIn(key, result, f"Missing: {key}")

    @patch("seo_page.validate_url", return_value={"valid": True})
    @patch("seo_page.fetch_page")
    def test_score_clamped(self, mock_fetch, mock_val):
        html = '<html><head></head><body></body></html>'
        mock_fetch.return_value = {"success": True, "html": html, "elapsed_seconds": 0.3}
        result = analyze_single_page("https://x.com")
        self.assertGreaterEqual(result["score"], 0)
        self.assertLessEqual(result["score"], 100)


if __name__ == "__main__":
    unittest.main()

"""Tests for seo_naver.py — Naver-specific SEO analysis."""

import sys
import os
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from seo_naver import (
    check_naver_verification,
    check_open_graph,
    check_naver_bot_access,
    analyze_naver_seo,
)


class TestCheckNaverVerification(unittest.TestCase):

    def test_present(self):
        html = '<meta name="naver-site-verification" content="abc123">'
        result = check_naver_verification(html)
        self.assertTrue(result["present"])
        self.assertEqual(result["code"], "abc123")

    def test_reversed_attrs(self):
        html = '<meta content="xyz789" name="naver-site-verification">'
        result = check_naver_verification(html)
        self.assertTrue(result["present"])
        self.assertEqual(result["code"], "xyz789")

    def test_not_present(self):
        html = '<html><head></head></html>'
        result = check_naver_verification(html)
        self.assertFalse(result["present"])
        self.assertIsNone(result["code"])

    def test_other_meta_tags_ignored(self):
        html = '<meta name="google-site-verification" content="abc">'
        result = check_naver_verification(html)
        self.assertFalse(result["present"])


class TestCheckOpenGraph(unittest.TestCase):

    def test_complete_og(self):
        html = '''
        <meta property="og:title" content="Title">
        <meta property="og:description" content="Desc">
        <meta property="og:image" content="https://x.com/img.jpg">
        <meta property="og:url" content="https://x.com">
        '''
        result = check_open_graph(html)
        self.assertTrue(result["complete"])
        self.assertEqual(len(result["missing_required"]), 0)
        self.assertEqual(result["count"], 4)

    def test_missing_og(self):
        html = '<meta property="og:title" content="Title">'
        result = check_open_graph(html)
        self.assertFalse(result["complete"])
        self.assertIn("og:description", result["missing_required"])

    def test_no_og_tags(self):
        html = '<html><head></head></html>'
        result = check_open_graph(html)
        self.assertFalse(result["complete"])
        self.assertEqual(result["count"], 0)
        self.assertEqual(len(result["missing_required"]), 4)

    def test_reversed_attrs(self):
        html = '<meta content="Title" property="og:title">'
        result = check_open_graph(html)
        self.assertIn("og:title", result["tags_found"])

    def test_extra_og_tags_counted(self):
        html = '''
        <meta property="og:title" content="T">
        <meta property="og:description" content="D">
        <meta property="og:image" content="I">
        <meta property="og:url" content="U">
        <meta property="og:type" content="website">
        '''
        result = check_open_graph(html)
        self.assertEqual(result["count"], 5)


class TestCheckNaverBotAccess(unittest.TestCase):

    @patch("seo_naver.fetch_page")
    def test_no_robots_txt(self, mock_fetch):
        mock_fetch.return_value = {"success": False, "error": "404"}
        result = check_naver_bot_access("https://x.com")
        self.assertTrue(result["accessible"])
        self.assertFalse(result["robots_txt"])

    @patch("seo_naver.fetch_page")
    def test_yeti_not_blocked(self, mock_fetch):
        mock_fetch.return_value = {"success": True, "html": "User-agent: *\nDisallow: /admin"}
        result = check_naver_bot_access("https://x.com")
        self.assertTrue(result["accessible"])

    @patch("seo_naver.fetch_page")
    def test_yeti_blocked_wildcard(self, mock_fetch):
        mock_fetch.return_value = {"success": True, "html": "User-agent: *\nDisallow: /"}
        result = check_naver_bot_access("https://x.com")
        self.assertFalse(result["accessible"])
        self.assertTrue(result["yeti_blocked"])

    @patch("seo_naver.fetch_page")
    def test_yeti_blocked_specific(self, mock_fetch):
        mock_fetch.return_value = {"success": True, "html": "User-agent: Yeti\nDisallow: /"}
        result = check_naver_bot_access("https://x.com")
        self.assertFalse(result["accessible"])

    @patch("seo_naver.fetch_page")
    def test_other_bot_blocked_yeti_ok(self, mock_fetch):
        mock_fetch.return_value = {"success": True, "html": "User-agent: Googlebot\nDisallow: /\nUser-agent: Yeti\nDisallow:"}
        result = check_naver_bot_access("https://x.com")
        self.assertTrue(result["accessible"])


class TestAnalyzeNaverSeo(unittest.TestCase):

    @patch("seo_naver.validate_url", return_value={"valid": False, "error": "bad"})
    def test_invalid_url(self, mock_val):
        result = analyze_naver_seo("bad")
        self.assertFalse(result["success"])

    @patch("seo_naver.validate_url", return_value={"valid": True})
    @patch("seo_naver.fetch_page", return_value={"success": False, "error": "timeout"})
    def test_fetch_failure(self, mock_fetch, mock_val):
        result = analyze_naver_seo("https://x.com")
        self.assertFalse(result["success"])

    @patch("seo_naver.validate_url", return_value={"valid": True})
    @patch("seo_naver.fetch_page")
    def test_perfect_page(self, mock_fetch, mock_val):
        html = '''<html><head>
        <meta name="naver-site-verification" content="abc">
        <meta property="og:title" content="T">
        <meta property="og:description" content="D">
        <meta property="og:image" content="I">
        <meta property="og:url" content="U">
        </head></html>'''
        mock_fetch.side_effect = [
            {"success": True, "html": html},
            {"success": True, "html": "User-agent: *\nDisallow: /admin"},
        ]
        result = analyze_naver_seo("https://x.com")
        self.assertTrue(result["success"])
        self.assertEqual(result["score"], 100)

    @patch("seo_naver.validate_url", return_value={"valid": True})
    @patch("seo_naver.fetch_page")
    def test_missing_verification_issue(self, mock_fetch, mock_val):
        html = '<html><head></head></html>'
        mock_fetch.side_effect = [
            {"success": True, "html": html},
            {"success": False, "error": "404"},
        ]
        result = analyze_naver_seo("https://x.com")
        msgs = [i["message"] for i in result["issues"]]
        self.assertTrue(any("naver-site-verification" in m for m in msgs))

    @patch("seo_naver.validate_url", return_value={"valid": True})
    @patch("seo_naver.fetch_page")
    def test_yeti_blocked_critical(self, mock_fetch, mock_val):
        html = '<html><head><meta name="naver-site-verification" content="x"></head></html>'
        mock_fetch.side_effect = [
            {"success": True, "html": html},
            {"success": True, "html": "User-agent: *\nDisallow: /"},
        ]
        result = analyze_naver_seo("https://x.com")
        critical = [i for i in result["issues"] if i["severity"] == "critical"]
        self.assertGreater(len(critical), 0)

    @patch("seo_naver.validate_url", return_value={"valid": True})
    @patch("seo_naver.fetch_page")
    def test_result_keys(self, mock_fetch, mock_val):
        mock_fetch.side_effect = [
            {"success": True, "html": "<html></html>"},
            {"success": False, "error": "404"},
        ]
        result = analyze_naver_seo("https://x.com")
        for key in ["success", "url", "score", "naver_verification", "open_graph", "bot_access", "issues"]:
            self.assertIn(key, result)

    @patch("seo_naver.validate_url", return_value={"valid": True})
    @patch("seo_naver.fetch_page")
    def test_score_clamped(self, mock_fetch, mock_val):
        mock_fetch.side_effect = [
            {"success": True, "html": "<html></html>"},
            {"success": True, "html": "User-agent: *\nDisallow: /"},
        ]
        result = analyze_naver_seo("https://x.com")
        self.assertGreaterEqual(result["score"], 0)
        self.assertLessEqual(result["score"], 100)


if __name__ == "__main__":
    unittest.main()

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
    check_x_robots_tag,
    check_meta_description_korean,
    check_naver_ecosystem,
    check_mobile_viewport,
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


class TestCheckXRobotsTag(unittest.TestCase):

    def test_no_header(self):
        result = check_x_robots_tag({})
        self.assertFalse(result["present"])
        self.assertFalse(result["noindex"])

    def test_noindex(self):
        result = check_x_robots_tag({"x-robots-tag": "noindex"})
        self.assertTrue(result["present"])
        self.assertTrue(result["noindex"])

    def test_nofollow(self):
        result = check_x_robots_tag({"x-robots-tag": "nofollow"})
        self.assertTrue(result["nofollow"])

    def test_yeti_specific(self):
        result = check_x_robots_tag({"x-robots-tag": "yeti: noindex"})
        self.assertTrue(result["yeti_specific"])
        self.assertTrue(result["noindex"])

    def test_case_insensitive_key(self):
        result = check_x_robots_tag({"X-Robots-Tag": "noindex, nofollow"})
        self.assertTrue(result["noindex"])
        self.assertTrue(result["nofollow"])


class TestCheckMetaDescriptionKorean(unittest.TestCase):

    def test_no_description(self):
        result = check_meta_description_korean("<html></html>")
        self.assertFalse(result["present"])

    def test_korean_optimal(self):
        desc = "스카이벤처스는 디지털 마케팅 전문 에이전시입니다. 검색엔진 최적화와 AI 가시성 최적화 서비스를 제공합니다."
        html = f'<meta name="description" content="{desc}">'
        result = check_meta_description_korean(html)
        self.assertTrue(result["present"])
        self.assertTrue(result["is_korean"])

    def test_korean_too_long(self):
        desc = "가" * 100
        html = f'<meta name="description" content="{desc}">'
        result = check_meta_description_korean(html)
        self.assertTrue(result["truncated_by_naver"])
        self.assertEqual(result["length"], 100)

    def test_korean_within_limit(self):
        desc = "가" * 50
        html = f'<meta name="description" content="{desc}">'
        result = check_meta_description_korean(html)
        self.assertFalse(result["truncated_by_naver"])
        self.assertTrue(result["optimal"])

    def test_english_description(self):
        html = '<meta name="description" content="This is a good English description for search engines.">'
        result = check_meta_description_korean(html)
        self.assertFalse(result["is_korean"])
        self.assertTrue(result["optimal"])

    def test_reversed_attrs(self):
        html = '<meta content="설명입니다" name="description">'
        result = check_meta_description_korean(html)
        self.assertTrue(result["present"])


class TestCheckNaverEcosystem(unittest.TestCase):

    def test_no_links(self):
        result = check_naver_ecosystem("<html><body></body></html>")
        self.assertEqual(result["linked_count"], 0)

    def test_blog_link(self):
        html = '<a href="https://blog.naver.com/myshop">Blog</a>'
        result = check_naver_ecosystem(html)
        self.assertTrue(result["links"]["blog"])
        self.assertEqual(result["linked_count"], 1)

    def test_place_link(self):
        html = '<a href="https://place.naver.com/restaurant/12345">Place</a>'
        result = check_naver_ecosystem(html)
        self.assertTrue(result["links"]["place"])

    def test_smartstore_link(self):
        html = '<a href="https://smartstore.naver.com/myshop">Shop</a>'
        result = check_naver_ecosystem(html)
        self.assertTrue(result["links"]["smartstore"])

    def test_cafe_link(self):
        html = '<a href="https://cafe.naver.com/mycafe">Cafe</a>'
        result = check_naver_ecosystem(html)
        self.assertTrue(result["links"]["cafe"])

    def test_map_link(self):
        html = '<a href="https://map.naver.com/v5/search">Map</a>'
        result = check_naver_ecosystem(html)
        self.assertTrue(result["links"]["map"])

    def test_multiple_links(self):
        html = '''
        <a href="https://blog.naver.com/x">Blog</a>
        <a href="https://smartstore.naver.com/x">Store</a>
        <a href="https://place.naver.com/x">Place</a>
        '''
        result = check_naver_ecosystem(html)
        self.assertEqual(result["linked_count"], 3)


class TestCheckMobileViewport(unittest.TestCase):

    def test_no_viewport(self):
        result = check_mobile_viewport("<html></html>")
        self.assertFalse(result["present"])
        self.assertFalse(result["mobile_friendly"])

    def test_proper_viewport(self):
        html = '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
        result = check_mobile_viewport(html)
        self.assertTrue(result["present"])
        self.assertTrue(result["mobile_friendly"])

    def test_incomplete_viewport(self):
        html = '<meta name="viewport" content="width=1024">'
        result = check_mobile_viewport(html)
        self.assertTrue(result["present"])
        self.assertFalse(result["mobile_friendly"])

    def test_reversed_attrs(self):
        html = '<meta content="width=device-width, initial-scale=1" name="viewport">'
        result = check_mobile_viewport(html)
        self.assertTrue(result["mobile_friendly"])


class TestAnalyzeNaverSeo(unittest.TestCase):

    def _full_html(self):
        return '''<html><head>
        <meta name="naver-site-verification" content="abc">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta name="description" content="스카이벤처스 디지털 마케팅 전문 에이전시">
        <meta property="og:title" content="T">
        <meta property="og:description" content="D">
        <meta property="og:image" content="I">
        <meta property="og:url" content="U">
        </head><body></body></html>'''

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
        mock_fetch.side_effect = [
            {"success": True, "html": self._full_html(), "headers": {}},
            {"success": True, "html": "User-agent: *\nDisallow: /admin"},
        ]
        result = analyze_naver_seo("https://x.com")
        self.assertTrue(result["success"])
        self.assertEqual(result["score"], 100)

    @patch("seo_naver.validate_url", return_value={"valid": True})
    @patch("seo_naver.fetch_page")
    def test_missing_verification_issue(self, mock_fetch, mock_val):
        html = '<html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><meta name="description" content="test desc for seo"></head></html>'
        mock_fetch.side_effect = [
            {"success": True, "html": html, "headers": {}},
            {"success": False, "error": "404"},
        ]
        result = analyze_naver_seo("https://x.com")
        msgs = [i["message"] for i in result["issues"]]
        self.assertTrue(any("naver-site-verification" in m for m in msgs))

    @patch("seo_naver.validate_url", return_value={"valid": True})
    @patch("seo_naver.fetch_page")
    def test_yeti_blocked_critical(self, mock_fetch, mock_val):
        mock_fetch.side_effect = [
            {"success": True, "html": self._full_html(), "headers": {}},
            {"success": True, "html": "User-agent: *\nDisallow: /"},
        ]
        result = analyze_naver_seo("https://x.com")
        critical = [i for i in result["issues"] if i["severity"] == "critical"]
        self.assertGreater(len(critical), 0)

    @patch("seo_naver.validate_url", return_value={"valid": True})
    @patch("seo_naver.fetch_page")
    def test_result_keys(self, mock_fetch, mock_val):
        mock_fetch.side_effect = [
            {"success": True, "html": "<html></html>", "headers": {}},
            {"success": False, "error": "404"},
        ]
        result = analyze_naver_seo("https://x.com")
        for key in ["success", "url", "score", "naver_verification", "open_graph",
                     "bot_access", "x_robots_tag", "meta_description",
                     "naver_ecosystem", "mobile_viewport", "issues"]:
            self.assertIn(key, result)

    @patch("seo_naver.validate_url", return_value={"valid": True})
    @patch("seo_naver.fetch_page")
    def test_score_clamped(self, mock_fetch, mock_val):
        mock_fetch.side_effect = [
            {"success": True, "html": "<html></html>", "headers": {}},
            {"success": True, "html": "User-agent: *\nDisallow: /"},
        ]
        result = analyze_naver_seo("https://x.com")
        self.assertGreaterEqual(result["score"], 0)
        self.assertLessEqual(result["score"], 100)

    @patch("seo_naver.validate_url", return_value={"valid": True})
    @patch("seo_naver.fetch_page")
    def test_x_robots_noindex_critical(self, mock_fetch, mock_val):
        mock_fetch.side_effect = [
            {"success": True, "html": self._full_html(), "headers": {"x-robots-tag": "noindex"}},
            {"success": True, "html": "User-agent: *\nDisallow: /admin"},
        ]
        result = analyze_naver_seo("https://x.com")
        critical = [i for i in result["issues"] if i["severity"] == "critical"]
        self.assertTrue(any("X-Robots-Tag" in i["message"] for i in critical))

    @patch("seo_naver.validate_url", return_value={"valid": True})
    @patch("seo_naver.fetch_page")
    def test_missing_viewport_issue(self, mock_fetch, mock_val):
        html = '<html><head><meta name="naver-site-verification" content="x"><meta name="description" content="test"></head></html>'
        mock_fetch.side_effect = [
            {"success": True, "html": html, "headers": {}},
            {"success": True, "html": "User-agent: *\nDisallow: /admin"},
        ]
        result = analyze_naver_seo("https://x.com")
        msgs = [i["message"] for i in result["issues"]]
        self.assertTrue(any("viewport" in m for m in msgs))

    @patch("seo_naver.validate_url", return_value={"valid": True})
    @patch("seo_naver.fetch_page")
    def test_crawl_delay_warning(self, mock_fetch, mock_val):
        mock_fetch.side_effect = [
            {"success": True, "html": self._full_html(), "headers": {}},
            {"success": True, "html": "User-agent: *\nCrawl-delay: 30\nDisallow: /admin"},
        ]
        result = analyze_naver_seo("https://x.com")
        msgs = [i["message"] for i in result["issues"]]
        self.assertTrue(any("crawl-delay" in m.lower() for m in msgs))


if __name__ == "__main__":
    unittest.main()

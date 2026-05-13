"""Tests for seo_indexing.py — indexing and crawl management."""

import sys
import os
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from seo_indexing import (
    check_robots_txt, check_sitemap, check_indexnow,
    check_meta_robots, analyze_indexing,
)


class TestCheckRobotsTxt(unittest.TestCase):

    @patch("seo_indexing.fetch_page")
    def test_exists(self, mock_fetch):
        content = "User-agent: *\nDisallow: /admin\nSitemap: https://x.com/sitemap.xml"
        mock_fetch.return_value = {"success": True, "status_code": 200, "html": content}
        result = check_robots_txt("https://x.com")
        self.assertTrue(result["exists"])
        self.assertEqual(len(result["sitemaps_declared"]), 1)
        self.assertTrue(result["disallow_all_detected"])

    @patch("seo_indexing.fetch_page")
    def test_not_found(self, mock_fetch):
        mock_fetch.return_value = {"success": False, "error": "404"}
        result = check_robots_txt("https://x.com")
        self.assertFalse(result["exists"])

    @patch("seo_indexing.fetch_page")
    def test_disallow_all(self, mock_fetch):
        mock_fetch.return_value = {"success": True, "status_code": 200, "html": "User-agent: *\nDisallow: /"}
        result = check_robots_txt("https://x.com")
        self.assertTrue(result["disallow_all_detected"])

    @patch("seo_indexing.fetch_page")
    def test_multiple_sitemaps(self, mock_fetch):
        content = "Sitemap: https://x.com/s1.xml\nSitemap: https://x.com/s2.xml"
        mock_fetch.return_value = {"success": True, "status_code": 200, "html": content}
        result = check_robots_txt("https://x.com")
        self.assertEqual(len(result["sitemaps_declared"]), 2)

    @patch("seo_indexing.fetch_page")
    def test_size_bytes(self, mock_fetch):
        content = "User-agent: *\nDisallow:"
        mock_fetch.return_value = {"success": True, "status_code": 200, "html": content}
        result = check_robots_txt("https://x.com")
        self.assertEqual(result["size_bytes"], len(content))


class TestCheckSitemap(unittest.TestCase):

    @patch("seo_indexing.fetch_page")
    def test_exists(self, mock_fetch):
        xml = '<urlset><url><loc>https://x.com/a</loc></url><url><loc>https://x.com/b</loc></url></urlset>'
        mock_fetch.return_value = {"success": True, "status_code": 200, "html": xml}
        result = check_sitemap("https://x.com")
        self.assertTrue(result["exists"])
        self.assertEqual(result["url_count"], 2)
        self.assertFalse(result["is_sitemap_index"])

    @patch("seo_indexing.fetch_page")
    def test_not_found(self, mock_fetch):
        mock_fetch.return_value = {"success": False, "error": "404"}
        result = check_sitemap("https://x.com")
        self.assertFalse(result["exists"])

    @patch("seo_indexing.fetch_page")
    def test_sitemap_index(self, mock_fetch):
        xml = '<sitemapindex><sitemap><loc>https://x.com/s1.xml</loc></sitemap></sitemapindex>'
        mock_fetch.return_value = {"success": True, "status_code": 200, "html": xml}
        result = check_sitemap("https://x.com")
        self.assertTrue(result["is_sitemap_index"])

    @patch("seo_indexing.fetch_page")
    def test_has_lastmod(self, mock_fetch):
        xml = '<urlset><url><loc>https://x.com/a</loc><lastmod>2024-01-01</lastmod></url></urlset>'
        mock_fetch.return_value = {"success": True, "status_code": 200, "html": xml}
        result = check_sitemap("https://x.com")
        self.assertTrue(result["has_lastmod"])

    @patch("seo_indexing.fetch_page")
    def test_no_lastmod(self, mock_fetch):
        xml = '<urlset><url><loc>https://x.com/a</loc></url></urlset>'
        mock_fetch.return_value = {"success": True, "status_code": 200, "html": xml}
        result = check_sitemap("https://x.com")
        self.assertFalse(result["has_lastmod"])

    @patch("seo_indexing.fetch_page")
    def test_sample_urls_max_5(self, mock_fetch):
        locs = "".join(f"<url><loc>https://x.com/{i}</loc></url>" for i in range(10))
        xml = f"<urlset>{locs}</urlset>"
        mock_fetch.return_value = {"success": True, "status_code": 200, "html": xml}
        result = check_sitemap("https://x.com")
        self.assertEqual(len(result["sample_urls"]), 5)
        self.assertEqual(result["url_count"], 10)


class TestCheckIndexNow(unittest.TestCase):

    @patch("seo_indexing.fetch_page")
    def test_configured(self, mock_fetch):
        mock_fetch.return_value = {"success": True, "status_code": 200}
        result = check_indexnow("https://x.com")
        self.assertTrue(result["configured"])

    @patch("seo_indexing.fetch_page")
    def test_not_configured(self, mock_fetch):
        mock_fetch.return_value = {"success": False, "error": "404"}
        result = check_indexnow("https://x.com")
        self.assertFalse(result["configured"])

    @patch("seo_indexing.fetch_page")
    def test_checks_two_locations(self, mock_fetch):
        mock_fetch.return_value = {"success": False, "error": "404"}
        check_indexnow("https://x.com")
        self.assertEqual(mock_fetch.call_count, 2)


class TestCheckMetaRobots(unittest.TestCase):

    def test_noindex(self):
        html = '<meta name="robots" content="noindex">'
        result = check_meta_robots(html)
        self.assertTrue(result["noindex"])

    def test_nofollow(self):
        html = '<meta name="robots" content="nofollow">'
        result = check_meta_robots(html)
        self.assertTrue(result["nofollow"])

    def test_noindex_nofollow(self):
        html = '<meta name="robots" content="noindex, nofollow">'
        result = check_meta_robots(html)
        self.assertTrue(result["noindex"])
        self.assertTrue(result["nofollow"])

    def test_index_follow(self):
        html = '<meta name="robots" content="index, follow">'
        result = check_meta_robots(html)
        self.assertFalse(result["noindex"])
        self.assertFalse(result["nofollow"])

    def test_no_meta_robots(self):
        html = '<html><head></head></html>'
        result = check_meta_robots(html)
        self.assertFalse(result["noindex"])
        self.assertFalse(result["nofollow"])

    def test_canonical(self):
        html = '<link rel="canonical" href="https://x.com/page">'
        result = check_meta_robots(html)
        self.assertEqual(result["canonical"], "https://x.com/page")

    def test_no_canonical(self):
        result = check_meta_robots("<html></html>")
        self.assertIsNone(result["canonical"])


class TestAnalyzeIndexing(unittest.TestCase):

    @patch("seo_indexing.validate_url", return_value={"valid": False, "error": "bad"})
    def test_invalid_url(self, mock_val):
        result = analyze_indexing("bad")
        self.assertFalse(result["success"])

    @patch("seo_indexing.validate_url", return_value={"valid": True})
    @patch("seo_indexing.fetch_page")
    def test_fetch_failure(self, mock_fetch, mock_val):
        mock_fetch.return_value = {"success": False, "error": "timeout"}
        result = analyze_indexing("https://x.com")
        self.assertFalse(result["success"])

    @patch("seo_indexing.validate_url", return_value={"valid": True})
    @patch("seo_indexing.fetch_page")
    def test_perfect_setup(self, mock_fetch, mock_val):
        html = '<html><head><link rel="canonical" href="https://x.com"></head></html>'
        robots = "User-agent: *\nDisallow:\nSitemap: https://x.com/sitemap.xml"
        sitemap = '<urlset><url><loc>https://x.com</loc><lastmod>2024-01-01</lastmod></url></urlset>'
        mock_fetch.side_effect = [
            {"success": True, "html": html},
            {"success": True, "status_code": 200, "html": robots},
            {"success": True, "status_code": 200, "html": sitemap},
            {"success": True, "status_code": 200},
        ]
        result = analyze_indexing("https://x.com")
        self.assertTrue(result["success"])
        self.assertEqual(result["score"], 100)

    @patch("seo_indexing.validate_url", return_value={"valid": True})
    @patch("seo_indexing.fetch_page")
    def test_no_sitemap_issue(self, mock_fetch, mock_val):
        mock_fetch.side_effect = [
            {"success": True, "html": "<html></html>"},
            {"success": True, "status_code": 200, "html": "User-agent: *\nDisallow:"},
            {"success": False, "error": "404"},
            {"success": False, "error": "404"},
            {"success": False, "error": "404"},
        ]
        result = analyze_indexing("https://x.com")
        issues = [i["message"] for i in result["issues"]]
        self.assertTrue(any("sitemap" in i.lower() for i in issues))

    @patch("seo_indexing.validate_url", return_value={"valid": True})
    @patch("seo_indexing.fetch_page")
    def test_noindex_critical(self, mock_fetch, mock_val):
        html = '<html><head><meta name="robots" content="noindex"></head></html>'
        mock_fetch.side_effect = [
            {"success": True, "html": html},
            {"success": True, "status_code": 200, "html": "User-agent: *\nDisallow:"},
            {"success": True, "status_code": 200, "html": "<urlset></urlset>"},
            {"success": False, "error": "404"},
            {"success": False, "error": "404"},
        ]
        result = analyze_indexing("https://x.com")
        issues = [i for i in result["issues"] if i["severity"] == "critical"]
        self.assertGreater(len(issues), 0)

    @patch("seo_indexing.validate_url", return_value={"valid": True})
    @patch("seo_indexing.fetch_page")
    def test_result_keys(self, mock_fetch, mock_val):
        mock_fetch.side_effect = [
            {"success": True, "html": "<html></html>"},
            {"success": False, "error": "404"},
            {"success": False, "error": "404"},
            {"success": False, "error": "404"},
            {"success": False, "error": "404"},
        ]
        result = analyze_indexing("https://x.com")
        for key in ["success", "url", "score", "robots_txt", "sitemap",
                     "indexnow", "meta_robots", "issues"]:
            self.assertIn(key, result, f"Missing: {key}")

    @patch("seo_indexing.validate_url", return_value={"valid": True})
    @patch("seo_indexing.fetch_page")
    def test_score_clamped(self, mock_fetch, mock_val):
        html = '<html><head><meta name="robots" content="noindex"></head></html>'
        mock_fetch.side_effect = [
            {"success": True, "html": html},
            {"success": False, "error": "404"},
            {"success": False, "error": "404"},
            {"success": False, "error": "404"},
            {"success": False, "error": "404"},
        ]
        result = analyze_indexing("https://x.com")
        self.assertGreaterEqual(result["score"], 0)
        self.assertLessEqual(result["score"], 100)


if __name__ == "__main__":
    unittest.main()

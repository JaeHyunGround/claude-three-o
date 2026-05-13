"""Tests for seo_sitemap.py — sitemap validation."""

import sys
import os
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from seo_sitemap import (
    fetch_sitemap,
    parse_sitemap,
    validate_sitemap,
)


class TestFetchSitemap(unittest.TestCase):

    @patch("seo_sitemap.fetch_page")
    def test_found_first_url(self, mock_fetch):
        mock_fetch.return_value = {"success": True, "status_code": 200, "html": "<urlset><url><loc>https://x.com</loc></url></urlset>"}
        result = fetch_sitemap("https://x.com")
        self.assertTrue(result["found"])
        self.assertIn("sitemap.xml", result["url"])

    @patch("seo_sitemap.fetch_page")
    def test_not_found(self, mock_fetch):
        mock_fetch.return_value = {"success": False, "error": "404"}
        result = fetch_sitemap("https://x.com")
        self.assertFalse(result["found"])

    @patch("seo_sitemap.fetch_page")
    def test_sitemap_index(self, mock_fetch):
        mock_fetch.return_value = {"success": True, "status_code": 200, "html": "<sitemapindex><sitemap><loc>https://x.com/s1.xml</loc></sitemap></sitemapindex>"}
        result = fetch_sitemap("https://x.com")
        self.assertTrue(result["found"])
        self.assertTrue(result.get("is_index"))

    @patch("seo_sitemap.fetch_page")
    def test_tries_multiple_urls(self, mock_fetch):
        mock_fetch.side_effect = [
            {"success": False, "error": "404"},
            {"success": False, "error": "404"},
            {"success": True, "status_code": 200, "html": "<urlset><url><loc>https://x.com</loc></url></urlset>"},
        ]
        result = fetch_sitemap("https://x.com")
        self.assertTrue(result["found"])
        self.assertEqual(mock_fetch.call_count, 3)

    @patch("seo_sitemap.fetch_page")
    def test_success_without_urlset_skipped(self, mock_fetch):
        mock_fetch.return_value = {"success": True, "status_code": 200, "html": "<html>Not a sitemap</html>"}
        result = fetch_sitemap("https://x.com")
        self.assertFalse(result["found"])


class TestParseSitemap(unittest.TestCase):

    def test_basic_urls(self):
        xml = "<urlset><url><loc>https://x.com/a</loc></url><url><loc>https://x.com/b</loc></url></urlset>"
        result = parse_sitemap(xml)
        self.assertEqual(result["url_count"], 2)
        self.assertFalse(result["is_index"])

    def test_sitemap_index(self):
        xml = "<sitemapindex><sitemap><loc>https://x.com/s1.xml</loc></sitemap></sitemapindex>"
        result = parse_sitemap(xml)
        self.assertTrue(result["is_index"])
        self.assertEqual(len(result["child_sitemaps"]), 1)
        self.assertEqual(result["url_count"], 0)

    def test_has_lastmod(self):
        xml = "<urlset><url><loc>https://x.com/a</loc><lastmod>2024-01-01</lastmod></url></urlset>"
        result = parse_sitemap(xml)
        self.assertTrue(result["has_lastmod"])
        self.assertEqual(result["lastmod_coverage"], 1.0)

    def test_no_lastmod(self):
        xml = "<urlset><url><loc>https://x.com/a</loc></url></urlset>"
        result = parse_sitemap(xml)
        self.assertFalse(result["has_lastmod"])

    def test_partial_lastmod(self):
        xml = "<urlset><url><loc>https://x.com/a</loc><lastmod>2024-01-01</lastmod></url><url><loc>https://x.com/b</loc></url></urlset>"
        result = parse_sitemap(xml)
        self.assertEqual(result["lastmod_coverage"], 0.5)

    def test_has_priority(self):
        xml = "<urlset><url><loc>https://x.com/a</loc><priority>0.8</priority></url></urlset>"
        result = parse_sitemap(xml)
        self.assertTrue(result["has_priority"])

    def test_has_changefreq(self):
        xml = "<urlset><url><loc>https://x.com/a</loc><changefreq>weekly</changefreq></url></urlset>"
        result = parse_sitemap(xml)
        self.assertTrue(result["has_changefreq"])

    def test_sample_urls_max_10(self):
        locs = "".join(f"<url><loc>https://x.com/{i}</loc></url>" for i in range(20))
        xml = f"<urlset>{locs}</urlset>"
        result = parse_sitemap(xml)
        self.assertEqual(len(result["sample_urls"]), 10)
        self.assertEqual(result["url_count"], 20)

    def test_empty_urlset(self):
        xml = "<urlset></urlset>"
        result = parse_sitemap(xml)
        self.assertEqual(result["url_count"], 0)


class TestValidateSitemap(unittest.TestCase):

    @patch("seo_sitemap.validate_url", return_value={"valid": False, "error": "bad"})
    def test_invalid_url(self, mock_val):
        result = validate_sitemap("bad")
        self.assertFalse(result["success"])

    @patch("seo_sitemap.validate_url", return_value={"valid": True})
    @patch("seo_sitemap.fetch_page")
    def test_no_sitemap(self, mock_fetch, mock_val):
        mock_fetch.return_value = {"success": False, "error": "404"}
        result = validate_sitemap("https://x.com")
        self.assertTrue(result["success"])
        self.assertFalse(result["sitemap_found"])
        self.assertEqual(result["score"], 0)

    @patch("seo_sitemap.validate_url", return_value={"valid": True})
    @patch("seo_sitemap.fetch_page")
    def test_good_sitemap(self, mock_fetch, mock_val):
        xml = "<urlset><url><loc>https://x.com/a</loc><lastmod>2024-01-01</lastmod></url></urlset>"
        mock_fetch.return_value = {"success": True, "status_code": 200, "html": xml}
        result = validate_sitemap("https://x.com")
        self.assertTrue(result["sitemap_found"])
        self.assertEqual(result["score"], 100)

    @patch("seo_sitemap.validate_url", return_value={"valid": True})
    @patch("seo_sitemap.fetch_page")
    def test_empty_sitemap_issue(self, mock_fetch, mock_val):
        xml = "<urlset></urlset>"
        mock_fetch.return_value = {"success": True, "status_code": 200, "html": xml}
        result = validate_sitemap("https://x.com")
        msgs = [i["message"] for i in result["issues"]]
        self.assertTrue(any("empty" in m.lower() for m in msgs))

    @patch("seo_sitemap.validate_url", return_value={"valid": True})
    @patch("seo_sitemap.fetch_page")
    def test_missing_lastmod_issue(self, mock_fetch, mock_val):
        xml = "<urlset><url><loc>https://x.com/a</loc></url></urlset>"
        mock_fetch.return_value = {"success": True, "status_code": 200, "html": xml}
        result = validate_sitemap("https://x.com")
        msgs = [i["message"] for i in result["issues"]]
        self.assertTrue(any("lastmod" in m.lower() for m in msgs))

    @patch("seo_sitemap.validate_url", return_value={"valid": True})
    @patch("seo_sitemap.fetch_page")
    def test_result_keys(self, mock_fetch, mock_val):
        xml = "<urlset><url><loc>https://x.com</loc></url></urlset>"
        mock_fetch.return_value = {"success": True, "status_code": 200, "html": xml}
        result = validate_sitemap("https://x.com")
        for key in ["success", "url", "sitemap_found", "score", "issues"]:
            self.assertIn(key, result)

    @patch("seo_sitemap.validate_url", return_value={"valid": True})
    @patch("seo_sitemap.fetch_page")
    def test_score_clamped(self, mock_fetch, mock_val):
        xml = "<urlset></urlset>"
        mock_fetch.return_value = {"success": True, "status_code": 200, "html": xml}
        result = validate_sitemap("https://x.com")
        self.assertGreaterEqual(result["score"], 0)
        self.assertLessEqual(result["score"], 100)


if __name__ == "__main__":
    unittest.main()

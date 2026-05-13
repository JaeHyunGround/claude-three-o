"""Tests for seo_cwv.py — Core Web Vitals analysis (INP, not FID)."""

import sys
import os
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from seo_cwv import (
    estimate_performance_from_html, classify_metric,
    analyze_cwv, CWV_THRESHOLDS,
)


class TestCWVThresholds(unittest.TestCase):

    def test_has_lcp(self):
        self.assertIn("LCP", CWV_THRESHOLDS)

    def test_has_inp(self):
        self.assertIn("INP", CWV_THRESHOLDS)

    def test_has_cls(self):
        self.assertIn("CLS", CWV_THRESHOLDS)

    def test_no_fid(self):
        self.assertNotIn("FID", CWV_THRESHOLDS)

    def test_lcp_good_threshold(self):
        self.assertEqual(CWV_THRESHOLDS["LCP"]["good"], 2500)

    def test_inp_good_threshold(self):
        self.assertEqual(CWV_THRESHOLDS["INP"]["good"], 200)

    def test_cls_good_threshold(self):
        self.assertEqual(CWV_THRESHOLDS["CLS"]["good"], 0.1)


class TestClassifyMetric(unittest.TestCase):

    def test_lcp_good(self):
        self.assertEqual(classify_metric("LCP", 2000), "good")

    def test_lcp_needs_improvement(self):
        self.assertEqual(classify_metric("LCP", 3000), "needs_improvement")

    def test_lcp_poor(self):
        self.assertEqual(classify_metric("LCP", 5000), "poor")

    def test_inp_good(self):
        self.assertEqual(classify_metric("INP", 150), "good")

    def test_inp_needs_improvement(self):
        self.assertEqual(classify_metric("INP", 300), "needs_improvement")

    def test_inp_poor(self):
        self.assertEqual(classify_metric("INP", 600), "poor")

    def test_cls_good(self):
        self.assertEqual(classify_metric("CLS", 0.05), "good")

    def test_cls_poor(self):
        self.assertEqual(classify_metric("CLS", 0.3), "poor")

    def test_unknown_metric(self):
        self.assertEqual(classify_metric("FID", 100), "unknown")

    def test_boundary_lcp_good(self):
        self.assertEqual(classify_metric("LCP", 2500), "good")

    def test_boundary_lcp_needs(self):
        self.assertEqual(classify_metric("LCP", 4000), "needs_improvement")

    def test_boundary_inp_good(self):
        self.assertEqual(classify_metric("INP", 200), "good")


class TestEstimatePerformance(unittest.TestCase):

    def _html(self, body="", head=""):
        return f"<html><head>{head}</head><body>{body}</body></html>"

    def test_ttfb(self):
        result = estimate_performance_from_html(self._html(), 0.5)
        self.assertEqual(result["ttfb_ms"], 500)

    def test_external_scripts_count(self):
        html = self._html(head='<script src="a.js"></script><script src="b.js"></script>')
        result = estimate_performance_from_html(html, 0.1)
        self.assertEqual(result["external_scripts"], 2)

    def test_inline_scripts_count(self):
        html = self._html(body='<script>var x=1;</script>')
        result = estimate_performance_from_html(html, 0.1)
        self.assertEqual(result["inline_scripts"], 1)

    def test_images_count(self):
        html = self._html(body='<img src="a.jpg"><img src="b.jpg">')
        result = estimate_performance_from_html(html, 0.1)
        self.assertEqual(result["images"], 2)

    def test_lazy_images(self):
        html = self._html(body='<img src="a.jpg" loading="lazy"><img src="b.jpg">')
        result = estimate_performance_from_html(html, 0.1)
        self.assertEqual(result["lazy_loaded_images"], 1)

    def test_preconnect(self):
        html = self._html(head='<link rel="preconnect" href="https://cdn.com">')
        result = estimate_performance_from_html(html, 0.1)
        self.assertTrue(result["has_preconnect"])

    def test_no_preconnect(self):
        result = estimate_performance_from_html(self._html(), 0.1)
        self.assertFalse(result["has_preconnect"])

    def test_preload(self):
        html = self._html(head='<link rel="preload" href="font.woff2" as="font">')
        result = estimate_performance_from_html(html, 0.1)
        self.assertTrue(result["has_preload"])

    def test_async_defer(self):
        html = self._html(head='<script src="a.js" async></script>')
        result = estimate_performance_from_html(html, 0.1)
        self.assertTrue(result["has_async_defer"])

    def test_no_async_defer(self):
        html = self._html(head='<script src="a.js"></script>')
        result = estimate_performance_from_html(html, 0.1)
        self.assertFalse(result["has_async_defer"])

    def test_estimated_lcp_increases_with_resources(self):
        simple = self._html()
        heavy = self._html(head='<script src="a.js"></script>' * 5,
                           body='<img src="x.jpg">' * 10)
        lcp_simple = estimate_performance_from_html(simple, 0.1)["estimated_lcp_ms"]
        lcp_heavy = estimate_performance_from_html(heavy, 0.1)["estimated_lcp_ms"]
        self.assertGreater(lcp_heavy, lcp_simple)

    def test_cls_risk_low(self):
        result = estimate_performance_from_html(self._html(), 0.1)
        self.assertIn(result["cls_risk"], ["low", "medium", "high"])


class TestAnalyzeCWV(unittest.TestCase):

    @patch("seo_cwv.validate_url", return_value={"valid": False, "error": "bad"})
    def test_invalid_url(self, mock_val):
        result = analyze_cwv("bad")
        self.assertFalse(result["success"])

    @patch("seo_cwv.validate_url", return_value={"valid": True})
    @patch("seo_cwv.fetch_page", return_value={"success": False, "error": "timeout"})
    def test_fetch_failure(self, mock_fetch, mock_val):
        result = analyze_cwv("https://x.com")
        self.assertFalse(result["success"])

    @patch("seo_cwv.validate_url", return_value={"valid": True})
    @patch("seo_cwv.fetch_page")
    def test_fast_page(self, mock_fetch, mock_val):
        html = '<html><head><link rel="preconnect" href="c"></head><body>content</body></html>'
        mock_fetch.return_value = {"success": True, "html": html, "elapsed_seconds": 0.1}
        result = analyze_cwv("https://x.com")
        self.assertTrue(result["success"])
        self.assertGreater(result["score"], 80)

    @patch("seo_cwv.validate_url", return_value={"valid": True})
    @patch("seo_cwv.fetch_page")
    def test_slow_ttfb_issue(self, mock_fetch, mock_val):
        mock_fetch.return_value = {"success": True, "html": "<html></html>", "elapsed_seconds": 2.0}
        result = analyze_cwv("https://x.com")
        msgs = [i["message"] for i in result["issues"]]
        self.assertTrue(any("TTFB" in m for m in msgs))

    @patch("seo_cwv.validate_url", return_value={"valid": True})
    @patch("seo_cwv.fetch_page")
    def test_many_scripts_issue(self, mock_fetch, mock_val):
        scripts = '<script src="s.js"></script>' * 12
        html = f'<html><head>{scripts}</head><body></body></html>'
        mock_fetch.return_value = {"success": True, "html": html, "elapsed_seconds": 0.1}
        result = analyze_cwv("https://x.com")
        msgs = [i["message"] for i in result["issues"]]
        self.assertTrue(any("scripts" in m.lower() for m in msgs))

    @patch("seo_cwv.validate_url", return_value={"valid": True})
    @patch("seo_cwv.fetch_page")
    def test_no_lazy_loading_issue(self, mock_fetch, mock_val):
        html = '<html><body><img src="a.jpg"><img src="b.jpg"></body></html>'
        mock_fetch.return_value = {"success": True, "html": html, "elapsed_seconds": 0.1}
        result = analyze_cwv("https://x.com")
        msgs = [i["message"] for i in result["issues"]]
        self.assertTrue(any("lazy" in m.lower() for m in msgs))

    @patch("seo_cwv.validate_url", return_value={"valid": True})
    @patch("seo_cwv.fetch_page")
    def test_result_keys(self, mock_fetch, mock_val):
        mock_fetch.return_value = {"success": True, "html": "<html></html>", "elapsed_seconds": 0.1}
        result = analyze_cwv("https://x.com")
        for key in ["success", "url", "score", "performance", "cwv_estimates", "issues"]:
            self.assertIn(key, result, f"Missing: {key}")

    @patch("seo_cwv.validate_url", return_value={"valid": True})
    @patch("seo_cwv.fetch_page")
    def test_cwv_estimates_has_inp(self, mock_fetch, mock_val):
        mock_fetch.return_value = {"success": True, "html": "<html></html>", "elapsed_seconds": 0.1}
        result = analyze_cwv("https://x.com")
        self.assertIn("INP", result["cwv_estimates"])
        self.assertIn("requires_field_data", result["cwv_estimates"]["INP"]["status"])

    @patch("seo_cwv.validate_url", return_value={"valid": True})
    @patch("seo_cwv.fetch_page")
    def test_score_clamped(self, mock_fetch, mock_val):
        scripts = '<script src="s.js"></script>' * 20
        html = f'<html><head>{scripts}</head><body><img src="x.jpg"></body></html>'
        mock_fetch.return_value = {"success": True, "html": html, "elapsed_seconds": 3.0}
        result = analyze_cwv("https://x.com")
        self.assertGreaterEqual(result["score"], 0)
        self.assertLessEqual(result["score"], 100)


if __name__ == "__main__":
    unittest.main()

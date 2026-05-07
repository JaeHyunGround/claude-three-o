"""Tests for SEO technical analysis: meta quality, headings, images, links."""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from seo_technical import (
    analyze_meta_tags, evaluate_meta_quality, analyze_heading_structure,
    analyze_images, analyze_links,
)


GOOD_HTML = """
<html lang="ko">
<head>
<title>Three-O SEO 최적화 가이드 - 검색엔진 최적화 전문</title>
<meta name="description" content="Three-O 플랫폼의 SEO 최적화 가이드입니다. 검색엔진 최적화부터 AI 가시성까지 통합적으로 분석하고 개선하는 방법을 알려드립니다. 한국 시장 특화 최적화 전략을 제공합니다.">
<meta property="og:title" content="Three-O SEO Guide">
<meta property="og:description" content="SEO optimization guide">
<meta property="og:image" content="https://example.com/og.png">
<meta property="og:url" content="https://example.com/guide">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Three-O SEO Guide">
<meta name="twitter:description" content="SEO optimization guide">
<link rel="canonical" href="https://example.com/guide">
</head>
<body>
<h1>SEO 최적화 가이드</h1>
<h2>기본 원칙</h2>
<p>Content here</p>
<h2>고급 전략</h2>
<h3>메타 태그</h3>
<img src="a.jpg" alt="SEO diagram">
<img src="b.jpg" alt="GEO flow">
<a href="/about">About</a>
<a href="https://google.com">Google</a>
</body></html>
"""

BAD_HTML = """
<html>
<head>
<title>Hi</title>
</head>
<body>
<h1>First</h1>
<h1>Second</h1>
<h3>Skipped H2</h3>
<img src="a.jpg">
<img src="b.jpg">
<img src="c.jpg">
</body></html>
"""


class TestMetaTags(unittest.TestCase):

    def test_extract_title(self):
        meta = analyze_meta_tags(GOOD_HTML)
        self.assertIn("title", meta)
        self.assertIn("SEO", meta["title"])

    def test_extract_description(self):
        meta = analyze_meta_tags(GOOD_HTML)
        self.assertIn("description", meta)
        self.assertGreater(len(meta["description"]), 80)

    def test_extract_canonical(self):
        meta = analyze_meta_tags(GOOD_HTML)
        self.assertIn("canonical", meta)
        self.assertTrue(meta["canonical"].startswith("https"))

    def test_extract_og_tags(self):
        meta = analyze_meta_tags(GOOD_HTML)
        self.assertIn("og:title", meta)
        self.assertIn("og:image", meta)

    def test_minimal_html(self):
        meta = analyze_meta_tags("<html><head></head><body></body></html>")
        self.assertNotIn("title", meta)
        self.assertNotIn("description", meta)


class TestMetaQuality(unittest.TestCase):

    def test_good_meta_high_score(self):
        meta = analyze_meta_tags(GOOD_HTML)
        quality = evaluate_meta_quality(meta, "https://example.com/guide")
        self.assertGreater(quality["score"], 70)

    def test_missing_meta_low_score(self):
        meta = analyze_meta_tags(BAD_HTML)
        quality = evaluate_meta_quality(meta, "https://example.com")
        self.assertLess(quality["score"], 40)

    def test_title_length_check(self):
        meta = {"title": "Hi"}
        quality = evaluate_meta_quality(meta, "https://example.com")
        issues = [i["message"] for i in quality["issues"]]
        self.assertTrue(any("Title length" in m or "title" in m.lower() for m in issues))

    def test_missing_title_critical(self):
        quality = evaluate_meta_quality({}, "https://example.com")
        severities = [i["severity"] for i in quality["issues"]]
        self.assertIn("critical", severities)

    def test_optimal_title_no_length_issue(self):
        meta = {"title": "Perfect Title Length for SEO Optimization"}
        quality = evaluate_meta_quality(meta, "https://example.com")
        title_len_issues = [i for i in quality["issues"] if "Title length" in i.get("message", "")]
        self.assertEqual(len(title_len_issues), 0)

    def test_duplicate_desc_penalized(self):
        meta = {"title": "Same text", "description": "Same text"}
        quality = evaluate_meta_quality(meta, "https://example.com")
        issues = [i["message"] for i in quality["issues"]]
        self.assertTrue(any("duplicates" in m.lower() for m in issues))

    def test_http_canonical_on_https_warned(self):
        meta = {"canonical": "http://example.com/page"}
        quality = evaluate_meta_quality(meta, "https://example.com/page")
        issues = [i["message"] for i in quality["issues"]]
        self.assertTrue(any("HTTP" in m for m in issues))


class TestHeadingStructure(unittest.TestCase):

    def test_good_hierarchy(self):
        result = analyze_heading_structure(GOOD_HTML)
        self.assertEqual(result["h1_count"], 1)
        self.assertEqual(result["h2_count"], 2)
        self.assertTrue(result["hierarchy_valid"])
        self.assertEqual(len(result["issues"]), 0)

    def test_multiple_h1(self):
        result = analyze_heading_structure(BAD_HTML)
        self.assertEqual(result["h1_count"], 2)
        self.assertFalse(result["hierarchy_valid"])
        issues = [i["message"] for i in result["issues"]]
        self.assertTrue(any("Multiple H1" in m for m in issues))

    def test_h3_without_h2(self):
        result = analyze_heading_structure(BAD_HTML)
        issues = [i["message"] for i in result["issues"]]
        self.assertTrue(any("H3 used without H2" in m for m in issues))

    def test_no_h1(self):
        html = "<html><body><h2>Section</h2><p>text</p></body></html>"
        result = analyze_heading_structure(html)
        self.assertEqual(result["h1_count"], 0)
        issues = [i["message"] for i in result["issues"]]
        self.assertTrue(any("Missing H1" in m for m in issues))


class TestImageAnalysis(unittest.TestCase):

    def test_all_with_alt(self):
        result = analyze_images(GOOD_HTML)
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["with_alt"], 2)
        self.assertEqual(result["coverage"], 100.0)

    def test_missing_alt(self):
        result = analyze_images(BAD_HTML)
        self.assertEqual(result["total"], 3)
        self.assertEqual(result["missing_alt"], 3)
        self.assertEqual(result["coverage"], 0.0)

    def test_no_images(self):
        html = "<html><body><p>No images here</p></body></html>"
        result = analyze_images(html)
        self.assertEqual(result["total"], 0)

    def test_missing_alt_issue(self):
        result = analyze_images(BAD_HTML)
        self.assertGreater(len(result["issues"]), 0)


class TestLinkAnalysis(unittest.TestCase):

    def test_internal_external(self):
        result = analyze_links(GOOD_HTML, "https://example.com/guide")
        self.assertGreater(result["internal"], 0)
        self.assertGreater(result["external"], 0)

    def test_total_count(self):
        result = analyze_links(GOOD_HTML, "https://example.com/guide")
        self.assertEqual(result["total"], result["internal"] + result["external"])

    def test_no_links(self):
        html = "<html><body><p>No links</p></body></html>"
        result = analyze_links(html, "https://example.com")
        self.assertEqual(result["total"], 0)


if __name__ == "__main__":
    unittest.main()

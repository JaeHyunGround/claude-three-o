"""Integration smoke tests — exercises multiple modules together with only HTTP mocked."""

import sys
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

SAMPLE_HTML = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="utf-8">
    <title>스카이벤처스 - 디지털 마케팅 에이전시</title>
    <meta name="description" content="SEO, GEO, AAO 통합 최적화 서비스를 제공합니다.">
    <meta name="robots" content="index, follow">
    <link rel="canonical" href="https://www.example.com/">
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": "스카이벤처스",
        "url": "https://www.example.com",
        "telephone": "+82-2-1234-5678"
    }
    </script>
</head>
<body>
    <h1>스카이벤처스 - 디지털 마케팅 전문 에이전시</h1>
    <h2>서비스 소개</h2>
    <p>스카이벤처스는 SEO, GEO, AAO 통합 최적화 서비스를 제공하는 디지털 마케팅 에이전시입니다.
    10년 이상의 경험을 바탕으로 고객의 온라인 가시성을 극대화합니다.</p>
    <h2>주요 서비스</h2>
    <ul>
        <li>검색엔진 최적화 (SEO)</li>
        <li>AI 엔진 최적화 (GEO)</li>
        <li>에이전트 최적화 (AAO)</li>
    </ul>
    <h2>연락처</h2>
    <p>이메일: contact@example.com | 전화: 02-1234-5678</p>
    <a href="https://www.example.com/about">회사 소개</a>
    <a href="https://www.example.com/services">서비스</a>
    <a href="https://blog.naver.com/example">네이버 블로그</a>
    <img src="/images/logo.png" alt="스카이벤처스 로고">
    <img src="/images/team.jpg" alt="팀 사진">
</body>
</html>"""

ROBOTS_TXT = """User-agent: *
Allow: /
Sitemap: https://www.example.com/sitemap.xml

User-agent: Googlebot
Allow: /

User-agent: GPTBot
Allow: /
"""

SITEMAP_XML = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url><loc>https://www.example.com/</loc><lastmod>2026-05-01</lastmod></url>
    <url><loc>https://www.example.com/about</loc><lastmod>2026-04-15</lastmod></url>
    <url><loc>https://www.example.com/services</loc><lastmod>2026-04-20</lastmod></url>
</urlset>"""


def _mock_fetch(url, user_agent="default", timeout=15):
    """Simulate fetch_page for different URL patterns."""
    if "robots.txt" in url:
        return {"success": True, "html": ROBOTS_TXT, "status_code": 200,
                "content_type": "text/plain", "content_length": len(ROBOTS_TXT),
                "elapsed_seconds": 0.1, "headers": {}, "url": url, "redirects": []}
    if "sitemap" in url:
        return {"success": True, "html": SITEMAP_XML, "status_code": 200,
                "content_type": "application/xml", "content_length": len(SITEMAP_XML),
                "elapsed_seconds": 0.1, "headers": {}, "url": url, "redirects": []}
    if "indexnow" in url or "bing.com" in url or "yandex.com" in url:
        return {"success": False, "error": "404"}
    return {"success": True, "html": SAMPLE_HTML, "status_code": 200,
            "content_type": "text/html", "content_length": len(SAMPLE_HTML),
            "elapsed_seconds": 0.5, "headers": {"content-type": "text/html"},
            "url": url, "redirects": []}


VALID_URL = {"valid": True, "url": "https://www.example.com", "hostname": "www.example.com", "scheme": "https"}


class TestFetchToKeywordPipeline(unittest.TestCase):
    """fetch_page → seo_keywords analysis without real HTTP."""

    @patch("validate_url.validate_url", return_value=VALID_URL)
    @patch("fetch_page.httpx.Client")
    def test_fetch_then_keyword_check(self, mock_client_cls, mock_val):
        mock_response = MagicMock()
        mock_response.url = "https://www.example.com"
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/html"}
        mock_response.text = SAMPLE_HTML
        mock_response.history = []
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value = mock_client

        from fetch_page import fetch_page
        result = fetch_page("https://www.example.com")
        self.assertTrue(result["success"])

        from seo_keywords import check_keyword_in_content
        kw_result = check_keyword_in_content(result["html"], "스카이벤처스")
        self.assertTrue(kw_result["in_title"])
        self.assertTrue(kw_result["in_h1"])
        self.assertGreater(kw_result["occurrences"], 0)


class TestSeoAnalysisPipeline(unittest.TestCase):
    """SEO page analysis → score calculation → report generation."""

    def test_page_analysis_to_report(self):
        from seo_page import analyze_single_page
        from score_calculator import compute_three_o_score
        from report_generator import generate_markdown_report, generate_json_report

        with patch("seo_page.validate_url", return_value=VALID_URL), \
             patch("seo_page.fetch_page", side_effect=_mock_fetch):
            page_result = analyze_single_page("https://www.example.com")

        self.assertTrue(page_result["success"])
        self.assertIn("score", page_result)
        self.assertGreater(page_result["score"], 0)

        seo_score = page_result["score"]
        three_o = compute_three_o_score(seo=seo_score, geo=45.0, aao=50.0, industry="agency")
        self.assertIn("three_o_score", three_o)
        self.assertGreater(three_o["three_o_score"], 0)
        self.assertLessEqual(three_o["three_o_score"], 100)
        self.assertIn("grade", three_o)

        report_data = {
            "brand": "example",
            "three_o_score": three_o["three_o_score"],
            "grade": three_o["grade"],
            "pillars": three_o["pillars"],
            "weights_applied": three_o["weights_applied"],
            "findings": [{"severity": "high", "description": "Missing H2 keywords"}],
            "actions": [{"description": "Add target keywords to H2 tags", "impact": "medium"}],
        }

        md = generate_markdown_report(report_data)
        self.assertIn("Three-O Audit Report", md)
        self.assertIn("example", md)
        self.assertIn("SEO", md)

        json_str = generate_json_report(report_data)
        import json
        parsed = json.loads(json_str)
        self.assertEqual(parsed["scores"]["three_o_score"], three_o["three_o_score"])


class TestSchemaDetectionPipeline(unittest.TestCase):
    """HTML → schema extraction → validation."""

    def test_extract_and_validate_schema(self):
        from seo_schema import extract_jsonld, validate_schema

        schemas = extract_jsonld(SAMPLE_HTML)
        self.assertGreater(len(schemas), 0)
        self.assertEqual(schemas[0]["@type"], "Organization")

        validation = validate_schema(schemas[0])
        self.assertIn("valid", validation)
        self.assertIn("type", validation)
        self.assertEqual(validation["type"], "Organization")


class TestIndexingPipeline(unittest.TestCase):
    """Indexing analysis with robots.txt + sitemap through the real pipeline."""

    @patch("seo_indexing.validate_url", return_value=VALID_URL)
    @patch("seo_indexing.fetch_page", side_effect=_mock_fetch)
    def test_full_indexing_analysis(self, mock_fetch, mock_val):
        from seo_indexing import analyze_indexing

        result = analyze_indexing("https://www.example.com")
        self.assertTrue(result["success"])
        self.assertIn("score", result)
        self.assertIn("robots_txt", result)
        self.assertIn("sitemap", result)
        self.assertIn("meta_robots", result)


class TestKeywordVariantsPipeline(unittest.TestCase):
    """Korean keyword variant generation → content check."""

    def test_variants_checked_in_html(self):
        from seo_keywords import generate_keyword_variants, check_keyword_in_content

        variants = generate_keyword_variants("마케팅")
        self.assertIn("마케팅", variants)
        self.assertIn("마케팅 추천", variants)

        found = []
        for variant in variants:
            result = check_keyword_in_content(SAMPLE_HTML, variant)
            if result["occurrences"] > 0:
                found.append(variant)

        self.assertIn("마케팅", found)


class TestScoreCalculationEdgeCases(unittest.TestCase):
    """Score calculator with real multi-pillar scenarios."""

    def test_balanced_high_scores(self):
        from score_calculator import compute_three_o_score
        result = compute_three_o_score(seo=85, geo=80, aao=75)
        self.assertGreater(result["three_o_score"], 70)
        self.assertGreaterEqual(result["balance_penalty"], 0.99)

    def test_imbalanced_scores_penalized(self):
        from score_calculator import compute_three_o_score
        result = compute_three_o_score(seo=90, geo=20, aao=85)
        self.assertLess(result["balance_penalty"], 1.0)

    def test_industry_adjustment_affects_score(self):
        from score_calculator import compute_three_o_score
        base = compute_three_o_score(seo=70, geo=70, aao=70)
        clinic = compute_three_o_score(seo=70, geo=70, aao=70, industry="clinic")
        self.assertNotEqual(base["weights_applied"], clinic["weights_applied"])

    def test_geo_score_partial_dimensions(self):
        from score_calculator import compute_geo_score
        full = compute_geo_score(mf=60, cq=70, vr=50, ep=40, ta=80)
        partial = compute_geo_score(mf=60, cq=70, vr=0, ep=0, ta=80)
        self.assertTrue(full["geo_score"] > 0)
        self.assertTrue(partial["partial"])
        self.assertLess(partial["confidence"], full["confidence"])

    def test_platform_geo_scores(self):
        from score_calculator import compute_platform_geo_scores
        data = {
            "chatgpt": {"mf": 60, "cq": 70, "vr": 50, "ep": 40, "ta": 80},
            "perplexity": {"mf": 50, "cq": 60, "vr": 40, "ep": 30, "ta": 70},
            "gemini": {"mf": 40, "cq": 50, "vr": 30, "ep": 20, "ta": 60},
            "claude": {"mf": 55, "cq": 65, "vr": 45, "ep": 35, "ta": 75},
        }
        result = compute_platform_geo_scores(data)
        self.assertIn("overall_geo_score", result)
        self.assertIn("best_platform", result)
        self.assertIn("worst_platform", result)
        self.assertEqual(result["best_platform"], "chatgpt")
        self.assertEqual(result["worst_platform"], "gemini")


class TestReportSaveRoundtrip(unittest.TestCase):
    """Generate report → save → read back."""

    def test_markdown_save_and_read(self):
        from report_generator import generate_markdown_report, save_report

        data = {
            "brand": "test-brand",
            "three_o_score": 72.5,
            "grade": "B+",
            "pillars": {"seo": 75, "geo": 70, "aao": 72},
            "weights_applied": {"seo": 0.35, "geo": 0.35, "aao": 0.30},
            "findings": [],
            "actions": [],
        }
        md = generate_markdown_report(data)

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("report_generator.get_reports_dir", return_value=__import__("pathlib").Path(tmpdir)):
                path = save_report(md, "test-brand", "full", "md")
                self.assertTrue(path.exists())
                content = path.read_text()
                self.assertIn("72.5", content)
                self.assertIn("test-brand", content)

    def test_json_save_roundtrip(self):
        import json
        from report_generator import generate_json_report, save_report

        data = {
            "brand": "roundtrip",
            "three_o_score": 65.0,
            "grade": "B",
            "pillars": {"seo": 60, "geo": 70, "aao": 65},
            "weights_applied": {"seo": 0.35, "geo": 0.35, "aao": 0.30},
        }
        json_str = generate_json_report(data)

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("report_generator.get_reports_dir", return_value=__import__("pathlib").Path(tmpdir)):
                path = save_report(json_str, "roundtrip", "full", "json")
                loaded = json.loads(path.read_text())
                self.assertEqual(loaded["scores"]["three_o_score"], 65.0)


class TestDbManagerIntegration(unittest.TestCase):
    """Database operations with real SQLite (in temp dir)."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._db_path = __import__("pathlib").Path(self._tmpdir.name) / "test.db"
        self._patcher = patch("db_manager.DB_PATH", self._db_path)
        self._patcher.start()

    def tearDown(self):
        self._patcher.stop()
        self._tmpdir.cleanup()

    def test_init_save_retrieve_baseline(self):
        from db_manager import init_db, save_baseline, get_latest_baseline

        init_db()
        save_baseline("testbrand", "seo", 75.5, {"details": "test data"})
        result = get_latest_baseline("testbrand", "seo")

        self.assertIsNotNone(result)
        self.assertEqual(result["brand"], "testbrand")
        self.assertEqual(result["score"], 75.5)

    def test_baseline_history_ordering(self):
        from db_manager import init_db, save_baseline, get_baseline_history

        init_db()
        save_baseline("brand", "geo", 60.0, {"v": 1})
        save_baseline("brand", "geo", 70.0, {"v": 2})
        save_baseline("brand", "geo", 80.0, {"v": 3})

        history = get_baseline_history("brand", "geo")
        self.assertEqual(len(history), 3)
        self.assertEqual(history[0]["score"], 80.0)

    def test_multi_pillar_baselines(self):
        from db_manager import init_db, save_baseline, get_all_pillar_baselines

        init_db()
        save_baseline("brand", "seo", 70.0, {})
        save_baseline("brand", "geo", 65.0, {})
        save_baseline("brand", "aao", 60.0, {})

        result = get_all_pillar_baselines("brand")
        self.assertEqual(len(result["seo"]), 1)
        self.assertEqual(len(result["geo"]), 1)
        self.assertEqual(len(result["aao"]), 1)

    def test_list_brands(self):
        from db_manager import init_db, save_baseline, list_brands

        init_db()
        save_baseline("alpha", "seo", 50.0, {})
        save_baseline("beta", "geo", 60.0, {})

        brands = list_brands()
        self.assertIn("alpha", brands)
        self.assertIn("beta", brands)


if __name__ == "__main__":
    unittest.main()

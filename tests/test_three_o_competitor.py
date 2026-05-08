"""Tests for cross-pillar competitor benchmarking."""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from three_o_competitor import (
    score_seo_dimensions, score_geo_dimensions, score_aao_dimensions,
    analyze_competitor, compute_dimension_gaps, compute_positioning,
    generate_action_plan, compare_competitors, format_benchmark_report,
    SEO_WEIGHTS, GEO_WEIGHTS, AAO_WEIGHTS, GAP_RECOMMENDATIONS,
)


RICH_HTML = """
<html lang="ko">
<head>
<title>Three-O SEO 최적화 가이드 - 검색엔진 최적화 전문 플랫폼</title>
<meta name="description" content="Three-O 플랫폼의 SEO 최적화 가이드입니다. 검색엔진 최적화부터 AI 가시성까지 통합적으로 분석합니다.">
<meta property="og:title" content="Three-O SEO Guide">
<meta property="og:description" content="SEO optimization guide">
<meta property="og:image" content="https://example.com/og.png">
<link rel="canonical" href="https://example.com/guide">
<script type="application/ld+json">{"@type":"Organization","name":"Three-O","aggregateRating":{"ratingValue":"4.5","reviewCount":"120"}}</script>
</head>
<body>
<main>
<h1>SEO 최적화 가이드</h1>
<h2>기본 원칙</h2>
<p>검색엔진 최적화(SEO)란 웹사이트의 기술적 구조와 콘텐츠를 개선하여 검색엔진 결과 페이지에서 높은 순위를 확보하는 디지털 마케팅 전략입니다.</p>
<p>2024년 기준 국내 검색엔진 시장에서 네이버는 56.2%, 구글은 34.8%의 점유율을 기록했습니다. SEO 전략은 두 엔진 모두를 고려해야 합니다.</p>
<h2>고급 전략</h2>
<h3>메타 태그 최적화</h3>
<p>타이틀 태그는 30-60자, 메타 디스크립션은 80-160자가 최적입니다. 핵심 키워드를 앞부분에 배치하세요.</p>
<img src="a.jpg" alt="SEO diagram">
<img src="b.jpg" alt="GEO flow chart">
<ul><li>기술적 SEO 점검</li><li>콘텐츠 품질 분석</li></ul>
<p>Published by Dr. Kim, SEO Expert. Source: Google Search Central 2024 연구 보고서</p>
<p>전화: 02-1234-5678 | 서울특별시 강남구 테헤란로 123</p>
<p>영업시간: 09:00 ~ 18:00</p>
<a href="/book">예약하기</a>
<p>ISO 9001 인증 | 2024 대한민국 디지털 혁신상 수상</p>
</main>
</body></html>
"""

POOR_HTML = """
<html>
<head><title>Hi</title></head>
<body>
<h1>Welcome</h1>
<h1>Second H1</h1>
<p>We provide great services.</p>
<img src="x.jpg">
</body></html>
"""

MEDIUM_HTML = """
<html lang="ko">
<head>
<title>중간 수준 페이지 - 테스트 사이트</title>
<meta name="description" content="이것은 중간 수준의 SEO를 가진 테스트 페이지입니다. 일부 최적화가 적용되었습니다.">
<link rel="canonical" href="https://example.com/medium">
</head>
<body>
<h1>중간 수준 페이지</h1>
<h2>섹션 1</h2>
<p>이 페이지는 기본적인 SEO 요소를 갖추고 있습니다. 타이틀과 디스크립션이 있으나 스키마가 없습니다.</p>
<p>전화번호: 02-9876-5432</p>
<img src="a.jpg" alt="test image">
<img src="b.jpg">
</body></html>
"""


class TestSEODimensions(unittest.TestCase):

    def test_rich_page_high_score(self):
        result = score_seo_dimensions(RICH_HTML, "https://example.com/guide", 0.5)
        self.assertGreater(result["score"], 60)

    def test_poor_page_low_score(self):
        result = score_seo_dimensions(POOR_HTML, "https://example.com", 3.5)
        self.assertLess(result["score"], 50)

    def test_has_all_dimensions(self):
        result = score_seo_dimensions(RICH_HTML, "https://example.com", 1.0)
        for dim in SEO_WEIGHTS:
            self.assertIn(dim, result["dimensions"])

    def test_fast_page_high_performance(self):
        result = score_seo_dimensions(RICH_HTML, "https://example.com", 0.3)
        self.assertGreater(result["dimensions"]["performance"], 90)

    def test_slow_page_low_performance(self):
        result = score_seo_dimensions(POOR_HTML, "https://example.com", 5.0)
        self.assertLess(result["dimensions"]["performance"], 40)

    def test_schema_present_scored(self):
        result = score_seo_dimensions(RICH_HTML, "https://example.com", 1.0)
        self.assertGreater(result["dimensions"]["schema"], 60)

    def test_no_schema_low(self):
        result = score_seo_dimensions(POOR_HTML, "https://example.com", 1.0)
        self.assertLess(result["dimensions"]["schema"], 30)

    def test_good_images_coverage(self):
        result = score_seo_dimensions(RICH_HTML, "https://example.com", 1.0)
        self.assertEqual(result["dimensions"]["images"], 100.0)

    def test_scores_bounded(self):
        result = score_seo_dimensions(RICH_HTML, "https://example.com", 1.0)
        for dim, val in result["dimensions"].items():
            self.assertGreaterEqual(val, 0.0)
            self.assertLessEqual(val, 100.0)


class TestGEODimensions(unittest.TestCase):

    def test_rich_content_high_score(self):
        result = score_geo_dimensions(RICH_HTML)
        self.assertGreater(result["score"], 40)

    def test_poor_content_low_score(self):
        result = score_geo_dimensions(POOR_HTML)
        self.assertLess(result["score"], 40)

    def test_has_all_dimensions(self):
        result = score_geo_dimensions(RICH_HTML)
        for dim in GEO_WEIGHTS:
            self.assertIn(dim, result["dimensions"])

    def test_empty_page_zero(self):
        result = score_geo_dimensions("<html><body></body></html>")
        self.assertEqual(result["score"], 0.0)

    def test_factual_content_scores_high(self):
        result = score_geo_dimensions(RICH_HTML)
        self.assertGreater(result["dimensions"]["factual_density"], 30)

    def test_authority_signals_detected(self):
        result = score_geo_dimensions(RICH_HTML)
        self.assertGreater(result["dimensions"]["authority_signals"], 50)


class TestAAODimensions(unittest.TestCase):

    def test_rich_page_has_scores(self):
        result = score_aao_dimensions(RICH_HTML, 1.0)
        self.assertGreater(result["score"], 20)

    def test_has_all_dimensions(self):
        result = score_aao_dimensions(RICH_HTML, 1.0)
        for dim in AAO_WEIGHTS:
            self.assertIn(dim, result["dimensions"])

    def test_schema_present(self):
        result = score_aao_dimensions(RICH_HTML, 1.0)
        self.assertGreater(result["dimensions"]["structured_data"], 20)

    def test_poor_page_low(self):
        result = score_aao_dimensions(POOR_HTML, 1.0)
        self.assertLess(result["score"], 30)

    def test_scores_bounded(self):
        result = score_aao_dimensions(RICH_HTML, 1.0)
        for dim, val in result["dimensions"].items():
            self.assertGreaterEqual(val, 0.0)
            self.assertLessEqual(val, 100.0)


class TestComputeDimensionGaps(unittest.TestCase):

    def _make_result(self, seo_dims, geo_dims, aao_dims):
        return {
            "seo": {"score": 50, "dimensions": seo_dims},
            "geo": {"score": 50, "dimensions": geo_dims},
            "aao": {"score": 50, "dimensions": aao_dims},
        }

    def test_detects_gap(self):
        target = self._make_result(
            {"meta_quality": 30}, {"passage_clarity": 50}, {"structured_data": 40}
        )
        competitor = self._make_result(
            {"meta_quality": 70}, {"passage_clarity": 50}, {"structured_data": 40}
        )
        gaps = compute_dimension_gaps(target, competitor)
        gap_dims = [g["dimension"] for g in gaps]
        self.assertIn("meta_quality", gap_dims)

    def test_detects_advantage(self):
        target = self._make_result(
            {"meta_quality": 80}, {"passage_clarity": 50}, {"structured_data": 40}
        )
        competitor = self._make_result(
            {"meta_quality": 30}, {"passage_clarity": 50}, {"structured_data": 40}
        )
        gaps = compute_dimension_gaps(target, competitor)
        advantages = [g for g in gaps if g["direction"] == "advantage"]
        self.assertGreater(len(advantages), 0)

    def test_no_gap_under_threshold(self):
        target = self._make_result(
            {"meta_quality": 50}, {"passage_clarity": 50}, {"structured_data": 50}
        )
        competitor = self._make_result(
            {"meta_quality": 52}, {"passage_clarity": 50}, {"structured_data": 50}
        )
        gaps = compute_dimension_gaps(target, competitor)
        self.assertEqual(len(gaps), 0)

    def test_gap_has_recommendation(self):
        target = self._make_result(
            {"meta_quality": 30}, {"passage_clarity": 50}, {"structured_data": 40}
        )
        competitor = self._make_result(
            {"meta_quality": 80}, {"passage_clarity": 50}, {"structured_data": 40}
        )
        gaps = compute_dimension_gaps(target, competitor)
        for gap in gaps:
            if gap["dimension"] == "meta_quality":
                self.assertIn("메타", gap["recommendation"])

    def test_sorted_by_delta(self):
        target = self._make_result(
            {"meta_quality": 30, "headings": 40},
            {"passage_clarity": 50},
            {"structured_data": 40},
        )
        competitor = self._make_result(
            {"meta_quality": 80, "headings": 90},
            {"passage_clarity": 50},
            {"structured_data": 40},
        )
        gaps = compute_dimension_gaps(target, competitor)
        deltas = [g["delta"] for g in gaps]
        self.assertEqual(deltas, sorted(deltas))


class TestComputePositioning(unittest.TestCase):

    def test_positioning_structure(self):
        results = [
            {
                "url": "https://a.com",
                "seo": {"dimensions": {"meta_quality": 80}},
                "geo": {"dimensions": {"passage_clarity": 60}},
                "aao": {"dimensions": {"structured_data": 70}},
            },
            {
                "url": "https://b.com",
                "seo": {"dimensions": {"meta_quality": 50}},
                "geo": {"dimensions": {"passage_clarity": 40}},
                "aao": {"dimensions": {"structured_data": 30}},
            },
        ]
        pos = compute_positioning(results)
        self.assertIn("per_site", pos)
        self.assertIn("market_average", pos)
        self.assertEqual(pos["market_average"]["meta_quality"], 65.0)

    def test_empty_results(self):
        pos = compute_positioning([])
        self.assertEqual(pos, {})


class TestGenerateActionPlan(unittest.TestCase):

    def test_critical_gap_is_p0(self):
        target = {"url": "https://example.com"}
        gaps = [
            {
                "dimension": "meta_quality", "pillar": "SEO",
                "target_score": 20, "competitor_score": 80,
                "delta": -60, "direction": "gap",
                "recommendation": "Fix meta tags",
            }
        ]
        actions = generate_action_plan(target, gaps)
        self.assertEqual(actions[0]["priority"], "P0")

    def test_moderate_gap_is_p1(self):
        target = {"url": "https://example.com"}
        gaps = [
            {
                "dimension": "headings", "pillar": "SEO",
                "target_score": 50, "competitor_score": 60,
                "delta": -10, "direction": "gap",
                "recommendation": "Fix headings",
            }
        ]
        actions = generate_action_plan(target, gaps)
        self.assertEqual(actions[0]["priority"], "P1")

    def test_advantage_is_maintain(self):
        target = {"url": "https://example.com"}
        gaps = [
            {
                "dimension": "schema", "pillar": "SEO",
                "target_score": 90, "competitor_score": 40,
                "delta": 50, "direction": "advantage",
                "recommendation": "",
            }
        ]
        actions = generate_action_plan(target, gaps)
        maintain_actions = [a for a in actions if a["priority"] == "maintain"]
        self.assertGreater(len(maintain_actions), 0)

    def test_sorted_by_priority(self):
        target = {"url": "https://example.com"}
        gaps = [
            {"dimension": "a", "pillar": "SEO", "target_score": 50, "competitor_score": 60,
             "delta": -10, "direction": "gap", "recommendation": "fix a"},
            {"dimension": "b", "pillar": "GEO", "target_score": 10, "competitor_score": 80,
             "delta": -70, "direction": "gap", "recommendation": "fix b"},
        ]
        actions = generate_action_plan(target, gaps)
        priorities = [a["priority"] for a in actions]
        self.assertEqual(priorities[0], "P0")

    def test_empty_gaps(self):
        actions = generate_action_plan({"url": "x"}, [])
        self.assertEqual(len(actions), 0)


class TestGAPRecommendations(unittest.TestCase):

    def test_all_dimensions_covered(self):
        all_dims = set(SEO_WEIGHTS.keys()) | set(GEO_WEIGHTS.keys()) | set(AAO_WEIGHTS.keys())
        for dim in all_dims:
            self.assertIn(dim, GAP_RECOMMENDATIONS)

    def test_recommendations_not_empty(self):
        for dim, rec in GAP_RECOMMENDATIONS.items():
            self.assertGreater(len(rec), 10)


class TestFormatReport(unittest.TestCase):

    def test_format_success(self):
        result = {
            "success": True,
            "target": "https://a.com",
            "competitors_analyzed": 2,
            "rankings": [
                {"rank": 1, "url": "https://a.com", "industry": "general",
                 "three_o_score": 70, "seo": 75, "geo": 65, "aao": 60,
                 "strengths": ["meta_quality"], "weaknesses": ["freshness"]},
                {"rank": 2, "url": "https://b.com", "industry": "saas",
                 "three_o_score": 55, "seo": 50, "geo": 55, "aao": 50,
                 "strengths": [], "weaknesses": ["schema"]},
            ],
            "leader": "https://a.com",
            "gaps": [
                {"pillar": "GEO", "dimension": "citation_pattern",
                 "target_score": 30, "competitor_score": 60, "delta": -30},
            ],
            "action_plan": [
                {"priority": "P0", "pillar": "GEO", "dimension": "citation_pattern",
                 "gap": 30, "action": "Add definition patterns"},
            ],
        }
        report = format_benchmark_report(result)
        self.assertIn("Competitor Benchmark", report)
        self.assertIn("a.com", report)
        self.assertIn("Action Plan", report)

    def test_format_error(self):
        report = format_benchmark_report({"success": False, "error": "test"})
        self.assertIn("Error", report)


class TestWeightsSumToOne(unittest.TestCase):

    def test_seo_weights(self):
        self.assertAlmostEqual(sum(SEO_WEIGHTS.values()), 1.0, places=2)

    def test_geo_weights(self):
        self.assertAlmostEqual(sum(GEO_WEIGHTS.values()), 1.0, places=2)

    def test_aao_weights(self):
        self.assertAlmostEqual(sum(AAO_WEIGHTS.values()), 1.0, places=2)


if __name__ == "__main__":
    unittest.main()

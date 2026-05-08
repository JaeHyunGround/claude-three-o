"""Tests for content rewrite suggestion engine."""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from content_rewrite import (
    analyze_weakness, suggest_strategies, compute_passage_score,
    estimate_improvement, platform_tips, analyze_rewrite,
    format_rewrite_report, _find_vague_words, _generate_priority_actions,
    REWRITE_STRATEGIES,
)


VAGUE_PASSAGE = "저희는 최고의 다양한 서비스를 제공합니다. 고객님의 만족을 위해 최선을 다하겠습니다."

GOOD_PASSAGE = (
    "Sky Ventures는 2024년 기준 한국 시장에서 SEO+GEO+AAO 통합 최적화를 제공하는 "
    "디지털 마케팅 컨설팅 기업입니다. 자체 개발한 Three-O 점수 시스템은 35%의 SEO, "
    "35%의 GEO, 30%의 AAO 가중치를 적용하여 0-100점 범위의 통합 점수를 산출합니다."
)

PRONOUN_PASSAGE = "이것은 그런 방식으로 처리됩니다. 그것이 위의 내용과 관련이 있습니다."

FILLER_PASSAGE = "저희는 최고의 서비스를 제공합니다. 고객님의 만족을 위해 항상 노력하고 있습니다."

SHORT_PASSAGE = "서비스 좋습니다."

LONG_PASSAGE = "가" * 600

DATA_RICH = (
    "2024년 3분기 기준 국내 검색엔진 시장 점유율은 네이버 56.2%, 구글 34.8%, "
    "다음 5.1%를 기록했다. 전년 동기 대비 구글은 3.2%p 상승, 네이버는 2.1%p 하락했다."
)

COMPARISON_PASSAGE = (
    "A 제품은 B 제품에 비해 배터리 수명이 30% 더 길며, 가격은 15% 낮습니다. "
    "반면 B 제품은 디스플레이 해상도에서 우위를 보입니다."
)

DEFINITION_PASSAGE = (
    "검색엔진 최적화(SEO)란 웹사이트의 기술적 구조와 콘텐츠를 개선하여 "
    "검색엔진 결과 페이지에서 높은 순위를 확보하는 디지털 마케팅 전략입니다."
)

PAGE_HTML = """
<html lang="ko">
<head><title>Test Page</title></head>
<body>
<p>저희는 최고의 다양한 서비스를 제공합니다. 고객님의 만족을 위해 최선을 다하겠습니다. 언제든지 연락 주세요.</p>
<p>이것은 그런 방식으로 동작합니다. 그것을 통해 위의 결과를 얻을 수 있으며 매우 혁신적인 접근입니다.</p>
<p>Sky Ventures는 2024년 기준 한국 시장에서 SEO와 GEO 통합 최적화를 제공하는 디지털 마케팅 컨설팅 기업입니다. 자체 개발한 Three-O 점수는 0-100점 범위입니다.</p>
<p>검색엔진 최적화(SEO)란 웹사이트의 기술적 구조와 콘텐츠를 개선하여 검색엔진 결과 페이지에서 높은 순위를 확보하는 디지털 마케팅 전략입니다.</p>
<p>A 제품은 B 제품에 비해 배터리 수명이 30% 더 길며, 가격은 15% 낮습니다. 반면 B 제품은 디스플레이 해상도에서 우위를 보입니다.</p>
</body></html>
"""

EMPTY_HTML = "<html><head><title>Empty</title></head><body></body></html>"


class TestAnalyzeWeakness(unittest.TestCase):

    def test_vague_passage_has_weaknesses(self):
        weaknesses = analyze_weakness(VAGUE_PASSAGE)
        self.assertGreater(len(weaknesses), 0)

    def test_vague_detects_language(self):
        weaknesses = analyze_weakness(VAGUE_PASSAGE)
        types = [w["type"] for w in weaknesses]
        self.assertIn("vague_language", types)

    def test_filler_detected(self):
        weaknesses = analyze_weakness(FILLER_PASSAGE)
        types = [w["type"] for w in weaknesses]
        self.assertIn("filler_content", types)

    def test_pronoun_passage_low_containment(self):
        weaknesses = analyze_weakness(PRONOUN_PASSAGE)
        types = [w["type"] for w in weaknesses]
        self.assertIn("low_self_containment", types)

    def test_weak_opener_detected(self):
        weaknesses = analyze_weakness(PRONOUN_PASSAGE)
        types = [w["type"] for w in weaknesses]
        self.assertIn("weak_opener", types)

    def test_short_passage(self):
        weaknesses = analyze_weakness(SHORT_PASSAGE)
        types = [w["type"] for w in weaknesses]
        self.assertIn("too_short", types)

    def test_long_passage(self):
        weaknesses = analyze_weakness(LONG_PASSAGE)
        types = [w["type"] for w in weaknesses]
        self.assertIn("too_long", types)

    def test_good_passage_fewer_weaknesses(self):
        good_weaknesses = analyze_weakness(GOOD_PASSAGE)
        vague_weaknesses = analyze_weakness(VAGUE_PASSAGE)
        self.assertLess(len(good_weaknesses), len(vague_weaknesses))

    def test_data_rich_no_factual_weakness(self):
        weaknesses = analyze_weakness(DATA_RICH)
        types = [w["type"] for w in weaknesses]
        self.assertNotIn("low_factual_density", types)

    def test_weakness_has_severity(self):
        weaknesses = analyze_weakness(VAGUE_PASSAGE)
        for w in weaknesses:
            self.assertIn(w["severity"], ["high", "medium", "low"])


class TestFindVagueWords(unittest.TestCase):

    def test_korean_vague(self):
        found = _find_vague_words("최고의 다양한 서비스를 제공합니다")
        self.assertIn("최고의", found)
        self.assertIn("다양한", found)

    def test_english_vague(self):
        found = _find_vague_words("Our amazing world-class innovative solution")
        self.assertIn("amazing", found)
        self.assertIn("innovative", found)

    def test_no_vague(self):
        found = _find_vague_words("2024년 매출 150억원을 기록했다")
        self.assertEqual(len(found), 0)


class TestSuggestStrategies(unittest.TestCase):

    def test_no_pattern_suggests_definition(self):
        weaknesses = [{"type": "no_citation_pattern", "severity": "high", "detail": ""}]
        strategies = suggest_strategies(weaknesses)
        keys = [s["key"] for s in strategies]
        self.assertIn("add_definition", keys)

    def test_low_containment_suggests_fix(self):
        weaknesses = [{"type": "low_self_containment", "severity": "high", "detail": ""}]
        strategies = suggest_strategies(weaknesses)
        keys = [s["key"] for s in strategies]
        self.assertIn("improve_self_containment", keys)

    def test_vague_suggests_data(self):
        weaknesses = [{"type": "vague_language", "severity": "medium", "detail": ""}]
        strategies = suggest_strategies(weaknesses)
        keys = [s["key"] for s in strategies]
        self.assertIn("add_data", keys)

    def test_strategies_sorted_by_impact(self):
        weaknesses = [
            {"type": "no_citation_pattern", "severity": "high", "detail": ""},
            {"type": "vague_language", "severity": "medium", "detail": ""},
        ]
        strategies = suggest_strategies(weaknesses)
        impacts = [s["impact"] for s in strategies]
        high_indices = [i for i, imp in enumerate(impacts) if imp == "high"]
        medium_indices = [i for i, imp in enumerate(impacts) if imp == "medium"]
        if high_indices and medium_indices:
            self.assertLess(max(high_indices), max(medium_indices))

    def test_strategy_has_templates(self):
        weaknesses = [{"type": "no_citation_pattern", "severity": "high", "detail": ""}]
        strategies = suggest_strategies(weaknesses)
        for s in strategies:
            self.assertIn("template_ko", s)
            self.assertIn("template_en", s)

    def test_empty_weaknesses(self):
        strategies = suggest_strategies([])
        self.assertEqual(len(strategies), 0)


class TestComputePassageScore(unittest.TestCase):

    def test_good_passage_high_score(self):
        score = compute_passage_score(GOOD_PASSAGE)
        self.assertGreater(score["overall"], 50)

    def test_vague_passage_low_score(self):
        score = compute_passage_score(VAGUE_PASSAGE)
        self.assertLess(score["overall"], 65)

    def test_data_rich_high_factual(self):
        score = compute_passage_score(DATA_RICH)
        self.assertGreater(score["factual_density"], 60)

    def test_definition_high_pattern(self):
        score = compute_passage_score(DEFINITION_PASSAGE)
        self.assertGreater(score["citation_pattern"], 40)
        self.assertIn("definition", score["patterns"])

    def test_comparison_detected(self):
        score = compute_passage_score(COMPARISON_PASSAGE)
        self.assertIn("comparison", score["patterns"])

    def test_score_has_all_dimensions(self):
        score = compute_passage_score(GOOD_PASSAGE)
        for key in ["overall", "clarity", "factual_density", "citation_pattern", "self_containment"]:
            self.assertIn(key, score)


class TestEstimateImprovement(unittest.TestCase):

    def test_low_score_high_improvement(self):
        score = compute_passage_score(VAGUE_PASSAGE)
        weaknesses = analyze_weakness(VAGUE_PASSAGE)
        strategies = suggest_strategies(weaknesses)
        improvement = estimate_improvement(score, strategies)
        self.assertGreater(improvement, 5)

    def test_high_score_low_improvement(self):
        score = compute_passage_score(GOOD_PASSAGE)
        weaknesses = analyze_weakness(GOOD_PASSAGE)
        strategies = suggest_strategies(weaknesses)
        improvement = estimate_improvement(score, strategies)
        self.assertLessEqual(improvement, score["overall"])

    def test_no_strategies_zero_improvement(self):
        score = compute_passage_score(GOOD_PASSAGE)
        improvement = estimate_improvement(score, [])
        self.assertEqual(improvement, 0.0)

    def test_improvement_within_bounds(self):
        score = compute_passage_score(VAGUE_PASSAGE)
        weaknesses = analyze_weakness(VAGUE_PASSAGE)
        strategies = suggest_strategies(weaknesses)
        improvement = estimate_improvement(score, strategies)
        self.assertLessEqual(score["overall"] + improvement, 100)
        self.assertGreaterEqual(improvement, 0)


class TestPlatformTips(unittest.TestCase):

    def test_tips_for_relevant_platforms(self):
        strategies = [REWRITE_STRATEGIES["add_definition"]]
        strategies[0] = dict(strategies[0])
        strategies[0]["key"] = "add_definition"
        tips = platform_tips(strategies)
        self.assertGreater(len(tips), 0)

    def test_empty_strategies(self):
        tips = platform_tips([])
        for platform_tips_list in tips.values():
            self.assertEqual(len(platform_tips_list), 0)


class TestAnalyzeRewrite(unittest.TestCase):

    def test_page_analysis(self):
        result = analyze_rewrite(PAGE_HTML, "https://example.com")
        self.assertTrue(result["success"])
        self.assertGreater(result["total_passages"], 0)

    def test_has_suggestions(self):
        result = analyze_rewrite(PAGE_HTML, "https://example.com")
        self.assertGreater(len(result["suggestions"]), 0)

    def test_has_page_summary(self):
        result = analyze_rewrite(PAGE_HTML, "https://example.com")
        summary = result["page_summary"]
        for key in ["avg_score", "weak_count", "ok_count", "strong_count"]:
            self.assertIn(key, summary)

    def test_suggestions_sorted_by_improvement(self):
        result = analyze_rewrite(PAGE_HTML, "https://example.com")
        if len(result["suggestions"]) >= 2:
            improvements = [s["estimated_improvement"] for s in result["suggestions"]]
            self.assertGreaterEqual(improvements[0], improvements[-1])

    def test_empty_page(self):
        result = analyze_rewrite(EMPTY_HTML, "https://example.com")
        self.assertTrue(result["success"])
        self.assertEqual(result["total_passages"], 0)
        self.assertGreater(len(result["priority_actions"]), 0)

    def test_max_suggestions_respected(self):
        result = analyze_rewrite(PAGE_HTML, "https://example.com", max_suggestions=2)
        self.assertLessEqual(len(result["suggestions"]), 2)

    def test_suggestion_structure(self):
        result = analyze_rewrite(PAGE_HTML, "https://example.com")
        for s in result["suggestions"]:
            self.assertIn("text", s)
            self.assertIn("score", s)
            self.assertIn("weaknesses", s)
            self.assertIn("strategies", s)
            self.assertIn("estimated_improvement", s)
            self.assertIn("platform_tips", s)


class TestPriorityActions(unittest.TestCase):

    def test_low_avg_generates_action(self):
        actions = _generate_priority_actions([], 30.0, 2)
        self.assertTrue(any("전면적" in a for a in actions))

    def test_many_weak_generates_action(self):
        actions = _generate_priority_actions([], 50.0, 6)
        self.assertTrue(any("우선순위" in a for a in actions))

    def test_repeated_weakness_pattern(self):
        suggestions = [
            {"weaknesses": [{"type": "no_citation_pattern"}]},
            {"weaknesses": [{"type": "no_citation_pattern"}]},
            {"weaknesses": [{"type": "no_citation_pattern"}]},
        ]
        actions = _generate_priority_actions(suggestions, 45.0, 3)
        self.assertTrue(any("인용 패턴" in a for a in actions))


class TestFormatReport(unittest.TestCase):

    def test_format_success(self):
        result = analyze_rewrite(PAGE_HTML, "https://example.com")
        report = format_rewrite_report(result)
        self.assertIn("Content Rewrite Suggestions", report)
        self.assertIn("Passage", report)

    def test_format_empty_page(self):
        result = analyze_rewrite(EMPTY_HTML, "https://example.com")
        report = format_rewrite_report(result)
        self.assertIn("0 total", report)

    def test_format_error(self):
        report = format_rewrite_report({"success": False, "error": "test error"})
        self.assertIn("Error", report)


class TestRewriteStrategies(unittest.TestCase):

    def test_all_strategies_have_fields(self):
        for key, strategy in REWRITE_STRATEGIES.items():
            self.assertIn("name_ko", strategy)
            self.assertIn("name_en", strategy)
            self.assertIn("template_ko", strategy)
            self.assertIn("template_en", strategy)
            self.assertIn("impact", strategy)
            self.assertIn("platforms", strategy)

    def test_all_impacts_valid(self):
        for strategy in REWRITE_STRATEGIES.values():
            self.assertIn(strategy["impact"], ["high", "medium", "low"])

    def test_all_platforms_valid(self):
        valid_platforms = {"chatgpt", "perplexity", "gemini", "claude"}
        for strategy in REWRITE_STRATEGIES.values():
            for p in strategy["platforms"]:
                self.assertIn(p, valid_platforms)


if __name__ == "__main__":
    unittest.main()

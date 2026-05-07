"""Tests for GEO citability: citation patterns, self-containment, platform scoring."""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from geo_citability import (
    score_citation_pattern, score_self_containment, score_platform_citability,
    score_passage_clarity, score_factual_density, score_structural_format,
    score_authority_signals, score_uniqueness, extract_passages,
    CITABILITY_WEIGHTS,
)


class TestCitationPattern(unittest.TestCase):

    def test_definition_pattern_korean(self):
        passage = "SEO란 검색엔진 최적화를 의미하며 웹사이트의 가시성을 높이는 전략입니다"
        result = score_citation_pattern(passage)
        self.assertIn("definition", result["patterns"])
        self.assertGreater(result["score"], 40)

    def test_definition_pattern_english(self):
        passage = "Three-O is a unified optimization platform that combines SEO, GEO, and AAO into a single score."
        result = score_citation_pattern(passage)
        self.assertIn("definition", result["patterns"])

    def test_comparison_pattern(self):
        passage = "SEO에 비해 GEO는 AI 엔진 최적화에 초점을 맞추며, 차이점은 타겟 엔진에 있다"
        result = score_citation_pattern(passage)
        self.assertIn("comparison", result["patterns"])

    def test_step_pattern(self):
        passage = "첫째, 기술적 기반을 구축합니다. 둘째, 콘텐츠를 최적화합니다."
        result = score_citation_pattern(passage)
        self.assertIn("step", result["patterns"])

    def test_causal_pattern(self):
        passage = "Because structured data provides machine-readable context, search engines can better understand the page."
        result = score_citation_pattern(passage)
        self.assertIn("causal", result["patterns"])

    def test_data_pattern(self):
        passage = "매출이 150% 증가했으며, 방문자 수는 월 50,000명을 달성했다."
        result = score_citation_pattern(passage)
        self.assertIn("data", result["patterns"])

    def test_no_patterns(self):
        passage = "A plain generic remark with nothing notable."
        result = score_citation_pattern(passage)
        self.assertLess(result["score"], 40)

    def test_multiple_patterns(self):
        passage = "SEO란 검색엔진 최적화이다. 에 비해 GEO는 다르다. 첫째 기반 구축. 매출 50% 증가."
        result = score_citation_pattern(passage)
        self.assertGreaterEqual(len(result["patterns"]), 2)
        self.assertGreater(result["score"], 60)

    def test_score_capped_at_100(self):
        passage = "SEO란 검색엔진이다. 에 비해 차이점. 첫째 둘째. 때문에 결과적으로. 150% 200명 300억."
        result = score_citation_pattern(passage)
        self.assertLessEqual(result["score"], 100)


class TestSelfContainment(unittest.TestCase):

    def test_standalone_passage(self):
        passage = "Three-O Score는 SEO, GEO, AAO 세 축의 통합 점수로, 0에서 100까지의 범위를 가진다."
        score = score_self_containment(passage)
        self.assertGreater(score, 60)

    def test_context_dependent_low(self):
        passage = "이것은 위의 내용을 바탕으로 그것을 설명한 것이다. this refers to that above."
        score = score_self_containment(passage)
        self.assertLess(score, 50)

    def test_optimal_length_bonus(self):
        short = "Short."
        medium = "This is a medium-length passage that contains enough information to be useful on its own as a standalone answer to a question."
        s_short = score_self_containment(short)
        s_medium = score_self_containment(medium)
        self.assertGreater(s_medium, s_short)

    def test_question_opener_bonus(self):
        passage = "What is Three-O? It is a unified optimization platform combining three pillars of digital visibility."
        score = score_self_containment(passage)
        self.assertGreater(score, 60)


class TestPlatformCitability(unittest.TestCase):

    def test_definition_boosts_chatgpt(self):
        pattern_result = {"score": 50, "patterns": ["definition"]}
        scores = score_platform_citability("test", pattern_result)
        self.assertGreater(scores["chatgpt"], scores["perplexity"])

    def test_data_boosts_perplexity(self):
        pattern_result = {"score": 50, "patterns": ["data"]}
        scores = score_platform_citability("test", pattern_result)
        self.assertGreater(scores["perplexity"], scores["chatgpt"])

    def test_all_platforms_present(self):
        pattern_result = {"score": 50, "patterns": ["definition"]}
        scores = score_platform_citability("test", pattern_result)
        self.assertIn("chatgpt", scores)
        self.assertIn("perplexity", scores)
        self.assertIn("gemini", scores)
        self.assertIn("claude", scores)

    def test_scores_capped_at_100(self):
        pattern_result = {"score": 95, "patterns": ["definition", "data", "comparison"]}
        scores = score_platform_citability("test", pattern_result)
        for s in scores.values():
            self.assertLessEqual(s, 100)


class TestPassageClarity(unittest.TestCase):

    def test_clear_passage_high(self):
        passage = "Structured data helps search engines understand page content. It uses Schema.org vocabulary to mark up entities."
        score = score_passage_clarity(passage)
        self.assertGreater(score, 50)

    def test_empty_low(self):
        score = score_passage_clarity("")
        self.assertLessEqual(score, 30)

    def test_pronoun_heavy_lower(self):
        clean = "SEO optimization requires careful keyword research. Content quality drives rankings."
        pronoun = "It requires this. They use that. It helps them."
        s_clean = score_passage_clarity(clean)
        s_pronoun = score_passage_clarity(pronoun)
        self.assertGreater(s_clean, s_pronoun)


class TestFactualDensity(unittest.TestCase):

    def test_data_rich(self):
        passage = "매출 150억, 직원 500명, 시장점유율 35%, 성장률 12.5%를 기록했다."
        score = score_factual_density(passage)
        self.assertGreater(score, 60)

    def test_no_data(self):
        passage = "this is a general statement without any specific numbers or facts"
        score = score_factual_density(passage)
        self.assertLess(score, 50)


class TestStructuralFormat(unittest.TestCase):

    def test_rich_structure(self):
        html = "<h2>A</h2><h2>B</h2><h3>C</h3><ul><li>x</li></ul><ol><li>y</li></ol><table><tr><td>z</td></tr></table>"
        score = score_structural_format(html)
        self.assertGreaterEqual(score, 60)

    def test_minimal_structure(self):
        html = "<p>Just a paragraph</p>"
        score = score_structural_format(html)
        self.assertLess(score, 50)


class TestAuthoritySignals(unittest.TestCase):

    def test_strong_authority(self):
        html = '<p>Author: Dr. Kim</p><p>Published: 2025-01-01</p><p>Source: Korea Research Institute</p><p>Study shows</p><script type="application/ld+json">{}</script>'
        score = score_authority_signals(html)
        self.assertGreater(score, 60)

    def test_no_authority(self):
        html = "<p>Hello world</p>"
        score = score_authority_signals(html)
        self.assertLess(score, 30)


class TestExtractPassages(unittest.TestCase):

    def test_extracts_paragraphs(self):
        html = '<p>This is a long enough paragraph that should be extracted as a passage for analysis.</p><p>Short</p>'
        passages = extract_passages(html)
        self.assertEqual(len(passages), 1)

    def test_extracts_list_items(self):
        html = '<li>This is a long enough list item that should be extracted as a passage for citability analysis.</li>'
        passages = extract_passages(html)
        self.assertEqual(len(passages), 1)

    def test_filters_short(self):
        html = '<p>Too short</p><p>Also too short</p>'
        passages = extract_passages(html)
        self.assertEqual(len(passages), 0)


class TestWeightsValid(unittest.TestCase):

    def test_weights_sum_to_one(self):
        total = sum(CITABILITY_WEIGHTS.values())
        self.assertAlmostEqual(total, 1.0, places=2)


if __name__ == "__main__":
    unittest.main()

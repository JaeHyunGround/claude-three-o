"""Tests for passage-level AI citability analysis."""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from geo_citability import (
    extract_passages,
    analyze_sentence_structure,
    score_passage_clarity,
    score_factual_density,
    score_citation_pattern,
    score_self_containment,
    score_quote_readiness,
    score_structural_format,
    score_authority_signals,
    score_platform_citability,
    analyze_citability_html,
    CITABILITY_WEIGHTS,
    PLATFORM_CRITERIA,
)


EMPTY_HTML = "<html><body></body></html>"

RICH_HTML = """
<html><head>
<script type="application/ld+json">{"@type":"Article","author":{"name":"Dr. Kim"}}</script>
</head><body>
<article>
<h1>한국 검색엔진 시장 분석 2024</h1>
<p>한국 검색엔진 시장은 2024년 기준 네이버가 56.2%의 점유율을 기록하고 있다. 구글은 34.8%로 전년 대비 3.2%p 상승했으며, 다음은 5.1%를 차지했다.</p>
<p>SEO란 검색엔진 최적화(Search Engine Optimization)를 의미하는 디지털 마케팅 전략이다. 웹사이트의 가시성을 높여 자연 검색 결과에서 상위 노출을 달성하는 것이 목표입니다.</p>
<h2>네이버 vs 구글 비교</h2>
<p>네이버에 비해 구글은 백링크 중심의 알고리즘을 사용한다. 반면 네이버는 콘텐츠 품질과 신뢰도에 더 높은 가중치를 부여한다. 이러한 차이점 때문에 전략을 달리해야 한다.</p>
<h2>최적화 단계</h2>
<p>첫째, 키워드 리서치를 실시한다. 둘째, 콘텐츠를 최적화한다. 셋째, 기술적 SEO를 점검한다. 마지막으로 성과를 측정한다.</p>
<blockquote>출처: 한국인터넷진흥원(KISA) 2024년 보고서에 따르면 모바일 검색 비중이 72%를 차지한다.</blockquote>
<ul>
<li>기술적 SEO: 사이트 속도, 모바일 최적화, 구조화 데이터 관리</li>
<li>콘텐츠 SEO: E-E-A-T 기반 고품질 콘텐츠 작성 및 키워드 전략</li>
</ul>
<table><tr><td>네이버 SEO 점수: 85점 — 콘텐츠 품질 위주 평가</td></tr></table>
<p>작성자: 김박사 (디지털마케팅 Ph.D, 전문가)</p>
<p>발행일: 2024-06-15</p>
<p>참고: Nielsen Korea 연구 보고서</p>
</article>
</body></html>
"""

VAGUE_HTML = """
<html><body>
<p>저희는 최고의 다양한 서비스를 제공합니다. 고객님의 만족을 위해 최선을 다하겠습니다.</p>
<p>이것은 그런 방식으로 처리됩니다. 그것이 위의 내용과 관련이 있습니다.</p>
<p>좋은 결과를 위해 노력하고 있습니다.</p>
</body></html>
"""

DEFINITION_PASSAGE = "SEO란 검색엔진 최적화를 의미하는 디지털 마케팅 전략이다. 웹사이트의 가시성을 높이는 것이 핵심 목표입니다."

COMPARISON_PASSAGE = "네이버에 비해 구글은 백링크 중심의 알고리즘을 사용한다. 반면 네이버는 콘텐츠 품질에 더 높은 가중치를 부여한다."

STEP_PASSAGE = "첫째, 키워드 리서치를 실시한다. 둘째, 콘텐츠를 최적화한다. 셋째, 기술적 SEO를 점검한다."

CAUSAL_PASSAGE = "모바일 트래픽이 증가했기 때문에 반응형 디자인이 필수적이다. 따라서 모바일 최적화에 투자해야 한다."

DATA_PASSAGE = "2024년 기준 네이버 점유율은 56.2%이며, 구글은 34.8%를 기록했다. 전년 대비 구글은 3.2%p 상승했다."

CONTEXT_DEPENDENT = "이것은 그런 방식으로 처리됩니다. 그것이 위의 내용과 관련이 있습니다. 저것도 마찬가지입니다."

SELF_CONTAINED = "Google Search Console은 웹사이트 소유자가 검색 성능을 모니터링하고 최적화할 수 있는 무료 도구이다. 인덱싱 상태, 검색 쿼리, 클릭률 등을 확인할 수 있다."

SHORT_PASSAGE = "좋습니다."

FILLER_PASSAGE = "저희는 최고의 다양한 서비스를 제공합니다. 정말 amazing한 incredible 경험을 드립니다."


class TestExtractPassages(unittest.TestCase):
    def test_paragraph_extraction(self):
        html = "<p>This is a passage with enough text to be extracted from the page.</p>"
        passages = extract_passages(html)
        self.assertGreater(len(passages), 0)
        self.assertEqual(passages[0]["source"], "paragraph")

    def test_list_extraction(self):
        html = "<li>A detailed list item with enough content to meet the minimum length threshold.</li>"
        passages = extract_passages(html)
        self.assertGreater(len(passages), 0)
        self.assertEqual(passages[0]["source"], "list_item")

    def test_blockquote_extraction(self):
        html = "<blockquote>A quoted passage with enough text to be meaningful for analysis purposes.</blockquote>"
        passages = extract_passages(html)
        self.assertGreater(len(passages), 0)
        self.assertEqual(passages[0]["source"], "blockquote")

    def test_table_cell_extraction(self):
        html = "<td>A table cell with enough content to be considered a meaningful passage for analysis.</td>"
        passages = extract_passages(html)
        self.assertGreater(len(passages), 0)

    def test_heading_paragraph_combined(self):
        html = "<h2>Section Title</h2><p>A paragraph that follows the heading with enough text to meet the threshold for extraction.</p>"
        passages = extract_passages(html)
        combined = [p for p in passages if p["source"] == "heading_paragraph"]
        self.assertGreater(len(combined), 0)

    def test_dedup(self):
        html = "<p>Duplicate passage with enough text to test deduplication logic.</p><p>Duplicate passage with enough text to test deduplication logic.</p>"
        passages = extract_passages(html)
        self.assertEqual(len(passages), 1)

    def test_short_filtered(self):
        html = "<p>Too short.</p>"
        passages = extract_passages(html)
        self.assertEqual(len(passages), 0)

    def test_empty_html(self):
        passages = extract_passages(EMPTY_HTML)
        self.assertEqual(len(passages), 0)

    def test_rich_html_many_passages(self):
        passages = extract_passages(RICH_HTML)
        self.assertGreater(len(passages), 5)


class TestAnalyzeSentenceStructure(unittest.TestCase):
    def test_good_structure(self):
        result = analyze_sentence_structure(DEFINITION_PASSAGE)
        self.assertGreater(result["quality"], 50)
        self.assertGreater(result["count"], 0)

    def test_empty_passage(self):
        result = analyze_sentence_structure("")
        self.assertEqual(result["quality"], 0)
        self.assertEqual(result["count"], 0)

    def test_active_ratio(self):
        active = "Google provides SEO tools. Naver offers search optimization."
        result = analyze_sentence_structure(active)
        self.assertGreater(result["active_ratio"], 0.5)

    def test_clear_subject(self):
        result = analyze_sentence_structure(SELF_CONTAINED)
        self.assertGreater(result["clear_subject_ratio"], 0.5)

    def test_avg_length(self):
        result = analyze_sentence_structure(DATA_PASSAGE)
        self.assertGreater(result["avg_length"], 0)


class TestScorePassageClarity(unittest.TestCase):
    def test_clear_passage_high(self):
        result = score_passage_clarity(SELF_CONTAINED)
        self.assertGreater(result["score"], 50)

    def test_vague_passage_lower(self):
        result = score_passage_clarity(CONTEXT_DEPENDENT)
        clear_result = score_passage_clarity(SELF_CONTAINED)
        self.assertLess(result["score"], clear_result["score"])

    def test_has_structure(self):
        result = score_passage_clarity(DEFINITION_PASSAGE)
        self.assertIn("structure", result)

    def test_empty(self):
        result = score_passage_clarity("")
        self.assertLessEqual(result["score"], 20)

    def test_score_range(self):
        for text in [DEFINITION_PASSAGE, CONTEXT_DEPENDENT, SHORT_PASSAGE, DATA_PASSAGE]:
            result = score_passage_clarity(text)
            self.assertGreaterEqual(result["score"], 0)
            self.assertLessEqual(result["score"], 100)


class TestScoreFactualDensity(unittest.TestCase):
    def test_data_rich_high(self):
        result = score_factual_density(DATA_PASSAGE)
        self.assertGreater(result["score"], 50)
        self.assertGreater(result["hard_stats"], 0)

    def test_vague_low(self):
        result = score_factual_density("좋은 서비스를 제공합니다.")
        self.assertLess(result["score"], 30)

    def test_proper_nouns(self):
        result = score_factual_density("Google Search Console and Microsoft Bing Webmaster Tools are essential.")
        self.assertGreater(result["proper_nouns"], 0)

    def test_korean_entities(self):
        result = score_factual_density("네이버와 카카오는 한국 시장에서 삼성과 함께 핵심 기업이다.")
        self.assertGreater(result["korean_entities"], 0)

    def test_dates(self):
        result = score_factual_density("2024년 3월 기준으로 시장 변화가 있었다.")
        self.assertGreater(result["dates"], 0)

    def test_sources(self):
        result = score_factual_density("한국인터넷진흥원 보고서에 따르면 모바일 비중이 증가했다.")
        self.assertGreater(result["sources"], 0)

    def test_density_calculation(self):
        result = score_factual_density(DATA_PASSAGE)
        self.assertGreater(result["fact_density"], 0)

    def test_score_range(self):
        for text in [DATA_PASSAGE, SHORT_PASSAGE, FILLER_PASSAGE]:
            result = score_factual_density(text)
            self.assertGreaterEqual(result["score"], 0)
            self.assertLessEqual(result["score"], 100)


class TestScoreCitationPattern(unittest.TestCase):
    def test_definition_detected(self):
        result = score_citation_pattern(DEFINITION_PASSAGE)
        self.assertIn("definition", result["patterns"])

    def test_comparison_detected(self):
        result = score_citation_pattern(COMPARISON_PASSAGE)
        self.assertIn("comparison", result["patterns"])

    def test_step_detected(self):
        result = score_citation_pattern(STEP_PASSAGE)
        self.assertIn("step", result["patterns"])

    def test_causal_detected(self):
        result = score_citation_pattern(CAUSAL_PASSAGE)
        self.assertIn("causal", result["patterns"])

    def test_data_detected(self):
        result = score_citation_pattern(DATA_PASSAGE)
        self.assertTrue("data" in result["patterns"] or "data_rich" in result["patterns"])

    def test_multiple_patterns_bonus(self):
        combined = "SEO란 검색엔진 최적화이다. 네이버에 비해 구글은 다르다. 따라서 전략이 필요하다. 점유율 56.2%, 34.8%, 5.1%를 기록했다."
        result = score_citation_pattern(combined)
        self.assertGreater(result["pattern_count"], 2)

    def test_no_patterns(self):
        result = score_citation_pattern("간단한 문장입니다.")
        self.assertEqual(len(result["patterns"]), 0)

    def test_score_range(self):
        for text in [DEFINITION_PASSAGE, SHORT_PASSAGE, DATA_PASSAGE]:
            result = score_citation_pattern(text)
            self.assertGreaterEqual(result["score"], 0)
            self.assertLessEqual(result["score"], 100)


class TestScoreSelfContainment(unittest.TestCase):
    def test_self_contained_high(self):
        result = score_self_containment(SELF_CONTAINED)
        self.assertGreater(result["score"], 60)
        self.assertEqual(result["context_dependencies"], 0)

    def test_context_dependent_low(self):
        result = score_self_containment(CONTEXT_DEPENDENT)
        self.assertLess(result["score"], 50)
        self.assertGreater(result["context_dependencies"], 0)

    def test_ideal_length_bonus(self):
        passage = "A" * 80 + " word " * 20 + " sentence end."
        result = score_self_containment(passage)
        self.assertGreater(result["score"], 40)

    def test_too_short_penalty(self):
        result = score_self_containment(SHORT_PASSAGE)
        self.assertIn("too_short", result["issues"])

    def test_question_start_bonus(self):
        result = score_self_containment("무엇이 SEO의 핵심 전략인가? 키워드 리서치와 콘텐츠 최적화가 가장 중요하다.")
        self.assertGreater(result["score"], 50)

    def test_weak_opener_penalty(self):
        result = score_self_containment("this method is effective for various situations and can be applied across multiple domains and use cases in practice.")
        self.assertIn("weak_opener", result["issues"])

    def test_score_range(self):
        for text in [SELF_CONTAINED, CONTEXT_DEPENDENT, SHORT_PASSAGE]:
            result = score_self_containment(text)
            self.assertGreaterEqual(result["score"], 0)
            self.assertLessEqual(result["score"], 100)


class TestScoreQuoteReadiness(unittest.TestCase):
    def test_definition_high(self):
        pattern = score_citation_pattern(DEFINITION_PASSAGE)
        result = score_quote_readiness(DEFINITION_PASSAGE, pattern)
        self.assertGreater(result["score"], 40)

    def test_filler_penalty(self):
        pattern = score_citation_pattern(FILLER_PASSAGE)
        result = score_quote_readiness(FILLER_PASSAGE, pattern)
        self.assertTrue(result["signals"]["has_filler"])

    def test_concise_bonus(self):
        short_def = "SEO는 검색엔진 최적화를 의미한다. 웹사이트 가시성 향상이 목표이다."
        pattern = score_citation_pattern(short_def)
        result = score_quote_readiness(short_def, pattern)
        self.assertTrue(result["signals"]["concise"])

    def test_self_contained_signal(self):
        pattern = score_citation_pattern(SELF_CONTAINED)
        result = score_quote_readiness(SELF_CONTAINED, pattern)
        self.assertTrue(result["signals"]["self_contained"])

    def test_context_dependent_not_contained(self):
        pattern = score_citation_pattern(CONTEXT_DEPENDENT)
        result = score_quote_readiness(CONTEXT_DEPENDENT, pattern)
        self.assertFalse(result["signals"]["self_contained"])

    def test_score_range(self):
        for text in [DEFINITION_PASSAGE, FILLER_PASSAGE, DATA_PASSAGE]:
            pattern = score_citation_pattern(text)
            result = score_quote_readiness(text, pattern)
            self.assertGreaterEqual(result["score"], 0)
            self.assertLessEqual(result["score"], 100)


class TestScoreStructuralFormat(unittest.TestCase):
    def test_rich_html_high(self):
        result = score_structural_format(RICH_HTML)
        self.assertGreater(result["score"], 50)

    def test_empty_html_low(self):
        result = score_structural_format(EMPTY_HTML)
        self.assertLess(result["score"], 30)

    def test_headings_counted(self):
        result = score_structural_format(RICH_HTML)
        self.assertGreater(result["details"]["headings"], 0)

    def test_lists_counted(self):
        result = score_structural_format(RICH_HTML)
        self.assertGreater(result["details"]["lists"], 0)

    def test_tables_counted(self):
        result = score_structural_format(RICH_HTML)
        self.assertGreater(result["details"]["tables"], 0)

    def test_semantic_html(self):
        result = score_structural_format(RICH_HTML)
        self.assertTrue(result["details"]["semantic_html"])

    def test_structured_data(self):
        result = score_structural_format(RICH_HTML)
        self.assertTrue(result["details"]["structured_data"])

    def test_blockquotes(self):
        result = score_structural_format(RICH_HTML)
        self.assertGreater(result["details"]["blockquotes"], 0)

    def test_score_range(self):
        for html in [EMPTY_HTML, RICH_HTML]:
            result = score_structural_format(html)
            self.assertGreaterEqual(result["score"], 0)
            self.assertLessEqual(result["score"], 100)


class TestScoreAuthoritySignals(unittest.TestCase):
    def test_rich_html_high(self):
        result = score_authority_signals(RICH_HTML)
        self.assertGreater(result["score"], 50)

    def test_empty_html_low(self):
        result = score_authority_signals(EMPTY_HTML)
        self.assertLess(result["score"], 20)

    def test_author_detected(self):
        result = score_authority_signals(RICH_HTML)
        self.assertTrue(result["details"]["author"])

    def test_date_detected(self):
        result = score_authority_signals(RICH_HTML)
        self.assertTrue(result["details"]["date"])

    def test_sources_detected(self):
        result = score_authority_signals(RICH_HTML)
        self.assertTrue(result["details"]["sources"])

    def test_expert_detected(self):
        result = score_authority_signals(RICH_HTML)
        self.assertTrue(result["details"]["expert"])

    def test_schema_detected(self):
        result = score_authority_signals(RICH_HTML)
        self.assertTrue(result["details"]["schema"])

    def test_score_range(self):
        for html in [EMPTY_HTML, RICH_HTML]:
            result = score_authority_signals(html)
            self.assertGreaterEqual(result["score"], 0)
            self.assertLessEqual(result["score"], 100)


class TestScorePlatformCitability(unittest.TestCase):
    def test_four_platforms(self):
        pattern = score_citation_pattern(DEFINITION_PASSAGE)
        result = score_platform_citability(DEFINITION_PASSAGE, pattern, len(DEFINITION_PASSAGE))
        self.assertEqual(len(result), 4)
        self.assertIn("chatgpt", result)
        self.assertIn("perplexity", result)
        self.assertIn("gemini", result)
        self.assertIn("claude", result)

    def test_definition_chatgpt_boost(self):
        pattern = score_citation_pattern(DEFINITION_PASSAGE)
        result = score_platform_citability(DEFINITION_PASSAGE, pattern, len(DEFINITION_PASSAGE))
        self.assertGreater(result["chatgpt"], pattern["score"])

    def test_data_perplexity_boost(self):
        pattern = score_citation_pattern(DATA_PASSAGE)
        result = score_platform_citability(DATA_PASSAGE, pattern, len(DATA_PASSAGE))
        self.assertGreaterEqual(result["perplexity"], result["chatgpt"])

    def test_causal_claude_boost(self):
        pattern = score_citation_pattern(CAUSAL_PASSAGE)
        result = score_platform_citability(CAUSAL_PASSAGE, pattern, len(CAUSAL_PASSAGE))
        self.assertGreater(result["claude"], pattern["score"])

    def test_comparison_gemini_boost(self):
        pattern = score_citation_pattern(COMPARISON_PASSAGE)
        result = score_platform_citability(COMPARISON_PASSAGE, pattern, len(COMPARISON_PASSAGE))
        self.assertGreater(result["gemini"], pattern["score"])

    def test_score_range(self):
        pattern = score_citation_pattern(DATA_PASSAGE)
        result = score_platform_citability(DATA_PASSAGE, pattern, len(DATA_PASSAGE))
        for plat_score in result.values():
            self.assertGreaterEqual(plat_score, 0)
            self.assertLessEqual(plat_score, 100)


class TestAnalyzeCitabilityHtml(unittest.TestCase):
    def test_success(self):
        result = analyze_citability_html(RICH_HTML, "https://example.com")
        self.assertTrue(result["success"])

    def test_all_fields(self):
        result = analyze_citability_html(RICH_HTML, "https://example.com")
        self.assertIn("score", result)
        self.assertIn("dimensions", result)
        self.assertIn("weakest_dimension", result)
        self.assertIn("platform_citability", result)
        self.assertIn("total_passages", result)
        self.assertIn("top_passages", result)
        self.assertIn("structural", result)
        self.assertIn("authority", result)
        self.assertIn("issues", result)

    def test_seven_dimensions(self):
        result = analyze_citability_html(RICH_HTML, "https://example.com")
        dims = result["dimensions"]
        self.assertEqual(len(dims), 7)
        for key in CITABILITY_WEIGHTS:
            self.assertIn(key, dims)

    def test_rich_html_high_score(self):
        result = analyze_citability_html(RICH_HTML, "https://example.com")
        self.assertGreater(result["score"], 40)

    def test_empty_html_low_score(self):
        result = analyze_citability_html(EMPTY_HTML, "https://example.com")
        self.assertLess(result["score"], 30)

    def test_vague_html_lower(self):
        result = analyze_citability_html(VAGUE_HTML, "https://example.com")
        rich_result = analyze_citability_html(RICH_HTML, "https://example.com")
        self.assertLess(result["score"], rich_result["score"])

    def test_platform_scores(self):
        result = analyze_citability_html(RICH_HTML, "https://example.com")
        for plat in PLATFORM_CRITERIA:
            self.assertIn(plat, result["platform_citability"])

    def test_top_passages_sorted(self):
        result = analyze_citability_html(RICH_HTML, "https://example.com")
        if len(result["top_passages"]) >= 2:
            for i in range(len(result["top_passages"]) - 1):
                self.assertGreaterEqual(
                    result["top_passages"][i]["score"],
                    result["top_passages"][i + 1]["score"]
                )

    def test_passage_has_platform_scores(self):
        result = analyze_citability_html(RICH_HTML, "https://example.com")
        if result["top_passages"]:
            p = result["top_passages"][0]
            self.assertIn("platform_scores", p)
            self.assertIn("chatgpt", p["platform_scores"])

    def test_issues_sorted(self):
        result = analyze_citability_html(VAGUE_HTML, "https://example.com")
        if len(result["issues"]) >= 2:
            severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            for i in range(len(result["issues"]) - 1):
                s1 = severity_order.get(result["issues"][i]["severity"], 4)
                s2 = severity_order.get(result["issues"][i + 1]["severity"], 4)
                self.assertLessEqual(s1, s2)

    def test_weakest_dimension(self):
        result = analyze_citability_html(RICH_HTML, "https://example.com")
        self.assertIn(result["weakest_dimension"], CITABILITY_WEIGHTS)

    def test_score_range(self):
        for html in [EMPTY_HTML, RICH_HTML, VAGUE_HTML]:
            result = analyze_citability_html(html, "https://example.com")
            self.assertGreaterEqual(result["score"], 0)
            self.assertLessEqual(result["score"], 100)
            for dim_score in result["dimensions"].values():
                self.assertGreaterEqual(dim_score, 0)
                self.assertLessEqual(dim_score, 100)


class TestCitabilityWeights(unittest.TestCase):
    def test_weights_sum_to_one(self):
        total = sum(CITABILITY_WEIGHTS.values())
        self.assertAlmostEqual(total, 1.0, places=5)

    def test_seven_dimensions(self):
        self.assertEqual(len(CITABILITY_WEIGHTS), 7)

    def test_four_platforms(self):
        self.assertEqual(len(PLATFORM_CRITERIA), 4)
        for plat in ["chatgpt", "perplexity", "gemini", "claude"]:
            self.assertIn(plat, PLATFORM_CRITERIA)


class TestEdgeCases(unittest.TestCase):
    def test_large_html(self):
        html = "<html><body>" + "<p>A detailed paragraph about SEO optimization techniques and strategies.</p>" * 100 + "</body></html>"
        result = analyze_citability_html(html, "https://example.com")
        self.assertTrue(result["success"])

    def test_no_url(self):
        result = analyze_citability_html(RICH_HTML, "")
        self.assertTrue(result["success"])

    def test_english_patterns(self):
        passage = "SEO refers to Search Engine Optimization, which is the process of improving website visibility. Compared to paid advertising, SEO provides long-term organic traffic growth."
        result = score_citation_pattern(passage)
        self.assertGreater(len(result["patterns"]), 0)

    def test_mixed_language(self):
        passage = "SEO란 Search Engine Optimization의 약자로 검색엔진 최적화를 의미합니다. 2024년 기준 56.2%의 점유율을 기록했다."
        result = score_factual_density(passage)
        self.assertGreater(result["score"], 30)

    def test_passage_source_tracking(self):
        result = analyze_citability_html(RICH_HTML, "https://example.com")
        if result["top_passages"]:
            self.assertIn("source", result["top_passages"][0])


if __name__ == "__main__":
    unittest.main()

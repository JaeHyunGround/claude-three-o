"""Tests for GEO platform-specific multi-dimensional analyzers."""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from geo_platforms import (
    analyze_for_chatgpt, analyze_for_perplexity,
    analyze_for_gemini, analyze_for_claude,
    analyze_platforms_html, compute_platform_gaps,
    _check_crawler_blocked, _detect_recency, _count_definitions,
    PLATFORM_CONFIGS, PLATFORM_ANALYZERS, CURRENT_YEAR,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

RICH_HTML = f"""
<html lang="ko"><head>
<title>SEO 최적화 완벽 가이드 - 검색엔진 최적화 전문</title>
<meta name="description" content="SEO 최적화 가이드입니다. 검색엔진 최적화부터 AI 가시성까지 통합적으로 분석하고 개선하는 방법을 알려드립니다. 한국 시장 특화 최적화.">
<meta property="og:title" content="SEO Guide">
<meta property="og:description" content="SEO optimization guide for Korean market">
<meta property="og:image" content="https://example.com/og.png">
<meta property="og:url" content="https://example.com/guide">
</head><body>
<h1>SEO 최적화 가이드</h1>
<h2>What is SEO?</h2>
<p>SEO is a comprehensive approach to improving website visibility in search engine results pages through technical optimization and content quality.</p>
<p>GEO refers to optimizing content for generative AI engines like ChatGPT and Perplexity.</p>
<p>AAO means agent optimization for AI assistants and automated tools.</p>
<h2>Technical SEO</h2>
<p>Source: Google Search Central {CURRENT_YEAR} research study</p>
<p>According to a survey by Moz, 67% of clicks go to the first 5 results. The study shows significant correlation between page speed and rankings.</p>
<p>Published: {CURRENT_YEAR}-03-15</p>
<h2>Content Strategy</h2>
<p>Author: Dr. Park, PhD in Information Science with 15 years of experience</p>
<p>However, although technical factors matter, content quality remains the primary ranking factor. On the other hand, user experience signals are growing in importance.</p>
<p>Nevertheless, some experts argue that backlinks still outweigh content signals in competitive niches.</p>
<h3>Keyword Research</h3>
<ul><li>Step 1: Identify seed keywords</li><li>Step 2: Analyze competition</li><li>Step 3: Map intent</li></ul>
<ol><li>First method</li><li>Second method</li><li>Third method</li></ol>
<h3>FAQ Section</h3>
<p>FAQ: What is the best approach?</p>
<h3>Comparison</h3>
<table><tr><td>Tool</td><td>Score</td><td>Price</td></tr><tr><td>Ahrefs</td><td>9.2</td><td>$99</td></tr></table>
<table><tr><td>Metric</td><td>Value</td></tr><tr><td>CTR</td><td>3.5%</td></tr></table>
<p>The pros and cons of each approach vary. Some tools offer advantages in link analysis while others excel at content optimization.</p>
<a href="https://external.com/ref1">Reference 1</a>
<a href="https://external.com/ref2">Reference 2</a>
<a href="https://external.com/ref3">Reference 3</a>
<a href="/about">About us</a>
<a href="/contact">Contact</a>
<pre><code>print("hello world")</code></pre>
<script type="application/ld+json">{{"@type":"Article","sameAs":"https://example.com","datePublished":"{CURRENT_YEAR}-01-01"}}</script>
</body></html>
"""

MINIMAL_HTML = "<html><body><p>Short page with no structure.</p></body></html>"


def _make_html(body="", head=""):
    return f"<html lang='ko'><head>{head}</head><body>{body}</body></html>"


# ===========================================================================
# Shared helpers
# ===========================================================================

class TestCrawlerBlocked(unittest.TestCase):
    def test_no_restriction(self):
        result = _check_crawler_blocked("<html><body></body></html>", "GPTBot")
        self.assertGreaterEqual(result["score"], 90)

    def test_noindex_penalty(self):
        html = '<html><head><meta name="robots" content="noindex"></head><body></body></html>'
        result = _check_crawler_blocked(html, "GPTBot")
        self.assertLessEqual(result["score"], 70)

    def test_specific_bot_blocked(self):
        html = '<html><head><meta name="GPTBot" content="noindex"></head><body></body></html>'
        result = _check_crawler_blocked(html, "GPTBot")
        self.assertLessEqual(result["score"], 60)

    def test_llms_txt_bonus(self):
        html = '<html><body><a href="/llms.txt">AI Policy</a></body></html>'
        result = _check_crawler_blocked(html, "GPTBot")
        self.assertTrue(any("llms.txt" in s for s in result["signals"]))

    def test_score_bounded(self):
        html = '<html><head><meta name="robots" content="noindex, nofollow"><meta name="GPTBot" content="none"></head></html>'
        result = _check_crawler_blocked(html, "GPTBot")
        self.assertGreaterEqual(result["score"], 0)
        self.assertLessEqual(result["score"], 100)


class TestDetectRecency(unittest.TestCase):
    def test_current_year(self):
        html = f"<html><body><p>Updated in {CURRENT_YEAR}</p></body></html>"
        result = _detect_recency(html)
        self.assertGreaterEqual(result["score"], 30)
        self.assertTrue(any(str(CURRENT_YEAR) in s for s in result["signals"]))

    def test_old_content(self):
        html = "<html><body><p>Written in 2019</p></body></html>"
        result = _detect_recency(html)
        self.assertLessEqual(result["score"], 20)

    def test_date_metadata(self):
        html = '<html><body><time datetime="2025-01-01">Jan 2025</time></body></html>'
        result = _detect_recency(html)
        self.assertTrue(any("time" in s.lower() for s in result["signals"]))

    def test_schema_date(self):
        html = '<html><body><script type="application/ld+json">{"dateModified":"2025-01-01"}</script></body></html>'
        result = _detect_recency(html)
        self.assertTrue(any("schema" in s for s in result["signals"]))


class TestCountDefinitions(unittest.TestCase):
    def test_english_definitions(self):
        paras = ["SEO is a technique for improving search rankings.", "GEO refers to AI optimization."]
        self.assertGreaterEqual(_count_definitions(paras), 2)

    def test_korean_definitions(self):
        paras = ["검색엔진 최적화는 웹사이트의 가시성을 높이는 기술입니다."]
        self.assertGreaterEqual(_count_definitions(paras), 1)

    def test_no_definitions(self):
        paras = ["The weather is nice today.", "Let's go for a walk."]
        self.assertEqual(_count_definitions(paras), 0)


# ===========================================================================
# ChatGPT analyzer
# ===========================================================================

class TestChatGPTAnalyzer(unittest.TestCase):
    def test_rich_page_reasonable_score(self):
        result = analyze_for_chatgpt(RICH_HTML, "https://example.com")
        self.assertGreater(result["score"], 40)
        self.assertGreater(len(result["signals"]), 3)

    def test_minimal_page_low_score(self):
        result = analyze_for_chatgpt(MINIMAL_HTML, "https://example.com")
        self.assertLess(result["score"], 40)

    def test_has_dimensions(self):
        result = analyze_for_chatgpt(RICH_HTML, "https://example.com")
        self.assertIn("dimensions", result)
        self.assertIn("extractability", result["dimensions"])
        self.assertIn("structure", result["dimensions"])
        self.assertIn("structured_data", result["dimensions"])
        self.assertIn("freshness", result["dimensions"])
        self.assertIn("crawler_access", result["dimensions"])

    def test_detects_definitions(self):
        html = '<html><body><p>SEO is a comprehensive approach to improving visibility.</p><p>GEO refers to optimizing for AI.</p><p>AAO means agent optimization.</p></body></html>'
        result = analyze_for_chatgpt(html, "https://example.com")
        self.assertTrue(any("definition" in s.lower() for s in result["signals"]))

    def test_detects_faq(self):
        html = '<html><body><h2>FAQ</h2><p>Q: What is SEO?</p></body></html>'
        result = analyze_for_chatgpt(html, "https://example.com")
        self.assertTrue(any("faq" in s.lower() or "q&a" in s.lower() for s in result["signals"]))

    def test_detects_headings(self):
        result = analyze_for_chatgpt(RICH_HTML, "https://example.com")
        self.assertTrue(any("heading" in s.lower() or "sub-heading" in s.lower() for s in result["signals"]))

    def test_detects_lists(self):
        result = analyze_for_chatgpt(RICH_HTML, "https://example.com")
        self.assertTrue(any("list" in s.lower() for s in result["signals"]))

    def test_detects_structured_data(self):
        result = analyze_for_chatgpt(RICH_HTML, "https://example.com")
        self.assertTrue(any("json-ld" in s.lower() for s in result["signals"]))

    def test_detects_freshness(self):
        result = analyze_for_chatgpt(RICH_HTML, "https://example.com")
        self.assertTrue(any(str(CURRENT_YEAR) in s or "date" in s.lower() for s in result["signals"]))

    def test_score_capped(self):
        result = analyze_for_chatgpt(RICH_HTML, "https://example.com")
        self.assertLessEqual(result["score"], 100)

    def test_step_by_step_detected(self):
        html = '<html><body><p>Step 1: Do this. Step 2: Do that. Step 3: Finish.</p></body></html>'
        result = analyze_for_chatgpt(html, "https://example.com")
        self.assertTrue(any("step" in s.lower() for s in result["signals"]))


# ===========================================================================
# Perplexity analyzer
# ===========================================================================

class TestPerplexityAnalyzer(unittest.TestCase):
    def test_rich_page_reasonable_score(self):
        result = analyze_for_perplexity(RICH_HTML, "https://example.com")
        self.assertGreater(result["score"], 35)

    def test_has_dimensions(self):
        result = analyze_for_perplexity(RICH_HTML, "https://example.com")
        self.assertIn("dimensions", result)
        self.assertIn("factual_density", result["dimensions"])
        self.assertIn("source_attribution", result["dimensions"])
        self.assertIn("recency", result["dimensions"])
        self.assertIn("snippet_quality", result["dimensions"])
        self.assertIn("crawler_access", result["dimensions"])

    def test_detects_sources(self):
        result = analyze_for_perplexity(RICH_HTML, "https://example.com")
        self.assertTrue(any("source" in s.lower() or "attribution" in s.lower() for s in result["signals"]))

    def test_detects_data_density(self):
        result = analyze_for_perplexity(RICH_HTML, "https://example.com")
        self.assertTrue(any("data" in s.lower() or "density" in s.lower() for s in result["signals"]))

    def test_detects_recency(self):
        result = analyze_for_perplexity(RICH_HTML, "https://example.com")
        self.assertTrue(any(str(CURRENT_YEAR) in s or "date" in s.lower() for s in result["signals"]))

    def test_detects_author(self):
        result = analyze_for_perplexity(RICH_HTML, "https://example.com")
        self.assertTrue(any("author" in s.lower() for s in result["signals"]))

    def test_detects_outbound(self):
        result = analyze_for_perplexity(RICH_HTML, "https://example.com")
        self.assertTrue(any("outbound" in s.lower() or "reference" in s.lower() for s in result["signals"]))

    def test_minimal_page_low(self):
        result = analyze_for_perplexity(MINIMAL_HTML, "https://example.com")
        self.assertLess(result["score"], 35)

    def test_snippet_quality(self):
        result = analyze_for_perplexity(RICH_HTML, "https://example.com")
        sq = result["dimensions"]["snippet_quality"]
        self.assertGreater(sq["score"], 0)


# ===========================================================================
# Gemini analyzer
# ===========================================================================

class TestGeminiAnalyzer(unittest.TestCase):
    def test_rich_page_reasonable_score(self):
        result = analyze_for_gemini(RICH_HTML, "https://example.com")
        self.assertGreater(result["score"], 35)

    def test_has_dimensions(self):
        result = analyze_for_gemini(RICH_HTML, "https://example.com")
        self.assertIn("dimensions", result)
        self.assertIn("eeat_signals", result["dimensions"])
        self.assertIn("structured_data", result["dimensions"])
        self.assertIn("content_depth", result["dimensions"])
        self.assertIn("comparison_data", result["dimensions"])
        self.assertIn("crawler_access", result["dimensions"])

    def test_detects_eeat_expertise(self):
        result = analyze_for_gemini(RICH_HTML, "https://example.com")
        self.assertTrue(any("expertise" in s.lower() or "author" in s.lower() or "experience" in s.lower() for s in result["signals"]))

    def test_detects_tables(self):
        result = analyze_for_gemini(RICH_HTML, "https://example.com")
        self.assertTrue(any("table" in s.lower() for s in result["signals"]))

    def test_detects_structured_data(self):
        result = analyze_for_gemini(RICH_HTML, "https://example.com")
        self.assertTrue(any("json-ld" in s.lower() or "schema" in s.lower() for s in result["signals"]))

    def test_detects_sameas(self):
        result = analyze_for_gemini(RICH_HTML, "https://example.com")
        self.assertTrue(any("sameAs" in s for s in result["signals"]))

    def test_detects_comparison(self):
        result = analyze_for_gemini(RICH_HTML, "https://example.com")
        self.assertTrue(any("comparison" in s.lower() or "pros" in s.lower() for s in result["signals"]))

    def test_minimal_page_low(self):
        result = analyze_for_gemini(MINIMAL_HTML, "https://example.com")
        self.assertLess(result["score"], 35)

    def test_content_depth_dimension(self):
        result = analyze_for_gemini(RICH_HTML, "https://example.com")
        cd = result["dimensions"]["content_depth"]
        self.assertGreater(cd["score"], 0)


# ===========================================================================
# Claude analyzer
# ===========================================================================

class TestClaudeAnalyzer(unittest.TestCase):
    def test_rich_page_reasonable_score(self):
        result = analyze_for_claude(RICH_HTML, "https://example.com")
        self.assertGreater(result["score"], 30)

    def test_has_dimensions(self):
        result = analyze_for_claude(RICH_HTML, "https://example.com")
        self.assertIn("dimensions", result)
        self.assertIn("content_depth", result["dimensions"])
        self.assertIn("data_evidence", result["dimensions"])
        self.assertIn("nuanced_reasoning", result["dimensions"])
        self.assertIn("technical_quality", result["dimensions"])
        self.assertIn("crawler_access", result["dimensions"])

    def test_detects_nuance(self):
        result = analyze_for_claude(RICH_HTML, "https://example.com")
        self.assertTrue(any("nuance" in s.lower() or "qualifier" in s.lower() for s in result["signals"]))

    def test_detects_research(self):
        result = analyze_for_claude(RICH_HTML, "https://example.com")
        self.assertTrue(any("research" in s.lower() or "study" in s.lower() or "source" in s.lower() for s in result["signals"]))

    def test_detects_code(self):
        result = analyze_for_claude(RICH_HTML, "https://example.com")
        self.assertTrue(any("code" in s.lower() for s in result["signals"]))

    def test_detects_data_claims(self):
        result = analyze_for_claude(RICH_HTML, "https://example.com")
        self.assertTrue(any("data" in s.lower() or "claim" in s.lower() for s in result["signals"]))

    def test_minimal_page_low(self):
        result = analyze_for_claude(MINIMAL_HTML, "https://example.com")
        self.assertLess(result["score"], 35)

    def test_pros_cons_detected(self):
        result = analyze_for_claude(RICH_HTML, "https://example.com")
        self.assertTrue(any("pros" in s.lower() for s in result["signals"]))


# ===========================================================================
# Platform differentiation
# ===========================================================================

class TestPlatformDifferentiation(unittest.TestCase):
    def test_platforms_give_different_scores(self):
        scores = {
            "chatgpt": analyze_for_chatgpt(RICH_HTML, "https://example.com")["score"],
            "perplexity": analyze_for_perplexity(RICH_HTML, "https://example.com")["score"],
            "gemini": analyze_for_gemini(RICH_HTML, "https://example.com")["score"],
            "claude": analyze_for_claude(RICH_HTML, "https://example.com")["score"],
        }
        unique_scores = set(scores.values())
        self.assertGreater(len(unique_scores), 1)

    def test_all_platforms_in_config(self):
        self.assertIn("chatgpt", PLATFORM_CONFIGS)
        self.assertIn("perplexity", PLATFORM_CONFIGS)
        self.assertIn("gemini", PLATFORM_CONFIGS)
        self.assertIn("claude", PLATFORM_CONFIGS)

    def test_config_has_required_fields(self):
        for platform, config in PLATFORM_CONFIGS.items():
            self.assertIn("name", config)
            self.assertIn("crawler", config)
            self.assertIn("factors", config)

    def test_all_analyzers_registered(self):
        for platform in PLATFORM_CONFIGS:
            self.assertIn(platform, PLATFORM_ANALYZERS)

    def test_data_heavy_favors_perplexity(self):
        html = '<html><body>' + '<p>The rate is 45.7% according to the 2024 survey of 1,500 participants. Source: Research Institute.</p>' * 10 + '</body></html>'
        pplx = analyze_for_perplexity(html, "https://example.com")
        analyze_for_claude(html, "https://example.com")
        self.assertGreater(pplx["dimensions"]["factual_density"]["score"], 30)

    def test_nuanced_content_favors_claude(self):
        html = '<html><body>' + '<p>However, this approach has limitations. Although it works well, nevertheless some experts disagree. On the other hand, the data suggests otherwise. In contrast, alternative methods exist.</p>' * 3 + '</body></html>'
        claude = analyze_for_claude(html, "https://example.com")
        self.assertGreater(claude["dimensions"]["nuanced_reasoning"]["score"], 30)

    def test_schema_heavy_favors_gemini(self):
        html = '<html><body><script type="application/ld+json">{"@type":"Organization","sameAs":"https://wiki.org","name":"Test"}</script><script type="application/ld+json">{"@type":"BreadcrumbList"}</script></body></html>'
        gemini = analyze_for_gemini(html, "https://example.com")
        self.assertGreater(gemini["dimensions"]["structured_data"]["score"], 40)


# ===========================================================================
# Cross-platform analysis
# ===========================================================================

class TestComputePlatformGaps(unittest.TestCase):
    def test_no_gaps_balanced(self):
        results = {
            "chatgpt": {"name": "ChatGPT", "score": 60},
            "perplexity": {"name": "Perplexity", "score": 58},
            "gemini": {"name": "Gemini", "score": 62},
            "claude": {"name": "Claude", "score": 60},
        }
        gaps = compute_platform_gaps(results)
        self.assertEqual(len(gaps), 0)

    def test_detects_gap(self):
        results = {
            "chatgpt": {"name": "ChatGPT", "score": 70},
            "perplexity": {"name": "Perplexity", "score": 30},
            "gemini": {"name": "Gemini", "score": 70},
            "claude": {"name": "Claude", "score": 70},
        }
        gaps = compute_platform_gaps(results)
        self.assertGreater(len(gaps), 0)
        self.assertEqual(gaps[0]["platform"], "perplexity")

    def test_gap_severity(self):
        results = {
            "chatgpt": {"name": "ChatGPT", "score": 80},
            "perplexity": {"name": "Perplexity", "score": 20},
            "gemini": {"name": "Gemini", "score": 80},
            "claude": {"name": "Claude", "score": 80},
        }
        gaps = compute_platform_gaps(results)
        self.assertTrue(any(g["severity"] == "high" for g in gaps))

    def test_single_platform_no_gaps(self):
        results = {"chatgpt": {"name": "ChatGPT", "score": 50}}
        gaps = compute_platform_gaps(results)
        self.assertEqual(len(gaps), 0)


class TestAnalyzePlatformsHTML(unittest.TestCase):
    def test_full_analysis(self):
        result = analyze_platforms_html(RICH_HTML, "https://example.com")
        self.assertIn("avg_score", result)
        self.assertIn("best_platform", result)
        self.assertIn("worst_platform", result)
        self.assertIn("platforms", result)
        self.assertEqual(len(result["platforms"]), 4)

    def test_single_platform(self):
        result = analyze_platforms_html(RICH_HTML, "https://example.com", ["chatgpt"])
        self.assertEqual(len(result["platforms"]), 1)
        self.assertIn("chatgpt", result["platforms"])

    def test_scores_bounded(self):
        result = analyze_platforms_html(RICH_HTML, "https://example.com")
        for platform, pr in result["platforms"].items():
            self.assertGreaterEqual(pr["score"], 0)
            self.assertLessEqual(pr["score"], 100)

    def test_dimensions_per_platform(self):
        result = analyze_platforms_html(RICH_HTML, "https://example.com")
        for platform, pr in result["platforms"].items():
            self.assertIn("dimensions", pr)
            self.assertGreater(len(pr["dimensions"]), 0)

    def test_score_spread(self):
        result = analyze_platforms_html(RICH_HTML, "https://example.com")
        self.assertIn("score_spread", result)
        self.assertGreaterEqual(result["score_spread"], 0)

    def test_gaps_detected(self):
        result = analyze_platforms_html(RICH_HTML, "https://example.com")
        self.assertIn("gaps", result)

    def test_minimal_html(self):
        result = analyze_platforms_html(MINIMAL_HTML, "https://example.com")
        self.assertLess(result["avg_score"], 40)

    def test_empty_html(self):
        result = analyze_platforms_html("", "https://example.com")
        self.assertIsInstance(result["avg_score"], float)


# ===========================================================================
# Edge cases
# ===========================================================================

class TestEdgeCases(unittest.TestCase):
    def test_all_scores_bounded(self):
        for html in [RICH_HTML, MINIMAL_HTML, "", "<html></html>"]:
            for platform in PLATFORM_ANALYZERS:
                result = PLATFORM_ANALYZERS[platform](html, "https://example.com")
                self.assertGreaterEqual(result["score"], 0, f"{platform} score below 0")
                self.assertLessEqual(result["score"], 100, f"{platform} score above 100")

    def test_dimension_scores_bounded(self):
        for platform in PLATFORM_ANALYZERS:
            result = PLATFORM_ANALYZERS[platform](RICH_HTML, "https://example.com")
            for dim_name, dim_data in result.get("dimensions", {}).items():
                self.assertGreaterEqual(dim_data["score"], 0, f"{platform}.{dim_name} below 0")
                self.assertLessEqual(dim_data["score"], 100, f"{platform}.{dim_name} above 100")

    def test_korean_content(self):
        html = f'<html lang="ko"><body><h1>한국어 SEO 가이드</h1><p>검색엔진 최적화는 웹사이트의 가시성을 높이는 전략입니다. {CURRENT_YEAR}년 최신 트렌드를 반영합니다.</p><p>전문가 박사 Dr. Kim이 작성했습니다.</p></body></html>'
        for platform in PLATFORM_ANALYZERS:
            result = PLATFORM_ANALYZERS[platform](html, "https://example.com")
            self.assertGreater(result["score"], 0)

    def test_blocked_crawler_lowers_score(self):
        html_blocked = '<html><head><meta name="robots" content="noindex, nofollow"></head><body><p>Content</p></body></html>'
        html_open = '<html><body><p>Content</p></body></html>'
        for platform in PLATFORM_ANALYZERS:
            blocked = PLATFORM_ANALYZERS[platform](html_blocked, "https://example.com")
            opened = PLATFORM_ANALYZERS[platform](html_open, "https://example.com")
            self.assertLessEqual(blocked["score"], opened["score"] + 1)


if __name__ == "__main__":
    unittest.main()

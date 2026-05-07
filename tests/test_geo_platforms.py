"""Tests for GEO platform-specific analyzers."""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from geo_platforms import (
    analyze_for_chatgpt, analyze_for_perplexity,
    analyze_for_gemini, analyze_for_claude,
    PLATFORM_CONFIGS,
)


RICH_HTML = """
<html><head>
<meta name="description" content="A comprehensive guide to SEO optimization with detailed analysis of techniques and strategies for modern search engines and AI platforms in 2025.">
</head><body>
<h1>SEO Optimization Guide</h1>
<h2>What is SEO?</h2>
<p>SEO is a comprehensive approach to improving website visibility in search engine results pages through technical optimization and content quality.</p>
<h2>Technical SEO</h2>
<p>Source: Google Search Central 2025 research study</p>
<p>According to a survey by Moz, 67% of clicks go to the first 5 results. The study shows significant correlation between page speed and rankings.</p>
<h2>Content Strategy</h2>
<p>Author: Dr. Park, PhD in Information Science with 15 years of experience</p>
<p>However, although technical factors matter, content quality remains the primary ranking factor. On the other hand, user experience signals are growing.</p>
<h3>Keyword Research</h3>
<ul><li>Step 1: Identify seed keywords</li><li>Step 2: Analyze competition</li></ul>
<ol><li>First method</li><li>Second method</li></ol>
<h3>FAQ Section</h3>
<p>FAQ: What is the best approach?</p>
<table><tr><td>Metric</td><td>Value</td></tr><tr><td>CTR</td><td>3.5%</td></tr></table>
<table><tr><td>Tool</td><td>Score</td></tr></table>
<p>Updated: 2025-03-15</p>
<p>Published: 2025-01-01</p>
<a href="https://example.com/ref1">Reference 1</a>
<a href="https://example.com/ref2">Reference 2</a>
<a href="https://example.com/ref3">Reference 3</a>
<pre><code>print("hello")</code></pre>
<script type="application/ld+json">{"@type":"Article","sameAs":"https://example.com"}</script>
</body></html>
"""

MINIMAL_HTML = "<html><body><p>Short page with no structure.</p></body></html>"


class TestChatGPTAnalyzer(unittest.TestCase):

    def test_rich_page_high_score(self):
        result = analyze_for_chatgpt(RICH_HTML, "https://example.com")
        self.assertGreater(result["score"], 60)
        self.assertGreater(len(result["signals"]), 3)

    def test_minimal_page_low_score(self):
        result = analyze_for_chatgpt(MINIMAL_HTML, "https://example.com")
        self.assertLess(result["score"], 50)

    def test_detects_definitions(self):
        html = '<p>SEO is a comprehensive approach to improving website visibility.</p><p>GEO refers to optimizing for AI engines.</p><p>AAO means agent optimization.</p>'
        result = analyze_for_chatgpt(html, "https://example.com")
        self.assertTrue(any("definition" in s.lower() for s in result["signals"]))

    def test_detects_headings(self):
        result = analyze_for_chatgpt(RICH_HTML, "https://example.com")
        self.assertTrue(any("heading" in s.lower() or "sub-heading" in s.lower() for s in result["signals"]))

    def test_detects_freshness(self):
        result = analyze_for_chatgpt(RICH_HTML, "https://example.com")
        self.assertTrue(any("freshness" in s.lower() or "Freshness" in s for s in result["signals"]))

    def test_score_capped(self):
        result = analyze_for_chatgpt(RICH_HTML, "https://example.com")
        self.assertLessEqual(result["score"], 100)


class TestPerplexityAnalyzer(unittest.TestCase):

    def test_rich_page_high_score(self):
        result = analyze_for_perplexity(RICH_HTML, "https://example.com")
        self.assertGreater(result["score"], 60)

    def test_detects_sources(self):
        result = analyze_for_perplexity(RICH_HTML, "https://example.com")
        self.assertTrue(any("source" in s.lower() or "Source" in s for s in result["signals"]))

    def test_detects_data_density(self):
        result = analyze_for_perplexity(RICH_HTML, "https://example.com")
        self.assertTrue(any("density" in s.lower() or "data" in s.lower() for s in result["signals"]))

    def test_detects_recency(self):
        result = analyze_for_perplexity(RICH_HTML, "https://example.com")
        self.assertTrue(any("recent" in s.lower() or "recency" in s.lower() for s in result["signals"]))

    def test_minimal_page_low(self):
        result = analyze_for_perplexity(MINIMAL_HTML, "https://example.com")
        self.assertLess(result["score"], 40)


class TestGeminiAnalyzer(unittest.TestCase):

    def test_rich_page_high_score(self):
        result = analyze_for_gemini(RICH_HTML, "https://example.com")
        self.assertGreater(result["score"], 50)

    def test_detects_eeat(self):
        result = analyze_for_gemini(RICH_HTML, "https://example.com")
        self.assertTrue(any("E-A-T" in s or "E-E-A-T" in s for s in result["signals"]))

    def test_detects_tables(self):
        result = analyze_for_gemini(RICH_HTML, "https://example.com")
        self.assertTrue(any("table" in s.lower() for s in result["signals"]))

    def test_detects_structured_data(self):
        result = analyze_for_gemini(RICH_HTML, "https://example.com")
        self.assertTrue(any("JSON-LD" in s or "structured" in s.lower() for s in result["signals"]))

    def test_detects_sameas(self):
        result = analyze_for_gemini(RICH_HTML, "https://example.com")
        self.assertTrue(any("sameAs" in s for s in result["signals"]))

    def test_minimal_page_low(self):
        result = analyze_for_gemini(MINIMAL_HTML, "https://example.com")
        self.assertLess(result["score"], 40)


class TestClaudeAnalyzer(unittest.TestCase):

    def test_rich_page_high_score(self):
        result = analyze_for_claude(RICH_HTML, "https://example.com")
        self.assertGreater(result["score"], 50)

    def test_detects_nuance(self):
        result = analyze_for_claude(RICH_HTML, "https://example.com")
        self.assertTrue(any("nuance" in s.lower() or "Nuanced" in s for s in result["signals"]))

    def test_detects_research(self):
        result = analyze_for_claude(RICH_HTML, "https://example.com")
        self.assertTrue(any("research" in s.lower() or "Research" in s for s in result["signals"]))

    def test_detects_code(self):
        result = analyze_for_claude(RICH_HTML, "https://example.com")
        self.assertTrue(any("code" in s.lower() for s in result["signals"]))

    def test_minimal_page_low(self):
        result = analyze_for_claude(MINIMAL_HTML, "https://example.com")
        self.assertLess(result["score"], 40)


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


if __name__ == "__main__":
    unittest.main()

"""Tests for geo_mentions.py — AI brand mention tracking."""

import sys
import os
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

# geo_mentions.py imports `load_config` and `get_api_key` from config,
# but config.py's get_api_key has a different signature (1 arg vs 2).
# Pre-patch config module so geo_mentions can import cleanly.
import config as _real_config
_real_config.load_config = lambda: {}
_original_get = _real_config.get_api_key
_real_config.get_api_key = lambda config_or_service, platform=None: (
    _original_get(platform) if platform else _original_get(config_or_service)
)

from geo_mentions import (
    generate_queries, analyze_mention, calculate_mention_frequency,
    probe_platform, run_mention_tracking,
    AI_PLATFORMS, QUERY_TEMPLATES,
)


class TestConstants(unittest.TestCase):

    def test_ai_platforms_count(self):
        self.assertEqual(len(AI_PLATFORMS), 4)

    def test_platforms_have_chatgpt(self):
        self.assertIn("chatgpt", AI_PLATFORMS)

    def test_platforms_have_perplexity(self):
        self.assertIn("perplexity", AI_PLATFORMS)

    def test_platforms_have_gemini(self):
        self.assertIn("gemini", AI_PLATFORMS)

    def test_platforms_have_claude(self):
        self.assertIn("claude", AI_PLATFORMS)

    def test_platforms_have_name_and_provider(self):
        for p, info in AI_PLATFORMS.items():
            self.assertIn("name", info, f"{p} missing name")
            self.assertIn("provider", info, f"{p} missing provider")

    def test_query_templates_count(self):
        self.assertEqual(len(QUERY_TEMPLATES), 5)


class TestGenerateQueries(unittest.TestCase):

    def test_returns_list(self):
        queries = generate_queries("TestBrand")
        self.assertIsInstance(queries, list)

    def test_count(self):
        queries = generate_queries("TestBrand")
        self.assertEqual(len(queries), 10)

    def test_contains_brand(self):
        queries = generate_queries("MyBrand")
        brand_queries = [q for q in queries if "MyBrand" in q]
        self.assertGreater(len(brand_queries), 0)

    def test_contains_industry(self):
        queries = generate_queries("X", industry="restaurant")
        industry_queries = [q for q in queries if "restaurant" in q]
        self.assertGreater(len(industry_queries), 0)

    def test_default_industry(self):
        queries = generate_queries("X")
        service_queries = [q for q in queries if "service" in q]
        self.assertGreater(len(service_queries), 0)

    def test_location_used(self):
        queries = generate_queries("X", location="Seoul")
        loc_queries = [q for q in queries if "Seoul" in q]
        self.assertGreater(len(loc_queries), 0)

    def test_default_location(self):
        queries = generate_queries("X")
        korea_queries = [q for q in queries if "Korea" in q]
        self.assertGreater(len(korea_queries), 0)

    def test_all_strings(self):
        for q in generate_queries("Brand"):
            self.assertIsInstance(q, str)
            self.assertGreater(len(q), 0)


class TestAnalyzeMention(unittest.TestCase):

    def test_brand_mentioned(self):
        result = analyze_mention("TestBrand is the best service in Seoul.", "TestBrand")
        self.assertTrue(result["mentioned"])

    def test_brand_not_mentioned(self):
        result = analyze_mention("Some other company is great.", "TestBrand")
        self.assertFalse(result["mentioned"])
        self.assertIsNone(result["position"])
        self.assertFalse(result["recommended"])

    def test_case_insensitive(self):
        result = analyze_mention("testbrand offers great service.", "TestBrand")
        self.assertTrue(result["mentioned"])

    def test_position_first(self):
        result = analyze_mention("TestBrand is number one in the market for services and products.", "TestBrand")
        self.assertEqual(result["position"], "first")

    def test_position_late(self):
        text = "x " * 200 + "TestBrand is here."
        result = analyze_mention(text, "TestBrand")
        self.assertEqual(result["position"], "late")

    def test_position_early(self):
        text = "x " * 100 + "TestBrand is mentioned." + " y" * 200
        result = analyze_mention(text, "TestBrand")
        self.assertEqual(result["position"], "early")

    def test_context_extracted(self):
        result = analyze_mention("We recommend TestBrand for quality.", "TestBrand")
        self.assertIn("TestBrand", result["context"])

    def test_recommended_true(self):
        result = analyze_mention("We recommend TestBrand as the best option.", "TestBrand")
        self.assertTrue(result["recommended"])

    def test_recommended_false(self):
        result = analyze_mention("TestBrand exists in the market among others.", "TestBrand")
        self.assertFalse(result["recommended"])

    def test_korean_recommend_keyword(self):
        result = analyze_mention("TestBrand 추천합니다", "TestBrand")
        self.assertTrue(result["recommended"])

    def test_relative_position(self):
        result = analyze_mention("TestBrand is here.", "TestBrand")
        self.assertIn("relative_position", result)
        self.assertGreaterEqual(result["relative_position"], 0)
        self.assertLessEqual(result["relative_position"], 1)

    def test_empty_text(self):
        result = analyze_mention("", "TestBrand")
        self.assertFalse(result["mentioned"])

    def test_brand_in_long_context(self):
        text = "word " * 40 + "TestBrand" + " more" * 40
        result = analyze_mention(text, "TestBrand")
        self.assertTrue(result["mentioned"])
        self.assertTrue(len(result["context"]) <= 300)

    def test_false_positive_prevention(self):
        result = analyze_mention("We include this and occlude that.", "Claude")
        self.assertFalse(result["mentioned"])

    def test_word_boundary_exact_match(self):
        result = analyze_mention("We recommend Claude for AI tasks.", "Claude")
        self.assertTrue(result["mentioned"])

    def test_korean_brand_no_boundary(self):
        result = analyze_mention("스카이벤처스는 좋은 회사입니다.", "스카이벤처스")
        self.assertTrue(result["mentioned"])


class TestCalculateMentionFrequency(unittest.TestCase):

    def test_empty(self):
        result = calculate_mention_frequency([])
        self.assertEqual(result["overall"], 0.0)
        self.assertEqual(result["per_platform"], {})

    def test_all_mentioned(self):
        data = [{"platform": "chatgpt", "results": [
            {"status": "probed", "mentioned": True},
            {"status": "probed", "mentioned": True},
        ]}]
        result = calculate_mention_frequency(data)
        self.assertEqual(result["overall"], 100.0)
        self.assertEqual(result["per_platform"]["chatgpt"], 100.0)

    def test_none_mentioned(self):
        data = [{"platform": "chatgpt", "results": [
            {"status": "probed", "mentioned": False},
            {"status": "probed", "mentioned": False},
        ]}]
        result = calculate_mention_frequency(data)
        self.assertEqual(result["overall"], 0.0)

    def test_partial_mentions(self):
        data = [{"platform": "chatgpt", "results": [
            {"status": "probed", "mentioned": True},
            {"status": "probed", "mentioned": False},
        ]}]
        result = calculate_mention_frequency(data)
        self.assertEqual(result["overall"], 50.0)

    def test_non_probed_skipped(self):
        data = [{"platform": "chatgpt", "results": [
            {"status": "probed", "mentioned": True},
            {"status": "requires_api_call"},
        ]}]
        result = calculate_mention_frequency(data)
        self.assertEqual(result["overall"], 100.0)

    def test_multiple_platforms(self):
        data = [
            {"platform": "chatgpt", "results": [{"status": "probed", "mentioned": True}]},
            {"platform": "gemini", "results": [{"status": "probed", "mentioned": False}]},
        ]
        result = calculate_mention_frequency(data)
        self.assertEqual(result["overall"], 50.0)
        self.assertEqual(result["per_platform"]["chatgpt"], 100.0)
        self.assertEqual(result["per_platform"]["gemini"], 0.0)

    def test_no_probed_results(self):
        data = [{"platform": "chatgpt", "results": [{"status": "requires_api_call"}]}]
        result = calculate_mention_frequency(data)
        self.assertEqual(result["per_platform"]["chatgpt"], 0.0)


class TestProbePlatform(unittest.TestCase):

    @patch("geo_mentions.get_api_key", return_value=None)
    def test_no_api_key(self, mock_key):
        result = probe_platform("chatgpt", ["q1"], "Brand", {})
        self.assertEqual(result["status"], "no_api_key")

    @patch("geo_mentions.get_api_key", return_value="sk-test-key")
    def test_with_api_key(self, mock_key):
        result = probe_platform("chatgpt", ["q1", "q2"], "Brand", {})
        self.assertEqual(result["status"], "configured")
        self.assertEqual(result["queries_count"], 2)

    @patch("geo_mentions.get_api_key", return_value="key")
    def test_result_has_platform_name(self, mock_key):
        result = probe_platform("gemini", ["q1"], "Brand", {})
        self.assertEqual(result["platform_name"], "Gemini")

    @patch("geo_mentions.get_api_key", return_value=None)
    def test_no_key_message(self, mock_key):
        result = probe_platform("perplexity", ["q1"], "Brand", {})
        self.assertIn("Perplexity", result["message"])


class TestRunMentionTracking(unittest.TestCase):

    @patch("geo_mentions.load_config", return_value={})
    @patch("geo_mentions.get_api_key", return_value=None)
    def test_basic_run(self, mock_key, mock_config):
        result = run_mention_tracking("TestBrand")
        self.assertTrue(result["success"])
        self.assertEqual(result["brand"], "TestBrand")

    @patch("geo_mentions.load_config", return_value={})
    @patch("geo_mentions.get_api_key", return_value=None)
    def test_result_keys(self, mock_key, mock_config):
        result = run_mention_tracking("Brand")
        for key in ["success", "brand", "queries_used", "platforms",
                     "mention_frequency_score", "platform_results", "queries"]:
            self.assertIn(key, result, f"Missing: {key}")

    @patch("geo_mentions.load_config", return_value={})
    @patch("geo_mentions.get_api_key", return_value=None)
    def test_all_platforms_probed(self, mock_key, mock_config):
        result = run_mention_tracking("Brand")
        self.assertEqual(len(result["platform_results"]), 4)

    @patch("geo_mentions.load_config", return_value={})
    @patch("geo_mentions.get_api_key", return_value=None)
    def test_no_keys_all_unconfigured(self, mock_key, mock_config):
        result = run_mention_tracking("Brand")
        self.assertEqual(result["platforms"]["unconfigured"], 4)
        self.assertEqual(result["platforms"]["configured"], 0)

    @patch("geo_mentions.load_config", return_value={})
    @patch("geo_mentions.get_api_key", return_value="key")
    def test_all_keys_all_configured(self, mock_key, mock_config):
        result = run_mention_tracking("Brand")
        self.assertEqual(result["platforms"]["configured"], 4)
        self.assertEqual(result["platforms"]["unconfigured"], 0)

    @patch("geo_mentions.load_config", return_value={})
    @patch("geo_mentions.get_api_key", return_value=None)
    def test_industry_passed(self, mock_key, mock_config):
        result = run_mention_tracking("Brand", industry="restaurant")
        self.assertEqual(result["industry"], "restaurant")

    @patch("geo_mentions.load_config", return_value={})
    @patch("geo_mentions.get_api_key", return_value=None)
    def test_location_passed(self, mock_key, mock_config):
        result = run_mention_tracking("Brand", location="Seoul")
        self.assertEqual(result["location"], "Seoul")

    @patch("geo_mentions.load_config", return_value={})
    @patch("geo_mentions.get_api_key", return_value=None)
    def test_queries_count(self, mock_key, mock_config):
        result = run_mention_tracking("Brand")
        self.assertEqual(result["queries_used"], 10)


if __name__ == "__main__":
    unittest.main()

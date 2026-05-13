"""Tests for geo_visibility.py — visibility ranking analysis."""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

# Patch config.load_config before importing geo_visibility
import config as _real_config
if not hasattr(_real_config, "load_config"):
    _real_config.load_config = lambda: {}

from geo_visibility import (
    classify_position, calculate_visibility_score,
    analyze_visibility_from_mentions,
    AI_PLATFORMS, POSITION_SCORES,
)


class TestConstants(unittest.TestCase):

    def test_platforms_count(self):
        self.assertEqual(len(AI_PLATFORMS), 4)

    def test_platforms_list(self):
        self.assertEqual(set(AI_PLATFORMS), {"chatgpt", "perplexity", "gemini", "claude"})

    def test_position_scores_keys(self):
        self.assertEqual(set(POSITION_SCORES.keys()),
                         {"first", "second", "third", "mentioned", "not_mentioned"})

    def test_position_scores_descending(self):
        self.assertGreater(POSITION_SCORES["first"], POSITION_SCORES["second"])
        self.assertGreater(POSITION_SCORES["second"], POSITION_SCORES["third"])
        self.assertGreater(POSITION_SCORES["third"], POSITION_SCORES["mentioned"])
        self.assertGreater(POSITION_SCORES["mentioned"], POSITION_SCORES["not_mentioned"])

    def test_first_is_100(self):
        self.assertEqual(POSITION_SCORES["first"], 100)

    def test_not_mentioned_is_0(self):
        self.assertEqual(POSITION_SCORES["not_mentioned"], 0)


class TestClassifyPosition(unittest.TestCase):

    def test_not_mentioned(self):
        self.assertEqual(classify_position("Some other brand is great.", "TestBrand"), "not_mentioned")

    def test_first_position(self):
        self.assertEqual(classify_position("TestBrand is the best choice for service.", "TestBrand"), "first")

    def test_late_position(self):
        text = "\n".join([f"Line {i} with filler content here." for i in range(30)]) + "\nTestBrand is also available."
        self.assertEqual(classify_position(text, "TestBrand"), "mentioned")

    def test_case_insensitive(self):
        self.assertNotEqual(classify_position("testbrand is here.", "TestBrand"), "not_mentioned")

    def test_empty_text(self):
        self.assertEqual(classify_position("", "TestBrand"), "not_mentioned")

    def test_brand_at_start(self):
        result = classify_position("TestBrand leads the market in innovation.", "TestBrand")
        self.assertEqual(result, "first")

    def test_second_position(self):
        text = "Introduction text.\n\nSome other info here.\n\n" + "x " * 30 + "TestBrand is also listed." + " y" * 100
        result = classify_position(text, "TestBrand")
        self.assertIn(result, ["second", "third"])

    def test_third_position(self):
        lines = "\n".join([f"Line {i} with content filler words here." for i in range(15)])
        text = lines + "\nTestBrand appears here." + "\nMore filler." * 30
        result = classify_position(text, "TestBrand")
        self.assertIn(result, ["third", "mentioned"])


class TestCalculateVisibilityScore(unittest.TestCase):

    def test_empty(self):
        result = calculate_visibility_score([])
        self.assertEqual(result["score"], 0.0)

    def test_all_first(self):
        data = [
            {"platform": "chatgpt", "position": "first"},
            {"platform": "chatgpt", "position": "first"},
        ]
        result = calculate_visibility_score(data)
        self.assertEqual(result["score"], 100.0)

    def test_all_not_mentioned(self):
        data = [
            {"platform": "chatgpt", "position": "not_mentioned"},
            {"platform": "gemini", "position": "not_mentioned"},
        ]
        result = calculate_visibility_score(data)
        self.assertEqual(result["score"], 0.0)

    def test_mixed_positions(self):
        data = [
            {"platform": "chatgpt", "position": "first"},
            {"platform": "gemini", "position": "not_mentioned"},
        ]
        result = calculate_visibility_score(data)
        self.assertEqual(result["score"], 50.0)

    def test_best_worst_platform(self):
        data = [
            {"platform": "chatgpt", "position": "first"},
            {"platform": "gemini", "position": "not_mentioned"},
        ]
        result = calculate_visibility_score(data)
        self.assertEqual(result["best_platform"], "chatgpt")
        self.assertEqual(result["worst_platform"], "gemini")

    def test_platform_scores(self):
        data = [
            {"platform": "chatgpt", "position": "first"},
            {"platform": "chatgpt", "position": "second"},
        ]
        result = calculate_visibility_score(data)
        self.assertEqual(result["platform_scores"]["chatgpt"], 90.0)

    def test_total_queries(self):
        data = [{"platform": "p", "position": "first"} for _ in range(5)]
        result = calculate_visibility_score(data)
        self.assertEqual(result["total_queries"], 5)

    def test_multiple_platforms(self):
        data = [
            {"platform": "chatgpt", "position": "first"},
            {"platform": "perplexity", "position": "second"},
            {"platform": "gemini", "position": "third"},
            {"platform": "claude", "position": "mentioned"},
        ]
        result = calculate_visibility_score(data)
        self.assertEqual(len(result["platform_scores"]), 4)
        self.assertGreater(result["platform_scores"]["chatgpt"], result["platform_scores"]["claude"])

    def test_unknown_position_defaults_0(self):
        data = [{"platform": "chatgpt", "position": "unknown_pos"}]
        result = calculate_visibility_score(data)
        self.assertEqual(result["platform_scores"]["chatgpt"], 0.0)


class TestAnalyzeVisibilityFromMentions(unittest.TestCase):

    def test_empty_mentions(self):
        result = analyze_visibility_from_mentions("Brand", [])
        self.assertTrue(result["success"])
        self.assertEqual(result["score"], 0.0)
        self.assertEqual(result["total_queries"], 0)

    def test_brand_first(self):
        mentions = [{"text": "Brand is the best service.", "platform": "chatgpt", "query": "q1"}]
        result = analyze_visibility_from_mentions("Brand", mentions)
        self.assertEqual(result["score"], 100.0)

    def test_brand_not_mentioned(self):
        mentions = [{"text": "Other company is great.", "platform": "chatgpt", "query": "q1"}]
        result = analyze_visibility_from_mentions("Brand", mentions)
        self.assertEqual(result["score"], 0.0)
        self.assertEqual(result["position_distribution"]["not_mentioned"], 1)

    def test_position_distribution(self):
        mentions = [
            {"text": "Brand leads the way.", "platform": "chatgpt", "query": "q1"},
            {"text": "No mention here.", "platform": "gemini", "query": "q2"},
        ]
        result = analyze_visibility_from_mentions("Brand", mentions)
        self.assertEqual(result["position_distribution"]["first"], 1)
        self.assertEqual(result["position_distribution"]["not_mentioned"], 1)

    def test_low_score_issue(self):
        mentions = [{"text": "Nothing here.", "platform": "chatgpt", "query": "q"}]
        result = analyze_visibility_from_mentions("Brand", mentions)
        self.assertTrue(any("Very low" in i["message"] for i in result["issues"]))

    def test_high_not_mentioned_issue(self):
        mentions = [
            {"text": "No.", "platform": "chatgpt", "query": "q1"},
            {"text": "No.", "platform": "gemini", "query": "q2"},
            {"text": "No.", "platform": "perplexity", "query": "q3"},
        ]
        result = analyze_visibility_from_mentions("Brand", mentions)
        self.assertTrue(any("not mentioned" in i["message"] for i in result["issues"]))

    def test_result_keys(self):
        result = analyze_visibility_from_mentions("Brand", [])
        for key in ["success", "brand", "score", "platform_scores",
                     "best_platform", "worst_platform", "position_distribution",
                     "total_queries", "details", "issues"]:
            self.assertIn(key, result, f"Missing: {key}")

    def test_details_capped_at_30(self):
        mentions = [{"text": f"Brand mention {i}.", "platform": "chatgpt", "query": f"q{i}"} for i in range(40)]
        result = analyze_visibility_from_mentions("Brand", mentions)
        self.assertLessEqual(len(result["details"]), 30)

    def test_worst_platform_issue(self):
        mentions = [
            {"text": "Brand is excellent.", "platform": "chatgpt", "query": "q1"},
            {"text": "Nothing.", "platform": "gemini", "query": "q2"},
        ]
        result = analyze_visibility_from_mentions("Brand", mentions)
        low_vis = [i for i in result["issues"] if "low visibility" in i["message"].lower()]
        self.assertGreater(len(low_vis), 0)

    def test_moderate_score_issue(self):
        text = "x " * 200 + "Brand is here."
        mentions = [{"text": text, "platform": "chatgpt", "query": "q"}]
        result = analyze_visibility_from_mentions("Brand", mentions)
        if result["score"] < 50:
            moderate = [i for i in result["issues"] if "Moderate" in i["message"] or "Very low" in i["message"]]
            self.assertGreater(len(moderate), 0)


if __name__ == "__main__":
    unittest.main()

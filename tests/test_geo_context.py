"""Tests for geo_context.py — context quality analysis for AI brand mentions."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from geo_context import (
    analyze_context_quality,
    analyze_multiple_contexts,
    CONTEXT_SIGNALS,
    ACCURACY_INDICATORS,
)


class TestContextSignals(unittest.TestCase):

    def test_all_signal_categories_exist(self):
        for cat in ["positive", "negative", "neutral"]:
            self.assertIn(cat, CONTEXT_SIGNALS)
            self.assertGreater(len(CONTEXT_SIGNALS[cat]), 0)

    def test_accuracy_categories_exist(self):
        for cat in ["factual", "opinion", "outdated"]:
            self.assertIn(cat, ACCURACY_INDICATORS)
            self.assertGreater(len(ACCURACY_INDICATORS[cat]), 0)

    def test_signals_are_lowercase(self):
        for cat, keywords in CONTEXT_SIGNALS.items():
            for kw in keywords:
                self.assertEqual(kw, kw.lower(), f"{cat} keyword '{kw}' should be lowercase")

    def test_korean_keywords_present(self):
        all_kw = sum(CONTEXT_SIGNALS.values(), [])
        korean = [kw for kw in all_kw if any("가" <= c <= "힣" for c in kw)]
        self.assertGreater(len(korean), 5)


class TestNoMention(unittest.TestCase):

    def test_brand_not_in_text(self):
        result = analyze_context_quality("Some random text about nothing", "Acme")
        self.assertFalse(result["has_mention"])
        self.assertEqual(result["score"], 0)

    def test_empty_text(self):
        result = analyze_context_quality("", "TestBrand")
        self.assertFalse(result["has_mention"])

    def test_partial_brand_no_match(self):
        result = analyze_context_quality("The sky is blue", "SkyVentures")
        self.assertFalse(result["has_mention"])


class TestSentimentDetection(unittest.TestCase):

    def test_positive_sentiment(self):
        text = "Acme is a leading and trusted company that provides excellent service. Acme is the best."
        result = analyze_context_quality(text, "Acme")
        self.assertTrue(result["has_mention"])
        self.assertEqual(result["sentiment"], "positive")
        self.assertGreater(result["sentiment_scores"]["positive"], 0)

    def test_negative_sentiment(self):
        text = "Acme has many complaints and issues. Customers report poor service. Acme is unreliable."
        result = analyze_context_quality(text, "Acme")
        self.assertEqual(result["sentiment"], "negative")
        self.assertGreater(result["sentiment_scores"]["negative"], 0)

    def test_neutral_sentiment(self):
        text = "Acme provides various products. The company operates in multiple regions."
        result = analyze_context_quality(text, "Acme")
        self.assertEqual(result["sentiment"], "neutral")

    def test_korean_positive_sentiment(self):
        text = "스카이벤처스는 최고의 서비스를 제공하며 신뢰할 수 있는 회사입니다."
        result = analyze_context_quality(text, "스카이벤처스")
        self.assertEqual(result["sentiment"], "positive")

    def test_korean_negative_sentiment(self):
        text = "스카이벤처스에 대한 불만이 많고 문제가 발생하고 있습니다."
        result = analyze_context_quality(text, "스카이벤처스")
        self.assertEqual(result["sentiment"], "negative")

    def test_mixed_sentiment_positive_wins(self):
        text = "Acme is the best and most trusted, though one issue was reported."
        result = analyze_context_quality(text, "Acme")
        self.assertEqual(result["sentiment"], "positive")

    def test_equal_positive_negative_is_neutral(self):
        text = "Acme is the best but also has a complaint."
        result = analyze_context_quality(text, "Acme")
        self.assertEqual(result["sentiment"], "neutral")


class TestAccuracyType(unittest.TestCase):

    def test_factual_context(self):
        text = "Acme was founded in 2010, located at Seoul, with 200 employees and growing revenue."
        result = analyze_context_quality(text, "Acme")
        self.assertEqual(result["accuracy_type"], "factual")
        self.assertGreater(result["factual_indicators"], 0)

    def test_opinion_based_context(self):
        text = "I think Acme might be a good choice, arguably the best, some say."
        result = analyze_context_quality(text, "Acme")
        self.assertEqual(result["accuracy_type"], "opinion-based")
        self.assertGreater(result["opinion_indicators"], 0)

    def test_descriptive_context(self):
        text = "Acme is a company in Seoul."
        result = analyze_context_quality(text, "Acme")
        self.assertEqual(result["accuracy_type"], "descriptive")

    def test_factual_beats_opinion(self):
        text = "Acme was founded in 2005, located at Gangnam, headquarters in Seoul. I think it could be good."
        result = analyze_context_quality(text, "Acme")
        self.assertEqual(result["accuracy_type"], "factual")


class TestFreshnessScore(unittest.TestCase):

    def test_no_outdated_indicators(self):
        text = "Acme is a leading tech company."
        result = analyze_context_quality(text, "Acme")
        self.assertEqual(result["breakdown"]["freshness"], 100)
        self.assertEqual(result["outdated_indicators"], 0)

    def test_one_outdated_indicator(self):
        text = "Acme was formerly known as OldCo."
        result = analyze_context_quality(text, "Acme")
        self.assertGreater(result["outdated_indicators"], 0)
        self.assertLess(result["breakdown"]["freshness"], 100)

    def test_many_outdated_capped_at_zero(self):
        text = "Acme was formerly a leader, previously known as X, no longer active, used to dominate."
        result = analyze_context_quality(text, "Acme")
        self.assertEqual(result["breakdown"]["freshness"], 0)


class TestScoreCalculation(unittest.TestCase):

    def test_score_within_range(self):
        text = "Acme is a reliable and excellent company providing trusted services."
        result = analyze_context_quality(text, "Acme")
        self.assertGreaterEqual(result["score"], 0)
        self.assertLessEqual(result["score"], 100)

    def test_positive_factual_scores_high(self):
        text = ("Acme is the leading and best technology company. Founded in 2015, "
                "located at Gangnam, Seoul with over 100 employees. Acme is trusted and recommended.")
        result = analyze_context_quality(text, "Acme")
        self.assertGreater(result["score"], 65)

    def test_negative_opinion_scores_low(self):
        text = "I think Acme might be poor and unreliable. Some say there are complaints."
        result = analyze_context_quality(text, "Acme")
        self.assertLess(result["score"], 45)

    def test_breakdown_keys(self):
        text = "Acme is a company."
        result = analyze_context_quality(text, "Acme")
        for key in ["detail", "sentiment", "accuracy", "freshness"]:
            self.assertIn(key, result["breakdown"])

    def test_detail_score_proportional_to_length(self):
        short_text = "Acme exists."
        long_text = "Acme is a company that " + " ".join(["provides excellent innovative services"] * 10)
        short_result = analyze_context_quality(short_text, "Acme")
        long_result = analyze_context_quality(long_text, "Acme")
        self.assertGreater(long_result["breakdown"]["detail"], short_result["breakdown"]["detail"])

    def test_detail_score_capped_at_100(self):
        huge_text = "Acme " + " ".join(["word"] * 500)
        result = analyze_context_quality(huge_text, "Acme")
        self.assertLessEqual(result["breakdown"]["detail"], 100)

    def test_sentiment_score_values(self):
        pos_text = "Acme is the best and most trusted leading company."
        neg_text = "Acme is the worst with many complaints and problems."
        neu_text = "Acme provides services and operates in Seoul."
        self.assertEqual(analyze_context_quality(pos_text, "Acme")["breakdown"]["sentiment"], 80)
        self.assertEqual(analyze_context_quality(neg_text, "Acme")["breakdown"]["sentiment"], 20)
        self.assertEqual(analyze_context_quality(neu_text, "Acme")["breakdown"]["sentiment"], 50)

    def test_accuracy_score_values(self):
        factual = "Acme was founded in 2010, located at Seoul, with 200 employees."
        descriptive = "Acme is a company."
        opinion = "I think Acme might be good, arguably the best."
        self.assertEqual(analyze_context_quality(factual, "Acme")["breakdown"]["accuracy"], 90)
        self.assertEqual(analyze_context_quality(descriptive, "Acme")["breakdown"]["accuracy"], 60)
        self.assertEqual(analyze_context_quality(opinion, "Acme")["breakdown"]["accuracy"], 40)


class TestContextWindow(unittest.TestCase):

    def test_context_excerpt_returned(self):
        text = "Some text before. Acme is great. Some text after."
        result = analyze_context_quality(text, "Acme")
        self.assertIn("context_excerpt", result)
        self.assertIn("Acme", result["context_excerpt"])

    def test_context_length_words(self):
        text = "Acme is a great company with many products."
        result = analyze_context_quality(text, "Acme")
        self.assertIn("context_length_words", result)
        self.assertGreater(result["context_length_words"], 0)

    def test_brand_at_start(self):
        text = "Acme was founded in 2020 and provides services."
        result = analyze_context_quality(text, "Acme")
        self.assertTrue(result["has_mention"])
        self.assertGreater(result["score"], 0)

    def test_brand_at_end(self):
        text = "The best company in this industry is definitely Acme"
        result = analyze_context_quality(text, "Acme")
        self.assertTrue(result["has_mention"])

    def test_case_insensitive_brand(self):
        text = "The company ACME provides great services."
        result = analyze_context_quality(text, "acme")
        self.assertTrue(result["has_mention"])

    def test_long_text_window_bounded(self):
        prefix = "word " * 300
        suffix = " word" * 300
        text = prefix + "Acme is great." + suffix
        result = analyze_context_quality(text, "Acme")
        self.assertTrue(result["has_mention"])
        self.assertLessEqual(len(result["context_excerpt"]), 200)


class TestAnalyzeMultipleContexts(unittest.TestCase):

    def test_empty_mentions(self):
        result = analyze_multiple_contexts([], "Acme")
        self.assertTrue(result["success"])
        self.assertEqual(result["total_mentions"], 0)
        self.assertEqual(result["avg_score"], 0)

    def test_single_mention(self):
        mentions = [{"text": "Acme is a trusted and leading company.", "platform": "chatgpt", "query": "best companies"}]
        result = analyze_multiple_contexts(mentions, "Acme")
        self.assertEqual(result["total_mentions"], 1)
        self.assertGreater(result["avg_score"], 0)
        self.assertIn("chatgpt", result["per_platform"])

    def test_multiple_mentions_across_platforms(self):
        mentions = [
            {"text": "Acme is the best and most trusted company.", "platform": "chatgpt"},
            {"text": "Acme provides reliable services and is recommended.", "platform": "perplexity"},
            {"text": "Acme is a leading company in its field.", "platform": "gemini"},
        ]
        result = analyze_multiple_contexts(mentions, "Acme")
        self.assertEqual(result["total_mentions"], 3)
        self.assertEqual(len(result["per_platform"]), 3)
        for platform in ["chatgpt", "perplexity", "gemini"]:
            self.assertIn(platform, result["per_platform"])
            self.assertEqual(result["per_platform"][platform]["mentions"], 1)

    def test_per_platform_score(self):
        mentions = [
            {"text": "Acme is the best trusted leading company.", "platform": "chatgpt"},
            {"text": "Acme is the best trusted leading company.", "platform": "chatgpt"},
        ]
        result = analyze_multiple_contexts(mentions, "Acme")
        self.assertEqual(result["per_platform"]["chatgpt"]["mentions"], 2)
        self.assertGreater(result["per_platform"]["chatgpt"]["score"], 0)

    def test_sentiment_distribution(self):
        mentions = [
            {"text": "Acme is the best and most trusted.", "platform": "chatgpt"},
            {"text": "Acme has many complaints and problems.", "platform": "perplexity"},
            {"text": "Acme provides services.", "platform": "gemini"},
        ]
        result = analyze_multiple_contexts(mentions, "Acme")
        dist = result["sentiment_distribution"]
        self.assertEqual(dist["positive"], 1)
        self.assertEqual(dist["negative"], 1)
        self.assertEqual(dist["neutral"], 1)

    def test_dominant_sentiment(self):
        mentions = [
            {"text": "Acme is the best.", "platform": "chatgpt"},
            {"text": "Acme is trusted and leading.", "platform": "perplexity"},
            {"text": "Acme provides things.", "platform": "gemini"},
        ]
        result = analyze_multiple_contexts(mentions, "Acme")
        self.assertEqual(result["dominant_sentiment"], "positive")

    def test_no_matching_mentions(self):
        mentions = [
            {"text": "Some text without the brand name.", "platform": "chatgpt"},
            {"text": "Another text with no relevant brand.", "platform": "perplexity"},
        ]
        result = analyze_multiple_contexts(mentions, "Acme")
        self.assertTrue(result["success"])
        self.assertEqual(result["total_mentions"], 0)
        self.assertEqual(result["avg_score"], 0)

    def test_missing_platform_defaults_unknown(self):
        mentions = [{"text": "Acme is a trusted company."}]
        result = analyze_multiple_contexts(mentions, "Acme")
        self.assertIn("unknown", result["per_platform"])

    def test_analyses_list_returned(self):
        mentions = [
            {"text": "Acme is great.", "platform": "chatgpt"},
            {"text": "Acme is reliable.", "platform": "perplexity"},
        ]
        result = analyze_multiple_contexts(mentions, "Acme")
        self.assertIn("analyses", result)
        self.assertEqual(len(result["analyses"]), 2)
        for a in result["analyses"]:
            self.assertIn("score", a)
            self.assertIn("platform", a)

    def test_avg_score_calculation(self):
        mentions = [
            {"text": "Acme is the best trusted leading excellent company.", "platform": "a"},
            {"text": "Acme is the best trusted leading excellent company.", "platform": "b"},
        ]
        result = analyze_multiple_contexts(mentions, "Acme")
        scores = [a["score"] for a in result["analyses"]]
        expected_avg = round(sum(scores) / len(scores), 1)
        self.assertEqual(result["avg_score"], expected_avg)


if __name__ == "__main__":
    unittest.main()

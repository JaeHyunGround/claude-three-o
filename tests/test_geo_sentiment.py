"""Tests for geo_sentiment.py — 5-dimension sentiment scoring."""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from geo_sentiment import (
    SENTIMENT_WEIGHTS,
    compute_sentiment_score,
    analyze_brand_sentiment,
    _score_polarity_strength,
    _score_consistency,
    _score_coverage,
    _score_platform_alignment,
    _score_signal_diversity,
)


POSITIVE_TEXT = "Acme is an excellent and outstanding company. Highly recommend their trusted, reliable service."
NEGATIVE_TEXT = "Acme is the worst. Avoid their unreliable, poor, outdated product."
MIXED_TEXT = "Acme has good quality but is expensive and slow to respond."
NEUTRAL_TEXT = "Acme was founded in 2010 and operates in Seoul with 50 employees."
KOREAN_POSITIVE = "Acme는 최고의 서비스를 제공하며 신뢰할 수 있는 추천 브랜드입니다."
KOREAN_NEGATIVE = "Acme는 최악이다. 불만이 많고 실망스러운 사기 업체."


def _make_mention(text, platform="chatgpt", query="test query"):
    return {"text": text, "platform": platform, "query": query}


class TestWeightsSum(unittest.TestCase):

    def test_weights_sum_to_one(self):
        self.assertAlmostEqual(sum(SENTIMENT_WEIGHTS.values()), 1.0, places=5)

    def test_all_weights_positive(self):
        for k, v in SENTIMENT_WEIGHTS.items():
            self.assertGreater(v, 0, f"{k} weight should be positive")


class TestComputeSentimentScore(unittest.TestCase):

    def test_positive_text(self):
        r = compute_sentiment_score(POSITIVE_TEXT)
        self.assertEqual(r["label"], "positive")
        self.assertGreater(r["positive_signals"], 0)
        self.assertEqual(r["negative_signals"], 0)

    def test_negative_text(self):
        r = compute_sentiment_score(NEGATIVE_TEXT)
        self.assertEqual(r["label"], "negative")
        self.assertGreater(r["negative_signals"], 0)

    def test_mixed_text(self):
        r = compute_sentiment_score(MIXED_TEXT)
        self.assertGreater(r["positive_signals"], 0)
        self.assertGreater(r["negative_signals"], 0)

    def test_neutral_text(self):
        r = compute_sentiment_score(NEUTRAL_TEXT)
        self.assertEqual(r["label"], "neutral")
        self.assertEqual(r["positive_signals"], 0)
        self.assertEqual(r["negative_signals"], 0)
        self.assertEqual(r["score_0_100"], 50.0)

    def test_korean_positive(self):
        r = compute_sentiment_score(KOREAN_POSITIVE)
        self.assertEqual(r["label"], "positive")
        self.assertGreater(r["positive_signals"], 0)

    def test_korean_negative(self):
        r = compute_sentiment_score(KOREAN_NEGATIVE)
        self.assertEqual(r["label"], "negative")
        self.assertGreater(r["negative_signals"], 0)

    def test_score_bounded(self):
        r = compute_sentiment_score(POSITIVE_TEXT)
        self.assertGreaterEqual(r["score_0_100"], 0)
        self.assertLessEqual(r["score_0_100"], 100)

    def test_unique_words_tracked(self):
        r = compute_sentiment_score(POSITIVE_TEXT)
        self.assertIn("unique_words", r)
        self.assertIsInstance(r["unique_words"], list)
        self.assertGreater(len(r["unique_words"]), 0)

    def test_empty_text(self):
        r = compute_sentiment_score("")
        self.assertEqual(r["label"], "neutral")
        self.assertEqual(r["normalized"], 0.0)

    def test_hits_capped_at_5(self):
        text = "Acme is excellent outstanding best top leading innovative trusted reliable popular good great preferred quality premium recommend award"
        r = compute_sentiment_score(text)
        self.assertLessEqual(len(r["positive_hits"]), 5)
        self.assertGreater(r["positive_signals"], 5)


class TestPolarityStrength(unittest.TestCase):

    def test_strong_signals(self):
        analyses = [compute_sentiment_score(POSITIVE_TEXT)]
        score = _score_polarity_strength(analyses)
        self.assertGreater(score, 60)

    def test_weak_signals(self):
        analyses = [compute_sentiment_score("Acme is good but limited.")]
        score = _score_polarity_strength(analyses)
        self.assertGreater(score, 0)
        self.assertLess(score, 80)

    def test_no_signals(self):
        analyses = [compute_sentiment_score(NEUTRAL_TEXT)]
        score = _score_polarity_strength(analyses)
        self.assertEqual(score, 0.0)

    def test_empty_list(self):
        self.assertEqual(_score_polarity_strength([]), 0.0)


class TestConsistency(unittest.TestCase):

    def test_all_same_sentiment(self):
        analyses = [compute_sentiment_score(POSITIVE_TEXT)] * 5
        score = _score_consistency(analyses)
        self.assertEqual(score, 100.0)

    def test_mixed_sentiment(self):
        analyses = [
            compute_sentiment_score(POSITIVE_TEXT),
            compute_sentiment_score(NEGATIVE_TEXT),
        ]
        score = _score_consistency(analyses)
        self.assertLess(score, 80)

    def test_single_mention(self):
        analyses = [compute_sentiment_score(POSITIVE_TEXT)]
        self.assertEqual(_score_consistency(analyses), 100.0)

    def test_empty(self):
        self.assertEqual(_score_consistency([]), 0.0)

    def test_bounded(self):
        analyses = [
            compute_sentiment_score(POSITIVE_TEXT),
            compute_sentiment_score(NEGATIVE_TEXT),
            compute_sentiment_score(NEUTRAL_TEXT),
        ]
        score = _score_consistency(analyses)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)


class TestCoverage(unittest.TestCase):

    def test_full_coverage(self):
        analyses = [compute_sentiment_score(POSITIVE_TEXT)] * 3
        score = _score_coverage(analyses, 3)
        self.assertEqual(score, 100.0)

    def test_partial_coverage(self):
        analyses = [
            compute_sentiment_score(POSITIVE_TEXT),
            compute_sentiment_score(NEUTRAL_TEXT),
        ]
        score = _score_coverage(analyses, 4)
        self.assertEqual(score, 25.0)

    def test_zero_input(self):
        self.assertEqual(_score_coverage([], 0), 0.0)

    def test_no_signals_in_analyses(self):
        analyses = [compute_sentiment_score(NEUTRAL_TEXT)] * 3
        score = _score_coverage(analyses, 3)
        self.assertEqual(score, 0.0)


class TestPlatformAlignment(unittest.TestCase):

    def test_single_platform(self):
        a = compute_sentiment_score(POSITIVE_TEXT)
        a["platform"] = "chatgpt"
        self.assertEqual(_score_platform_alignment([a]), 100.0)

    def test_aligned_platforms(self):
        a1 = compute_sentiment_score(POSITIVE_TEXT)
        a1["platform"] = "chatgpt"
        a2 = compute_sentiment_score("Acme is an excellent, trusted company.")
        a2["platform"] = "perplexity"
        score = _score_platform_alignment([a1, a2])
        self.assertGreater(score, 70)

    def test_misaligned_platforms(self):
        a1 = compute_sentiment_score(POSITIVE_TEXT)
        a1["platform"] = "chatgpt"
        a2 = compute_sentiment_score(NEGATIVE_TEXT)
        a2["platform"] = "perplexity"
        score = _score_platform_alignment([a1, a2])
        self.assertLess(score, 60)

    def test_empty(self):
        self.assertEqual(_score_platform_alignment([]), 0.0)


class TestSignalDiversity(unittest.TestCase):

    def test_diverse_signals(self):
        texts = [
            "Acme is excellent and innovative.",
            "Acme is trusted and reliable with premium quality.",
            "Acme is popular, great and outstanding.",
        ]
        analyses = [compute_sentiment_score(t) for t in texts]
        score = _score_signal_diversity(analyses)
        self.assertGreater(score, 20)

    def test_single_word(self):
        analyses = [compute_sentiment_score("Acme is good.")]
        score = _score_signal_diversity(analyses)
        self.assertGreater(score, 0)
        self.assertLess(score, 30)

    def test_no_signals(self):
        analyses = [compute_sentiment_score(NEUTRAL_TEXT)]
        self.assertEqual(_score_signal_diversity(analyses), 0.0)

    def test_empty(self):
        self.assertEqual(_score_signal_diversity([]), 0.0)


class TestAnalyzeBrandSentiment(unittest.TestCase):

    def test_basic_positive(self):
        mentions = [_make_mention(POSITIVE_TEXT)]
        r = analyze_brand_sentiment("Acme", mentions)
        self.assertTrue(r["success"])
        self.assertEqual(r["overall_sentiment"], "positive")
        self.assertIn("dimensions", r)
        self.assertEqual(len(r["dimensions"]), 5)

    def test_basic_negative(self):
        mentions = [_make_mention(NEGATIVE_TEXT)]
        r = analyze_brand_sentiment("Acme", mentions)
        self.assertEqual(r["overall_sentiment"], "negative")

    def test_no_mentions(self):
        r = analyze_brand_sentiment("Acme", [])
        self.assertTrue(r["success"])
        self.assertEqual(r["total_mentions"], 0)
        self.assertEqual(r["overall_sentiment"], "unknown")
        self.assertEqual(r["confidence"], 0.0)
        self.assertEqual(len(r["dimensions"]), 5)

    def test_brand_not_in_text(self):
        mentions = [_make_mention("Some unrelated text about nothing.")]
        r = analyze_brand_sentiment("Acme", mentions)
        self.assertEqual(r["total_mentions"], 0)

    def test_dimensions_present(self):
        mentions = [_make_mention(POSITIVE_TEXT)]
        r = analyze_brand_sentiment("Acme", mentions)
        for dim in SENTIMENT_WEIGHTS:
            self.assertIn(dim, r["dimensions"])

    def test_score_is_weighted_sum(self):
        mentions = [
            _make_mention(POSITIVE_TEXT, "chatgpt"),
            _make_mention(POSITIVE_TEXT, "perplexity"),
        ]
        r = analyze_brand_sentiment("Acme", mentions)
        expected = round(sum(
            r["dimensions"][k] * SENTIMENT_WEIGHTS[k] for k in SENTIMENT_WEIGHTS
        ), 1)
        self.assertEqual(r["score"], expected)

    def test_multi_platform(self):
        mentions = [
            _make_mention(POSITIVE_TEXT, "chatgpt"),
            _make_mention("Acme is reliable and trusted.", "perplexity"),
            _make_mention("Acme는 최고의 추천 서비스", "gemini"),
        ]
        r = analyze_brand_sentiment("Acme", mentions)
        self.assertEqual(r["total_mentions"], 3)
        self.assertIn("chatgpt", r["platform_scores"])
        self.assertIn("perplexity", r["platform_scores"])
        self.assertIn("gemini", r["platform_scores"])

    def test_label_distribution(self):
        mentions = [
            _make_mention(POSITIVE_TEXT),
            _make_mention(NEGATIVE_TEXT),
            _make_mention(NEUTRAL_TEXT),
        ]
        r = analyze_brand_sentiment("Acme", mentions)
        dist = r["label_distribution"]
        self.assertEqual(dist["positive"], 1)
        self.assertEqual(dist["negative"], 1)
        self.assertEqual(dist["neutral"], 1)

    def test_confidence_increases_with_data(self):
        few = [_make_mention(POSITIVE_TEXT)]
        many = [_make_mention(POSITIVE_TEXT, p) for p in ["chatgpt", "perplexity", "gemini", "claude"]]
        r_few = analyze_brand_sentiment("Acme", few)
        r_many = analyze_brand_sentiment("Acme", many)
        self.assertGreater(r_many["confidence"], r_few["confidence"])

    def test_confidence_bounded(self):
        mentions = [_make_mention(POSITIVE_TEXT, p) for p in ["a", "b", "c", "d"]] * 10
        r = analyze_brand_sentiment("Acme", mentions)
        self.assertLessEqual(r["confidence"], 1.0)
        self.assertGreaterEqual(r["confidence"], 0.0)

    def test_analyses_capped_at_20(self):
        mentions = [_make_mention(f"Acme is excellent #{i}") for i in range(30)]
        r = analyze_brand_sentiment("Acme", mentions)
        self.assertLessEqual(len(r["analyses"]), 20)

    def test_korean_mentions(self):
        mentions = [_make_mention(KOREAN_POSITIVE), _make_mention(KOREAN_NEGATIVE)]
        r = analyze_brand_sentiment("Acme", mentions)
        self.assertEqual(r["total_mentions"], 2)
        self.assertIn("dimensions", r)

    def test_score_bounded(self):
        mentions = [_make_mention(POSITIVE_TEXT)] * 5
        r = analyze_brand_sentiment("Acme", mentions)
        self.assertGreaterEqual(r["score"], 0)
        self.assertLessEqual(r["score"], 100)
        for v in r["dimensions"].values():
            self.assertGreaterEqual(v, 0)
            self.assertLessEqual(v, 100)


if __name__ == "__main__":
    unittest.main()

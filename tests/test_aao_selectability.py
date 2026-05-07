"""Tests for AAO selectability: industry detection, signal correlation, dimension scorers."""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from aao_selectability import (
    detect_industry, get_industry_weights, score_structured_data,
    score_reviews_ratings, score_info_completeness, score_api_booking,
    score_trust_signals, score_freshness, _compute_correlation_bonus,
    _cross_validate_schema, BASE_WEIGHTS,
)


RESTAURANT_HTML = """
<html><body>
<h1>맛집 레스토랑</h1>
<p>메뉴: 파스타, 스테이크, 리조또</p>
<p>예약 가능합니다</p>
<script type="application/ld+json">
{"@type": "Restaurant", "name": "맛집", "telephone": "02-1234-5678",
 "address": {"streetAddress": "서울시 강남구"}, "priceRange": "$$",
 "openingHoursSpecification": {"opens": "11:00", "closes": "22:00"}}
</script>
</body></html>
"""

ECOMMERCE_HTML = """
<html><body>
<h1>온라인 쇼핑몰</h1>
<p>장바구니에 담기</p><p>가격: 29,900원</p>
<p>배송: 무료배송</p><p>결제하기</p>
<script type="application/ld+json">
{"@type": "Product", "name": "테스트 상품", "offers": {"price": "29900"}}
</script>
</body></html>
"""

MINIMAL_HTML = "<html><body><p>Hello world</p></body></html>"


class TestIndustryDetection(unittest.TestCase):

    def test_detect_restaurant(self):
        self.assertEqual(detect_industry(RESTAURANT_HTML), "restaurant")

    def test_detect_ecommerce(self):
        self.assertEqual(detect_industry(ECOMMERCE_HTML), "ecommerce")

    def test_detect_clinic(self):
        html = "<html><body><p>진료 안내 - 병원 예약</p><p>의사 소개</p><p>치료 프로그램</p></body></html>"
        self.assertEqual(detect_industry(html), "clinic")

    def test_detect_general_fallback(self):
        self.assertEqual(detect_industry(MINIMAL_HTML), "general")

    def test_detect_saas(self):
        html = "<html><body><p>pricing plan</p><p>API dashboard</p><p>free trial subscription</p></body></html>"
        self.assertEqual(detect_industry(html), "saas")


class TestIndustryWeights(unittest.TestCase):

    def test_general_uses_base(self):
        weights = get_industry_weights("general")
        self.assertEqual(weights, BASE_WEIGHTS)

    def test_restaurant_boosts_reviews(self):
        weights = get_industry_weights("restaurant")
        base = BASE_WEIGHTS["reviews_ratings"]
        self.assertGreater(weights["reviews_ratings"], base)

    def test_ecommerce_boosts_api(self):
        weights = get_industry_weights("ecommerce")
        base = BASE_WEIGHTS["api_booking"]
        self.assertGreater(weights["api_booking"], base)

    def test_weights_sum_to_one(self):
        for industry in ["restaurant", "ecommerce", "clinic", "hotel", "education", "saas"]:
            weights = get_industry_weights(industry)
            self.assertAlmostEqual(sum(weights.values()), 1.0, places=2)


class TestStructuredData(unittest.TestCase):

    def test_restaurant_schema(self):
        result = score_structured_data(RESTAURANT_HTML)
        self.assertGreater(result["score"], 30)
        self.assertIn("claims", result)

    def test_no_schema(self):
        result = score_structured_data(MINIMAL_HTML)
        self.assertEqual(result["score"], 0)

    def test_product_schema(self):
        result = score_structured_data(ECOMMERCE_HTML)
        self.assertGreater(result["score"], 20)

    def test_cross_validation(self):
        claims = {"name": "맛집", "telephone": "02-1234-5678"}
        result = _cross_validate_schema(RESTAURANT_HTML, claims)
        self.assertGreater(result["match_ratio"], 0.5)

    def test_cross_validation_empty(self):
        result = _cross_validate_schema(MINIMAL_HTML, {})
        self.assertEqual(result["match_ratio"], 0.5)


class TestReviewsRatings(unittest.TestCase):

    def test_with_rating(self):
        html = '<div>"ratingValue": "4.5", "reviewCount": "120"</div><div>AggregateRating</div>'
        result = score_reviews_ratings(html)
        self.assertGreater(result["score"], 50)

    def test_no_rating(self):
        result = score_reviews_ratings(MINIMAL_HTML)
        self.assertEqual(result["score"], 0)

    def test_visible_rating_no_schema(self):
        html = '<div>평점 4.3 / 리뷰 50개</div><p>리뷰 리뷰 리뷰</p>'
        result = score_reviews_ratings(html)
        self.assertGreater(result["score"], 0)

    def test_low_rating_lower_score(self):
        high = '<div>"ratingValue": "4.8"</div>'
        low = '<div>"ratingValue": "2.5"</div>'
        r_high = score_reviews_ratings(high)
        r_low = score_reviews_ratings(low)
        self.assertGreater(r_high["score"], r_low["score"])


class TestInfoCompleteness(unittest.TestCase):

    def test_rich_page(self):
        result = score_info_completeness(RESTAURANT_HTML)
        self.assertGreater(result["score"], 30)
        self.assertIn("checks", result)

    def test_minimal_page(self):
        result = score_info_completeness(MINIMAL_HTML)
        self.assertLess(result["score"], 20)

    def test_missing_fields_reported(self):
        result = score_info_completeness(MINIMAL_HTML)
        missing = [k for k, v in result["checks"].items() if not v]
        self.assertGreater(len(missing), 3)


class TestApiBooking(unittest.TestCase):

    def test_booking_cta(self):
        html = '<a href="#">예약하기</a><a href="#">바로예약</a>'
        result = score_api_booking(html)
        self.assertGreater(result["score"], 15)

    def test_purchase_cta(self):
        html = '<button>장바구니</button><button>구매하기</button>'
        result = score_api_booking(html)
        self.assertGreater(result["score"], 15)

    def test_no_actions(self):
        result = score_api_booking(MINIMAL_HTML)
        self.assertLessEqual(result["score"], 10)

    def test_schema_action(self):
        html = '"@type": "ReserveAction"  "potentialAction"'
        result = score_api_booking(html)
        self.assertGreater(result["score"], 30)


class TestTrustSignals(unittest.TestCase):

    def test_with_certs(self):
        html = '<p>ISO 9001 인증</p><p>사업자 등록 번호: 123-45-67890</p>'
        result = score_trust_signals(html)
        self.assertGreater(result["score"], 30)

    def test_minimal(self):
        result = score_trust_signals(MINIMAL_HTML)
        self.assertLess(result["score"], 20)

    def test_named_partners(self):
        html = '<p>파트너: 삼성, Google</p>'
        result = score_trust_signals(html)
        self.assertTrue(any("Named partners" in s for s in result["signals"]))


class TestFreshness(unittest.TestCase):

    def test_current_year(self):
        html = '<p>2026-05-01 업데이트</p><p>copyright © 2026</p>'
        result = score_freshness(html, 0.5)
        self.assertGreater(result["score"], 50)

    def test_no_dates(self):
        result = score_freshness(MINIMAL_HTML, 2.0)
        self.assertLess(result["score"], 30)

    def test_fast_response_bonus(self):
        fast = score_freshness(MINIMAL_HTML, 0.3)
        slow = score_freshness(MINIMAL_HTML, 6.0)
        self.assertGreater(fast["score"], slow["score"])


class TestCorrelationBonus(unittest.TestCase):

    def test_both_high_gets_bonus(self):
        dims = {
            "structured_data": {"score": 70},
            "reviews_ratings": {"score": 60},
            "info_completeness": {"score": 55},
            "api_booking": {"score": 65},
            "trust_signals": {"score": 55},
            "freshness": {"score": 50},
        }
        result = _compute_correlation_bonus(dims)
        self.assertGreater(result["bonus"], 0)
        self.assertGreater(len(result["applied"]), 0)

    def test_low_scores_no_bonus(self):
        dims = {k: {"score": 20} for k in BASE_WEIGHTS}
        result = _compute_correlation_bonus(dims)
        bonuses = [c for c in result["applied"] if c["value"] > 0]
        self.assertEqual(len(bonuses), 0)

    def test_penalty_for_conflict(self):
        dims = {
            "structured_data": {"score": 80},
            "reviews_ratings": {"score": 20},
            "info_completeness": {"score": 20},
            "api_booking": {"score": 20},
            "trust_signals": {"score": 20},
            "freshness": {"score": 20},
        }
        result = _compute_correlation_bonus(dims)
        penalties = [c for c in result["applied"] if c["value"] < 0]
        self.assertGreater(len(penalties), 0)


if __name__ == "__main__":
    unittest.main()

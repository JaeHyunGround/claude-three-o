"""Tests for agent conversion funnel readiness analysis."""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from aao_conversion import (
    detect_flow_type,
    detect_industry,
    score_cta_quality,
    score_form_accessibility,
    score_flow_completeness,
    score_mobile_conversion,
    score_deep_link,
    score_confirmation_error,
    analyze_conversion_html,
    CONVERSION_WEIGHTS,
    FRICTION_POINTS,
)


EMPTY_HTML = "<html><body></body></html>"

BOOKING_HTML = """
<html><head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta property="og:url" content="https://hotel.example.com">
<link rel="canonical" href="https://hotel.example.com">
</head><body>
<nav><a href="/reserve">예약하기</a></nav>
<h1>호텔 객실 예약</h1>
<p>체크인 시간: 15:00</p>
<p>요금: ₩150,000/박</p>
<button class="btn cta" role="button">지금 예약</button>
<a href="/book/room" class="btn">바로 구매</a>
<script type="application/ld+json">
{"@type": "LodgingReservation", "potentialAction": {"@type": "ReserveAction"}}
</script>
<form action="/api/reserve" method="post">
    <label for="name">이름</label>
    <input id="name" type="text" name="name" required autocomplete="name" placeholder="홍길동">
    <label for="email">이메일</label>
    <input id="email" type="email" name="email" required autocomplete="email" placeholder="email@example.com">
    <label for="phone">전화번호</label>
    <input id="phone" type="tel" name="phone" autocomplete="tel" inputmode="tel">
    <label for="date">체크인 날짜</label>
    <input id="date" type="date" name="checkin" required>
    <button type="submit">예약 확인</button>
</form>
<p>비회원 예약 가능</p>
<p>네이버페이, 카카오페이, 신용카드 결제</p>
<p>안전한 결제 (SSL 보안)</p>
<p>환불 정책: 체크인 24시간 전 무료 취소</p>
<p>예약 완료 시 이메일로 예약번호 전송</p>
<p>오류 발생 시 다시 시도해 주세요.</p>
<div role="alert" aria-invalid="true">유효하지 않은 입력</div>
<a href="tel:+82-2-1234-5678">전화 문의</a>
<a href="https://maps.google.com/place">지도 보기</a>
<a href="kakaomap://place">카카오맵</a>
<p class="loading">처리 중...</p>
<div class="sticky bottom"><button>예약하기</button></div>
<p>한정 특가 — 오늘만!</p>
</body></html>
"""

ECOMMERCE_HTML = """
<html><head><meta name="viewport" content="width=device-width"></head><body>
<h1>상품 구매</h1>
<p>가격: ₩50,000</p>
<button>장바구니 담기</button>
<a href="/cart">장바구니</a>
<a href="/checkout">구매하기</a>
<form method="post" action="/buy">
    <input type="number" name="qty" placeholder="수량">
    <input type="hidden" name="product" value="123">
    <button type="submit">구매</button>
</form>
<p>배송비 무료</p>
<p>카드 결제, 네이버페이</p>
<p>주문번호 확인</p>
<p>validation 검증</p>
</body></html>
"""

CAPTCHA_HTML = """
<html><body>
<h1>Sign Up</h1>
<form>
    <input type="text" name="name">
    <div class="g-recaptcha"></div>
    <p>로그인 필수 required</p>
    <p>회원 가입</p>
</form>
<p>step 1</p><p>step 2</p><p>step 3</p><p>step 4</p><p>step 5</p><p>step 6</p>
</body></html>
"""

APP_LINK_HTML = """
<html><head>
<meta name="apple-itunes-app" content="app-id=123456">
<link rel="canonical" href="https://app.example.com/page">
<meta property="og:url" content="https://app.example.com/page">
</head><body>
<a href="intent://open#Intent;package=com.example.app;end">앱으로 보기</a>
<a href="kakaotalk://share">카카오톡 공유</a>
<a href="/api/v2/data.json">API</a>
<a href="/book/123">예약 페이지</a>
<a href="#section1">섹션1</a>
<a href="#section2">섹션2</a>
<a href="#section3">섹션3</a>
<p>링크 복사</p>
</body></html>
"""

MOBILE_RICH_HTML = """
<html><head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>@media (max-width: 768px) { .mobile { display: block; } }</style>
</head><body>
<a href="tel:+82-2-1234-5678">전화하기</a>
<a href="sms:+82-10-1234-5678">문자하기</a>
<a href="https://map.naver.com/place">길찾기</a>
<div style="touch-action: manipulation;">
    <input inputmode="numeric" placeholder="숫자 입력">
</div>
<div class="sticky bottom"><button>예약하기</button></div>
<p>카카오 로그인으로 간편 신청</p>
</body></html>
"""

CLINIC_HTML = """
<html><body>
<h1>병원 진료 예약</h1>
<p>의사 상담 예약</p>
<form>
    <label>이름</label><input type="text">
    <label>연락처</label><input type="tel">
    <label>진료과</label><select><option>내과</option></select>
    <button>상담 신청</button>
</form>
<p>예약 완료 감사합니다</p>
</body></html>
"""

IFRAME_FORM_HTML = """
<html><body>
<h1>예약</h1>
<iframe src="https://booking.external.com/form-reserve"></iframe>
</body></html>
"""


class TestDetectFlowType(unittest.TestCase):
    def test_booking(self):
        self.assertEqual(detect_flow_type(BOOKING_HTML), "book")

    def test_ecommerce(self):
        self.assertEqual(detect_flow_type(ECOMMERCE_HTML), "buy")

    def test_signup(self):
        self.assertEqual(detect_flow_type(CAPTCHA_HTML), "signup")

    def test_inquiry(self):
        html = "<p>문의하기 견적 요청</p>"
        self.assertEqual(detect_flow_type(html), "inquiry")

    def test_download(self):
        html = "<p>다운로드 받기</p>"
        self.assertEqual(detect_flow_type(html), "download")

    def test_unknown(self):
        self.assertEqual(detect_flow_type(EMPTY_HTML), "unknown")


class TestDetectIndustry(unittest.TestCase):
    def test_hotel(self):
        self.assertEqual(detect_industry(BOOKING_HTML), "hotel")

    def test_ecommerce(self):
        self.assertEqual(detect_industry(ECOMMERCE_HTML), "ecommerce")

    def test_clinic(self):
        self.assertEqual(detect_industry(CLINIC_HTML), "clinic")

    def test_restaurant(self):
        html = "<p>메뉴 음식 맛집 레스토랑</p>"
        self.assertEqual(detect_industry(html), "restaurant")

    def test_education(self):
        html = "<p>수강 신청 강좌 학원</p>"
        self.assertEqual(detect_industry(html), "education")

    def test_saas(self):
        html = "<p>요금제 플랜 pricing plan</p>"
        self.assertEqual(detect_industry(html), "saas")

    def test_general(self):
        self.assertEqual(detect_industry(EMPTY_HTML), "general")


class TestScoreCtaQuality(unittest.TestCase):
    def test_rich_cta_high_score(self):
        result = score_cta_quality(BOOKING_HTML)
        self.assertGreater(result["score"], 60)

    def test_empty_html_low_score(self):
        result = score_cta_quality(EMPTY_HTML)
        self.assertLess(result["score"], 20)

    def test_specific_ctas_detected(self):
        result = score_cta_quality(BOOKING_HTML)
        self.assertGreater(result["details"]["specific_ctas"], 0)

    def test_schema_action_detected(self):
        result = score_cta_quality(BOOKING_HTML)
        self.assertTrue(result["details"]["schema_action"])

    def test_action_urls(self):
        result = score_cta_quality(BOOKING_HTML)
        self.assertGreater(result["details"]["action_urls"], 0)

    def test_urgency_signals(self):
        result = score_cta_quality(BOOKING_HTML)
        self.assertTrue(result["details"]["urgency_signals"])

    def test_aria_roles(self):
        result = score_cta_quality(BOOKING_HTML)
        self.assertTrue(result["details"]["aria_roles"])

    def test_nav_action(self):
        result = score_cta_quality(BOOKING_HTML)
        self.assertTrue(result["details"]["nav_action"])

    def test_score_capped(self):
        result = score_cta_quality(BOOKING_HTML)
        self.assertLessEqual(result["score"], 100)

    def test_generic_cta_lower_score(self):
        html = '<button>클릭</button><a href="#">더보기</a>'
        result = score_cta_quality(html)
        self.assertGreater(result["details"]["generic_ctas"], 0)


class TestScoreFormAccessibility(unittest.TestCase):
    def test_rich_form_high_score(self):
        result = score_form_accessibility(BOOKING_HTML)
        self.assertGreater(result["score"], 60)

    def test_no_form(self):
        result = score_form_accessibility(EMPTY_HTML)
        self.assertEqual(result["score"], 0.0)

    def test_form_count(self):
        result = score_form_accessibility(BOOKING_HTML)
        self.assertGreater(result["details"]["form_count"], 0)

    def test_labels_detected(self):
        result = score_form_accessibility(BOOKING_HTML)
        self.assertGreater(result["details"]["total_labels"], 0)

    def test_typed_inputs(self):
        result = score_form_accessibility(BOOKING_HTML)
        self.assertGreater(result["details"]["typed_inputs"], 0)

    def test_autocomplete(self):
        result = score_form_accessibility(BOOKING_HTML)
        self.assertGreater(result["details"]["autocomplete_attrs"], 0)

    def test_required_marked(self):
        result = score_form_accessibility(BOOKING_HTML)
        self.assertGreater(result["details"]["required_marked"], 0)

    def test_field_efficiency(self):
        result = score_form_accessibility(BOOKING_HTML)
        self.assertIn(result["details"]["field_efficiency"], ["optimal", "acceptable", "heavy"])

    def test_iframe_form(self):
        result = score_form_accessibility(IFRAME_FORM_HTML)
        self.assertTrue(result["details"].get("iframe_form"))
        self.assertGreater(result["score"], 0)

    def test_score_capped(self):
        result = score_form_accessibility(BOOKING_HTML)
        self.assertLessEqual(result["score"], 100)


class TestScoreFlowCompleteness(unittest.TestCase):
    def test_good_flow_high_score(self):
        result = score_flow_completeness(BOOKING_HTML)
        self.assertGreater(result["score"], 50)

    def test_captcha_penalty(self):
        result = score_flow_completeness(CAPTCHA_HTML)
        captcha_frictions = [f for f in result["frictions"] if f["impact"] == "critical"]
        self.assertGreater(len(captcha_frictions), 0)
        self.assertTrue(result["details"].get("captcha"))

    def test_login_required_penalty(self):
        result = score_flow_completeness(CAPTCHA_HTML)
        login_frictions = [f for f in result["frictions"] if "로그인" in f["message"]]
        self.assertGreater(len(login_frictions), 0)

    def test_guest_access_bonus(self):
        result = score_flow_completeness(BOOKING_HTML)
        self.assertTrue(result["details"]["guest_access"])

    def test_payment_signals(self):
        result = score_flow_completeness(BOOKING_HTML)
        payment = result["details"]["payment"]
        self.assertTrue(payment["price_visible"])
        self.assertTrue(payment["payment_methods"])
        self.assertTrue(payment["secure_checkout"])
        self.assertTrue(payment["refund_policy"])

    def test_complex_flow_penalty(self):
        result = score_flow_completeness(CAPTCHA_HTML)
        complex_frictions = [f for f in result["frictions"] if "복잡" in f["message"]]
        self.assertGreater(len(complex_frictions), 0)

    def test_no_guest_friction(self):
        result = score_flow_completeness(CAPTCHA_HTML)
        no_guest = [f for f in result["frictions"] if "비회원" in f["message"]]
        self.assertGreater(len(no_guest), 0)

    def test_score_range(self):
        for html in [EMPTY_HTML, BOOKING_HTML, CAPTCHA_HTML]:
            result = score_flow_completeness(html)
            self.assertGreaterEqual(result["score"], 0)
            self.assertLessEqual(result["score"], 100)

    def test_iframe_form_friction(self):
        html = '<iframe src="https://booking.com/form-payment"></iframe>'
        result = score_flow_completeness(html)
        iframe_frictions = [f for f in result["frictions"] if "iframe" in f["message"]]
        self.assertGreater(len(iframe_frictions), 0)


class TestScoreMobileConversion(unittest.TestCase):
    def test_rich_mobile_high_score(self):
        result = score_mobile_conversion(MOBILE_RICH_HTML)
        self.assertGreater(result["score"], 60)

    def test_empty_html_low_score(self):
        result = score_mobile_conversion(EMPTY_HTML)
        self.assertLess(result["score"], 15)

    def test_viewport_detected(self):
        result = score_mobile_conversion(BOOKING_HTML)
        self.assertTrue(result["details"]["viewport"])

    def test_click_to_call(self):
        result = score_mobile_conversion(MOBILE_RICH_HTML)
        self.assertTrue(result["details"]["click_to_call"])

    def test_click_to_sms(self):
        result = score_mobile_conversion(MOBILE_RICH_HTML)
        self.assertTrue(result["details"]["click_to_sms"])

    def test_click_to_map(self):
        result = score_mobile_conversion(MOBILE_RICH_HTML)
        self.assertTrue(result["details"]["click_to_map"])

    def test_mobile_input_modes(self):
        result = score_mobile_conversion(MOBILE_RICH_HTML)
        self.assertTrue(result["details"]["mobile_input_modes"])

    def test_sns_login(self):
        result = score_mobile_conversion(MOBILE_RICH_HTML)
        self.assertTrue(result["details"]["sns_login"])

    def test_responsive(self):
        result = score_mobile_conversion(MOBILE_RICH_HTML)
        self.assertTrue(result["details"]["responsive"])

    def test_blocks_zoom_penalty(self):
        html = '<meta name="viewport" content="width=device-width, user-scalable=no">'
        result = score_mobile_conversion(html)
        self.assertTrue(result["details"]["blocks_zoom"])

    def test_score_capped(self):
        result = score_mobile_conversion(MOBILE_RICH_HTML)
        self.assertLessEqual(result["score"], 100)


class TestScoreDeepLink(unittest.TestCase):
    def test_app_links_high_score(self):
        result = score_deep_link(APP_LINK_HTML)
        self.assertGreater(result["score"], 60)

    def test_empty_html_low_score(self):
        result = score_deep_link(EMPTY_HTML)
        self.assertLess(result["score"], 15)

    def test_ios_universal_link(self):
        result = score_deep_link(APP_LINK_HTML)
        self.assertTrue(result["details"]["ios_universal_link"])

    def test_android_app_link(self):
        result = score_deep_link(APP_LINK_HTML)
        self.assertTrue(result["details"]["android_app_link"])

    def test_custom_scheme(self):
        result = score_deep_link(APP_LINK_HTML)
        self.assertTrue(result["details"]["custom_scheme"])

    def test_canonical(self):
        result = score_deep_link(APP_LINK_HTML)
        self.assertTrue(result["details"]["canonical"])

    def test_api_endpoints(self):
        result = score_deep_link(APP_LINK_HTML)
        self.assertTrue(result["details"]["api_endpoints"])

    def test_og_url(self):
        result = score_deep_link(APP_LINK_HTML)
        self.assertTrue(result["details"]["og_url"])

    def test_direct_action_paths(self):
        result = score_deep_link(APP_LINK_HTML)
        self.assertGreater(result["details"]["direct_action_paths"], 0)

    def test_share_mechanism(self):
        result = score_deep_link(APP_LINK_HTML)
        self.assertTrue(result["details"]["share_mechanism"])

    def test_hash_navigation(self):
        result = score_deep_link(APP_LINK_HTML)
        self.assertTrue(result["details"]["hash_navigation"])

    def test_score_capped(self):
        result = score_deep_link(APP_LINK_HTML)
        self.assertLessEqual(result["score"], 100)


class TestScoreConfirmationError(unittest.TestCase):
    def test_booking_signals(self):
        result = score_confirmation_error(BOOKING_HTML)
        self.assertGreater(result["score"], 50)

    def test_empty_html(self):
        result = score_confirmation_error(EMPTY_HTML)
        self.assertLess(result["score"], 15)

    def test_success_language(self):
        result = score_confirmation_error(BOOKING_HTML)
        self.assertTrue(result["details"].get("confirmation_id") or result["details"].get("success_language"))

    def test_aria_errors(self):
        result = score_confirmation_error(BOOKING_HTML)
        self.assertTrue(result["details"]["aria_errors"])

    def test_retry_guidance(self):
        result = score_confirmation_error(BOOKING_HTML)
        self.assertTrue(result["details"]["retry_guidance"])

    def test_loading_state(self):
        result = score_confirmation_error(BOOKING_HTML)
        self.assertTrue(result["details"]["loading_state"])

    def test_client_validation(self):
        result = score_confirmation_error(ECOMMERCE_HTML)
        self.assertTrue(result["details"]["client_validation"])

    def test_score_capped(self):
        result = score_confirmation_error(BOOKING_HTML)
        self.assertLessEqual(result["score"], 100)


class TestAnalyzeConversionHtml(unittest.TestCase):
    def test_success(self):
        result = analyze_conversion_html(BOOKING_HTML, "https://hotel.example.com")
        self.assertTrue(result["success"])

    def test_all_fields(self):
        result = analyze_conversion_html(BOOKING_HTML, "https://hotel.example.com")
        self.assertIn("score", result)
        self.assertIn("dimensions", result)
        self.assertIn("dimension_details", result)
        self.assertIn("weakest_dimension", result)
        self.assertIn("strongest_dimension", result)
        self.assertIn("flow_type", result)
        self.assertIn("industry", result)
        self.assertIn("friction_points", result)
        self.assertIn("issues", result)
        self.assertIn("estimated_completion_rate", result)

    def test_six_dimensions(self):
        result = analyze_conversion_html(BOOKING_HTML, "https://hotel.example.com")
        dims = result["dimensions"]
        self.assertEqual(len(dims), 6)
        self.assertIn("cta_quality", dims)
        self.assertIn("form_accessibility", dims)
        self.assertIn("flow_completeness", dims)
        self.assertIn("mobile_conversion", dims)
        self.assertIn("deep_link", dims)
        self.assertIn("confirmation_error", dims)

    def test_booking_high_score(self):
        result = analyze_conversion_html(BOOKING_HTML, "https://hotel.example.com")
        self.assertGreater(result["score"], 50)

    def test_empty_html_low_score(self):
        result = analyze_conversion_html(EMPTY_HTML, "https://example.com")
        self.assertLess(result["score"], 20)

    def test_flow_type_detected(self):
        result = analyze_conversion_html(BOOKING_HTML, "https://hotel.example.com")
        self.assertEqual(result["flow_type"], "book")

    def test_industry_detected(self):
        result = analyze_conversion_html(BOOKING_HTML, "https://hotel.example.com")
        self.assertEqual(result["industry"], "hotel")

    def test_flow_type_override(self):
        result = analyze_conversion_html(BOOKING_HTML, "https://example.com", flow_type="buy")
        self.assertEqual(result["flow_type"], "buy")

    def test_weakest_strongest(self):
        result = analyze_conversion_html(BOOKING_HTML, "https://hotel.example.com")
        self.assertIn(result["weakest_dimension"], CONVERSION_WEIGHTS)
        self.assertIn(result["strongest_dimension"], CONVERSION_WEIGHTS)

    def test_captcha_friction(self):
        result = analyze_conversion_html(CAPTCHA_HTML, "https://example.com")
        critical = [f for f in result["friction_points"] if f["impact"] == "critical"]
        self.assertGreater(len(critical), 0)

    def test_issues_sorted(self):
        result = analyze_conversion_html(CAPTCHA_HTML, "https://example.com")
        if len(result["issues"]) >= 2:
            severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            for i in range(len(result["issues"]) - 1):
                s1 = severity_order.get(result["issues"][i].get("severity"), 4)
                s2 = severity_order.get(result["issues"][i + 1].get("severity"), 4)
                self.assertLessEqual(s1, s2)

    def test_score_formula(self):
        result = analyze_conversion_html(BOOKING_HTML, "https://hotel.example.com")
        dims = result["dimensions"]
        expected = round(sum(dims[k] * CONVERSION_WEIGHTS[k] for k in CONVERSION_WEIGHTS), 1)
        self.assertAlmostEqual(result["score"], expected, places=0)

    def test_completion_rate(self):
        result = analyze_conversion_html(BOOKING_HTML, "https://hotel.example.com")
        rate = int(result["estimated_completion_rate"].replace("%", ""))
        self.assertGreaterEqual(rate, 0)
        self.assertLessEqual(rate, 100)

    def test_score_range(self):
        for html in [EMPTY_HTML, BOOKING_HTML, ECOMMERCE_HTML, CAPTCHA_HTML]:
            result = analyze_conversion_html(html, "https://example.com")
            self.assertGreaterEqual(result["score"], 0)
            self.assertLessEqual(result["score"], 100)
            for dim_score in result["dimensions"].values():
                self.assertGreaterEqual(dim_score, 0)
                self.assertLessEqual(dim_score, 100)

    def test_clinic_industry(self):
        result = analyze_conversion_html(CLINIC_HTML, "https://clinic.example.com")
        self.assertEqual(result["industry"], "clinic")


class TestConversionWeights(unittest.TestCase):
    def test_weights_sum_to_one(self):
        total = sum(CONVERSION_WEIGHTS.values())
        self.assertAlmostEqual(total, 1.0, places=5)

    def test_six_dimensions(self):
        self.assertEqual(len(CONVERSION_WEIGHTS), 6)


class TestEdgeCases(unittest.TestCase):
    def test_large_html(self):
        html = "<html><body>" + "<p>content</p>" * 1000 + "</body></html>"
        result = analyze_conversion_html(html, "https://example.com")
        self.assertTrue(result["success"])

    def test_no_url(self):
        result = analyze_conversion_html(BOOKING_HTML, "")
        self.assertTrue(result["success"])
        self.assertEqual(result["url"], "")

    def test_special_chars(self):
        html = '<form><input value="₩50,000 &amp; ¥5,000"></form>'
        result = score_form_accessibility(html)
        self.assertGreater(result["score"], 0)

    def test_multiple_forms(self):
        html = """
        <form><input type="text"></form>
        <form><input type="email"><label>Email</label></form>
        <form><input type="tel"><label>Phone</label></form>
        """
        result = score_form_accessibility(html)
        self.assertEqual(result["details"]["form_count"], 3)

    def test_naver_map_link(self):
        html = '<a href="https://map.naver.com/place/12345">지도</a>'
        result = score_mobile_conversion(html)
        self.assertTrue(result["details"]["click_to_map"])

    def test_kakao_map_link(self):
        html = '<a href="https://map.kakao.com/link/123">지도</a>'
        result = score_mobile_conversion(html)
        self.assertTrue(result["details"]["click_to_map"])

    def test_toss_scheme(self):
        html = '<a href="toss://payment">토스로 결제</a>'
        result = score_deep_link(html)
        self.assertTrue(result["details"]["custom_scheme"])


if __name__ == "__main__":
    unittest.main()

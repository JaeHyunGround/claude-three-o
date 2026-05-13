"""Tests for schema auto-generation: extraction, template filling, suggestions."""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from schema_generator import (
    extract_title, extract_description, extract_image, extract_phone,
    extract_prices, extract_address, extract_hours, extract_rating,
    extract_social_links, extract_cuisine, extract_specialty,
    extract_services, extract_founding_year, extract_email, extract_logo,
    extract_parent_org, extract_employee_count, extract_area_served,
    extract_page_data, load_template, fill_template, generate_schema,
    format_jsonld_output, _count_template_fields, _count_filled_fields,
    _generate_suggestions, _clean_unfilled, _price_range_label,
)


RESTAURANT_HTML = """
<html lang="ko">
<head>
<title>맛있는 한식당 - 서울 강남 한식 맛집</title>
<meta name="description" content="서울 강남에 위치한 전통 한식 맛집입니다. 정성 가득한 한식 코스 요리를 즐겨보세요. 예약 가능합니다.">
<meta property="og:title" content="맛있는 한식당">
<meta property="og:image" content="https://example.com/restaurant.jpg">
</head>
<body>
<h1>맛있는 한식당</h1>
<p>서울특별시 강남구 테헤란로 123번길 45</p>
<p>전화: 02-1234-5678</p>
<p>영업시간: 11:00 ~ 22:00</p>
<p>점심 코스: 25,000원 / 저녁 코스: 45,000원</p>
<p>평점: 4.7 / 5 (리뷰 328개)</p>
<p>한식 전문 레스토랑</p>
<a href="https://www.instagram.com/tasty_hansik/">Instagram</a>
<a href="https://blog.naver.com/tastyhansik">Blog</a>
</body></html>
"""

CLINIC_HTML = """
<html lang="ko">
<head>
<title>서울밝은치과 - 강남역 치과 전문</title>
<meta name="description" content="강남역 3번 출구 서울밝은치과입니다. 임플란트, 교정, 심미치료 전문. 야간진료 가능.">
</head>
<body>
<h1>서울밝은치과</h1>
<p>서울특별시 강남구 강남대로 456</p>
<p>우편번호: 06120</p>
<p>전화: 02-555-1234</p>
<p>진료시간: 09:30 ~ 19:00</p>
<p>임플란트 상담 무료 / 스케일링 50,000원</p>
<p>rating: 4.8 (후기 512개)</p>
</body></html>
"""

HOTEL_HTML = """
<html lang="ko">
<head>
<title>그랜드 파라다이스 호텔 제주</title>
<meta name="description" content="제주도 서귀포시 중문관광단지 내 5성급 리조트 호텔. 오션뷰 객실과 스파, 인피니티 풀.">
<meta property="og:image" content="https://example.com/hotel-main.jpg">
</head>
<body>
<h1>그랜드 파라다이스 호텔</h1>
<p>제주특별자치도 서귀포시 중문동 2800</p>
<p>전화: 064-738-1234</p>
<p>체크인: 15:00 ~ 체크아웃: 11:00</p>
<p>스탠다드룸 150,000원 / 스위트룸 350,000원</p>
<p>별점 4.5 / 5 (review 1,203개)</p>
<a href="https://www.instagram.com/grand_paradise_jeju/">Instagram</a>
</body></html>
"""

ECOMMERCE_HTML = """
<html lang="ko">
<head>
<title>프리미엄 무선 이어폰 - BestShop</title>
<meta name="description" content="노이즈캔슬링 무선 이어폰. 최대 30시간 재생. 방수 IPX5.">
</head>
<body>
<h1>프리미엄 무선 이어폰 Pro Max</h1>
<p>가격: 89,000원</p>
<p>할인가: 69,000원</p>
<p>배송비 무료</p>
<p>구매 리뷰 4.3점 (리뷰 2,456개)</p>
<button>장바구니 담기</button>
</body></html>
"""

SAAS_HTML = """
<html lang="en">
<head>
<title>CloudFlow - Team Collaboration Platform</title>
<meta name="description" content="All-in-one team collaboration with real-time dashboard, API integration, and enterprise support.">
</head>
<body>
<h1>CloudFlow</h1>
<p>Pricing: Basic 29,000원/mo, Pro 79,000원/mo, Enterprise 199,000원/mo</p>
<p>Start your free trial today</p>
<p>무료체험 available</p>
<a href="https://www.linkedin.com/company/cloudflow/">LinkedIn</a>
</body></html>
"""

AGENCY_HTML = """
<html lang="ko">
<head>
<title>스카이벤처스 - 종합 마케팅 대행사</title>
<meta name="description" content="브랜딩과 퍼포먼스 캠페인의 조합으로 최적의 솔루션을 찾는 종합대행사입니다.">
<meta property="og:image" content="https://www.skyventures.co.kr/img/og.jpg">
<link rel="icon" href="/favicon.png">
</head>
<body>
<img class="logo" src="/img/logo.png" alt="스카이벤처스">
<h1>스카이벤처스</h1>
<p>함파트너스 그룹 계열사</p>
<p>설립: 2015년</p>
<p>직원: 약 50명</p>
<p>서울특별시 성동구 성수이로7길 7, 8층</p>
<p>전화: 02-2088-7892</p>
<p>이메일: svc@skyventures.co.kr</p>
<h2>서비스</h2>
<p>디지털 마케팅, 브랜딩, 크리에이티브 제작</p>
<p>퍼포먼스 마케팅, PR, IMC 캠페인</p>
<p>웹 개발, 영상 제작</p>
<h2>포트폴리오</h2>
<p>클라이언트: BBQ, Lotte GRS, 귀한족발</p>
<a href="https://www.instagram.com/skyventures_official/">Instagram</a>
<a href="https://www.youtube.com/channel/UCtest">YouTube</a>
</body></html>
"""

REALESTATE_HTML = """
<html lang="ko">
<head><title>강남부동산 - 강남 아파트 전문</title></head>
<body>
<h1>강남부동산</h1>
<p>서울특별시 강남구 역삼동 123</p>
<p>전화: 02-555-9876</p>
<p>매물 안내: 아파트 분양, 전세, 월세</p>
<p>서비스 지역: 서울 강남, 서초, 송파</p>
</body></html>
"""

MINIMAL_HTML = """
<html><head><title>Test Page</title></head>
<body><p>Very little content here</p></body></html>
"""


class TestExtractServices(unittest.TestCase):

    def test_detect_services(self):
        services = extract_services(AGENCY_HTML)
        self.assertTrue(len(services) >= 3)

    def test_digital_marketing(self):
        services = extract_services("<p>디지털 마케팅 전문</p>")
        self.assertTrue(any("마케팅" in s for s in services))

    def test_branding(self):
        services = extract_services("<p>브랜딩 전략 수립</p>")
        self.assertTrue(any("브랜딩" in s for s in services))

    def test_no_services(self):
        self.assertEqual(extract_services("<p>hello</p>"), [])

    def test_max_8(self):
        html = "<p>디지털 마케팅 브랜딩 크리에이티브 퍼포먼스 마케팅 PR IMC 웹 개발 영상 제작 SEO UX BTL 데이터 분석</p>"
        self.assertLessEqual(len(extract_services(html)), 8)


class TestExtractFoundingYear(unittest.TestCase):

    def test_korean_format(self):
        self.assertEqual(extract_founding_year("<p>2015년 설립</p>"), "2015")

    def test_since_format(self):
        self.assertEqual(extract_founding_year("<p>Since 2010</p>"), "2010")

    def test_established_format(self):
        self.assertEqual(extract_founding_year("<p>Established: 2008</p>"), "2008")

    def test_no_year(self):
        self.assertEqual(extract_founding_year("<p>hello</p>"), "")

    def test_invalid_year_rejected(self):
        self.assertEqual(extract_founding_year("<p>설립 1800</p>"), "")


class TestExtractEmail(unittest.TestCase):

    def test_korean_domain(self):
        self.assertEqual(extract_email("<p>svc@skyventures.co.kr</p>"), "svc@skyventures.co.kr")

    def test_com_domain(self):
        self.assertEqual(extract_email("<p>info@example.com</p>"), "info@example.com")

    def test_css_gradient_ignored(self):
        html = "<style>background: linear-gradient(GRAD@20..48deg)</style><p>real@test.com</p>"
        self.assertEqual(extract_email(html), "real@test.com")

    def test_no_email(self):
        self.assertEqual(extract_email("<p>no email</p>"), "")


class TestExtractLogo(unittest.TestCase):

    def test_from_class(self):
        html = '<img class="logo" src="/img/logo.png">'
        self.assertEqual(extract_logo(html), "/img/logo.png")

    def test_from_src_name(self):
        html = '<img src="/assets/company-logo.svg">'
        self.assertEqual(extract_logo(html), "/assets/company-logo.svg")

    def test_favicon(self):
        html = '<link rel="icon" href="/favicon.ico">'
        self.assertEqual(extract_logo(html), "/favicon.ico")

    def test_no_logo(self):
        self.assertEqual(extract_logo("<p>no images</p>"), "")


class TestExtractParentOrg(unittest.TestCase):

    def test_korean_group(self):
        self.assertEqual(extract_parent_org("<p>함파트너스 그룹 계열사</p>"), "함파트너스 그룹")

    def test_english_group(self):
        self.assertEqual(extract_parent_org("<p>Hahm Partners Group</p>"), "Hahm Partners Group")

    def test_no_parent(self):
        self.assertEqual(extract_parent_org("<p>independent company</p>"), "")


class TestExtractEmployeeCount(unittest.TestCase):

    def test_korean_format(self):
        self.assertEqual(extract_employee_count("<p>직원: 약 50명</p>"), "50")

    def test_team_format(self):
        self.assertEqual(extract_employee_count("<p>30명의 전문가</p>"), "30")

    def test_no_count(self):
        self.assertEqual(extract_employee_count("<p>hello</p>"), "")


class TestExtractAreaServed(unittest.TestCase):

    def test_seoul(self):
        result = extract_area_served("<p>서비스 지역: 서울 강남</p>")
        self.assertIn("서울", result)

    def test_region(self):
        result = extract_area_served("<p>부산 해운대 전문</p>")
        self.assertIn("부산", result)

    def test_no_area(self):
        self.assertEqual(extract_area_served("<p>hello</p>"), "")


class TestExtractTitle(unittest.TestCase):

    def test_from_title_tag(self):
        self.assertIn("한식당", extract_title(RESTAURANT_HTML))

    def test_strips_suffix(self):
        title = extract_title('<html><head><title>My Site - Company Name</title></head><body></body></html>')
        self.assertEqual(title, "My Site")

    def test_from_og_title(self):
        html = '<html><head><meta property="og:title" content="OG Title"></head><body></body></html>'
        self.assertEqual(extract_title(html), "OG Title")

    def test_from_h1(self):
        html = "<html><head></head><body><h1>H1 Title</h1></body></html>"
        self.assertEqual(extract_title(html), "H1 Title")

    def test_empty_html(self):
        self.assertEqual(extract_title("<html><head></head><body></body></html>"), "")


class TestExtractDescription(unittest.TestCase):

    def test_from_meta(self):
        desc = extract_description(RESTAURANT_HTML)
        self.assertIn("한식", desc)

    def test_from_og(self):
        html = '<html><head><meta property="og:description" content="OG desc"></head><body></body></html>'
        self.assertEqual(extract_description(html), "OG desc")

    def test_missing(self):
        self.assertEqual(extract_description(MINIMAL_HTML), "")


class TestExtractPhone(unittest.TestCase):

    def test_korean_phone(self):
        phone = extract_phone(RESTAURANT_HTML)
        self.assertIn("02", phone)
        self.assertIn("1234", phone)

    def test_regional_phone(self):
        phone = extract_phone(HOTEL_HTML)
        self.assertIn("064", phone)

    def test_no_phone(self):
        self.assertEqual(extract_phone(MINIMAL_HTML), "")


class TestExtractPrices(unittest.TestCase):

    def test_multiple_prices(self):
        prices = extract_prices(RESTAURANT_HTML)
        self.assertGreaterEqual(len(prices), 2)
        self.assertIn(25000, prices)
        self.assertIn(45000, prices)

    def test_ecommerce_prices(self):
        prices = extract_prices(ECOMMERCE_HTML)
        self.assertIn(89000, prices)
        self.assertIn(69000, prices)

    def test_no_prices(self):
        self.assertEqual(extract_prices(MINIMAL_HTML), [])


class TestExtractAddress(unittest.TestCase):

    def test_seoul_address(self):
        addr = extract_address(RESTAURANT_HTML)
        self.assertIn("서울", addr["region"])
        self.assertIn("강남", addr.get("city", "") + addr.get("street", ""))

    def test_jeju_address(self):
        addr = extract_address(HOTEL_HTML)
        self.assertIn("제주", addr["region"])

    def test_postal_code(self):
        addr = extract_address(CLINIC_HTML)
        self.assertEqual(addr["postal_code"], "06120")

    def test_no_address(self):
        addr = extract_address(MINIMAL_HTML)
        self.assertEqual(addr["street"], "")


class TestExtractHours(unittest.TestCase):

    def test_restaurant_hours(self):
        open_t, close_t = extract_hours(RESTAURANT_HTML)
        self.assertEqual(open_t, "11:00")
        self.assertEqual(close_t, "22:00")

    def test_clinic_hours(self):
        open_t, close_t = extract_hours(CLINIC_HTML)
        self.assertEqual(open_t, "09:30")
        self.assertEqual(close_t, "19:00")

    def test_no_hours(self):
        open_t, close_t = extract_hours(MINIMAL_HTML)
        self.assertEqual(open_t, "")
        self.assertEqual(close_t, "")


class TestExtractRating(unittest.TestCase):

    def test_restaurant_rating(self):
        rating, count = extract_rating(RESTAURANT_HTML)
        self.assertEqual(rating, "4.7")
        self.assertEqual(count, "328")

    def test_clinic_rating(self):
        rating, count = extract_rating(CLINIC_HTML)
        self.assertEqual(rating, "4.8")
        self.assertEqual(count, "512")

    def test_ecommerce_rating(self):
        rating, count = extract_rating(ECOMMERCE_HTML)
        self.assertEqual(rating, "4.3")

    def test_no_rating(self):
        rating, count = extract_rating(MINIMAL_HTML)
        self.assertEqual(rating, "")
        self.assertEqual(count, "")


class TestExtractSocialLinks(unittest.TestCase):

    def test_instagram(self):
        links = extract_social_links(RESTAURANT_HTML)
        self.assertTrue(any("instagram.com" in l for l in links))

    def test_naver_blog(self):
        links = extract_social_links(RESTAURANT_HTML)
        self.assertTrue(any("blog.naver.com" in l for l in links))

    def test_linkedin(self):
        links = extract_social_links(SAAS_HTML)
        self.assertTrue(any("linkedin.com" in l for l in links))

    def test_no_social(self):
        self.assertEqual(extract_social_links(MINIMAL_HTML), [])


class TestExtractCuisine(unittest.TestCase):

    def test_korean(self):
        self.assertEqual(extract_cuisine(RESTAURANT_HTML), "Korean")

    def test_no_cuisine(self):
        self.assertEqual(extract_cuisine(MINIMAL_HTML), "")


class TestExtractSpecialty(unittest.TestCase):

    def test_dentistry(self):
        self.assertEqual(extract_specialty(CLINIC_HTML), "Dentistry")

    def test_no_specialty(self):
        self.assertEqual(extract_specialty(MINIMAL_HTML), "")


class TestPriceRangeLabel(unittest.TestCase):

    def test_cheap(self):
        self.assertEqual(_price_range_label([5000, 8000]), "₩")

    def test_moderate(self):
        self.assertEqual(_price_range_label([15000, 25000]), "₩₩")

    def test_expensive(self):
        self.assertEqual(_price_range_label([50000, 80000]), "₩₩₩")

    def test_luxury(self):
        self.assertEqual(_price_range_label([150000, 350000]), "₩₩₩₩")

    def test_empty(self):
        self.assertEqual(_price_range_label([]), "")


class TestLoadTemplate(unittest.TestCase):

    def test_restaurant_template(self):
        t = load_template("restaurant.json")
        self.assertEqual(t["@type"], "Restaurant")

    def test_clinic_template(self):
        t = load_template("clinic.json")
        self.assertEqual(t["@type"], "MedicalBusiness")

    def test_missing_template(self):
        self.assertEqual(load_template("nonexistent.json"), {})


class TestFillTemplate(unittest.TestCase):

    def test_restaurant_fill(self):
        template = load_template("restaurant.json")
        data = extract_page_data(RESTAURANT_HTML, "https://example.com")
        result = fill_template(template, data, "restaurant")
        self.assertEqual(result["@type"], "Restaurant")
        self.assertIn("한식당", result.get("name", ""))
        self.assertIn("servesCuisine", result)

    def test_removes_unfilled(self):
        template = load_template("hotel.json")
        data = extract_page_data(MINIMAL_HTML, "https://example.com")
        result = fill_template(template, data, "hotel")
        raw = str(result)
        self.assertNotIn("{{", raw)

    def test_social_links_filled(self):
        template = load_template("restaurant.json")
        data = extract_page_data(RESTAURANT_HTML, "https://example.com")
        result = fill_template(template, data, "restaurant")
        self.assertIn("sameAs", result)
        self.assertGreater(len(result["sameAs"]), 0)


class TestCleanUnfilled(unittest.TestCase):

    def test_removes_placeholder_strings(self):
        obj = {"name": "Valid", "phone": "{{phone}}", "url": ""}
        _clean_unfilled(obj)
        self.assertNotIn("phone", obj)
        self.assertNotIn("url", obj)

    def test_removes_empty_nested(self):
        obj = {"address": {"@type": "PostalAddress", "street": ""}}
        _clean_unfilled(obj)
        self.assertNotIn("address", obj)

    def test_preserves_filled(self):
        obj = {"name": "Test", "phone": "02-1234-5678"}
        _clean_unfilled(obj)
        self.assertEqual(obj["name"], "Test")
        self.assertEqual(obj["phone"], "02-1234-5678")


class TestCountFields(unittest.TestCase):

    def test_template_field_count(self):
        t = load_template("restaurant.json")
        count = _count_template_fields(t)
        self.assertGreater(count, 10)

    def test_filled_field_count(self):
        schema = {"@type": "Restaurant", "name": "Test", "telephone": "123"}
        count = _count_filled_fields(schema)
        self.assertEqual(count, 2)


class TestGenerateSchema(unittest.TestCase):

    def test_restaurant_generation(self):
        result = generate_schema(RESTAURANT_HTML, "https://example.com")
        self.assertTrue(result["success"])
        self.assertEqual(result["industry"], "restaurant")
        self.assertEqual(result["template"], "restaurant.json")
        self.assertGreater(result["coverage"], 30)

    def test_clinic_generation(self):
        result = generate_schema(CLINIC_HTML, "https://example.com")
        self.assertTrue(result["success"])
        self.assertEqual(result["industry"], "clinic")

    def test_hotel_generation(self):
        result = generate_schema(HOTEL_HTML, "https://example.com")
        self.assertTrue(result["success"])
        self.assertEqual(result["industry"], "hotel")

    def test_ecommerce_generation(self):
        result = generate_schema(ECOMMERCE_HTML, "https://example.com")
        self.assertTrue(result["success"])
        self.assertEqual(result["industry"], "ecommerce")

    def test_saas_generation(self):
        result = generate_schema(SAAS_HTML, "https://example.com")
        self.assertTrue(result["success"])
        self.assertEqual(result["industry"], "saas")

    def test_industry_override(self):
        result = generate_schema(MINIMAL_HTML, "https://example.com", "restaurant")
        self.assertTrue(result["success"])
        self.assertEqual(result["industry"], "restaurant")

    def test_schema_has_context(self):
        result = generate_schema(RESTAURANT_HTML, "https://example.com")
        self.assertEqual(result["schema"]["@context"], "https://schema.org")

    def test_agency_generation(self):
        result = generate_schema(AGENCY_HTML, "https://www.skyventures.co.kr")
        self.assertTrue(result["success"])
        self.assertEqual(result["industry"], "agency")
        self.assertEqual(result["schema"]["@type"], "ProfessionalService")
        self.assertIn("knowsAbout", result["schema"])
        self.assertIsInstance(result["schema"]["knowsAbout"], list)

    def test_realestate_generation(self):
        result = generate_schema(REALESTATE_HTML, "https://example.com")
        self.assertTrue(result["success"])
        self.assertEqual(result["industry"], "realestate")
        self.assertEqual(result["schema"]["@type"], "RealEstateAgent")

    def test_minimal_page(self):
        result = generate_schema(MINIMAL_HTML, "https://example.com")
        self.assertTrue(result["success"])
        self.assertLess(result["coverage"], 30)


class TestSuggestions(unittest.TestCase):

    def test_minimal_page_many_suggestions(self):
        data = extract_page_data(MINIMAL_HTML, "https://example.com")
        suggestions = _generate_suggestions(data, "general", 10.0)
        self.assertGreater(len(suggestions), 3)

    def test_missing_phone_suggestion(self):
        data = {"phone": "", "rating": "4.5", "address": {"street": "x"}, "description": "x", "image": "x", "social_links": ["x"]}
        suggestions = _generate_suggestions(data, "general", 80.0)
        fields = [s["field"] for s in suggestions]
        self.assertIn("telephone", fields)

    def test_clinic_specialty_suggestion(self):
        data = {"phone": "x", "rating": "x", "address": {"street": "x"}, "description": "x", "image": "x", "social_links": [], "specialty": "", "cuisine": ""}
        suggestions = _generate_suggestions(data, "clinic", 60.0)
        fields = [s["field"] for s in suggestions]
        self.assertIn("medicalSpecialty", fields)

    def test_low_coverage_flagged(self):
        data = extract_page_data(MINIMAL_HTML, "https://example.com")
        suggestions = _generate_suggestions(data, "general", 20.0)
        fields = [s["field"] for s in suggestions]
        self.assertIn("_overall", fields)


class TestFormatOutput(unittest.TestCase):

    def test_script_tag_format(self):
        schema = {"@context": "https://schema.org", "@type": "Restaurant", "name": "Test"}
        output = format_jsonld_output(schema)
        self.assertIn('<script type="application/ld+json">', output)
        self.assertIn("</script>", output)
        self.assertIn('"Restaurant"', output)

    def test_json_valid(self):
        schema = {"@type": "Restaurant", "name": "테스트"}
        output = format_jsonld_output(schema)
        json_part = output.split("\n", 1)[1].rsplit("\n", 1)[0]
        import json
        parsed = json.loads(json_part)
        self.assertEqual(parsed["name"], "테스트")


if __name__ == "__main__":
    unittest.main()

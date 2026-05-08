"""Tests for SEO content quality and E-E-A-T analysis."""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from seo_content import (
    extract_text_content,
    count_headings,
    analyze_korean_content,
    _count_signal_matches,
    score_experience,
    score_expertise,
    score_authoritativeness,
    score_trust,
    compute_eeat_score,
    analyze_content_depth,
    analyze_content_html,
    EEAT_WEIGHTS,
    EXPERIENCE_SIGNALS,
    EXPERTISE_SIGNALS,
    AUTHORITY_SIGNALS,
    TRUST_SIGNALS,
)


MINIMAL_HTML = "<html><body><p>Hello world</p></body></html>"

RICH_EXPERIENCE_HTML = """
<html><body>
<h1>3년간 직접 사용한 SEO 도구 리뷰</h1>
<p>제가 직접 3년 동안 사용해본 경험을 공유합니다.</p>
<p>저희 팀은 시행착오를 거쳐 단계별 프로세스를 완성했습니다.</p>
<p>실제 사용 후기: 이 도구는 탁월한 성능을 보여줬습니다.</p>
<img src="/uploads/original/screenshot.png" alt="실제 사용 화면">
<video src="/content/media/demo.mp4"></video>
<p>2년간 테스트한 결과적으로 확실한 효과를 확인했습니다.</p>
</body></html>
"""

RICH_EXPERTISE_HTML = """
<html><body>
<h1>SEO 전문가 가이드</h1>
<script type="application/ld+json">
{"@type": "Person", "name": "Dr. Kim", "author": {"@type": "Person"}}
</script>
<p>작성자: 김박사 (Ph.D, 디지털마케팅 전문가, CPA 자격증 보유)</p>
<p>알고리즘 최적화와 프레임워크 아키텍처에 대한 분석입니다.</p>
<p>인덱싱과 크롤링 과정에서 시맨틱 구조화가 핵심입니다.</p>
<p>분석 결과에 따르면 데이터에 따르면 성능이 45% 향상되었습니다.</p>
</body></html>
"""

RICH_AUTHORITY_HTML = """
<html><body>
<h1>업계 인정받는 서비스</h1>
<p>출처: 한국인터넷진흥원 보고서</p>
<p>참고 문헌 및 인용 자료 목록</p>
<a href="https://example.org/study">외부 연구 자료</a>
<a href="https://kisa.or.kr/report">KISA 보고서</a>
<a href="https://www.example.go.kr/data">정부 데이터</a>
<p>ISO 9001 인증, 특허 등록 완료</p>
<p>한국디지털마케팅협회 회원</p>
<p>뉴스 보도 및 미디어 인터뷰 다수</p>
<script type="application/ld+json">{"sameAs": ["https://twitter.com/example"]}</script>
</body></html>
"""

RICH_TRUST_HTML = """
<html><body>
<h1>신뢰할 수 있는 서비스</h1>
<a href="/privacy">개인정보처리방침</a>
<a href="/terms">이용약관</a>
<p>연락처: 고객센터 1588-0000</p>
<p>서울특별시 강남구 테헤란로 123</p>
<p>사업자 등록번호: 123-45-67890, 대표자: 홍길동</p>
<form action="https://secure.example.com/submit" method="post">
<input type="text" name="email">
</form>
<p>발행일: 2024-03-15, 수정일: 2024-06-01</p>
</body></html>
"""

EMPTY_HTML = "<html><body></body></html>"

KOREAN_CONTENT = """
<html><body>
<h1>한국어 콘텐츠 테스트</h1>
<p>이것은 한국어로 작성된 테스트 콘텐츠입니다. 다양한 주제에 대해 설명합니다.</p>
</body></html>
"""

ENGLISH_CONTENT = """
<html><body>
<h1>English Content Test</h1>
<p>This is a test content written in English about various topics and SEO optimization.</p>
</body></html>
"""

MULTI_H1_HTML = """
<html><body>
<h1>First Heading</h1>
<h1>Second Heading</h1>
<h2>Sub heading</h2>
<h3>Sub sub heading</h3>
</body></html>
"""

NO_H1_HTML = """
<html><body>
<h2>Only H2</h2>
<h3>And H3</h3>
</body></html>
"""

LONG_CONTENT = """
<html><body>
<h1>Comprehensive Guide to SEO</h1>
""" + " ".join(["This is a detailed paragraph about search engine optimization." for _ in range(100)]) + """
<p>Numbers: 45%, 1200 users, 3.5 billion queries per day.</p>
<p>Google Search Console is an important tool. Microsoft Bing Webmaster also helps.</p>
</body></html>
"""

SCRIPT_STYLE_HTML = """
<html><head>
<script>var x = "should not appear";</script>
<style>.cls { display: none; }</style>
</head><body>
<p>Visible content only</p>
</body></html>
"""


class TestExtractTextContent(unittest.TestCase):
    def test_basic_extraction(self):
        text = extract_text_content("<p>Hello <b>world</b></p>")
        self.assertIn("Hello", text)
        self.assertIn("world", text)

    def test_script_removal(self):
        text = extract_text_content(SCRIPT_STYLE_HTML)
        self.assertNotIn("should not appear", text)
        self.assertNotIn("display", text)
        self.assertIn("Visible content only", text)

    def test_whitespace_normalization(self):
        text = extract_text_content("<p>Hello    \n\n   world</p>")
        self.assertNotIn("\n", text)
        self.assertNotIn("    ", text)

    def test_empty_html(self):
        text = extract_text_content(EMPTY_HTML)
        self.assertEqual(len(text.strip()), 0)


class TestCountHeadings(unittest.TestCase):
    def test_multiple_levels(self):
        html = "<h1>A</h1><h2>B</h2><h2>C</h2><h3>D</h3>"
        counts = count_headings(html)
        self.assertEqual(counts["h1"], 1)
        self.assertEqual(counts["h2"], 2)
        self.assertEqual(counts["h3"], 1)
        self.assertEqual(counts["h4"], 0)

    def test_no_headings(self):
        counts = count_headings("<p>No headings</p>")
        for level in range(1, 7):
            self.assertEqual(counts[f"h{level}"], 0)

    def test_case_insensitive(self):
        counts = count_headings("<H1>Title</H1><H2>Sub</H2>")
        self.assertEqual(counts["h1"], 1)
        self.assertEqual(counts["h2"], 1)

    def test_headings_with_attributes(self):
        counts = count_headings('<h1 class="title" id="main">Title</h1>')
        self.assertEqual(counts["h1"], 1)


class TestAnalyzeKoreanContent(unittest.TestCase):
    def test_korean_detection(self):
        result = analyze_korean_content("한국어 테스트입니다")
        self.assertTrue(result["is_korean_content"])
        self.assertGreater(result["korean_ratio"], 0.3)

    def test_english_content(self):
        result = analyze_korean_content("This is English content only")
        self.assertFalse(result["is_korean_content"])
        self.assertEqual(result["korean_chars"], 0)

    def test_mixed_content(self):
        result = analyze_korean_content("SEO 최적화 guide for 한국")
        self.assertGreater(result["korean_chars"], 0)
        self.assertGreater(result["total_chars"], 0)

    def test_empty_text(self):
        result = analyze_korean_content("")
        self.assertEqual(result["korean_chars"], 0)
        self.assertFalse(result["is_korean_content"])


class TestCountSignalMatches(unittest.TestCase):
    def test_single_pattern_match(self):
        count = _count_signal_matches("제가 직접 경험했습니다", [r"(?:제가|직접|경험)"])
        self.assertGreaterEqual(count, 2)

    def test_no_match(self):
        count = _count_signal_matches("nothing special here", [r"(?:제가|직접)"])
        self.assertEqual(count, 0)

    def test_multiple_patterns(self):
        count = _count_signal_matches(
            "I have experience with this case study review",
            [r"(?:I |we )", r"(?:case study|review)"]
        )
        self.assertGreaterEqual(count, 2)

    def test_empty_patterns(self):
        count = _count_signal_matches("any text", [])
        self.assertEqual(count, 0)


class TestScoreExperience(unittest.TestCase):
    def test_rich_experience_high_score(self):
        result = score_experience(RICH_EXPERIENCE_HTML)
        self.assertGreater(result["score"], 60)
        self.assertIn("details", result)

    def test_minimal_html_low_score(self):
        result = score_experience(MINIMAL_HTML)
        self.assertLess(result["score"], 30)

    def test_first_person_signals(self):
        html = "<p>제가 직접 사용해봤습니다. 저희 팀의 경험을 공유합니다.</p>"
        result = score_experience(html)
        self.assertGreater(result["details"]["first_person"], 0)

    def test_case_study_signals(self):
        html = "<p>실제 사용 후기와 체험 사례를 소개합니다.</p>"
        result = score_experience(html)
        self.assertGreater(result["details"]["case_study"], 0)

    def test_original_media_signals(self):
        html = '<img src="/uploads/original/photo.jpg"><video src="/content/media/v.mp4">'
        result = score_experience(html)
        self.assertGreater(result["details"]["original_media"], 0)

    def test_temporal_experience(self):
        html = "<p>3년 동안 사용했습니다. for 5 years of experience.</p>"
        result = score_experience(html)
        self.assertGreater(result["details"]["temporal_experience"], 0)

    def test_process_narrative(self):
        html = "<p>단계별 과정을 거쳐 시행착오 끝에 결과적으로 성공했습니다.</p>"
        result = score_experience(html)
        self.assertGreater(result["details"]["process_narrative"], 0)

    def test_score_capped_at_100(self):
        html = RICH_EXPERIENCE_HTML * 5
        result = score_experience(html)
        self.assertLessEqual(result["score"], 100)

    def test_baseline_score(self):
        result = score_experience(EMPTY_HTML)
        self.assertEqual(result["score"], 15.0)


class TestScoreExpertise(unittest.TestCase):
    def test_rich_expertise_high_score(self):
        result = score_expertise(RICH_EXPERTISE_HTML)
        self.assertGreater(result["score"], 60)

    def test_credentials_detected(self):
        html = "<p>박사 학위, Ph.D, CPA 자격증 보유 전문가</p>"
        result = score_expertise(html)
        self.assertGreater(result["details"]["credentials"], 0)

    def test_technical_depth(self):
        html = "<p>알고리즘과 프레임워크 아키텍처를 분석합니다.</p>"
        result = score_expertise(html)
        self.assertGreater(result["details"]["technical_depth"], 0)

    def test_author_bio(self):
        html = "<p>작성자 프로필: 10년 경력 SEO 전문가</p>"
        result = score_expertise(html)
        self.assertGreater(result["details"]["author_bio"], 0)

    def test_author_schema(self):
        html = '<script>{"@type": "Person", "author": {"name": "Kim"}}</script>'
        result = score_expertise(html)
        self.assertGreater(result["details"]["author_schema"], 0)

    def test_data_analysis_signals(self):
        html = "<p>분석 결과에 따르면 데이터에 따르면 효과적입니다.</p>"
        result = score_expertise(html)
        self.assertGreater(result["details"]["data_analysis"], 0)

    def test_minimal_html_low_score(self):
        result = score_expertise(MINIMAL_HTML)
        self.assertLess(result["score"], 25)

    def test_score_capped_at_100(self):
        html = RICH_EXPERTISE_HTML * 5
        result = score_expertise(html)
        self.assertLessEqual(result["score"], 100)

    def test_baseline_score(self):
        result = score_expertise(EMPTY_HTML)
        self.assertEqual(result["score"], 10.0)


class TestScoreAuthoritativeness(unittest.TestCase):
    def test_rich_authority_high_score(self):
        result = score_authoritativeness(RICH_AUTHORITY_HTML)
        self.assertGreater(result["score"], 60)

    def test_external_citations(self):
        html = '<a href="https://example.org/study">Study</a>'
        result = score_authoritativeness(html)
        self.assertGreater(result["details"]["external_citations"], 0)

    def test_social_links_excluded_from_citations(self):
        html = '<a href="https://www.facebook.com/page">FB</a>'
        result = score_authoritativeness(html)
        self.assertEqual(result["details"]["external_citations"], 0)

    def test_source_attribution(self):
        html = "<p>출처: 한국인터넷진흥원. 참고 자료 인용.</p>"
        result = score_authoritativeness(html)
        self.assertGreater(result["details"]["source_attribution"], 0)

    def test_awards_certs(self):
        html = "<p>ISO 인증, 특허 등록, 수상 경력</p>"
        result = score_authoritativeness(html)
        self.assertGreater(result["details"]["awards_certs"], 0)

    def test_institutional_links(self):
        html = '<a href="https://www.mois.go.kr/data">정부 자료</a>'
        result = score_authoritativeness(html)
        self.assertGreater(result["details"]["institutional_links"], 0)

    def test_institutional_links_edu(self):
        html = '<a href="https://www.mit.edu/research">MIT Research</a>'
        result = score_authoritativeness(html)
        self.assertGreater(result["details"]["institutional_links"], 0)

    def test_same_as_links(self):
        html = '<script>{"sameAs": ["https://twitter.com/x"]}</script>'
        result = score_authoritativeness(html)
        self.assertEqual(result["details"]["same_as_links"], 1)

    def test_industry_affiliation(self):
        html = "<p>한국디지털마케팅협회 회원, 학회 소속</p>"
        result = score_authoritativeness(html)
        self.assertGreater(result["details"]["industry_affiliation"], 0)

    def test_media_mentions(self):
        html = "<p>뉴스 보도 및 미디어 인터뷰 기사</p>"
        result = score_authoritativeness(html)
        self.assertGreater(result["details"]["media_mentions"], 0)

    def test_minimal_html_low_score(self):
        result = score_authoritativeness(MINIMAL_HTML)
        self.assertLess(result["score"], 25)

    def test_baseline_score(self):
        result = score_authoritativeness(EMPTY_HTML)
        self.assertEqual(result["score"], 10.0)


class TestScoreTrust(unittest.TestCase):
    def test_rich_trust_high_score(self):
        result = score_trust(RICH_TRUST_HTML, "https://example.com")
        self.assertGreater(result["score"], 70)

    def test_https_detection_from_url(self):
        result = score_trust("<p>content</p>", "https://example.com")
        self.assertTrue(result["details"]["https"])

    def test_http_not_https(self):
        result = score_trust("<p>content</p>", "http://example.com")
        self.assertFalse(result["details"]["https"])

    def test_privacy_policy(self):
        html = '<a href="/privacy">개인정보처리방침</a>'
        result = score_trust(html)
        self.assertTrue(result["details"]["privacy_policy"])

    def test_terms_of_service(self):
        html = '<a href="/terms">이용약관</a>'
        result = score_trust(html)
        self.assertTrue(result["details"]["terms_of_service"])

    def test_contact_info(self):
        html = "<p>연락처: 고객센터 문의</p>"
        result = score_trust(html)
        self.assertTrue(result["details"]["contact_info"])

    def test_physical_address_korean(self):
        html = "<p>서울특별시 강남구 테헤란로</p>"
        result = score_trust(html)
        self.assertTrue(result["details"]["physical_address"])

    def test_business_registration(self):
        html = "<p>사업자 등록번호: 123-45-67890</p>"
        result = score_trust(html)
        self.assertTrue(result["details"]["business_registration"])

    def test_secure_forms(self):
        html = '<form action="https://secure.example.com" method="post"><input></form>'
        result = score_trust(html)
        self.assertTrue(result["details"]["secure_forms"])

    def test_clear_attribution(self):
        html = "<p>발행일: 2024-01-15</p>"
        result = score_trust(html)
        self.assertTrue(result["details"]["clear_attribution"])

    def test_clear_attribution_schema(self):
        html = '<script>{"datePublished": "2024-01-15"}</script>'
        result = score_trust(html)
        self.assertTrue(result["details"]["clear_attribution"])

    def test_minimal_html_low_score(self):
        result = score_trust(MINIMAL_HTML, "http://example.com")
        self.assertLess(result["score"], 30)

    def test_baseline_score(self):
        result = score_trust(EMPTY_HTML, "")
        self.assertEqual(result["score"], 10.0)

    def test_all_trust_signals_max(self):
        result = score_trust(RICH_TRUST_HTML, "https://example.com")
        self.assertTrue(result["details"]["https"])
        self.assertTrue(result["details"]["privacy_policy"])
        self.assertTrue(result["details"]["contact_info"])
        self.assertTrue(result["details"]["physical_address"])
        self.assertTrue(result["details"]["business_registration"])
        self.assertTrue(result["details"]["secure_forms"])
        self.assertTrue(result["details"]["clear_attribution"])


class TestComputeEeatScore(unittest.TestCase):
    def test_weighted_computation(self):
        exp = {"score": 80.0}
        ext = {"score": 70.0}
        auth = {"score": 60.0}
        trust = {"score": 90.0}
        result = compute_eeat_score(exp, ext, auth, trust)
        expected = 80 * 0.20 + 70 * 0.30 + 60 * 0.25 + 90 * 0.25
        self.assertAlmostEqual(result["score"], expected, places=1)

    def test_weakest_strongest(self):
        exp = {"score": 20.0}
        ext = {"score": 90.0}
        auth = {"score": 50.0}
        trust = {"score": 60.0}
        result = compute_eeat_score(exp, ext, auth, trust)
        self.assertEqual(result["weakest"], "experience")
        self.assertEqual(result["strongest"], "expertise")

    def test_critical_issues(self):
        exp = {"score": 10.0}
        ext = {"score": 15.0}
        auth = {"score": 80.0}
        trust = {"score": 80.0}
        result = compute_eeat_score(exp, ext, auth, trust)
        critical = [i for i in result["issues"] if i["severity"] == "critical"]
        self.assertGreater(len(critical), 0)

    def test_high_issues(self):
        exp = {"score": 35.0}
        ext = {"score": 80.0}
        auth = {"score": 30.0}
        trust = {"score": 80.0}
        result = compute_eeat_score(exp, ext, auth, trust)
        high = [i for i in result["issues"] if i["severity"] == "high"]
        self.assertGreater(len(high), 0)

    def test_no_issues_when_all_high(self):
        exp = {"score": 80.0}
        ext = {"score": 80.0}
        auth = {"score": 80.0}
        trust = {"score": 80.0}
        result = compute_eeat_score(exp, ext, auth, trust)
        self.assertEqual(len(result["issues"]), 0)

    def test_all_axes_present(self):
        exp = {"score": 50.0}
        ext = {"score": 50.0}
        auth = {"score": 50.0}
        trust = {"score": 50.0}
        result = compute_eeat_score(exp, ext, auth, trust)
        self.assertIn("experience", result["axes"])
        self.assertIn("expertise", result["axes"])
        self.assertIn("authoritativeness", result["axes"])
        self.assertIn("trust", result["axes"])

    def test_all_zero(self):
        z = {"score": 0.0}
        result = compute_eeat_score(z, z, z, z)
        self.assertEqual(result["score"], 0.0)

    def test_all_hundred(self):
        h = {"score": 100.0}
        result = compute_eeat_score(h, h, h, h)
        self.assertEqual(result["score"], 100.0)

    def test_weights_sum_to_one(self):
        total = sum(EEAT_WEIGHTS.values())
        self.assertAlmostEqual(total, 1.0, places=5)


class TestAnalyzeContentDepth(unittest.TestCase):
    def test_short_content(self):
        result = analyze_content_depth("Hello world.")
        self.assertLess(result["depth_score"], 50)
        self.assertEqual(result["word_count"], 2)

    def test_long_content(self):
        text = " ".join(["word"] * 1600)
        result = analyze_content_depth(text)
        self.assertGreater(result["depth_score"], 50)
        self.assertEqual(result["word_count"], 1600)

    def test_medium_content(self):
        text = " ".join(["word"] * 500)
        result = analyze_content_depth(text)
        self.assertGreaterEqual(result["word_count"], 300)

    def test_numbers_boost(self):
        text = "Score is 45% and 1200 users with 3.5 billion queries. " * 10
        result = analyze_content_depth(text)
        self.assertGreater(result["numbers_count"], 0)

    def test_proper_nouns_boost(self):
        text = "Google Search Console and Microsoft Bing Webmaster are important tools. " * 10
        result = analyze_content_depth(text)
        self.assertGreater(result["proper_nouns"], 0)

    def test_sentence_counting(self):
        text = "First sentence. Second sentence. Third sentence."
        result = analyze_content_depth(text)
        self.assertGreaterEqual(result["sentence_count"], 3)

    def test_avg_sentence_length(self):
        text = "This is a moderate sentence length for testing purposes. Another sentence here."
        result = analyze_content_depth(text)
        self.assertGreater(result["avg_sentence_length"], 0)

    def test_depth_score_capped(self):
        text = " ".join(["word"] * 2000) + " " + " ".join([f"{i}%" for i in range(50)])
        result = analyze_content_depth(text)
        self.assertLessEqual(result["depth_score"], 100)

    def test_empty_text(self):
        result = analyze_content_depth("")
        self.assertEqual(result["word_count"], 0)
        self.assertEqual(result["sentence_count"], 0)

    def test_good_sentence_length_bonus(self):
        words = " ".join(["word"] * 15)
        text = ". ".join([words] * 20) + "."
        result = analyze_content_depth(text)
        self.assertGreater(result["avg_sentence_length"], 5)


class TestAnalyzeContentHtml(unittest.TestCase):
    def test_success_flag(self):
        result = analyze_content_html(MINIMAL_HTML, "https://example.com")
        self.assertTrue(result["success"])

    def test_has_all_fields(self):
        result = analyze_content_html(MINIMAL_HTML, "https://example.com")
        self.assertIn("score", result)
        self.assertIn("eeat", result)
        self.assertIn("content_depth", result)
        self.assertIn("headings", result)
        self.assertIn("korean_analysis", result)
        self.assertIn("issues", result)

    def test_eeat_structure(self):
        result = analyze_content_html(RICH_EXPERTISE_HTML, "https://example.com")
        eeat = result["eeat"]
        self.assertIn("score", eeat)
        self.assertIn("axes", eeat)
        self.assertIn("weakest", eeat)
        self.assertIn("strongest", eeat)
        self.assertIn("experience", eeat)
        self.assertIn("expertise", eeat)
        self.assertIn("authoritativeness", eeat)
        self.assertIn("trust", eeat)

    def test_score_formula(self):
        result = analyze_content_html(RICH_EXPERTISE_HTML, "https://example.com")
        expected = round(
            result["content_depth"]["depth_score"] * 0.4 + result["eeat"]["score"] * 0.6, 1
        )
        self.assertAlmostEqual(result["score"], expected, places=0)

    def test_missing_h1_issue(self):
        result = analyze_content_html(NO_H1_HTML, "https://example.com")
        h1_issues = [i for i in result["issues"] if "H1" in i["message"]]
        self.assertGreater(len(h1_issues), 0)

    def test_multiple_h1_issue(self):
        result = analyze_content_html(MULTI_H1_HTML, "https://example.com")
        multi_h1 = [i for i in result["issues"] if "Multiple H1" in i["message"]]
        self.assertGreater(len(multi_h1), 0)

    def test_thin_content_issue(self):
        result = analyze_content_html(MINIMAL_HTML, "https://example.com")
        thin = [i for i in result["issues"] if "Thin content" in i.get("message", "")]
        self.assertGreater(len(thin), 0)

    def test_korean_detection(self):
        result = analyze_content_html(KOREAN_CONTENT, "https://example.com")
        self.assertTrue(result["korean_analysis"]["is_korean_content"])

    def test_english_detection(self):
        result = analyze_content_html(ENGLISH_CONTENT, "https://example.com")
        self.assertFalse(result["korean_analysis"]["is_korean_content"])

    def test_rich_page_high_score(self):
        combined = """
        <html><body>
        <h1>종합 SEO 가이드: 전문가의 3년 실전 경험</h1>
        <p>작성자: 김박사 (Ph.D 디지털마케팅 전문가)</p>
        <p>제가 직접 3년 동안 SEO 알고리즘과 프레임워크를 분석한 경험을 공유합니다.</p>
        <p>단계별 과정과 시행착오를 거쳐 완성한 최적화 방법론입니다.</p>
        <p>출처: 한국인터넷진흥원 보고서에 따르면 SEO 효과는 45% 향상됩니다.</p>
        <a href="https://kisa.or.kr/data">KISA 보고서</a>
        <a href="https://example.org/study">외부 연구</a>
        <p>ISO 인증 완료, 한국디지털마케팅협회 회원</p>
        <p>연락처: 고객센터 1588-0000</p>
        <p>서울특별시 강남구</p>
        <p>사업자 등록번호: 123-45-67890</p>
        <a href="/privacy">개인정보처리방침</a>
        <a href="/terms">이용약관</a>
        <p>발행일: 2024-01-15</p>
        """ + " ".join(["검색엔진 최적화 전략을 수립합니다." for _ in range(50)]) + """
        <p>분석 결과 데이터에 따르면 성능이 개선되었습니다.</p>
        <img src="/uploads/original/result.png" alt="분석 결과">
        <script type="application/ld+json">{"@type": "Person", "sameAs": ["https://twitter.com/x"]}</script>
        </body></html>
        """
        result = analyze_content_html(combined, "https://example.com")
        self.assertGreater(result["score"], 50)
        self.assertGreater(result["eeat"]["score"], 50)

    def test_empty_url(self):
        result = analyze_content_html(MINIMAL_HTML, "")
        self.assertTrue(result["success"])
        self.assertEqual(result["url"], "")

    def test_headings_in_result(self):
        result = analyze_content_html(MULTI_H1_HTML, "https://example.com")
        self.assertEqual(result["headings"]["h1"], 2)
        self.assertEqual(result["headings"]["h2"], 1)
        self.assertEqual(result["headings"]["h3"], 1)


class TestEeatWeights(unittest.TestCase):
    def test_four_axes(self):
        self.assertEqual(len(EEAT_WEIGHTS), 4)
        self.assertIn("experience", EEAT_WEIGHTS)
        self.assertIn("expertise", EEAT_WEIGHTS)
        self.assertIn("authoritativeness", EEAT_WEIGHTS)
        self.assertIn("trust", EEAT_WEIGHTS)

    def test_expertise_highest_weight(self):
        self.assertEqual(max(EEAT_WEIGHTS, key=EEAT_WEIGHTS.get), "expertise")

    def test_experience_lowest_weight(self):
        self.assertEqual(min(EEAT_WEIGHTS, key=EEAT_WEIGHTS.get), "experience")


class TestSignalDictionaries(unittest.TestCase):
    def test_experience_signals_keys(self):
        expected = {"first_person", "case_study", "original_media", "process_narrative", "temporal_experience"}
        self.assertEqual(set(EXPERIENCE_SIGNALS.keys()), expected)

    def test_expertise_signals_keys(self):
        expected = {"credentials", "technical_depth", "author_bio", "author_schema", "specialized_terms", "data_analysis"}
        self.assertEqual(set(EXPERTISE_SIGNALS.keys()), expected)

    def test_authority_signals_keys(self):
        expected = {"external_citations", "source_attribution", "awards_certs", "institutional_links",
                    "media_mentions", "same_as_links", "industry_affiliation"}
        self.assertEqual(set(AUTHORITY_SIGNALS.keys()), expected)

    def test_trust_signals_keys(self):
        expected = {"https", "privacy_policy", "terms_of_service", "contact_info",
                    "physical_address", "business_registration", "secure_forms", "clear_attribution"}
        self.assertEqual(set(TRUST_SIGNALS.keys()), expected)

    def test_all_signals_are_lists(self):
        for signals in [EXPERIENCE_SIGNALS, EXPERTISE_SIGNALS, AUTHORITY_SIGNALS, TRUST_SIGNALS]:
            for key, patterns in signals.items():
                self.assertIsInstance(patterns, list, f"{key} patterns should be a list")


class TestEdgeCases(unittest.TestCase):
    def test_html_with_entities(self):
        html = "<p>&amp; &lt; &gt; &quot;</p>"
        result = analyze_content_html(html, "https://example.com")
        self.assertTrue(result["success"])

    def test_nested_tags(self):
        html = "<div><div><div><p>Deep <b><i>nesting</i></b></p></div></div></div>"
        text = extract_text_content(html)
        self.assertIn("Deep", text)
        self.assertIn("nesting", text)

    def test_large_html(self):
        html = "<html><body>" + "<p>Paragraph content here.</p>\n" * 1000 + "</body></html>"
        result = analyze_content_html(html, "https://example.com")
        self.assertTrue(result["success"])

    def test_special_characters_in_content(self):
        html = "<p>Price: ₩50,000 (약 $40). Email: test@example.com</p>"
        result = analyze_content_html(html, "https://example.com")
        self.assertTrue(result["success"])

    def test_score_range(self):
        for html in [EMPTY_HTML, MINIMAL_HTML, RICH_EXPERIENCE_HTML, RICH_TRUST_HTML]:
            result = analyze_content_html(html, "https://example.com")
            self.assertGreaterEqual(result["score"], 0)
            self.assertLessEqual(result["score"], 100)
            self.assertGreaterEqual(result["eeat"]["score"], 0)
            self.assertLessEqual(result["eeat"]["score"], 100)

    def test_english_experience_signals(self):
        html = "<p>I have been working on this for 5 years. We've tested it extensively in practice.</p>"
        result = score_experience(html)
        self.assertGreater(result["details"]["first_person"], 0)
        self.assertGreater(result["details"]["temporal_experience"], 0)

    def test_english_authority_signals(self):
        html = '<p>As featured in major press. Source: MIT study.</p><a href="https://mit.edu/paper">Paper</a>'
        result = score_authoritativeness(html)
        self.assertGreater(result["details"]["institutional_links"], 0)

    def test_english_trust_signals(self):
        html = '<p>Contact us for support. Terms of service apply. Privacy policy.</p>'
        result = score_trust(html, "https://example.com")
        self.assertTrue(result["details"]["contact_info"])
        self.assertTrue(result["details"]["terms_of_service"])
        self.assertTrue(result["details"]["privacy_policy"])


if __name__ == "__main__":
    unittest.main()

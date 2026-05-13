"""Tests for SEO technical 8-dimension quality scoring."""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from seo_technical import (
    analyze_meta_tags, evaluate_meta_quality,
    analyze_heading_structure, analyze_images, analyze_links,
    score_meta_quality, score_heading_structure, score_image_optimization,
    score_link_health, score_mobile_readiness, score_indexability,
    score_security_signals, score_performance_signals,
    analyze_technical_html, DIMENSION_WEIGHTS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

GOOD_HTML = """
<html lang="ko">
<head>
<title>Three-O SEO 최적화 가이드 - 검색엔진 최적화 전문</title>
<meta name="description" content="Three-O 플랫폼의 SEO 최적화 가이드입니다. 검색엔진 최적화부터 AI 가시성까지 통합적으로 분석하고 개선하는 방법을 알려드립니다. 한국 시장 특화 최적화 전략을 제공합니다.">
<meta property="og:title" content="Three-O SEO Guide">
<meta property="og:description" content="SEO optimization guide">
<meta property="og:image" content="https://example.com/og.png">
<meta property="og:url" content="https://example.com/guide">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Three-O SEO Guide">
<meta name="twitter:description" content="SEO optimization guide">
<link rel="canonical" href="https://example.com/guide">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="index, follow">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preload" as="style" href="main.css">
<style>body{margin:0;font-family:sans-serif;display:flex}</style>
<script type="application/ld+json">{"@type":"Organization","name":"Test"}</script>
</head>
<body>
<header><nav>
<a href="/" title="Home">Home</a>
<a href="/about" title="About">About</a>
<a href="/seo" title="SEO">SEO Guide</a>
<a href="/geo" title="GEO">GEO Guide</a>
<a href="/contact" title="Contact">Contact</a>
</nav></header>
<main>
<h1>SEO 최적화 가이드</h1>
<h2>기본 원칙</h2>
<p>Content here</p>
<h2>고급 전략</h2>
<h3>메타 태그</h3>
<img src="a.webp" alt="SEO diagram" loading="lazy" width="800" height="600" srcset="a-2x.webp 2x" decoding="async">
<img src="b.webp" alt="GEO flow" loading="lazy" width="600" height="400">
<a href="/about">About</a>
<a href="https://google.com">Google</a>
</main>
<footer><a href="/privacy">Privacy</a></footer>
</body></html>
"""

BAD_HTML = """
<html>
<head>
<title>Hi</title>
</head>
<body>
<h1>First</h1>
<h1>Second</h1>
<h3>Skipped H2</h3>
<img src="a.jpg">
<img src="b.jpg">
<img src="c.jpg">
</body></html>
"""


def _make_html(body="", head="", lang="ko"):
    return f'<html lang="{lang}"><head>{head}</head><body>{body}</body></html>'


# ===========================================================================
# Backward-compat: analyze_meta_tags
# ===========================================================================

class TestMetaTags(unittest.TestCase):
    def test_extract_title(self):
        meta = analyze_meta_tags(GOOD_HTML)
        self.assertIn("title", meta)
        self.assertIn("SEO", meta["title"])

    def test_extract_description(self):
        meta = analyze_meta_tags(GOOD_HTML)
        self.assertIn("description", meta)
        self.assertGreater(len(meta["description"]), 80)

    def test_extract_canonical(self):
        meta = analyze_meta_tags(GOOD_HTML)
        self.assertIn("canonical", meta)
        self.assertTrue(meta["canonical"].startswith("https"))

    def test_extract_og_tags(self):
        meta = analyze_meta_tags(GOOD_HTML)
        self.assertIn("og:title", meta)
        self.assertIn("og:image", meta)

    def test_minimal_html(self):
        meta = analyze_meta_tags("<html><head></head><body></body></html>")
        self.assertNotIn("title", meta)
        self.assertNotIn("description", meta)


# ===========================================================================
# Backward-compat: evaluate_meta_quality
# ===========================================================================

class TestMetaQuality(unittest.TestCase):
    def test_good_meta_high_score(self):
        meta = analyze_meta_tags(GOOD_HTML)
        quality = evaluate_meta_quality(meta, "https://example.com/guide")
        self.assertGreater(quality["score"], 70)

    def test_missing_meta_low_score(self):
        meta = analyze_meta_tags(BAD_HTML)
        quality = evaluate_meta_quality(meta, "https://example.com")
        self.assertLess(quality["score"], 40)

    def test_title_length_check(self):
        meta = {"title": "Hi"}
        quality = evaluate_meta_quality(meta, "https://example.com")
        issues = [i["message"] for i in quality["issues"]]
        self.assertTrue(any("Title length" in m or "title" in m.lower() for m in issues))

    def test_missing_title_critical(self):
        quality = evaluate_meta_quality({}, "https://example.com")
        severities = [i["severity"] for i in quality["issues"]]
        self.assertIn("critical", severities)

    def test_optimal_title_no_length_issue(self):
        meta = {"title": "Perfect Title Length for SEO Optimization"}
        quality = evaluate_meta_quality(meta, "https://example.com")
        title_len_issues = [i for i in quality["issues"] if "Title length" in i.get("message", "")]
        self.assertEqual(len(title_len_issues), 0)

    def test_duplicate_desc_penalized(self):
        meta = {"title": "Same text", "description": "Same text"}
        quality = evaluate_meta_quality(meta, "https://example.com")
        issues = [i["message"] for i in quality["issues"]]
        self.assertTrue(any("duplicates" in m.lower() for m in issues))

    def test_http_canonical_on_https_warned(self):
        meta = {"canonical": "http://example.com/page"}
        quality = evaluate_meta_quality(meta, "https://example.com/page")
        issues = [i["message"] for i in quality["issues"]]
        self.assertTrue(any("HTTP" in m for m in issues))


# ===========================================================================
# Backward-compat: analyze_heading_structure
# ===========================================================================

class TestHeadingStructure(unittest.TestCase):
    def test_good_hierarchy(self):
        result = analyze_heading_structure(GOOD_HTML)
        self.assertEqual(result["h1_count"], 1)
        self.assertEqual(result["h2_count"], 2)
        self.assertTrue(result["hierarchy_valid"])
        self.assertEqual(len(result["issues"]), 0)

    def test_multiple_h1(self):
        result = analyze_heading_structure(BAD_HTML)
        self.assertEqual(result["h1_count"], 2)
        self.assertFalse(result["hierarchy_valid"])
        issues = [i["message"] for i in result["issues"]]
        self.assertTrue(any("Multiple H1" in m for m in issues))

    def test_h3_without_h2(self):
        result = analyze_heading_structure(BAD_HTML)
        issues = [i["message"] for i in result["issues"]]
        self.assertTrue(any("H3 used without H2" in m for m in issues))

    def test_no_h1(self):
        html = "<html><body><h2>Section</h2><p>text</p></body></html>"
        result = analyze_heading_structure(html)
        self.assertEqual(result["h1_count"], 0)
        issues = [i["message"] for i in result["issues"]]
        self.assertTrue(any("Missing H1" in m for m in issues))


# ===========================================================================
# Backward-compat: analyze_images / analyze_links
# ===========================================================================

class TestImageAnalysis(unittest.TestCase):
    def test_all_with_alt(self):
        result = analyze_images(GOOD_HTML)
        self.assertEqual(result["with_alt"], result["total"])
        self.assertEqual(result["coverage"], 100.0)

    def test_missing_alt(self):
        result = analyze_images(BAD_HTML)
        self.assertEqual(result["total"], 3)
        self.assertEqual(result["missing_alt"], 3)

    def test_no_images(self):
        html = "<html><body><p>No images</p></body></html>"
        result = analyze_images(html)
        self.assertEqual(result["total"], 0)

    def test_missing_alt_issue(self):
        result = analyze_images(BAD_HTML)
        self.assertGreater(len(result["issues"]), 0)


class TestLinkAnalysis(unittest.TestCase):
    def test_internal_external(self):
        result = analyze_links(GOOD_HTML, "https://example.com/guide")
        self.assertGreater(result["internal"], 0)
        self.assertGreater(result["external"], 0)

    def test_total_count(self):
        result = analyze_links(GOOD_HTML, "https://example.com/guide")
        self.assertEqual(result["total"], result["internal"] + result["external"])

    def test_no_links(self):
        html = "<html><body><p>No links</p></body></html>"
        result = analyze_links(html, "https://example.com")
        self.assertEqual(result["total"], 0)


# ===========================================================================
# score_meta_quality
# ===========================================================================

class TestScoreMetaQuality(unittest.TestCase):
    def test_good_html(self):
        result = score_meta_quality(GOOD_HTML, "https://example.com/guide")
        self.assertGreaterEqual(result["score"], 70)
        self.assertIn("details", result)

    def test_bad_html(self):
        result = score_meta_quality(BAD_HTML)
        self.assertLessEqual(result["score"], 40)

    def test_charset_bonus(self):
        html = _make_html(head='<meta charset="utf-8"><title>Test Title for Good Length</title>')
        result = score_meta_quality(html)
        self.assertTrue(result["details"]["charset_utf8"])

    def test_score_capped(self):
        result = score_meta_quality(GOOD_HTML)
        self.assertLessEqual(result["score"], 100)


# ===========================================================================
# score_heading_structure
# ===========================================================================

class TestScoreHeadingStructure(unittest.TestCase):
    def test_good_hierarchy_high(self):
        html = "<html><body><h1>Title Here OK</h1><h2>Sub A</h2><h3>Detail</h3><h2>Sub B</h2><h3>More</h3><h4>Deep</h4></body></html>"
        result = score_heading_structure(html)
        self.assertGreaterEqual(result["score"], 70)

    def test_no_headings_low(self):
        html = "<html><body><p>No headings at all</p></body></html>"
        result = score_heading_structure(html)
        self.assertLessEqual(result["score"], 10)

    def test_multiple_h1_lower(self):
        html_multi = "<html><body><h1>A</h1><h1>B</h1><h2>C</h2></body></html>"
        html_single = "<html><body><h1>A Good Title</h1><h2>C</h2></body></html>"
        r_multi = score_heading_structure(html_multi)
        r_single = score_heading_structure(html_single)
        self.assertGreater(r_single["score"], r_multi["score"])

    def test_skip_penalty(self):
        html = "<html><body><h1>Title</h1><h3>Skipped</h3></body></html>"
        result = score_heading_structure(html)
        self.assertTrue(result["details"]["skip_penalty"])

    def test_heading_depth(self):
        html = "<html><body><h1>T</h1><h2>S</h2><h3>D</h3><h4>DD</h4></body></html>"
        result = score_heading_structure(html)
        self.assertEqual(result["details"]["heading_depth"], 4)

    def test_h1_length_scoring(self):
        html_good = "<html><body><h1>A Proper Length Heading</h1></body></html>"
        html_bad = "<html><body><h1>X</h1></body></html>"
        r_good = score_heading_structure(html_good)
        r_bad = score_heading_structure(html_bad)
        self.assertGreater(r_good["score"], r_bad["score"])

    def test_score_capped(self):
        html = "<html><body><h1>Good Heading Title</h1><h2>S1</h2><h2>S2</h2><h2>S3</h2><h3>D1</h3><h3>D2</h3><h4>DD</h4></body></html>"
        result = score_heading_structure(html)
        self.assertLessEqual(result["score"], 100)


# ===========================================================================
# score_image_optimization
# ===========================================================================

class TestScoreImageOptimization(unittest.TestCase):
    def test_no_images_full_score(self):
        html = "<html><body><p>Text only</p></body></html>"
        result = score_image_optimization(html)
        self.assertEqual(result["score"], 100.0)

    def test_fully_optimized(self):
        result = score_image_optimization(GOOD_HTML)
        self.assertGreaterEqual(result["score"], 60)

    def test_no_alt_low(self):
        html = '<html><body><img src="a.jpg"><img src="b.jpg"></body></html>'
        result = score_image_optimization(html)
        self.assertLessEqual(result["score"], 20)

    def test_lazy_loading_detected(self):
        html = '<html><body><img src="a.jpg" alt="A" loading="lazy"><img src="b.jpg" alt="B" loading="eager"></body></html>'
        result = score_image_optimization(html)
        self.assertEqual(result["details"]["lazy_loading"], 1)
        self.assertEqual(result["details"]["eager_loading"], 1)

    def test_srcset_detected(self):
        html = '<html><body><img src="a.jpg" alt="A" srcset="a-2x.jpg 2x"></body></html>'
        result = score_image_optimization(html)
        self.assertEqual(result["details"]["srcset_count"], 1)

    def test_modern_format(self):
        html = '<html><body><img src="a.webp" alt="A"><img src="b.avif" alt="B"></body></html>'
        result = score_image_optimization(html)
        self.assertEqual(result["details"]["modern_format_count"], 2)

    def test_explicit_sizing(self):
        html = '<html><body><img src="a.jpg" alt="A" width="800" height="600"></body></html>'
        result = score_image_optimization(html)
        self.assertGreaterEqual(result["details"]["explicitly_sized"], 1)

    def test_decoding_async(self):
        html = '<html><body><img src="a.jpg" alt="A" decoding="async"></body></html>'
        result = score_image_optimization(html)
        self.assertEqual(result["details"]["decoding_async"], 1)

    def test_picture_elements(self):
        html = '<html><body><picture><source srcset="a.webp" type="image/webp"><img src="a.jpg" alt="A"></picture></body></html>'
        result = score_image_optimization(html)
        self.assertEqual(result["details"]["picture_elements"], 1)


# ===========================================================================
# score_link_health
# ===========================================================================

class TestScoreLinkHealth(unittest.TestCase):
    def test_good_links(self):
        result = score_link_health(GOOD_HTML, "https://example.com")
        self.assertGreaterEqual(result["score"], 50)

    def test_no_links_low(self):
        html = "<html><body><p>No links</p></body></html>"
        result = score_link_health(html)
        self.assertLessEqual(result["score"], 15)

    def test_nav_links_bonus(self):
        nav = '<nav>' + ''.join(f'<a href="/p{i}">Page {i}</a>' for i in range(8)) + '</nav>'
        html = _make_html(body=nav)
        result = score_link_health(html)
        self.assertGreaterEqual(result["details"]["nav_link_count"], 8)

    def test_breadcrumb_detected(self):
        html = _make_html(body='<nav aria-label="breadcrumb"><a href="/">Home</a> > <a href="/cat">Cat</a></nav>')
        result = score_link_health(html)
        self.assertTrue(result["details"]["has_breadcrumb"])

    def test_generic_anchor_penalty(self):
        body = '<a href="/a">click here</a><a href="/b">here</a><a href="/c">more</a>'
        html = _make_html(body=body)
        result = score_link_health(html)
        self.assertGreater(result["details"]["generic_anchors"], 0)

    def test_nofollow_detected(self):
        html = _make_html(body='<a href="/a" rel="nofollow">Link</a><a href="/b">Normal</a>')
        result = score_link_health(html)
        self.assertEqual(result["details"]["nofollow_count"], 1)

    def test_titled_links(self):
        html = _make_html(body='<a href="/a" title="About page">About</a>')
        result = score_link_health(html)
        self.assertGreaterEqual(result["details"]["titled_links"], 1)

    def test_score_never_negative(self):
        body = '<a href="/a">click here</a>' * 20
        html = _make_html(body=body)
        result = score_link_health(html)
        self.assertGreaterEqual(result["score"], 0)


# ===========================================================================
# score_mobile_readiness
# ===========================================================================

class TestScoreMobileReadiness(unittest.TestCase):
    def test_optimal_viewport(self):
        html = _make_html(head='<meta name="viewport" content="width=device-width, initial-scale=1.0">')
        result = score_mobile_readiness(html)
        self.assertTrue(any("optimal" in s for s in result["signals"]))

    def test_missing_viewport(self):
        html = "<html><body><p>No viewport</p></body></html>"
        result = score_mobile_readiness(html)
        self.assertTrue(any("missing" in s for s in result["signals"]))
        self.assertLessEqual(result["score"], 30)

    def test_zoom_disabled_penalty(self):
        html = _make_html(head='<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">')
        result = score_mobile_readiness(html)
        self.assertTrue(any("zoom disabled" in s for s in result["signals"]))

    def test_responsive_breakpoints(self):
        css = '<style>@media (max-width: 768px){} @media (max-width: 480px){} @media (min-width: 1024px){}</style>'
        html = _make_html(head=css)
        result = score_mobile_readiness(html)
        self.assertTrue(any("responsive" in s for s in result["signals"]))

    def test_tel_links(self):
        html = _make_html(body='<a href="tel:010-1234-5678">Call us</a>')
        result = score_mobile_readiness(html)
        self.assertTrue(any("click-to-call" in s for s in result["signals"]))

    def test_fixed_width_penalty(self):
        html = _make_html(head='<style>.container{width:1200px}</style>')
        result = score_mobile_readiness(html)
        self.assertTrue(any("fixed width" in s for s in result["signals"]))

    def test_theme_color(self):
        html = _make_html(head='<meta name="theme-color" content="#ffffff">')
        result = score_mobile_readiness(html)
        self.assertTrue(any("theme-color" in s for s in result["signals"]))

    def test_flex_grid_bonus(self):
        html = _make_html(head='<style>.row{display:flex}.grid{display:grid}</style>')
        result = score_mobile_readiness(html)
        self.assertTrue(any("modern layout" in s for s in result["signals"]))

    def test_good_html_high_score(self):
        result = score_mobile_readiness(GOOD_HTML)
        self.assertGreaterEqual(result["score"], 30)

    def test_score_capped(self):
        result = score_mobile_readiness(GOOD_HTML)
        self.assertLessEqual(result["score"], 100)


# ===========================================================================
# score_indexability
# ===========================================================================

class TestScoreIndexability(unittest.TestCase):
    def test_good_indexability(self):
        result = score_indexability(GOOD_HTML)
        self.assertGreaterEqual(result["score"], 60)

    def test_noindex_penalty(self):
        html = _make_html(head='<meta name="robots" content="noindex, nofollow">')
        result = score_indexability(html)
        self.assertTrue(any("noindex" in s for s in result["signals"]))

    def test_canonical_https(self):
        html = _make_html(head='<link rel="canonical" href="https://example.com/page">')
        result = score_indexability(html)
        self.assertTrue(any("canonical: https" in s for s in result["signals"]))

    def test_canonical_relative(self):
        html = _make_html(head='<link rel="canonical" href="/page">')
        result = score_indexability(html)
        self.assertTrue(any("relative" in s for s in result["signals"]))

    def test_lang_attribute(self):
        html = '<html lang="ko"><head></head><body></body></html>'
        result = score_indexability(html)
        self.assertTrue(any("lang: ko" in s for s in result["signals"]))

    def test_hreflang_multi(self):
        head = '<link rel="alternate" hreflang="ko" href="/ko"><link rel="alternate" hreflang="en" href="/en"><link rel="alternate" hreflang="x-default" href="/">'
        html = _make_html(head=head)
        result = score_indexability(html)
        self.assertTrue(any("3 languages" in s for s in result["signals"]))
        self.assertTrue(any("x-default" in s for s in result["signals"]))

    def test_json_ld_present(self):
        html = _make_html(head='<script type="application/ld+json">{"@type":"WebSite"}</script>')
        result = score_indexability(html)
        self.assertTrue(any("JSON-LD" in s for s in result["signals"]))

    def test_title_and_desc(self):
        html = _make_html(head='<title>Test Title</title><meta name="description" content="Test desc">')
        result = score_indexability(html)
        self.assertTrue(any("title" in s for s in result["signals"]))
        self.assertTrue(any("meta description" in s for s in result["signals"]))

    def test_score_never_negative(self):
        html = _make_html(head='<meta name="robots" content="noindex, nofollow, noarchive">')
        result = score_indexability(html)
        self.assertGreaterEqual(result["score"], 0)

    def test_score_capped(self):
        result = score_indexability(GOOD_HTML)
        self.assertLessEqual(result["score"], 100)


# ===========================================================================
# score_security_signals
# ===========================================================================

class TestScoreSecuritySignals(unittest.TestCase):
    def test_https_bonus(self):
        html = "<html><body></body></html>"
        result = score_security_signals(html, "https://example.com")
        self.assertTrue(any("HTTPS" in s for s in result["signals"]))

    def test_http_no_bonus(self):
        html = "<html><body></body></html>"
        result = score_security_signals(html, "http://example.com")
        self.assertTrue(any("HTTP only" in s for s in result["signals"]))

    def test_csp_meta(self):
        html = _make_html(head='<meta http-equiv="Content-Security-Policy" content="default-src \'self\'">')
        result = score_security_signals(html, "https://example.com")
        self.assertTrue(any("CSP" in s for s in result["signals"]))

    def test_mixed_content_penalty(self):
        html = _make_html(body='<img src="http://cdn.example.com/img.jpg"><script src="http://cdn.example.com/script.js"></script>')
        result = score_security_signals(html, "https://example.com")
        self.assertTrue(any("mixed content" in s for s in result["signals"]))

    def test_no_mixed_content(self):
        html = _make_html(body='<img src="https://cdn.example.com/img.jpg">')
        result = score_security_signals(html, "https://example.com")
        self.assertTrue(any("no mixed content" in s for s in result["signals"]))

    def test_sri_detected(self):
        html = _make_html(body='<script src="app.js" integrity="sha384-abc123" crossorigin="anonymous"></script>')
        result = score_security_signals(html, "https://example.com")
        self.assertTrue(any("SRI" in s for s in result["signals"]))

    def test_inline_event_handlers_penalty(self):
        body = ''.join(f'<div onclick="handler{i}()">Click</div>' for i in range(8))
        html = _make_html(body=body)
        result = score_security_signals(html, "https://example.com")
        self.assertTrue(any("inline event" in s for s in result["signals"]))

    def test_insecure_form_action(self):
        html = _make_html(body='<form action="http://api.example.com/submit"><input type="text"></form>')
        result = score_security_signals(html, "https://example.com")
        self.assertTrue(any("insecure form" in s for s in result["signals"]))

    def test_secure_form_action(self):
        html = _make_html(body='<form action="https://api.example.com/submit"><input type="text"></form>')
        result = score_security_signals(html, "https://example.com")
        self.assertTrue(any("secure form" in s for s in result["signals"]))

    def test_score_never_negative(self):
        body = '<img src="http://a.com/1"><img src="http://a.com/2"><img src="http://a.com/3"><img src="http://a.com/4"><img src="http://a.com/5">'
        body += ''.join(f'<div onclick="h{i}()">X</div>' for i in range(10))
        body += '<form action="http://a.com/s"></form>'
        html = _make_html(body=body)
        result = score_security_signals(html, "http://example.com")
        self.assertGreaterEqual(result["score"], 0)


# ===========================================================================
# score_performance_signals
# ===========================================================================

class TestScorePerformanceSignals(unittest.TestCase):
    def test_resource_hints(self):
        head = '<link rel="preconnect" href="https://a.com"><link rel="preload" as="style" href="m.css"><link rel="dns-prefetch" href="//b.com"><link rel="prefetch" href="/next.js">'
        html = _make_html(head=head)
        result = score_performance_signals(html)
        self.assertTrue(any("resource hints" in s for s in result["signals"]))

    def test_critical_css(self):
        html = _make_html(head='<style>body{margin:0}</style>')
        result = score_performance_signals(html)
        self.assertTrue(any("critical CSS" in s for s in result["signals"]))

    def test_async_defer_scripts(self):
        scripts = '<script src="a.js" async></script><script src="b.js" defer></script>'
        html = _make_html(body=scripts)
        result = score_performance_signals(html)
        self.assertTrue(any("script optimization" in s for s in result["signals"]))

    def test_no_scripts_bonus(self):
        html = "<html><body><p>No scripts</p></body></html>"
        result = score_performance_signals(html)
        self.assertTrue(any("no blocking scripts" in s for s in result["signals"]))

    def test_module_scripts(self):
        html = _make_html(body='<script type="module" src="app.js"></script>')
        result = score_performance_signals(html)
        self.assertTrue(any("ES modules" in s for s in result["signals"]))

    def test_lazy_images(self):
        body = '<img src="a.jpg" loading="lazy"><img src="b.jpg" loading="lazy"><img src="c.jpg" loading="lazy">'
        html = _make_html(body=body)
        result = score_performance_signals(html)
        self.assertTrue(any("lazy images" in s for s in result["signals"]))

    def test_font_display(self):
        html = _make_html(head='<style>@font-face{font-family:X;font-display:swap}</style>')
        result = score_performance_signals(html)
        self.assertTrue(any("font-display" in s for s in result["signals"]))

    def test_preloaded_fonts(self):
        html = _make_html(head='<link rel="preload" as="font" href="font.woff2" crossorigin>')
        result = score_performance_signals(html)
        self.assertTrue(any("preloaded fonts" in s for s in result["signals"]))

    def test_css_containment(self):
        html = _make_html(head='<style>.card{contain:content;will-change:transform}</style>')
        result = score_performance_signals(html)
        self.assertTrue(any("containment" in s for s in result["signals"]))

    def test_good_html_has_signals(self):
        result = score_performance_signals(GOOD_HTML)
        self.assertGreater(result["score"], 0)
        self.assertGreater(len(result["signals"]), 0)

    def test_score_capped(self):
        result = score_performance_signals(GOOD_HTML)
        self.assertLessEqual(result["score"], 100)


# ===========================================================================
# analyze_technical_html (integration)
# ===========================================================================

class TestAnalyzeTechnicalHTML(unittest.TestCase):
    def test_good_page(self):
        result = analyze_technical_html(GOOD_HTML, "https://example.com/guide")
        self.assertGreaterEqual(result["score"], 50)
        self.assertEqual(len(result["dimensions"]), 8)

    def test_bad_page(self):
        result = analyze_technical_html(BAD_HTML)
        self.assertLessEqual(result["score"], 40)

    def test_all_dimensions_present(self):
        result = analyze_technical_html(GOOD_HTML)
        for dim in DIMENSION_WEIGHTS:
            self.assertIn(dim, result["dimensions"])
            self.assertGreaterEqual(result["dimensions"][dim], 0)
            self.assertLessEqual(result["dimensions"][dim], 100)

    def test_weighted_sum_correct(self):
        result = analyze_technical_html(GOOD_HTML)
        expected = round(sum(result["dimensions"][k] * DIMENSION_WEIGHTS[k] for k in DIMENSION_WEIGHTS), 1)
        self.assertAlmostEqual(result["score"], expected, places=1)

    def test_issues_present_for_bad(self):
        result = analyze_technical_html(BAD_HTML)
        self.assertGreater(len(result["issues"]), 0)

    def test_backward_compat_section_scores(self):
        result = analyze_technical_html(GOOD_HTML)
        self.assertIn("section_scores", result)
        self.assertIn("meta_quality", result["section_scores"])
        self.assertIn("headings", result["section_scores"])

    def test_details_per_dimension(self):
        result = analyze_technical_html(GOOD_HTML)
        self.assertIn("details", result)
        for dim in DIMENSION_WEIGHTS:
            self.assertIn(dim, result["details"])
            self.assertIn("score", result["details"][dim])

    def test_empty_html(self):
        result = analyze_technical_html("")
        self.assertIsInstance(result["score"], float)
        self.assertGreaterEqual(result["score"], 0)

    def test_minimal_html(self):
        result = analyze_technical_html("<html><body>x</body></html>")
        self.assertLessEqual(result["score"], 40)


# ===========================================================================
# Edge cases
# ===========================================================================

class TestEdgeCases(unittest.TestCase):
    def test_dimension_weights_sum_to_1(self):
        total = sum(DIMENSION_WEIGHTS.values())
        self.assertAlmostEqual(total, 1.0, places=5)

    def test_all_scores_bounded(self):
        for html, url in [
            (GOOD_HTML, "https://example.com"),
            (BAD_HTML, "https://example.com"),
            ("", "https://example.com"),
            ("<html><body></body></html>", "http://example.com"),
        ]:
            result = analyze_technical_html(html, url)
            self.assertGreaterEqual(result["score"], 0)
            self.assertLessEqual(result["score"], 100)
            for dim in DIMENSION_WEIGHTS:
                self.assertGreaterEqual(result["dimensions"][dim], 0, f"{dim} below 0 for {url}")
                self.assertLessEqual(result["dimensions"][dim], 100, f"{dim} above 100 for {url}")

    def test_korean_content(self):
        html = '<html lang="ko"><head><title>한국어 SEO 최적화 가이드</title><meta name="description" content="한국어로 작성된 SEO 가이드입니다. 검색엔진 최적화 전략을 상세히 설명합니다. 이 가이드를 통해 웹사이트 트래픽을 늘려보세요."></head><body><h1>최적화 가이드</h1></body></html>'
        result = analyze_technical_html(html)
        self.assertGreater(result["score"], 0)


if __name__ == "__main__":
    unittest.main()

"""Tests for AAO rendering 6-dimension quality scoring."""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from aao_rendering import (
    detect_frameworks,
    detect_hydration_pattern,
    score_ssr_quality,
    score_js_dependency,
    score_semantic_structure,
    score_content_accessibility,
    score_agent_crawlability,
    score_rendering_resilience,
    analyze_rendering_html,
    DIMENSION_WEIGHTS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_html(body="", head="", scripts="", lang="ko"):
    return f'<html lang="{lang}"><head>{head}</head><body>{body}{scripts}</body></html>'


def _rich_body(word_count=300):
    words = " ".join(f"word{i}" for i in range(word_count))
    return f"<h1>Title Here</h1><p>{words}</p><p>More content with details and facts.</p>"


def _many_scripts(n=20):
    return "".join(f'<script src="script{i}.js"></script>' for i in range(n))


def _semantic_body():
    return (
        '<header><nav><a href="/a">A</a><a href="/b">B</a></nav></header>'
        '<main><article><h1>Title</h1><section><h2>Sub</h2><p>Content here.</p></section></article></main>'
        '<aside>Sidebar</aside><footer>Footer</footer>'
    )


def _meta_head():
    return (
        '<title>A Good Title for Testing</title>'
        '<meta name="description" content="A proper meta description that is between fifty and one hundred sixty characters long for optimal display.">'
        '<link rel="canonical" href="https://example.com/page">'
        '<meta property="og:title" content="Title">'
        '<meta property="og:description" content="Desc">'
        '<meta property="og:image" content="img.jpg">'
        '<meta property="og:url" content="https://example.com">'
        '<meta property="og:type" content="website">'
        '<meta name="twitter:card" content="summary_large_image">'
        '<meta charset="utf-8">'
        '<script type="application/ld+json">{"@type":"Organization","name":"Test"}</script>'
    )


# ===========================================================================
# detect_frameworks
# ===========================================================================

class TestDetectFrameworks(unittest.TestCase):
    def test_nextjs(self):
        html = '<script id="__NEXT_DATA__" type="application/json">{}</script>'
        self.assertIn("Next.js", detect_frameworks(html))

    def test_nuxtjs(self):
        html = '<script src="/_nuxt/app.js"></script>'
        self.assertIn("Nuxt.js", detect_frameworks(html))

    def test_react(self):
        html = '<div data-reactroot>content</div>'
        self.assertIn("React", detect_frameworks(html))

    def test_vue(self):
        html = '<div data-v-abc123ef class="comp"></div>'
        self.assertIn("Vue.js", detect_frameworks(html))

    def test_angular(self):
        html = '<div ng-app="myApp" ng-controller="ctrl"></div>'
        self.assertIn("Angular", detect_frameworks(html))

    def test_svelte(self):
        html = '<div class="svelte-abc123">content</div>'
        self.assertIn("Svelte", detect_frameworks(html))

    def test_remix(self):
        html = '<script>window.__remix = {}</script>'
        self.assertIn("Remix", detect_frameworks(html))

    def test_astro(self):
        html = '<astro-island uid="abc"></astro-island>'
        self.assertIn("Astro", detect_frameworks(html))

    def test_gatsby(self):
        html = '<div id="___gatsby"><div>content</div></div>'
        self.assertIn("Gatsby", detect_frameworks(html))

    def test_no_framework(self):
        html = "<html><body><p>Plain HTML page</p></body></html>"
        self.assertEqual(detect_frameworks(html), [])

    def test_multiple_frameworks(self):
        html = '<div data-reactroot></div><script src="/_next/static/chunk.js"></script>'
        fw = detect_frameworks(html)
        self.assertIn("Next.js", fw)
        self.assertIn("React", fw)


# ===========================================================================
# detect_hydration_pattern
# ===========================================================================

class TestDetectHydration(unittest.TestCase):
    def test_static_no_framework(self):
        html = _make_html(body=_rich_body(200))
        self.assertEqual(detect_hydration_pattern(html, []), "static")

    def test_csr_empty_root(self):
        html = '<html><body><div id="root"></div></body></html>'
        self.assertEqual(detect_hydration_pattern(html, ["React"]), "csr")

    def test_ssr_hydrate(self):
        html = _make_html(body=_rich_body(200))
        self.assertEqual(detect_hydration_pattern(html, ["Next.js"]), "ssr_hydrate")

    def test_hybrid_non_ssr_framework_with_content(self):
        html = _make_html(body=_rich_body(200))
        self.assertEqual(detect_hydration_pattern(html, ["React"]), "hybrid")

    def test_csr_low_content(self):
        html = '<html><body><div id="app"></div><p>loading</p></body></html>'
        self.assertEqual(detect_hydration_pattern(html, ["Vue.js"]), "csr")


# ===========================================================================
# score_ssr_quality
# ===========================================================================

class TestScoreSSRQuality(unittest.TestCase):
    def test_rich_ssr_content(self):
        html = _make_html(body=_rich_body(400))
        result = score_ssr_quality(html)
        self.assertGreaterEqual(result["score"], 60)
        self.assertIn("word_count", result["details"])
        self.assertGreaterEqual(result["details"]["word_count"], 300)

    def test_empty_page(self):
        html = "<html><body></body></html>"
        result = score_ssr_quality(html)
        self.assertLessEqual(result["score"], 20)

    def test_csr_empty_root(self):
        html = '<html><body><div id="root"></div></body></html>'
        result = score_ssr_quality(html)
        self.assertLessEqual(result["score"], 15)

    def test_h1_bonus(self):
        html = _make_html(body="<h1>Title</h1>" + "<p>" + " ".join(["word"] * 150) + "</p>")
        result = score_ssr_quality(html)
        self.assertTrue(result["details"]["h1_in_ssr"])

    def test_noscript_bonus(self):
        body = _rich_body(200) + '<noscript><p>JavaScript를 활성화해주세요. 이 사이트는 JS가 필요합니다.</p></noscript>'
        html = _make_html(body=body)
        result = score_ssr_quality(html)
        self.assertTrue(result["details"]["has_noscript"])

    def test_good_text_ratio(self):
        body = "<p>" + " ".join(["content"] * 500) + "</p>"
        html = _make_html(body=body)
        result = score_ssr_quality(html)
        self.assertGreaterEqual(result["details"]["text_to_html_ratio"], 0.08)

    def test_low_text_ratio_heavy_markup(self):
        markup = "".join(f'<div class="layer-{i}"><span class="x-{i}"></span></div>' for i in range(200))
        html = _make_html(body=markup + "<p>tiny</p>")
        result = score_ssr_quality(html)
        self.assertLessEqual(result["details"]["text_to_html_ratio"], 0.05)

    def test_lists_and_tables_counted(self):
        body = "<h1>Title</h1><ul><li>A</li><li>B</li></ul><table><tr><td>Data</td></tr></table>" + "<p>" + " ".join(["w"] * 120) + "</p>"
        html = _make_html(body=body)
        result = score_ssr_quality(html)
        self.assertGreaterEqual(result["details"]["lists"], 1)
        self.assertGreaterEqual(result["details"]["tables"], 1)

    def test_hydration_detected(self):
        html = '<html><body><script id="__NEXT_DATA__">{}</script><h1>SSR Title</h1>' + "<p>" + " ".join(["w"] * 200) + "</p></body></html>"
        result = score_ssr_quality(html)
        self.assertEqual(result["details"]["hydration_pattern"], "ssr_hydrate")

    def test_score_capped_at_100(self):
        body = "<h1>T</h1>" + "".join(f"<h2>S{i}</h2><p>" + " ".join(["w"] * 80) + "</p>" for i in range(10))
        body += '<noscript><p>Long fallback content for the page.</p></noscript>'
        html = _make_html(body=body)
        result = score_ssr_quality(html)
        self.assertLessEqual(result["score"], 100)


# ===========================================================================
# score_js_dependency
# ===========================================================================

class TestScoreJSDependency(unittest.TestCase):
    def test_no_scripts(self):
        html = "<html><body><p>Static page</p></body></html>"
        result = score_js_dependency(html)
        self.assertGreaterEqual(result["score"], 90)
        self.assertEqual(result["details"]["dependency_level"], "low")

    def test_few_scripts(self):
        html = _make_html(body="<p>Content</p>", scripts='<script src="a.js"></script><script src="b.js"></script>')
        result = score_js_dependency(html)
        self.assertGreaterEqual(result["score"], 70)

    def test_many_scripts_high_dependency(self):
        html = _make_html(body="<p>Content</p>", scripts=_many_scripts(25))
        result = score_js_dependency(html)
        self.assertLessEqual(result["score"], 70)

    def test_empty_root_critical(self):
        html = '<html><body><div id="root"></div>' + _many_scripts(10) + '</body></html>'
        result = score_js_dependency(html)
        self.assertEqual(result["details"]["dependency_level"], "critical")
        self.assertTrue(result["details"]["empty_root"])

    def test_ssr_framework_no_empty_root(self):
        html = '<html><body><script id="__NEXT_DATA__">{}</script><div id="__next"><h1>Content</h1></div>' + '<script src="a.js"></script></body></html>'
        result = score_js_dependency(html)
        self.assertTrue(result["details"]["ssr_capable_framework"])
        self.assertFalse(result["details"]["empty_root"])

    def test_async_defer_bonus(self):
        scripts = ''.join(f'<script src="s{i}.js" async></script>' for i in range(5))
        html = _make_html(body="<p>Content</p>", scripts=scripts)
        result = score_js_dependency(html)
        self.assertEqual(result["details"]["async_defer_count"], 5)

    def test_module_scripts_bonus(self):
        html = _make_html(body="<p>Content</p>", scripts='<script type="module" src="app.js"></script>')
        result = score_js_dependency(html)
        self.assertGreaterEqual(result["details"]["module_scripts"], 1)

    def test_score_never_negative(self):
        html = '<html><body><div id="root"></div>' + _many_scripts(40) + '</body></html>'
        result = score_js_dependency(html)
        self.assertGreaterEqual(result["score"], 0)

    def test_score_capped_at_100(self):
        html = "<html><body><p>No scripts at all</p></body></html>"
        result = score_js_dependency(html)
        self.assertLessEqual(result["score"], 100)


# ===========================================================================
# score_semantic_structure
# ===========================================================================

class TestScoreSemanticStructure(unittest.TestCase):
    def test_full_semantic(self):
        html = _make_html(body=_semantic_body())
        result = score_semantic_structure(html)
        self.assertGreaterEqual(result["score"], 50)
        self.assertTrue(any("<main>" in s for s in result["signals"]))

    def test_no_semantic(self):
        html = "<html><body><div><div><span>Text</span></div></div></body></html>"
        result = score_semantic_structure(html)
        self.assertLessEqual(result["score"], 15)

    def test_heading_hierarchy_good(self):
        body = "<h1>Title</h1><h2>Sub A</h2><h3>Detail</h3><h2>Sub B</h2>"
        html = _make_html(body=body)
        result = score_semantic_structure(html)
        self.assertTrue(any("headings" in s for s in result["signals"]))

    def test_multiple_h1_penalty(self):
        body = "<h1>First</h1><h1>Second</h1><h2>Sub</h2>"
        html_multi = _make_html(body=body)
        body_single = "<h1>Only</h1><h2>Sub</h2><h3>Detail</h3>"
        html_single = _make_html(body=body_single)
        r_multi = score_semantic_structure(html_multi)
        r_single = score_semantic_structure(html_single)
        self.assertGreaterEqual(r_single["score"], r_multi["score"])

    def test_aria_labels(self):
        body = ''.join(f'<button aria-label="Action {i}">Btn</button>' for i in range(12))
        html = _make_html(body=body)
        result = score_semantic_structure(html)
        self.assertTrue(any("ARIA" in s for s in result["signals"]))

    def test_landmark_roles(self):
        body = '<div role="main"><div role="navigation">Nav</div><div role="banner">Banner</div><div role="search"><input></div></div>'
        html = _make_html(body=body)
        result = score_semantic_structure(html)
        self.assertTrue(any("roles" in s for s in result["signals"]))

    def test_lang_attribute(self):
        html = '<html lang="ko"><body><p>Text</p></body></html>'
        result = score_semantic_structure(html)
        self.assertTrue(any("lang" in s for s in result["signals"]))

    def test_extra_semantic_elements(self):
        body = "<dl><dt>Term</dt><dd>Definition</dd></dl><figure><img src='x.jpg'><figcaption>Caption</figcaption></figure><time datetime='2024-01-01'>Jan 1</time>"
        html = _make_html(body=body)
        result = score_semantic_structure(html)
        self.assertGreater(result["score"], 0)

    def test_score_capped_at_100(self):
        body = _semantic_body()
        body += ''.join(f'<button aria-label="a{i}" role="main">B</button>' for i in range(20))
        body += "<dl><dt>T</dt></dl><figure>F</figure><time>T</time>"
        html = _make_html(body=body)
        result = score_semantic_structure(html)
        self.assertLessEqual(result["score"], 100)


# ===========================================================================
# score_content_accessibility
# ===========================================================================

class TestScoreContentAccessibility(unittest.TestCase):
    def test_full_meta(self):
        html = _make_html(head=_meta_head(), body="<p>Content</p>")
        result = score_content_accessibility(html)
        self.assertGreaterEqual(result["score"], 75)

    def test_no_meta(self):
        html = "<html><body><p>Content only</p></body></html>"
        result = score_content_accessibility(html)
        self.assertLessEqual(result["score"], 20)

    def test_title_good_length(self):
        html = _make_html(head='<title>A Good Page Title Here</title>')
        result = score_content_accessibility(html)
        self.assertTrue(any("title" in s for s in result["signals"]))

    def test_title_too_short(self):
        html = _make_html(head='<title>Hi</title>')
        result = score_content_accessibility(html)
        signals = [s for s in result["signals"] if "title" in s]
        self.assertTrue(any("suboptimal" in s for s in signals))

    def test_meta_description_quality(self):
        desc = "A proper meta description that is between fifty and one hundred sixty characters for optimal display."
        html = _make_html(head=f'<meta name="description" content="{desc}">')
        result = score_content_accessibility(html)
        self.assertTrue(any("meta description" in s for s in result["signals"]))

    def test_og_tags_full(self):
        head = (
            '<meta property="og:title" content="T">'
            '<meta property="og:description" content="D">'
            '<meta property="og:image" content="i.jpg">'
            '<meta property="og:url" content="https://e.com">'
            '<meta property="og:type" content="website">'
        )
        html = _make_html(head=head)
        result = score_content_accessibility(html)
        self.assertTrue(any("OG (5/5)" in s for s in result["signals"]))

    def test_json_ld_valid(self):
        html = _make_html(head='<script type="application/ld+json">{"@type":"Organization","name":"Test"}</script>')
        result = score_content_accessibility(html)
        self.assertTrue(any("JSON-LD" in s for s in result["signals"]))

    def test_json_ld_multiple(self):
        ld1 = '<script type="application/ld+json">{"@type":"Organization","name":"A"}</script>'
        ld2 = '<script type="application/ld+json">{"@type":"WebSite","name":"B"}</script>'
        html = _make_html(head=ld1 + ld2)
        result = score_content_accessibility(html)
        self.assertTrue(any("2 schemas" in s for s in result["signals"]))

    def test_json_ld_invalid(self):
        html = _make_html(head='<script type="application/ld+json">{not valid json</script>')
        result = score_content_accessibility(html)
        self.assertGreater(result["score"], 0)

    def test_image_alt_coverage(self):
        body = '<img src="a.jpg" alt="Photo A"><img src="b.jpg" alt="Photo B"><img src="c.jpg">'
        html = _make_html(body=body)
        result = score_content_accessibility(html)
        self.assertTrue(any("alt text" in s for s in result["signals"]))

    def test_all_images_have_alt(self):
        body = '<img src="a.jpg" alt="A"><img src="b.jpg" alt="B">'
        html = _make_html(body=body)
        result = score_content_accessibility(html)
        signals = [s for s in result["signals"] if "alt text" in s]
        self.assertTrue(any("2/2" in s for s in signals))

    def test_utf8_and_lang(self):
        html = '<html lang="ko"><head><meta charset="utf-8"></head><body></body></html>'
        result = score_content_accessibility(html)
        self.assertTrue(any("UTF-8" in s for s in result["signals"]))
        self.assertTrue(any("lang" in s for s in result["signals"]))

    def test_hreflang(self):
        html = _make_html(head='<link rel="alternate" hreflang="en" href="https://e.com/en">')
        result = score_content_accessibility(html)
        self.assertTrue(any("hreflang" in s for s in result["signals"]))

    def test_score_capped_at_100(self):
        html = _make_html(head=_meta_head(), body='<img src="a.jpg" alt="Alt">')
        result = score_content_accessibility(html)
        self.assertLessEqual(result["score"], 100)


# ===========================================================================
# score_agent_crawlability
# ===========================================================================

class TestScoreAgentCrawlability(unittest.TestCase):
    def test_many_links(self):
        links = "".join(f'<a href="/page/{i}">Page {i}</a>' for i in range(30))
        html = _make_html(body=links)
        result = score_agent_crawlability(html)
        self.assertGreaterEqual(result["score"], 20)

    def test_no_links(self):
        html = "<html><body><p>No links at all</p></body></html>"
        result = score_agent_crawlability(html)
        self.assertLessEqual(result["score"], 30)

    def test_nav_links(self):
        nav = '<nav><a href="/a">A</a><a href="/b">B</a><a href="/c">C</a><a href="/d">D</a><a href="/e">E</a></nav>'
        html = _make_html(body=nav)
        result = score_agent_crawlability(html)
        self.assertTrue(any("nav links" in s for s in result["signals"]))

    def test_robots_noindex_penalty(self):
        html = _make_html(head='<meta name="robots" content="noindex, nofollow">')
        result = score_agent_crawlability(html)
        signals = [s for s in result["signals"] if "noindex" in s]
        self.assertTrue(len(signals) > 0)

    def test_canonical_https(self):
        html = _make_html(head='<link rel="canonical" href="https://example.com/page">')
        result = score_agent_crawlability(html)
        self.assertTrue(any("canonical: https" in s for s in result["signals"]))

    def test_breadcrumb_detected(self):
        html = _make_html(body='<nav aria-label="breadcrumb"><ol><li>Home</li><li>Page</li></ol></nav>')
        result = score_agent_crawlability(html)
        self.assertTrue(any("breadcrumb" in s for s in result["signals"]))

    def test_breadcrumb_schema(self):
        html = _make_html(head='<script type="application/ld+json">{"@type":"BreadcrumbList"}</script>')
        result = score_agent_crawlability(html)
        self.assertTrue(any("breadcrumb" in s for s in result["signals"]))

    def test_pagination_rel(self):
        html = _make_html(head='<link rel="next" href="/page/2">')
        result = score_agent_crawlability(html)
        self.assertTrue(any("pagination" in s for s in result["signals"]))

    def test_navigation_schema(self):
        html = _make_html(head='<script type="application/ld+json">{"@type":"SiteNavigationElement"}</script>')
        result = score_agent_crawlability(html)
        self.assertTrue(any("navigation schema" in s for s in result["signals"]))

    def test_high_hash_link_ratio(self):
        body = '<a href="#s1">1</a><a href="#s2">2</a><a href="#s3">3</a><a href="/real">R</a>'
        html = _make_html(body=body)
        result = score_agent_crawlability(html)
        self.assertTrue(any("hash-link" in s for s in result["signals"]))

    def test_score_never_negative(self):
        html = _make_html(head='<meta name="robots" content="noindex, nofollow">')
        result = score_agent_crawlability(html)
        self.assertGreaterEqual(result["score"], 0)


# ===========================================================================
# score_rendering_resilience
# ===========================================================================

class TestScoreRenderingResilience(unittest.TestCase):
    def test_content_heavy_low_js(self):
        body = "<p>" + " ".join(["word"] * 300) + "</p>"
        html = _make_html(body=body)
        result = score_rendering_resilience(html)
        self.assertGreaterEqual(result["score"], 25)
        self.assertTrue(any("content-heavy" in s for s in result["signals"]))

    def test_noscript_fallback(self):
        body = '<noscript><p>이 사이트를 이용하려면 JavaScript를 활성화해야 합니다. 주요 콘텐츠를 보려면 여기를 참조하세요. 기본 페이지 대체 콘텐츠가 표시됩니다.</p></noscript>'
        html = _make_html(body=body)
        result = score_rendering_resilience(html)
        self.assertTrue(any("noscript" in s for s in result["signals"]))

    def test_inline_css(self):
        html = _make_html(head="<style>body{margin:0;font-family:sans-serif}</style>")
        result = score_rendering_resilience(html)
        self.assertTrue(any("inline CSS" in s for s in result["signals"]))

    def test_css_preload(self):
        html = _make_html(head='<link rel="preload" as="style" href="main.css">')
        result = score_rendering_resilience(html)
        self.assertTrue(any("CSS preload" in s for s in result["signals"]))

    def test_lazy_loading_images(self):
        body = '<img src="a.jpg" loading="lazy"><img src="b.jpg" loading="eager">'
        html = _make_html(body=body)
        result = score_rendering_resilience(html)
        self.assertTrue(any("img loading strategy" in s for s in result["signals"]))

    def test_responsive_images(self):
        body = '<img srcset="small.jpg 480w, large.jpg 1024w" src="large.jpg">'
        html = _make_html(body=body)
        result = score_rendering_resilience(html)
        self.assertTrue(any("responsive images" in s for s in result["signals"]))

    def test_picture_element(self):
        body = '<picture><source srcset="img.webp" type="image/webp"><img src="img.jpg"></picture>'
        html = _make_html(body=body)
        result = score_rendering_resilience(html)
        self.assertTrue(any("responsive images" in s for s in result["signals"]))

    def test_resource_hints(self):
        html = _make_html(head='<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="dns-prefetch" href="https://cdn.example.com">')
        result = score_rendering_resilience(html)
        self.assertTrue(any("resource hints" in s for s in result["signals"]))

    def test_details_element(self):
        body = "<details><summary>FAQ</summary><p>Answer here</p></details>"
        html = _make_html(body=body)
        result = score_rendering_resilience(html)
        self.assertTrue(any("<details>" in s for s in result["signals"]))

    def test_empty_page_low_resilience(self):
        html = '<html><body><div id="root"></div>' + _many_scripts(15) + '</body></html>'
        result = score_rendering_resilience(html)
        self.assertLessEqual(result["score"], 25)

    def test_score_capped_at_100(self):
        body = (
            '<noscript><p>' + " ".join(["fallback"] * 50) + '</p></noscript>'
            '<p>' + " ".join(["content"] * 400) + '</p>'
            '<img src="a.jpg" loading="eager" srcset="a-2x.jpg 2x">'
            '<details><summary>FAQ</summary><p>A</p></details>'
        )
        head = '<style>body{}</style><link rel="preload" as="style" href="x.css"><link rel="preconnect" href="https://x.com"><meta name="prerender-status-code" content="200">'
        html = _make_html(body=body, head=head)
        result = score_rendering_resilience(html)
        self.assertLessEqual(result["score"], 100)


# ===========================================================================
# analyze_rendering_html (integration)
# ===========================================================================

class TestAnalyzeRenderingHTML(unittest.TestCase):
    def test_well_optimized_page(self):
        body = _semantic_body() + "<p>" + " ".join(["content"] * 200) + "</p>"
        body += '<a href="/p1">P1</a><a href="/p2">P2</a><a href="/p3">P3</a>'
        head = _meta_head()
        html = _make_html(head=head, body=body)
        result = analyze_rendering_html(html)

        self.assertGreaterEqual(result["score"], 50)
        self.assertIn("dimensions", result)
        self.assertEqual(len(result["dimensions"]), 6)
        for dim in DIMENSION_WEIGHTS:
            self.assertIn(dim, result["dimensions"])
            self.assertGreaterEqual(result["dimensions"][dim], 0)
            self.assertLessEqual(result["dimensions"][dim], 100)

    def test_spa_csr_page(self):
        html = '<html><body><div id="root"></div>' + _many_scripts(20) + '</body></html>'
        result = analyze_rendering_html(html)
        self.assertLessEqual(result["score"], 35)
        self.assertTrue(any(i["severity"] == "critical" for i in result["issues"]))

    def test_backward_compat_ssr(self):
        html = _make_html(body=_rich_body(200))
        result = analyze_rendering_html(html)
        self.assertIn("ssr", result)
        self.assertIn("has_ssr_content", result["ssr"])
        self.assertIn("word_count", result["ssr"])
        self.assertIn("score", result["ssr"])

    def test_backward_compat_js_dependency(self):
        html = _make_html(body="<p>Content</p>", scripts=_many_scripts(5))
        result = analyze_rendering_html(html)
        self.assertIn("js_dependency", result)
        self.assertIn("dependency_level", result["js_dependency"])
        self.assertIn("total_scripts", result["js_dependency"])
        self.assertIn("frameworks", result["js_dependency"])
        self.assertIn("empty_root", result["js_dependency"])

    def test_issues_generated(self):
        html = '<html><body><div id="root"></div>' + _many_scripts(20) + '</body></html>'
        result = analyze_rendering_html(html)
        self.assertGreater(len(result["issues"]), 0)

    def test_no_issues_on_good_page(self):
        body = _semantic_body() + "<p>" + " ".join(["content"] * 300) + "</p>"
        nav = '<nav>' + ''.join(f'<a href="/p{i}">P{i}</a>' for i in range(10)) + '</nav>'
        body += nav
        head = _meta_head()
        head += '<link rel="canonical" href="https://example.com">'
        html = _make_html(head=head, body=body)
        result = analyze_rendering_html(html)
        critical_issues = [i for i in result["issues"] if i["severity"] == "critical"]
        self.assertEqual(len(critical_issues), 0)

    def test_dimensions_weighted_sum(self):
        html = _make_html(body=_rich_body(200), head=_meta_head())
        result = analyze_rendering_html(html)
        expected = round(sum(result["dimensions"][k] * DIMENSION_WEIGHTS[k] for k in DIMENSION_WEIGHTS), 1)
        self.assertAlmostEqual(result["score"], expected, places=1)

    def test_empty_html(self):
        result = analyze_rendering_html("")
        self.assertLessEqual(result["score"], 25)

    def test_details_present(self):
        html = _make_html(body=_rich_body(100))
        result = analyze_rendering_html(html)
        self.assertIn("details", result)
        for dim in DIMENSION_WEIGHTS:
            self.assertIn(dim, result["details"])
            self.assertIn("score", result["details"][dim])

    def test_next_js_ssr_page(self):
        body = '<script id="__NEXT_DATA__" type="application/json">{"page":"/"}</script>'
        body += '<div id="__next">' + _rich_body(300) + '</div>'
        head = _meta_head()
        html = f'<html lang="ko"><head>{head}</head><body>{body}</body></html>'
        result = analyze_rendering_html(html)
        self.assertGreaterEqual(result["score"], 45)
        self.assertIn("Next.js", result["js_dependency"]["frameworks"])

    def test_static_html_page(self):
        body = _semantic_body() + "<p>" + " ".join(["word"] * 400) + "</p>"
        nav = '<nav>' + ''.join(f'<a href="/p{i}">P{i}</a>' for i in range(15)) + '</nav>'
        head = _meta_head() + '<style>body{margin:0}</style>'
        html = _make_html(head=head, body=body + nav)
        result = analyze_rendering_html(html)
        self.assertGreaterEqual(result["score"], 60)


# ===========================================================================
# Edge cases
# ===========================================================================

class TestEdgeCases(unittest.TestCase):
    def test_score_range_all_dimensions(self):
        html = _make_html(body=_rich_body(200), head=_meta_head())
        result = analyze_rendering_html(html)
        for dim in DIMENSION_WEIGHTS:
            self.assertGreaterEqual(result["dimensions"][dim], 0)
            self.assertLessEqual(result["dimensions"][dim], 100)

    def test_dimension_weights_sum_to_1(self):
        total = sum(DIMENSION_WEIGHTS.values())
        self.assertAlmostEqual(total, 1.0, places=5)

    def test_minimal_html(self):
        result = analyze_rendering_html("<html><body>x</body></html>")
        self.assertIsInstance(result["score"], float)
        self.assertGreaterEqual(result["score"], 0)

    def test_script_inside_noscript_not_counted(self):
        body = '<noscript><p>Fallback content for users without JavaScript enabled in their browser settings</p></noscript>'
        html = _make_html(body=body)
        result = score_rendering_resilience(html)
        self.assertTrue(any("noscript" in s for s in result["signals"]))

    def test_korean_content_ssr(self):
        body = "<h1>서울 맛집 추천</h1><p>" + " ".join(["맛집"] * 200) + "</p>"
        html = _make_html(body=body)
        result = score_ssr_quality(html)
        self.assertGreaterEqual(result["score"], 50)


if __name__ == "__main__":
    unittest.main()

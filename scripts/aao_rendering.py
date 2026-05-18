"""AAO rendering analysis — 6-dimension quality scoring for AI agent accessibility.

Dimensions (weights):
  1. ssr_quality      (0.20) — server-rendered content richness and hydration patterns
  2. js_dependency    (0.20) — JavaScript rendering risk assessment
  3. semantic_structure (0.15) — HTML landmark/heading hierarchy for agent parsing
  4. content_accessibility (0.20) — meta, structured data, image alt coverage
  5. agent_crawlability (0.15) — link structure, robots, canonical, navigation
  6. rendering_resilience (0.10) — graceful degradation without JS
"""

import argparse
import json
import re
import sys

from validate_url import validate_url
from fetch_page import fetch_page


DIMENSION_WEIGHTS = {
    "ssr_quality": 0.20,
    "js_dependency": 0.20,
    "semantic_structure": 0.15,
    "content_accessibility": 0.20,
    "agent_crawlability": 0.15,
    "rendering_resilience": 0.10,
}

FRAMEWORK_SSR_CAPABLE = {
    "Next.js": True,
    "Nuxt.js": True,
    "Angular Universal": True,
    "SvelteKit": True,
    "Remix": True,
    "Astro": True,
    "Gatsby": True,
    "React": False,
    "Vue.js": False,
    "Angular": False,
    "Svelte": False,
}


def _extract_body_text(html: str) -> str:
    body_match = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL | re.IGNORECASE)
    body = body_match.group(1) if body_match else html
    no_script = re.sub(r'<script[^>]*>.*?</script>', '', body, flags=re.DOTALL | re.IGNORECASE)
    no_style = re.sub(r'<style[^>]*>.*?</style>', '', no_script, flags=re.DOTALL | re.IGNORECASE)
    return re.sub(r'<[^>]+>', ' ', no_style).strip()


def _count_images(html: str) -> int:
    return len(re.findall(r'<img\b', html, re.IGNORECASE))


def _count_images_with_alt(html: str) -> int:
    return len(re.findall(r'<img\b[^>]*\balt="[^"]+', html, re.IGNORECASE))


def detect_frameworks(html: str) -> list:
    """Detect frontend frameworks from HTML source."""
    found = []
    patterns = [
        ("Next.js", r'(__NEXT_DATA__|_next/static|_next/image)'),
        ("Nuxt.js", r'(__NUXT__|_nuxt/|nuxt\.config)'),
        ("Remix", r'(__remix|remix\.run)'),
        ("Astro", r'(astro-island|data-astro)'),
        ("Gatsby", r'(gatsby-image|___gatsby)'),
        ("SvelteKit", r'(__sveltekit|svelte-kit)'),
        ("Angular Universal", r'(ng-server-context|_nghost)'),
        ("Angular", r'(ng-app|ng-controller|\bng-version=)'),
        ("React", r'(data-reactroot|__REACT|react-app|_reactListening)'),
        ("Vue.js", r'data-v-[a-f0-9]{6,}'),
        ("Svelte", r'(svelte-\w+|__svelte)'),
    ]
    for name, pattern in patterns:
        if re.search(pattern, html, re.IGNORECASE):
            found.append(name)
    return found


def detect_hydration_pattern(html: str, frameworks: list) -> str:
    """Classify rendering pattern: static, ssr_hydrate, csr, or hybrid."""
    text = _extract_body_text(html)
    word_count = len(text.split()) if text else 0
    empty_root = bool(re.search(r'<div\s+id="(app|root|__next|__nuxt)">\s*</div>', html))

    ssr_capable = any(FRAMEWORK_SSR_CAPABLE.get(f, False) for f in frameworks)

    if empty_root and word_count < 50:
        return "csr"
    if ssr_capable and word_count > 100:
        return "ssr_hydrate"
    if not frameworks and word_count > 100:
        return "static"
    if frameworks and word_count > 100:
        return "hybrid"
    if word_count < 50:
        return "csr"
    return "static"


def score_ssr_quality(html: str) -> dict:
    """Score server-side rendering content quality (0-100)."""
    text = _extract_body_text(html)
    words = text.split() if text else []
    word_count = len(words)

    headings = len(re.findall(r'<h[1-6][^>]*>.+?</h[1-6]>', html, re.IGNORECASE | re.DOTALL))
    paragraphs = len(re.findall(r'<p[^>]*>.{20,}</p>', html, re.IGNORECASE | re.DOTALL))
    lists = len(re.findall(r'<[ou]l[^>]*>', html, re.IGNORECASE))
    tables = len(re.findall(r'<table[^>]*>', html, re.IGNORECASE))

    frameworks = detect_frameworks(html)
    hydration = detect_hydration_pattern(html, frameworks)

    score = 0.0
    details = {}

    if word_count >= 300:
        score += 30
    elif word_count >= 100:
        score += 20
    elif word_count >= 30:
        score += 10
    elif word_count > 0:
        score += 5
    details["word_count"] = word_count

    content_elements = min(headings * 3 + paragraphs * 2 + lists * 2 + tables * 3, 25)
    score += content_elements
    details["headings"] = headings
    details["paragraphs"] = paragraphs
    details["lists"] = lists
    details["tables"] = tables

    html_size = len(html)
    text_size = len(text) if text else 0
    ratio = round(text_size / html_size, 3) if html_size > 0 else 0
    if ratio >= 0.15:
        score += 15
    elif ratio >= 0.08:
        score += 10
    elif ratio >= 0.03:
        score += 5
    details["text_to_html_ratio"] = ratio

    hydration_bonus = {
        "static": 15,
        "ssr_hydrate": 15,
        "hybrid": 10,
        "csr": 0,
    }
    score += hydration_bonus.get(hydration, 0)
    details["hydration_pattern"] = hydration
    details["frameworks"] = frameworks

    has_noscript = bool(re.search(r'<noscript[^>]*>.{10,}</noscript>', html, re.DOTALL | re.IGNORECASE))
    if has_noscript:
        score += 5
    details["has_noscript"] = has_noscript

    h1_with_text = bool(re.search(r'<h1[^>]*>[^<]{2,}</h1>', html, re.IGNORECASE))
    if h1_with_text:
        score += 10
    details["h1_in_ssr"] = h1_with_text

    score = round(min(100, score), 1)
    return {"score": score, "details": details}


def score_js_dependency(html: str) -> dict:
    """Score JavaScript dependency risk (0-100, higher = less dependent = better)."""
    external_scripts = len(re.findall(r'<script[^>]*\bsrc=', html, re.IGNORECASE))
    inline_scripts = len(re.findall(r'<script(?![^>]*\bsrc=)[^>]*>', html, re.IGNORECASE))
    total_scripts = external_scripts + inline_scripts

    frameworks = detect_frameworks(html)
    empty_root = bool(re.search(r'<div\s+id="(app|root|__next|__nuxt)">\s*</div>', html))

    ssr_capable = any(FRAMEWORK_SSR_CAPABLE.get(f, False) for f in frameworks)

    score = 100.0
    details = {}

    if total_scripts <= 3:
        score -= 0
    elif total_scripts <= 8:
        score -= 10
    elif total_scripts <= 15:
        score -= 20
    elif total_scripts <= 25:
        score -= 35
    else:
        score -= 50
    details["external_scripts"] = external_scripts
    details["inline_scripts"] = inline_scripts
    details["total_scripts"] = total_scripts

    if empty_root:
        score -= 30
    details["empty_root"] = empty_root

    if frameworks:
        if ssr_capable and not empty_root:
            score -= 5
        elif ssr_capable and empty_root:
            score -= 15
        elif not ssr_capable and empty_root:
            score -= 25
        elif not ssr_capable:
            score -= 10
    details["frameworks"] = frameworks
    details["ssr_capable_framework"] = ssr_capable

    async_defer = len(re.findall(r'<script[^>]*\b(async|defer)\b', html, re.IGNORECASE))
    if total_scripts > 0:
        async_ratio = async_defer / total_scripts
        if async_ratio >= 0.7:
            score += 10
        elif async_ratio >= 0.4:
            score += 5
    details["async_defer_count"] = async_defer

    module_scripts = len(re.findall(r'<script[^>]*type="module"', html, re.IGNORECASE))
    if module_scripts > 0:
        score += 5
    details["module_scripts"] = module_scripts

    dependency_level = "low"
    if empty_root or score < 30:
        dependency_level = "critical"
    elif score < 50:
        dependency_level = "high"
    elif score < 70:
        dependency_level = "moderate"
    details["dependency_level"] = dependency_level

    score = round(max(0, min(100, score)), 1)
    return {"score": score, "details": details}


def score_semantic_structure(html: str) -> dict:
    """Score semantic HTML structure quality for agent parsing (0-100)."""
    score = 0.0
    signals = []

    landmark_checks = [
        ("header", r'<header\b[^>]*>', 6),
        ("nav", r'<nav\b[^>]*>', 6),
        ("main", r'<main\b[^>]*>', 10),
        ("article", r'<article\b[^>]*>', 8),
        ("section", r'<section\b[^>]*>', 4),
        ("footer", r'<footer\b[^>]*>', 6),
        ("aside", r'<aside\b[^>]*>', 3),
    ]
    landmark_score = 0
    for tag, pattern, points in landmark_checks:
        if re.search(pattern, html, re.IGNORECASE):
            landmark_score += points
            signals.append(f"<{tag}>")
    score += min(35, landmark_score)

    h_levels = []
    for level in range(1, 7):
        if re.search(rf'<h{level}\b[^>]*>', html, re.IGNORECASE):
            h_levels.append(level)

    if h_levels:
        has_h1 = 1 in h_levels
        h1_count = len(re.findall(r'<h1\b[^>]*>', html, re.IGNORECASE))
        sequential = all(h_levels[i] <= h_levels[i + 1] + 1 for i in range(len(h_levels) - 1)) if len(h_levels) > 1 else True

        heading_score = 0
        if has_h1:
            heading_score += 8
        if h1_count == 1:
            heading_score += 5
        elif h1_count > 1:
            heading_score += 2
        if sequential:
            heading_score += 7
        if len(h_levels) >= 3:
            heading_score += 5
        score += min(25, heading_score)
        signals.append(f"headings: {', '.join(f'h{h}' for h in sorted(set(h_levels)))}")

    aria_labels = len(re.findall(r'aria-label="[^"]+"', html))
    aria_described = len(re.findall(r'aria-describedby="[^"]+"', html))
    aria_live = len(re.findall(r'aria-live="', html))
    aria_total = aria_labels + aria_described + aria_live

    if aria_total >= 10:
        score += 15
    elif aria_total >= 5:
        score += 10
    elif aria_total > 0:
        score += 5
    if aria_total > 0:
        signals.append(f"ARIA ({aria_total})")

    role_matches = re.findall(r'role="(main|navigation|banner|contentinfo|search|complementary|form|region)"', html, re.IGNORECASE)
    unique_roles = set(r.lower() for r in role_matches)
    if len(unique_roles) >= 4:
        score += 15
    elif len(unique_roles) >= 2:
        score += 10
    elif len(unique_roles) >= 1:
        score += 5
    if unique_roles:
        signals.append(f"roles: {', '.join(sorted(unique_roles))}")

    lang_attr = bool(re.search(r'<html[^>]*\blang="[a-z]{2}', html, re.IGNORECASE))
    if lang_attr:
        score += 5
        signals.append("lang")

    dl_tags = len(re.findall(r'<dl\b[^>]*>', html, re.IGNORECASE))
    figure_tags = len(re.findall(r'<figure\b[^>]*>', html, re.IGNORECASE))
    time_tags = len(re.findall(r'<time\b[^>]*>', html, re.IGNORECASE))
    extra = min(5, dl_tags * 2 + figure_tags * 2 + time_tags)
    score += extra

    score = round(min(100, score), 1)
    return {"score": score, "signals": signals}


def score_content_accessibility(html: str) -> dict:
    """Score content accessibility for non-browser agents (0-100)."""
    score = 0.0
    signals = []

    title_match = re.search(r'<title>([^<]+)</title>', html, re.IGNORECASE)
    if title_match:
        title_text = title_match.group(1).strip()
        if 10 <= len(title_text) <= 70:
            score += 12
            signals.append("title (good length)")
        elif title_text:
            score += 7
            signals.append("title (suboptimal length)")

    desc_match = re.search(r'<meta[^>]*name="description"[^>]*content="([^"]*)"', html, re.IGNORECASE)
    if not desc_match:
        desc_match = re.search(r'<meta[^>]*content="([^"]*)"[^>]*name="description"', html, re.IGNORECASE)
    if desc_match:
        desc = desc_match.group(1).strip()
        if 50 <= len(desc) <= 160:
            score += 12
            signals.append("meta description (good)")
        elif desc:
            score += 7
            signals.append("meta description (suboptimal)")

    if re.search(r'rel="canonical"', html, re.IGNORECASE):
        score += 8
        signals.append("canonical")

    og_props = ["og:title", "og:description", "og:image", "og:url", "og:type"]
    og_found = sum(1 for p in og_props if re.search(rf'property="{p}"', html, re.IGNORECASE))
    if og_found >= 4:
        score += 12
        signals.append(f"OG ({og_found}/{len(og_props)})")
    elif og_found >= 2:
        score += 7
        signals.append(f"OG ({og_found}/{len(og_props)})")
    elif og_found > 0:
        score += 3
        signals.append(f"OG ({og_found}/{len(og_props)})")

    twitter_card = bool(re.search(r'name="twitter:card"', html, re.IGNORECASE))
    if twitter_card:
        score += 4
        signals.append("twitter card")

    ld_json_blocks = re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.DOTALL | re.IGNORECASE)
    if ld_json_blocks:
        valid_schemas = 0
        for block in ld_json_blocks:
            try:
                data = json.loads(block)
                if isinstance(data, dict) and "@type" in data:
                    valid_schemas += 1
                elif isinstance(data, list):
                    valid_schemas += sum(1 for item in data if isinstance(item, dict) and "@type" in item)
            except (json.JSONDecodeError, TypeError):
                pass
        if valid_schemas >= 2:
            score += 20
            signals.append(f"JSON-LD ({valid_schemas} schemas)")
        elif valid_schemas == 1:
            score += 14
            signals.append("JSON-LD (1 schema)")
        else:
            score += 5
            signals.append("JSON-LD (invalid)")

    total_img = _count_images(html)
    img_with_alt = _count_images_with_alt(html)
    if total_img > 0:
        alt_ratio = img_with_alt / total_img
        if alt_ratio >= 0.9:
            score += 10
            signals.append(f"alt text ({img_with_alt}/{total_img})")
        elif alt_ratio >= 0.5:
            score += 5
            signals.append(f"alt text ({img_with_alt}/{total_img})")
        else:
            score += 2
    else:
        score += 5

    if re.search(r'charset="?utf-8"?', html, re.IGNORECASE):
        score += 4
        signals.append("UTF-8")

    lang = bool(re.search(r'<html[^>]*\blang="[a-z]{2}', html, re.IGNORECASE))
    if lang:
        score += 4
        signals.append("lang attr")

    hreflang = bool(re.search(r'hreflang="', html, re.IGNORECASE))
    if hreflang:
        score += 4
        signals.append("hreflang")

    score = round(min(100, score), 1)
    return {"score": score, "signals": signals}


def score_agent_crawlability(html: str) -> dict:
    """Score how well agents can discover and traverse content (0-100)."""
    score = 0.0
    signals = []

    internal_links = re.findall(r'<a[^>]*href="(/[^"]*|https?://[^"]*)"', html, re.IGNORECASE)
    unique_links = set(internal_links)
    if len(unique_links) >= 20:
        score += 20
    elif len(unique_links) >= 10:
        score += 15
    elif len(unique_links) >= 3:
        score += 10
    elif len(unique_links) > 0:
        score += 5
    signals.append(f"links: {len(unique_links)} unique")

    nav_links = re.findall(r'<nav\b[^>]*>(.*?)</nav>', html, re.DOTALL | re.IGNORECASE)
    nav_link_count = 0
    for nav_content in nav_links:
        nav_link_count += len(re.findall(r'<a\b[^>]*href=', nav_content, re.IGNORECASE))
    if nav_link_count >= 5:
        score += 15
        signals.append(f"nav links: {nav_link_count}")
    elif nav_link_count > 0:
        score += 8
        signals.append(f"nav links: {nav_link_count}")

    robots_meta = re.search(r'<meta[^>]*name="robots"[^>]*content="([^"]*)"', html, re.IGNORECASE)
    if not robots_meta:
        robots_meta = re.search(r'<meta[^>]*content="([^"]*)"[^>]*name="robots"', html, re.IGNORECASE)

    if robots_meta:
        directives = robots_meta.group(1).lower()
        if "noindex" in directives:
            score -= 20
            signals.append("robots: noindex")
        elif "nofollow" in directives:
            score -= 10
            signals.append("robots: nofollow")
        else:
            score += 10
            signals.append("robots: allowed")
    else:
        score += 10
        signals.append("robots: no restriction")

    canonical = re.search(r'<link[^>]*rel="canonical"[^>]*href="([^"]*)"', html, re.IGNORECASE)
    if canonical:
        href = canonical.group(1)
        if href.startswith("https://"):
            score += 10
            signals.append("canonical: https")
        elif href.startswith("http"):
            score += 6
            signals.append("canonical: http")
        else:
            score += 3
    else:
        score += 0

    sitemap_ref = bool(re.search(r'sitemap', html, re.IGNORECASE))
    if sitemap_ref:
        score += 5
        signals.append("sitemap reference")

    breadcrumb = bool(re.search(r'(BreadcrumbList|breadcrumb|aria-label="breadcrumb")', html, re.IGNORECASE))
    if breadcrumb:
        score += 10
        signals.append("breadcrumb")

    pagination = bool(re.search(r'rel="(next|prev)"', html, re.IGNORECASE))
    if pagination:
        score += 5
        signals.append("pagination rel")

    linked_data_nav = bool(re.search(r'"(SiteNavigationElement|WebSite)"', html))
    if linked_data_nav:
        score += 10
        signals.append("navigation schema")

    hash_links = len(re.findall(r'href="#[^"]*"', html))
    if len(unique_links) > 0:
        hash_ratio = hash_links / (len(unique_links) + hash_links) if (len(unique_links) + hash_links) > 0 else 0
        if hash_ratio > 0.5:
            score -= 5
            signals.append("high hash-link ratio")

    score = round(max(0, min(100, score)), 1)
    return {"score": score, "signals": signals}


def score_rendering_resilience(html: str) -> dict:
    """Score how well content degrades without JavaScript (0-100)."""
    score = 0.0
    signals = []

    noscript_blocks = re.findall(r'<noscript[^>]*>(.*?)</noscript>', html, re.DOTALL | re.IGNORECASE)
    noscript_content_len = sum(len(block.strip()) for block in noscript_blocks)
    if noscript_content_len > 200:
        score += 20
        signals.append(f"noscript content ({noscript_content_len} chars)")
    elif noscript_content_len > 50:
        score += 12
        signals.append(f"noscript content ({noscript_content_len} chars)")
    elif noscript_content_len > 0:
        score += 5
        signals.append("noscript (minimal)")

    text = _extract_body_text(html)
    word_count = len(text.split()) if text else 0
    total_scripts = len(re.findall(r'<script\b', html, re.IGNORECASE))

    if word_count > 200 and total_scripts <= 5:
        score += 25
        signals.append("content-heavy, low JS")
    elif word_count > 200:
        score += 15
        signals.append("content available despite JS")
    elif word_count > 50:
        score += 8

    critical_css = bool(re.search(r'<style[^>]*>(.*?)</style>', html, re.DOTALL | re.IGNORECASE))
    if critical_css:
        score += 10
        signals.append("inline CSS")

    len(re.findall(r'<link[^>]*rel="stylesheet"', html, re.IGNORECASE))
    preloaded_css = len(re.findall(r'<link[^>]*rel="preload"[^>]*as="style"', html, re.IGNORECASE))
    if preloaded_css > 0:
        score += 5
        signals.append("CSS preload")

    lazy_imgs = len(re.findall(r'loading="lazy"', html, re.IGNORECASE))
    eager_imgs = len(re.findall(r'loading="eager"', html, re.IGNORECASE))
    total_imgs = _count_images(html)
    if total_imgs > 0:
        if eager_imgs > 0 or lazy_imgs > 0:
            score += 10
            signals.append(f"img loading strategy (eager:{eager_imgs} lazy:{lazy_imgs})")
        else:
            score += 3

    srcset = len(re.findall(r'\bsrcset="', html, re.IGNORECASE))
    picture = len(re.findall(r'<picture\b', html, re.IGNORECASE))
    if srcset > 0 or picture > 0:
        score += 5
        signals.append("responsive images")

    preconnect = len(re.findall(r'rel="(preconnect|dns-prefetch)"', html, re.IGNORECASE))
    if preconnect > 0:
        score += 5
        signals.append(f"resource hints ({preconnect})")

    details_els = len(re.findall(r'<details\b', html, re.IGNORECASE))
    if details_els > 0:
        score += 5
        signals.append(f"CSS-only interactive ({details_els} <details>)")

    prerender = bool(re.search(r'<meta[^>]*name="(prerender-status-code|fragment)"', html, re.IGNORECASE))
    if prerender:
        score += 10
        signals.append("prerender meta")

    score = round(max(0, min(100, score)), 1)
    return {"score": score, "signals": signals}


def analyze_rendering_html(html: str) -> dict:
    """Full 6-dimension rendering analysis on raw HTML."""
    ssr = score_ssr_quality(html)
    js_dep = score_js_dependency(html)
    semantic = score_semantic_structure(html)
    content_acc = score_content_accessibility(html)
    crawl = score_agent_crawlability(html)
    resilience = score_rendering_resilience(html)

    dimensions = {
        "ssr_quality": ssr["score"],
        "js_dependency": js_dep["score"],
        "semantic_structure": semantic["score"],
        "content_accessibility": content_acc["score"],
        "agent_crawlability": crawl["score"],
        "rendering_resilience": resilience["score"],
    }

    overall = round(sum(dimensions[k] * DIMENSION_WEIGHTS[k] for k in DIMENSION_WEIGHTS), 1)

    issues = []
    if ssr["score"] < 30:
        issues.append({"severity": "critical", "message": "콘텐츠가 JS 렌더링에 의존 — 대부분의 AI 에이전트에 보이지 않음"})
    if js_dep["details"].get("empty_root"):
        issues.append({"severity": "critical", "message": "빈 root div 감지 — SSR 없는 SPA"})
    if js_dep["score"] < 40:
        dep_level = js_dep["details"].get("dependency_level", "high")
        fw = js_dep["details"].get("frameworks", [])
        fw_str = f" ({', '.join(fw)})" if fw else ""
        issues.append({"severity": "high", "message": f"JS 의존도 {dep_level}{fw_str}"})
    if semantic["score"] < 30:
        issues.append({"severity": "medium", "message": "시멘틱 HTML 구조 미흡 — 에이전트 파싱 어려움"})
    if content_acc["score"] < 40:
        issues.append({"severity": "medium", "message": "메타/구조화 데이터 불완전 — 에이전트 접근성 저하"})
    if crawl["score"] < 40:
        issues.append({"severity": "medium", "message": "크롤 가능성 미흡 — 내부 링크 구조 또는 robots 확인 필요"})
    if resilience["score"] < 30:
        issues.append({"severity": "low", "message": "JS 비활성 시 콘텐츠 접근 불가 — noscript 폴백 필요"})

    return {
        "score": overall,
        "dimensions": dimensions,
        "details": {
            "ssr_quality": ssr,
            "js_dependency": js_dep,
            "semantic_structure": semantic,
            "content_accessibility": content_acc,
            "agent_crawlability": crawl,
            "rendering_resilience": resilience,
        },
        "issues": issues,
        # backward compat for aao_audit.py
        "ssr": {
            "has_ssr_content": ssr["score"] >= 30,
            "word_count": ssr["details"].get("word_count", 0),
            "headings": ssr["details"].get("headings", 0),
            "paragraphs": ssr["details"].get("paragraphs", 0),
            "score": ssr["score"],
        },
        "js_dependency": {
            "dependency_level": js_dep["details"].get("dependency_level", "low"),
            "total_scripts": js_dep["details"].get("total_scripts", 0),
            "frameworks": js_dep["details"].get("frameworks", []),
            "empty_root": js_dep["details"].get("empty_root", False),
            "score": js_dep["score"],
        },
    }


def analyze_rendering(url: str) -> dict:
    """Full rendering analysis for AI agents (URL-based entry point)."""
    validation = validate_url(url)
    if not validation["valid"]:
        return {"success": False, "error": validation["error"]}

    result = fetch_page(url)
    if not result["success"]:
        return {"success": False, "error": result["error"]}

    analysis = analyze_rendering_html(result["html"])
    analysis["success"] = True
    analysis["url"] = url
    return analysis


def main():
    parser = argparse.ArgumentParser(description="AAO rendering analysis — 6-dimension scoring")
    parser.add_argument("url", help="URL to analyze")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    result = analyze_rendering(args.url)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result["success"]:
            print(f"Rendering Score: {result['score']}/100")
            print("\nDimensions:")
            for dim, w in DIMENSION_WEIGHTS.items():
                s = result["dimensions"][dim]
                bar = "█" * int(s / 5) + "░" * (20 - int(s / 5))
                print(f"  {dim:25s} {bar} {s:5.1f} (×{w})")
            print(f"\nSSR: {'✓' if result['ssr']['has_ssr_content'] else '✗'} ({result['ssr']['word_count']} words)")
            print(f"JS Dependency: {result['js_dependency']['dependency_level']} ({result['js_dependency']['total_scripts']} scripts)")
            if result["js_dependency"]["frameworks"]:
                print(f"Frameworks: {', '.join(result['js_dependency']['frameworks'])}")
            for issue in result["issues"]:
                print(f"  [{issue['severity'].upper()}] {issue['message']}")
        else:
            print(f"Error: {result['error']}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()

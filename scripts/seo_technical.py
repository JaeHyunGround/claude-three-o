"""SEO technical analysis — 8-dimension quality scoring.

Dimensions (weights):
  1. meta_quality        (0.20) — title, description, OG, twitter, canonical quality
  2. heading_structure   (0.12) — hierarchy depth, nesting, keyword presence, balance
  3. image_optimization  (0.10) — alt coverage, lazy loading, responsive, format, sizing
  4. link_health         (0.10) — internal/external ratio, anchor diversity, nofollow, nav quality
  5. mobile_readiness    (0.15) — viewport, touch targets, font sizing, responsive signals
  6. indexability        (0.13) — robots, canonical validation, hreflang, lang, sitemap
  7. security_signals    (0.10) — HTTPS, CSP, mixed content, security meta
  8. performance_signals (0.10) — resource hints, preload, critical CSS, compression signals
"""

import argparse
import json
import re
import sys
from typing import Optional

from validate_url import validate_url
from fetch_page import fetch_page


DIMENSION_WEIGHTS = {
    "meta_quality": 0.20,
    "heading_structure": 0.12,
    "image_optimization": 0.10,
    "link_health": 0.10,
    "mobile_readiness": 0.15,
    "indexability": 0.13,
    "security_signals": 0.10,
    "performance_signals": 0.10,
}


# ---------------------------------------------------------------------------
# Backward-compatible functions (used by three_o_competitor.py)
# ---------------------------------------------------------------------------

def analyze_meta_tags(html: str) -> dict:
    """Extract and analyze meta tags from HTML."""
    from html.parser import HTMLParser

    tags = {}

    class MetaParser(HTMLParser):
        def handle_starttag(self, tag, attrs):
            if tag == "meta":
                attrs_dict = dict(attrs)
                name = attrs_dict.get("name", attrs_dict.get("property", ""))
                content = attrs_dict.get("content", "")
                if name:
                    tags[name] = content
            elif tag == "title":
                self.in_title = True
            elif tag == "link":
                attrs_dict = dict(attrs)
                if attrs_dict.get("rel") == "canonical":
                    tags["canonical"] = attrs_dict.get("href", "")

        def handle_data(self, data):
            if getattr(self, "in_title", False):
                tags["title"] = data.strip()
                self.in_title = False

    parser = MetaParser()
    parser.feed(html)
    return tags


def evaluate_meta_quality(meta: dict, url: str) -> dict:
    """Evaluate the quality of meta tags, not just their existence."""
    quality = {"score": 0, "checks": [], "issues": []}
    total_weight = 0
    weighted_score = 0

    title = meta.get("title", "")
    title_weight = 20
    total_weight += title_weight
    if title:
        title_len = len(title)
        if 30 <= title_len <= 60:
            weighted_score += title_weight
            quality["checks"].append({"tag": "title", "status": "optimal", "value": title_len, "detail": f"{title_len} chars (ideal: 30-60)"})
        elif 20 <= title_len < 30 or 60 < title_len <= 70:
            weighted_score += title_weight * 0.7
            quality["checks"].append({"tag": "title", "status": "acceptable", "value": title_len, "detail": f"{title_len} chars (slightly off)"})
        else:
            weighted_score += title_weight * 0.3
            quality["issues"].append({"severity": "medium", "message": f"Title length {title_len} chars (ideal: 30-60)"})
    else:
        quality["issues"].append({"severity": "critical", "message": "Missing title tag"})

    desc = meta.get("description", "")
    desc_weight = 15
    total_weight += desc_weight
    if desc:
        desc_len = len(desc)
        if 120 <= desc_len <= 160:
            weighted_score += desc_weight
            quality["checks"].append({"tag": "description", "status": "optimal", "value": desc_len, "detail": f"{desc_len} chars (ideal: 120-160)"})
        elif 80 <= desc_len < 120 or 160 < desc_len <= 200:
            weighted_score += desc_weight * 0.7
            quality["checks"].append({"tag": "description", "status": "acceptable", "value": desc_len, "detail": f"{desc_len} chars"})
        else:
            weighted_score += desc_weight * 0.3
            quality["issues"].append({"severity": "low", "message": f"Description length {desc_len} chars (ideal: 120-160)"})
        if title and desc == title:
            weighted_score -= desc_weight * 0.3
            quality["issues"].append({"severity": "medium", "message": "Description duplicates title"})
    else:
        quality["issues"].append({"severity": "high", "message": "Missing meta description"})

    canonical = meta.get("canonical", "")
    canon_weight = 10
    total_weight += canon_weight
    if canonical:
        if canonical.startswith("http"):
            weighted_score += canon_weight
            if canonical.startswith("http://") and url.startswith("https://"):
                weighted_score -= canon_weight * 0.4
                quality["issues"].append({"severity": "medium", "message": "Canonical uses HTTP but page is HTTPS"})
        else:
            weighted_score += canon_weight * 0.5
            quality["issues"].append({"severity": "low", "message": "Canonical is relative URL (absolute recommended)"})
    else:
        quality["issues"].append({"severity": "medium", "message": "Missing canonical tag"})

    og_tags = ["og:title", "og:description", "og:image", "og:url"]
    og_weight = 10
    total_weight += og_weight
    og_present = sum(1 for t in og_tags if meta.get(t))
    og_ratio = og_present / len(og_tags)
    weighted_score += og_weight * og_ratio
    if og_ratio < 1.0:
        missing = [t for t in og_tags if not meta.get(t)]
        quality["issues"].append({"severity": "low", "message": f"Missing OG tags: {', '.join(missing)}"})

    twitter_tags = ["twitter:card", "twitter:title", "twitter:description"]
    tw_weight = 5
    total_weight += tw_weight
    tw_present = sum(1 for t in twitter_tags if meta.get(t))
    weighted_score += tw_weight * (tw_present / len(twitter_tags))

    quality["score"] = round((weighted_score / max(total_weight, 1)) * 100, 1)
    return quality


def analyze_heading_structure(html: str) -> dict:
    """Analyze heading hierarchy and H1 usage."""
    h1s = re.findall(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL | re.IGNORECASE)
    h2s = re.findall(r'<h2[^>]*>(.*?)</h2>', html, re.DOTALL | re.IGNORECASE)
    h3s = re.findall(r'<h3[^>]*>(.*?)</h3>', html, re.DOTALL | re.IGNORECASE)

    h1_clean = [re.sub(r'<[^>]+>', '', h).strip() for h in h1s]
    issues = []

    if len(h1s) == 0:
        issues.append({"severity": "high", "category": "structure", "message": "Missing H1 tag"})
    elif len(h1s) > 1:
        issues.append({"severity": "medium", "category": "structure", "message": f"Multiple H1 tags ({len(h1s)}) — use only one"})

    if len(h2s) == 0 and len(h3s) > 0:
        issues.append({"severity": "medium", "category": "structure", "message": "H3 used without H2 — broken heading hierarchy"})

    return {
        "h1_count": len(h1s),
        "h2_count": len(h2s),
        "h3_count": len(h3s),
        "h1_text": h1_clean[:3],
        "hierarchy_valid": len(h1s) == 1 and (len(h2s) > 0 or len(h3s) == 0),
        "issues": issues,
    }


def analyze_images(html: str) -> dict:
    """Analyze image alt text coverage."""
    images = re.findall(r'<img[^>]*>', html, re.IGNORECASE)
    total = len(images)
    with_alt = sum(1 for img in images if re.search(r'alt="[^"]+"|alt=\'[^\']+\'', img, re.IGNORECASE))
    empty_alt = sum(1 for img in images if re.search(r'alt=""|alt=\'\'', img, re.IGNORECASE))
    missing_alt = total - with_alt - empty_alt

    issues = []
    if total > 0 and missing_alt > 0:
        issues.append({"severity": "medium", "category": "accessibility", "message": f"{missing_alt}/{total} images missing alt text"})

    coverage = round((with_alt / max(total, 1)) * 100, 1)
    return {"total": total, "with_alt": with_alt, "missing_alt": missing_alt, "coverage": coverage, "issues": issues}


def analyze_links(html: str, url: str) -> dict:
    """Analyze internal vs external link distribution."""
    domain = url.split('/')[2] if len(url.split('/')) > 2 else ""
    all_links = re.findall(r'<a[^>]+href="([^"]*)"', html, re.IGNORECASE)

    internal = 0
    external = 0
    for link in all_links:
        if link.startswith('#') or link.startswith('javascript'):
            continue
        if link.startswith('/') or domain in link:
            internal += 1
        elif link.startswith('http'):
            external += 1

    return {"internal": internal, "external": external, "total": internal + external}


# ---------------------------------------------------------------------------
# 8-dimension quality scoring
# ---------------------------------------------------------------------------

def score_meta_quality(html: str, url: str = "https://example.com") -> dict:
    """Score meta tag quality (0-100)."""
    meta = analyze_meta_tags(html)
    quality = evaluate_meta_quality(meta, url)

    score = quality["score"]
    details = {"meta_tags": meta, "checks": quality["checks"], "issues": quality["issues"]}

    charset = bool(re.search(r'charset="?utf-8"?', html, re.IGNORECASE))
    if charset:
        score = min(100, score + 3)
    details["charset_utf8"] = charset

    og_type = bool(meta.get("og:type"))
    if og_type:
        score = min(100, score + 2)
    details["og_type"] = og_type

    return {"score": round(min(100, score), 1), "details": details}


def score_heading_structure(html: str) -> dict:
    """Score heading hierarchy quality (0-100)."""
    headings = analyze_heading_structure(html)

    score = 0.0
    details = dict(headings)

    h1_count = headings["h1_count"]
    h2_count = headings["h2_count"]
    h3_count = headings["h3_count"]
    h4s = len(re.findall(r'<h4[^>]*>', html, re.IGNORECASE))
    h5s = len(re.findall(r'<h5[^>]*>', html, re.IGNORECASE))
    h6s = len(re.findall(r'<h6[^>]*>', html, re.IGNORECASE))
    details["h4_count"] = h4s
    details["h5_count"] = h5s
    details["h6_count"] = h6s

    if h1_count == 1:
        score += 25
    elif h1_count > 1:
        score += 10
    # else 0

    if headings["hierarchy_valid"]:
        score += 20
    elif h1_count == 1:
        score += 10

    if h2_count >= 2:
        score += 15
    elif h2_count == 1:
        score += 10
    elif h2_count == 0 and h1_count > 0:
        score += 3

    depth = sum(1 for c in [h1_count, h2_count, h3_count, h4s] if c > 0)
    if depth >= 4:
        score += 15
    elif depth >= 3:
        score += 12
    elif depth >= 2:
        score += 8
    elif depth == 1:
        score += 3
    details["heading_depth"] = depth

    total_headings = h1_count + h2_count + h3_count + h4s + h5s + h6s
    if total_headings >= 5:
        score += 10
    elif total_headings >= 3:
        score += 7
    elif total_headings >= 1:
        score += 3
    details["total_headings"] = total_headings

    h1_text = headings["h1_text"]
    if h1_text:
        h1_len = len(h1_text[0])
        if 10 <= h1_len <= 70:
            score += 10
        elif h1_len > 0:
            score += 5
    details["h1_length_ok"] = bool(h1_text and 10 <= len(h1_text[0]) <= 70)

    if h1_count == 1 and h3_count > 0 and h2_count == 0:
        score -= 10
    details["skip_penalty"] = h3_count > 0 and h2_count == 0

    score = round(max(0, min(100, score)), 1)
    return {"score": score, "details": details}


def score_image_optimization(html: str) -> dict:
    """Score image optimization quality (0-100)."""
    images_data = analyze_images(html)
    total = images_data["total"]

    if total == 0:
        return {"score": 100.0, "details": {"total": 0, "note": "no images to optimize"}}

    score = 0.0
    details = dict(images_data)

    coverage = images_data["coverage"]
    if coverage >= 95:
        score += 30
    elif coverage >= 80:
        score += 22
    elif coverage >= 50:
        score += 12
    elif coverage > 0:
        score += 5

    all_imgs = re.findall(r'<img[^>]*>', html, re.IGNORECASE)

    lazy_count = sum(1 for img in all_imgs if 'loading="lazy"' in img.lower())
    eager_count = sum(1 for img in all_imgs if 'loading="eager"' in img.lower())
    loading_declared = lazy_count + eager_count
    if loading_declared > 0:
        score += 15
    details["lazy_loading"] = lazy_count
    details["eager_loading"] = eager_count

    srcset_count = sum(1 for img in all_imgs if 'srcset=' in img.lower())
    if srcset_count > 0:
        ratio = srcset_count / total
        if ratio >= 0.5:
            score += 15
        else:
            score += 8
    details["srcset_count"] = srcset_count

    picture_count = len(re.findall(r'<picture\b', html, re.IGNORECASE))
    if picture_count > 0:
        score += 5
    details["picture_elements"] = picture_count

    sized = sum(1 for img in all_imgs if re.search(r'\b(width|height)=', img, re.IGNORECASE))
    if sized > 0:
        ratio = sized / total
        if ratio >= 0.7:
            score += 10
        else:
            score += 5
    details["explicitly_sized"] = sized

    webp = sum(1 for img in all_imgs if '.webp' in img.lower())
    avif = sum(1 for img in all_imgs if '.avif' in img.lower())
    modern_formats = webp + avif
    if modern_formats > 0:
        score += 10
    details["modern_format_count"] = modern_formats

    decoding_async = sum(1 for img in all_imgs if 'decoding="async"' in img.lower())
    if decoding_async > 0:
        score += 5
    details["decoding_async"] = decoding_async

    fetchpriority = sum(1 for img in all_imgs if 'fetchpriority=' in img.lower())
    if fetchpriority > 0:
        score += 5
    details["fetchpriority"] = fetchpriority

    svg_imgs = sum(1 for img in all_imgs if '.svg' in img.lower())
    details["svg_count"] = svg_imgs

    score = round(min(100, score), 1)
    return {"score": score, "details": details}


def score_link_health(html: str, url: str = "https://example.com") -> dict:
    """Score link quality and distribution (0-100)."""
    links_data = analyze_links(html, url)
    internal = links_data["internal"]
    external = links_data["external"]
    total = links_data["total"]

    score = 0.0
    details = dict(links_data)

    if internal >= 10:
        score += 20
    elif internal >= 5:
        score += 15
    elif internal >= 1:
        score += 8

    if external >= 1 and external <= 20:
        score += 10
    elif external > 20:
        score += 5

    if total > 0:
        int_ratio = internal / total
        if 0.5 <= int_ratio <= 0.9:
            score += 10
        elif int_ratio > 0:
            score += 5
    details["internal_ratio"] = round(internal / max(total, 1), 2)

    all_anchors = re.findall(r'<a[^>]*>(.*?)</a>', html, re.DOTALL | re.IGNORECASE)
    non_empty = [re.sub(r'<[^>]+>', '', a).strip() for a in all_anchors]
    non_empty = [a for a in non_empty if a]
    unique_anchors = set(non_empty)
    if len(unique_anchors) >= 5:
        score += 10
    elif len(unique_anchors) >= 2:
        score += 5
    details["unique_anchor_texts"] = len(unique_anchors)

    generic_anchors = sum(1 for a in non_empty if a.lower() in (
        "click here", "here", "read more", "more", "link", "자세히", "더보기", "여기", "클릭"
    ))
    if non_empty and generic_anchors / len(non_empty) > 0.3:
        score -= 5
    details["generic_anchors"] = generic_anchors

    nofollow_links = len(re.findall(r'rel="[^"]*nofollow[^"]*"', html, re.IGNORECASE))
    details["nofollow_count"] = nofollow_links
    if nofollow_links > 0 and total > 0:
        nf_ratio = nofollow_links / total
        if nf_ratio > 0.5:
            score -= 5
    details["nofollow_ratio"] = round(nofollow_links / max(total, 1), 2)

    nav_links = re.findall(r'<nav\b[^>]*>(.*?)</nav>', html, re.DOTALL | re.IGNORECASE)
    nav_link_count = sum(len(re.findall(r'<a\b', nav, re.IGNORECASE)) for nav in nav_links)
    if nav_link_count >= 5:
        score += 15
    elif nav_link_count > 0:
        score += 8
    details["nav_link_count"] = nav_link_count

    breadcrumb = bool(re.search(r'(BreadcrumbList|aria-label="[^"]*breadcrumb|class="[^"]*breadcrumb)', html, re.IGNORECASE))
    if breadcrumb:
        score += 10
    details["has_breadcrumb"] = breadcrumb

    title_links = sum(1 for a in re.findall(r'<a[^>]*>', html, re.IGNORECASE) if 'title=' in a.lower())
    if title_links > 0:
        score += 5
    details["titled_links"] = title_links

    score = round(max(0, min(100, score)), 1)
    return {"score": score, "details": details}


def score_mobile_readiness(html: str) -> dict:
    """Score mobile optimization signals (0-100)."""
    score = 0.0
    signals = []

    viewport_match = re.search(r'<meta[^>]*name="viewport"[^>]*content="([^"]*)"', html, re.IGNORECASE)
    if not viewport_match:
        viewport_match = re.search(r'<meta[^>]*content="([^"]*)"[^>]*name="viewport"', html, re.IGNORECASE)

    if viewport_match:
        vp_content = viewport_match.group(1).lower()
        has_width = "width=device-width" in vp_content
        has_initial = "initial-scale=1" in vp_content or "initial-scale=1.0" in vp_content
        if has_width and has_initial:
            score += 25
            signals.append("viewport: optimal")
        elif has_width:
            score += 18
            signals.append("viewport: width only")
        else:
            score += 10
            signals.append("viewport: present but suboptimal")

        no_user_scalable = "user-scalable=no" in vp_content or "maximum-scale=1" in vp_content
        if no_user_scalable:
            score -= 10
            signals.append("viewport: zoom disabled (accessibility issue)")
    else:
        signals.append("viewport: missing")

    media_queries = len(re.findall(r'@media[^{]*\b(max-width|min-width)', html, re.IGNORECASE))
    responsive_links = len(re.findall(r'<link[^>]*media="[^"]*(?:max-width|min-width)', html, re.IGNORECASE))
    responsive_total = media_queries + responsive_links
    if responsive_total >= 3:
        score += 15
        signals.append(f"responsive: {responsive_total} breakpoints")
    elif responsive_total >= 1:
        score += 8
        signals.append(f"responsive: {responsive_total} breakpoint(s)")

    touch_targets = 0
    large_buttons = len(re.findall(r'<button\b[^>]*>', html, re.IGNORECASE))
    input_fields = len(re.findall(r'<input\b[^>]*>', html, re.IGNORECASE))
    touch_targets = large_buttons + input_fields
    if touch_targets >= 3:
        score += 10
        signals.append(f"touch targets: {touch_targets}")
    elif touch_targets > 0:
        score += 5

    tel_links = len(re.findall(r'href="tel:', html, re.IGNORECASE))
    if tel_links > 0:
        score += 8
        signals.append(f"click-to-call ({tel_links})")

    font_size_keywords = len(re.findall(r'font-size:\s*(?:\d+(?:\.\d+)?(?:rem|em|vw|%))', html, re.IGNORECASE))
    has_relative_fonts = font_size_keywords > 0
    if has_relative_fonts:
        score += 5
        signals.append("relative font sizes")

    fixed_width = bool(re.search(r'(?:width|min-width):\s*(?:9[0-9]{2}|[1-9]\d{3,})px', html, re.IGNORECASE))
    if fixed_width:
        score -= 10
        signals.append("fixed width detected (>= 900px)")

    apple_meta = bool(re.search(r'apple-mobile-web-app', html, re.IGNORECASE))
    theme_color = bool(re.search(r'name="theme-color"', html, re.IGNORECASE))
    if apple_meta:
        score += 5
        signals.append("apple mobile meta")
    if theme_color:
        score += 5
        signals.append("theme-color")

    sticky_nav = bool(re.search(r'position:\s*(?:sticky|fixed)', html, re.IGNORECASE))
    if sticky_nav:
        score += 5
        signals.append("sticky/fixed element")

    flexbox = bool(re.search(r'display:\s*flex', html, re.IGNORECASE))
    grid = bool(re.search(r'display:\s*grid', html, re.IGNORECASE))
    if flexbox or grid:
        score += 7
        signals.append("modern layout (flex/grid)")

    score = round(max(0, min(100, score)), 1)
    return {"score": score, "signals": signals}


def score_indexability(html: str) -> dict:
    """Score indexability signals (0-100)."""
    score = 0.0
    signals = []

    robots_meta = re.search(r'<meta[^>]*name="robots"[^>]*content="([^"]*)"', html, re.IGNORECASE)
    if not robots_meta:
        robots_meta = re.search(r'<meta[^>]*content="([^"]*)"[^>]*name="robots"', html, re.IGNORECASE)

    if robots_meta:
        directives = robots_meta.group(1).lower()
        if "noindex" in directives:
            score -= 30
            signals.append("robots: noindex")
        else:
            score += 15
            signals.append("robots: index allowed")
        if "nofollow" in directives:
            score -= 10
            signals.append("robots: nofollow")
    else:
        score += 15
        signals.append("robots: no restriction (default index)")

    canonical = re.search(r'<link[^>]*rel="canonical"[^>]*href="([^"]*)"', html, re.IGNORECASE)
    if not canonical:
        canonical = re.search(r'<link[^>]*href="([^"]*)"[^>]*rel="canonical"', html, re.IGNORECASE)
    if canonical:
        href = canonical.group(1)
        if href.startswith("https://"):
            score += 15
            signals.append("canonical: https absolute")
        elif href.startswith("http://"):
            score += 8
            signals.append("canonical: http (should be https)")
        elif href.startswith("/"):
            score += 5
            signals.append("canonical: relative (absolute recommended)")
        else:
            score += 3
    else:
        signals.append("canonical: missing")

    lang_match = re.search(r'<html[^>]*\blang="([^"]+)"', html, re.IGNORECASE)
    if lang_match:
        lang_val = lang_match.group(1)
        if re.match(r'^[a-z]{2}(-[A-Z]{2})?$', lang_val):
            score += 10
            signals.append(f"lang: {lang_val}")
        else:
            score += 5
            signals.append(f"lang: {lang_val} (non-standard format)")
    else:
        signals.append("lang: missing")

    hreflang_tags = re.findall(r'hreflang="([^"]+)"', html, re.IGNORECASE)
    unique_hreflangs = set(hreflang_tags)
    if len(unique_hreflangs) >= 2:
        score += 10
        signals.append(f"hreflang: {len(unique_hreflangs)} languages")
        if "x-default" in unique_hreflangs:
            score += 5
            signals.append("hreflang: x-default present")
    elif len(unique_hreflangs) == 1:
        score += 5
        signals.append("hreflang: 1 language")

    title = bool(re.search(r'<title>[^<]+</title>', html, re.IGNORECASE))
    if title:
        score += 10
        signals.append("title tag present")

    desc = bool(re.search(r'name="description"', html, re.IGNORECASE))
    if desc:
        score += 8
        signals.append("meta description present")

    sitemap_ref = bool(re.search(r'sitemap\.xml', html, re.IGNORECASE))
    if sitemap_ref:
        score += 5
        signals.append("sitemap reference")

    json_ld = bool(re.search(r'application/ld\+json', html, re.IGNORECASE))
    if json_ld:
        score += 10
        signals.append("JSON-LD present")

    noarchive = bool(re.search(r'noarchive', html, re.IGNORECASE))
    if noarchive:
        score -= 5
        signals.append("noarchive directive")

    score = round(max(0, min(100, score)), 1)
    return {"score": score, "signals": signals}


def score_security_signals(html: str, url: str = "https://example.com") -> dict:
    """Score security signals detectable from HTML (0-100)."""
    score = 0.0
    signals = []

    is_https = url.startswith("https://")
    if is_https:
        score += 30
        signals.append("HTTPS")
    else:
        signals.append("HTTP only")

    csp_meta = bool(re.search(r'<meta[^>]*http-equiv="Content-Security-Policy"', html, re.IGNORECASE))
    if csp_meta:
        score += 15
        signals.append("CSP meta tag")

    mixed_http_src = len(re.findall(r'(?:src|href)="http://', html, re.IGNORECASE))
    mixed_http_link = len(re.findall(r'<link[^>]*href="http://', html, re.IGNORECASE))
    mixed_content = mixed_http_src + mixed_http_link
    if is_https and mixed_content > 0:
        penalty = min(15, mixed_content * 3)
        score -= penalty
        signals.append(f"mixed content ({mixed_content} http resources)")
    elif is_https:
        score += 10
        signals.append("no mixed content")

    referrer_policy = bool(re.search(r'name="referrer"', html, re.IGNORECASE))
    if referrer_policy:
        score += 8
        signals.append("referrer policy")

    sri_tags = len(re.findall(r'\bintegrity="sha', html, re.IGNORECASE))
    if sri_tags > 0:
        score += 10
        signals.append(f"SRI ({sri_tags} resources)")

    crossorigin = len(re.findall(r'\bcrossorigin=', html, re.IGNORECASE))
    if crossorigin > 0:
        score += 5
        signals.append(f"crossorigin ({crossorigin})")

    permissions_policy = bool(re.search(r'permissions-policy', html, re.IGNORECASE))
    if permissions_policy:
        score += 5
        signals.append("permissions policy")

    unsafe_inline_js = len(re.findall(r'on(?:click|load|error|mouseover)\s*=', html, re.IGNORECASE))
    if unsafe_inline_js > 5:
        score -= 10
        signals.append(f"inline event handlers ({unsafe_inline_js})")
    elif unsafe_inline_js > 0:
        score -= 3

    form_actions = re.findall(r'<form[^>]*action="(https?://[^"]*)"', html, re.IGNORECASE)
    insecure_forms = [f for f in form_actions if f.startswith("http://")]
    if insecure_forms:
        score -= 10
        signals.append(f"insecure form action ({len(insecure_forms)})")
    elif form_actions:
        score += 5
        signals.append("secure form actions")

    autocomplete_off = bool(re.search(r'autocomplete="off"', html, re.IGNORECASE))
    if autocomplete_off:
        score += 3

    score = round(max(0, min(100, score)), 1)
    return {"score": score, "signals": signals}


def score_performance_signals(html: str) -> dict:
    """Score performance optimization signals detectable from HTML (0-100)."""
    score = 0.0
    signals = []

    preconnect = len(re.findall(r'rel="preconnect"', html, re.IGNORECASE))
    dns_prefetch = len(re.findall(r'rel="dns-prefetch"', html, re.IGNORECASE))
    preload = len(re.findall(r'rel="preload"', html, re.IGNORECASE))
    prefetch = len(re.findall(r'rel="prefetch"', html, re.IGNORECASE))

    hints_total = preconnect + dns_prefetch + preload + prefetch
    if hints_total >= 4:
        score += 20
        signals.append(f"resource hints ({hints_total}: preconnect={preconnect}, preload={preload})")
    elif hints_total >= 2:
        score += 12
        signals.append(f"resource hints ({hints_total})")
    elif hints_total >= 1:
        score += 6
        signals.append(f"resource hints ({hints_total})")

    critical_css = bool(re.search(r'<style[^>]*>(.*?)</style>', html, re.DOTALL | re.IGNORECASE))
    if critical_css:
        score += 12
        signals.append("inline critical CSS")

    async_scripts = len(re.findall(r'<script[^>]*\basync\b', html, re.IGNORECASE))
    defer_scripts = len(re.findall(r'<script[^>]*\bdefer\b', html, re.IGNORECASE))
    total_scripts = len(re.findall(r'<script\b', html, re.IGNORECASE))
    if total_scripts > 0:
        optimized_ratio = (async_scripts + defer_scripts) / total_scripts
        if optimized_ratio >= 0.7:
            score += 15
            signals.append(f"script optimization ({async_scripts} async, {defer_scripts} defer / {total_scripts} total)")
        elif optimized_ratio >= 0.3:
            score += 8
            signals.append(f"partial script optimization ({async_scripts + defer_scripts}/{total_scripts})")
    else:
        score += 15
        signals.append("no blocking scripts")

    module_scripts = len(re.findall(r'type="module"', html, re.IGNORECASE))
    if module_scripts > 0:
        score += 5
        signals.append(f"ES modules ({module_scripts})")

    lazy_images = len(re.findall(r'loading="lazy"', html, re.IGNORECASE))
    if lazy_images >= 3:
        score += 10
        signals.append(f"lazy images ({lazy_images})")
    elif lazy_images > 0:
        score += 5
        signals.append(f"lazy images ({lazy_images})")

    srcset = len(re.findall(r'\bsrcset=', html, re.IGNORECASE))
    if srcset > 0:
        score += 5
        signals.append(f"responsive images ({srcset})")

    font_display = len(re.findall(r'font-display:\s*(?:swap|optional|fallback)', html, re.IGNORECASE))
    if font_display > 0:
        score += 8
        signals.append(f"font-display ({font_display})")

    preload_fonts = len(re.findall(r'rel="preload"[^>]*as="font"', html, re.IGNORECASE))
    if preload_fonts > 0:
        score += 5
        signals.append(f"preloaded fonts ({preload_fonts})")

    will_change = len(re.findall(r'will-change:', html, re.IGNORECASE))
    contain = len(re.findall(r'contain:\s*(?:content|strict|layout|paint)', html, re.IGNORECASE))
    if will_change > 0 or contain > 0:
        score += 5
        signals.append("CSS containment/will-change")

    score = round(min(100, score), 1)
    return {"score": score, "signals": signals}


# ---------------------------------------------------------------------------
# Orchestrators
# ---------------------------------------------------------------------------

def analyze_technical_html(html: str, url: str = "https://example.com") -> dict:
    """Full 8-dimension technical SEO analysis on raw HTML."""
    meta_q = score_meta_quality(html, url)
    heading_s = score_heading_structure(html)
    image_o = score_image_optimization(html)
    link_h = score_link_health(html, url)
    mobile_r = score_mobile_readiness(html)
    index_s = score_indexability(html)
    security_s = score_security_signals(html, url)
    perf_s = score_performance_signals(html)

    dimensions = {
        "meta_quality": meta_q["score"],
        "heading_structure": heading_s["score"],
        "image_optimization": image_o["score"],
        "link_health": link_h["score"],
        "mobile_readiness": mobile_r["score"],
        "indexability": index_s["score"],
        "security_signals": security_s["score"],
        "performance_signals": perf_s["score"],
    }

    overall = round(sum(dimensions[k] * DIMENSION_WEIGHTS[k] for k in DIMENSION_WEIGHTS), 1)

    issues = []
    if meta_q["score"] < 40:
        issues.append({"severity": "critical", "category": "meta", "message": "메타 태그 품질 심각하게 미흡"})
    if heading_s["score"] < 30:
        issues.append({"severity": "high", "category": "structure", "message": "헤딩 구조 미흡 — H1/H2 계층 확인 필요"})
    if image_o["score"] < 40 and image_o["details"].get("total", 0) > 0:
        issues.append({"severity": "medium", "category": "images", "message": "이미지 최적화 부족 — alt, lazy loading, srcset 확인"})
    if mobile_r["score"] < 30:
        issues.append({"severity": "critical", "category": "mobile", "message": "모바일 최적화 미흡 — viewport 및 반응형 확인"})
    if index_s["score"] < 40:
        issues.append({"severity": "high", "category": "indexability", "message": "인덱싱 신호 부족 — robots, canonical, lang 확인"})
    if security_s["score"] < 30:
        issues.append({"severity": "high", "category": "security", "message": "보안 신호 미흡 — HTTPS, CSP, 혼합 콘텐츠 확인"})
    if perf_s["score"] < 30:
        issues.append({"severity": "medium", "category": "performance", "message": "성능 신호 미흡 — preload, async/defer, lazy loading 확인"})
    issues.extend(heading_s["details"].get("issues", []))
    issues.extend(image_o["details"].get("issues", []))

    return {
        "score": overall,
        "dimensions": dimensions,
        "details": {
            "meta_quality": meta_q,
            "heading_structure": heading_s,
            "image_optimization": image_o,
            "link_health": link_h,
            "mobile_readiness": mobile_r,
            "indexability": index_s,
            "security_signals": security_s,
            "performance_signals": perf_s,
        },
        "issues": issues,
        # backward compat for analyze_technical callers
        "section_scores": {
            "meta_quality": meta_q["score"],
            "headings": heading_s["score"],
            "images": image_o["score"],
            "mobile": mobile_r["score"],
            "security": security_s["score"],
            "performance": perf_s["score"],
        },
    }


def check_https(url: str) -> dict:
    """Check HTTPS and security headers."""
    result = fetch_page(url, user_agent="default")
    if not result["success"]:
        return {"https": False, "error": result["error"]}

    headers = result.get("headers", {})
    return {
        "https": url.startswith("https"),
        "hsts": "strict-transport-security" in headers,
        "x_content_type": "x-content-type-options" in headers,
        "x_frame": "x-frame-options" in headers,
        "csp": "content-security-policy" in headers,
    }


def check_mobile(html: str) -> dict:
    """Check mobile optimization signals (legacy)."""
    has_viewport = 'name="viewport"' in html or "name='viewport'" in html
    has_responsive = "@media" in html or 'rel="stylesheet"' in html
    return {
        "viewport_meta": has_viewport,
        "responsive_signals": has_responsive,
    }


def analyze_technical(url: str) -> dict:
    """Run full technical SEO analysis (URL-based entry point)."""
    validation = validate_url(url)
    if not validation["valid"]:
        return {"success": False, "error": validation["error"]}

    result = fetch_page(url)
    if not result["success"]:
        return {"success": False, "error": result["error"]}

    html = result["html"]
    analysis = analyze_technical_html(html, url)

    security = check_https(url)
    mobile = check_mobile(html)
    meta = analyze_meta_tags(html)
    headings = analyze_heading_structure(html)
    images = analyze_images(html)
    links = analyze_links(html, url)

    elapsed = result.get("elapsed_seconds", 0)
    issues = list(analysis["issues"])

    if not security.get("https"):
        issues.append({"severity": "critical", "category": "security", "message": "Not using HTTPS"})
    if not security.get("hsts"):
        issues.append({"severity": "medium", "category": "security", "message": "Missing HSTS header"})
    if not mobile.get("viewport_meta"):
        issues.append({"severity": "critical", "category": "mobile", "message": "Missing viewport meta tag"})
    if elapsed and elapsed > 3.0:
        issues.append({"severity": "high", "category": "performance", "message": f"Slow response time: {elapsed:.1f}s (target: <1s)"})
    elif elapsed and elapsed > 1.0:
        issues.append({"severity": "medium", "category": "performance", "message": f"Response time {elapsed:.1f}s (target: <1s)"})

    return {
        "success": True,
        "url": url,
        "score": analysis["score"],
        "dimensions": analysis["dimensions"],
        "section_scores": analysis["section_scores"],
        "meta_tags": meta,
        "meta_quality": analysis["details"]["meta_quality"]["details"].get("checks", []),
        "security": security,
        "mobile": mobile,
        "headings": headings,
        "images": {"total": images["total"], "with_alt": images["with_alt"], "coverage": images["coverage"]},
        "links": links,
        "issues": issues,
        "response_time": elapsed,
    }


def main():
    parser = argparse.ArgumentParser(description="Technical SEO analysis — 8-dimension scoring")
    parser.add_argument("url", help="URL to analyze")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    result = analyze_technical(args.url)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result["success"]:
            print(f"Technical SEO Score: {result['score']}/100")
            print(f"\nDimensions:")
            for dim, w in DIMENSION_WEIGHTS.items():
                s = result["dimensions"][dim]
                bar = "█" * int(s / 5) + "░" * (20 - int(s / 5))
                print(f"  {dim:25s} {bar} {s:5.1f} (×{w})")
            print(f"\nIssues ({len(result['issues'])}):")
            for issue in result["issues"]:
                print(f"  [{issue['severity'].upper()}] {issue['message']}")
        else:
            print(f"Error: {result['error']}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()

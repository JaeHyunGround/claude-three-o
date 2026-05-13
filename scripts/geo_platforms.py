"""Platform-specific AI optimization — multi-dimensional per-platform scoring.

Each platform (ChatGPT, Perplexity, Gemini, Claude) is scored across 5 dimensions
tuned to that platform's actual citation/ranking preferences.

Cross-platform analysis identifies optimization gaps and priority actions.
"""

import argparse
import json
import re
import sys
from datetime import datetime
from typing import Optional

from validate_url import validate_url
from fetch_page import fetch_page


CURRENT_YEAR = datetime.now().year

PLATFORM_CONFIGS = {
    "chatgpt": {
        "name": "ChatGPT",
        "provider": "OpenAI",
        "crawler": "GPTBot",
        "factors": ["extractability", "structure", "structured_data", "freshness", "crawler_access"],
    },
    "perplexity": {
        "name": "Perplexity",
        "provider": "Perplexity AI",
        "crawler": "PerplexityBot",
        "factors": ["factual_density", "source_attribution", "recency", "snippet_quality", "crawler_access"],
    },
    "gemini": {
        "name": "Gemini",
        "provider": "Google",
        "crawler": "Google-Extended",
        "factors": ["eeat_signals", "structured_data", "content_depth", "comparison_data", "crawler_access"],
    },
    "claude": {
        "name": "Claude",
        "provider": "Anthropic",
        "crawler": "ClaudeBot",
        "factors": ["content_depth", "data_evidence", "nuanced_reasoning", "technical_quality", "crawler_access"],
    },
}


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _extract_text(html: str) -> str:
    return re.sub(r'<[^>]+>', ' ', html).strip()


def _extract_paragraphs(html: str) -> list:
    paras = re.findall(r'<p[^>]*>(.*?)</p>', html, re.DOTALL | re.IGNORECASE)
    return [re.sub(r'<[^>]+>', '', p).strip() for p in paras if len(re.sub(r'<[^>]+>', '', p).strip()) > 20]


def _check_crawler_blocked(html: str, crawler_name: str) -> dict:
    """Check if a specific crawler is blocked via robots meta."""
    score = 100.0
    signals = []

    generic_robots = re.search(r'<meta[^>]*name="robots"[^>]*content="([^"]*)"', html, re.IGNORECASE)
    if not generic_robots:
        generic_robots = re.search(r'<meta[^>]*content="([^"]*)"[^>]*name="robots"', html, re.IGNORECASE)

    if generic_robots:
        directives = generic_robots.group(1).lower()
        if "noindex" in directives:
            score -= 40
            signals.append("robots: noindex (blocks all crawlers)")
        if "nofollow" in directives:
            score -= 15
            signals.append("robots: nofollow")

    bot_robots = re.search(
        rf'<meta[^>]*name="{re.escape(crawler_name)}"[^>]*content="([^"]*)"',
        html, re.IGNORECASE
    )
    if not bot_robots:
        bot_robots = re.search(
            rf'<meta[^>]*content="([^"]*)"[^>]*name="{re.escape(crawler_name)}"',
            html, re.IGNORECASE
        )

    if bot_robots:
        directives = bot_robots.group(1).lower()
        if "noindex" in directives or "none" in directives:
            score -= 50
            signals.append(f"{crawler_name}: explicitly blocked")
        elif "nofollow" in directives:
            score -= 20
            signals.append(f"{crawler_name}: nofollow")
        else:
            signals.append(f"{crawler_name}: allowed")
    else:
        signals.append(f"{crawler_name}: no restriction")

    llms_txt = bool(re.search(r'llms\.txt', html, re.IGNORECASE))
    if llms_txt:
        score = min(100, score + 10)
        signals.append("llms.txt reference detected")

    ai_txt = bool(re.search(r'ai\.txt', html, re.IGNORECASE))
    if ai_txt:
        score = min(100, score + 5)
        signals.append("ai.txt reference detected")

    return {"score": round(max(0, min(100, score)), 1), "signals": signals}


def _count_definitions(paragraphs: list) -> int:
    count = 0
    for p in paragraphs:
        if re.search(r'(는|은|이란|란)\s+.{10,}(이다|입니다|합니다|것이다|것입니다)', p):
            count += 1
        elif re.search(r'\b(is a|is the|refers to|means|defined as|known as)\b', p, re.IGNORECASE):
            count += 1
    return count


def _count_data_points(text: str) -> int:
    numbers = re.findall(r'\d+[\d,.]*\s*(?:%|원|달러|\$|€|명|건|억|만|배|kg|km|GB|MB|개|회|년|위)', text)
    plain_nums = re.findall(r'(?<!\w)\d{2,}(?:[,.\d]*\d)?(?!\w)', text)
    return len(numbers) + len(plain_nums) // 3


def _detect_recency(html: str) -> dict:
    score = 0.0
    signals = []

    current = CURRENT_YEAR
    if re.search(rf'\b{current}\b', html):
        score += 40
        signals.append(f"current year ({current}) reference")
    elif re.search(rf'\b{current - 1}\b', html):
        score += 25
        signals.append(f"last year ({current - 1}) reference")
    elif re.search(rf'\b{current - 2}\b', html):
        score += 10
        signals.append(f"{current - 2} reference (aging)")

    date_patterns = re.findall(r'(published|modified|updated|datePublished|dateModified|작성일|수정일|업데이트)', html, re.IGNORECASE)
    if date_patterns:
        score += 20
        signals.append(f"date metadata ({len(date_patterns)} signals)")

    time_tags = len(re.findall(r'<time\b[^>]*datetime=', html, re.IGNORECASE))
    if time_tags > 0:
        score += 15
        signals.append(f"<time> elements ({time_tags})")

    schema_date = bool(re.search(r'"dateModified"|"datePublished"', html))
    if schema_date:
        score += 15
        signals.append("schema date fields")

    recent_words = len(re.findall(r'(latest|newest|updated|최신|업데이트|신규|개정)', html, re.IGNORECASE))
    if recent_words >= 2:
        score += 10
        signals.append(f"freshness language ({recent_words})")

    return {"score": round(min(100, score), 1), "signals": signals}


# ---------------------------------------------------------------------------
# Platform analyzers — multi-dimensional
# ---------------------------------------------------------------------------

def analyze_for_chatgpt(html: str, url: str) -> dict:
    """ChatGPT optimization: extractability, structure, schema, freshness, access."""
    paragraphs = _extract_paragraphs(html)
    dimensions = {}

    # 1. Extractability (0.30) — concise citable passages, definitions, Q&A
    ext_score = 0.0
    ext_signals = []

    short_clear = sum(1 for p in paragraphs if 80 < len(p) < 300)
    if short_clear >= 5:
        ext_score += 30
        ext_signals.append(f"{short_clear} concise paragraphs (80-300 chars)")
    elif short_clear >= 3:
        ext_score += 18
        ext_signals.append(f"{short_clear} concise paragraphs")
    elif short_clear >= 1:
        ext_score += 8

    defs = _count_definitions(paragraphs)
    if defs >= 3:
        ext_score += 30
        ext_signals.append(f"{defs} definition sentences (high citation probability)")
    elif defs >= 1:
        ext_score += 15
        ext_signals.append(f"{defs} definition sentence(s)")

    has_faq = bool(re.search(r'(FAQ|자주\s*묻는|질문과\s*답|Q\s*&\s*A|Q:)', html, re.IGNORECASE))
    if has_faq:
        ext_score += 15
        ext_signals.append("FAQ/Q&A content")

    step_patterns = len(re.findall(r'(step \d|단계\s*\d|(?:첫째|둘째|셋째)|1\.\s|2\.\s|3\.\s)', html, re.IGNORECASE))
    if step_patterns >= 3:
        ext_score += 15
        ext_signals.append(f"step-by-step content ({step_patterns})")
    elif step_patterns >= 1:
        ext_score += 8

    how_to = bool(re.search(r'(how to|방법|하는 법|가이드)', html, re.IGNORECASE))
    if how_to:
        ext_score += 10
        ext_signals.append("how-to/guide content")

    dimensions["extractability"] = {"score": round(min(100, ext_score), 1), "signals": ext_signals}

    # 2. Structure (0.25) — headings, lists, tables
    str_score = 0.0
    str_signals = []

    headings = len(re.findall(r'<h[2-4][^>]*>', html, re.IGNORECASE))
    if headings >= 6:
        str_score += 30
        str_signals.append(f"{headings} sub-headings (strong hierarchy)")
    elif headings >= 3:
        str_score += 20
        str_signals.append(f"{headings} sub-headings")
    elif headings >= 1:
        str_score += 10

    lists = len(re.findall(r'<[ou]l[^>]*>', html, re.IGNORECASE))
    list_items = len(re.findall(r'<li[^>]*>', html, re.IGNORECASE))
    if list_items >= 10:
        str_score += 25
        str_signals.append(f"{lists} lists ({list_items} items)")
    elif list_items >= 5:
        str_score += 15
        str_signals.append(f"{lists} lists ({list_items} items)")
    elif lists > 0:
        str_score += 8

    tables = len(re.findall(r'<table[^>]*>', html, re.IGNORECASE))
    if tables >= 2:
        str_score += 20
        str_signals.append(f"{tables} data tables")
    elif tables > 0:
        str_score += 10

    dl_tags = len(re.findall(r'<dl[^>]*>', html, re.IGNORECASE))
    if dl_tags > 0:
        str_score += 10
        str_signals.append(f"definition lists ({dl_tags})")

    blockquotes = len(re.findall(r'<blockquote[^>]*>', html, re.IGNORECASE))
    if blockquotes > 0:
        str_score += 10
        str_signals.append(f"blockquotes ({blockquotes})")

    summary_details = len(re.findall(r'<details[^>]*>', html, re.IGNORECASE))
    if summary_details > 0:
        str_score += 5

    dimensions["structure"] = {"score": round(min(100, str_score), 1), "signals": str_signals}

    # 3. Structured data (0.20)
    sd_score = 0.0
    sd_signals = []

    ld_blocks = re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.DOTALL | re.IGNORECASE)
    valid_schemas = 0
    schema_types = []
    for block in ld_blocks:
        try:
            data = json.loads(block)
            if isinstance(data, dict) and "@type" in data:
                valid_schemas += 1
                schema_types.append(data["@type"])
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and "@type" in item:
                        valid_schemas += 1
                        schema_types.append(item["@type"])
        except (json.JSONDecodeError, TypeError):
            pass

    if valid_schemas >= 3:
        sd_score += 40
        sd_signals.append(f"JSON-LD ({valid_schemas} schemas: {', '.join(schema_types[:5])})")
    elif valid_schemas >= 1:
        sd_score += 25
        sd_signals.append(f"JSON-LD ({valid_schemas} schema: {', '.join(schema_types)})")
    elif ld_blocks:
        sd_score += 10
        sd_signals.append("JSON-LD present (parse errors)")

    og_count = len(re.findall(r'property="og:', html, re.IGNORECASE))
    if og_count >= 4:
        sd_score += 20
        sd_signals.append(f"Open Graph ({og_count} tags)")
    elif og_count > 0:
        sd_score += 10

    article_schema = any(t in ("Article", "NewsArticle", "BlogPosting", "TechArticle") for t in schema_types)
    if article_schema:
        sd_score += 20
        sd_signals.append("Article-type schema (ChatGPT preferred)")

    faq_schema = "FAQPage" in schema_types
    if faq_schema:
        sd_score += 15
        sd_signals.append("FAQPage schema")

    microdata = len(re.findall(r'itemtype=', html, re.IGNORECASE))
    if microdata > 0 and valid_schemas == 0:
        sd_score += 10
        sd_signals.append(f"Microdata ({microdata})")

    dimensions["structured_data"] = {"score": round(min(100, sd_score), 1), "signals": sd_signals}

    # 4. Freshness (0.10)
    recency = _detect_recency(html)
    dimensions["freshness"] = recency

    # 5. Crawler access (0.15)
    access = _check_crawler_blocked(html, "GPTBot")
    dimensions["crawler_access"] = access

    # Weighted overall
    weights = {"extractability": 0.30, "structure": 0.25, "structured_data": 0.20, "freshness": 0.10, "crawler_access": 0.15}
    overall = round(sum(dimensions[k]["score"] * weights[k] for k in weights), 1)

    all_signals = []
    for dim in dimensions.values():
        all_signals.extend(dim["signals"])

    return {"score": min(100, overall), "signals": all_signals, "dimensions": dimensions}


def analyze_for_perplexity(html: str, url: str) -> dict:
    """Perplexity optimization: factual density, sources, recency, snippets, access."""
    text = _extract_text(html)
    paragraphs = _extract_paragraphs(html)
    dimensions = {}

    # 1. Factual density (0.30)
    fd_score = 0.0
    fd_signals = []

    data_points = _count_data_points(text)
    if data_points > 20:
        fd_score += 35
        fd_signals.append(f"very high data density ({data_points} data points)")
    elif data_points > 10:
        fd_score += 25
        fd_signals.append(f"good data density ({data_points} data points)")
    elif data_points > 5:
        fd_score += 15
        fd_signals.append(f"moderate data ({data_points} points)")
    elif data_points > 0:
        fd_score += 5

    proper_nouns = len(re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b', text))
    korean_proper = len(re.findall(r'[가-힣]{2,4}(?:대학교|연구소|병원|센터|그룹|주식회사)', text))
    named_entities = proper_nouns + korean_proper
    if named_entities >= 10:
        fd_score += 25
        fd_signals.append(f"high entity density ({named_entities} named entities)")
    elif named_entities >= 5:
        fd_score += 15
        fd_signals.append(f"entity mentions ({named_entities})")
    elif named_entities > 0:
        fd_score += 5

    tables = len(re.findall(r'<table[^>]*>', html, re.IGNORECASE))
    if tables >= 1:
        fd_score += 15
        fd_signals.append(f"tabular data ({tables} tables)")

    comparisons = len(re.findall(r'(vs\.?|versus|비교|차이점|대비|compared to)', html, re.IGNORECASE))
    if comparisons >= 2:
        fd_score += 15
        fd_signals.append(f"comparison data ({comparisons})")
    elif comparisons > 0:
        fd_score += 8

    stat_patterns = len(re.findall(r'(according to|survey|study|research|statistics|통계|조사|연구)', text, re.IGNORECASE))
    if stat_patterns >= 2:
        fd_score += 10
        fd_signals.append("statistical references")

    dimensions["factual_density"] = {"score": round(min(100, fd_score), 1), "signals": fd_signals}

    # 2. Source attribution (0.25)
    sa_score = 0.0
    sa_signals = []

    source_refs = len(re.findall(r'(source|reference|citation|출처|참고|참조|인용)', html, re.IGNORECASE))
    if source_refs >= 5:
        sa_score += 30
        sa_signals.append(f"{source_refs} source attributions")
    elif source_refs >= 2:
        sa_score += 20
        sa_signals.append(f"{source_refs} source attributions")
    elif source_refs > 0:
        sa_score += 10
        sa_signals.append("source attribution present")

    has_author = bool(re.search(r'(author|byline|작성자|기자|편집|저자)', html, re.IGNORECASE))
    if has_author:
        sa_score += 20
        sa_signals.append("author attribution")

    domain = url.split('/')[2] if len(url.split('/')) > 2 else ""
    outbound = len(re.findall(r'<a[^>]+href="https?://(?!' + re.escape(domain) + r')', html, re.IGNORECASE))
    if outbound >= 5:
        sa_score += 20
        sa_signals.append(f"{outbound} outbound references (cross-verification)")
    elif outbound >= 2:
        sa_score += 12
        sa_signals.append(f"{outbound} outbound references")
    elif outbound > 0:
        sa_score += 5

    footnotes = len(re.findall(r'(\[\d+\]|<sup|<footnote|각주)', html, re.IGNORECASE))
    if footnotes > 0:
        sa_score += 15
        sa_signals.append(f"footnotes/citations ({footnotes})")

    canonical = bool(re.search(r'rel="canonical"', html, re.IGNORECASE))
    if canonical:
        sa_score += 10
        sa_signals.append("canonical URL")

    dimensions["source_attribution"] = {"score": round(min(100, sa_score), 1), "signals": sa_signals}

    # 3. Recency (0.15)
    recency = _detect_recency(html)
    dimensions["recency"] = recency

    # 4. Snippet quality (0.15)
    sq_score = 0.0
    sq_signals = []

    meta_desc = re.search(r'name="description"[^>]*content="([^"]*)"', html, re.IGNORECASE)
    if not meta_desc:
        meta_desc = re.search(r'content="([^"]*)"[^>]*name="description"', html, re.IGNORECASE)
    if meta_desc:
        desc_len = len(meta_desc.group(1))
        if 80 <= desc_len <= 160:
            sq_score += 30
            sq_signals.append("rich meta description (optimal length)")
        elif desc_len > 50:
            sq_score += 18
            sq_signals.append("meta description present")
        else:
            sq_score += 8

    self_contained = sum(1 for p in paragraphs if len(p) >= 100 and not p.startswith(("이", "그", "저", "이것", "그것")))
    if self_contained >= 5:
        sq_score += 25
        sq_signals.append(f"{self_contained} self-contained passages")
    elif self_contained >= 2:
        sq_score += 15
        sq_signals.append(f"{self_contained} self-contained passages")

    title_match = re.search(r'<title>([^<]+)</title>', html, re.IGNORECASE)
    if title_match:
        title = title_match.group(1).strip()
        if 30 <= len(title) <= 65:
            sq_score += 20
            sq_signals.append("optimal title length")
        elif title:
            sq_score += 10

    h1_match = re.search(r'<h1[^>]*>([^<]+)</h1>', html, re.IGNORECASE)
    if h1_match and title_match:
        h1_text = h1_match.group(1).strip().lower()
        title_text = title_match.group(1).strip().lower()
        if h1_text in title_text or title_text in h1_text:
            sq_score += 10
            sq_signals.append("title/H1 alignment")

    og_desc = bool(re.search(r'property="og:description"', html, re.IGNORECASE))
    if og_desc:
        sq_score += 10
        sq_signals.append("OG description")

    dimensions["snippet_quality"] = {"score": round(min(100, sq_score), 1), "signals": sq_signals}

    # 5. Crawler access (0.15)
    access = _check_crawler_blocked(html, "PerplexityBot")
    dimensions["crawler_access"] = access

    weights = {"factual_density": 0.30, "source_attribution": 0.25, "recency": 0.15, "snippet_quality": 0.15, "crawler_access": 0.15}
    overall = round(sum(dimensions[k]["score"] * weights[k] for k in weights), 1)

    all_signals = []
    for dim in dimensions.values():
        all_signals.extend(dim["signals"])

    return {"score": min(100, overall), "signals": all_signals, "dimensions": dimensions}


def analyze_for_gemini(html: str, url: str) -> dict:
    """Gemini/AI Overview optimization: E-E-A-T, schema, depth, comparison, access."""
    text = _extract_text(html)
    paragraphs = _extract_paragraphs(html)
    dimensions = {}

    # 1. E-E-A-T signals (0.30)
    eeat_score = 0.0
    eeat_signals = []

    author_patterns = [
        (r'(author|written by|작성자|기자|저자)', "author attribution"),
        (r'(expert|Ph\.?D|professor|박사|전문가|자격증|면허)', "expertise credentials"),
        (r'(years? of experience|경력\s*\d+|경험|실무\s*\d+)', "experience signals"),
        (r'(award|certified|인증|수상|선정|공인)', "recognition/certification"),
        (r'(review|peer|검증|검토|감수)', "peer review signals"),
        (r'(established|founded|since\s*\d{4}|설립|창립)', "establishment history"),
    ]
    for pattern, label in author_patterns:
        if re.search(pattern, html, re.IGNORECASE):
            eeat_score += 12
            eeat_signals.append(label)

    about_page = bool(re.search(r'href="[^"]*(?:about|소개|회사)"', html, re.IGNORECASE))
    if about_page:
        eeat_score += 8
        eeat_signals.append("about page link")

    contact_info = bool(re.search(r'(tel:|mailto:|@|전화|이메일|contact)', html, re.IGNORECASE))
    if contact_info:
        eeat_score += 8
        eeat_signals.append("contact information")

    dimensions["eeat_signals"] = {"score": round(min(100, eeat_score), 1), "signals": eeat_signals}

    # 2. Structured data (0.25)
    sd_score = 0.0
    sd_signals = []

    ld_blocks = re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.DOTALL | re.IGNORECASE)
    schema_types = []
    for block in ld_blocks:
        try:
            data = json.loads(block)
            if isinstance(data, dict) and "@type" in data:
                schema_types.append(data["@type"])
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and "@type" in item:
                        schema_types.append(item["@type"])
        except (json.JSONDecodeError, TypeError):
            pass

    if len(schema_types) >= 3:
        sd_score += 35
        sd_signals.append(f"rich JSON-LD ({len(schema_types)} types: {', '.join(schema_types[:5])})")
    elif len(schema_types) >= 1:
        sd_score += 22
        sd_signals.append(f"JSON-LD ({', '.join(schema_types)})")

    same_as = len(re.findall(r'"sameAs"', html, re.IGNORECASE))
    if same_as > 0:
        sd_score += 20
        sd_signals.append(f"sameAs links ({same_as}) — knowledge graph connectivity")

    breadcrumb = bool(re.search(r'BreadcrumbList', html))
    if breadcrumb:
        sd_score += 15
        sd_signals.append("BreadcrumbList schema")

    kg_types = set(schema_types) & {"Organization", "Person", "LocalBusiness", "Product", "Event"}
    if kg_types:
        sd_score += 15
        sd_signals.append(f"knowledge graph types: {', '.join(kg_types)}")

    dimensions["structured_data"] = {"score": round(min(100, sd_score), 1), "signals": sd_signals}

    # 3. Content depth (0.20)
    cd_score = 0.0
    cd_signals = []

    word_count = len(text.split())
    if word_count > 3000:
        cd_score += 30
        cd_signals.append(f"comprehensive ({word_count} words)")
    elif word_count > 1500:
        cd_score += 22
        cd_signals.append(f"substantial ({word_count} words)")
    elif word_count > 500:
        cd_score += 12
        cd_signals.append(f"moderate ({word_count} words)")
    elif word_count > 100:
        cd_score += 5

    headings = len(re.findall(r'<h[2-4][^>]*>', html, re.IGNORECASE))
    if headings >= 8:
        cd_score += 25
        cd_signals.append(f"{headings} sub-headings (thorough coverage)")
    elif headings >= 4:
        cd_score += 15
        cd_signals.append(f"{headings} sub-headings")
    elif headings >= 1:
        cd_score += 8

    deep_paras = sum(1 for p in paragraphs if len(p) > 200)
    if deep_paras >= 5:
        cd_score += 20
        cd_signals.append(f"{deep_paras} in-depth paragraphs")
    elif deep_paras >= 2:
        cd_score += 12

    internal_links = len(re.findall(r'<a[^>]*href="/', html, re.IGNORECASE))
    if internal_links >= 5:
        cd_score += 15
        cd_signals.append(f"{internal_links} internal links (topical cluster)")
    elif internal_links >= 2:
        cd_score += 8

    toc = bool(re.search(r'(table.of.contents|목차|id="toc")', html, re.IGNORECASE))
    if toc:
        cd_score += 10
        cd_signals.append("table of contents")

    dimensions["content_depth"] = {"score": round(min(100, cd_score), 1), "signals": cd_signals}

    # 4. Comparison/tabular data (0.10)
    ct_score = 0.0
    ct_signals = []

    tables = len(re.findall(r'<table[^>]*>', html, re.IGNORECASE))
    if tables >= 3:
        ct_score += 35
        ct_signals.append(f"{tables} data tables")
    elif tables >= 1:
        ct_score += 20
        ct_signals.append(f"{tables} data table(s)")

    comparison = len(re.findall(r'(vs\.?|versus|비교|차이점|장단점|pros|cons|advantages|disadvantages)', html, re.IGNORECASE))
    if comparison >= 3:
        ct_score += 30
        ct_signals.append(f"comparison content ({comparison} signals)")
    elif comparison >= 1:
        ct_score += 15
        ct_signals.append("comparison content")

    charts = len(re.findall(r'(chart|graph|figure|그래프|차트|<canvas|<svg)', html, re.IGNORECASE))
    if charts > 0:
        ct_score += 20
        ct_signals.append(f"visual data ({charts})")

    rankings = bool(re.search(r'(top \d|best \d|ranking|순위|\d위)', html, re.IGNORECASE))
    if rankings:
        ct_score += 15
        ct_signals.append("ranking content")

    dimensions["comparison_data"] = {"score": round(min(100, ct_score), 1), "signals": ct_signals}

    # 5. Crawler access (0.15)
    access = _check_crawler_blocked(html, "Google-Extended")
    dimensions["crawler_access"] = access

    weights = {"eeat_signals": 0.30, "structured_data": 0.25, "content_depth": 0.20, "comparison_data": 0.10, "crawler_access": 0.15}
    overall = round(sum(dimensions[k]["score"] * weights[k] for k in weights), 1)

    all_signals = []
    for dim in dimensions.values():
        all_signals.extend(dim["signals"])

    return {"score": min(100, overall), "signals": all_signals, "dimensions": dimensions}


def analyze_for_claude(html: str, url: str) -> dict:
    """Claude optimization: depth, evidence, nuance, technical quality, access."""
    text = _extract_text(html)
    paragraphs = _extract_paragraphs(html)
    dimensions = {}

    # 1. Content depth (0.25)
    cd_score = 0.0
    cd_signals = []

    substantial = [p for p in text.split('\n\n') if len(p.strip()) > 100]
    if len(substantial) > 10:
        cd_score += 30
        cd_signals.append(f"{len(substantial)} substantial paragraphs")
    elif len(substantial) > 5:
        cd_score += 20
        cd_signals.append(f"{len(substantial)} substantial paragraphs")
    elif len(substantial) > 2:
        cd_score += 10

    headings = re.findall(r'<h[2-4][^>]*>(.*?)</h[2-4]>', html, re.IGNORECASE)
    if len(headings) >= 8:
        cd_score += 25
        cd_signals.append(f"deep structure ({len(headings)} sections)")
    elif len(headings) >= 4:
        cd_score += 15
        cd_signals.append(f"{len(headings)} sections")
    elif len(headings) >= 1:
        cd_score += 8

    word_count = len(text.split())
    if word_count > 2000:
        cd_score += 20
        cd_signals.append(f"comprehensive ({word_count} words)")
    elif word_count > 1000:
        cd_score += 12
    elif word_count > 300:
        cd_score += 5

    nested_sections = len(re.findall(r'<h3[^>]*>', html, re.IGNORECASE))
    if nested_sections >= 3:
        cd_score += 15
        cd_signals.append(f"nested sections ({nested_sections} h3)")
    elif nested_sections > 0:
        cd_score += 7

    dimensions["content_depth"] = {"score": round(min(100, cd_score), 1), "signals": cd_signals}

    # 2. Data & evidence (0.25)
    de_score = 0.0
    de_signals = []

    data_claims = len(re.findall(r'\d+[\d,.]*\s*(?:%|원|달러|\$|€|명|건|억|만|배)', text))
    if data_claims >= 8:
        de_score += 30
        de_signals.append(f"{data_claims} data-backed claims")
    elif data_claims >= 3:
        de_score += 20
        de_signals.append(f"{data_claims} data-backed claims")
    elif data_claims >= 1:
        de_score += 10

    research = len(re.findall(r'(study|research|survey|paper|연구|조사|통계|논문|실험)', text, re.IGNORECASE))
    if research >= 3:
        de_score += 25
        de_signals.append(f"research references ({research})")
    elif research >= 1:
        de_score += 15
        de_signals.append("research/data reference")

    quotes = len(re.findall(r'<blockquote|"[^"]{30,}"', html))
    if quotes >= 2:
        de_score += 15
        de_signals.append(f"quotations ({quotes})")
    elif quotes > 0:
        de_score += 8

    source_links = len(re.findall(r'(source|reference|citation|출처|참고)', html, re.IGNORECASE))
    if source_links >= 2:
        de_score += 15
        de_signals.append(f"source attributions ({source_links})")
    elif source_links > 0:
        de_score += 8

    case_studies = bool(re.search(r'(case study|사례|실제 사례|use case)', html, re.IGNORECASE))
    if case_studies:
        de_score += 15
        de_signals.append("case study content")

    dimensions["data_evidence"] = {"score": round(min(100, de_score), 1), "signals": de_signals}

    # 3. Nuanced reasoning (0.20)
    nr_score = 0.0
    nr_signals = []

    nuance_words = re.findall(r'(however|although|nevertheless|반면|그러나|다만|한편|반대로|on the other hand|in contrast|nonetheless)', text, re.IGNORECASE)
    if len(nuance_words) >= 5:
        nr_score += 35
        nr_signals.append(f"strong nuanced reasoning ({len(nuance_words)} qualifiers)")
    elif len(nuance_words) >= 2:
        nr_score += 22
        nr_signals.append(f"nuanced reasoning ({len(nuance_words)} qualifiers)")
    elif len(nuance_words) >= 1:
        nr_score += 12

    pros_cons = bool(re.search(r'(장점|단점|pros|cons|advantages|disadvantages|장단점)', html, re.IGNORECASE))
    if pros_cons:
        nr_score += 20
        nr_signals.append("pros/cons analysis")

    caveats = len(re.findall(r'(but|note that|주의|유의|제한|limitation|caveat|단,)', text, re.IGNORECASE))
    if caveats >= 3:
        nr_score += 20
        nr_signals.append(f"caveats/limitations ({caveats})")
    elif caveats >= 1:
        nr_score += 10

    multiple_viewpoints = bool(re.search(r'(on one hand|some .* while|일부.*반면|찬반|양면)', text, re.IGNORECASE))
    if multiple_viewpoints:
        nr_score += 15
        nr_signals.append("multiple viewpoints")

    conditional = len(re.findall(r'(if .* then|경우에|상황에 따라|depends on|depending)', text, re.IGNORECASE))
    if conditional >= 2:
        nr_score += 10
        nr_signals.append("conditional reasoning")

    dimensions["nuanced_reasoning"] = {"score": round(min(100, nr_score), 1), "signals": nr_signals}

    # 4. Technical quality (0.15)
    tq_score = 0.0
    tq_signals = []

    code_blocks = len(re.findall(r'<(pre|code)[^>]*>', html, re.IGNORECASE))
    if code_blocks >= 3:
        tq_score += 30
        tq_signals.append(f"code examples ({code_blocks})")
    elif code_blocks > 0:
        tq_score += 18
        tq_signals.append("code example present")

    definitions = len(re.findall(r'<(dfn|abbr|dt|dd)[^>]*>', html, re.IGNORECASE))
    if definitions >= 3:
        tq_score += 20
        tq_signals.append(f"definition markup ({definitions})")
    elif definitions > 0:
        tq_score += 10
        tq_signals.append("definition/terminology markup")

    technical_terms = len(re.findall(r'<(kbd|samp|var|mark)[^>]*>', html, re.IGNORECASE))
    if technical_terms > 0:
        tq_score += 10
        tq_signals.append("technical markup elements")

    structured_lists = len(re.findall(r'<[ou]l[^>]*>', html, re.IGNORECASE))
    if structured_lists >= 3:
        tq_score += 15
        tq_signals.append(f"structured lists ({structured_lists})")
    elif structured_lists >= 1:
        tq_score += 8

    math_formulas = bool(re.search(r'(MathJax|katex|<math|\\frac|\\sum)', html, re.IGNORECASE))
    if math_formulas:
        tq_score += 15
        tq_signals.append("mathematical content")

    json_ld = bool(re.search(r'application/ld\+json', html))
    if json_ld:
        tq_score += 10
        tq_signals.append("structured data")

    dimensions["technical_quality"] = {"score": round(min(100, tq_score), 1), "signals": tq_signals}

    # 5. Crawler access (0.15)
    access = _check_crawler_blocked(html, "ClaudeBot")
    dimensions["crawler_access"] = access

    weights = {"content_depth": 0.25, "data_evidence": 0.25, "nuanced_reasoning": 0.20, "technical_quality": 0.15, "crawler_access": 0.15}
    overall = round(sum(dimensions[k]["score"] * weights[k] for k in weights), 1)

    all_signals = []
    for dim in dimensions.values():
        all_signals.extend(dim["signals"])

    return {"score": min(100, overall), "signals": all_signals, "dimensions": dimensions}


PLATFORM_ANALYZERS = {
    "chatgpt": analyze_for_chatgpt,
    "perplexity": analyze_for_perplexity,
    "gemini": analyze_for_gemini,
    "claude": analyze_for_claude,
}


# ---------------------------------------------------------------------------
# Cross-platform analysis
# ---------------------------------------------------------------------------

def compute_platform_gaps(platform_results: dict) -> list:
    """Identify optimization gaps across platforms."""
    if len(platform_results) < 2:
        return []

    scores = {p: pr["score"] for p, pr in platform_results.items()}
    avg = sum(scores.values()) / len(scores)
    gaps = []

    for platform, score in scores.items():
        delta = round(score - avg, 1)
        if delta < -10:
            gaps.append({
                "platform": platform,
                "name": platform_results[platform]["name"],
                "score": score,
                "delta": delta,
                "severity": "high" if delta < -20 else "medium",
                "message": f"{platform_results[platform]['name']} 최적화 부족 (평균 대비 {delta:+.1f}점)",
            })

    gaps.sort(key=lambda g: g["delta"])
    return gaps


def analyze_platforms_html(html: str, url: str, platforms: Optional[list] = None) -> dict:
    """Analyze HTML optimization for specific AI platforms."""
    target_platforms = platforms or list(PLATFORM_CONFIGS.keys())

    platform_results = {}
    for platform in target_platforms:
        if platform in PLATFORM_ANALYZERS:
            analysis = PLATFORM_ANALYZERS[platform](html, url)
            platform_results[platform] = {
                "name": PLATFORM_CONFIGS[platform]["name"],
                "score": analysis["score"],
                "signals": analysis["signals"],
                "dimensions": analysis.get("dimensions", {}),
            }

    scores = [pr["score"] for pr in platform_results.values()]
    avg_score = round(sum(scores) / max(len(scores), 1), 1)

    best = max(platform_results, key=lambda p: platform_results[p]["score"]) if platform_results else None
    worst = min(platform_results, key=lambda p: platform_results[p]["score"]) if platform_results else None

    gaps = compute_platform_gaps(platform_results)

    issues = []
    for gap in gaps:
        issues.append({"severity": gap["severity"], "message": gap["message"]})
    for platform, pr in platform_results.items():
        if pr["score"] < 30:
            issues.append({"severity": "high", "message": f"{pr['name']} 최적화 매우 낮음: {pr['score']}/100"})
        elif pr["score"] < 50:
            issues.append({"severity": "medium", "message": f"{pr['name']} 최적화 부족: {pr['score']}/100"})

    score_spread = max(scores) - min(scores) if scores else 0
    balance_note = None
    if score_spread > 30:
        balance_note = f"플랫폼 간 점수 편차 큼 ({score_spread:.0f}점) — 약한 플랫폼 집중 개선 필요"
        issues.append({"severity": "medium", "message": balance_note})

    return {
        "avg_score": avg_score,
        "best_platform": best,
        "worst_platform": worst,
        "score_spread": round(score_spread, 1),
        "platforms": platform_results,
        "gaps": gaps,
        "issues": issues,
    }


def analyze_platforms(url: str, platforms: Optional[list] = None) -> dict:
    """Analyze URL optimization for specific AI platforms."""
    validation = validate_url(url)
    if not validation["valid"]:
        return {"success": False, "error": validation["error"]}

    result = fetch_page(url)
    if not result["success"]:
        return {"success": False, "error": result["error"]}

    analysis = analyze_platforms_html(result["html"], url, platforms)
    analysis["success"] = True
    analysis["url"] = url
    return analysis


def main():
    parser = argparse.ArgumentParser(description="Platform-specific AI optimization — multi-dimensional scoring")
    parser.add_argument("url", help="URL to analyze")
    parser.add_argument("--platform", choices=list(PLATFORM_CONFIGS.keys()), help="Analyze specific platform")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    platforms = [args.platform] if args.platform else None
    result = analyze_platforms(args.url, platforms)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result["success"]:
            print(f"Platform Optimization Score: {result['avg_score']}/100")
            print(f"Best: {result['best_platform']} | Worst: {result['worst_platform']} | Spread: {result['score_spread']}")
            print(f"\nPlatform Breakdown:")
            for platform, pr in result["platforms"].items():
                bar = "█" * int(pr["score"] / 5) + "░" * (20 - int(pr["score"] / 5))
                print(f"  {pr['name']:15s} {bar} {pr['score']:.1f}")
                if pr.get("dimensions"):
                    for dim_name, dim_data in pr["dimensions"].items():
                        print(f"    {dim_name:25s} {dim_data['score']:5.1f}")
            if result["gaps"]:
                print(f"\nOptimization Gaps:")
                for gap in result["gaps"]:
                    print(f"  [{gap['severity'].upper()}] {gap['message']}")
            for issue in result["issues"]:
                if issue["message"] not in [g.get("message") for g in result.get("gaps", [])]:
                    print(f"  [{issue['severity'].upper()}] {issue['message']}")
        else:
            print(f"Error: {result['error']}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()

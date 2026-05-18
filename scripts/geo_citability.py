"""Passage-level AI citability analysis script for Three-O platform.

Scores how likely page content is to be cited by AI platforms across
seven dimensions with sentence structure analysis, weighted factual
density, context independence scoring, and per-platform citation
probability modeling.
"""

import argparse
import json
import re
import sys

from validate_url import validate_url
from fetch_page import fetch_page


CITABILITY_WEIGHTS = {
    "passage_clarity": 0.15,
    "factual_density": 0.15,
    "citation_pattern": 0.20,
    "self_containment": 0.15,
    "quote_readiness": 0.10,
    "structural_format": 0.10,
    "authority_signals": 0.15,
}

DEFINITION_PATTERNS = [
    r'(?:는|은|란|이란)\s+.{10,}(?:이다|입니다|합니다|됩니다)',
    r'(?:is|are|refers to|means|defined as)\s+.{10,}',
    r'^[A-Z가-힣].{5,}(?:is a|is the|refers to)',
    r'(?:의미하는|뜻하는|가리키는|말하는)\s+.{5,}',
]

COMPARISON_PATTERNS = [
    r'(?:에 비해|보다|대비|반면|차이점|vs\.?|versus)',
    r'(?:compared to|unlike|whereas|in contrast|difference between)',
    r'(?:장점|단점|pros|cons|advantages|disadvantages)',
    r'(?:상위|하위|높은|낮은|큰|작은)\s*(?:\d|[가-힣]{2,})',
]

STEP_PATTERNS = [
    r'(?:첫째|둘째|셋째|먼저|다음으로|마지막으로|최종적으로)',
    r'(?:first(?:ly)?|second(?:ly)?|third(?:ly)?|step \d|finally|next)',
    r'^\d+[\.\)]\s+',
    r'(?:방법|단계|절차|과정)\s*[:：]',
]

CAUSAL_PATTERNS = [
    r'(?:때문에|으로 인해|결과적으로|따라서|그러므로|그래서)',
    r'(?:because|therefore|as a result|consequently|due to|leads to|thus)',
    r'(?:원인|결과|영향|효과)\s*[:：은는이가]',
]

STAT_PATTERNS = [
    r'\d+[\d,.]*\s*(?:%|퍼센트|percent)',
    r'(?:₩|원|달러|\$|€)\s*[\d,.]+',
    r'\d+[\d,.]*\s*(?:km|m|kg|g|GB|MB|TB|명|개|건|억|만|조|배)',
    r'(?:19|20)\d{2}년',
    r'\d+(?:\.\d+)?\s*(?:배|times|x)\s',
]

CONTEXT_DEPENDENT_KO = [
    "이것", "그것", "저것", "이런", "그런", "저런",
    "위의", "아래의", "앞의", "뒤의", "해당", "그러한",
    "이를", "그를", "이에", "그에",
]

CONTEXT_DEPENDENT_EN = [
    "this", "that", "these", "those", "above", "below",
    "the former", "the latter", "as mentioned", "said",
    "the following", "the previous", "the above",
]

PLATFORM_CRITERIA = {
    "chatgpt": {
        "name": "ChatGPT",
        "ideal_length": (80, 300),
        "prefers": ["definition", "step", "concise"],
        "weights": {"definition": 1.4, "comparison": 1.1, "step": 1.3, "causal": 1.0, "data": 1.0},
        "freshness_bonus": True,
        "faq_bonus": True,
    },
    "perplexity": {
        "name": "Perplexity",
        "ideal_length": (100, 500),
        "prefers": ["data", "source", "recency"],
        "weights": {"definition": 1.0, "comparison": 1.1, "step": 1.0, "causal": 1.0, "data": 1.5},
        "source_bonus": True,
        "numbers_bonus": True,
    },
    "gemini": {
        "name": "Gemini",
        "ideal_length": (80, 400),
        "prefers": ["definition", "comparison", "eeat"],
        "weights": {"definition": 1.3, "comparison": 1.3, "step": 1.0, "causal": 1.1, "data": 1.1},
        "table_bonus": True,
        "eeat_bonus": True,
    },
    "claude": {
        "name": "Claude",
        "ideal_length": (100, 600),
        "prefers": ["depth", "data", "nuance", "causal"],
        "weights": {"definition": 1.1, "comparison": 1.1, "step": 1.1, "causal": 1.3, "data": 1.3},
        "depth_bonus": True,
        "nuance_bonus": True,
    },
}


def extract_text_content(html: str) -> str:
    """Strip HTML tags and extract text."""
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_passages(html: str) -> list:
    """Extract meaningful text passages from HTML with broader element coverage."""
    selectors = [
        (r'<p[^>]*>(.*?)</p>', "paragraph"),
        (r'<li[^>]*>(.*?)</li>', "list_item"),
        (r'<blockquote[^>]*>(.*?)</blockquote>', "blockquote"),
        (r'<figcaption[^>]*>(.*?)</figcaption>', "caption"),
        (r'<dd[^>]*>(.*?)</dd>', "definition"),
        (r'<td[^>]*>(.*?)</td>', "table_cell"),
    ]

    passages = []
    seen = set()

    for pattern, source in selectors:
        matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
        for match in matches:
            clean = re.sub(r'<[^>]+>', '', match).strip()
            clean = re.sub(r'\s+', ' ', clean)
            if len(clean) > 40 and clean[:40] not in seen:
                seen.add(clean[:40])
                passages.append({"text": clean, "source": source})

    heading_para = re.findall(
        r'<h[2-4][^>]*>(.*?)</h[2-4]>\s*<p[^>]*>(.*?)</p>',
        html, re.DOTALL | re.IGNORECASE
    )
    for heading, para in heading_para:
        h_clean = re.sub(r'<[^>]+>', '', heading).strip()
        p_clean = re.sub(r'<[^>]+>', '', para).strip()
        combined = f"{h_clean}: {p_clean}"
        if len(combined) > 50 and combined[:40] not in seen:
            seen.add(combined[:40])
            passages.append({"text": combined, "source": "heading_paragraph"})

    return passages


def analyze_sentence_structure(passage: str) -> dict:
    """Analyze sentence-level quality for citability."""
    sentences = re.split(r'[.!?。]\s*', passage)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 5]

    if not sentences:
        return {"quality": 0, "count": 0, "avg_length": 0, "active_ratio": 0, "clear_subject_ratio": 0}

    lengths = [len(s.split()) for s in sentences]
    avg_len = sum(lengths) / len(lengths)

    passive_ko = sum(1 for s in sentences if re.search(r'(?:되다|되었|되는|된다|받다|받는)', s))
    passive_en = sum(1 for s in sentences if re.search(r'(?:is|are|was|were|been)\s+\w+ed\b', s, re.IGNORECASE))
    passive_count = passive_ko + passive_en
    active_ratio = round(1 - (passive_count / len(sentences)), 2)

    clear_subject = sum(1 for s in sentences if re.match(r'^[A-Z가-힣\d]', s))
    clear_subject_ratio = round(clear_subject / len(sentences), 2)

    quality = 30.0
    if 8 <= avg_len <= 25:
        quality += 25
    elif 5 <= avg_len <= 35:
        quality += 15

    quality += active_ratio * 20
    quality += clear_subject_ratio * 15

    if 2 <= len(sentences) <= 5:
        quality += 10

    return {
        "quality": round(min(100.0, quality), 1),
        "count": len(sentences),
        "avg_length": round(avg_len, 1),
        "active_ratio": active_ratio,
        "clear_subject_ratio": clear_subject_ratio,
    }


def score_passage_clarity(passage: str) -> dict:
    """Score passage clarity with sentence structure analysis."""
    structure = analyze_sentence_structure(passage)
    score = structure["quality"]

    if structure["count"] == 0:
        return {"score": 15.0, "structure": structure}

    pronouns_ko = len(re.findall(r'(?:이것|그것|저것|이를|그를)', passage))
    pronouns_en = len(re.findall(r'\b(?:it|they|them|this|that)\b', passage, re.IGNORECASE))
    pronoun_density = (pronouns_ko + pronouns_en) / max(len(passage.split()), 1)
    if pronoun_density < 0.05:
        score += 10

    return {"score": round(min(100.0, score), 1), "structure": structure}


def score_factual_density(passage: str) -> dict:
    """Score factual density with type-weighted fact counting."""
    hard_stats = 0
    for pattern in STAT_PATTERNS:
        hard_stats += len(re.findall(pattern, passage))

    proper_nouns = len(re.findall(r'\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)*\b', passage))

    korean_entities = len(re.findall(
        r'(?:서울|부산|대구|인천|네이버|카카오|삼성|LG|SK|현대|구글|마이크로소프트|애플)',
        passage
    ))

    dates = len(re.findall(r'(?:19|20)\d{2}[-./년]\s*\d{0,2}', passage))

    sources = len(re.findall(
        r'(?:에 따르면|에 의하면|발표|보고서|연구|조사|according to|study|report|survey)',
        passage, re.IGNORECASE
    ))

    score = 15.0
    score += min(30, hard_stats * 8)
    score += min(15, proper_nouns * 4)
    score += min(10, korean_entities * 5)
    score += min(10, dates * 7)
    score += min(15, sources * 10)

    words = len(passage.split())
    fact_count = hard_stats + proper_nouns + korean_entities + dates
    density = fact_count / max(words, 1)

    return {
        "score": round(min(100.0, score), 1),
        "hard_stats": hard_stats,
        "proper_nouns": proper_nouns,
        "korean_entities": korean_entities,
        "dates": dates,
        "sources": sources,
        "fact_density": round(density, 3),
    }


def score_citation_pattern(passage: str) -> dict:
    """Score citation pattern match with confidence levels."""
    score = 15.0
    patterns_found = []

    for pattern in DEFINITION_PATTERNS:
        if re.search(pattern, passage, re.IGNORECASE):
            score += 22
            patterns_found.append("definition")
            break

    for pattern in COMPARISON_PATTERNS:
        if re.search(pattern, passage, re.IGNORECASE):
            score += 18
            patterns_found.append("comparison")
            break

    for pattern in STEP_PATTERNS:
        if re.search(pattern, passage, re.IGNORECASE | re.MULTILINE):
            score += 13
            patterns_found.append("step")
            break

    for pattern in CAUSAL_PATTERNS:
        if re.search(pattern, passage, re.IGNORECASE):
            score += 13
            patterns_found.append("causal")
            break

    stat_count = 0
    for pattern in STAT_PATTERNS:
        stat_count += len(re.findall(pattern, passage))
    if stat_count >= 3:
        score += 15
        patterns_found.append("data_rich")
    elif stat_count >= 1:
        score += 8
        patterns_found.append("data")

    if len(patterns_found) >= 3:
        score += 10

    return {"score": round(min(100.0, score), 1), "patterns": patterns_found, "pattern_count": len(patterns_found)}


def score_self_containment(passage: str) -> dict:
    """Score context independence with anaphora detection."""
    score = 55.0
    issues = []

    dep_count_ko = sum(1 for w in CONTEXT_DEPENDENT_KO if w in passage)
    dep_count_en = sum(1 for w in CONTEXT_DEPENDENT_EN if w.lower() in passage.lower())
    total_dep = dep_count_ko + dep_count_en

    if total_dep == 0:
        score += 15
    elif total_dep <= 1:
        score += 5
    else:
        score -= total_dep * 8
        issues.append(f"context_dependent_words: {total_dep}")

    sentences = re.split(r'[.!?。]\s*', passage)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 5]
    if sentences:
        first = sentences[0]
        if re.match(r'^[A-Z가-힣\d]', first) and len(first.split()) >= 3:
            score += 12
        elif re.match(r'^(?:이|그|저|the|this|that)\s', first, re.IGNORECASE):
            score -= 8
            issues.append("weak_opener")

    plen = len(passage)
    if 80 <= plen <= 400:
        score += 12
    elif 50 <= plen <= 600:
        score += 6
    elif plen < 50:
        score -= 10
        issues.append("too_short")
    elif plen > 800:
        score -= 5
        issues.append("too_long")

    question_start = bool(re.match(r'^(?:무엇|어떻게|왜|언제|누가|what|how|why|when|who)\b', passage, re.IGNORECASE))
    if question_start:
        score += 8

    return {
        "score": round(max(0.0, min(100.0, score)), 1),
        "context_dependencies": total_dep,
        "issues": issues,
    }


def score_quote_readiness(passage: str, pattern_result: dict) -> dict:
    """Score how likely the passage is to be directly quoted by AI."""
    score = 20.0
    signals = {}

    plen = len(passage)
    if 80 <= plen <= 250:
        score += 20
        signals["ideal_length"] = True
    elif 60 <= plen <= 400:
        score += 10
        signals["ideal_length"] = False
    else:
        signals["ideal_length"] = False

    sentences = re.split(r'[.!?。]\s*', passage)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 5]
    if 1 <= len(sentences) <= 3:
        score += 15
        signals["concise"] = True
    else:
        signals["concise"] = False

    if "definition" in pattern_result.get("patterns", []):
        score += 15
        signals["has_definition"] = True

    stat_count = 0
    for p in STAT_PATTERNS:
        stat_count += len(re.findall(p, passage))
    if stat_count >= 2:
        score += 10
        signals["data_backed"] = True

    has_filler = bool(re.search(
        r'(?:다양한|최고의|최선을|노력하|very|best|great|amazing|incredible)',
        passage, re.IGNORECASE
    ))
    signals["has_filler"] = has_filler
    if has_filler:
        score -= 10

    dep_count = sum(1 for w in CONTEXT_DEPENDENT_KO + CONTEXT_DEPENDENT_EN if w.lower() in passage.lower())
    if dep_count == 0:
        score += 10
        signals["self_contained"] = True
    else:
        signals["self_contained"] = False

    return {"score": round(max(0.0, min(100.0, score)), 1), "signals": signals}


def score_structural_format(html: str) -> dict:
    """Score page structural formatting for AI extraction."""
    score = 20.0
    details = {}

    headings = len(re.findall(r'<h[2-4][^>]*>', html, re.IGNORECASE))
    details["headings"] = headings
    score += min(15, headings * 3)

    lists = len(re.findall(r'<[ou]l[^>]*>', html, re.IGNORECASE))
    details["lists"] = lists
    score += min(12, lists * 4)

    tables = len(re.findall(r'<table[^>]*>', html, re.IGNORECASE))
    details["tables"] = tables
    score += min(12, tables * 6)

    definitions = len(re.findall(r'<(?:dt|dfn|abbr)[^>]*>', html, re.IGNORECASE))
    details["definitions"] = definitions
    score += min(8, definitions * 4)

    blockquotes = len(re.findall(r'<blockquote[^>]*>', html, re.IGNORECASE))
    details["blockquotes"] = blockquotes
    score += min(8, blockquotes * 4)

    paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', html, re.DOTALL)
    short_p = sum(1 for p in paragraphs if 50 < len(re.sub(r'<[^>]+>', '', p)) < 300)
    details["short_paragraphs_ratio"] = round(short_p / max(len(paragraphs), 1), 2)
    if len(paragraphs) > 0 and short_p / len(paragraphs) > 0.5:
        score += 10

    has_semantic = bool(re.search(r'<(?:article|section|main|aside|figure)[^>]*>', html, re.IGNORECASE))
    details["semantic_html"] = has_semantic
    if has_semantic:
        score += 8

    has_schema = 'application/ld+json' in html
    details["structured_data"] = has_schema
    if has_schema:
        score += 7

    return {"score": round(min(100.0, score), 1), "details": details}


def score_authority_signals(html: str) -> dict:
    """Score authority indicators for citation worthiness."""
    score = 15.0
    details = {}

    checks = [
        ("author", r'(?:author|byline|written by|작성자|저자)', 12),
        ("date", r'(?:published|datePublished|발행일|수정일|작성일|\d{4}[-./]\d{1,2}[-./]\d{1,2})', 10),
        ("sources", r'(?:source|reference|citation|출처|참고|참조)', 12),
        ("research", r'(?:study|research|survey|data shows|연구|조사|분석)', 12),
        ("expert", r'(?:expert|professor|Ph\.?D|Dr\.|박사|전문가|교수)', 12),
        ("institution", r'(?:university|institute|government|대학|연구소|정부|기관)', 10),
        ("schema", r'application/ld\+json', 8),
        ("external_links", r'<a[^>]+href="https?://(?!(?:www\.)?(?:facebook|twitter|instagram))', 9),
    ]

    for key, pattern, points in checks:
        found = bool(re.search(pattern, html, re.IGNORECASE))
        details[key] = found
        if found:
            score += points

    return {"score": round(min(100.0, score), 1), "details": details}


def score_platform_citability(passage: str, pattern_result: dict, passage_len: int) -> dict:
    """Score per-platform citation probability with detailed criteria."""
    base_score = pattern_result["score"]
    patterns = pattern_result.get("patterns", [])

    platform_scores = {}

    for platform, criteria in PLATFORM_CRITERIA.items():
        multiplier = 1.0

        for pat in patterns:
            pat_key = pat.replace("data_rich", "data")
            if pat_key in criteria["weights"]:
                multiplier = max(multiplier, criteria["weights"][pat_key])

        ideal_min, ideal_max = criteria["ideal_length"]
        if ideal_min <= passage_len <= ideal_max:
            multiplier *= 1.1

        if criteria.get("source_bonus") and "data" in patterns:
            multiplier *= 1.1
        if criteria.get("depth_bonus") and passage_len > 200:
            multiplier *= 1.05
        if criteria.get("nuance_bonus") and "causal" in patterns:
            multiplier *= 1.1

        plat_score = round(min(100.0, base_score * multiplier), 1)
        platform_scores[platform] = plat_score

    return platform_scores


PLATFORM_CITATION_PREFS = {
    k: v["weights"] for k, v in PLATFORM_CRITERIA.items()
}


def analyze_citability_html(html: str, url: str = "") -> dict:
    """Run full citability analysis on raw HTML."""
    raw_passages = extract_passages(html)
    passages = [p["text"] for p in raw_passages]

    passage_analyses = []
    platform_totals = {p: [] for p in PLATFORM_CRITERIA}

    for pdata in raw_passages[:25]:
        text = pdata["text"]
        clarity = score_passage_clarity(text)
        factual = score_factual_density(text)
        pattern_result = score_citation_pattern(text)
        containment = score_self_containment(text)
        quote = score_quote_readiness(text, pattern_result)
        platform_cit = score_platform_citability(text, pattern_result, len(text))

        p_score = round(
            clarity["score"] * 0.20 +
            factual["score"] * 0.20 +
            pattern_result["score"] * 0.25 +
            containment["score"] * 0.20 +
            quote["score"] * 0.15,
            1
        )

        passage_analyses.append({
            "text": text[:150] + ("..." if len(text) > 150 else ""),
            "source": pdata["source"],
            "score": p_score,
            "clarity": clarity["score"],
            "factual_density": factual["score"],
            "citation_pattern": pattern_result["score"],
            "self_containment": containment["score"],
            "quote_readiness": quote["score"],
            "patterns_found": pattern_result["patterns"],
            "platform_scores": platform_cit,
        })

        for plat, plat_score in platform_cit.items():
            platform_totals[plat].append(plat_score)

    passage_analyses.sort(key=lambda x: x["score"], reverse=True)

    sample_texts = passages[:15]
    clarity_scores = [score_passage_clarity(p)["score"] for p in sample_texts] if sample_texts else [0]
    factual_scores = [score_factual_density(p)["score"] for p in sample_texts] if sample_texts else [0]
    pattern_scores = [score_citation_pattern(p)["score"] for p in sample_texts] if sample_texts else [0]
    containment_scores = [score_self_containment(p)["score"] for p in sample_texts] if sample_texts else [0]
    quote_scores = [score_quote_readiness(p, score_citation_pattern(p))["score"] for p in sample_texts] if sample_texts else [0]

    struct = score_structural_format(html)
    authority = score_authority_signals(html)

    dim_scores = {
        "passage_clarity": round(sum(clarity_scores) / len(clarity_scores), 1),
        "factual_density": round(sum(factual_scores) / len(factual_scores), 1),
        "citation_pattern": round(sum(pattern_scores) / len(pattern_scores), 1),
        "self_containment": round(sum(containment_scores) / len(containment_scores), 1),
        "quote_readiness": round(sum(quote_scores) / len(quote_scores), 1),
        "structural_format": struct["score"],
        "authority_signals": authority["score"],
    }

    overall = round(sum(dim_scores[k] * CITABILITY_WEIGHTS[k] for k in CITABILITY_WEIGHTS), 1)

    platform_avg = {}
    for plat, scores in platform_totals.items():
        platform_avg[plat] = round(sum(scores) / max(len(scores), 1), 1) if scores else 0.0

    issues = []
    if dim_scores["passage_clarity"] < 45:
        issues.append({"severity": "high", "dimension": "passage_clarity",
                        "message": "패시지 명확도 낮음 — 문장 구조 개선, 대명사 줄이기"})
    if dim_scores["factual_density"] < 35:
        issues.append({"severity": "high", "dimension": "factual_density",
                        "message": "팩트 밀도 낮음 — 구체적 수치, 고유명사, 날짜 추가"})
    if dim_scores["citation_pattern"] < 40:
        issues.append({"severity": "medium", "dimension": "citation_pattern",
                        "message": "인용 패턴 약함 — 정의문, 비교문, 인과 구조 추가"})
    if dim_scores["self_containment"] < 45:
        issues.append({"severity": "medium", "dimension": "self_containment",
                        "message": "맥락 의존도 높음 — '이것', '그것' 등 대명사 대체"})
    if dim_scores["quote_readiness"] < 35:
        issues.append({"severity": "medium", "dimension": "quote_readiness",
                        "message": "직접 인용 가능성 낮음 — 80-300자 자기완결 문장 작성"})
    if dim_scores["structural_format"] < 40:
        issues.append({"severity": "medium", "dimension": "structural_format",
                        "message": "구조 부족 — 소제목, 목록, 표 추가"})
    if dim_scores["authority_signals"] < 35:
        issues.append({"severity": "medium", "dimension": "authority_signals",
                        "message": "권위 신호 약함 — 작성자, 출처, 날짜, 전문가 표기"})
    if len(raw_passages) < 5:
        issues.append({"severity": "high", "dimension": "content_volume",
                        "message": f"인용 가능 패시지 {len(raw_passages)}개 — 최소 5개 이상 권장"})

    issues.sort(key=lambda x: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(x["severity"], 4))

    weakest = min(CITABILITY_WEIGHTS, key=lambda k: dim_scores[k])

    return {
        "success": True,
        "url": url,
        "score": overall,
        "dimensions": dim_scores,
        "weakest_dimension": weakest,
        "platform_citability": platform_avg,
        "total_passages": len(raw_passages),
        "top_passages": passage_analyses[:5],
        "structural": struct,
        "authority": authority,
        "issues": issues,
    }


def analyze_citability(url: str, depth: int = 1) -> dict:
    """Full citability analysis for a URL."""
    validation = validate_url(url)
    if not validation["valid"]:
        return {"success": False, "error": validation["error"]}

    result = fetch_page(url)
    if not result["success"]:
        return {"success": False, "error": result["error"]}

    return analyze_citability_html(result["html"], url)


def main():
    parser = argparse.ArgumentParser(description="AI citability analysis")
    parser.add_argument("url", help="URL to analyze")
    parser.add_argument("--depth", type=int, default=1, choices=[1, 2, 3], help="Analysis depth")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    result = analyze_citability(args.url, args.depth)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result["success"]:
            print(f"Citability Score: {result['score']}/100")
            print(f"Passages: {result['total_passages']} | Weakest: {result['weakest_dimension']}")
            print("\nDimensions:")
            for dim, s in result["dimensions"].items():
                print(f"  {dim.replace('_', ' ').title():25s} {s:5.1f}/100")
            print("\nPlatform Citability:")
            for plat, s in result["platform_citability"].items():
                name = PLATFORM_CRITERIA[plat]["name"]
                print(f"  {name:15s} {s:5.1f}/100")
            if result["top_passages"]:
                print("\nTop Passages:")
                for i, p in enumerate(result["top_passages"][:3], 1):
                    print(f"  {i}. [{p['score']:.0f}] {p['text'][:80]}...")
            for issue in result.get("issues", []):
                print(f"  [{issue['severity'].upper()}] {issue['message']}")
        else:
            print(f"Error: {result['error']}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()

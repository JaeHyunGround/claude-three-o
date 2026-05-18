"""Content quality and E-E-A-T analysis script for Three-O platform.

Scores Experience, Expertise, Authoritativeness, and Trust as four
independent axes with quality-based grading, not binary checks.
"""

import argparse
import json
import re
import sys

from validate_url import validate_url
from fetch_page import fetch_page


EEAT_WEIGHTS = {
    "experience": 0.20,
    "expertise": 0.30,
    "authoritativeness": 0.25,
    "trust": 0.25,
}

EXPERIENCE_SIGNALS = {
    "first_person": [
        r'(?:제가|저는|저희|우리가|우리는|직접|경험)',
        r'(?:I |we |my |our |I\'ve |we\'ve )',
    ],
    "case_study": [
        r'(?:사례|후기|리뷰|체험|실제\s*사용|실사용)',
        r'(?:case study|review|testimonial|hands-on|real-world)',
    ],
    "original_media": [
        r'<(?:img|video|audio)[^>]*(?:src|poster)=["\'][^"\']*(?:upload|original|content|media)',
    ],
    "process_narrative": [
        r'(?:과정|단계별|시행착오|시도|결과적으로)',
        r'(?:process|step-by-step|trial and error|as a result|in practice)',
    ],
    "temporal_experience": [
        r'(?:\d+\s*(?:년|개월|주|일)\s*(?:간|동안|째|넘게))',
        r'(?:for \d+ (?:years?|months?|weeks?|days?))',
        r'(?:since \d{4}|from \d{4})',
    ],
}

EXPERTISE_SIGNALS = {
    "credentials": [
        r'(?:박사|석사|교수|전문가|자격증|면허|Ph\.?D|M\.?D|CPA|변호사|의사|약사)',
        r'(?:certified|licensed|accredited|qualified|specialist|expert)',
    ],
    "technical_depth": [
        r'(?:알고리즘|프레임워크|아키텍처|프로토콜|API|SDK|메서드)',
        r'(?:algorithm|framework|architecture|protocol|methodology|implementation)',
    ],
    "author_bio": [
        r'(?:작성자|저자|글쓴이|프로필|소개)',
        r'(?:author|written by|byline|bio|about the author)',
    ],
    "author_schema": [
        r'"@type"\s*:\s*"Person"',
        r'"author"\s*:\s*\{',
    ],
    "specialized_terms": [
        r'(?:최적화|인덱싱|크롤링|렌더링|시맨틱|구조화)',
        r'(?:optimization|indexing|crawling|rendering|semantic|structured)',
    ],
    "data_analysis": [
        r'(?:분석\s*결과|데이터에\s*따르면|통계|조사\s*결과)',
        r'(?:analysis shows|data indicates|statistics|survey results|according to)',
    ],
}

AUTHORITY_SIGNALS = {
    "external_citations": [
        r'<a[^>]+href="https?://(?!(?:www\.)?(?:facebook|twitter|instagram|youtube|linkedin))[^"]*"[^>]*>',
    ],
    "source_attribution": [
        r'(?:출처|참고|인용|근거|참조)',
        r'(?:source|reference|citation|according to|cited from)',
    ],
    "awards_certs": [
        r'(?:수상|인증|ISO|HACCP|GMP|KS|특허|등록)',
        r'(?:award|certified|patent|registered|recognized|accredited)',
    ],
    "institutional_links": [
        r'href="https?://[^"]*\.(?:go\.kr|gov|edu|ac\.kr|or\.kr|org)',
    ],
    "media_mentions": [
        r'(?:보도|기사|언론|미디어|뉴스|인터뷰)',
        r'(?:featured in|as seen on|press|media|news|interview)',
    ],
    "same_as_links": [
        r'"sameAs"\s*:',
    ],
    "industry_affiliation": [
        r'(?:협회|학회|연합|위원회|단체|회원)',
        r'(?:association|society|member of|affiliated with|committee)',
    ],
}

TRUST_SIGNALS = {
    "https": [],
    "privacy_policy": [
        r'(?:개인정보|프라이버시|정보보호)',
        r'(?:privacy policy|privacy|data protection)',
        r'href="[^"]*(?:privacy|개인정보)[^"]*"',
    ],
    "terms_of_service": [
        r'(?:이용약관|서비스약관|이용규정)',
        r'(?:terms of service|terms and conditions|terms of use)',
        r'href="[^"]*(?:terms|약관)[^"]*"',
    ],
    "contact_info": [
        r'(?:연락처|문의|고객센터|상담)',
        r'(?:contact us|get in touch|customer service|support)',
        r'href="[^"]*(?:contact|문의)[^"]*"',
    ],
    "physical_address": [
        r'(?:서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주)',
        r'(?:주소|address)',
    ],
    "business_registration": [
        r'(?:사업자\s*등록|사업자\s*번호|대표자|법인)',
        r'(?:business registration|company number|registered)',
    ],
    "secure_forms": [
        r'<form[^>]*(?:action="https|method="post")',
    ],
    "clear_attribution": [
        r'(?:발행일|수정일|작성일|업데이트)',
        r'(?:published|updated|modified|last reviewed)',
        r'(?:datePublished|dateModified)',
    ],
}


def extract_text_content(html: str) -> str:
    """Strip HTML tags and extract text content."""
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def count_headings(html: str) -> dict:
    """Count heading tags by level."""
    counts = {}
    for level in range(1, 7):
        pattern = f"<h{level}[^>]*>"
        counts[f"h{level}"] = len(re.findall(pattern, html, re.IGNORECASE))
    return counts


def _count_content_units(text: str, is_korean: bool) -> int:
    """Count content units: characters for Korean, words for English.

    Korean text often lacks spaces between meaningful units, so word-based
    counting (text.split()) severely undercounts. Character count (excluding
    whitespace) is the standard metric for Korean content length."""
    if is_korean:
        return len(re.sub(r'\s', '', text))
    return len(text.split())


def analyze_korean_content(text: str) -> dict:
    """Analyze Korean-specific content metrics."""
    korean_chars = len(re.findall(r"[가-힯]", text))
    non_ws_chars = len(re.sub(r'\s', '', text))
    korean_ratio = korean_chars / max(non_ws_chars, 1)
    return {
        "korean_chars": korean_chars,
        "total_chars": non_ws_chars,
        "korean_ratio": round(korean_ratio, 3),
        "is_korean_content": korean_ratio > 0.3,
    }


def _count_signal_matches(html: str, patterns: list) -> int:
    """Count total regex matches across patterns."""
    total = 0
    for pattern in patterns:
        total += len(re.findall(pattern, html, re.IGNORECASE))
    return total


def score_experience(html: str) -> dict:
    """Score Experience axis — first-hand knowledge, case studies, original content."""
    score = 15.0
    details = {}

    fp = _count_signal_matches(html, EXPERIENCE_SIGNALS["first_person"])
    details["first_person"] = min(fp, 10)
    score += min(20, fp * 5)

    cs = _count_signal_matches(html, EXPERIENCE_SIGNALS["case_study"])
    details["case_study"] = min(cs, 5)
    score += min(20, cs * 8)

    om = _count_signal_matches(html, EXPERIENCE_SIGNALS["original_media"])
    details["original_media"] = min(om, 5)
    score += min(15, om * 5)

    pn = _count_signal_matches(html, EXPERIENCE_SIGNALS["process_narrative"])
    details["process_narrative"] = min(pn, 5)
    score += min(15, pn * 5)

    te = _count_signal_matches(html, EXPERIENCE_SIGNALS["temporal_experience"])
    details["temporal_experience"] = min(te, 3)
    score += min(15, te * 8)

    return {"score": round(min(100.0, score), 1), "details": details}


def score_expertise(html: str) -> dict:
    """Score Expertise axis — credentials, technical depth, author profile."""
    score = 10.0
    details = {}

    cr = _count_signal_matches(html, EXPERTISE_SIGNALS["credentials"])
    details["credentials"] = min(cr, 5)
    score += min(25, cr * 10)

    td = _count_signal_matches(html, EXPERTISE_SIGNALS["technical_depth"])
    details["technical_depth"] = min(td, 10)
    score += min(15, td * 3)

    ab = _count_signal_matches(html, EXPERTISE_SIGNALS["author_bio"])
    details["author_bio"] = min(ab, 3)
    score += min(15, ab * 8)

    as_ = _count_signal_matches(html, EXPERTISE_SIGNALS["author_schema"])
    details["author_schema"] = min(as_, 2)
    score += min(15, as_ * 10)

    st = _count_signal_matches(html, EXPERTISE_SIGNALS["specialized_terms"])
    details["specialized_terms"] = min(st, 10)
    score += min(15, st * 3)

    da = _count_signal_matches(html, EXPERTISE_SIGNALS["data_analysis"])
    details["data_analysis"] = min(da, 5)
    score += min(15, da * 5)

    return {"score": round(min(100.0, score), 1), "details": details}


def score_authoritativeness(html: str) -> dict:
    """Score Authoritativeness axis — citations, awards, institutional links."""
    score = 10.0
    details = {}

    ec = _count_signal_matches(html, AUTHORITY_SIGNALS["external_citations"])
    details["external_citations"] = min(ec, 20)
    score += min(15, ec * 3)

    sa = _count_signal_matches(html, AUTHORITY_SIGNALS["source_attribution"])
    details["source_attribution"] = min(sa, 10)
    score += min(15, sa * 4)

    ac = _count_signal_matches(html, AUTHORITY_SIGNALS["awards_certs"])
    details["awards_certs"] = min(ac, 5)
    score += min(15, ac * 6)

    il = _count_signal_matches(html, AUTHORITY_SIGNALS["institutional_links"])
    details["institutional_links"] = min(il, 5)
    score += min(15, il * 6)

    mm = _count_signal_matches(html, AUTHORITY_SIGNALS["media_mentions"])
    details["media_mentions"] = min(mm, 5)
    score += min(15, mm * 5)

    sl = _count_signal_matches(html, AUTHORITY_SIGNALS["same_as_links"])
    details["same_as_links"] = min(sl, 1)
    score += 10 if sl > 0 else 0

    ia = _count_signal_matches(html, AUTHORITY_SIGNALS["industry_affiliation"])
    details["industry_affiliation"] = min(ia, 3)
    score += min(15, ia * 6)

    return {"score": round(min(100.0, score), 1), "details": details}


def score_trust(html: str, url: str = "") -> dict:
    """Score Trust axis — security, policies, contact, attribution."""
    score = 10.0
    details = {}

    is_https = url.startswith("https://") if url else "https" in html[:200].lower()
    details["https"] = is_https
    score += 15 if is_https else 0

    pp = _count_signal_matches(html, TRUST_SIGNALS["privacy_policy"])
    details["privacy_policy"] = pp > 0
    score += 12 if pp > 0 else 0

    ts = _count_signal_matches(html, TRUST_SIGNALS["terms_of_service"])
    details["terms_of_service"] = ts > 0
    score += 10 if ts > 0 else 0

    ci = _count_signal_matches(html, TRUST_SIGNALS["contact_info"])
    details["contact_info"] = ci > 0
    score += 12 if ci > 0 else 0

    pa = _count_signal_matches(html, TRUST_SIGNALS["physical_address"])
    details["physical_address"] = pa > 0
    score += 10 if pa > 0 else 0

    br = _count_signal_matches(html, TRUST_SIGNALS["business_registration"])
    details["business_registration"] = br > 0
    score += 12 if br > 0 else 0

    sf = _count_signal_matches(html, TRUST_SIGNALS["secure_forms"])
    details["secure_forms"] = sf > 0
    score += 8 if sf > 0 else 0

    ca = _count_signal_matches(html, TRUST_SIGNALS["clear_attribution"])
    details["clear_attribution"] = ca > 0
    score += 11 if ca > 0 else 0

    return {"score": round(min(100.0, score), 1), "details": details}


def compute_eeat_score(experience: dict, expertise: dict,
                       authoritativeness: dict, trust: dict) -> dict:
    """Compute weighted E-E-A-T score from four axes."""
    axes = {
        "experience": experience["score"],
        "expertise": expertise["score"],
        "authoritativeness": authoritativeness["score"],
        "trust": trust["score"],
    }

    overall = round(sum(axes[k] * EEAT_WEIGHTS[k] for k in EEAT_WEIGHTS), 1)

    weakest = min(axes, key=axes.get)
    strongest = max(axes, key=axes.get)

    issues = []
    for axis, val in axes.items():
        if val < 25:
            issues.append({
                "severity": "critical",
                "axis": axis,
                "message": f"{axis.title()} 매우 약함 ({val:.0f}/100)",
            })
        elif val < 40:
            issues.append({
                "severity": "high",
                "axis": axis,
                "message": f"{axis.title()} 보강 필요 ({val:.0f}/100)",
            })

    return {
        "score": overall,
        "axes": axes,
        "weakest": weakest,
        "strongest": strongest,
        "issues": issues,
    }


def analyze_content_depth(text: str) -> dict:
    """Analyze content depth and quality metrics."""
    korean_chars = len(re.findall(r"[가-힯]", text))
    non_ws = len(re.sub(r'\s', '', text))
    is_korean = (korean_chars / max(non_ws, 1)) > 0.3
    word_count = _count_content_units(text, is_korean)
    sentences = re.split(r'[.!?。]', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 5]
    sentence_count = len(sentences)

    avg_sentence_len = 0
    if sentences:
        avg_sentence_len = round(
            sum(_count_content_units(s, is_korean) for s in sentences) / len(sentences), 1
        )

    numbers = len(re.findall(r'\d+[\d,.%]*', text))
    proper_nouns = len(re.findall(r'\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)*\b', text))

    depth_score = 30.0
    if word_count >= 1500:
        depth_score += 25
    elif word_count >= 800:
        depth_score += 20
    elif word_count >= 300:
        depth_score += 10

    if 10 <= avg_sentence_len <= 25:
        depth_score += 15
    elif avg_sentence_len > 0:
        depth_score += 5

    depth_score += min(15, numbers * 2)
    depth_score += min(15, proper_nouns)

    return {
        "word_count": word_count,
        "sentence_count": sentence_count,
        "avg_sentence_length": avg_sentence_len,
        "numbers_count": numbers,
        "proper_nouns": proper_nouns,
        "depth_score": round(min(100.0, depth_score), 1),
    }


COMMODITY_TITLE_PATTERNS = [
    r'(?:\d+\s*(?:가지|개|tips|ways|things|reasons|steps))',
    r'(?:꿀팁|필수|추천|방법|알아보기|총정리|모음)',
    r'(?:best|top|ultimate|complete|definitive)\s+(?:guide|list|tips)',
    r'(?:everything you need to know|beginner.s guide|101)',
]

COMMODITY_BODY_PATTERNS = [
    r'(?:많은\s*사람들이|누구나\s*알다시피|잘\s*알려진)',
    r'(?:as (?:we all|everyone) knows|it.s (?:well known|no secret))',
    r'(?:이\s*글에서는?\s*.{0,20}(?:알아보|살펴보|소개))',
    r'(?:in this (?:article|post|guide),?\s*(?:we will|we.ll|I.ll)\s*(?:explore|discuss|cover|look at))',
]


def detect_commodity_content(html: str, text: str) -> dict:
    """Detect commodity (generic, non-unique) content signals per Google's AI search guide."""
    title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
    title = title_match.group(1).strip() if title_match else ""

    commodity_signals = 0
    details = {}

    title_commodity = any(re.search(p, title, re.IGNORECASE) for p in COMMODITY_TITLE_PATTERNS)
    details["generic_title"] = title_commodity
    if title_commodity:
        commodity_signals += 1

    body_generic = sum(1 for p in COMMODITY_BODY_PATTERNS if re.search(p, text, re.IGNORECASE))
    details["generic_body_phrases"] = body_generic
    if body_generic >= 2:
        commodity_signals += 1

    first_person = len(re.findall(r'(?:제가|저는|직접|I |my |I\'ve )', text, re.IGNORECASE))
    details["first_person_count"] = first_person
    if first_person == 0:
        commodity_signals += 1

    numbers_data = len(re.findall(r'\d+[\d,.%]*', text))
    korean_ch = len(re.findall(r"[가-힯]", text))
    non_ws_ch = len(re.sub(r'\s', '', text))
    is_ko = (korean_ch / max(non_ws_ch, 1)) > 0.3
    word_count = _count_content_units(text, is_ko)
    data_density = numbers_data / max(word_count, 1)
    details["data_density"] = round(data_density, 4)
    if data_density < 0.005:
        commodity_signals += 1

    is_commodity = commodity_signals >= 2
    details["signal_count"] = commodity_signals

    return {
        "is_commodity": is_commodity,
        "commodity_score": min(100, commodity_signals * 25),
        "details": details,
    }


def analyze_content(url: str) -> dict:
    """Run full content quality analysis with E-E-A-T."""
    validation = validate_url(url)
    if not validation["valid"]:
        return {"success": False, "error": validation["error"]}

    result = fetch_page(url)
    if not result["success"]:
        return {"success": False, "error": result["error"]}

    html = result["html"]
    return analyze_content_html(html, url)


def analyze_content_html(html: str, url: str = "") -> dict:
    """Run content quality analysis on raw HTML."""
    text = extract_text_content(html)
    headings = count_headings(html)
    korean = analyze_korean_content(text)

    experience = score_experience(html)
    expertise = score_expertise(html)
    authoritativeness = score_authoritativeness(html)
    trust = score_trust(html, url)
    eeat = compute_eeat_score(experience, expertise, authoritativeness, trust)

    depth = analyze_content_depth(text)
    commodity = detect_commodity_content(html, text)

    issues = list(eeat["issues"])
    if depth["word_count"] < 300:
        issues.append({"severity": "high", "message": f"Thin content: {depth['word_count']} words (min 300)"})
    if headings.get("h1", 0) == 0:
        issues.append({"severity": "critical", "message": "Missing H1 tag"})
    if headings.get("h1", 0) > 1:
        issues.append({"severity": "medium", "message": f"Multiple H1 tags ({headings['h1']})"})
    if commodity["is_commodity"]:
        issues.append({"severity": "high", "message": "Commodity content detected: lacks unique perspective, first-hand experience, or original data. Google AI systems prioritize non-commodity content."})

    commodity_penalty = 5 if commodity["is_commodity"] else 0
    content_score = round(depth["depth_score"] * 0.4 + eeat["score"] * 0.6 - commodity_penalty, 1)
    content_score = max(0.0, content_score)

    return {
        "success": True,
        "url": url,
        "score": content_score,
        "commodity_analysis": commodity,
        "eeat": {
            "score": eeat["score"],
            "axes": eeat["axes"],
            "weakest": eeat["weakest"],
            "strongest": eeat["strongest"],
            "experience": experience,
            "expertise": expertise,
            "authoritativeness": authoritativeness,
            "trust": trust,
        },
        "content_depth": depth,
        "headings": headings,
        "korean_analysis": korean,
        "issues": issues,
    }


def main():
    parser = argparse.ArgumentParser(description="Content quality and E-E-A-T analysis")
    parser.add_argument("url", help="URL to analyze")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    result = analyze_content(args.url)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result["success"]:
            eeat = result["eeat"]
            print(f"Content Score: {result['score']}/100")
            print(f"E-E-A-T Score: {eeat['score']}/100")
            print(f"  Experience:        {eeat['axes']['experience']:5.1f}/100")
            print(f"  Expertise:         {eeat['axes']['expertise']:5.1f}/100")
            print(f"  Authoritativeness: {eeat['axes']['authoritativeness']:5.1f}/100")
            print(f"  Trust:             {eeat['axes']['trust']:5.1f}/100")
            print(f"  Weakest: {eeat['weakest']} | Strongest: {eeat['strongest']}")
            depth = result["content_depth"]
            print(f"\nContent Depth: {depth['depth_score']}/100 ({depth['word_count']} words)")
            print(f"Korean: {'Yes' if result['korean_analysis']['is_korean_content'] else 'No'}")
            for issue in result["issues"]:
                sev = issue.get("severity", "info")
                print(f"  [{sev.upper()}] {issue['message']}")
        else:
            print(f"Error: {result['error']}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()

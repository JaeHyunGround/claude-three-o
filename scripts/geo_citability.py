"""Passage-level AI citability analysis script for Three-O platform."""

import argparse
import json
import re
import sys

from validate_url import validate_url
from fetch_page import fetch_page


CITABILITY_WEIGHTS = {
    "passage_clarity": 0.25,
    "factual_density": 0.25,
    "structural_format": 0.20,
    "authority_signals": 0.15,
    "uniqueness": 0.15,
}


def extract_passages(html: str) -> list:
    """Extract meaningful text passages from HTML."""
    text_blocks = re.findall(r'<p[^>]*>(.*?)</p>', html, re.DOTALL | re.IGNORECASE)
    li_items = re.findall(r'<li[^>]*>(.*?)</li>', html, re.DOTALL | re.IGNORECASE)

    passages = []
    for block in text_blocks + li_items:
        clean = re.sub(r'<[^>]+>', '', block).strip()
        if len(clean) > 50:
            passages.append(clean)

    return passages


def score_passage_clarity(passage: str) -> float:
    """Score how well a passage can stand alone as an answer."""
    sentences = re.split(r'[.!?。]', passage)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

    if not sentences:
        return 20.0

    score = 50.0
    avg_sentence_len = sum(len(s.split()) for s in sentences) / len(sentences)
    if 10 <= avg_sentence_len <= 25:
        score += 20
    elif avg_sentence_len < 40:
        score += 10

    if any(s[0].isupper() or re.match(r'[가-힣]', s[0]) for s in sentences if s):
        score += 10

    if len(sentences) >= 2:
        score += 10

    pronouns = sum(1 for s in sentences for w in s.lower().split() if w in ["this", "that", "it", "they", "이것", "그것"])
    if pronouns == 0:
        score += 10

    return min(100.0, score)


def score_factual_density(passage: str) -> float:
    """Score the density of facts, numbers, and named entities."""
    score = 30.0

    numbers = re.findall(r'\d+[\d,.%]*', passage)
    score += min(30, len(numbers) * 10)

    proper_nouns = re.findall(r'\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)*\b', passage)
    score += min(20, len(proper_nouns) * 5)

    units = re.findall(r'\d+\s*(km|m|kg|원|달러|%|명|개|건|억|만)', passage)
    score += min(20, len(units) * 7)

    return min(100.0, score)


def score_structural_format(html: str) -> float:
    """Score structural formatting of the page."""
    score = 30.0

    headings = len(re.findall(r'<h[2-4][^>]*>', html, re.IGNORECASE))
    score += min(20, headings * 4)

    lists = len(re.findall(r'<[ou]l[^>]*>', html, re.IGNORECASE))
    score += min(15, lists * 5)

    tables = len(re.findall(r'<table[^>]*>', html, re.IGNORECASE))
    score += min(15, tables * 8)

    definitions = len(re.findall(r'<(dt|dfn|abbr)[^>]*>', html, re.IGNORECASE))
    score += min(10, definitions * 5)

    short_paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', html, re.DOTALL)
    short_count = sum(1 for p in short_paragraphs if 50 < len(re.sub(r'<[^>]+>', '', p)) < 300)
    if short_count > len(short_paragraphs) * 0.5:
        score += 10

    return min(100.0, score)


def score_authority_signals(html: str) -> float:
    """Score authority indicators."""
    score = 20.0

    if re.search(r'(author|byline|written by|작성자)', html, re.IGNORECASE):
        score += 15
    if re.search(r'(published|date|updated|발행일|수정일)', html, re.IGNORECASE):
        score += 10
    if re.search(r'(source|reference|citation|출처|참고)', html, re.IGNORECASE):
        score += 15
    if re.search(r'(study|research|survey|data|연구|조사)', html, re.IGNORECASE):
        score += 15
    if re.search(r'(expert|professor|Ph\.?D|박사|전문가)', html, re.IGNORECASE):
        score += 15
    if 'application/ld+json' in html:
        score += 10

    return min(100.0, score)


def score_uniqueness(passages: list) -> float:
    """Estimate content uniqueness (heuristic-based)."""
    if not passages:
        return 20.0

    score = 40.0

    avg_length = sum(len(p) for p in passages) / len(passages)
    if avg_length > 100:
        score += 15

    numbers_in_passages = sum(1 for p in passages if re.search(r'\d', p))
    if numbers_in_passages > len(passages) * 0.3:
        score += 20

    unique_ratio = len(set(p[:50] for p in passages)) / max(len(passages), 1)
    if unique_ratio > 0.9:
        score += 15

    long_passages = sum(1 for p in passages if len(p) > 200)
    if long_passages > 3:
        score += 10

    return min(100.0, score)


def analyze_citability(url: str, depth: int = 1) -> dict:
    """Full citability analysis for a URL."""
    validation = validate_url(url)
    if not validation["valid"]:
        return {"success": False, "error": validation["error"]}

    result = fetch_page(url)
    if not result["success"]:
        return {"success": False, "error": result["error"]}

    html = result["html"]
    passages = extract_passages(html)

    passage_scores = []
    for passage in passages[:20]:
        clarity = score_passage_clarity(passage)
        factual = score_factual_density(passage)
        p_score = round(clarity * 0.6 + factual * 0.4, 1)
        passage_scores.append({
            "text": passage[:150] + ("..." if len(passage) > 150 else ""),
            "score": p_score,
            "clarity": round(clarity, 1),
            "factual_density": round(factual, 1),
        })

    passage_scores.sort(key=lambda x: x["score"], reverse=True)

    dim_scores = {
        "passage_clarity": round(sum(score_passage_clarity(p) for p in passages[:10]) / max(len(passages[:10]), 1), 1),
        "factual_density": round(sum(score_factual_density(p) for p in passages[:10]) / max(len(passages[:10]), 1), 1),
        "structural_format": round(score_structural_format(html), 1),
        "authority_signals": round(score_authority_signals(html), 1),
        "uniqueness": round(score_uniqueness(passages), 1),
    }

    overall = round(sum(dim_scores[k] * CITABILITY_WEIGHTS[k] for k in CITABILITY_WEIGHTS), 1)

    issues = []
    if dim_scores["passage_clarity"] < 50:
        issues.append({"severity": "high", "message": "Low passage clarity — content not extractable as standalone answers"})
    if dim_scores["factual_density"] < 40:
        issues.append({"severity": "medium", "message": "Low factual density — add specific data, numbers, names"})
    if dim_scores["structural_format"] < 50:
        issues.append({"severity": "medium", "message": "Poor structure — add headings, lists, tables"})
    if dim_scores["authority_signals"] < 40:
        issues.append({"severity": "medium", "message": "Weak authority signals — add author, sources, dates"})
    if len(passages) < 5:
        issues.append({"severity": "high", "message": "Too few citable passages found on page"})

    return {
        "success": True,
        "url": url,
        "score": overall,
        "dimensions": dim_scores,
        "total_passages": len(passages),
        "top_passages": passage_scores[:5],
        "issues": issues,
    }


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
            print(f"Passages Found: {result['total_passages']}")
            print(f"\nDimension Scores:")
            for dim, score in result["dimensions"].items():
                print(f"  {dim.replace('_', ' ').title():25s} {score:5.1f}/100")
            if result["top_passages"]:
                print(f"\nTop Citable Passages:")
                for i, p in enumerate(result["top_passages"][:3], 1):
                    print(f"  {i}. [{p['score']:.0f}] {p['text'][:80]}...")
            for issue in result["issues"]:
                print(f"  [{issue['severity'].upper()}] {issue['message']}")
        else:
            print(f"Error: {result['error']}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()

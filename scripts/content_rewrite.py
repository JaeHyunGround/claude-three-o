"""Content rewrite suggestion engine for Three-O platform.

Analyzes page passages for content quality weaknesses and generates
specific rewrite suggestions to improve clarity, factual density,
and overall helpfulness. Aligned with Google's 'helpful, reliable,
people-first content' guidelines — improving content quality for
readers naturally improves visibility in both traditional and
AI-powered search experiences.
"""

import argparse
import json
import re
import sys

from validate_url import validate_url
from fetch_page import fetch_page
from geo_citability import (
    extract_passages, score_citation_pattern, score_self_containment,
    score_passage_clarity, score_factual_density,
    PLATFORM_CITATION_PREFS,
)


VAGUE_WORDS_KO = [
    "좋은", "다양한", "최고의", "훌륭한", "뛰어난", "우수한",
    "많은", "여러", "가지", "등등", "특별한", "독특한",
    "최선의", "완벽한", "놀라운", "혁신적인",
]

VAGUE_WORDS_EN = [
    "great", "various", "best", "excellent", "amazing", "wonderful",
    "unique", "innovative", "cutting-edge", "world-class", "leading",
    "top-notch", "state-of-the-art", "premier", "superior",
]

FILLER_PATTERNS = [
    r'저희는?\s+.{0,10}(?:제공|드리|합니다)',
    r'(?:we|our)\s+(?:provide|offer|deliver)\s+(?:the best|great|excellent)',
    r'고객\s*(?:님|여러분)?.{0,15}(?:만족|감사|모시)',
    r'(?:your|our)\s+(?:satisfaction|happiness)',
]

WEAK_OPENER_PATTERNS = [
    r'^(?:이것|그것|저것|이런|그런|이에|그에)',
    r'^(?:this|that|it|these|those|here|there)\s',
    r'^(?:그래서|그리고|또한|그러나|하지만)\s',
    r'^(?:and|but|so|also|however|moreover)\s',
]

REWRITE_STRATEGIES = {
    "add_definition": {
        "name_ko": "정의문 추가",
        "name_en": "Add definition pattern",
        "template_ko": "[주어]는 [구체적 설명]을 [동사]하는 [분류]입니다.",
        "template_en": "[Subject] is a [category] that [specific description].",
        "impact": "high",
        "platforms": ["chatgpt", "gemini"],
    },
    "add_data": {
        "name_ko": "수치 데이터 삽입",
        "name_en": "Insert quantitative data",
        "template_ko": "[주어]는 [수치]의 [측정항목]을 기록하며, [비교 기준] 대비 [차이]% [방향]입니다.",
        "template_en": "[Subject] achieves [metric] of [number], [X]% [direction] compared to [benchmark].",
        "impact": "high",
        "platforms": ["perplexity", "claude"],
    },
    "add_comparison": {
        "name_ko": "비교문 구성",
        "name_en": "Add comparison structure",
        "template_ko": "[A]는 [B]에 비해 [차원]에서 [수치/정도] [방향]합니다.",
        "template_en": "[A] [verb] [X]% more/less [metric] compared to [B].",
        "impact": "medium",
        "platforms": ["gemini", "chatgpt"],
    },
    "improve_self_containment": {
        "name_ko": "자기 완결성 강화",
        "name_en": "Improve self-containment",
        "template_ko": "[고유명사 주어]는 [구체적 맥락]에서 [독립적 설명].",
        "template_en": "[Proper noun subject] [verb] [specific context] [standalone explanation].",
        "impact": "high",
        "platforms": ["chatgpt", "perplexity", "gemini", "claude"],
    },
    "add_causal": {
        "name_ko": "인과관계 구문 추가",
        "name_en": "Add causal reasoning",
        "template_ko": "[원인] 때문에 [결과]가 발생하며, 이는 [영향]으로 이어집니다.",
        "template_en": "Because [cause], [effect] occurs, leading to [impact].",
        "impact": "medium",
        "platforms": ["claude", "perplexity"],
    },
    "add_list_structure": {
        "name_ko": "리스트 구조화",
        "name_en": "Convert to structured list",
        "template_ko": "[주제]의 핵심 요소: 1) [항목1] 2) [항목2] 3) [항목3]",
        "template_en": "Key [topic] factors: 1) [item1] 2) [item2] 3) [item3]",
        "impact": "medium",
        "platforms": ["chatgpt", "gemini"],
    },
    "remove_vague": {
        "name_ko": "모호한 표현 제거",
        "name_en": "Remove vague language",
        "template_ko": "'좋은 서비스' → '평균 응답시간 2시간 이내의 1:1 고객지원'",
        "template_en": "'great service' → '1:1 support with average 2-hour response time'",
        "impact": "medium",
        "platforms": ["perplexity", "claude"],
    },
    "fix_opener": {
        "name_ko": "독립적 문장 시작",
        "name_en": "Fix weak opening",
        "template_ko": "'이것은...' → '[브랜드명]의 [서비스명]은...'",
        "template_en": "'This is...' → '[Brand]'s [product] is...'",
        "impact": "high",
        "platforms": ["chatgpt", "perplexity", "gemini", "claude"],
    },
}


def analyze_weakness(passage: str) -> list:
    """Identify specific citability weaknesses in a passage."""
    weaknesses = []

    pattern_result = score_citation_pattern(passage)
    if pattern_result["score"] < 40:
        weaknesses.append({
            "type": "no_citation_pattern",
            "severity": "high",
            "detail": "인용 패턴 미탐지 (정의문, 비교문, 단계, 인과 없음)",
        })

    containment_result = score_self_containment(passage)
    containment = containment_result["score"] if isinstance(containment_result, dict) else containment_result
    if containment < 50:
        weaknesses.append({
            "type": "low_self_containment",
            "severity": "high",
            "detail": "맥락 의존적 — 독립적으로 이해 불가능",
        })

    clarity_result = score_passage_clarity(passage)
    clarity = clarity_result["score"] if isinstance(clarity_result, dict) else clarity_result
    if clarity < 50:
        weaknesses.append({
            "type": "low_clarity",
            "severity": "medium",
            "detail": "문장 구조 불명확 — 주어/서술어 관계 약함",
        })

    factual_result = score_factual_density(passage)
    factual = factual_result["score"] if isinstance(factual_result, dict) else factual_result
    if factual < 40:
        weaknesses.append({
            "type": "low_factual_density",
            "severity": "medium",
            "detail": "구체적 수치/데이터/고유명사 부족",
        })

    vague_found = _find_vague_words(passage)
    if vague_found:
        weaknesses.append({
            "type": "vague_language",
            "severity": "medium",
            "detail": f"모호한 표현 감지: {', '.join(vague_found[:5])}",
        })

    filler_count = sum(1 for p in FILLER_PATTERNS if re.search(p, passage, re.IGNORECASE))
    if filler_count > 0:
        weaknesses.append({
            "type": "filler_content",
            "severity": "high",
            "detail": "의미 없는 마케팅/인사 문구 — AI가 인용하지 않는 패턴",
        })

    for pattern in WEAK_OPENER_PATTERNS:
        if re.search(pattern, passage, re.IGNORECASE):
            weaknesses.append({
                "type": "weak_opener",
                "severity": "medium",
                "detail": "지시어/접속사로 시작 — 독립 인용 불가",
            })
            break

    if len(passage) < 80:
        weaknesses.append({
            "type": "too_short",
            "severity": "low",
            "detail": "패시지가 너무 짧음 (80자 미만) — AI 인용 최소 단위 미달",
        })
    elif len(passage) > 500:
        weaknesses.append({
            "type": "too_long",
            "severity": "low",
            "detail": "패시지가 너무 김 (500자 초과) — 핵심만 추출하기 어려움",
        })

    return weaknesses


def _find_vague_words(passage: str) -> list:
    """Find vague/generic words in passage."""
    found = []
    lower = passage.lower()
    for word in VAGUE_WORDS_KO:
        if word in passage:
            found.append(word)
    for word in VAGUE_WORDS_EN:
        if word in lower:
            found.append(word)
    return found


def suggest_strategies(weaknesses: list) -> list:
    """Select rewrite strategies based on identified weaknesses."""
    strategy_keys = set()

    weakness_to_strategy = {
        "no_citation_pattern": ["add_definition", "add_comparison", "add_causal"],
        "low_self_containment": ["improve_self_containment", "fix_opener"],
        "low_clarity": ["add_definition", "add_list_structure"],
        "low_factual_density": ["add_data"],
        "vague_language": ["remove_vague", "add_data"],
        "filler_content": ["add_definition", "add_data"],
        "weak_opener": ["fix_opener", "improve_self_containment"],
        "too_short": ["add_data", "add_comparison"],
        "too_long": ["add_list_structure"],
    }

    for w in weaknesses:
        keys = weakness_to_strategy.get(w["type"], [])
        strategy_keys.update(keys)

    strategies = []
    for key in strategy_keys:
        if key in REWRITE_STRATEGIES:
            strategy = dict(REWRITE_STRATEGIES[key])
            strategy["key"] = key
            strategies.append(strategy)

    impact_order = {"high": 0, "medium": 1, "low": 2}
    strategies.sort(key=lambda s: impact_order.get(s["impact"], 3))

    return strategies


def compute_passage_score(passage: str) -> dict:
    """Compute full citability breakdown for a passage."""
    pattern_result = score_citation_pattern(passage)
    containment_r = score_self_containment(passage)
    clarity_r = score_passage_clarity(passage)
    factual_r = score_factual_density(passage)
    containment = containment_r["score"] if isinstance(containment_r, dict) else containment_r
    clarity = clarity_r["score"] if isinstance(clarity_r, dict) else clarity_r
    factual = factual_r["score"] if isinstance(factual_r, dict) else factual_r

    overall = round(
        clarity * 0.25 +
        factual * 0.20 +
        pattern_result["score"] * 0.30 +
        containment * 0.25,
        1,
    )

    return {
        "overall": overall,
        "clarity": round(clarity, 1),
        "factual_density": round(factual, 1),
        "citation_pattern": round(pattern_result["score"], 1),
        "self_containment": round(containment, 1),
        "patterns": pattern_result["patterns"],
    }


def estimate_improvement(current_score: dict, strategies: list) -> float:
    """Estimate score improvement from applying strategies."""
    boost = 0.0
    strategy_keys = {s["key"] for s in strategies}

    if "add_definition" in strategy_keys:
        boost += min(25, max(0, 70 - current_score["citation_pattern"]) * 0.4)
    if "add_data" in strategy_keys:
        boost += min(15, max(0, 60 - current_score["factual_density"]) * 0.3)
    if "improve_self_containment" in strategy_keys:
        boost += min(15, max(0, 70 - current_score["self_containment"]) * 0.3)
    if "add_comparison" in strategy_keys:
        boost += min(10, max(0, 50 - current_score["citation_pattern"]) * 0.2)
    if "fix_opener" in strategy_keys:
        boost += min(8, max(0, 60 - current_score["self_containment"]) * 0.15)
    if "remove_vague" in strategy_keys:
        boost += 5
    if "add_list_structure" in strategy_keys:
        boost += 5
    if "add_causal" in strategy_keys:
        boost += min(8, max(0, 50 - current_score["citation_pattern"]) * 0.15)

    return round(min(boost, 100 - current_score["overall"]), 1)


def platform_tips(strategies: list) -> dict:
    """Generate platform-specific tips based on strategies."""
    tips = {}
    for platform in PLATFORM_CITATION_PREFS:
        platform_strategies = [s for s in strategies if platform in s.get("platforms", [])]
        if platform_strategies:
            tips[platform] = [s["name_ko"] for s in platform_strategies[:3]]
    return tips


def analyze_rewrite(html: str, url: str, max_suggestions: int = 10) -> dict:
    """Analyze page and generate rewrite suggestions for low-citability passages.

    Args:
        html: Page HTML content.
        url: Page URL.
        max_suggestions: Maximum number of passage suggestions to return.

    Returns:
        dict with keys: success, url, total_passages, suggestions,
        page_summary, priority_actions.
    """
    passages = extract_passages(html)

    if not passages:
        return {
            "success": True,
            "url": url,
            "total_passages": 0,
            "suggestions": [],
            "analyzed_passages": 0,
            "page_summary": {"avg_score": 0, "weak_count": 0, "ok_count": 0, "strong_count": 0},
            "priority_actions": ["페이지에 충분한 텍스트 콘텐츠가 없습니다. <p> 태그로 본문을 추가하세요."],
        }

    all_scores = []
    candidates = []

    for raw_passage in passages[:30]:
        passage_text = raw_passage["text"] if isinstance(raw_passage, dict) else raw_passage
        score = compute_passage_score(passage_text)
        all_scores.append(score["overall"])

        if score["overall"] < 65:
            weaknesses = analyze_weakness(passage_text)
            strategies = suggest_strategies(weaknesses)
            improvement = estimate_improvement(score, strategies)
            tips = platform_tips(strategies)

            candidates.append({
                "text": passage_text[:200] + ("..." if len(passage_text) > 200 else ""),
                "full_length": len(passage_text),
                "score": score,
                "weaknesses": weaknesses,
                "strategies": strategies,
                "estimated_improvement": improvement,
                "platform_tips": tips,
            })

    candidates.sort(key=lambda c: (
        -c["estimated_improvement"],
        c["score"]["overall"],
    ))

    suggestions = candidates[:max_suggestions]

    weak_count = sum(1 for s in all_scores if s < 40)
    ok_count = sum(1 for s in all_scores if 40 <= s < 65)
    strong_count = sum(1 for s in all_scores if s >= 65)
    avg_score = round(sum(all_scores) / max(len(all_scores), 1), 1)

    priority_actions = _generate_priority_actions(suggestions, avg_score, weak_count)

    return {
        "success": True,
        "url": url,
        "total_passages": len(passages),
        "analyzed_passages": len(all_scores),
        "suggestions": suggestions,
        "page_summary": {
            "avg_score": avg_score,
            "weak_count": weak_count,
            "ok_count": ok_count,
            "strong_count": strong_count,
        },
        "priority_actions": priority_actions,
    }


def _generate_priority_actions(suggestions: list, avg_score: float, weak_count: int) -> list:
    """Generate page-level priority actions from suggestion patterns."""
    actions = []

    weakness_types = {}
    for s in suggestions:
        for w in s["weaknesses"]:
            weakness_types[w["type"]] = weakness_types.get(w["type"], 0) + 1

    if weakness_types.get("no_citation_pattern", 0) >= 3:
        actions.append("대부분의 패시지에 AI 인용 패턴이 없습니다. 정의문('X는 Y이다')과 비교문을 추가하세요.")

    if weakness_types.get("low_factual_density", 0) >= 3:
        actions.append("수치 데이터가 부족합니다. 구체적 숫자, 통계, 측정값을 본문에 포함하세요.")

    if weakness_types.get("vague_language", 0) >= 2:
        actions.append("모호한 마케팅 표현이 많습니다. '최고의', '다양한' 대신 구체적 사실로 대체하세요.")

    if weakness_types.get("low_self_containment", 0) >= 2:
        actions.append("맥락 의존적 문장이 많습니다. 각 단락을 독립적으로 이해 가능하게 작성하세요.")

    if weakness_types.get("filler_content", 0) >= 1:
        actions.append("마케팅/인사 문구를 정보성 콘텐츠로 교체하세요. AI는 사실 기반 문장만 인용합니다.")

    if avg_score < 35:
        actions.append(f"페이지 평균 인용성 {avg_score}점 — 전면적 콘텐츠 리라이트를 권장합니다.")
    elif avg_score < 50:
        actions.append(f"페이지 평균 인용성 {avg_score}점 — 주요 패시지 위주로 개선하세요.")

    if weak_count >= 5:
        actions.append(f"인용성 40점 미만 패시지 {weak_count}개 — 우선순위 높은 순서대로 리라이트하세요.")

    return actions


def format_rewrite_report(result: dict) -> str:
    """Format rewrite analysis as readable report."""
    if not result.get("success"):
        return f"Error: {result.get('error', 'Unknown error')}"

    summary = result["page_summary"]
    lines = [
        "=== Content Rewrite Suggestions ===",
        f"URL: {result['url']}",
        f"Passages: {result['total_passages']} total, {result['analyzed_passages']} analyzed",
        f"Average Citability: {summary['avg_score']}/100",
        f"Distribution: {summary['strong_count']} strong / {summary['ok_count']} moderate / {summary['weak_count']} weak",
        "",
    ]

    if result.get("priority_actions"):
        lines.append("--- Priority Actions ---")
        for i, action in enumerate(result["priority_actions"], 1):
            lines.append(f"  {i}. {action}")
        lines.append("")

    for i, s in enumerate(result["suggestions"], 1):
        score = s["score"]
        lines.append(f"--- Passage {i} (Score: {score['overall']}/100, +{s['estimated_improvement']} potential) ---")
        lines.append(f"  Text: {s['text']}")
        lines.append(f"  Scores: clarity={score['clarity']} factual={score['factual_density']} "
                      f"pattern={score['citation_pattern']} containment={score['self_containment']}")

        if s["weaknesses"]:
            lines.append("  Weaknesses:")
            for w in s["weaknesses"]:
                icon = {"high": "!!", "medium": "!", "low": "."}[w["severity"]]
                lines.append(f"    [{icon}] {w['detail']}")

        if s["strategies"]:
            lines.append("  Rewrite strategies:")
            for st in s["strategies"][:3]:
                lines.append(f"    [{st['impact'].upper()}] {st['name_ko']}")
                lines.append(f"         Template: {st['template_ko']}")

        if s["platform_tips"]:
            tip_parts = [f"{p}: {', '.join(t)}" for p, t in s["platform_tips"].items()]
            lines.append(f"  Platform tips: {' | '.join(tip_parts)}")

        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Content rewrite suggestion engine")
    parser.add_argument("url", help="URL to analyze")
    parser.add_argument("--max", type=int, default=10, help="Max suggestions")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    validation = validate_url(args.url)
    if not validation["valid"]:
        print(f"Error: {validation['error']}", file=sys.stderr)
        sys.exit(1)

    page = fetch_page(args.url)
    if not page["success"]:
        print(f"Error: {page['error']}", file=sys.stderr)
        sys.exit(1)

    result = analyze_rewrite(page["html"], args.url, args.max)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(format_rewrite_report(result))


if __name__ == "__main__":
    main()

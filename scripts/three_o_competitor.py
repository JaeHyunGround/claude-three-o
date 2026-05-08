"""Cross-pillar competitor benchmarking script for Three-O platform.

Uses quality-based scorers from SEO technical, GEO citability, and AAO
selectability modules for multi-dimensional comparison with gap analysis
and actionable recommendations.
"""

import argparse
import json
import re
import sys

from validate_url import validate_url
from fetch_page import fetch_page
from seo_technical import (
    analyze_meta_tags, evaluate_meta_quality,
    analyze_heading_structure, analyze_images,
)
from geo_citability import (
    extract_passages, score_passage_clarity, score_factual_density,
    score_citation_pattern, score_self_containment,
    score_structural_format, score_authority_signals,
)
from aao_selectability import (
    detect_industry, score_structured_data, score_reviews_ratings,
    score_info_completeness, score_api_booking, score_trust_signals,
    score_freshness,
)


SEO_WEIGHTS = {
    "meta_quality": 0.30,
    "headings": 0.20,
    "images": 0.15,
    "performance": 0.20,
    "schema": 0.15,
}

GEO_WEIGHTS = {
    "passage_clarity": 0.20,
    "factual_density": 0.20,
    "citation_pattern": 0.25,
    "structural_format": 0.15,
    "authority_signals": 0.20,
}

AAO_WEIGHTS = {
    "structured_data": 0.25,
    "reviews_ratings": 0.20,
    "info_completeness": 0.20,
    "api_booking": 0.15,
    "trust_signals": 0.10,
    "freshness": 0.10,
}

GAP_RECOMMENDATIONS = {
    "meta_quality": "메타 태그 품질 개선 — 타이틀 30-60자, 디스크립션 80-160자, OG/canonical 추가",
    "headings": "헤딩 구조 수정 — H1 1개, H2/H3 계층 구조, 키워드 포함",
    "images": "이미지 최적화 — alt 텍스트 추가, WebP 전환, lazy loading",
    "performance": "페이지 속도 개선 — 리소스 압축, CDN, 렌더링 최적화",
    "schema": "Schema.org JSON-LD 추가 — 업종별 스키마 적용",
    "passage_clarity": "패시지 명확성 향상 — 짧고 독립적인 문장, 주어 명시",
    "factual_density": "수치 데이터 보강 — 구체적 숫자, 통계, 측정값 삽입",
    "citation_pattern": "AI 인용 패턴 추가 — 정의문, 비교문, 인과관계 구문",
    "structural_format": "구조적 포맷 개선 — 리스트, 테이블, 소제목 활용",
    "authority_signals": "권위 신호 강화 — 저자 표시, 출처 인용, 발행일 추가",
    "structured_data": "구조화 데이터 보강 — 액션 스키마, 필드 완성도 향상",
    "reviews_ratings": "리뷰/평점 시스템 강화 — 가시적 리뷰 표시, rating 스키마",
    "info_completeness": "사업 정보 완성 — 주소, 전화, 영업시간 구조화 표시",
    "api_booking": "예약/구매 액션 추가 — CTA 버튼, 폼 액션, deep link",
    "trust_signals": "신뢰 신호 추가 — 인증, 수상, 파트너, 사업자등록",
    "freshness": "콘텐츠 최신성 향상 — 날짜 표시, 정기 업데이트, 동적 콘텐츠",
}


def score_seo_dimensions(html: str, url: str, elapsed: float) -> dict:
    """Score SEO across multiple quality dimensions."""
    meta = analyze_meta_tags(html)
    meta_quality = evaluate_meta_quality(meta, url)
    headings = analyze_heading_structure(html)
    images = analyze_images(html)

    has_schema = 'application/ld+json' in html
    schema_score = 70.0 if has_schema else 20.0
    if has_schema:
        schema_count = len(re.findall(r'application/ld\+json', html))
        schema_score = min(100.0, 60.0 + schema_count * 10)

    perf_score = 70.0
    if elapsed < 0.5:
        perf_score = 95.0
    elif elapsed < 1.0:
        perf_score = 85.0
    elif elapsed < 2.0:
        perf_score = 70.0
    elif elapsed < 3.0:
        perf_score = 50.0
    else:
        perf_score = 30.0

    heading_score = 80.0 if headings["hierarchy_valid"] else 40.0
    if headings["h1_count"] == 1:
        heading_score += 10
    heading_score -= len(headings["issues"]) * 10
    heading_score = max(0.0, min(100.0, heading_score))

    dimensions = {
        "meta_quality": round(float(meta_quality["score"]), 1),
        "headings": round(heading_score, 1),
        "images": round(images.get("coverage", 0.0), 1),
        "performance": round(perf_score, 1),
        "schema": round(schema_score, 1),
    }

    overall = round(sum(dimensions[k] * SEO_WEIGHTS[k] for k in SEO_WEIGHTS), 1)

    return {"score": overall, "dimensions": dimensions}


def score_geo_dimensions(html: str) -> dict:
    """Score GEO across citability dimensions."""
    passages = extract_passages(html)
    sample = passages[:10]

    if not sample:
        return {
            "score": 0.0,
            "dimensions": {k: 0.0 for k in GEO_WEIGHTS},
        }

    clarity_avg = round(sum(score_passage_clarity(p) for p in sample) / len(sample), 1)
    factual_avg = round(sum(score_factual_density(p) for p in sample) / len(sample), 1)
    pattern_avg = round(
        sum(score_citation_pattern(p)["score"] for p in sample) / len(sample), 1
    )
    structural = round(score_structural_format(html), 1)
    authority = round(score_authority_signals(html), 1)

    dimensions = {
        "passage_clarity": clarity_avg,
        "factual_density": factual_avg,
        "citation_pattern": pattern_avg,
        "structural_format": structural,
        "authority_signals": authority,
    }

    overall = round(sum(dimensions[k] * GEO_WEIGHTS[k] for k in GEO_WEIGHTS), 1)

    return {"score": overall, "dimensions": dimensions}


def score_aao_dimensions(html: str, elapsed: float) -> dict:
    """Score AAO across selectability dimensions."""
    sd = score_structured_data(html)
    rr = score_reviews_ratings(html)
    ic = score_info_completeness(html)
    ab = score_api_booking(html)
    ts = score_trust_signals(html)
    fr = score_freshness(html, elapsed)

    dimensions = {
        "structured_data": round(float(sd["score"]), 1),
        "reviews_ratings": round(float(rr["score"]), 1),
        "info_completeness": round(float(ic["score"]), 1),
        "api_booking": round(float(ab["score"]), 1),
        "trust_signals": round(float(ts["score"]), 1),
        "freshness": round(float(fr["score"]), 1),
    }

    overall = round(sum(dimensions[k] * AAO_WEIGHTS[k] for k in AAO_WEIGHTS), 1)

    return {"score": overall, "dimensions": dimensions}


def analyze_competitor(url: str) -> dict:
    """Deep analysis of a single URL across all pillars and dimensions."""
    validation = validate_url(url)
    if not validation["valid"]:
        return {"url": url, "success": False, "error": validation["error"]}

    result = fetch_page(url)
    if not result["success"]:
        return {"url": url, "success": False, "error": result["error"]}

    html = result["html"]
    elapsed = result.get("elapsed_seconds", 0)

    industry = detect_industry(html)
    seo = score_seo_dimensions(html, url, elapsed)
    geo = score_geo_dimensions(html)
    aao = score_aao_dimensions(html, elapsed)

    three_o = round(seo["score"] * 0.35 + geo["score"] * 0.35 + aao["score"] * 0.30, 1)

    strengths = []
    weaknesses = []
    all_dims = {}
    for pillar_name, pillar_data in [("SEO", seo), ("GEO", geo), ("AAO", aao)]:
        for dim, val in pillar_data["dimensions"].items():
            all_dims[dim] = val
            if val >= 70:
                strengths.append({"dimension": dim, "pillar": pillar_name, "score": val})
            elif val < 40:
                weaknesses.append({"dimension": dim, "pillar": pillar_name, "score": val})

    strengths.sort(key=lambda x: x["score"], reverse=True)
    weaknesses.sort(key=lambda x: x["score"])

    return {
        "url": url,
        "success": True,
        "industry": industry,
        "three_o_score": three_o,
        "seo": seo,
        "geo": geo,
        "aao": aao,
        "strengths": strengths[:5],
        "weaknesses": weaknesses[:5],
        "response_time": round(elapsed, 2),
    }


def compute_dimension_gaps(target: dict, competitor: dict) -> list:
    """Compute per-dimension gaps between target and competitor."""
    gaps = []

    for pillar in ["seo", "geo", "aao"]:
        target_dims = target[pillar]["dimensions"]
        comp_dims = competitor[pillar]["dimensions"]

        for dim in target_dims:
            if dim not in comp_dims:
                continue
            delta = round(target_dims[dim] - comp_dims[dim], 1)
            if abs(delta) >= 5:
                gaps.append({
                    "dimension": dim,
                    "pillar": pillar.upper(),
                    "target_score": target_dims[dim],
                    "competitor_score": comp_dims[dim],
                    "delta": delta,
                    "direction": "advantage" if delta > 0 else "gap",
                    "recommendation": GAP_RECOMMENDATIONS.get(dim, ""),
                })

    gaps.sort(key=lambda g: g["delta"])
    return gaps


def compute_positioning(results: list) -> dict:
    """Compute competitive positioning (radar chart data)."""
    if not results:
        return {}

    all_dimensions = set()
    for r in results:
        for pillar in ["seo", "geo", "aao"]:
            all_dimensions.update(r[pillar]["dimensions"].keys())

    positioning = {}
    for r in results:
        url = r["url"]
        dims = {}
        for pillar in ["seo", "geo", "aao"]:
            for dim, val in r[pillar]["dimensions"].items():
                dims[dim] = val
        positioning[url] = dims

    averages = {}
    for dim in all_dimensions:
        vals = [positioning[url].get(dim, 0) for url in positioning]
        averages[dim] = round(sum(vals) / max(len(vals), 1), 1)

    return {"per_site": positioning, "market_average": averages}


def generate_action_plan(target: dict, gaps: list) -> list:
    """Generate prioritized action plan from gap analysis."""
    actions = []

    critical_gaps = [g for g in gaps if g["direction"] == "gap" and abs(g["delta"]) >= 15]
    moderate_gaps = [g for g in gaps if g["direction"] == "gap" and 5 <= abs(g["delta"]) < 15]

    for gap in critical_gaps:
        actions.append({
            "priority": "P0",
            "dimension": gap["dimension"],
            "pillar": gap["pillar"],
            "gap": abs(gap["delta"]),
            "action": gap["recommendation"],
        })

    for gap in moderate_gaps:
        actions.append({
            "priority": "P1",
            "dimension": gap["dimension"],
            "pillar": gap["pillar"],
            "gap": abs(gap["delta"]),
            "action": gap["recommendation"],
        })

    advantages = [g for g in gaps if g["direction"] == "advantage" and g["delta"] >= 10]
    for adv in advantages:
        actions.append({
            "priority": "maintain",
            "dimension": adv["dimension"],
            "pillar": adv["pillar"],
            "gap": adv["delta"],
            "action": f"우위 유지 — {adv['dimension']} 현재 +{adv['delta']}점 리드",
        })

    priority_order = {"P0": 0, "P1": 1, "maintain": 2}
    actions.sort(key=lambda a: (priority_order.get(a["priority"], 9), -a["gap"]))

    return actions


def compare_competitors(urls: list, target_url: str = "") -> dict:
    """Compare multiple competitors with deep multi-dimensional analysis.

    Args:
        urls: List of URLs to compare.
        target_url: The primary URL to compare against (defaults to first URL).

    Returns:
        dict with rankings, gaps, positioning, and action plan.
    """
    results = []
    for url in urls:
        analysis = analyze_competitor(url)
        results.append(analysis)

    successful = [r for r in results if r.get("success")]
    if not successful:
        return {"success": False, "error": "No URLs could be analyzed"}

    successful.sort(key=lambda x: x["three_o_score"], reverse=True)

    if target_url:
        target = next((r for r in successful if r["url"] == target_url), successful[0])
    else:
        target = successful[0]

    others = [r for r in successful if r["url"] != target["url"]]

    all_gaps = []
    per_competitor_gaps = {}
    for other in others:
        gaps = compute_dimension_gaps(target, other)
        per_competitor_gaps[other["url"]] = gaps
        all_gaps.extend(gaps)

    worst_gaps = [g for g in all_gaps if g["direction"] == "gap"]
    worst_gaps.sort(key=lambda g: g["delta"])
    worst_gaps = worst_gaps[:10]

    positioning = compute_positioning(successful)
    action_plan = generate_action_plan(target, worst_gaps) if worst_gaps else []

    rankings = []
    for i, r in enumerate(successful):
        rankings.append({
            "rank": i + 1,
            "url": r["url"],
            "industry": r["industry"],
            "three_o_score": r["three_o_score"],
            "seo": r["seo"]["score"],
            "geo": r["geo"]["score"],
            "aao": r["aao"]["score"],
            "strengths": [s["dimension"] for s in r["strengths"][:3]],
            "weaknesses": [w["dimension"] for w in r["weaknesses"][:3]],
        })

    return {
        "success": True,
        "target": target["url"],
        "competitors_analyzed": len(successful),
        "rankings": rankings,
        "leader": successful[0]["url"],
        "gaps": worst_gaps,
        "per_competitor_gaps": per_competitor_gaps,
        "positioning": positioning,
        "action_plan": action_plan,
        "detail": results,
    }


def format_benchmark_report(result: dict) -> str:
    """Format benchmark result as readable report."""
    if not result.get("success"):
        return f"Error: {result.get('error', 'Unknown error')}"

    lines = [
        f"=== Competitor Benchmark ({result['competitors_analyzed']} sites) ===",
        f"Target: {result['target']}",
        "",
        f"{'Rank':<5} {'URL':<40} {'Three-O':>8} {'SEO':>6} {'GEO':>6} {'AAO':>6}",
        "-" * 75,
    ]

    for r in result["rankings"]:
        url_short = r["url"][:38]
        marker = " *" if r["url"] == result["target"] else ""
        lines.append(
            f"{r['rank']:<5} {url_short:<40} {r['three_o_score']:>7.1f} "
            f"{r['seo']:>5.1f} {r['geo']:>5.1f} {r['aao']:>5.1f}{marker}"
        )

    for r in result["rankings"]:
        lines.append(f"\n--- {r['url'][:50]} ({r['industry']}) ---")
        if r["strengths"]:
            lines.append(f"  Strengths: {', '.join(r['strengths'])}")
        if r["weaknesses"]:
            lines.append(f"  Weaknesses: {', '.join(r['weaknesses'])}")

    if result.get("gaps"):
        lines.append("\n=== Key Gaps (vs competitors) ===")
        for gap in result["gaps"][:8]:
            lines.append(
                f"  [{gap['pillar']}] {gap['dimension']}: "
                f"{gap['target_score']} vs {gap['competitor_score']} "
                f"(delta {gap['delta']:+.1f})"
            )

    if result.get("action_plan"):
        lines.append("\n=== Action Plan ===")
        for action in result["action_plan"][:8]:
            lines.append(
                f"  [{action['priority']}] {action['pillar']}/{action['dimension']} "
                f"(gap: {action['gap']:.0f}) — {action['action']}"
            )

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Cross-pillar competitor benchmarking")
    parser.add_argument("urls", nargs="+", help="URLs to compare (first = target)")
    parser.add_argument("--target", default="", help="Override target URL")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    result = compare_competitors(args.urls, args.target)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(format_benchmark_report(result))


if __name__ == "__main__":
    main()

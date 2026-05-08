"""SEO drift detection script for Three-O platform.

Tracks dimension-level changes in meta quality, headings, images,
schema, and performance across snapshots.
"""

import argparse
import json
import re
import sys
from db_manager import init_db, get_latest_baseline, save_baseline


SEO_DRIFT_RULES = {
    "score_change": {"threshold": 2, "critical": 10, "warning": 5},
    "meta_quality": {"threshold": 5, "critical": 15, "warning": 8},
    "headings": {"threshold": 5, "critical": 15, "warning": 8},
    "images": {"threshold": 10, "critical": 25, "warning": 15},
    "schema": {"threshold": 5, "critical": 15, "warning": 8},
    "performance": {"threshold": 5, "critical": 15, "warning": 8},
}


def compare_snapshots(current: dict, baseline: dict) -> list:
    """Compare current vs baseline and return changes."""
    changes = []

    _check_score_change(current, baseline, changes)
    _check_dimension_changes(current, baseline, changes)
    _check_meta_changes(current, baseline, changes)
    _check_schema_changes(current, baseline, changes)
    _check_structural_changes(current, baseline, changes)

    return changes


def _check_score_change(current: dict, baseline: dict, changes: list):
    """Check overall score drift."""
    curr_score = current.get("score")
    base_score = baseline.get("score")
    if curr_score is None or base_score is None:
        return

    delta = curr_score - base_score
    rule = SEO_DRIFT_RULES["score_change"]
    if abs(delta) <= rule["threshold"]:
        return

    severity = "critical" if abs(delta) > rule["critical"] else "warning" if abs(delta) > rule["warning"] else "info"
    direction = "improved" if delta > 0 else "declined"
    changes.append({
        "rule": "score_change",
        "severity": severity,
        "direction": direction,
        "delta": round(delta, 1),
        "message": f"Score {direction}: {base_score} → {curr_score} ({'+' if delta > 0 else ''}{delta:.1f})",
    })


def _check_dimension_changes(current: dict, baseline: dict, changes: list):
    """Check per-dimension score drifts."""
    curr_dims = current.get("data", {}).get("dimensions", {})
    base_dims = baseline.get("data", {}).get("dimensions", {})

    dim_labels = {
        "meta_quality": "메타 품질",
        "headings": "헤딩 구조",
        "images": "이미지 최적화",
        "schema": "스키마",
        "performance": "성능",
    }

    for dim, label in dim_labels.items():
        curr_val = curr_dims.get(dim)
        base_val = base_dims.get(dim)
        if curr_val is None or base_val is None:
            continue

        delta = curr_val - base_val
        rule = SEO_DRIFT_RULES.get(dim, SEO_DRIFT_RULES["score_change"])
        if abs(delta) <= rule["threshold"]:
            continue

        severity = "critical" if abs(delta) > rule["critical"] else "warning" if abs(delta) > rule["warning"] else "info"
        direction = "improved" if delta > 0 else "declined"
        changes.append({
            "rule": f"{dim}_change",
            "severity": severity,
            "direction": direction,
            "delta": round(delta, 1),
            "dimension": dim,
            "message": f"{label} {direction}: {base_val:.1f} → {curr_val:.1f} ({'+' if delta > 0 else ''}{delta:.1f})",
        })


def _check_meta_changes(current: dict, baseline: dict, changes: list):
    """Check specific meta tag changes."""
    curr_data = current.get("data", {})
    base_data = baseline.get("data", {})

    if curr_data.get("title") and base_data.get("title"):
        if curr_data["title"] != base_data["title"]:
            changes.append({
                "rule": "title_changed",
                "severity": "warning",
                "message": f"타이틀 변경: \"{base_data['title'][:50]}\" → \"{curr_data['title'][:50]}\"",
            })

    if curr_data.get("description") and base_data.get("description"):
        if curr_data["description"] != base_data["description"]:
            changes.append({
                "rule": "description_changed",
                "severity": "info",
                "message": "메타 디스크립션 변경됨",
            })

    if base_data.get("canonical") and curr_data.get("canonical"):
        if base_data["canonical"] != curr_data["canonical"]:
            changes.append({
                "rule": "canonical_changed",
                "severity": "warning",
                "message": f"Canonical URL 변경: {base_data['canonical'][:50]} → {curr_data['canonical'][:50]}",
            })
    elif base_data.get("canonical") and not curr_data.get("canonical"):
        changes.append({
            "rule": "canonical_removed",
            "severity": "critical",
            "message": "Canonical URL 제거됨",
        })

    base_og = {k: v for k, v in base_data.items() if k.startswith("og:")}
    curr_og = {k: v for k, v in curr_data.items() if k.startswith("og:")}
    lost_og = set(base_og.keys()) - set(curr_og.keys())
    if lost_og:
        changes.append({
            "rule": "og_tags_removed",
            "severity": "warning",
            "message": f"OG 태그 제거: {', '.join(lost_og)}",
        })


def _check_schema_changes(current: dict, baseline: dict, changes: list):
    """Check structured data changes."""
    curr_data = current.get("data", {})
    base_data = baseline.get("data", {})

    curr_schema = curr_data.get("has_schema", False)
    base_schema = base_data.get("has_schema", False)

    if base_schema and not curr_schema:
        changes.append({
            "rule": "schema_removed",
            "severity": "critical",
            "message": "JSON-LD 구조화 데이터 제거됨",
        })
    elif not base_schema and curr_schema:
        changes.append({
            "rule": "schema_added",
            "severity": "info",
            "direction": "improved",
            "message": "JSON-LD 구조화 데이터 추가됨",
        })

    curr_types = set(curr_data.get("schema_types", []))
    base_types = set(base_data.get("schema_types", []))
    lost_types = base_types - curr_types
    new_types = curr_types - base_types
    if lost_types:
        changes.append({
            "rule": "schema_type_removed",
            "severity": "warning",
            "message": f"스키마 타입 제거: {', '.join(lost_types)}",
        })
    if new_types:
        changes.append({
            "rule": "schema_type_added",
            "severity": "info",
            "direction": "improved",
            "message": f"스키마 타입 추가: {', '.join(new_types)}",
        })


def _check_structural_changes(current: dict, baseline: dict, changes: list):
    """Check heading and image structural changes."""
    curr_data = current.get("data", {})
    base_data = baseline.get("data", {})

    curr_h1 = curr_data.get("h1_count", 0)
    base_h1 = base_data.get("h1_count", 0)
    if curr_h1 != base_h1 and base_h1 > 0:
        severity = "critical" if curr_h1 == 0 else "warning"
        changes.append({
            "rule": "h1_count_changed",
            "severity": severity,
            "message": f"H1 태그 수 변경: {base_h1} → {curr_h1}",
        })

    curr_alt = curr_data.get("image_alt_coverage", -1)
    base_alt = base_data.get("image_alt_coverage", -1)
    if curr_alt >= 0 and base_alt >= 0:
        delta = curr_alt - base_alt
        if delta < -20:
            changes.append({
                "rule": "image_alt_declined",
                "severity": "warning",
                "message": f"이미지 alt 커버리지 하락: {base_alt:.0f}% → {curr_alt:.0f}%",
            })


def calculate_drift_score(changes: list) -> float:
    """Calculate overall drift score from changes."""
    score = 0
    for change in changes:
        if change["severity"] == "critical":
            score -= 3
        elif change["severity"] == "warning":
            score -= 1
        elif change.get("direction") == "improved":
            score += 2
    return score


def classify_trend(drift_score: float) -> str:
    """Classify drift trend from score."""
    if drift_score < -8:
        return "declining_fast"
    if drift_score < -3:
        return "declining"
    if drift_score > 8:
        return "improving_fast"
    if drift_score > 3:
        return "improving"
    return "stable"


def run_drift_check(brand: str, current_data: dict) -> dict:
    """Run drift check against stored baseline."""
    init_db()
    baseline_row = get_latest_baseline(brand, "seo")

    if not baseline_row:
        save_baseline(brand, "seo", current_data.get("score", 0), current_data)
        return {
            "success": True,
            "brand": brand,
            "status": "baseline_created",
            "message": "First run — baseline created. No comparison available.",
        }

    baseline = {
        "score": baseline_row["score"],
        "data": json.loads(baseline_row["data_json"]) if baseline_row["data_json"] else {},
    }
    current = {"score": current_data.get("score", 0), "data": current_data}

    changes = compare_snapshots(current, baseline)
    drift_score = calculate_drift_score(changes)
    trend = classify_trend(drift_score)

    dimension_summary = {}
    for c in changes:
        if c.get("dimension"):
            dimension_summary[c["dimension"]] = {
                "direction": c["direction"],
                "delta": c["delta"],
                "severity": c["severity"],
            }

    save_baseline(brand, "seo", current_data.get("score", 0), current_data)

    return {
        "success": True,
        "brand": brand,
        "status": "compared",
        "drift_score": drift_score,
        "trend": trend,
        "changes": changes,
        "dimension_summary": dimension_summary,
        "baseline_date": baseline_row["timestamp"],
        "current_score": current_data.get("score", 0),
        "baseline_score": baseline_row["score"],
    }


def main():
    parser = argparse.ArgumentParser(description="SEO drift detection")
    parser.add_argument("brand", help="Brand name for baseline lookup")
    parser.add_argument("--input", help="Current audit data JSON file")
    parser.add_argument("--score", type=float, help="Current score (if no input file)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    if args.input:
        from pathlib import Path
        data = json.loads(Path(args.input).read_text())
    elif args.score is not None:
        data = {"score": args.score}
    else:
        print("Error: Provide --input or --score", file=sys.stderr)
        sys.exit(1)

    result = run_drift_check(args.brand, data)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result["status"] == "baseline_created":
            print(f"Baseline created for '{args.brand}'. Run again after changes to detect drift.")
        else:
            print(f"SEO Drift: {args.brand}")
            print(f"Score: {result['baseline_score']} → {result['current_score']} (drift: {result['drift_score']})")
            print(f"Trend: {result['trend']}")
            if result["changes"]:
                print(f"Changes ({len(result['changes'])}):")
                for c in result["changes"]:
                    icon = "↑" if c.get("direction") == "improved" else "↓" if c.get("direction") == "declined" else "!"
                    print(f"  {icon} [{c['severity'].upper()}] {c['message']}")


if __name__ == "__main__":
    main()

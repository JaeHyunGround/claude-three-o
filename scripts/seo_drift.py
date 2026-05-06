"""SEO drift detection script for Three-O platform."""

import argparse
import json
import sys
from db_manager import init_db, get_latest_baseline, save_baseline


def compare_snapshots(current: dict, baseline: dict) -> list:
    """Compare current vs baseline and return changes."""
    changes = []

    if current.get("score") and baseline.get("score"):
        delta = current["score"] - baseline["score"]
        if abs(delta) > 2:
            severity = "critical" if abs(delta) > 10 else "warning" if abs(delta) > 5 else "info"
            direction = "improved" if delta > 0 else "declined"
            changes.append({
                "rule": "score_change",
                "severity": severity,
                "direction": direction,
                "delta": round(delta, 1),
                "message": f"Score {direction}: {baseline['score']} → {current['score']} ({'+' if delta > 0 else ''}{delta:.1f})",
            })

    current_data = current.get("data", {})
    baseline_data = baseline.get("data", {})

    if current_data.get("title") and baseline_data.get("title"):
        if current_data["title"] != baseline_data["title"]:
            changes.append({
                "rule": "title_changed",
                "severity": "warning",
                "message": f"Title changed: \"{baseline_data['title']}\" → \"{current_data['title']}\"",
            })

    if baseline_data.get("has_schema") and not current_data.get("has_schema"):
        changes.append({
            "rule": "schema_removed",
            "severity": "critical",
            "message": "JSON-LD structured data was removed",
        })

    if baseline_data.get("canonical") != current_data.get("canonical"):
        if current_data.get("canonical") and baseline_data.get("canonical"):
            changes.append({
                "rule": "canonical_changed",
                "severity": "warning",
                "message": f"Canonical URL changed",
            })

    return changes


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

    if drift_score < -5:
        trend = "declining"
    elif drift_score > 5:
        trend = "improving"
    else:
        trend = "stable"

    save_baseline(brand, "seo", current_data.get("score", 0), current_data)

    return {
        "success": True,
        "brand": brand,
        "status": "compared",
        "drift_score": drift_score,
        "trend": trend,
        "changes": changes,
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
                    print(f"  [{c['severity'].upper()}] {c['message']}")


if __name__ == "__main__":
    main()

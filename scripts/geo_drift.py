"""GEO drift detection script for Three-O platform."""

import argparse
import json
import sys
from datetime import datetime

from db_manager import get_connection, init_db, get_latest_baseline, save_baseline


def compare_geo_snapshots(current: dict, baseline: dict) -> list:
    """Compare current GEO metrics vs baseline."""
    changes = []

    if current.get("score") is not None and baseline.get("score") is not None:
        delta = current["score"] - baseline["score"]
        if abs(delta) > 2:
            severity = "critical" if abs(delta) > 15 else "warning" if abs(delta) > 7 else "info"
            direction = "improved" if delta > 0 else "declined"
            changes.append({
                "rule": "geo_score_change",
                "severity": severity,
                "direction": direction,
                "delta": round(delta, 1),
                "message": f"GEO Score {direction}: {baseline['score']} → {current['score']} ({'+' if delta > 0 else ''}{delta:.1f})",
            })

    current_data = current.get("data", {})
    baseline_data = baseline.get("data", {})

    dimensions = ["mf", "cq", "vr", "ep", "ta"]
    dim_names = {"mf": "Mention Frequency", "cq": "Context Quality",
                 "vr": "Visibility Ranking", "ep": "Entity Presence",
                 "ta": "Technical Accessibility"}

    for dim in dimensions:
        curr_val = current_data.get(dim)
        base_val = baseline_data.get(dim)
        if curr_val is not None and base_val is not None:
            delta = curr_val - base_val
            if abs(delta) > 5:
                severity = "warning" if abs(delta) > 15 else "info"
                direction = "improved" if delta > 0 else "declined"
                changes.append({
                    "rule": f"{dim}_change",
                    "severity": severity,
                    "direction": direction,
                    "delta": round(delta, 1),
                    "message": f"{dim_names[dim]} {direction}: {base_val:.1f} → {curr_val:.1f}",
                })

    curr_platforms = current_data.get("platform_mentions", {})
    base_platforms = baseline_data.get("platform_mentions", {})
    for platform in set(list(curr_platforms.keys()) + list(base_platforms.keys())):
        curr_pct = curr_platforms.get(platform, 0)
        base_pct = base_platforms.get(platform, 0)
        if base_pct > 0 and curr_pct == 0:
            changes.append({
                "rule": "platform_lost",
                "severity": "critical",
                "message": f"Brand disappeared from {platform} (was {base_pct}% mention rate)",
            })
        elif curr_pct > 0 and base_pct == 0:
            changes.append({
                "rule": "platform_gained",
                "severity": "info",
                "direction": "improved",
                "message": f"Brand now appearing on {platform} ({curr_pct}% mention rate)",
            })

    if baseline_data.get("entity_linked") and not current_data.get("entity_linked"):
        changes.append({
            "rule": "entity_delinked",
            "severity": "critical",
            "message": "Entity linking lost — sameAs or schema removed",
        })

    return changes


def calculate_geo_drift_score(changes: list) -> float:
    """Calculate drift severity score."""
    score = 0
    for change in changes:
        if change["severity"] == "critical":
            score -= 4
        elif change["severity"] == "warning":
            score -= 2
        elif change.get("direction") == "improved":
            score += 2
    return score


def run_geo_drift_check(brand: str, current_data: dict) -> dict:
    """Run GEO drift check against stored baseline."""
    init_db()
    baseline_row = get_latest_baseline(brand, "geo")

    if not baseline_row:
        save_baseline(brand, "geo", current_data.get("score", 0), current_data)
        return {
            "success": True,
            "brand": brand,
            "status": "baseline_created",
            "message": "First GEO measurement — baseline created. Run again to detect drift.",
        }

    baseline = {
        "score": baseline_row["score"],
        "data": json.loads(baseline_row["data_json"]) if baseline_row["data_json"] else {},
    }
    current = {"score": current_data.get("score", 0), "data": current_data}

    changes = compare_geo_snapshots(current, baseline)
    drift_score = calculate_geo_drift_score(changes)

    if drift_score < -8:
        trend = "declining_fast"
    elif drift_score < -3:
        trend = "declining"
    elif drift_score > 8:
        trend = "improving_fast"
    elif drift_score > 3:
        trend = "improving"
    else:
        trend = "stable"

    save_baseline(brand, "geo", current_data.get("score", 0), current_data)

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
    parser = argparse.ArgumentParser(description="GEO drift detection")
    parser.add_argument("brand", help="Brand name")
    parser.add_argument("--input", help="Current GEO data JSON file")
    parser.add_argument("--score", type=float, help="Current GEO score")
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

    result = run_geo_drift_check(args.brand, data)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result["status"] == "baseline_created":
            print(f"GEO baseline created for '{args.brand}'. Run again to detect drift.")
        else:
            print(f"GEO Drift: {args.brand}")
            print(f"Score: {result['baseline_score']} → {result['current_score']} (drift: {result['drift_score']})")
            print(f"Trend: {result['trend']}")
            if result["changes"]:
                print(f"Changes ({len(result['changes'])}):")
                for c in result["changes"]:
                    icon = "↑" if c.get("direction") == "improved" else "↓" if c.get("direction") == "declined" else "!"
                    print(f"  {icon} [{c['severity'].upper()}] {c['message']}")


if __name__ == "__main__":
    main()

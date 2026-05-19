"""Unified Three-O drift detection with velocity, trend, and cross-pillar analysis.

Tracks score changes across SEO, GEO, and AAO pillars over multiple snapshots,
computes velocity (rate of change), detects trend direction per dimension,
and generates cross-pillar correlation alerts.
"""

import argparse
import json
from typing import Optional

from db_manager import (
    init_db, get_all_pillar_baselines,
    save_baseline,
)


ALERT_THRESHOLDS = {
    "score_drop_critical": -10,
    "score_drop_warning": -5,
    "velocity_critical": -3.0,
    "velocity_warning": -1.0,
    "pillar_divergence": 15,
}


def compute_velocity(history: list) -> dict:
    """Compute score velocity (points per snapshot) from history.

    Args:
        history: List of baseline dicts ordered by timestamp DESC.

    Returns:
        dict with velocity, acceleration, direction, data_points.
    """
    if len(history) < 2:
        return {"velocity": 0.0, "acceleration": 0.0, "direction": "insufficient_data", "data_points": len(history)}

    scores = [h["score"] for h in history if h.get("score") is not None]
    if len(scores) < 2:
        return {"velocity": 0.0, "acceleration": 0.0, "direction": "insufficient_data", "data_points": len(scores)}

    scores.reverse()

    deltas = [scores[i + 1] - scores[i] for i in range(len(scores) - 1)]
    velocity = round(sum(deltas) / len(deltas), 2)

    acceleration = 0.0
    if len(deltas) >= 2:
        recent_avg = sum(deltas[-min(2, len(deltas)):]) / min(2, len(deltas))
        older_avg = sum(deltas[:min(2, len(deltas))]) / min(2, len(deltas))
        acceleration = round(recent_avg - older_avg, 2)

    if velocity > 1.0:
        direction = "improving"
    elif velocity < -1.0:
        direction = "declining"
    else:
        direction = "stable"

    return {
        "velocity": velocity,
        "acceleration": acceleration,
        "direction": direction,
        "data_points": len(scores),
    }


def compute_trend(history: list) -> dict:
    """Compute trend from score history.

    Returns:
        dict with trend, score_range, latest, oldest, total_change.
    """
    if not history:
        return {"trend": "no_data", "score_range": [0, 0], "latest": 0, "oldest": 0, "total_change": 0}

    scores = [h["score"] for h in history if h.get("score") is not None]
    if not scores:
        return {"trend": "no_data", "score_range": [0, 0], "latest": 0, "oldest": 0, "total_change": 0}

    latest = scores[0]
    oldest = scores[-1]
    total_change = round(latest - oldest, 1)

    if len(scores) < 3:
        if total_change > 3:
            trend = "up"
        elif total_change < -3:
            trend = "down"
        else:
            trend = "flat"
    else:
        scores_rev = list(reversed(scores))
        ups = sum(1 for i in range(len(scores_rev) - 1) if scores_rev[i + 1] > scores_rev[i])
        downs = sum(1 for i in range(len(scores_rev) - 1) if scores_rev[i + 1] < scores_rev[i])

        if ups + downs == 0:
            trend = "flat"
            return {"trend": trend, "score_range": [round(min(scores), 1), round(max(scores), 1)],
                    "latest": round(latest, 1), "oldest": round(oldest, 1), "total_change": total_change}

        ratio = ups / (ups + downs)

        if ratio >= 0.7:
            trend = "consistent_up"
        elif ratio <= 0.3:
            trend = "consistent_down"
        elif total_change > 5:
            trend = "up"
        elif total_change < -5:
            trend = "down"
        else:
            trend = "volatile" if ups > 0 and downs > 0 else "flat"

    return {
        "trend": trend,
        "score_range": [round(min(scores), 1), round(max(scores), 1)],
        "latest": round(latest, 1),
        "oldest": round(oldest, 1),
        "total_change": total_change,
    }


def build_time_series(history: list) -> list:
    """Build time series data points from history."""
    series = []
    for h in reversed(history):
        data = json.loads(h["data_json"]) if h.get("data_json") else {}
        series.append({
            "timestamp": h["timestamp"],
            "score": h.get("score", 0),
            "dimensions": data.get("dimensions", {}),
        })
    return series


def detect_cross_pillar_correlation(pillar_trends: dict) -> list:
    """Detect cross-pillar patterns and generate correlation alerts."""
    alerts = []

    directions = {p: t["trend"] for p, t in pillar_trends.items() if t.get("trend")}

    declining = [p for p, d in directions.items() if d in ("down", "consistent_down")]
    [p for p, d in directions.items() if d in ("up", "consistent_up")]

    if len(declining) >= 2:
        alerts.append({
            "type": "multi_pillar_decline",
            "severity": "critical",
            "pillars": declining,
            "message": f"복수 pillar 동시 하락: {', '.join(p.upper() for p in declining)}",
        })

    if "seo" in declining and "geo" not in declining:
        alerts.append({
            "type": "seo_only_decline",
            "severity": "warning",
            "message": "SEO만 하락 중 — 기술적 SEO 문제(메타, 스키마, 속도) 가능성",
        })
    elif "geo" in declining and "seo" not in declining:
        alerts.append({
            "type": "geo_only_decline",
            "severity": "warning",
            "message": "GEO만 하락 중 — AI 인용성/콘텐츠 품질 확인 필요",
        })
    elif "aao" in declining and len(declining) == 1:
        alerts.append({
            "type": "aao_only_decline",
            "severity": "warning",
            "message": "AAO만 하락 중 — 구조화 데이터 또는 예약/구매 액션 확인",
        })

    scores = {}
    for p, t in pillar_trends.items():
        if t.get("latest"):
            scores[p] = t["latest"]
    if len(scores) >= 2:
        score_vals = list(scores.values())
        divergence = max(score_vals) - min(score_vals)
        if divergence > ALERT_THRESHOLDS["pillar_divergence"]:
            high_p = max(scores, key=lambda k: scores[k])
            low_p = min(scores, key=lambda k: scores[k])
            alerts.append({
                "type": "pillar_divergence",
                "severity": "warning",
                "message": f"Pillar 간 격차 {divergence:.0f}점 — {high_p.upper()} ({scores[high_p]:.0f}) vs {low_p.upper()} ({scores[low_p]:.0f})",
            })

    return alerts


def generate_velocity_alerts(velocities: dict) -> list:
    """Generate alerts based on velocity thresholds."""
    alerts = []
    for pillar, vel_data in velocities.items():
        v = vel_data["velocity"]
        if v <= ALERT_THRESHOLDS["velocity_critical"]:
            alerts.append({
                "type": "velocity_critical",
                "severity": "critical",
                "pillar": pillar,
                "velocity": v,
                "message": f"{pillar.upper()} 급속 하락 중 (속도: {v:+.1f}점/스냅샷)",
            })
        elif v <= ALERT_THRESHOLDS["velocity_warning"]:
            alerts.append({
                "type": "velocity_warning",
                "severity": "warning",
                "pillar": pillar,
                "velocity": v,
                "message": f"{pillar.upper()} 점진 하락 중 (속도: {v:+.1f}점/스냅샷)",
            })
        elif v >= 3.0:
            alerts.append({
                "type": "velocity_positive",
                "severity": "info",
                "pillar": pillar,
                "velocity": v,
                "message": f"{pillar.upper()} 빠른 개선 중 (속도: {v:+.1f}점/스냅샷)",
            })
    return alerts


def analyze_unified_drift(brand: str, current_scores: Optional[dict] = None, history_limit: int = 10) -> dict:
    """Run unified cross-pillar drift analysis.

    Args:
        brand: Brand identifier.
        current_scores: Optional dict with current pillar scores and data
            {"seo": {"score": N, ...}, "geo": {...}, "aao": {...}}.
        history_limit: How many historical snapshots to analyze.

    Returns:
        dict with per-pillar velocity/trend, cross-pillar alerts, time series.
    """
    init_db()

    if current_scores:
        for pillar in ["seo", "geo", "aao"]:
            if pillar in current_scores:
                pillar_data = current_scores[pillar]
                save_baseline(brand, pillar, pillar_data.get("score", 0), pillar_data)

    all_history = get_all_pillar_baselines(brand, history_limit)

    velocities = {}
    trends = {}
    time_series = {}

    for pillar in ["seo", "geo", "aao"]:
        history = all_history.get(pillar, [])
        velocities[pillar] = compute_velocity(history)
        trends[pillar] = compute_trend(history)
        time_series[pillar] = build_time_series(history)

    cross_alerts = detect_cross_pillar_correlation(trends)
    velocity_alerts = generate_velocity_alerts(velocities)
    all_alerts = cross_alerts + velocity_alerts

    all_alerts.sort(key=lambda a: {"critical": 0, "warning": 1, "info": 2}.get(a["severity"], 3))

    overall_status = "stable"
    critical_count = sum(1 for a in all_alerts if a["severity"] == "critical")
    warning_count = sum(1 for a in all_alerts if a["severity"] == "warning")
    if critical_count > 0:
        overall_status = "critical"
    elif warning_count >= 2:
        overall_status = "warning"
    elif any(v["direction"] == "declining" for v in velocities.values()):
        overall_status = "watch"

    return {
        "success": True,
        "brand": brand,
        "overall_status": overall_status,
        "velocities": velocities,
        "trends": trends,
        "alerts": all_alerts,
        "time_series": time_series,
        "history_depth": {p: len(h) for p, h in all_history.items()},
    }


def get_dashboard_trends(brand: str, history_limit: int = 10) -> dict:
    """Get trend data formatted for the HTML dashboard chart.

    Returns:
        dict with 'trends' (for _trend_chart_svg) and 'alerts' (for alert section).
    """
    result = analyze_unified_drift(brand, history_limit=history_limit)
    return {
        "trends": result.get("time_series", {}),
        "alerts": result.get("alerts", []),
        "velocities": result.get("velocities", {}),
        "overall_status": result.get("overall_status", "stable"),
    }


def format_drift_report(result: dict) -> str:
    """Format unified drift report."""
    if not result.get("success"):
        return f"Error: {result.get('error', 'Unknown error')}"

    lines = [
        f"=== Three-O Drift Report: {result['brand']} ===",
        f"Status: {result['overall_status'].upper()}",
        "",
        f"{'Pillar':<8} {'Latest':>8} {'Change':>8} {'Velocity':>10} {'Trend':>15}",
        "-" * 55,
    ]

    for pillar in ["seo", "geo", "aao"]:
        trend = result["trends"].get(pillar, {})
        vel = result["velocities"].get(pillar, {})
        latest = trend.get("latest", 0)
        change = trend.get("total_change", 0)
        velocity = vel.get("velocity", 0)
        trend_dir = trend.get("trend", "no_data")

        lines.append(
            f"{pillar.upper():<8} {latest:>7.1f} {change:>+7.1f} {velocity:>+9.1f}/snap {trend_dir:>15}"
        )

    if result.get("alerts"):
        lines.append(f"\n=== Alerts ({len(result['alerts'])}) ===")
        for alert in result["alerts"]:
            icon = {"critical": "!!", "warning": "!", "info": "i"}.get(alert["severity"], "?")
            lines.append(f"  [{icon}] {alert['message']}")

    lines.append(f"\nHistory depth: SEO={result['history_depth'].get('seo', 0)} "
                 f"GEO={result['history_depth'].get('geo', 0)} "
                 f"AAO={result['history_depth'].get('aao', 0)} snapshots")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Unified Three-O drift analysis")
    parser.add_argument("brand", help="Brand name")
    parser.add_argument("--input", help="Current scores JSON file")
    parser.add_argument("--history", type=int, default=10, help="History depth")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    current = None
    if args.input:
        from pathlib import Path
        current = json.loads(Path(args.input).read_text())

    result = analyze_unified_drift(args.brand, current, args.history)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(format_drift_report(result))


if __name__ == "__main__":
    main()

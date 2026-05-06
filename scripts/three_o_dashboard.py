"""Dashboard data export script for Three-O platform."""

import argparse
import json
import os
import sys
from datetime import datetime

from db_manager import init_db, get_latest_baseline


DASHBOARD_METRICS = {
    "overview": ["three_o_score", "seo_score", "geo_score", "aao_score", "grade"],
    "seo": ["technical", "content", "keywords", "schema", "performance"],
    "geo": ["mention_frequency", "context_quality", "visibility_ranking",
            "entity_presence", "technical_accessibility"],
    "aao": ["selectability", "conversion", "structured_data",
            "rendering", "entity_consistency"],
}


def get_brand_dashboard(brand: str) -> dict:
    """Get dashboard data for a brand from stored baselines."""
    init_db()

    dashboard = {
        "brand": brand,
        "generated_at": datetime.now().isoformat(),
        "pillars": {},
    }

    for pillar in ["seo", "geo", "aao"]:
        baseline = get_latest_baseline(brand, pillar)
        if baseline:
            data = json.loads(baseline["data_json"]) if baseline.get("data_json") else {}
            dashboard["pillars"][pillar] = {
                "score": baseline["score"],
                "last_updated": baseline["timestamp"],
                "data": data,
            }
        else:
            dashboard["pillars"][pillar] = {
                "score": None,
                "last_updated": None,
                "data": {},
            }

    scores = [p["score"] for p in dashboard["pillars"].values() if p["score"] is not None]
    if len(scores) == 3:
        seo = dashboard["pillars"]["seo"]["score"]
        geo = dashboard["pillars"]["geo"]["score"]
        aao = dashboard["pillars"]["aao"]["score"]
        dashboard["three_o_score"] = round(seo * 0.35 + geo * 0.35 + aao * 0.30, 1)
    else:
        dashboard["three_o_score"] = None

    dashboard["data_completeness"] = round(len(scores) / 3 * 100)

    return dashboard


def get_trend_data(brand: str, pillar: str, limit: int = 30) -> list:
    """Get historical trend data for a pillar."""
    init_db()

    import sqlite3
    from config import get_config_dir

    db_path = os.path.join(get_config_dir(), "data", "three_o.db")
    if not os.path.exists(db_path):
        return []

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT score, timestamp FROM baselines "
            "WHERE brand = ? AND pillar = ? "
            "ORDER BY timestamp DESC LIMIT ?",
            (brand, pillar, limit)
        )
        rows = cursor.fetchall()
        return [{"score": row["score"], "date": row["timestamp"]} for row in reversed(rows)]
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()


def export_dashboard(brand: str, output_format: str = "json") -> dict:
    """Export full dashboard data."""
    dashboard = get_brand_dashboard(brand)

    trends = {}
    for pillar in ["seo", "geo", "aao"]:
        trend = get_trend_data(brand, pillar)
        if trend:
            trends[pillar] = trend

    dashboard["trends"] = trends

    if output_format == "csv":
        lines = ["pillar,score,last_updated"]
        for pillar, data in dashboard["pillars"].items():
            score = data["score"] if data["score"] is not None else ""
            updated = data["last_updated"] or ""
            lines.append(f"{pillar},{score},{updated}")
        dashboard["csv_export"] = "\n".join(lines)

    return {"success": True, "dashboard": dashboard}


def main():
    parser = argparse.ArgumentParser(description="Three-O dashboard data export")
    parser.add_argument("brand", help="Brand name")
    parser.add_argument("--format", choices=["json", "csv"], default="json", help="Export format")
    parser.add_argument("--trend", action="store_true", help="Include trend data")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    result = export_dashboard(args.brand, args.format)

    if args.json or args.format == "json":
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif args.format == "csv":
        print(result["dashboard"].get("csv_export", ""))
    else:
        d = result["dashboard"]
        print(f"Dashboard: {args.brand}")
        if d["three_o_score"] is not None:
            print(f"Three-O Score: {d['three_o_score']}/100")
        else:
            print(f"Three-O Score: Incomplete data ({d['data_completeness']}%)")
        print(f"\nPillar Scores:")
        for pillar, data in d["pillars"].items():
            score = f"{data['score']}/100" if data["score"] is not None else "N/A"
            updated = data["last_updated"] or "never"
            print(f"  {pillar.upper():4s} {score:>8s}  (updated: {updated})")


if __name__ == "__main__":
    main()

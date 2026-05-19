"""HTML dashboard report generator for Three-O platform."""

import argparse
import json
import sys
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any, Dict, List, Optional


SEVERITY_COLORS = {
    "critical": "#ef4444",
    "high": "#dc2626",
    "medium": "#f59e0b",
    "warning": "#f59e0b",
    "low": "#64748b",
    "info": "#3b82f6",
}

PILLAR_COLORS = {
    "seo": "#2962ff",
    "geo": "#7c3aed",
    "aao": "#059669",
}

GRADE_COLORS = {
    "A+": "#16a34a", "A": "#22c55e", "B+": "#84cc16", "B": "#eab308",
    "C+": "#f59e0b", "C": "#f97316", "D": "#ef4444", "F": "#dc2626",
}


def _svg_gauge(score: float, label: str, color: str, size: int = 120) -> str:
    r = size // 2 - 8
    circumference = 2 * 3.14159 * r
    offset = circumference * (1 - score / 100)
    return f"""\
<svg width="{size}" height="{size + 30}" viewBox="0 0 {size} {size + 30}">
  <circle cx="{size // 2}" cy="{size // 2}" r="{r}" fill="none" stroke="#e2e8f0" stroke-width="8"/>
  <circle cx="{size // 2}" cy="{size // 2}" r="{r}" fill="none" stroke="{color}" stroke-width="8"
    stroke-dasharray="{circumference}" stroke-dashoffset="{offset:.1f}"
    stroke-linecap="round" transform="rotate(-90 {size // 2} {size // 2})"
    style="transition: stroke-dashoffset 0.8s ease;"/>
  <text x="{size // 2}" y="{size // 2 + 6}" text-anchor="middle" font-size="24" font-weight="700" fill="#1e293b">{score:.0f}</text>
  <text x="{size // 2}" y="{size + 20}" text-anchor="middle" font-size="13" font-weight="600" fill="#64748b">{escape(label)}</text>
</svg>"""


def _severity_badge(severity: str) -> str:
    color = SEVERITY_COLORS.get(severity, "#64748b")
    return f'<span class="badge" style="background:{color}">{escape(severity.upper())}</span>'


def _finding_rows(findings: List[Dict[str, Any]]) -> str:
    if not findings:
        return '<tr><td colspan="3" class="empty">No findings</td></tr>'
    rows = []
    for f in findings[:30]:
        sev = f.get("severity", "info")
        desc = f.get("description", "")
        pillar = f.get("pillar", "")
        rows.append(f"<tr><td>{_severity_badge(sev)}</td><td>{escape(pillar.upper())}</td><td>{escape(desc)}</td></tr>")
    return "\n".join(rows)


def _action_rows(actions: List[Dict[str, Any]]) -> str:
    if not actions:
        return '<tr><td colspan="4" class="empty">No actions</td></tr>'
    rows = []
    for i, a in enumerate(actions[:20], 1):
        desc = a.get("description", "")
        impact = a.get("impact", "")
        effort = a.get("effort", "")
        rows.append(f"<tr><td>{i}</td><td>{escape(desc)}</td><td>{escape(impact)}</td><td>{escape(effort)}</td></tr>")
    return "\n".join(rows)


def _trend_chart_svg(trends: Dict[str, List[Dict]], width: int = 600, height: int = 200) -> str:
    if not trends:
        return ""
    lines_svg = []
    legend_items = []
    max_points = max(len(v) for v in trends.values()) if trends else 0
    if max_points < 2:
        return ""

    for pillar, points in trends.items():
        if len(points) < 2:
            continue
        color = PILLAR_COLORS.get(pillar, "#64748b")
        scores = [p.get("score", 0) or 0 for p in points]
        n = len(scores)
        coords = []
        for i, s in enumerate(scores):
            x = 40 + (i / max(n - 1, 1)) * (width - 60)
            y = 20 + (100 - s) / 100 * (height - 40)
            coords.append(f"{x:.1f},{y:.1f}")
        lines_svg.append(f'<polyline points="{" ".join(coords)}" fill="none" stroke="{color}" stroke-width="2.5"/>')
        for coord in coords:
            lines_svg.append(f'<circle cx="{coord.split(",")[0]}" cy="{coord.split(",")[1]}" r="3" fill="{color}"/>')
        legend_items.append(f'<span style="color:{color};font-weight:600">● {pillar.upper()}</span>')

    grid_lines = []
    for val in [0, 25, 50, 75, 100]:
        y = 20 + (100 - val) / 100 * (height - 40)
        grid_lines.append(f'<line x1="40" y1="{y:.0f}" x2="{width}" y2="{y:.0f}" stroke="#e2e8f0" stroke-width="0.5"/>')
        grid_lines.append(f'<text x="35" y="{y + 4:.0f}" text-anchor="end" font-size="10" fill="#94a3b8">{val}</text>')

    return f"""\
<div class="card">
  <h3>Score Trends</h3>
  <svg width="{width}" height="{height}" viewBox="0 0 {width} {height}">
    {"".join(grid_lines)}
    {"".join(lines_svg)}
  </svg>
  <div class="legend">{" &nbsp; ".join(legend_items)}</div>
</div>"""


def _drift_alerts_html(alerts: list, velocities: dict, overall_status: str) -> str:
    """Render drift alerts section."""
    if not alerts and not velocities:
        return ""
    status_colors = {"critical": "#ef4444", "warning": "#f59e0b", "watch": "#3b82f6", "stable": "#10b981"}
    status_color = status_colors.get(overall_status, "#64748b")
    rows = []
    for a in alerts:
        sev = a.get("severity", "info")
        color = SEVERITY_COLORS.get(sev, "#64748b")
        msg = escape(a.get("message", ""))
        rows.append(f'<tr><td><span class="badge" style="background:{color}">{sev.upper()}</span></td><td>{msg}</td></tr>')
    vel_items = []
    for p in ["seo", "geo", "aao"]:
        v = velocities.get(p, {})
        vel = v.get("velocity", 0)
        direction = v.get("direction", "stable")
        arrow = {"improving": "&#9650;", "declining": "&#9660;"}.get(direction, "&#9644;")
        color = {"improving": "#10b981", "declining": "#ef4444"}.get(direction, "#64748b")
        vel_items.append(f'<span style="color:{color};font-weight:600">{arrow} {p.upper()} {vel:+.1f}/snap</span>')
    return f"""\
<div class="card">
  <h3>Drift Monitor <span class="badge" style="background:{status_color}">{overall_status.upper()}</span></h3>
  <div style="display:flex;gap:24px;margin-bottom:16px;flex-wrap:wrap">{" ".join(vel_items)}</div>
  {f'<table><thead><tr><th>Severity</th><th>Alert</th></tr></thead><tbody>{"".join(rows)}</tbody></table>' if rows else '<div class="empty">No drift alerts</div>'}
</div>"""


def generate_html_report(data: Dict[str, Any], trends: Optional[Dict] = None,
                         drift_alerts: Optional[list] = None,
                         drift_velocities: Optional[dict] = None,
                         drift_status: str = "stable") -> str:
    """Generate a self-contained HTML dashboard from audit data."""
    brand = escape(str(data.get("brand", "Unknown")))
    date = datetime.now().strftime("%Y-%m-%d %H:%M")
    score = data.get("three_o_score", 0) or 0
    grade = data.get("grade", "N/A")
    grade_color = GRADE_COLORS.get(grade, "#64748b")
    industry = data.get("industry", "")
    pillars = data.get("pillars", {})
    seo = pillars.get("seo", 0) or 0
    geo = pillars.get("geo", 0) or 0
    aao = pillars.get("aao", 0) or 0
    weights = data.get("weights_applied", {"seo": 0.35, "geo": 0.35, "aao": 0.30})
    findings = data.get("findings", [])
    actions = data.get("actions", [])
    confidence = data.get("confidence", 1.0)
    balance = data.get("balance_penalty", 1.0)

    main_gauge = _svg_gauge(score, "Three-O Score", "#2962ff", 160)
    seo_gauge = _svg_gauge(seo, f"SEO ({weights.get('seo', 0.35):.0%})", PILLAR_COLORS["seo"])
    geo_gauge = _svg_gauge(geo, f"GEO ({weights.get('geo', 0.35):.0%})", PILLAR_COLORS["geo"])
    aao_gauge = _svg_gauge(aao, f"AAO ({weights.get('aao', 0.30):.0%})", PILLAR_COLORS["aao"])

    severity_counts = {}
    for f in findings:
        s = f.get("severity", "info")
        severity_counts[s] = severity_counts.get(s, 0) + 1

    stats_html = ""
    for sev in ["critical", "high", "medium", "low"]:
        cnt = severity_counts.get(sev, 0)
        if cnt > 0:
            color = SEVERITY_COLORS.get(sev, "#64748b")
            stats_html += f'<div class="stat"><span class="stat-num" style="color:{color}">{cnt}</span><span class="stat-label">{sev.title()}</span></div>'

    trend_html = _trend_chart_svg(trends or {})
    drift_html = _drift_alerts_html(drift_alerts or [], drift_velocities or {}, drift_status)

    return f"""\
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Three-O Report: {brand}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif; background: #f1f5f9; color: #1e293b; line-height: 1.6; }}
  .container {{ max-width: 1100px; margin: 0 auto; padding: 24px; }}
  header {{ background: linear-gradient(135deg, #1e293b, #334155); color: white; padding: 32px; border-radius: 16px; margin-bottom: 24px; }}
  header h1 {{ font-size: 28px; margin-bottom: 4px; }}
  header .meta {{ color: #94a3b8; font-size: 14px; }}
  header .meta span {{ margin-right: 16px; }}
  .grade {{ display: inline-block; background: {grade_color}; color: white; font-size: 18px; font-weight: 700; padding: 4px 14px; border-radius: 8px; margin-left: 12px; vertical-align: middle; }}
  .gauges {{ display: flex; justify-content: center; align-items: flex-start; gap: 40px; flex-wrap: wrap; margin: 24px 0; }}
  .card {{ background: white; border-radius: 12px; padding: 24px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }}
  .card h3 {{ font-size: 16px; color: #475569; margin-bottom: 16px; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; }}
  .stats {{ display: flex; gap: 24px; flex-wrap: wrap; margin-bottom: 20px; }}
  .stat {{ text-align: center; }}
  .stat-num {{ display: block; font-size: 28px; font-weight: 700; }}
  .stat-label {{ font-size: 12px; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
  th {{ text-align: left; padding: 10px 12px; background: #f8fafc; color: #64748b; font-weight: 600; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 2px solid #e2e8f0; }}
  td {{ padding: 10px 12px; border-bottom: 1px solid #f1f5f9; }}
  tr:hover td {{ background: #f8fafc; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; color: white; font-size: 11px; font-weight: 600; letter-spacing: 0.3px; }}
  .empty {{ text-align: center; color: #94a3b8; padding: 24px; }}
  .legend {{ text-align: center; margin-top: 8px; font-size: 13px; }}
  .meta-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; font-size: 14px; }}
  .meta-grid dt {{ color: #64748b; }}
  .meta-grid dd {{ font-weight: 600; }}
  footer {{ text-align: center; color: #94a3b8; font-size: 12px; margin-top: 32px; padding: 16px; }}
  @media (max-width: 640px) {{
    .gauges {{ gap: 16px; }}
    .container {{ padding: 12px; }}
    header {{ padding: 20px; }}
    header h1 {{ font-size: 22px; }}
  }}
  @media print {{
    body {{ background: white; }}
    .card {{ box-shadow: none; border: 1px solid #e2e8f0; }}
  }}
</style>
</head>
<body>
<div class="container">
  <header>
    <h1>{brand} <span class="grade">{escape(grade)}</span></h1>
    <div class="meta">
      <span>Generated: {date}</span>
      {f'<span>Industry: {escape(industry)}</span>' if industry else ''}
      <span>Confidence: {confidence:.0%}</span>
      {f'<span>Balance: {balance:.1%}</span>' if balance < 1.0 else ''}
    </div>
  </header>

  <div class="card">
    <div class="gauges">
      {main_gauge}
      {seo_gauge}
      {geo_gauge}
      {aao_gauge}
    </div>
  </div>

  {f'<div class="card"><h3>Issue Summary</h3><div class="stats">{stats_html}</div></div>' if stats_html else ''}

  {trend_html}

  {drift_html}

  <div class="card">
    <h3>Findings ({len(findings)})</h3>
    <table>
      <thead><tr><th>Severity</th><th>Pillar</th><th>Description</th></tr></thead>
      <tbody>{_finding_rows(findings)}</tbody>
    </table>
  </div>

  <div class="card">
    <h3>Action Plan ({len(actions)})</h3>
    <table>
      <thead><tr><th>#</th><th>Action</th><th>Impact</th><th>Effort</th></tr></thead>
      <tbody>{_action_rows(actions)}</tbody>
    </table>
  </div>

  <div class="card">
    <h3>Audit Details</h3>
    <dl class="meta-grid">
      <dt>SEO Score</dt><dd>{seo:.1f}/100 (weight: {weights.get('seo', 0.35):.1%})</dd>
      <dt>GEO Score</dt><dd>{geo:.1f}/100 (weight: {weights.get('geo', 0.35):.1%})</dd>
      <dt>AAO Score</dt><dd>{aao:.1f}/100 (weight: {weights.get('aao', 0.30):.1%})</dd>
      <dt>Three-O Score</dt><dd>{score:.1f}/100</dd>
    </dl>
  </div>

  <footer>Generated by Three-O Platform v1.0 &mdash; SEO + GEO + AAO Unified Optimization</footer>
</div>
</body>
</html>"""


def save_html_report(data: Dict[str, Any], brand: str, trends: Optional[Dict] = None,
                     drift_alerts: Optional[list] = None,
                     drift_velocities: Optional[dict] = None,
                     drift_status: str = "stable") -> Path:
    """Generate and save HTML report. Returns filepath."""
    html = generate_html_report(data, trends, drift_alerts, drift_velocities, drift_status)
    reports_dir = Path.cwd() / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")
    filepath = reports_dir / f"{brand}-{date_str}-dashboard.html"
    filepath.write_text(html, encoding="utf-8")
    return filepath


def main():
    parser = argparse.ArgumentParser(description="Generate Three-O HTML dashboard report")
    parser.add_argument("--input", required=True, help="Input JSON data file")
    parser.add_argument("--output", help="Output HTML file path (auto-generated if omitted)")
    parser.add_argument("--json", action="store_true", help="Output filepath as JSON")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(input_path.read_text())
    brand = data.get("brand", "unknown").replace(" ", "-").lower()

    if args.output:
        html = generate_html_report(data)
        Path(args.output).write_text(html, encoding="utf-8")
        filepath = Path(args.output)
    else:
        filepath = save_html_report(data, brand)

    if args.json:
        print(json.dumps({"path": str(filepath), "format": "html"}))
    else:
        print(f"HTML dashboard saved: {filepath}")


if __name__ == "__main__":
    main()

"""Tests for HTML dashboard report generator."""

import json

import pytest

from report_html import (
    generate_html_report,
    save_html_report,
    _svg_gauge,
    _severity_badge,
    _finding_rows,
    _action_rows,
    _trend_chart_svg,
    _drift_alerts_html,
)


SAMPLE_DATA = {
    "brand": "SkyVentures",
    "three_o_score": 72.5,
    "grade": "B+",
    "industry": "agency",
    "confidence": 1.0,
    "balance_penalty": 0.98,
    "pillars": {"seo": 78.0, "geo": 65.0, "aao": 74.0},
    "weights_applied": {"seo": 0.367, "geo": 0.333, "aao": 0.300},
    "findings": [
        {"severity": "critical", "pillar": "seo", "description": "Missing H1 tag"},
        {"severity": "high", "pillar": "geo", "description": "No AI brand mentions found"},
        {"severity": "medium", "pillar": "aao", "description": "Slow server response"},
        {"severity": "low", "pillar": "seo", "description": "Missing alt text on 2 images"},
    ],
    "actions": [
        {"description": "Add H1 tag to homepage", "impact": "high", "effort": "low"},
        {"description": "Create FAQ structured data", "impact": "medium", "effort": "medium"},
    ],
}

SAMPLE_TRENDS = {
    "seo": [
        {"score": 70, "date": "2025-01-01"},
        {"score": 73, "date": "2025-02-01"},
        {"score": 78, "date": "2025-03-01"},
    ],
    "geo": [
        {"score": 50, "date": "2025-01-01"},
        {"score": 58, "date": "2025-02-01"},
        {"score": 65, "date": "2025-03-01"},
    ],
}


class TestSvgGauge:
    def test_returns_svg(self):
        svg = _svg_gauge(85.0, "SEO", "#2962ff")
        assert "<svg" in svg
        assert "</svg>" in svg
        assert "85" in svg
        assert "SEO" in svg

    def test_zero_score(self):
        svg = _svg_gauge(0, "Empty", "#ccc")
        assert "0" in svg

    def test_full_score(self):
        svg = _svg_gauge(100, "Perfect", "#00ff00")
        assert "100" in svg

    def test_custom_size(self):
        svg = _svg_gauge(50, "Test", "#000", size=200)
        assert 'width="200"' in svg


class TestSeverityBadge:
    def test_critical_badge(self):
        badge = _severity_badge("critical")
        assert "CRITICAL" in badge
        assert "#ef4444" in badge

    def test_unknown_severity(self):
        badge = _severity_badge("unknown")
        assert "UNKNOWN" in badge
        assert "#64748b" in badge


class TestFindingRows:
    def test_empty_findings(self):
        html = _finding_rows([])
        assert "No findings" in html

    def test_findings_rendered(self):
        findings = [
            {"severity": "high", "pillar": "seo", "description": "Missing title"},
        ]
        html = _finding_rows(findings)
        assert "Missing title" in html
        assert "SEO" in html
        assert "HIGH" in html

    def test_max_30_findings(self):
        findings = [{"severity": "low", "pillar": "seo", "description": f"Issue {i}"} for i in range(50)]
        html = _finding_rows(findings)
        assert "Issue 29" in html
        assert "Issue 30" not in html

    def test_html_escaping(self):
        findings = [{"severity": "info", "pillar": "seo", "description": '<script>alert("xss")</script>'}]
        html = _finding_rows(findings)
        assert "<script>" not in html
        assert "&lt;script&gt;" in html


class TestActionRows:
    def test_empty_actions(self):
        html = _action_rows([])
        assert "No actions" in html

    def test_actions_numbered(self):
        actions = [
            {"description": "Fix title", "impact": "high", "effort": "low"},
            {"description": "Add schema", "impact": "medium", "effort": "medium"},
        ]
        html = _action_rows(actions)
        assert "<td>1</td>" in html
        assert "<td>2</td>" in html
        assert "Fix title" in html


class TestTrendChart:
    def test_empty_trends(self):
        assert _trend_chart_svg({}) == ""

    def test_single_point_no_chart(self):
        trends = {"seo": [{"score": 70, "date": "2025-01-01"}]}
        assert _trend_chart_svg(trends) == ""

    def test_renders_polyline(self):
        svg = _trend_chart_svg(SAMPLE_TRENDS)
        assert "<polyline" in svg
        assert "SEO" in svg
        assert "GEO" in svg

    def test_has_grid_lines(self):
        svg = _trend_chart_svg(SAMPLE_TRENDS)
        assert "<line" in svg


class TestGenerateHtmlReport:
    def test_returns_valid_html(self):
        html = generate_html_report(SAMPLE_DATA)
        assert "<!DOCTYPE html>" in html
        assert "</html>" in html
        assert "SkyVentures" in html

    def test_contains_scores(self):
        html = generate_html_report(SAMPLE_DATA)
        assert "72" in html  # three_o_score rounded
        assert "78" in html  # seo
        assert "65" in html  # geo
        assert "74" in html  # aao

    def test_contains_grade(self):
        html = generate_html_report(SAMPLE_DATA)
        assert "B+" in html

    def test_contains_findings(self):
        html = generate_html_report(SAMPLE_DATA)
        assert "Missing H1 tag" in html
        assert "CRITICAL" in html

    def test_contains_actions(self):
        html = generate_html_report(SAMPLE_DATA)
        assert "Add H1 tag to homepage" in html

    def test_industry_shown(self):
        html = generate_html_report(SAMPLE_DATA)
        assert "agency" in html

    def test_with_trends(self):
        html = generate_html_report(SAMPLE_DATA, trends=SAMPLE_TRENDS)
        assert "Score Trends" in html
        assert "<polyline" in html

    def test_without_trends(self):
        html = generate_html_report(SAMPLE_DATA)
        assert "Score Trends" not in html

    def test_minimal_data(self):
        html = generate_html_report({"brand": "Test"})
        assert "<!DOCTYPE html>" in html
        assert "Test" in html

    def test_xss_prevention_brand(self):
        data = dict(SAMPLE_DATA, brand='<script>alert("xss")</script>')
        html = generate_html_report(data)
        assert "<script>alert" not in html
        assert "&lt;script&gt;" in html

    def test_korean_brand(self):
        data = dict(SAMPLE_DATA, brand="스카이벤처스")
        html = generate_html_report(data)
        assert "스카이벤처스" in html
        assert 'lang="ko"' in html

    def test_balance_penalty_shown_when_below_1(self):
        html = generate_html_report(SAMPLE_DATA)
        assert "Balance" in html

    def test_balance_penalty_hidden_when_1(self):
        data = dict(SAMPLE_DATA, balance_penalty=1.0)
        html = generate_html_report(data)
        assert "Balance:" not in html

    def test_responsive_meta_tag(self):
        html = generate_html_report(SAMPLE_DATA)
        assert "viewport" in html

    def test_print_styles(self):
        html = generate_html_report(SAMPLE_DATA)
        assert "@media print" in html


class TestDriftAlertsHtml:
    def test_empty_returns_empty(self):
        assert _drift_alerts_html([], {}, "stable") == ""

    def test_with_alerts_renders_table(self):
        alerts = [{"severity": "critical", "message": "Score dropped"}]
        html = _drift_alerts_html(alerts, {}, "critical")
        assert "Drift Monitor" in html
        assert "Score dropped" in html
        assert "CRITICAL" in html

    def test_velocity_arrows(self):
        velocities = {
            "seo": {"velocity": 2.5, "direction": "improving"},
            "geo": {"velocity": -1.5, "direction": "declining"},
            "aao": {"velocity": 0.0, "direction": "stable"},
        }
        html = _drift_alerts_html([], velocities, "stable")
        assert "SEO" in html
        assert "GEO" in html
        assert "AAO" in html

    def test_status_badge(self):
        html = _drift_alerts_html([{"severity": "warning", "message": "test"}], {}, "warning")
        assert "WARNING" in html

    def test_xss_prevention(self):
        alerts = [{"severity": "info", "message": '<script>alert("xss")</script>'}]
        html = _drift_alerts_html(alerts, {}, "stable")
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_no_alerts_shows_empty_message(self):
        html = _drift_alerts_html([], {"seo": {"velocity": 0, "direction": "stable"}}, "stable")
        assert "No drift alerts" in html


class TestGenerateHtmlWithDrift:
    def test_drift_section_rendered(self):
        alerts = [{"severity": "warning", "message": "GEO declining"}]
        velocities = {"seo": {"velocity": 1.0, "direction": "improving"}}
        html = generate_html_report(SAMPLE_DATA, drift_alerts=alerts, drift_velocities=velocities, drift_status="warning")
        assert "Drift Monitor" in html
        assert "GEO declining" in html

    def test_no_drift_no_section(self):
        html = generate_html_report(SAMPLE_DATA)
        assert "Drift Monitor" not in html


class TestSaveHtmlReport:
    def test_creates_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        filepath = save_html_report(SAMPLE_DATA, "skyventures")
        assert filepath.exists()
        assert filepath.suffix == ".html"
        content = filepath.read_text()
        assert "<!DOCTYPE html>" in content

    def test_filename_format(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        filepath = save_html_report(SAMPLE_DATA, "mysite")
        assert "mysite-" in filepath.name
        assert "-dashboard.html" in filepath.name

    def test_reports_dir_created(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        save_html_report(SAMPLE_DATA, "test")
        assert (tmp_path / "reports").is_dir()


class TestMainCli:
    def test_main_with_input_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        input_file = tmp_path / "input.json"
        input_file.write_text(json.dumps(SAMPLE_DATA))

        import report_html
        import sys
        sys.argv = ["report_html", "--input", str(input_file), "--json"]
        report_html.main()

        reports = list((tmp_path / "reports").glob("*.html"))
        assert len(reports) == 1

    def test_main_missing_input(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        import report_html
        import sys
        sys.argv = ["report_html", "--input", "nonexistent.json"]
        with pytest.raises(SystemExit) as exc:
            report_html.main()
        assert exc.value.code == 1

    def test_main_custom_output(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        input_file = tmp_path / "input.json"
        input_file.write_text(json.dumps(SAMPLE_DATA))
        output_file = tmp_path / "custom.html"

        import report_html
        import sys
        sys.argv = ["report_html", "--input", str(input_file), "--output", str(output_file)]
        report_html.main()

        assert output_file.exists()
        assert "<!DOCTYPE html>" in output_file.read_text()

"""CLI routing logic for Three-O platform."""

import importlib
import sys

from config import VERSION

COMMANDS = {
    "seo": {
        "technical": "seo_technical",
        "content": "seo_content",
        "keywords": "seo_keywords",
        "schema": "seo_schema",
        "page": "seo_page",
        "robots": "seo_robots",
        "sitemap": "seo_sitemap",
        "indexing": "seo_indexing",
        "naver": "seo_naver",
        "cwv": "seo_cwv",
        "competitor": "seo_competitor",
        "drift": "seo_drift",
    },
    "geo": {
        "audit": "geo_audit",
        "mentions": "geo_mentions",
        "citability": "geo_citability",
        "entity": "geo_entity",
        "sentiment": "geo_sentiment",
        "context": "geo_context",
        "score": "geo_score",
        "visibility": "geo_visibility",
        "platforms": "geo_platforms",
        "technical": "geo_technical",
        "llms-txt": "geo_llms_txt",
        "drift": "geo_drift",
    },
    "aao": {
        "selectability": "aao_selectability",
        "conversion": "aao_conversion",
        "data": "aao_data",
        "entity": "aao_entity",
        "feed": "aao_feed",
        "rendering": "aao_rendering",
        "scenario": "aao_scenario",
    },
    "score": "score_calculator",
    "report": "report_generator",
    "report-pdf": "report_pdf",
    "report-html": "report_html",
    "dashboard": "three_o_dashboard",
    "config": "config",
    "plan": "three_o_plan",
    "competitor": "three_o_competitor",
    "drift": "three_o_drift",
    "rewrite": "content_rewrite",
    "recommend": "recommendations",
}

DESCRIPTION = """\
Three-O: Unified SEO + GEO + AAO Optimization Platform

Modules:
  seo <cmd>       Search engine optimization (technical, content, keywords, ...)
  geo <cmd>       Generative engine optimization (mentions, citability, entity, ...)
  aao <cmd>       Assistive agent optimization (selectability, conversion, feed, ...)

Utilities:
  score           Compute Three-O / GEO scores
  report          Generate Markdown/JSON report
  report-pdf      Generate PDF report
  report-html     Generate HTML dashboard report
  dashboard       Dashboard data export
  config          API key configuration
  plan            Strategic planning
  competitor      Cross-pillar competitor analysis
  drift           Drift monitoring
  rewrite         Content rewrite suggestions
  recommend       Recommendation engine

Examples:
  python3 -m scripts seo technical https://example.com --json
  python3 -m scripts geo mentions "my brand" --json
  python3 -m scripts score three-o --seo 80 --geo 70 --aao 65
  python3 -m scripts report-html --input data.json
  python3 -m scripts dashboard mybrand --format json
"""


def main(argv=None):
    args = argv if argv is not None else sys.argv[1:]

    if not args or args[0] in ("--help", "-h"):
        print(DESCRIPTION)
        sys.exit(0)

    if args[0] in ("--version", "-V"):
        print(f"Three-O {VERSION}")
        sys.exit(0)

    command = args[0]
    entry = COMMANDS.get(command)
    if entry is None:
        print(f"Unknown command: {command}", file=sys.stderr)
        print(f"Available: {', '.join(COMMANDS.keys())}", file=sys.stderr)
        sys.exit(1)

    if isinstance(entry, dict):
        rest = args[1:]
        if not rest or rest[0] in ("--help", "-h"):
            print(f"Available {command} sub-commands: {', '.join(entry.keys())}")
            sys.exit(0)
        subcmd = rest[0]
        module_name = entry.get(subcmd)
        if module_name is None:
            print(f"Unknown {command} sub-command: {subcmd}", file=sys.stderr)
            print(f"Available: {', '.join(entry.keys())}", file=sys.stderr)
            sys.exit(1)
        sys.argv = [f"three-o {command} {subcmd}"] + rest[1:]
    else:
        module_name = entry
        sys.argv = [f"three-o {command}"] + args[1:]

    module = importlib.import_module(module_name)
    if hasattr(module, "main"):
        module.main()
    else:
        print(f"Module {module_name} has no main() function", file=sys.stderr)
        sys.exit(1)

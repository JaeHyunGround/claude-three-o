# Changelog

All notable changes to Claude Three-O are documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.8.0] - 2026-05-19

### Changed
- `seo_technical.py`: HTML pre-parsing (`_preparse_html`) extracts all elements once, shared across 8 scoring functions
- `analyze_technical()` reuses data from `analyze_technical_html()` instead of re-calling backward-compat functions
- Eliminated redundant HTTP fetch — `check_https()` was making a second request for headers already available
- `score_performance_signals` reuses pre-extracted `<script>` tags instead of re-scanning HTML
- All `score_*` functions accept optional `_pre` parameter while keeping backward-compatible standalone usage

## [1.7.0] - 2026-05-18

### Added
- Retry logic in `fetch_page` — retries transient failures (timeout, connection error, 5xx) up to 2 times with 1s delay
- `SETUP_GUIDES` dict and `get_setup_guide()` in config.py — per-service setup instructions with URLs
- Setup guide field in GEO mention tracking when API key is missing
- 10 new tests: 6 retry logic, 4 setup guides — total 2516 → 2526

### Fixed
- `geo_mentions.py` called nonexistent `load_config()` and passed wrong args to `get_api_key()` — fixed function signatures to match config.py API
- Removed compatibility shim from test_geo_mentions.py that masked the signature mismatch

## [1.6.0] - 2026-05-18

### Added
- Naver OG image dimension validation (min 200x200)
- Crawl-delay parsing for Yeti bot in robots.txt
- X-Robots-Tag header analysis for Naver/Yeti directives
- Korean meta description length check (Naver truncates at ~77 chars)
- Naver ecosystem link detection (Blog, Place, Smart Store, Cafe, Map)
- Mobile viewport check (Naver prioritizes mobile-friendly pages)
- 25 new Naver tests (21 → 46), total 2491 → 2516

### Changed
- `analyze_naver_seo` now returns 11 result keys (was 7), covers 6 new analysis dimensions
- Naver score calculation incorporates X-Robots-Tag, viewport, crawl-delay, and meta description checks

## [1.5.0] - 2026-05-18

### Added
- In-memory TTL cache (5min) in `fetch_page.py` — eliminates duplicate HTTP requests across analysis modules
- Concurrent bot comparison (`fetch_with_bot_comparison`) via ThreadPoolExecutor — ~5x speedup
- Word boundary regex for AI brand mention detection — prevents false positives (e.g. "claude" no longer matches "include")
- Korean-aware content unit counting (`_count_content_units`) — character-based for Korean, word-based for English
- Expanded recommendation keywords: +8 Korean ("적합", "권장", "강추", etc.) and +5 English terms

### Fixed
- `analyze_korean_content` total_chars now excludes whitespace for accurate korean_ratio
- `analyze_content_depth` word count was inaccurate for Korean (split() undercounts spaceless Korean text)
- `detect_commodity_content` data_density now uses Korean-aware content units

## [1.4.0] - 2026-05-18

### Added
- CLI entrypoint: `python3 -m scripts [command]` unified interface for all modules
- HTML dashboard report generator (`report_html.py`) with SVG score gauges, trend charts, findings table, action plan
- `cli.py` routing module with command/subcommand dispatch for seo/geo/aao modules
- 56 new tests (test_main.py + test_report_html.py), total 2432 → 2488

## [1.3.0] - 2026-05-18

### Added
- GitHub Actions CI pipeline (Python 3.9/3.11/3.12 matrix)
- Ruff linter integration with CI enforcement
- mypy type checking on 6 core modules (validate_url, config, fetch_page, db_manager, score_calculator, report_generator)
- Codecov coverage reporting (80%+ coverage)
- Integration smoke tests (16 tests across 7 pipelines)
- Pre-commit hooks (ruff + mypy)
- `requirements-dev.txt` with dev dependencies
- `pyproject.toml` with unified tool configuration
- CI/Codecov/Ruff badges in README

### Changed
- `requirements.txt` trimmed to actual imports (httpx, fpdf2)
- `.gitignore` expanded with coverage/cache artifacts
- Fixed 133 lint issues across scripts and tests (unused imports, ambiguous variables, duplicate dict keys)
- Fixed duplicate `mobile_readiness` key in report_pdf.py (`mobile_conversion` for AAO context)

## [1.2.0] - 2026-05-18

### Added
- Comprehensive test suite: 191 → 2431 tests (+2240)
- Test coverage for all 47 Python scripts in `scripts/`
- Test files: 50 test modules covering SEO, GEO, AAO, cross-cutting, and core utilities

### Test suites added (chronological)
- score_calculator, geo_score, db_manager, geo_llms_txt
- recommendations, seo_robots, aao_entity
- geo_audit, aao_data, aao_scenario, geo_mentions
- geo_visibility, geo_technical, seo_page, three_o_dashboard
- seo_indexing, seo_cwv, three_o_drift, three_o_report
- seo_drift, three_o_plan, aao_audit, geo_drift
- seo_naver, seo_schema, report_generator, seo_sitemap
- seo_competitor, seo_keywords, fetch_page, config

## [1.1.0] - 2026-05-17

### Added
- Schema auto-generation: industry-aware JSON-LD from page content
- Content rewrite suggestion engine for AI citability optimization
- Multi-dimensional competitor benchmarking with gap analysis
- Dimension-level drift detection with velocity tracking and cross-pillar correlation
- E-E-A-T content quality: 4-axis independent scoring system
- GEO entity recognition: 4-dimension quality scoring
- AAO conversion funnel: 6-dimension quality scoring
- GEO sentiment: 5-dimension scoring with confidence tracking
- Business audience report mode with Korean plain-language output
- Korean translations for recommendation titles, details, and effort labels
- Agency, real estate, franchise industry detection with disambiguation

### Changed
- Improved scoring precision: balance penalty, partial GEO, confidence tracking
- Improved SEO technical: meta quality scoring, heading/image/link analysis
- Improved AAO selectability: industry detection, signal correlation
- Enhanced 5 analysis modules with multi-dimensional quality scoring

## [1.0.0] - 2026-05-16

### Added
- Initial release: Three-O SEO + GEO + AAO unified optimization plugin
- 32 skills across three pillars (SEO 10, GEO 9, AAO 8, cross-cutting 5)
- 24 subagents for parallel analysis
- 42 Python execution scripts
- Platform-specific GEO scoring (ChatGPT, Perplexity, Gemini, Claude)
- GEO citability and platform scoring
- Recommendation engine with prioritized action plans
- Three-O Score (0-100): SEO 35% + GEO 35% + AAO 30%
- Industry-specific adjustments for Korean market
- Korean market context: Naver vs Google dynamics
- Quality gates: INP (not FID), character-based Korean length analysis
- SSRF-protected URL validation
- SQLite baseline and drift storage
- PDF, Markdown, and JSON report generation
- MIT License

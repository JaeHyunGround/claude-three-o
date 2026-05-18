# Changelog

All notable changes to Claude Three-O are documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

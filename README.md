# Claude Three-O - SEO + GEO + AAO Unified Optimization Plugin

Unified search and AI visibility optimization plugin for Claude Code. Three pillars — SEO, GEO, and AAO — analyzed in parallel with a single score (0-100) and prioritized action plan.

[![Claude Code Plugin](https://img.shields.io/badge/Claude%20Code-Plugin-blue)](https://claude.ai/claude-code)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-green)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **Three-O** = **SEO** (Search Engine) + **GEO** (Generative Engine) + **AAO** (Assistive Agent)
>
> Built for the Korean market by [SKYVENTURES](https://www.skyventures.co.kr/)

[한국어 README](README.ko.md)

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Commands](#commands)
- [Scoring System](#scoring-system)
- [Architecture](#architecture)
- [Output Formats](#output-formats)
- [Requirements](#requirements)

## Installation

### Plugin Install (Claude Code 1.0.33+)

```bash
/plugin install claude-three-o
```

### Manual Install

```bash
git clone https://github.com/skyventures/claude-three-o.git
cd claude-three-o && bash install.sh
```

## Quick Start

```bash
# Full 3-pillar audit
/three-o audit https://example.com

# Individual pillar
/three-o seo audit https://example.com
/three-o geo audit "Brand Name"
/three-o aao audit https://example.com

# Generate PDF report
/three-o report full --format pdf
```

## Commands

### Main Commands

| Command | Description |
|---------|-------------|
| `/three-o audit <url>` | Full 3-pillar audit (SEO + GEO + AAO parallel) |
| `/three-o report [type]` | Unified report (md / json / pdf) |
| `/three-o plan <business>` | Strategic optimization plan with timeline |
| `/three-o competitor <u1> <u2>` | Cross-pillar competitor benchmarking |
| `/three-o dashboard` | Dashboard data export |
| `/three-o setup` | API key configuration wizard |

### SEO Module

| Command | Description |
|---------|-------------|
| `/three-o seo audit <url>` | Full SEO analysis |
| `/three-o seo technical <url>` | Technical SEO (meta, security, mobile, speed) |
| `/three-o seo naver <url>` | Naver-specific SEO (Smart Store, Place) |
| `/three-o seo content <url>` | Content quality and E-E-A-T signals |
| `/three-o seo schema <url>` | Schema.org structured data audit |
| `/three-o seo images <url>` | Image optimization analysis |
| `/three-o seo drift baseline <url>` | Capture SEO baseline for monitoring |
| `/three-o seo drift compare <url>` | Detect changes from baseline |

### GEO Module

| Command | Description |
|---------|-------------|
| `/three-o geo audit <brand>` | Full GEO analysis (all dimensions) |
| `/three-o geo mentions <brand>` | AI platform mention tracking |
| `/three-o geo context <brand>` | Context quality and sentiment analysis |
| `/three-o geo citability <url>` | Passage-level AI citation readiness |
| `/three-o geo entity <brand>` | Knowledge graph entity presence |
| `/three-o geo visibility <brand>` | Position ranking in AI responses |
| `/three-o geo technical <url>` | AI crawler accessibility |
| `/three-o geo llms-txt <url>` | llms.txt validation and generation |
| `/three-o geo platforms <brand>` | Platform-specific analysis (ChatGPT, Perplexity, Gemini, Claude) |
| `/three-o geo drift <brand>` | GEO drift detection over time |

### AAO Module

| Command | Description |
|---------|-------------|
| `/three-o aao audit <url>` | Full AAO analysis |
| `/three-o aao selectability <url>` | Agent selectability signals (6 dimensions) |
| `/three-o aao conversion <url>` | Conversion funnel analysis |
| `/three-o aao data <url>` | Structured data with action schema detection |
| `/three-o aao rendering <url>` | SSR, JS dependency, semantic HTML |
| `/three-o aao entity <url>` | NAP consistency + sameAs linking |
| `/three-o aao feed <url>` | Product feed validation (Google Merchant / Naver EP) |
| `/three-o aao scenario <url>` | Agent scenario testing by industry |

## Scoring System

### Three-O Score (0-100)

```
Three-O Score = SEO (35%) + GEO (35%) + AAO (30%)
```

| Grade | Score | Meaning |
|-------|-------|---------|
| A+ | 90-100 | Excellent across all pillars |
| A | 80-89 | Strong with minor gaps |
| B+ | 70-79 | Good foundation, room for improvement |
| B | 60-69 | Average, significant gaps |
| C+ | 50-59 | Below average, action needed |
| C | 40-49 | Poor, major issues |
| D | 20-39 | Very poor visibility |
| F | 0-19 | Minimal presence |

### SEO Score
Technical + Content + On-Page + Schema + Performance + AI Readiness + Images

### GEO Score (Geometric Mean)
```
GEO = geometric_mean(MF^0.30 x CQ^0.25 x VR^0.20 x EP^0.15 x TA^0.10)
```
- **MF** (30%): Mention Frequency across AI platforms
- **CQ** (25%): Context Quality and accuracy
- **VR** (20%): Visibility Ranking position
- **EP** (15%): Entity Presence in knowledge graphs
- **TA** (10%): Technical Accessibility for AI crawlers

### AAO Score
Selectability + Conversion Readiness + Structured Data + Rendering + Entity Consistency

### Industry-Specific Adjustments (Korean Market)

| Industry | Adjustment |
|----------|-----------|
| E-commerce (Smart Store) | AAO +10% |
| Franchise HQ | GEO +5%, AAO +5% |
| Academy / Education | GEO +10% |
| Clinic / Healthcare | GEO +10% |
| Restaurant | SEO +5% (Naver Place) |

## Architecture

```
claude-three-o/
  .claude-plugin/
    plugin.json              # Plugin manifest
    marketplace.json         # Marketplace catalog
  skills/                    # 32 skills
    three-o/                 # Main orchestrator
    seo-*/                   # SEO module (10 skills)
    geo-*/                   # GEO module (9 skills)
    aao-*/                   # AAO module (8 skills)
    three-o-*/               # Cross-cutting (4 skills)
  agents/                    # 24 subagents
  hooks/                     # Quality gate hooks (3)
  scripts/                   # 42 Python scripts
  schema/                    # Schema.org JSON-LD templates
  tests/                     # Test suite (41 tests)
  reports/                   # Generated reports (gitignored)
```

### Quality Gate Hooks

| Hook | Purpose |
|------|---------|
| `validate_quality.py` | INP (not FID), no HowTo, FAQ gov/health only, no hardcoded paths |
| `check_cwv.py` | Core Web Vitals terminology validation |
| `check_schema.py` | Schema recommendation rules enforcement |

## Output Formats

| Format | Command | Use Case |
|--------|---------|----------|
| Terminal | (default) | Quick analysis with color-coded bars |
| JSON | `--json` | API integration, data pipeline |
| Markdown | `--format md` | Documentation, PR descriptions |
| PDF | `--format pdf` | Client deliverables, presentations |

### PDF Report Features
- Korean text support (AppleGothic / NanumGothic)
- Color-coded score visualizations
- 6-page structure: Title, Executive Summary, SEO, GEO, AAO, Action Plan
- Priority-ordered action table (P0/P1/P2)
- SKYVENTURES branding

## Requirements

- Python 3.9+
- Claude Code CLI
- `httpx` (HTTP client)
- `fpdf2` (PDF generation)
- Optional: API keys for live AI platform data

## License

MIT License

---

Built by [SKYVENTURES](https://www.skyventures.co.kr/) | Powered by Claude Code

# Claude Three-O - SEO + GEO + AAO Unified Optimization Plugin

Unified search and AI visibility optimization plugin for Claude Code. Three pillars — SEO, GEO, and AAO — analyzed in parallel with a single score (0-100) and prioritized action plan.

[![Claude Code Plugin](https://img.shields.io/badge/Claude%20Code-Plugin-blue)](https://claude.ai/claude-code)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-green)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **Three-O** = **SEO** (Search Engine) + **GEO** (Generative Engine) + **AAO** (Assistive Agent)
>
> Built for the Korean market by [JaeHyunGround](https://github.com/JaeHyunGround)

[한국어 README](README.ko.md)

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Commands](#commands)
- [Scoring System](#scoring-system)
- [Architecture](#architecture)
- [Output Formats](#output-formats)
- [Analysis Accuracy](#analysis-accuracy)
- [Requirements](#requirements)

## Installation

### Plugin Install (Claude Code 1.0.33+)

```bash
/plugin install claude-three-o
```

### Manual Install

```bash
git clone https://github.com/JaeHyunGround/claude-three-o.git
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
| `/three-o seo schema generate <url>` | Auto-generate JSON-LD from page content |
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
| `/three-o geo rewrite <url>` | Content rewrite suggestions for AI citability |

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
Three-O Score = (SEO × 35% + GEO × 35% + AAO × 30%) × balance_penalty
```

The balance penalty (0.85–1.0) penalizes imbalanced profiles — a site with SEO 90 but GEO 10 scores lower than pure weighted average. Confidence score (0–1.0) indicates data availability.

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
Technical (meta quality + security + mobile + headings + images + performance) + Content + On-Page + Schema + AI Readiness

Key features:
- **Meta quality evaluation**: not just presence but optimal length (title 30-60, desc 120-160), protocol consistency, duplication detection
- **Heading hierarchy validation**: single H1, proper H2→H3 nesting
- **Image alt coverage**: percentage-based scoring
- **Weighted section scoring**: meta_quality 30%, security 15%, mobile 15%, headings 15%, images 10%, performance 15%

### GEO Score (Geometric Mean)
```
GEO = geometric_mean(MF^0.30 x CQ^0.25 x VR^0.20 x EP^0.15 x TA^0.10)
```
- **MF** (30%): Mention Frequency across AI platforms
- **CQ** (25%): Context Quality and accuracy
- **VR** (20%): Visibility Ranking position
- **EP** (15%): Entity Presence in knowledge graphs
- **TA** (10%): Technical Accessibility for AI crawlers

**Partial scoring**: Dimensions requiring API keys (MF, VR) are excluded when unavailable — remaining dimensions' weights are redistributed. Confidence score tracks data completeness.

**Platform-specific GEO**: Each AI platform (ChatGPT, Perplexity, Gemini, Claude) gets an individual GEO score based on its citation preferences:
- **ChatGPT**: definition sentences, concise paragraphs (80-300 chars), FAQ, freshness
- **Perplexity**: source attribution, data density, recency, outbound references
- **Gemini**: E-E-A-T signals, tables, comparison content, knowledge graph connectivity
- **Claude**: content depth, data-backed claims, nuance, research references

### AAO Score
Selectability (industry-weighted) + Conversion Readiness + Structured Data + Rendering + Entity Consistency

**Selectability dimensions**: structured_data (25%) + reviews_ratings (20%) + info_completeness (20%) + api_booking (15%) + trust_signals (10%) + freshness (10%)

Key features:
- **Industry auto-detection**: restaurant, ecommerce, clinic, hotel, education, saas → weight adjustment
- **Signal correlation**: cross-dimension bonuses (e.g., schema + reviews = +8) and penalties
- **Cross-validation**: schema claims verified against actual page content
- **Quality scoring**: not just presence/absence, but quality assessment per field

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
  scripts/                   # 45 Python scripts
  schema/                    # Schema.org JSON-LD templates (8 industry types)
  tests/                     # Test suite (674 tests)
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
- JaeHyunGround branding

## Analysis Accuracy

Three-O prioritizes realistic scoring over inflated numbers. Key accuracy mechanisms:

| Module | Mechanism | Effect |
|--------|-----------|--------|
| GEO Citability | AI citation pattern detection (definition, comparison, step, causal) | Identifies passages most likely to be cited |
| GEO Citability | Self-containment scoring | Penalizes context-dependent passages |
| GEO Entity | 4-dimension entity scoring | Schema presence, connection strength, attribute completeness, disambiguation |
| GEO Entity | Tiered sameAs verification | Knowledge (Wikidata/Wikipedia) > Authority (LinkedIn/Naver) > Social platforms |
| GEO Entity | Type-aware attribute completeness | Per-entity-type required fields (Restaurant ≠ Organization ≠ Hotel) |
| GEO Entity | Disambiguation signal detection | Business registration, founding year, CEO, location qualifier, generic name penalty |
| GEO Platforms | Differentiated per-platform criteria | Each AI platform scored by its actual preferences |
| SEO Content | 4-axis E-E-A-T quality scoring | Experience, Expertise, Authoritativeness, Trust scored independently (0-100) |
| SEO Content | Korean + English signal detection | Bilingual regex patterns per axis (5+6+7+8 signal categories) |
| SEO Content | Weighted content score | depth_score × 0.4 + eeat_score × 0.6 with axis-level diagnostics |
| SEO Technical | Meta quality evaluation (not binary) | Title length, desc length, canonical protocol check |
| SEO Technical | Weighted multi-section scoring | 6 sub-dimensions with configurable weights |
| AAO Conversion | 6-dimension funnel scoring | CTA quality, form accessibility, flow completeness, mobile, deep link, confirmation |
| AAO Conversion | CTA quality assessment | Specific vs generic CTA detection, schema action, urgency, ARIA roles |
| AAO Conversion | Mobile conversion optimization | Viewport, click-to-call/map, touch targets, SNS login, sticky CTA |
| AAO Conversion | Deep link & app integration | iOS universal links, Android intents, custom schemes, API endpoints |
| AAO Conversion | Payment path depth analysis | Price visibility, payment methods, secure checkout, refund policy |
| AAO Selectability | Industry auto-detection + weight adjustment | Restaurant ≠ SaaS ≠ Clinic scoring |
| AAO Selectability | Signal correlation bonuses/penalties | Schema + reviews = synergy bonus |
| AAO Selectability | Cross-validation | Schema claims verified against page content |
| Three-O Score | Balance penalty | Imbalanced pillar profiles penalized (0.85-1.0) |
| GEO Score | Partial dimension support | Unavailable dimensions excluded, weights redistributed |
| Drift Detection | SEO dimension-level tracking | Meta, headings, images, schema, performance changes with severity |
| Drift Detection | Velocity + acceleration | Score change rate per snapshot with trend classification |
| Drift Detection | Cross-pillar correlation alerts | Multi-pillar decline, single-pillar isolation, divergence detection |
| Competitor Benchmark | Multi-dimensional gap analysis | Per-dimension scoring across 16 dimensions (SEO 5 + GEO 5 + AAO 6) |
| Competitor Benchmark | Prioritized action plan | P0/P1/maintain based on gap severity with Korean recommendations |
| Competitor Benchmark | Competitive positioning | Radar chart data with market averages per dimension |
| Content Rewrite | Weakness analysis per passage | Detects vague language, filler, weak openers, low factual density |
| Content Rewrite | Strategy-based rewrite suggestions | Definition, comparison, data, causal patterns with templates |
| Content Rewrite | Platform-specific tips | Per-platform (ChatGPT, Perplexity, Gemini, Claude) optimization tips |
| Schema Generator | Industry auto-detection + template selection | Restaurant, clinic, hotel, ecommerce, education, SaaS templates |
| Schema Generator | HTML content extraction | Extracts name, phone, address, hours, prices, ratings, social links |
| Schema Generator | Coverage scoring + suggestions | Identifies missing fields with impact-based improvement tips |
| All Scores | Confidence tracking | Data availability (0-1.0) per computation |

## Requirements

- Python 3.9+
- Claude Code CLI
- `httpx` (HTTP client)
- `fpdf2` (PDF generation)
- Optional: API keys for live AI platform data

## License

MIT License

---

Built by [JaeHyunGround](https://github.com/JaeHyunGround) | Powered by Claude Code

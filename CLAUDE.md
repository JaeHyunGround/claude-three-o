# Claude Three-O: SEO + GEO + AAO Unified Optimization Plugin

## Project Overview

This repository contains **Claude Three-O**, a Claude Code plugin for unified search and AI visibility optimization by JaeHyunGround. It integrates three optimization pillars into a single platform:

- **SEO** (Search Engine Optimization): Google + Naver dual-engine keyword tracking, technical SEO, content quality
- **GEO** (Generative Engine Optimization): AI brand mention tracking across ChatGPT, Perplexity, Gemini, Claude
- **AAO** (Assistive Agent Optimization): Agent selectability, conversion funnels, structured data push

## Architecture

```
claude-three-o/
  CLAUDE.md                          # Project instructions (this file)
  .claude-plugin/
    plugin.json                      # Plugin manifest (v1.0.0)
    marketplace.json                 # Marketplace catalog
  skills/                            # 32 skills (auto-discovered)
    three-o/                         # Main orchestrator
    seo-*/                           # SEO module (10 skills)
    geo-*/                           # GEO module (9 skills)
    aao-*/                           # AAO module (8 skills)
    three-o-*/                       # Cross-cutting (4 skills)
  agents/                            # 24 subagents
    seo-*.md                         # SEO agents (9)
    geo-*.md                         # GEO agents (7)
    aao-*.md                         # AAO agents (5)
    three-o-*.md                     # Cross-cutting agents (3)
  hooks/                             # Quality gate hooks
    hooks.json                       # PostToolUse validation
  scripts/                           # 42 Python execution scripts
  schema/                            # Schema.org JSON-LD templates
  extensions/                        # External service integrations
  docs/                              # Extended documentation
  tests/                             # Test suite
```

## Command Structure

Main entry point: `/three-o [module] [command] [args]`

### Top-Level Commands
| Command | Description |
|---------|-------------|
| `/three-o audit <url>` | Full 3-pillar audit (SEO + GEO + AAO parallel) |
| `/three-o seo [cmd] <url>` | SEO module |
| `/three-o geo [cmd] <brand>` | GEO module |
| `/three-o aao [cmd] <url>` | AAO module |
| `/three-o report [type]` | Unified report generation |
| `/three-o plan <business>` | Strategic planning |
| `/three-o competitor <u1> <u2>` | Cross-pillar competitor benchmarking |
| `/three-o dashboard` | Dashboard data export |
| `/three-o setup` | API key configuration wizard |

## Scoring System

### Three-O Score (0-100)
- **SEO Score** (35%): Technical + Content + On-Page + Schema + Performance + AI Readiness + Images
- **GEO Score** (35%): Mention Frequency + Context Quality + Visibility Ranking + Entity Presence + Technical Accessibility
- **AAO Score** (30%): Selectability + Conversion Readiness + Structured Data + Rendering + Entity Consistency

### Industry-Specific Adjustments (Korean Market)
- E-commerce (Smart Store): AAO +10%
- Franchise HQ: GEO +5%, AAO +5%
- Academy/Education: GEO +10%
- Clinic/Healthcare: GEO +10%
- Restaurant: SEO +5% (Naver Place)

## Development Rules

### File Conventions
- SKILL.md: Max 500 lines / 5000 tokens
- Reference files: Max 200 lines, on-demand loading
- Skills: kebab-case (e.g., `seo-naver`)
- Agents: kebab-case (e.g., `geo-mentions`)
- Scripts: snake_case (e.g., `naver_search_advisor.py`)

### Script Standards
- All scripts require docstrings and argparse CLI interface
- JSON output via `--json` flag
- URL validation via `validate_url()` before any API calls (SSRF protection)
- Config stored at `~/.config/three-o/`, never in repo
- No hardcoded paths: use `os.path.dirname(os.path.abspath(__file__))`

### Quality Gates
- All Core Web Vitals references use INP, never FID
- Never recommend HowTo schema (deprecated Sept 2023)
- FAQ schema: government and healthcare sites only (Aug 2023 restriction)
- Korean content analysis must account for byte vs character length differences

### Security
- Never commit: `.env`, `client_secret*.json`, `oauth-token.json`, `service_account*.json`
- All URLs validated before API calls
- OAuth tokens never stored with client_secret

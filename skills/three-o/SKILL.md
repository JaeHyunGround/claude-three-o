---
name: three-o
description: >
  Three-O unified SEO + GEO + AAO optimization platform.
  Full site audits across search engines (Google, Naver) and AI platforms
  (ChatGPT, Perplexity, Gemini, Claude). Keyword tracking, AI brand mention
  monitoring, agent selectability scoring, conversion funnel optimization,
  and structured data management.
  Use when user says "three-o", "쓰리오", "SEO audit", "GEO score",
  "AAO", "AI visibility", "brand mentions", "agent optimization",
  "naver seo", "네이버 최적화", "AI 노출", "에이전트 선택 최적화".
user-invocable: true
argument-hint: "[module] [command] [url|brand]"
license: proprietary
metadata:
  author: Jaehyun Ahn
  version: "1.0.0"
  category: three-o
---

# Three-O: Unified SEO + GEO + AAO Optimization

**Invocation:** `/three-o $1 $2 $3` where `$1` is the module/command, `$2` is the sub-command, `$3` is the URL or brand.

Orchestrates 32 specialized sub-skills and 24 subagents across three optimization pillars: SEO (Search Engine Optimization), GEO (Generative Engine Optimization), and AAO (Assistive Agent Optimization).

## Quick Reference

| Command | What it does |
|---------|-------------|
| `/three-o audit <url>` | Full 3-pillar audit (SEO + GEO + AAO in parallel) |
| `/three-o seo [command] <url>` | SEO module commands |
| `/three-o geo [command] <brand>` | GEO module commands |
| `/three-o aao [command] <url>` | AAO module commands |
| `/three-o report [full\|seo\|geo\|aao]` | Unified report generation |
| `/three-o plan <business-type>` | Strategic planning (90-day roadmap) |
| `/three-o competitor <url1> <url2>` | Cross-pillar competitor benchmarking |
| `/three-o dashboard` | Dashboard data export (JSON) |
| `/three-o setup` | API key configuration wizard |

## SEO Sub-Commands

| Command | What it does |
|---------|-------------|
| `/three-o seo audit <url>` | Full site SEO audit (Google + Naver dual-engine) |
| `/three-o seo page <url>` | Deep single-page analysis |
| `/three-o seo technical <url>` | Technical SEO (9 categories + Naver-specific) |
| `/three-o seo content <url>` | E-E-A-T + Korean content quality |
| `/three-o seo keywords <keyword>` | Keyword ranking tracker (Google + Naver) |
| `/three-o seo competitor <url>` | Competitor keyword gap analysis |
| `/three-o seo naver <url>` | Naver-specific SEO (Search Advisor, Blog, Place, Smart Store) |
| `/three-o seo schema <url>` | Schema.org markup detection/validation/generation |
| `/three-o seo indexing <url>` | Crawling/indexing error detection + IndexNow |
| `/three-o seo drift [baseline\|compare] <url>` | SEO drift monitoring |

## GEO Sub-Commands

| Command | What it does |
|---------|-------------|
| `/three-o geo audit <brand>` | Full GEO analysis across all AI platforms |
| `/three-o geo mentions <brand>` | AI brand mention tracking (ChatGPT/Perplexity/Gemini/Claude) |
| `/three-o geo score <brand>` | GEO Score calculation |
| `/three-o geo context <brand>` | Query-type mapping analysis |
| `/three-o geo sentiment <brand>` | Sentiment analysis of AI mentions |
| `/three-o geo citability <url>` | Passage-level citability scoring |
| `/three-o geo entity <brand>` | Entity & knowledge graph optimization |
| `/three-o geo llms-txt <url>` | llms.txt compliance and generation |
| `/three-o geo drift [baseline\|compare] <brand>` | GEO drift monitoring |

## AAO Sub-Commands

| Command | What it does |
|---------|-------------|
| `/three-o aao audit <url>` | Full AAO analysis |
| `/three-o aao selectability <brand>` | Agent selection optimization scoring |
| `/three-o aao conversion <url>` | Conversion funnel optimization |
| `/three-o aao data <url>` | Structured data integration audit |
| `/three-o aao rendering <url>` | SSR/rendering check for AI accessibility |
| `/three-o aao entity <brand>` | Brand entity consistency check |
| `/three-o aao feed <url>` | Product feed validation (Google Merchant + Naver) |
| `/three-o aao scenario <brand>` | Conversational scenario design |

## Orchestration Logic

### Full Audit (`/three-o audit <url>`)

1. Detect business type via `references/industry-detection.md`
2. Spawn SEO agents in parallel: seo-technical, seo-content, seo-schema, seo-performance, seo-visual
3. Spawn GEO agents in parallel: geo-mentions, geo-citability, geo-entity
4. Spawn AAO agents in parallel: aao-selectability, aao-structured-data, aao-rendering
5. Conditional agents:
   - If Naver domain or Korean content detected → spawn seo-naver
   - If Google API credentials detected → spawn seo-indexing with GSC data
   - If e-commerce detected → spawn aao-product-feed (product feed validation)
   - If existing drift baseline found → spawn seo-drift and geo-drift
6. Collect all agent results
7. Compute unified Three-O Score per `references/scoring-methodology.md`
8. Generate prioritized action plan (Critical → High → Medium → Low)
9. Offer report: "Generate PDF report? Use `/three-o report full`"

### Module Routing

For individual module commands, load the relevant sub-skill directly:
- `/three-o seo *` → route to `seo-*` skill
- `/three-o geo *` → route to `geo-*` skill
- `/three-o aao *` → route to `aao-*` skill

## Industry Detection (Korean Market)

Detect business type from homepage signals. Load `references/industry-detection.md` for full rules.

| Type | Detection Signals |
|------|-------------------|
| Franchise HQ | Multiple branch pages, /stores, /locations, franchise FAQ |
| Academy/Education | /courses, /curriculum, class schedule, instructor profiles |
| Clinic/Healthcare | Doctor profiles, /departments, appointment booking, medical terms |
| Restaurant/F&B | Menu page, /reservation, Naver Place embed, food images |
| E-commerce | /products, /cart, product schema, Naver Smart Store link |
| Real Estate | /listings, property search, /map, area guides |
| SaaS | /pricing, /features, /docs, free trial CTA |
| Agency | /portfolio, /case-studies, client logos |

## Scoring

Load `references/scoring-methodology.md` for full scoring weights.

**Three-O Score (0-100):**
- SEO Score × 0.35
- GEO Score × 0.35
- AAO Score × 0.30

Apply industry-specific adjustments per `references/korean-market-context.md`.

## Output Format

All analysis results follow this priority structure:
- **Critical**: Immediate action required (broken indexing, zero AI mentions, JS-only rendering)
- **High**: Address within 1 week (missing schema, negative AI sentiment, poor selectability)
- **Medium**: Address within 1 month (content gaps, suboptimal feed structure)
- **Low**: Nice-to-have improvements (additional entity linking, scenario expansion)

## Quality Gates

Load `references/quality-gates.md` for content thresholds.
- Never recommend HowTo schema (deprecated Sept 2023)
- FAQ schema: government/healthcare only (Aug 2023)
- Core Web Vitals: always INP, never FID
- Korean content: character-based length analysis, not byte-based

## Reference Files

Load on-demand as needed:
- `references/scoring-methodology.md` — Three-O Score weights and computation
- `references/industry-detection.md` — Korean industry classification rules
- `references/quality-gates.md` — Content thresholds per page type
- `references/korean-market-context.md` — Naver vs Google market dynamics

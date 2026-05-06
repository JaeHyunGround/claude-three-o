---
name: aao-rendering
description: >
  Checks SSR/rendering compatibility for AI agent and crawler access.
  Verifies that key content is accessible without JavaScript execution.
  Use when user says "rendering check", "렌더링 체크", "SSR audit",
  "SSR 감사", "AI accessibility", "AI 접근성 체크".
user-invocable: true
argument-hint: "<url> [--pages <count>]"
license: proprietary
metadata:
  author: Jaehyun Ahn
  version: "1.0.0"
  category: aao
---

# AAO Rendering: AI Accessibility Check

**Invocation:** `/three-o aao rendering <url> [--pages <count>]`

## Purpose

AI agents and crawlers access web content differently from browsers.
Many sites rely heavily on client-side JavaScript rendering, making
content invisible to AI platforms. This skill identifies rendering
gaps that prevent AI agents from accessing critical information.

## Analysis Method

1. **Static fetch** — GET request without JS execution (what AI crawlers see)
2. **Rendered fetch** — Full browser rendering via Playwright
3. **Compare** — Identify content only available after JS execution
4. **Score** — Rate accessibility for AI consumption

## Checks Performed

| Check | Weight | Description |
|-------|--------|-------------|
| HTML content ratio | 25% | % of meaningful content in static HTML |
| Key data in source | 25% | Price, name, hours visible without JS |
| JSON-LD in source | 20% | Structured data in initial HTML |
| Meta tags present | 15% | Title, description, OG in static |
| Navigation accessible | 15% | Links discoverable without JS |

## Content Comparison

For each page, compare static vs rendered:

| Element | Static HTML | After JS | Gap? |
|---------|-------------|----------|------|
| Product name | ✓/✗ | ✓ | yes/no |
| Price | ✓/✗ | ✓ | yes/no |
| Description | ✓/✗ | ✓ | yes/no |
| Images | ✓/✗ | ✓ | yes/no |
| Reviews | ✓/✗ | ✓ | yes/no |
| Contact info | ✓/✗ | ✓ | yes/no |

## Bot Access Check

Verify these user-agents are not blocked:
- `GPTBot` (OpenAI)
- `Anthropic-AI` (Anthropic)
- `Google-Extended` (Google AI)
- `PerplexityBot` (Perplexity)
- `Googlebot` (baseline SEO)

## Framework-Specific Issues

| Framework | Common Issue | Fix |
|-----------|-------------|-----|
| React SPA | All content in JS bundles | Implement SSR/SSG (Next.js) |
| Vue SPA | Dynamic routes invisible | Nuxt.js SSR or prerendering |
| Angular | Heavy JS dependency | Angular Universal SSR |
| WordPress + Ajax | Lazy-loaded content | Ensure above-fold in HTML |
| Shopify | Some apps inject via JS | Check Liquid template output |

## Output Format

```
Rendering Analysis: [url]
━━━━━━━━━━━━━━━━━━━━━━━━
Rendering Score: XX/100
Pages Checked: XX

Content Accessibility:
  Static HTML content: XX% of total
  JS-dependent content: XX% (gap)
  JSON-LD in source: [✓/✗]
  Meta tags complete: [✓/✗]

Bot Access:
  GPTBot: [allowed/blocked]
  Anthropic-AI: [allowed/blocked]
  Google-Extended: [allowed/blocked]
  PerplexityBot: [allowed/blocked]

Critical Gaps:
  [page] — [element] only visible after JS
  ...

Framework: [detected]
Recommendation: [SSR implementation advice]
```

---
name: geo-llms-txt
description: >
  Validates and generates llms.txt files for AI crawler accessibility.
  Checks compliance with the llms.txt specification, content structure,
  and accessibility for AI platforms.
  Use when user says "llms.txt", "llms txt", "AI crawler",
  "AI 크롤러", "llms-txt check", "AI 접근성".
user-invocable: true
argument-hint: "<url>"
license: proprietary
metadata:
  author: Jaehyun Ahn
  version: "1.0.0"
  category: geo
---

# GEO llms.txt: AI Crawler Accessibility

**Invocation:** `/three-o geo llms-txt <url>`

## Purpose

`llms.txt` is a proposed standard for websites to provide AI-friendly
content summaries. Similar to robots.txt but designed to help LLMs
understand site content, key pages, and preferred citation format.

## Validation Checks

### File Presence
1. Check `{domain}/llms.txt` exists
2. Check `{domain}/.well-known/llms.txt` (alternate location)
3. Verify HTTP 200 response with text/plain content type

### Content Compliance

| Field | Required | Description |
|-------|----------|-------------|
| # Title | Yes | Site/brand name |
| > Description | Yes | One-line site description |
| ## Sections | Yes | At least one section |
| - Links | Yes | Markdown links to key pages |
| Optional: metadata | No | Contact, update frequency |

### Structure Quality
- Clear hierarchical organization
- Key pages accessible (not 404, not login-gated)
- Descriptions are informative (not just page titles)
- Covers main products/services
- Includes Korean content pages (for Korean sites)

## Generation Mode

If no llms.txt exists, generate one by:
1. Crawl site structure (max 50 pages)
2. Identify key pages: homepage, about, products/services, pricing, contact
3. Extract page descriptions from meta tags or first paragraph
4. Organize by section
5. Output llms.txt compliant file

## llms-full.txt Check

Also check for extended version:
- `{domain}/llms-full.txt` — Full content dump for AI training
- Validates Markdown formatting
- Checks content completeness vs sitemap

## Output Format

```
llms.txt Analysis: [url]
━━━━━━━━━━━━━━━━━━━━━━━━
Status: [Present ✓ / Missing ✗]
Location: [/llms.txt or /.well-known/llms.txt]

Compliance Score: XX/100
  Title present:       [✓/✗]
  Description present: [✓/✗]
  Sections defined:    [✓/✗] (XX sections)
  Links valid:         XX/XX accessible
  Content quality:     [good/fair/poor]

Issues:
  [issue description and fix]
  ...

[If missing: Generated llms.txt proposal below]
```

## Additional AI Accessibility Checks

Beyond llms.txt, also verify:
- `robots.txt` does not block AI crawlers (GPTBot, Anthropic, Google-Extended)
- Key pages render without JavaScript (SSR check)
- Response time under 3 seconds
- No CAPTCHA or aggressive bot detection on content pages

---
name: seo-page
description: >
  Deep single-page SEO analysis covering on-page elements, content quality,
  schema markup, performance, and internal linking. Korean-aware title and
  meta analysis accounting for character vs byte length differences.
  Use when user says "page analysis", "페이지 분석", "single page SEO",
  "on-page SEO", "페이지 SEO 진단".
user-invocable: true
argument-hint: "<url>"
license: proprietary
metadata:
  author: Jaehyun Ahn
  version: "1.0.0"
  category: seo
---

# SEO Page: Deep Single-Page Analysis

**Invocation:** `/three-o seo page <url>`

## Analysis Dimensions

### 1. Title Tag
- Length: 30 Korean chars / 60 English chars optimal
- Primary keyword presence and position
- Brand inclusion (end position preferred)
- Uniqueness across site

### 2. Meta Description
- Length: 80 Korean chars / 155 English chars optimal
- CTA inclusion and compelling copy
- Keyword presence (natural, not stuffed)

### 3. Heading Structure
- Single H1 with primary keyword
- Logical H2-H6 hierarchy
- Keyword distribution across headings

### 4. Content Analysis
- Word count / character count (Korean-aware)
- Keyword density (morphological variants for Korean)
- Readability score
- E-E-A-T signals (author, credentials, sources, dates)
- Content freshness (last modified date)

### 5. Internal Linking
- Inbound internal links count
- Outbound internal links count
- Anchor text relevance
- Orphan page detection

### 6. Technical Elements
- Canonical tag
- Open Graph / Twitter Card tags
- Mobile viewport
- Page speed (LCP, INP, CLS)
- Image optimization (alt text, format, size)

### 7. Schema Markup
- Detected types and validity
- Missing recommended types for page type
- JSON-LD structure validation

## Output Format

Produce a structured report with score (0-100) and findings grouped by priority.
Each finding includes: issue description, current state, recommendation, impact level.

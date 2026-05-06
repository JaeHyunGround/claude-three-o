---
name: seo-indexing
description: >
  Crawling and indexing error detection for Google and Naver.
  URL inspection, IndexNow push support, sitemap validation,
  and indexing status monitoring.
  Use when user says "indexing", "인덱싱", "crawl errors", "크롤링 오류",
  "index status", "색인 상태", "IndexNow", "sitemap".
user-invocable: true
argument-hint: "<url>"
license: proprietary
metadata:
  author: Jaehyun Ahn
  version: "1.0.0"
  category: seo
---

# SEO Indexing: Crawl & Index Error Detection

**Invocation:** `/three-o seo indexing <url>`

## Sub-Commands

| Command | What it does |
|---------|-------------|
| `/three-o seo indexing <url>` | Full crawl/index audit |
| `/three-o seo indexing inspect <url>` | URL inspection (Google + Naver) |
| `/three-o seo indexing push <url>` | IndexNow push notification |
| `/three-o seo indexing sitemap <url>` | Sitemap validation and analysis |

## Analysis Dimensions

### Crawl Error Detection
- HTTP status code audit (4xx, 5xx errors)
- Redirect chain analysis (max 2 hops recommended)
- Soft 404 detection
- Crawl budget waste identification
- robots.txt blocking analysis

### Index Status Check
- Google Search Console URL inspection (if API available)
- Naver Search Advisor index status (if API available)
- Meta robots / X-Robots-Tag audit
- Canonical tag consistency
- Noindex page inventory

### Sitemap Analysis
- XML sitemap presence and accessibility
- Sitemap index structure (for large sites)
- URL count vs indexed URL count
- Last modified dates freshness
- Sitemap submission status (Google + Naver)

### IndexNow Integration
- IndexNow key file detection
- Push notification to supported engines: Bing, Yandex, Naver
- Bulk URL submission support
- Response status tracking

## Workflow

1. Fetch robots.txt and XML sitemap
2. Check Google Search Console data (if available)
3. Check Naver Search Advisor data (if available)
4. Crawl sample pages for status codes and redirect chains
5. Compare sitemap URLs vs actually indexed URLs
6. Identify indexing gaps and recommend fixes
7. Offer IndexNow push for priority pages

## Reference Files

Load on-demand:
- `references/indexnow-protocol.md` — IndexNow setup and usage
- `references/google-indexing-api.md` — Google Indexing API reference

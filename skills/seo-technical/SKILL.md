---
name: seo-technical
description: >
  Technical SEO audit across 9 categories plus Naver-specific checks.
  Crawlability, indexability, HTTPS/security, URL structure, mobile
  optimization, Core Web Vitals (INP), JavaScript rendering, structured
  data, and international/hreflang. Includes Naver robots.txt directives
  and Naver-specific meta tags.
  Use when user says "technical SEO", "기술 SEO", "crawlability",
  "indexability", "site health", "크롤링 진단".
user-invocable: true
argument-hint: "<url>"
license: proprietary
metadata:
  author: Jaehyun Ahn
  version: "1.0.0"
  category: seo
---

# SEO Technical: 9-Category Technical Audit

**Invocation:** `/three-o seo technical <url>`

## Categories

### 1. Crawlability
- robots.txt analysis (Google + Naver directives)
- XML sitemap presence and validity
- Crawl depth analysis (max 3 clicks recommended)
- Internal link structure

### 2. Indexability
- Meta robots / X-Robots-Tag directives
- Canonical tag consistency
- Noindex page audit
- Google Search Console indexing status (if API available)
- Naver Search Advisor indexing status (if API available)

### 3. HTTPS & Security
- SSL certificate validity
- Mixed content detection
- HSTS header presence
- Security headers (CSP, X-Frame-Options, etc.)

### 4. URL Structure
- URL length and readability
- Korean URL encoding handling
- Trailing slash consistency
- Parameter handling and canonical

### 5. Mobile Optimization
- Mobile viewport configuration
- Touch target sizes
- Font size readability
- Mobile-specific usability issues

### 6. Core Web Vitals
- LCP (Largest Contentful Paint): Good <= 2.5s
- INP (Interaction to Next Paint): Good <= 200ms
- CLS (Cumulative Layout Shift): Good <= 0.1
- Use PSI API when available, estimate from HTML otherwise

### 7. JavaScript Rendering
- CSR vs SSR detection
- Critical content accessibility without JS
- JS bundle size analysis
- Render-blocking resources

### 8. Structured Data
- JSON-LD presence and validity
- Required property completeness
- Schema type coverage for page type
- Deprecated schema detection

### 9. Naver-Specific (Korean sites)
- Naver Search Advisor meta verification tag
- Naver-specific robots.txt rules
- Naver sitemap submission status
- Naver Blog/Cafe canonical handling

## Output

Technical SEO Score (0-100) with per-category breakdown and prioritized fixes.

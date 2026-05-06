---
name: seo-naver
description: >
  Naver-specific SEO analysis covering Search Advisor diagnostics,
  Blog ranking optimization, Place (local) optimization, and Smart Store
  product SEO. Essential for Korean market businesses.
  Use when user says "naver seo", "네이버 SEO", "네이버 최적화",
  "naver blog", "네이버 블로그", "naver place", "네이버 플레이스",
  "smart store", "스마트스토어".
user-invocable: true
argument-hint: "<url>"
license: proprietary
metadata:
  author: Jaehyun Ahn
  version: "1.0.0"
  category: seo
---

# SEO Naver: Naver-Specific Optimization

**Invocation:** `/three-o seo naver <url>`

## Sub-Commands

| Command | What it does |
|---------|-------------|
| `/three-o seo naver <url>` | Full Naver SEO audit |
| `/three-o seo naver blog <url>` | Blog ranking analysis |
| `/three-o seo naver place <business>` | Place listing optimization |
| `/three-o seo naver store <url>` | Smart Store product SEO |

## Analysis Dimensions

### 1. Naver Search Advisor (서치어드바이저)
- Site verification status
- Indexing request history and status
- Crawl error detection
- Sitemap submission status
- Robot.txt Naver-specific directives

### 2. Naver Blog Optimization (블로그 최적화)
- Blog post ranking for target keywords
- Post frequency and recency
- Content quality signals (length, images, formatting)
- Blog authority metrics (visitors, subscriber count)
- Optimal posting schedule analysis

### 3. Naver Place (플레이스)
- Listing claim and verification status
- Business information completeness
- Photo count and quality
- Review count, rating, and response rate
- Menu/service information completeness
- Booking/reservation integration
- Competitor comparison in same area

### 4. Naver Smart Store (스마트스토어)
- Product listing completeness
- Category classification accuracy
- Product image quality and count
- Price competitiveness signals
- Review and rating management
- Naver Pay integration status
- Product feed format compliance

## Naver-Specific Recommendations

| Area | Critical Actions |
|------|-----------------|
| Search Advisor | Verify site, submit sitemap, fix crawl errors |
| Blog | Post 2-3x/week with 1500+ char, include images |
| Place | Complete all fields, respond to reviews within 24h |
| Smart Store | Fill all product attributes, maintain 4.5+ rating |

## Reference Files

Load on-demand:
- `references/naver-search-advisor-api.md` — API endpoints and usage
- `references/naver-blog-optimization.md` — Blog ranking best practices
- `references/naver-smart-store.md` — Smart Store feed format
- `references/naver-place.md` — Place optimization checklist

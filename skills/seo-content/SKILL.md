---
name: seo-content
description: >
  Content quality analysis with E-E-A-T evaluation, readability scoring,
  content depth assessment, and Korean morphological keyword analysis.
  Thin content detection with industry-specific thresholds.
  Use when user says "content quality", "콘텐츠 품질", "E-E-A-T",
  "content analysis", "콘텐츠 분석", "thin content".
user-invocable: true
argument-hint: "<url>"
license: proprietary
metadata:
  author: Jaehyun Ahn
  version: "1.0.0"
  category: seo
---

# SEO Content: E-E-A-T & Content Quality Analysis

**Invocation:** `/three-o seo content <url>`

## Analysis Dimensions

### E-E-A-T Evaluation

**Experience:**
- First-person accounts or case studies
- Original photos/videos (not stock)
- Specific examples from direct usage

**Expertise:**
- Author credentials and bios
- Professional certifications (Korean: 의사, 변호사, 세무사, 공인중개사)
- Technical depth appropriate to topic

**Authoritativeness:**
- Domain authority signals
- Industry recognition and awards
- Press coverage (네이버 뉴스 inclusion is strong signal in Korea)
- Government registrations (사업자등록번호)

**Trustworthiness:**
- Contact information completeness
- Privacy policy and terms
- Secure site (HTTPS)
- Review authenticity signals
- Source citations

### Readability Analysis
- Sentence length distribution
- Paragraph length (Korean: 3-5 sentences optimal)
- Subheading frequency (every 200-300 Korean characters)
- List and table usage for scannability

### Content Depth
- Topic coverage completeness
- Supporting data and statistics
- Internal/external reference links
- Multimedia support (images, videos, infographics)

### Korean Keyword Analysis
- Morphological variant detection (조사, 어미 variants)
- Keyword density (accounting for agglutination)
- LSI keyword coverage
- Search intent alignment

### Thin Content Detection
Load thresholds from `three-o/references/quality-gates.md`:
- Blog/Article: minimum 1600 Korean characters
- Product page: minimum 400 Korean characters
- Location page: minimum 500 Korean characters + 60% uniqueness

## Output

Content Quality Score (0-100) with E-E-A-T breakdown and specific improvement recommendations.

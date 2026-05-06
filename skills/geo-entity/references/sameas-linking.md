<!-- Updated: 2026-05-04 -->
# sameAs Linking Best Practices

## What is sameAs?

`sameAs` is a Schema.org property that tells search engines and AI platforms
that different URLs all refer to the same entity. It consolidates brand
identity across platforms.

## Required Links (Priority Order)

### Tier 1 — Critical
These directly influence Knowledge Panel and AI entity recognition:
1. Official website URL
2. Wikidata entity URL (`https://www.wikidata.org/wiki/QXXXXX`)
3. Wikipedia article URL
4. Google Knowledge Graph entity ID

### Tier 2 — Important
These strengthen entity signals:
5. LinkedIn company page
6. Facebook/Meta page
7. Instagram profile
8. YouTube channel
9. X/Twitter profile

### Tier 3 — Korean Market
Essential for Korean brand entity presence:
10. Naver Blog (official)
11. Naver Place listing
12. Kakao Channel
13. Naver Smart Store (if applicable)

## Implementation Template

```json
{
  "@context": "https://schema.org",
  "@type": "Organization",
  "name": "Brand Name",
  "url": "https://example.com",
  "sameAs": [
    "https://www.wikidata.org/wiki/QXXXXX",
    "https://ko.wikipedia.org/wiki/Brand_Name",
    "https://www.linkedin.com/company/brand",
    "https://www.facebook.com/brand",
    "https://www.instagram.com/brand",
    "https://www.youtube.com/@brand",
    "https://x.com/brand",
    "https://blog.naver.com/brand",
    "https://place.map.naver.com/place/XXXXX",
    "https://pf.kakao.com/_brand"
  ]
}
```

## Linking Audit Checklist

| Check | Pass Criteria |
|-------|--------------|
| Website → Wikidata | sameAs includes Wikidata URL |
| Website → Social | All active profiles listed in sameAs |
| Wikidata → Website | P856 property points to correct URL |
| Wikidata → Social | P2002, P2013, P2003 properties set |
| Google KP → Website | URL link present in Knowledge Panel |
| Naver → Website | Business registration has correct URL |

## Common Issues

| Issue | Impact | Fix |
|-------|--------|-----|
| sameAs to deleted profile | Entity confusion | Remove dead links |
| Multiple sameAs to same platform | Dilutes signals | Keep only primary |
| Missing Wikidata link | Major gap for AI | Create/find Wikidata entry |
| Old URL in sameAs | Broken chain | Update to current URL |
| sameAs on wrong page | Ineffective | Place on homepage or /about |

## Bidirectional Linking

For maximum effect, link in BOTH directions:
- Website (sameAs) → External profiles
- External profiles (website field) → Primary domain
- Wikidata (P856) → Primary domain
- Wikidata (sameAs/P2888) → All official URLs

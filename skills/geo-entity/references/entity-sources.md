<!-- Updated: 2026-05-04 -->
# Entity Source Check Methods

## Google Knowledge Panel

**Detection method:**
1. Search `{brand}` on Google
2. Check for Knowledge Panel in right sidebar
3. Extract: name, description, category, attributes, images

**API approach:**
- Google Knowledge Graph Search API
- Endpoint: `https://kgsearch.googleapis.com/v1/entities:search`
- Auth: Google API key at `~/.config/three-o/google_api_key.txt`
- Returns: entity ID, name, description, types, detailedDescription

**Completeness criteria:**
- Name present: +10
- Description present: +15
- Category/type present: +15
- Image present: +10
- URL present: +10
- Social links present: +10
- Reviews/rating present: +15
- Location (if applicable): +15

## Wikidata

**Detection method:**
1. SPARQL query for entity by label
2. Check properties completeness
3. Verify sameAs links

**API approach:**
- Wikidata SPARQL endpoint: `https://query.wikidata.org/sparql`
- Search API: `https://www.wikidata.org/w/api.php?action=wbsearchentities`
- No auth required

**Key properties to check:**
- P31 (instance of)
- P17 (country)
- P159 (headquarters)
- P856 (official website)
- P154 (logo)
- P2002 (Twitter/X)
- P2013 (Facebook)
- P2003 (Instagram)

## Naver Knowledge (지식백과)

**Detection method:**
1. Search `{brand}` on Naver
2. Check for 지식백과 panel
3. Check Naver Business registration

**Access:**
- Naver Search API: `https://openapi.naver.com/v1/search/encyc`
- Auth: Naver Client ID + Secret at `~/.config/three-o/naver_api.json`

## Schema.org (Website)

**Detection method:**
1. Fetch target URL
2. Parse JSON-LD blocks
3. Look for Organization, LocalBusiness, or Corporation types

**Key properties:**
- @type
- name
- url
- logo
- sameAs (array of social/external links)
- address
- contactPoint
- foundingDate
- numberOfEmployees

## Wikipedia

**Detection method:**
1. Search Wikipedia for brand name
2. Check if dedicated article exists
3. If no article, check for mentions in relevant articles

**API:**
- Wikipedia API: `https://en.wikipedia.org/w/api.php`
- Korean: `https://ko.wikipedia.org/w/api.php`
- Action: `query`, `search`

<!-- Updated: 2026-05-04 -->
# Query Mapping Rules

## Mapping Logic

### Step 1: Brand Decomposition
Extract from brand input:
- Brand name (Korean + English variants)
- Primary category/service
- Location(s) served
- Known competitors (from entity data or user input)

### Step 2: Template Selection
Based on detected industry, load templates from `query-templates.md`:
1. Universal queries (always included)
2. Industry-specific queries
3. Korean-language variants

### Step 3: Variable Expansion
Replace template variables with actual values:
- `{brand}` → all brand name variants (Korean, English, abbreviated)
- `{category}` → primary + secondary categories
- `{location}` → all served locations (시/구/동 levels)
- `{competitor}` → top 3-5 known competitors

### Step 4: Deduplication & Prioritization
- Remove semantically duplicate queries
- Score by: search volume estimate × conversion potential × coverage gap
- Select top N queries per platform (default: 20)

## Priority Matrix

| Factor | Weight | Measurement |
|--------|--------|-------------|
| Search volume | 0.30 | Estimated monthly queries |
| Conversion potential | 0.25 | Transactional intent score |
| Coverage gap | 0.25 | Currently not mentioned |
| Competitive presence | 0.20 | Competitors mentioned here |

## Platform-Specific Adjustments

### ChatGPT
- Prefers natural language / conversational queries
- Responds well to "recommend" and "best" queries
- Less effective with very short queries

### Perplexity
- Citation-heavy: mention correlates with indexable source content
- Good with specific comparison queries
- Returns source URLs — useful for citability analysis

### Gemini
- Integrates with Google ecosystem (Maps, Shopping)
- Stronger on local/transactional queries
- May reference Google Business Profile data

### Claude
- Knowledge cutoff affects freshness
- Strong on analytical/comparison queries
- Less prone to hallucinated recommendations

## Gap Diagnosis Rules

When brand is NOT mentioned for a query:

| Diagnosis | Signal | Action |
|-----------|--------|--------|
| No content | No relevant page exists | Create content targeting query |
| Weak content | Page exists but thin | Expand with cited facts, stats |
| No entity | Brand not in knowledge graph | Build entity presence |
| Competitor dominance | 3+ competitors mentioned | Differentiation content needed |
| Technical block | AI can't access content | Fix SSR, llms.txt, bot access |

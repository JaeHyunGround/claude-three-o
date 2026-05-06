<!-- Updated: 2026-05-04 -->
# Query Type Taxonomy

## Intent Classification

### Informational (정보형)
User seeks knowledge. AI provides comprehensive answers.
- "what is {category}"
- "{category} 뜻"
- "how does {category} work"
- "{category} 장단점"

### Navigational (탐색형)
User seeks specific brand/entity. AI routes to brand info.
- "{brand} official site"
- "{brand} 공식 홈페이지"
- "{brand} contact"
- "{brand} 위치"

### Transactional (거래형)
User intends action. AI suggests options with purchase context.
- "buy {category}"
- "{category} 가격"
- "{brand} 예약"
- "{category} 할인"

### Comparative (비교형)
User evaluating options. AI provides structured comparison.
- "{brand} vs {competitor}"
- "best {category} comparison"
- "{category} 비교"
- "{brand} 장단점 비교"

### Local (지역형)
User seeks nearby options. AI filters by location.
- "{category} near me"
- "{location} {category} 추천"
- "best {category} in {location}"
- "{location} {category} 맛집"

## Query Expansion Rules

For each base query, generate:
1. English version (for ChatGPT, Perplexity, Claude)
2. Korean version (for Gemini Korean, Perplexity, future Naver CLOVA X)
3. Long-tail variant (adds specificity)
4. Conversational variant (natural language phrasing)

## Priority by Industry

| Industry | Primary Types | Secondary Types |
|----------|--------------|-----------------|
| Restaurant | Local, Recommendation | Review, Comparison |
| Clinic | Recommendation, Evaluation | Local, Review |
| Academy | Comparison, Recommendation | Review, Local |
| E-commerce | Purchase, Comparison | Review, Recommendation |
| SaaS | Comparison, Evaluation | Purchase, How-to |
| Franchise | Local, Recommendation | Review, Evaluation |

## Korean Query Patterns

| Pattern | Intent | Example |
|---------|--------|---------|
| "추천" | Recommendation | "{category} 추천" |
| "비교" | Comparison | "{brand} vs {competitor} 비교" |
| "후기" / "리뷰" | Review | "{brand} 후기" |
| "가격" / "비용" | Transactional | "{brand} 가격" |
| "맛집" | Local+Recommendation | "{location} {category} 맛집" |
| "잘하는" | Evaluation | "{category} 잘하는 곳" |

<!-- Updated: 2026-05-04 -->
# AI Platform Probe Endpoints

## ChatGPT

| Method | Details |
|--------|---------|
| Primary | OpenAI Chat Completions API with web search enabled |
| Fallback | DataForSEO AI Overview scraper |
| Model | gpt-4o or latest available |
| Rate limit | Depends on API tier |
| Auth | OpenAI API key at `~/.config/three-o/openai_key.txt` |

Probe prompt template:
```
[query] — Provide a comprehensive answer with specific brand/product recommendations.
```

## Perplexity

| Method | Details |
|--------|---------|
| Primary | Perplexity Sonar API |
| Fallback | WebFetch of perplexity.ai results |
| Rate limit | 50 req/min (Pro tier) |
| Auth | Perplexity API key at `~/.config/three-o/perplexity_key.txt` |

## Gemini

| Method | Details |
|--------|---------|
| Primary | Google Gemini API with grounding enabled |
| Fallback | DataForSEO Google AI Overview scraper |
| Rate limit | Depends on API tier |
| Auth | Google API key at `~/.config/three-o/google_api_key.txt` |

## Claude

| Method | Details |
|--------|---------|
| Primary | Anthropic Messages API |
| Fallback | N/A |
| Rate limit | Depends on API tier |
| Auth | Anthropic API key at `~/.config/three-o/anthropic_key.txt` |

## Korean AI Platforms (Future)

| Platform | Status | Notes |
|----------|--------|-------|
| Naver CLOVA X | Planned | Naver HyperCLOVA X API |
| Kakao i | Planned | Limited API access |

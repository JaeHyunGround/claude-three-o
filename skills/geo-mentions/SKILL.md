---
name: geo-mentions
description: >
  AI brand mention tracking across ChatGPT, Perplexity, Gemini, and Claude.
  Probes AI platforms with industry-relevant queries to measure brand
  visibility, mention frequency, position, and context quality.
  Use when user says "brand mentions", "브랜드 언급", "AI mentions",
  "AI 언급 추적", "ChatGPT mentions", "Perplexity mentions".
user-invocable: true
argument-hint: "<brand> [--queries file]"
license: proprietary
metadata:
  author: Jaehyun Ahn
  version: "1.0.0"
  category: geo
---

# GEO Mentions: AI Brand Mention Tracking

**Invocation:** `/three-o geo mentions <brand> [--queries file]`

## Supported Platforms

| Platform | Probe Method | Data Extracted |
|----------|-------------|----------------|
| ChatGPT | OpenAI API / DataForSEO scraper | Mentions, citations, position, context |
| Perplexity | Perplexity API | Mentions, source links, position |
| Gemini | Gemini API | Mentions, AI Overview references |
| Claude | Claude API | Mentions, context, source analysis |

## Query Generation

If no `--queries` file provided, auto-generate queries based on:
1. Brand name + industry keywords
2. Comparison queries ("best [category] in [location]")
3. Recommendation queries ("[category] recommendations")
4. Review queries ("[brand] review", "[brand] vs [competitor]")
5. Purchase intent queries ("buy [product]", "[product] price")

Default: 20 queries per platform (80 total).

## Mention Extraction

For each AI response, extract:
- **Mentioned**: Boolean (brand name found in response)
- **Position**: 1st, 2nd, 3rd mention or not mentioned
- **Context**: Surrounding text (positive/negative/neutral)
- **Citation**: Whether source URL was cited
- **Recommendation**: Whether brand was explicitly recommended

## Output Format

```
Brand Mention Report: [brand]
━━━━━━━━━━━━━━━━━━━━━━━━━━
Queries probed: XX per platform (XX total)

Platform Results:
  ChatGPT:    XX/XX queries mentioned (XX%)
  Perplexity: XX/XX queries mentioned (XX%)
  Gemini:     XX/XX queries mentioned (XX%)
  Claude:     XX/XX queries mentioned (XX%)

Top Performing Queries:
  "[query]" - Mentioned on 4/4 platforms, 1st position
  ...

Missing Opportunities:
  "[query]" - Not mentioned on any platform, high volume
  ...
```

## Reference Files

Load on-demand:
- `references/ai-platform-endpoints.md` — API access and probe methods
- `references/query-templates.md` — Industry-specific query templates

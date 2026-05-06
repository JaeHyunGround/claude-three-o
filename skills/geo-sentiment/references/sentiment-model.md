<!-- Updated: 2026-05-04 -->
# Sentiment Classification Model

## Multi-Signal Analysis

Sentiment is NOT determined by simple keyword matching.
Uses layered analysis:

### Layer 1: Explicit Signals
Direct statements about brand quality:
- "highly recommended" → Strong Positive
- "a good option" → Positive
- "you could try" → Neutral
- "has some issues" → Negative
- "I would avoid" → Strong Negative

### Layer 2: Positional Signals
Where brand appears in AI response:
- Listed first → Positive bias (+0.1)
- Listed in middle → Neutral (no adjustment)
- Listed last / as afterthought → Slight negative (-0.05)
- Only mentioned when asked directly → Neutral

### Layer 3: Qualifier Analysis
Conditional language modifies base sentiment:
- "best for [specific use case]" → Positive (targeted)
- "if budget isn't a concern" → Neutral with caveat
- "despite [negative], still..." → Net positive with acknowledged weakness
- "unless you need [feature]" → Conditional negative

### Layer 4: Comparative Frame
How brand is positioned relative to competitors:
- "better than [competitor]" → Strong positive
- "similar to [competitor]" → Neutral
- "not as good as [competitor]" → Negative
- "cheaper alternative to [competitor]" → Context-dependent

## Scoring Calculation

```
sentiment_score = base_signal + positional_adj + qualifier_mod + comparative_mod
final = clamp(sentiment_score, 0.0, 1.0)
```

## Aggregation

Per-platform sentiment:
```
platform_sentiment = weighted_avg(query_sentiments)
  where weight = query_relevance × query_volume_estimate
```

Overall sentiment:
```
overall = chatgpt(0.35) + perplexity(0.25) + gemini(0.25) + claude(0.15)
```

## Korean Language Signals

| Korean Signal | Sentiment | English Equivalent |
|---------------|-----------|-------------------|
| "강추" | Strong Positive | Highly recommend |
| "괜찮은" | Positive | Decent/fine |
| "무난한" | Neutral | Passable |
| "별로" | Negative | Not great |
| "비추" | Strong Negative | Do not recommend |
| "가성비 좋은" | Positive | Good value |
| "아쉬운" | Mild Negative | Disappointing |

## Confidence Scoring

Each sentiment classification includes confidence (0-1):
- High (0.8-1.0): Clear explicit signal, consistent across context
- Medium (0.5-0.79): Mixed signals or qualified statements
- Low (0.0-0.49): Ambiguous, requires human review

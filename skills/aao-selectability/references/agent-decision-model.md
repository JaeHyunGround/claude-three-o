<!-- Updated: 2026-05-04 -->
# AI Agent Decision Model

## How AI Agents Select Options

When a user asks an AI agent to perform a task (book, buy, recommend),
the agent follows a decision pipeline:

```
User Request → Parse Intent → Search Options → Rank → Select → Act
```

## Ranking Algorithm (Simulated)

### Stage 1: Eligibility Filter
Remove options that don't match basic criteria:
- Location mismatch
- Category mismatch
- Price out of range
- Closed / unavailable
- Missing critical info (can't verify eligibility)

### Stage 2: Quality Scoring
Score remaining options on:
```
quality = (rating × 0.3) + (review_volume × 0.2) + (info_completeness × 0.2)
        + (trust × 0.15) + (freshness × 0.15)
```

### Stage 3: Actionability Boost
Options where agent can complete action get priority:
- API available: +30% boost
- Online booking: +20% boost
- Form submission: +10% boost
- Contact only: no boost

### Stage 4: Confidence Check
Agent needs minimum confidence to recommend:
- High confidence (0.8+): "I recommend [brand]"
- Medium confidence (0.5-0.8): "Here are some options: [brand], [others]"
- Low confidence (<0.5): "I found these but suggest verifying: [list]"

## Platform-Specific Behavior

### ChatGPT (with plugins/actions)
- Prefers options with API integrations
- May use browse tool to verify info
- Values recent, structured data

### Perplexity
- Citation-focused: only recommends what it can cite
- Prefers pages with clear, extractable answers
- Links to sources

### Google Gemini (with Google ecosystem)
- Integrates Google Maps, Shopping, Flights data
- Prefers Google Business Profile rich businesses
- May pull from Google Merchant Center feeds

### Claude
- Conservative: won't recommend without confidence
- Values factual accuracy over popularity
- Less likely to make transactional suggestions

## Optimization Implications

To maximize selectability across all agents:
1. **Structured data** — agents parse this first
2. **API/booking** — agents prefer actionable options
3. **Ratings/reviews** — social proof affects ranking
4. **Completeness** — missing info = eliminated early
5. **Freshness** — stale data reduces confidence

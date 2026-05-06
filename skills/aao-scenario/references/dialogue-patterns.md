<!-- Updated: 2026-05-04 -->
# AI Agent Dialogue Patterns

## Pattern 1: Clarification Loop

```
User: "I need a dentist"
Agent: "Where are you located?"
User: "Seoul, Gangnam"
Agent: "What type of treatment? (General, Orthodontics, Implant, etc.)"
User: "Implant"
Agent: → Searches for implant dentists in Gangnam
       → Needs: location, specialty, availability, pricing
```

**Content requirement:** Service pages must clearly state:
- Specific services offered (not just "dental care")
- Service area (구/동 level for Korean market)
- Price ranges per service

## Pattern 2: Comparison Request

```
User: "Compare [brand] and [competitor] for [need]"
Agent: → Fetches data for both
       → Compares on: price, rating, features, location
       → Presents structured comparison
```

**Content requirement:**
- Unique selling points clearly stated
- Quantifiable advantages (numbers, stats)
- Honest pros/cons (builds AI trust)

## Pattern 3: Action Execution

```
User: "Book [service] at [brand] for [date/time]"
Agent: → Checks availability for requested time
       → Confirms details (service, price, duration)
       → Executes booking
       → Returns confirmation
```

**Content requirement:**
- Real-time availability (API or widget)
- Clear service + price + duration mapping
- Programmatic booking capability
- Confirmation response format

## Pattern 4: Information Gathering

```
User: "Tell me about [brand]'s [specific aspect]"
Agent: → Searches brand content
       → Extracts relevant passage
       → Presents answer with source
```

**Content requirement:**
- Clear, extractable passages (citability)
- One topic per section
- Factual, specific information
- Updated regularly (freshness signal)

## Pattern 5: Recommendation with Constraints

```
User: "Recommend [category] that is [constraint1] and [constraint2]"
Agent: → Filters by constraints
       → Ranks remaining options
       → Presents top 3-5 with reasons
```

**Content requirement:**
- Structured attributes (filterable)
- Clear constraint information (price, location, features)
- Differentiation from competitors

## Agent Response Patterns (What Agents Prefer)

| Pattern | Agent Prefers | Agent Avoids |
|---------|--------------|--------------|
| Data format | Structured (schema, tables) | Prose paragraphs |
| Specificity | "4.5/5 from 230 reviews" | "Highly rated" |
| Recency | "Updated May 2026" | No date visible |
| Actionability | "Book now" with link/API | "Call us" |
| Completeness | All attributes present | Partial info |
| Verification | Cross-platform consistent | Single-source only |

## Korean Agent Interaction Notes

Korean users ask agents differently:
- More indirect: "이 근처에 괜찮은 데 있어?" (Anywhere decent nearby?)
- Formality levels: agents should match (존댓말 default)
- Group context: Korean queries often for groups, not individuals
- Price sensitivity: "가성비" (value for money) is common filter
- Trust signals: "후기 많은 곳" (places with many reviews)

Content should anticipate these patterns with:
- Natural Korean phrasing in FAQ/content
- Group-friendly information (group sizes, set menus)
- Prominent review counts and ratings
- Clear value propositions

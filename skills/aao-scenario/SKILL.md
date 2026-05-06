---
name: aao-scenario
description: >
  Designs conversational scenarios for AI agent interactions.
  Maps user intents to brand responses, creates dialogue flows,
  and optimizes content for agent conversation patterns.
  Use when user says "scenario design", "시나리오 설계",
  "conversation flow", "대화 흐름", "agent dialogue", "에이전트 대화".
user-invocable: true
argument-hint: "<brand> --industry <type>"
license: proprietary
metadata:
  author: Jaehyun Ahn
  version: "1.0.0"
  category: aao
---

# AAO Scenario: Conversational Scenario Design

**Invocation:** `/three-o aao scenario <brand> --industry <type>`

## Purpose

AI agents engage users in conversations to fulfill requests.
Businesses need content structured to answer the questions agents
ask on behalf of users. This skill designs conversational scenarios
and maps them to content requirements.

## Scenario Components

### 1. Intent Mapping
Map common user intents to brand-relevant responses:
- Discovery: "Find me a [category] near [location]"
- Comparison: "Which is better, [brand] or [competitor]?"
- Action: "Book/buy [product/service] at [brand]"
- Information: "What are [brand]'s hours/prices/services?"
- Support: "I have a problem with [brand]'s [product]"

### 2. Dialogue Flow Design
For each intent, design the optimal conversation:
```
User Intent → Agent Questions → Brand Data Needed → Response → Action
```

### 3. Content Gap Identification
For each scenario step, check if required content exists:
- Does the website answer this question clearly?
- Is the answer in structured, extractable format?
- Can the agent find this without deep navigation?

## Industry Scenario Templates

### Restaurant
| Scenario | Agent Needs | Content Required |
|----------|-------------|-----------------|
| "Book dinner" | Hours, menu, reservation | Booking widget, menu schema |
| "Menu options for allergies" | Allergen info | Detailed menu with allergens |
| "Family-friendly?" | Amenities | Kids menu, facilities list |
| "Delivery available?" | Delivery zone, menu, prices | Delivery schema, service area |

### Clinic
| Scenario | Agent Needs | Content Required |
|----------|-------------|-----------------|
| "Book appointment" | Availability, services | Booking API, service list |
| "Does Dr. X treat Y?" | Doctor specialties | Physician schema per doctor |
| "Insurance accepted?" | Insurance list | Structured insurance data |
| "Emergency available?" | Hours, emergency policy | Clear emergency info |

### E-commerce
| Scenario | Agent Needs | Content Required |
|----------|-------------|-----------------|
| "Buy product X" | Price, stock, shipping | Product schema + Offer |
| "Compare options" | Specs, reviews, prices | Comparison-ready data |
| "Return policy?" | Return terms | Returns page, structured |
| "Track my order" | Order API | Order status endpoint |

## Scenario Coverage Score

```
coverage = scenarios_supported / total_relevant_scenarios × 100
```

| Coverage | Level | Meaning |
|----------|-------|---------|
| 90-100% | Excellent | Agent can handle almost all interactions |
| 70-89% | Good | Most common scenarios covered |
| 50-69% | Fair | Gaps in important scenarios |
| <50% | Poor | Agent frequently cannot help users |

## Output Format

```
Scenario Coverage: [brand]
━━━━━━━━━━━━━━━━━━━━━━━━━━
Industry: [type]
Coverage Score: XX/100
Scenarios Analyzed: XX

Supported Scenarios:
  ✓ [scenario] — Content available, agent can respond
  ...

Gap Scenarios:
  ✗ [scenario] — Missing: [what content is needed]
  ...

Priority Content to Create:
  1. [content piece] — Enables [X] scenarios
  2. [content piece] — Enables [X] scenarios
  ...

Sample Dialogue Flows:
  [Most important scenario with step-by-step flow]
```

## Reference Files

Load on-demand:
- `references/scenario-templates.md` — Full scenario library by industry
- `references/dialogue-patterns.md` — Common AI agent dialogue patterns

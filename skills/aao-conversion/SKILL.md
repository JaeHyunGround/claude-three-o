---
name: aao-conversion
description: >
  Analyzes conversion funnel readiness for AI agent transactions.
  Checks if agents can complete purchases, bookings, or signups
  without human intervention.
  Use when user says "conversion funnel", "전환 퍼널", "agent conversion",
  "에이전트 전환", "booking optimization", "예약 최적화".
user-invocable: true
argument-hint: "<url> [--flow <book|buy|signup>]"
license: proprietary
metadata:
  author: Jaehyun Ahn
  version: "1.0.0"
  category: aao
---

# AAO Conversion: Agent Transaction Readiness

**Invocation:** `/three-o aao conversion <url> [--flow <book|buy|signup>]`

## Purpose

Evaluates whether AI agents can complete end-to-end transactions
on behalf of users. As agents become capable of taking actions,
businesses with frictionless conversion paths gain competitive advantage.

## Conversion Flow Types

| Flow | Description | Key Pages |
|------|-------------|-----------|
| book | Appointment/reservation booking | Service page → Calendar → Confirm |
| buy | Product purchase | Product → Cart → Checkout → Payment |
| signup | Service registration | Landing → Form → Verify → Welcome |

## Analysis Dimensions

### 1. Entry Point Clarity (20%)
- Can agent find the conversion start point?
- Clear CTA with semantic markup?
- Action type identifiable from structured data?

### 2. Form Accessibility (25%)
- Forms parseable without JavaScript rendering?
- Input fields with proper labels and types?
- Required vs optional fields clear?
- Validation rules discoverable?

### 3. Flow Completeness (25%)
- Full flow completable programmatically?
- No CAPTCHA blocking?
- No mandatory phone verification mid-flow?
- Guest checkout available?

### 4. Confirmation Signals (15%)
- Success state clearly identifiable?
- Confirmation data returned (ID, reference)?
- Email/notification triggers working?

### 5. Error Handling (15%)
- Clear error messages on failure?
- Agent can understand what went wrong?
- Retry path available?

## Friction Points Detected

| Friction | Impact | Agent Behavior |
|----------|--------|---------------|
| Login required | High | Agent abandons |
| CAPTCHA | Critical | Agent cannot proceed |
| Phone-only booking | High | Agent hands off to user |
| Complex multi-step | Medium | Agent may lose state |
| PDF-only info | Medium | Agent can't extract details |
| Dynamic pricing (no API) | Medium | Agent can't confirm price |

## Output Format

```
Conversion Analysis: [url]
━━━━━━━━━━━━━━━━━━━━━━━━━━
Flow Type: [book/buy/signup]
Conversion Score: XX/100

Dimension Scores:
  Entry Point Clarity: XX/100
  Form Accessibility:  XX/100
  Flow Completeness:   XX/100
  Confirmation:        XX/100
  Error Handling:      XX/100

Friction Points:
  [Critical] [description] → [fix]
  [High] [description] → [fix]
  ...

Agent Completion Rate: [estimated %]
Recommendation: [what to fix first]
```

## Reference Files

Load on-demand:
- `references/conversion-patterns.md` — Common flow patterns by industry
- `references/friction-checklist.md` — Full friction point detection rules

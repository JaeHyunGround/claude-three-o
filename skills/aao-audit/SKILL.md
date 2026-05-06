---
name: aao-audit
description: >
  Full AAO (Assistive Agent Optimization) analysis. Evaluates how well
  a brand/website is optimized for AI agent selection, conversion,
  and structured data consumption.
  Use when user says "AAO audit", "AAO 분석", "agent optimization",
  "에이전트 최적화", "AI agent audit".
user-invocable: true
argument-hint: "<url or brand>"
license: proprietary
metadata:
  author: Jaehyun Ahn
  version: "1.0.0"
  category: aao
---

# AAO Audit: Full Agent Optimization Analysis

**Invocation:** `/three-o aao audit <url or brand>`

## Purpose

Evaluates how well a business is prepared for AI agent-driven commerce.
As AI assistants increasingly make purchasing decisions on behalf of users,
businesses need to be "agent-selectable" — optimized for AI agents to
discover, evaluate, and convert through.

## Workflow

1. Extract brand name and primary URL from input
2. Spawn AAO agents in parallel:
   - **aao-selectability**: Agent selection scoring
   - **aao-conversion**: Conversion funnel analysis
   - **aao-data**: Structured data audit
   - **aao-rendering**: AI accessibility check
3. Sequential analysis:
   - **aao-entity**: Brand entity consistency
   - **aao-feed**: Product feed validation (if e-commerce)
4. Conditional:
   - If e-commerce detected → full product feed audit
   - If service business → scenario coverage check
5. Aggregate into AAO Score (0-100)
6. Generate prioritized action plan
7. Offer report: "Generate PDF? Use `/three-o report aao`"

## AAO Score Components

| Dimension | Weight | Description |
|-----------|--------|-------------|
| Selectability | 30% | How likely an AI agent picks this brand |
| Conversion Readiness | 25% | Can an agent complete a transaction? |
| Structured Data | 20% | Schema.org, product feeds, API availability |
| Rendering | 15% | SSR, no JS dependency for key info |
| Entity Consistency | 10% | Consistent brand info across platforms |

## Output Format

```
AAO Audit Report: [brand]
━━━━━━━━━━━━━━━━━━━━━━━━━━
AAO Score: XX/100

Dimension Scores:
  Selectability:       XX/100
  Conversion Readiness: XX/100
  Structured Data:     XX/100
  Rendering:           XX/100
  Entity Consistency:  XX/100

Agent Readiness Level: [Not Ready / Basic / Intermediate / Advanced / Excellent]

Priority Actions:
  1. [Critical: action]
  2. [High: action]
  ...

Industry: [detected]
Benchmark: [Your score vs industry median]
```

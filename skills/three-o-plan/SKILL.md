---
name: three-o-plan
description: >
  Generates strategic 90-day optimization roadmap based on audit results.
  Creates prioritized action plans with timeline, resource estimates,
  and expected ROI per action.
  Use when user says "plan", "계획", "roadmap", "로드맵",
  "strategy", "전략", "action plan", "액션 플랜".
user-invocable: true
argument-hint: "<business-type> [--budget <level>] [--timeline <days>]"
license: proprietary
metadata:
  author: Jaehyun Ahn
  version: "1.0.0"
  category: three-o
---

# Three-O Plan: Strategic Optimization Roadmap

**Invocation:** `/three-o plan <business-type> [--budget <level>] [--timeline <days>]`

## Purpose

Converts audit findings into an actionable, prioritized roadmap.
Considers business type, budget constraints, and timeline to create
a realistic optimization plan across all three pillars.

## Input Options

| Parameter | Values | Default |
|-----------|--------|---------|
| business-type | restaurant, clinic, academy, ecommerce, saas, franchise, agency, realestate | auto-detect |
| --budget | low, medium, high | medium |
| --timeline | 30, 60, 90, 180 | 90 |

## Planning Framework

### Priority Matrix

Actions scored by: `impact × feasibility / effort`

| Factor | Measurement |
|--------|-------------|
| Impact | Expected score improvement (points) |
| Feasibility | Technical/resource availability (1-5) |
| Effort | Time and cost required (1-5, inverted) |

### Phase Allocation

| Phase | Timeline | Focus |
|-------|----------|-------|
| Quick Wins | Week 1-2 | High impact, low effort fixes |
| Foundation | Week 3-4 | Technical infrastructure |
| Build | Month 2 | Content and entity development |
| Optimize | Month 3 | Advanced optimization and monitoring |

## Industry-Specific Priorities

| Industry | Phase 1 Focus | Phase 2 Focus | Phase 3 Focus |
|----------|---------------|---------------|---------------|
| Restaurant | Naver Place + Schema | Menu content + GEO | Booking flow + AAO |
| Clinic | Technical SEO + Entity | Content E-E-A-T | AI visibility + conversion |
| Academy | Keyword strategy | Course content | Agent selectability |
| E-commerce | Product feed + Schema | Content + GEO entity | Conversion + AAO |
| SaaS | Technical + Schema | Comparison content | API + agent integration |
| Franchise | Multi-location SEO | Brand entity build | Scenario coverage |

## Budget Consideration

| Budget | Actions Included | Excludes |
|--------|-----------------|----------|
| Low | DIY fixes, free tools only | Paid tools, dev work, content creation |
| Medium | Some dev work, basic content | Large redesigns, ongoing paid tools |
| High | Full implementation, paid tools, content team | Nothing excluded |

## Output Format

```
Three-O Strategic Plan: [business-type]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Timeline: [X] days | Budget: [level]
Expected Score Improvement: +XX points

Phase 1: Quick Wins (Week 1-2)
  □ [Action] — Impact: +X pts | Effort: [low/med/high]
  □ [Action] — Impact: +X pts | Effort: [low/med/high]
  ...

Phase 2: Foundation (Week 3-4)
  □ [Action] — Impact: +X pts | Effort: [low/med/high]
  ...

Phase 3: Build (Month 2)
  □ [Action] — Impact: +X pts | Effort: [low/med/high]
  ...

Phase 4: Optimize (Month 3)
  □ [Action] — Impact: +X pts | Effort: [low/med/high]
  ...

Projected Outcome:
  Three-O Score: {current} → {target}
  SEO: {current} → {target}
  GEO: {current} → {target}
  AAO: {current} → {target}
```

## Reference Files

Load on-demand:
- `references/action-catalog.md` — Complete action library with estimates

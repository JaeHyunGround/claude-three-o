---
name: aao-entity
description: >
  Checks brand entity consistency across platforms for agent trust.
  Verifies NAP (Name, Address, Phone), attributes, and descriptions
  are consistent across all digital touchpoints.
  Use when user says "entity consistency", "엔티티 일관성",
  "brand consistency", "브랜드 일관성", "NAP check", "NAP 확인".
user-invocable: true
argument-hint: "<brand>"
license: proprietary
metadata:
  author: Jaehyun Ahn
  version: "1.0.0"
  category: aao
---

# AAO Entity: Brand Entity Consistency

**Invocation:** `/three-o aao entity <brand>`

## Purpose

AI agents cross-reference brand information across multiple platforms.
Inconsistencies reduce agent confidence and may cause the agent to
skip the brand in favor of competitors with cleaner data.

## Consistency Dimensions

### 1. NAP Consistency (30%)
Name, Address, Phone must match across:
- Website (Schema.org)
- Google Business Profile
- Naver Place
- Social media profiles
- Directory listings

### 2. Description Consistency (25%)
Brand description/tagline should be coherent:
- Website meta description
- Google Business description
- Naver Place description
- Social media bios
- Directory listings

### 3. Category Consistency (20%)
Business category should match:
- Schema.org @type
- Google Business category
- Naver Place category
- Industry directories

### 4. Attribute Consistency (15%)
Key attributes must align:
- Hours of operation
- Price range
- Services offered
- Payment methods
- Languages supported

### 5. Visual Consistency (10%)
Brand presentation alignment:
- Logo consistent across platforms
- Primary brand colors
- Cover/banner images professional

## Cross-Platform Check Matrix

| Platform | NAP | Desc | Category | Hours | Rating |
|----------|-----|------|----------|-------|--------|
| Website | ✓/✗ | ✓/✗ | ✓/✗ | ✓/✗ | ✓/✗ |
| Google Business | ✓/✗ | ✓/✗ | ✓/✗ | ✓/✗ | ✓/✗ |
| Naver Place | ✓/✗ | ✓/✗ | ✓/✗ | ✓/✗ | ✓/✗ |
| Kakao Map | ✓/✗ | ✓/✗ | ✓/✗ | ✓/✗ | ✓/✗ |
| Instagram | ✓/✗ | ✓/✗ | — | — | — |
| Facebook | ✓/✗ | ✓/✗ | ✓/✗ | ✓/✗ | ✓/✗ |

## Impact on Agent Decisions

| Inconsistency | Agent Behavior |
|---------------|---------------|
| Name mismatch | May treat as different entities |
| Address mismatch | Incorrect location routing |
| Phone mismatch | Broken contact action |
| Hours mismatch | Incorrect availability recommendation |
| Category mismatch | Wrong query matching |
| Price mismatch | Trust reduction, may skip |

## Output Format

```
Entity Consistency Report: [brand]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Consistency Score: XX/100

Dimension Scores:
  NAP Consistency:         XX/100
  Description Consistency: XX/100
  Category Consistency:    XX/100
  Attribute Consistency:   XX/100
  Visual Consistency:      XX/100

Inconsistencies Found:
  [platform1] vs [platform2]: [field] differs
    → Platform A: "[value]"
    → Platform B: "[value]"
  ...

Priority Fixes:
  1. [fix with highest agent impact]
  ...
```

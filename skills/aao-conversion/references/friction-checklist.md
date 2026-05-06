<!-- Updated: 2026-05-04 -->
# Conversion Friction Point Checklist

## Critical Blockers (Agent Cannot Proceed)

| # | Friction Point | Detection Method |
|---|----------------|-----------------|
| 1 | CAPTCHA on conversion path | Check for reCAPTCHA/hCaptcha elements |
| 2 | Login required before action | Check if conversion page redirects to auth |
| 3 | JavaScript-only rendering | Compare SSR vs JS-rendered content |
| 4 | Phone verification required | Check for phone input with SMS step |
| 5 | Flash/Silverlight dependency | Check for legacy embed elements |

## High Friction (Agent Struggles)

| # | Friction Point | Detection Method |
|---|----------------|-----------------|
| 6 | Multi-page form without API | Count form steps, check for AJAX |
| 7 | Unclear input requirements | Check for label, placeholder, pattern attrs |
| 8 | Dynamic pricing (no structured) | Check if price changes without Offer schema |
| 9 | Mandatory account creation | Check if guest path exists |
| 10 | File upload required | Check for file input in conversion flow |
| 11 | Payment only via redirect | Check if payment leaves domain |
| 12 | Time-limited session | Check for session timeout indicators |

## Medium Friction (Agent Works Around)

| # | Friction Point | Detection Method |
|---|----------------|-----------------|
| 13 | Inconsistent form validation | Submit with various inputs, check errors |
| 14 | Hidden required fields | Check display:none inputs that are required |
| 15 | Ambiguous success state | Check for clear confirmation signals |
| 16 | Multiple CTAs competing | Count action buttons on conversion page |
| 17 | Slow page load (>3s) | Measure TTFB and LCP |
| 18 | Pop-ups interrupting flow | Check for modal/overlay elements |

## Low Friction (Minor Issues)

| # | Friction Point | Detection Method |
|---|----------------|-----------------|
| 19 | No breadcrumb/progress bar | Check for step indicators |
| 20 | Missing error context | Check error message specificity |
| 21 | No back button support | Test browser history state |
| 22 | Missing autofill hints | Check autocomplete attributes |

## Scoring

```
conversion_friction = 100 - sum(friction_penalties)

Penalties:
  Critical: -25 per item
  High: -10 per item
  Medium: -5 per item
  Low: -2 per item
```

## Agent-Specific Friction

### ChatGPT Actions
- Needs OpenAPI spec for API integration
- Cannot handle OAuth without user intervention
- Prefers simple REST endpoints

### General Web Agents
- Need semantic HTML (proper labels, ARIA)
- Prefer single-page flows over multi-redirects
- Cannot solve CAPTCHAs
- Cannot handle 2FA/MFA without user

## Korean Market Friction Points

| Friction | Common In | Fix |
|----------|-----------|-----|
| ActiveX requirement | Banking, government | Modern alternative payment |
| 공인인증서 | Financial services | Simple auth alternative |
| Naver Login only | Korean services | Add guest option |
| Korean phone required | Verification | Email alternative |
| 주민등록번호 | Age verification | CI/DI based verification |

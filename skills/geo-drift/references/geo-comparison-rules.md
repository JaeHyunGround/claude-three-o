<!-- Updated: 2026-05-04 -->
# GEO Drift Comparison Rules

## Rule Specifications

### Rule 1: Score Change Detection
```
IF abs(current_score - baseline_score) > threshold:
  severity = critical IF delta > 10
  severity = warning IF delta > 5
  severity = info IF delta > 2
```

### Rule 2: Mention Presence Change
```
IF baseline.mentioned == true AND current.mentioned == false:
  severity = critical
  label = "Brand disappeared from [platform] for query: [query]"

IF baseline.mentioned == false AND current.mentioned == true:
  severity = positive
  label = "New mention gained on [platform] for query: [query]"
```

### Rule 3: Position Change
```
IF current.position > baseline.position (lower position):
  severity = warning IF drop >= 2
  severity = info IF drop == 1

IF current.position < baseline.position (higher position):
  severity = positive
```

### Rule 4: Sentiment Shift
```
IF baseline.sentiment == "positive" AND current.sentiment == "negative":
  severity = critical
  label = "Sentiment reversed on [platform]"

IF baseline.sentiment == "positive" AND current.sentiment == "neutral":
  severity = info

IF baseline.sentiment == "negative" AND current.sentiment == "positive":
  severity = positive
```

### Rule 5: Competitor Entry
```
IF competitor NOT IN baseline.mentioned_brands AND competitor IN current.mentioned_brands:
  severity = warning
  label = "New competitor [name] appeared in [query]"
```

### Rule 6: Citation Change
```
IF baseline.cited == true AND current.cited == false:
  severity = warning
  label = "Citation lost on [platform]"
```

### Rule 7: Platform Consistency
```
IF brand mentioned on all platforms in baseline BUT missing on one now:
  severity = critical
  label = "Lost presence on [platform] (was present on all)"
```

## Drift Score Aggregation

```
total_drift = 0
for each rule_trigger:
  total_drift += severity_weight × platform_importance

platform_importance:
  ChatGPT:    0.35
  Perplexity: 0.25
  Gemini:     0.25
  Claude:     0.15
```

## Alert Thresholds

| Drift Score | Alert Level | Action |
|-------------|-------------|--------|
| < -15 | Red Alert | Immediate investigation required |
| -15 to -5 | Warning | Review within 48 hours |
| -5 to +5 | Stable | Normal monitoring |
| +5 to +15 | Improving | Note what's working |
| > +15 | Strong gain | Document successful strategy |

## Baseline Management

### Auto-baseline
- First run for a brand creates initial baseline
- Subsequent runs compare against most recent baseline
- After comparison, current data becomes new baseline

### Manual baseline
- User can lock a baseline: `--lock-baseline`
- Locked baselines persist until explicitly cleared
- Useful for measuring impact of specific changes

### Baseline Cleanup
- Baselines older than 365 days auto-archived
- Archived data compressed but available for trend analysis
- `--purge-old` removes archived data

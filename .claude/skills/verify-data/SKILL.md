---
name: verify-data
description: Verify ace-tracker data accuracy against official NOAA HURDAT2 sources
disable-model-invocation: false
---

# Data Accuracy Verification Procedure

## When to Verify

- After changes to ACE calculation logic
- When migrating data sources
- When suspicious ACE values appear
- Before public launch; at end of each season after NOAA finalizes data

## 1. Select Storms

Pick 6 total: 3 Atlantic, 3 Pacific. Mix of categories (TS, Cat 1–2, Cat 3–5), different decades, at least one recent season and one major hurricane.

## 2. Pull Official Data via Tropycal

```python
python3 -c "
import tropycal.tracks as tracks
basin = tracks.TrackDataset(basin='north_atlantic', source='hurdat')
storm = basin.get_storm(('ida', 2021))
print(f'Max Wind: {storm.max_sustained_wind} kt')
print(f'ACE: {storm.ace:.4f}')
print(f'Start: {storm.time[0]}  End: {storm.time[-1]}')
"
```

Use `basin='east_pacific'` for Pacific storms.

## 3. Compare Against Tracker Output

Find storms in the **Historical Storms** tab of the Excel files. For each storm:

| Field | Tolerance |
|---|---|
| Max wind (kt) | Must match exactly |
| ACE | Within 5% = excellent, within 10% = acceptable |
| Duration | Within 1 day acceptable |

## 4. Document in VERIFICATION_REPORT.md

For each storm: name/year, wind match (✅/❌), ACE % diff, duration match.

Summary line: `X/6 wind exact, Y/6 ACE within 5%, Z/6 duration within 1 day`

## 5. Investigate Discrepancies (>10% ACE)

1. Confirm ACE only counted at 0000, 0600, 1200, 1800 UTC
2. Confirm only TS/HU/SS statuses counted
3. Check for Tropycal cached older data
4. NOAA periodically revises HURDAT2 — small diffs are expected

## Success Criteria

- Wind: 100% exact match
- ACE: 80%+ within 5%
- Duration: 90%+ within 1 day

**Baseline (April 2026):** 100% wind, 83% ACE, 100% duration.

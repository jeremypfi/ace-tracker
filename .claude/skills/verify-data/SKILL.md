---
name: verify-data
description: Verify ace-tracker data accuracy against official NOAA HURDAT2 sources
disable-model-invocation: false
---

# Data Accuracy Verification Procedure

Use this procedure to verify ace-tracker's calculations match official NOAA HURDAT2 data. Do this periodically or when you suspect data issues.

## When to Verify

- After major code changes (especially ACE calculation logic)
- When migrating data sources (like we did with Tropycal)
- If you notice suspicious ACE values
- Before sharing the project publicly
- At end of hurricane season (once NOAA finalizes data)

## Verification Procedure

### 1. Select Random Storms

**Pick 6 storms total:**
- 3 from Atlantic basin (different years)
- 3 from Pacific basin (different years)

**Selection criteria:**
- Mix of categories (TS, Cat 1-2, Cat 3-5)
- Different time periods (1990s, 2000s, 2010s, 2020s)
- Include at least one recent season
- Include at least one major hurricane

**Example selections:**
- Atlantic: Katia 2017, Ida 2021, Gordon 2024
- Pacific: Carlotta 2024, Ulika 2016, Julio 2020

### 2. Get Your Tracker Data

Run the tracker:
```bash
python3 ace_tracker.py
```

Open the Excel files and find your selected storms in the **"Historical Storms"** tab.

**Record for each storm:**
- Storm name and year
- Max wind speed (knots)
- ACE value
- Duration (days)
- Category

### 3. Get Official NOAA Data

**Option A: Direct HURDAT2 File** (Most Accurate)

Atlantic:
```bash
curl -s https://www.nhc.noaa.gov/data/hurdat/hurdat2-1851-2024-050425.txt | grep "STORM_ID"
```

Pacific:
```bash
curl -s https://www.nhc.noaa.gov/data/hurdat/hurdat2-nepac-1949-2024-050425.txt | grep "STORM_ID"
```

**Option B: NHC Storm Reports**

Go to: https://www.nhc.noaa.gov/data/tcr/

Find the storm's Tropical Cyclone Report (TCR). These reports include:
- Maximum sustained wind
- ACE value
- Storm duration

**Option C: Use Tropycal Directly** (Sanity Check)

```python
python3 -c "
import tropycal.tracks as tracks

# For Atlantic
basin = tracks.TrackDataset(basin='north_atlantic', source='hurdat')
storm = basin.get_storm(('katia', 2017))

print(f'Name: {storm.name}')
print(f'Year: {storm.year}')
print(f'Max Wind: {storm.max_sustained_wind} kt')
print(f'ACE: {storm.ace:.4f}')
print(f'Start: {storm.time[0]}')
print(f'End: {storm.time[-1]}')
"
```

### 4. Compare Values

Create a comparison table:

| Storm | Year | Source | Max Wind (kt) | ACE | Duration (days) |
|-------|------|--------|---------------|-----|-----------------|
| Katia | 2017 | NOAA   | 120           | 6.86| 9               |
| Katia | 2017 | Tracker| 120           | 6.86| 9               |
| Ida   | 2021 | NOAA   | 130           | 8.09| 7               |
| Ida   | 2021 | Tracker| 130           | 8.24| 7               |

### 5. Calculate Accuracy

**Acceptable tolerances:**
- **Wind Speed:** Must match exactly (0% error)
- **ACE:** Within 5% is excellent, within 10% is acceptable
- **Duration:** Within 1 day is acceptable (timing of formation/dissipation can vary)

**Calculate percentage difference:**
```
ACE Difference = |Tracker ACE - Official ACE| / Official ACE × 100%
```

**Example:**
- Official: 8.09
- Tracker: 8.24
- Difference: |8.24 - 8.09| / 8.09 × 100% = 1.85% ✅ Excellent

### 6. Document Results

Update `VERIFICATION_REPORT.md`:

```markdown
# Data Verification Report

**Date:** April 24, 2026
**Verified by:** JP

## Storms Verified

### Atlantic Basin
1. **Katia 2017**
   - Max Wind: 120 kt ✅ Perfect match
   - ACE: 6.86 vs 6.86 ✅ Perfect match (0.0% diff)
   - Duration: 9 days ✅ Exact match

2. **Ida 2021**
   - Max Wind: 130 kt ✅ Perfect match
   - ACE: 8.24 vs 8.09 ⚠️ Close (1.85% diff)
   - Duration: 7 days ✅ Exact match

[... continue for all 6 storms]

## Summary

- **Wind Accuracy:** 6/6 perfect matches (100%)
- **ACE Accuracy:** 5/6 within 5% (83% excellent)
- **Duration Accuracy:** 6/6 within 1 day (100%)

## Conclusion

ACE tracker data is highly accurate and suitable for tracking hurricane seasons.
Minor ACE discrepancies are likely due to timing of data finalization.
```

### 7. Investigate Discrepancies

**If you find significant errors (>10% ACE difference):**

1. Check the storm's synoptic time records in HURDAT2
2. Verify ACE is only counted when status is TS, HU, or SS
3. Confirm wind speeds at 0000, 0600, 1200, 1800 UTC only
4. Check if Tropycal data is outdated (older storms may differ from recent HURDAT2 updates)

**Common causes of small differences:**
- NOAA revises HURDAT2 data (old storms get updated wind speeds)
- Tropycal library may cache data
- Timing of "best track" finalization vs real-time data

## ✅ Verification Checklist

- [ ] Selected 6 diverse storms (3 Atlantic, 3 Pacific)
- [ ] Recorded tracker values from Excel
- [ ] Downloaded official NOAA data
- [ ] Compared wind speeds (must match exactly)
- [ ] Compared ACE values (within 5% target)
- [ ] Compared durations (within 1 day target)
- [ ] Documented results in VERIFICATION_REPORT.md
- [ ] Investigated any significant discrepancies
- [ ] Committed updated report to git

## 📊 Success Criteria

**Your tracker is accurate if:**
- ✅ Wind speeds: 100% exact match
- ✅ ACE values: 80%+ within 5% tolerance
- ✅ Duration: 90%+ within 1 day

**Historical verification results:**
- April 2026 verification: 100% wind, 83% ACE (excellent), 100% duration

## Resources

- NOAA HURDAT2: https://www.nhc.noaa.gov/data/#hurdat
- NHC Storm Reports: https://www.nhc.noaa.gov/data/tcr/
- Tropycal Docs: https://tropycal.github.io/tropycal/
- NOAA ACE Info: https://www.nhc.noaa.gov/climo/

**Remember:** Small discrepancies (<5%) are normal and acceptable. Exact matches are ideal but not always achievable due to data revision timing.

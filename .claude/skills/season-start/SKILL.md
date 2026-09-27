---
name: season-start
description: Steps to verify ace-tracker when new hurricane season starts
disable-model-invocation: false
---

# New Hurricane Season Start Checklist

- **Atlantic:** June 1 – November 30
- **Eastern Pacific:** May 15 – November 30

## 1. Verify Tropycal Has Current Year Data

```bash
python3 -c "
import tropycal.tracks as tracks
basin = tracks.TrackDataset(basin='north_atlantic', source='hurdat')
print(f'Latest year: {max(basin.df.year)}')
print(f'Latest storms: {list(basin.df[basin.df.year == max(basin.df.year)].name.unique())}')
"
```

Should show current year and any named storms so far.

## 2. Run Full Tracker

```bash
python3 ace_tracker.py
```

Verify:
- Current season year appears in console
- If no storms yet: ACE shows 0.0
- All pages in `data/` generate successfully (dashboard, history, records, What Is ACE?)

## 3. Verify the Generated Pages

Open the pages in `data/` for both the Atlantic and E/C Pacific tabs:

- **Dashboard** (`ACE_Dashboard.html`): current year in the heading and page title, season progress bar dates correct, storm table present (or the no-storms-yet view)
- **History** (`history.html`): previous year's row present with its storms and NHC report links, all years 1991–present, current year marked active
- **Records** (`records.html`): records include the previous season

## 4. Check First Named Storm

When the first named storm forms, run the tracker and verify:
- Name appears correctly
- ACE > 0 (if storm reached TS strength)
- Duration shows in days, category correct

**Common first storm issues:**
- Duration "N/A" → Tropycal data lag (6–24 hrs) — recheck later
- ACE 0.0 → Storm hasn't reached 34 kt TS threshold yet
- Storm missing → Tropycal lag — recheck in 6 hours

## 5. Run Tests

```bash
python3 test_ace_tracker.py
```

All tests must still pass.

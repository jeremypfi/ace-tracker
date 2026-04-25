---
name: season-start
description: Steps to verify ace-tracker when new hurricane season starts
disable-model-invocation: false
---

# New Hurricane Season Start Checklist

When a new hurricane season begins (Atlantic: June 1, Pacific: May 15), follow these steps to ensure ace-tracker is ready.

## Season Start Dates

- **Atlantic Hurricane Season:** June 1 - November 30
- **Eastern Pacific Hurricane Season:** May 15 - November 30

## 1. Verify Tropycal Data Availability

Check if Tropycal has been updated with the new season:

```bash
python3 -c "
import tropycal.tracks as tracks
basin = tracks.TrackDataset(basin='north_atlantic', source='hurdat')
print(f'Latest year: {max(basin.df.year)}')
print(f'Latest storms: {list(basin.df[basin.df.year == max(basin.df.year)].name.unique())}')
"
```

**Expected:** Should show current year and any named storms so far.

## 2. Run Full Tracker Test

```bash
python3 ace_tracker.py
```

**Verify:**
- Script completes without errors
- Console shows current season year (e.g., 2026)
- If no storms yet: ACE should be 0.0 for current season
- If storms exist: Storms should appear in output
- Both Excel files generate successfully
- HTML dashboard shows current year

## 3. Check Excel Spreadsheets

Open the generated files:
- `data/ACE_Tracker_Atlantic.xlsx`
- `data/ACE_Tracker_Pacific.xlsx`

**Verify in "Summary" tab:**
- Current year shows at top
- Season dates are correct
- ACE calculation shows (even if 0.0)
- Historical ranking includes previous year

**Verify in "Current Season Storms" tab:**
- If storms exist: They appear with correct data
- If no storms yet: Tab shows headers but no storm rows
- Current year storms highlighted in yellow

**Verify in "Historical Storms" tab:**
- Previous year's storms are now in historical data
- Current year storms (if any) are highlighted
- All years from 1991 to current year present

**Verify in "Yearly Totals" tab:**
- Previous year appears in the rankings
- Current year shows at top (even with 0.0 ACE if no storms)
- Rankings are correct

## 4. Check First Named Storm

When the first named storm of the season forms:

```bash
python3 ace_tracker.py
```

**Verify the first storm:**
- Name appears correctly (e.g., "Alberto" for Atlantic)
- ACE value calculated (should be > 0)
- Duration shows in days
- Max wind speed recorded
- Category determined (TD, TS, or Cat 1-5)

**Common first storm issues:**
- Duration showing "N/A" → Tropycal may not have complete data yet
- ACE showing 0.0 → Storm may not have reached TS strength yet (34 kt minimum)
- Storm not appearing → Tropycal data may lag by 6-24 hours

## 5. Data Source Verification

**Check Tropycal is working:**
- Go to: https://github.com/tropycal/tropycal
- Check for recent updates/releases
- Verify HURDAT2 data source is accessible

**Check NOAA NHC:**
- Go to: https://www.nhc.noaa.gov
- Verify advisories are being issued
- Compare storm names with your output

## 6. Test Discord Update

**Verify "Discord Update" tab:**
- Format looks correct
- Storm count matches
- ACE values match Summary tab
- Copy a few lines and test in Discord (formatting should work)

## 7. Update README (Optional)

If it's a new year, consider updating:

```markdown
## 🌊 2026 Hurricane Season

Good luck tracking the storms! 🌀
```

Change year to current season.

## 8. Run Tests

Confirm nothing broke:

```bash
python3 test_ace_tracker.py
```

All 25 tests should still pass.

## 9. Commit Season Start Verification

If you made any updates:

```bash
git add README.md  # Only if you updated it
git commit -m "Verify ace-tracker for 2026 hurricane season

Confirmed:
- Tropycal data availability for 2026
- Tracker runs successfully
- First storm (if any) appears correctly
- All tests passing

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
git push origin main
```

## ✅ Season Start Checklist

- [ ] Tropycal has current year data
- [ ] Tracker runs without errors
- [ ] Excel files generate correctly
- [ ] All tabs show current year
- [ ] Previous year in historical data
- [ ] First storm appears (when formed)
- [ ] Discord update format works
- [ ] All tests pass
- [ ] README updated (optional)

## 📊 Season Statistics to Monitor

Throughout the season, interesting milestones:
- **First named storm** (usually late May - early June)
- **ACE reaches "normal" threshold** (122.5 Atlantic, 132.0 Pacific)
- **First major hurricane** (Cat 3+)
- **Season classification** (Below/Near/Above Normal, Extremely Active)
- **Historical ranking** (where does this season rank?)

**Happy tracking!** 🌀

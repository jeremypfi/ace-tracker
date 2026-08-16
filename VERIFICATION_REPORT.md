# Data Verification Report

## Sprint 0 — Data accuracy fixes (Aug 15, 2026)

Verified after unifying the ACE formula (dashboard + history now both use the
synoptic-time calculation, `ace_from_winds`) and fixing the season-rank
double-count.

### Per-storm ACE vs official Tropycal/HURDAT2 values

| Storm | Basin | Max wind | Official ACE | Tracker ACE | Diff | Duration |
|---|---|---|---|---|---|---|
| Katrina 2005 | Atlantic | 150 kt ✅ | 20.0050 | 20.0050 | 0.00% ✅ | 8d ✅ |
| Sandy 2012 | Atlantic | 100 kt ✅ | 13.6675 | 13.6675 | 0.00% ✅ | 10d ✅ |
| Ida 2021 | Atlantic | 130 kt ✅ | 10.5800 | 10.5800 | 0.00% ✅ | 10d ✅ |
| Patricia 2015 | E. Pacific | 185 kt ✅ | 17.3225 | 17.3225 | 0.00% ✅ | 5d ✅ |
| Rosa 2018 | E. Pacific | 130 kt ✅ | 16.9525 | 16.9525 | 0.00% ✅ | 8d ✅ |
| Genevieve 2026 (BTK, current season) | E. Pacific | 140 kt ✅ | 26.1175 | 26.1175 | 0.00% ✅ | 12d ✅ |

**Summary: 6/6 wind exact, 6/6 ACE within 5% (all exact), 6/6 duration within 1 day.**

### Season rank

1991–2026 inclusive = **36 seasons**. Generated dashboard now reports
"#N of 36" (previously "of 37" due to the current year being counted twice).
Dashboard and history pages report identical per-storm ACE for all 2026 storms
(spot-checked Genevieve, Fausto, Lala, Hernan on both pages).

### Method

Official values pulled fresh via `tropycal.tracks.TrackDataset(source='hurdat',
include_btk=True)`; tracker values computed via
`ace_from_winds(_extract_synoptic_winds(storm))` — the single formula now used
by every code path.

Previous baseline (April 2026): 100% wind, 83% ACE within 5%, 100% duration.
This run improves ACE agreement to 100% exact.

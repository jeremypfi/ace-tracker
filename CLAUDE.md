# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

ACE Tracker tracks **Accumulated Cyclone Energy (ACE)** for Atlantic and East & Central Pacific hurricane seasons, generating an HTML dashboard and history page from NOAA HURDAT2 data (1991–present) via the Tropycal library.

## ACE Domain Knowledge

- **Formula**: ACE = Σ(V²max) × 10⁻⁴ — wind speeds always in **knots**, never mph
- Only counted at synoptic times: `0000`, `0600`, `1200`, `1800` UTC
- Only counts when storm status is `TS` (Tropical Storm), `HU` (Hurricane), or `SS` (Subtropical Storm)
- Minimum wind for named storm: 34 knots

```python
SYNOPTIC_TIMES = ['0000', '0600', '1200', '1800']
ACE_STATUSES = ['TS', 'HU', 'SS']
MIN_NAMED_STORM_WIND = 34  # knots
START_YEAR = 1991
```

## NOAA Season Classifications

Same thresholds for both Atlantic and Eastern Pacific:

| Classification | ACE |
|---|---|
| Below Normal | < 73 |
| Near Normal | 73–126 |
| Above Normal | 126–159 |
| Extremely Active | 159+ |

## Development Commands

```bash
python3 ace_tracker.py        # generates HTML files in data/
python3 test_ace_tracker.py   # 34 tests — ALL must pass before committing
pip3 install -r requirements.txt
```

## Architecture

`ace_tracker.py` (~2,600 lines): fetches via Tropycal → calculates ACE at synoptic times → generates HTML dashboard + history page in `data/`.

`test_ace_tracker.py`: 34 tests across 10 classes — categorization, ACE formula, NOAA classification, storm finalization, yearly totals, similar-season matching.

## Repository Rules

- **Only @jeremypfi can approve and merge PRs** (CODEOWNERS + branch protection)
- All 34 tests must pass before committing — run `/pre-commit` skill
- Never commit `data/*.html` — gitignored
- **Before opening any PR:** fetch origin and merge main into the branch first:
  ```bash
  git fetch origin
  git merge origin/main --no-edit
  git push
  ```

## Known Issue

Tropycal `_version.py` uses `pkg_resources`, removed in setuptools 82+. Pinned `setuptools<82` in `requirements.txt`. Revisit when tropycal ships a fix.

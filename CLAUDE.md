# CLAUDE.md

ACE Tracker: Accumulated Cyclone Energy for Atlantic and East/Central Pacific seasons. Builds an HTML dashboard from NOAA HURDAT2 (1991-present) via Tropycal.
Modules: `ace_data.py` (fetch, ACE math, domain constants), `ace_html.py` (page rendering), `ace_tracker.py` (CLI entrypoint).

## Domain rules

- ACE = sum(Vmax^2) x 10^-4. Wind speeds always in **knots**, never mph.
- Count only synoptic times (0000, 0600, 1200, 1800 UTC) when status is `TS`, `HU` or `SS`.
- Constants and NOAA season thresholds live in `ace_data.py`. Change them there only, and update the tests.

## Development Commands

```bash
python3 verify_pr.py          # unit tests + syntax check + live tracker run; must pass before any commit
python3 verify_pr.py --fast   # unit tests + syntax check only
python3 ace_tracker.py        # generates HTML files in data/
pip3 install -r requirements.txt
```

## Repository Rules

- **Only @jeremypfi can approve and merge PRs** (CODEOWNERS + branch protection)
- Before committing: run `python3 verify_pr.py`, then check `git diff` for keys, personal paths and `.env` files. The `/pre-commit` skill does the same.
- Never commit `data/*.html` (gitignored)

## Known Issue

Tropycal's `_version.py` imports `pkg_resources`, which setuptools has deprecated and plans to remove. `requirements.txt` pins `setuptools<85`. `pkg_resources` still imports at setuptools 84.0.0 (checked 2026-10-03). Revisit when tropycal ships a fix.

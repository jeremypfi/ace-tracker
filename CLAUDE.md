# CLAUDE.md

ACE Tracker: Accumulated Cyclone Energy for Atlantic and East/Central Pacific seasons. Builds an HTML dashboard from NOAA HURDAT2 (1991-present) via Tropycal.
Modules: `ace_data.py` (fetch, ACE math, domain constants), `ace_html.py` (page rendering), `ace_feeds.py` (JSON API + RSS), `ace_cards.py` (share-card image), `ace_assets.py` (CSS/JS shared by pages), `ace_storm_pages.py` (per-storm pages), `ace_tracker.py` (CLI entrypoint).
`ace_data.build_season_payload()` is the single source of per-basin season data (plain data, no HTML, does the render-time NHC fetches). Pages, `ace_feeds.py` and any new output should consume it rather than re-deriving numbers from `process_basin()` results.

## Domain rules

- ACE = sum(Vmax^2) x 10^-4. Wind speeds always in **knots**, never mph.
- Count only synoptic times (0000, 0600, 1200, 1800 UTC) when status is `TS`, `HU` or `SS`.
- Constants and NOAA season thresholds live in `ace_data.py`. Change them there only, and update the tests.

## Development Commands

```bash
uv run python verify_pr.py          # unit tests + syntax check + live tracker run; must pass before any commit
uv run python verify_pr.py --fast   # unit tests + syntax check only
uv run python ace_tracker.py        # generates HTML files in data/
uv venv --python 3.12 && uv pip install -r requirements.txt   # one-time setup; 3.13+ unsupported
```

## Testing

- Use `unittest` in `test_ace_tracker.py` for logic, calculations and generated HTML strings.
- Use Playwright only for behavior that needs a real browser and JS: tooltip positioning, tab switching, the no-JS fallback.

## Repository Rules

- **Only @jeremypfi can approve and merge PRs** (CODEOWNERS + branch protection)
- Before committing: run `uv run python verify_pr.py`, then check `git diff` for keys, personal paths and `.env` files. The `/pre-commit` skill does the same.
- Never commit `data/*.html`, `data/api/` or `data/feed.xml` (gitignored)
- `api/v1/season.json` is a public contract: add fields freely, but a rename or removal needs `api/v2/`

## Known Issue

Tropycal's `_version.py` imports `pkg_resources`, which setuptools has deprecated and plans to remove. `requirements.txt` pins `setuptools<85`. `pkg_resources` still imports at setuptools 84.0.0 (checked 2026-10-03). Revisit when tropycal ships a fix.

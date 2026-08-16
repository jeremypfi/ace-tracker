# ACE Tracker

**Atlantic & Eastern Pacific Hurricane ACE Tracker**

Tracks Accumulated Cyclone Energy (ACE) for Atlantic and Eastern Pacific hurricane seasons with storm-by-storm data from 1991 onward. Publishes a live web dashboard updated every 3 hours during hurricane season.

[![Tests](https://github.com/jeremypfi/ace-tracker/actions/workflows/tests.yml/badge.svg)](https://github.com/jeremypfi/ace-tracker/actions/workflows/tests.yml)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Ko-fi](https://img.shields.io/badge/Support-Ko--fi-ff5e5b?logo=ko-fi)](https://ko-fi.com/aceofcanes)

---

## Live Site

| Page | URL |
|---|---|
| Current Season Dashboard | https://aceofcanes.com |
| Season History (1991–present) | https://aceofcanes.com/history.html |

Updated every 3 hours during hurricane season (Eastern Pacific: May 15 – Nov 30 · Atlantic: Jun 1 – Nov 30).

---

## Features

- **Real-time tracking** — current season ACE updated every 3 hours via NHC best track data
- **Dual basin** — Atlantic and Eastern Pacific, toggle between them on each page
- **Dark/light mode** — defaults to system preference for first-time visitors, persisted across sessions after that
- **Season progress bar** — shows current day and percent complete
- **Landfall data** — each storm shows where it made landfall and its intensity at the moment of impact (not just peak). Multi-landfall storms show all locations (e.g. `Florida (Cat 1) · Louisiana (Cat 3)`). Storms that never made landfall are labeled **Fish Storm**
- **NHC development alert** — amber banner appears when NHC is tracking an area with Medium (≥40%) or High (≥70%) formation chances, with direct link to the NHC Tropical Weather Outlook
- **Honest season comparisons** — Season Insights show both same-date historical averages (what's typical by this point in the season) and full-season averages, so early-season numbers aren't misleadingly compared against totals that take six months to accumulate
- **Storm track maps** — interactive Leaflet maps per storm with intensity color-coding; expandable inline on the dashboard, with a loading indicator while tiles load
- **Shareable storm links** — copy a direct link to any storm on the dashboard via the 🔗 button on each row; opening the link auto-switches basin and expands that storm
- **NHC forecast cone** — active storms show their official 5-day forecast cone graphic, fetched from NHC once per run and served from our own domain (not hotlinked)
- **Season history page** — all seasons 1991–present in a sortable table with classification badges, top-5 highlights, per-year storm accordions with landfall data, and a long-term average row
- **Similar seasons** — finds the 3 closest historical seasons by ACE accumulated through the same date
- **Pace rank** — shows where this season ranks among all historical seasons at this same calendar date, alongside the full-season rank
- **NOAA classifications** — Below Normal / Near Normal / Above Normal / Extremely Active
- **Season projection widget** — shows the daily ACE rate needed for the rest of the season to reach each remaining NOAA classification by Nov 30

---

## What is ACE?

**Accumulated Cyclone Energy (ACE)** measures total hurricane season activity by combining storm intensity and duration. It's calculated by squaring the maximum sustained wind speed (in knots) at each 6-hour synoptic time when the system is at tropical storm strength or higher, then summing across all storms.

**Formula:** ACE = Σ(V²max) × 10⁻⁴

A long-lived major hurricane contributes far more ACE than a brief tropical storm. NOAA uses seasonal ACE totals to classify activity levels.

### NOAA Season Classifications (both basins)

| Classification | ACE |
|---|---|
| Extremely Active | ≥ 159 |
| Above Normal | 126 – 159 |
| Near Normal | 73 – 126 |
| Below Normal | < 73 |

---

## Quick Start

### Requirements

- Python 3.10 or higher
- Internet connection (for fetching live data)

### Installation

```bash
git clone https://github.com/jeremypfi/ace-tracker.git
cd ace-tracker
pip3 install -r requirements.txt
```

### Run

```bash
python3 ace_tracker.py
```

Generates in `data/`:
- `ACE_Dashboard.html` — current season dashboard (open in any browser)
- `history.html` — all-seasons history page

### Run tests

```bash
python3 test_ace_tracker.py
```

All 59 tests must pass before committing. Use the `/pre-commit` skill in Claude Code for the full checklist.

---

## Project Structure

```
ace-tracker/
├── ace_data.py             # Data fetch, ACE calc, plain-text report generation
├── ace_html.py             # Dashboard + history HTML rendering
├── ace_tracker.py          # CLI entrypoint — wires ace_data.py + ace_html.py together
├── test_ace_tracker.py     # 59 unit + smoke tests
├── requirements.txt        # Python dependencies
├── ace.png                 # Site logo (favicon + OG image)
├── ace_preview.png         # Social share preview image (copied into data/ at publish time)
├── landfall_cache.json     # Cached landfall geocoding results (gitignored, built by CI)
├── CNAME                   # Custom domain for GitHub Pages (aceofcanes.com)
├── robots.txt              # Search engine crawl rules
├── sitemap.xml             # Sitemap for search engine indexing
├── CLAUDE.md               # Project instructions for Claude Code
├── CONTRIBUTING.md         # Contribution guidelines
├── images/                 # Reference/marketing images
├── .claude/skills/          # /pre-commit, /season-start, /verify-data
├── .github/
│   ├── workflows/
│   │   ├── tests.yml       # CI: runs tests on push/PR (Python 3.10, 3.11, 3.12)
│   │   └── publish.yml     # Scheduled: generates and deploys dashboard every 3 hours
│   ├── dependabot.yml      # Automated dependency updates
│   └── CODEOWNERS          # @jeremypfi must approve all PRs
├── SECURITY.md
└── data/                   # Generated output (html gitignored, images committed)
    ├── ace.png
    ├── ACE_Dashboard.html
    ├── history.html
    └── cones/              # NHC forecast cone images, fetched fresh each run (gitignored)
```

---

## Data Sources

- **[NOAA HURDAT2](https://www.nhc.noaa.gov/data/#hurdat)** — official historical best-track database (1991–present) via the [Tropycal](https://tropycal.github.io/tropycal/) library
- **[NHC Real-time Best Track](https://www.nhc.noaa.gov/data/#hurdat)** — current season preliminary data (`include_btk=True` in Tropycal), updated continuously during active storms
- **[NHC Tropical Weather Outlook](https://www.nhc.noaa.gov/gtwo.php)** — XML feeds (`TWOAT.xml` / `TWOEP.xml`) parsed every run for active disturbances with development potential
- **[NHC CurrentStorms.json](https://www.nhc.noaa.gov/CurrentStorms.json)** — active storm metadata used to locate and cache each storm's 5-day forecast cone graphic
- **[NOAA CPC](https://www.cpc.ncep.noaa.gov/products/outlooks/background_information.shtml)** — season classification thresholds and 1991–2020 climatological normals
- **[Natural Earth](https://www.naturalearthdata.com/)** — 10m shapefiles (via Cartopy) for offline landfall geocoding

---

## How Landfall Detection Works

Historical storms (completed seasons) use the official HURDAT2 `'L'` landfall markers, which record the exact time and position of each landfall. These markers aren't added to the real-time best-track data until the post-season analysis, so active-season storms use a geographic fallback: track points are checked against Natural Earth shapefiles using exact point-in-polygon containment. Results are cached in `landfall_cache.json` and persisted via GitHub Actions cache so geocoding only runs for new or updated storms.

---

## Configuration

Key constants, mostly in `ace_data.py` (`OUTPUT_FOLDER` is the one exception — it stays in `ace_tracker.py` since only `main()` uses it):

| Constant | Purpose |
|---|---|
| `START_YEAR` | Earliest year included in historical data (default: 1991) |
| `OUTPUT_FOLDER` | Where HTML files are saved (default: `data/`) — defined in `ace_tracker.py` |
| `LANDFALL_CACHE_PATH` | Path to the landfall geocoding cache (default: repo root) |
| `BASINS` | Normal ACE values and average storm counts per basin |
| `BACKUP_DATA` | Fallback season data used if NOAA is unreachable |

---

## Troubleshooting

**Script can't fetch data**
The tracker falls back to `BACKUP_DATA` automatically. You'll see:
```
✗ Error loading Tropycal data → Using backup data (yearly totals only)
```

**Landfall cache miss on first CI run**
The `landfall_cache.json` is built on the first run and cached by GitHub Actions. The first run after a fresh clone will geocode all historical storms (~1 min extra). Every subsequent run reads from cache.

**`pkg_resources` deprecation warning**
Tropycal uses `pkg_resources` which is deprecated in setuptools 81+. `requirements.txt` pins `setuptools<84` as a workaround. Monitor [Tropycal releases](https://github.com/tropycal/tropycal/releases) for a fix.

---

## Credits

- Built with [Claude Code](https://claude.ai/claude-code) (Anthropic)
- Data from [NOAA National Hurricane Center](https://www.nhc.noaa.gov/) via [Tropycal](https://tropycal.github.io/tropycal/)
- Maps powered by [Leaflet](https://leafletjs.com/)
- Inspired by hurricane tracking communities

---

**Questions or issues?** Open an issue on GitHub or reach out to [@jeremypfi](https://github.com/jeremypfi)

# ACE Tracker

**Atlantic & Eastern Pacific Hurricane ACE Tracker**

Tracks Accumulated Cyclone Energy (ACE) for Atlantic and Eastern Pacific hurricane seasons with storm-by-storm data from 1991 onward. Publishes a live web dashboard updated every 6 hours during hurricane season.

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

Updated every 6 hours during hurricane season (Eastern Pacific: May 15 – Nov 30 · Atlantic: Jun 1 – Nov 30).

---

## Features

- **Real-time tracking** — current season ACE updated every 6 hours via NHC best track data
- **Dual basin** — Atlantic and Eastern Pacific, toggle between them on each page
- **Live web dashboard** — published to [aceofcanes.com](https://aceofcanes.com) automatically; dark/light mode toggle
- **Season progress bar** — shows current day of season and percent complete; marks past seasons as complete
- **Season history page** — all seasons 1991–present in a sortable table with classification badges, top-5 highlights, and a long-term average row; similar seasons link directly to matching history rows
- **Excel spreadsheets** — two workbooks generated each run with 5 tabs each:
  - Summary (season overview, stats, similar years)
  - Current Season Storms (storm-by-storm ACE breakdown)
  - Historical Storms (all storms since 1991)
  - Yearly Totals (ranked historical seasons)
  - Discord Update (copy/paste ready)
- **Offline fallback** — backup data for the current season if NOAA is unreachable
- **NOAA classifications** — Below Normal / Near Normal / Above Normal / Extremely Active

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
- `ACE_Tracker_Atlantic.xlsx`
- `ACE_Tracker_Pacific.xlsx`
- `ACE_Dashboard.html` — open in any browser
- `history.html` — all-seasons history page

### Run tests

```bash
python3 test_ace_tracker.py
```

All 25 tests must pass before committing.

---

## Project Structure

```
ace-tracker/
├── ace_tracker.py          # Main script — data fetch, ACE calc, HTML/Excel generation
├── test_ace_tracker.py     # 25 unit tests
├── requirements.txt        # Python dependencies
├── ace.png                 # Site logo (favicon + header)
├── CNAME                   # Custom domain for GitHub Pages (aceofcanes.com)
├── robots.txt              # Search engine crawl rules
├── sitemap.xml             # Sitemap for search engine indexing
├── .github/
│   ├── workflows/
│   │   ├── tests.yml       # CI: runs tests on push/PR (Python 3.10, 3.11, 3.12)
│   │   └── publish.yml     # Scheduled: generates and deploys dashboard every 6 hours
│   ├── dependabot.yml      # Automated dependency updates
│   └── CODEOWNERS          # @jeremypfi must approve all PRs
├── SECURITY.md
└── data/                   # Generated output (xlsx/html gitignored, ace.png committed)
    ├── ace.png
    ├── ACE_Tracker_Atlantic.xlsx
    ├── ACE_Tracker_Pacific.xlsx
    ├── ACE_Dashboard.html
    └── history.html
```

---

## Data Sources

- **[NOAA HURDAT2](https://www.nhc.noaa.gov/data/#hurdat)** — official historical best-track database (1991–present) via the [Tropycal](https://tropycal.github.io/tropycal/) library
- **[NHC Real-time Best Track](https://www.nhc.noaa.gov/data/#hurdat)** — current season preliminary data (`include_btk=True` in Tropycal), updated continuously during active storms
- **[NOAA CPC](https://www.cpc.ncep.noaa.gov/products/outlooks/background_information.shtml)** — season classification thresholds and 1991–2020 climatological normals

---

## Configuration

Key constants at the top of `ace_tracker.py`:

| Constant | Purpose |
|---|---|
| `START_YEAR` | Earliest year included in historical data (default: 1991) |
| `OUTPUT_FOLDER` | Where Excel and HTML files are saved (default: `data/`) |
| `BASINS` | Normal ACE values and average storm counts per basin |
| `BACKUP_DATA` | Fallback season data used if NOAA is unreachable |

---

## Troubleshooting

**`No module named openpyxl`**
```bash
pip3 install -r requirements.txt
```

**Script can't fetch data**
The tracker falls back to `BACKUP_DATA` automatically. You'll see:
```
✗ Error loading Tropycal data → Using backup data (yearly totals only)
```

**`pkg_resources` deprecation warning**
Tropycal 1.4 uses `pkg_resources` which is deprecated in setuptools 81+. `requirements.txt` pins `setuptools<82` as a workaround. Monitor [Tropycal releases](https://github.com/tropycal/tropycal/releases) for a fix.

---

## Credits

- Built with [Claude Code](https://claude.ai/claude-code) (Anthropic)
- Data from [NOAA National Hurricane Center](https://www.nhc.noaa.gov/) via [Tropycal](https://tropycal.github.io/tropycal/)
- Inspired by hurricane tracking communities

---

**Questions or issues?** Open an issue on GitHub or reach out to [@jeremypfi](https://github.com/jeremypfi)

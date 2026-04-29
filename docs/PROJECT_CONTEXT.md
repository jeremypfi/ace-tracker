# ACE Tracker — Project Context
> One source of truth for Claude Code and Claude.ai. Keep this file current. Last updated: 2026-04-28.

---

## About Jeremy

- **Role:** New Director of QA, 20+ years testing software
- **This project:** Hobby/fun — staying hands-on with tech, no hard deadlines, no external dependencies
- **Discord handle:** AceOfCanes (weather community)
- **Standards:** Holds Claude to a professional QA standard. Claude should verify before presenting, check related work proactively, and never wait to be asked. Jeremy should not be doing Claude's QA.
- **Preferences:** Dark UI themes. Terse responses. No trailing summaries of what Claude just did — he can read the diff.
- **Monetization goal:** Cover hosting costs (~$12/yr domain) only. Ko-fi is fine, keep it unobtrusive.

---

## How Claude Should Work With Jeremy

### Self-QA — Mandatory
Before closing any turn, run this checklist. Not optional.

1. **Impact Analysis** — What files, docs, or outputs reference the thing just changed? List them before touching anything.
2. **Consistency Check** — After making changes, open every related file and verify nothing contradicts what was just changed. Update stale files in the same turn without being asked.
3. **Assumption Audit** — Are estimates based on Jeremy's review time (not implementation time)? Is anything listed as "user's job" that Claude could actually do?
4. **Verification Gate** — Did Claude actually run/test it, or just assume it works?
5. **Completeness Check** — Are there obvious follow-on steps that should be done in this same turn?

### Defect Log (real misses — don't repeat these)
- Changed one planning doc but didn't update the others with overlapping content → Now: when any `docs/` file changes, check all others for conflicts before closing the turn
- Wrote time estimates based on manual developer workflow, not Claude-assisted → Now: explicitly state who the estimate is based on before writing any estimate
- Listed data verification as "user's time" when Claude can do it → Now: for every "user's responsibilities" item, ask "can Claude actually do this?" first

---

## Project Overview

ACE Tracker is a Python tool that generates Excel spreadsheets and an HTML dashboard tracking **Accumulated Cyclone Energy (ACE)** for Atlantic and Eastern Pacific hurricane seasons, using historical data from 1991 onward.

**The goal:** Expand this into a public web dashboard at `aceofcanes.com`, auto-updating every 6 hours during hurricane season, served via GitHub Pages at zero hosting cost.

**Critical constraint:** Excel spreadsheet output must continue working throughout the entire web build. Both outputs (Excel + website) run from the same `ace_tracker.py` script and must always work in parallel. Never sacrifice one for the other. Do not stop spreadsheet updates until Jeremy explicitly says to.

---

## Domain Knowledge

### ACE Calculation
- **Formula:** ACE = Σ(V²max) × 10⁻⁴
- Wind speeds are ALWAYS in **knots**, never mph
- Only counted at synoptic times: 0000, 0600, 1200, 1800 UTC
- Only when storm status is: TS (Tropical Storm), HU (Hurricane), SS (Subtropical Storm)
- Minimum wind for named storm: 34 knots

### NOAA Season Classifications (both basins)
- Below Normal: < 73 ACE
- Near Normal: 73–126 ACE
- Above Normal: 126–159 ACE
- Extremely Active: 159+ ACE

### Key Constants
```python
SYNOPTIC_TIMES = ['0000', '0600', '1200', '1800']
ACE_STATUSES = ['TS', 'HU', 'SS']
MIN_NAMED_STORM_WIND = 34  # knots
START_YEAR = 1991
```

---

## Repository Structure

```
ace-tracker/
├── ace_tracker.py              # Core engine (1322 lines) — generates Excel + HTML
├── test_ace_tracker.py         # 25 tests — ALL must pass before committing
├── requirements.txt            # openpyxl, tropycal, shapely, cartopy
├── templates/                  # Jinja2 templates (to be built in Session 3)
├── data/                       # Generated output (not committed)
│   ├── ACE_Dashboard_Mockup.html   # Dark-theme design target
│   ├── ACE_Tracker_Atlantic.xlsx
│   ├── ACE_Tracker_Pacific.xlsx
│   └── ACE_Dashboard.html
├── docs/
│   ├── ARCHITECTURE.md
│   ├── REQUIREMENTS.md
│   ├── PROJECT_PLAN.md
│   ├── ROADMAP.md
│   ├── SEASON_2026_PLAN.md
│   └── PROJECT_CONTEXT.md      # This file
├── .github/
│   ├── workflows/
│   │   ├── tests.yml           # CI — runs on push/PR, Python 3.10 + 3.11
│   │   └── publish.yml         # Cron deploy scaffold (deploy steps still commented out)
│   ├── dependabot.yml          # Weekly pip + Actions scanning
│   └── CODEOWNERS              # @jeremypfi required on all PRs
└── CLAUDE.md                   # Project instructions for Claude Code
```

---

## Current State (as of 2026-04-28)

### Done
- Excel spreadsheets generating correctly (Atlantic + Pacific, 5 tabs each)
- HTML dashboard generating (dark theme mockup at `data/ACE_Dashboard_Mockup.html`)
- CI green on Python 3.10 and 3.11
- Security hardening: Dependabot, workflow permissions, timeouts, concurrency groups
- All 5 Dependabot PRs merged (cartopy, openpyxl, shapely, actions/checkout v6, actions/setup-python v6)
- `publish.yml` scaffold committed (deploy steps commented out — TODO Session 1)
- All 5 planning docs in `docs/`
- CODEOWNERS in place (only @jeremypfi can merge)
- `dependencies` label created for Dependabot PRs

### Not Done Yet
- GitHub Pages not enabled (requires Jeremy in repo Settings UI)
- `publish.yml` deploy steps still commented out
- Domain not registered yet (`aceofcanes.com` on Namecheap recommended)
- Cloudflare proxy not set up (add after domain is live for bandwidth headroom)
- No Jinja2 templates yet (Session 3)
- No realtime data failover chain yet (Session 2)
- Branch protection rules not enabled in GitHub Settings (CODEOWNERS exists but not enforced — Jeremy must enable in UI)

### Known Issues / Risks
- Tropycal `_version.py` uses `pkg_resources`, which was removed from setuptools 81+. Worked around by pinning `setuptools<81` in `requirements.txt`. CI tests 3.10/3.11/3.12. Revisit when tropycal ships a fix or replaces setuptools_scm version detection.
- HURDAT2 lag: 2025 season data won't be in HURDAT2 until spring 2026. Historical comparison will show 2025 as incomplete until then — needs disclosure on site.
- No rollback plan for gh-pages yet — a bad cron run could push broken HTML. Add validation step before deploy (check HTML file exists and is >1kb) when activating publish.yml.

---

## Architecture Decisions Made

| Decision | Rationale |
|---|---|
| GitHub Pages (static) | Free, zero maintenance, correct for pre-generated HTML |
| Jinja2 templates | Python-native, no new runtime dependencies |
| 3-source failover chain | Never go blank mid-season: Tropycal → NHC ATCF → Climatlas → cache |
| `aceofcanes.com` on Namecheap | Tied to Jeremy's Discord identity, ~$12/yr, free WHOIS privacy |
| Cloudflare proxy (planned) | Free CDN, unlimited bandwidth — buffer before GitHub Pages limits matter |
| Ko-fi only monetization | Unobtrusive, covers domain cost, no ads |
| SEO via meta/OG tags in templates | OG tags matter more than Google for Discord community sharing |
| Static HTML scales well | At Tropical Tidbits-level traffic, static files + Cloudflare CDN cost ~$20-50/mo max |
| Excel + website parallel | Same `ace_tracker.py` run generates both — additive, never either/or |
| CSU Tropical = verification only | Derived from NHC (not independent); terms of use unclear for live scraping |

---

## Session Plan

> All estimates = Jeremy's review time. Claude handles implementation, testing, and verification.

| Session | Target Date | Focus | Your Time |
|---|---|---|---|
| **1** | Apr 25 | Activate publish.yml, enable GitHub Pages, register domain | ~2 hrs |
| **2** | Apr 27 | Realtime data + 3-source failover chain | ~1 hr |
| **3** | Apr 29 | Dashboard redesign (Jinja2 templates) | ~1 hr |
| **Checkpoint** | May 14 | E. Pacific season — site live, auto-updating, new design | — |
| **4** | May 1–15 | History + Records pages | ~1 hr |
| **5** | May 1–15 | Compare + About + Recap pages | ~1 hr |
| **6** | May 1–15 | PDI + RI Events + Landfall ACE metrics | ~1 hr |
| **7** | May 1–31 | SEO, polish, final QA | ~1.5 hrs |
| **Launch** | Jun 1 | Share with weather group | — |
| **Off-season A** | Nov–May | End-of-season recap generation | ~1 hr |
| **Off-season B–D** | Nov–May | IKE / TIKE (complex, 2004+ only) | ~2 hrs |
| **Off-season E** | Nov–May | Discord webhook (30 min — code basically done) | ~30 min |

---

## Immediate Next Steps

1. **Enable branch protection in GitHub Settings UI** — CODEOWNERS exists but is not enforced yet. Anyone with write access could push directly to `main`.
2. **Activate publish.yml** — uncomment deploy steps, enable GitHub Pages in repo Settings
3. **Register `aceofcanes.com`** on Namecheap (~$12/yr, free WHOIS privacy)
4. **Add Cloudflare proxy** in front of GitHub Pages after domain is live
5. **Session 2:** Build realtime data failover chain

---

## Development Commands

```bash
# Run the tracker (generates Excel + HTML)
python3 ace_tracker.py

# Run all tests (must pass before committing)
python3 test_ace_tracker.py

# Install dependencies
pip3 install -r requirements.txt

# Regenerate planning docs as HTML/PDF
python3 docs/generate_docs.py
```

---

## Repo Rules

- **Only @jeremypfi can approve and merge PRs** (CODEOWNERS enforced)
- All 25 tests must pass before committing
- Never commit generated files (`data/*.xlsx`, `data/*.html`) — they're in `.gitignore`
- Never commit secrets, credentials, or `.env` files
- Spreadsheet output must always keep working — verify after every `ace_tracker.py` change

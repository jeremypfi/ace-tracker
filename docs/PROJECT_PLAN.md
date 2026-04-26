# ACE Tracker Web Dashboard — Project Plan

## Phases at a Glance

> **Note on estimates:** All times are *your time* — review, approval, testing on your devices, and decision-making. Claude handles implementation, data verification against NOAA HURDAT2, running the test suite, and reading CI logs. Coding tasks that would take a developer hours take Claude minutes; what takes your time is checking the output is right and approving it.

| Phase | Name | Your Time Est. | Dependency |
|---|---|---|---|
| 0 | Foundation: Data & Automation | 2–3 hrs | None |
| 1 | Dashboard Redesign | 1–2 hrs | Phase 0 |
| 2 | Multi-Page Static Site | 2–3 hrs | Phase 1 |
| 3 | PDI, RI, Landfall ACE | 1 hr | Phase 2 |
| 4 | IKE / TIKE / HSI (2004+) | 1–2 hrs | Phase 3 |
| 5 | Polish, Monetization, Domain | 1 hr | Phase 1+ |

Total estimated time from you: ~8–12 hrs across sessions. DNS wait (24–48 hrs, Session 1) is the only item that can't be compressed.

---

## Phase 0 — Foundation: Data & Automation

**Goal:** Get data updating correctly and automatically before anything goes public.
This phase must be complete before the redesigned dashboard is deployed.

### Tasks

**0.1 — Audit current data accuracy**
- Claude runs `test_ace_tracker.py`, runs `ace_tracker.py`, confirms Tropycal is fetching the right year, reports status
- Your time: reviewing the report (~5 min)

**0.2 — Implement realtime data source (Tropycal)**
- Claude investigates `tropycal.realtime` module capabilities and maintenance health (the historical module has an unpatched Python 3.12 bug 18+ months old — realtime module may have similar issues)
- Claude writes `fetch_realtime_tropycal()`, adds unit tests, verifies output against a known recent storm
- **Decision gate:** if realtime module is unreliable or unmaintained, NHC ATCF is promoted to primary (Source 1) and Tropycal realtime drops to Source 2
- Your time: reviewing Claude's reliability assessment and approving source priority order (~10 min)

**0.3 — Implement NHC ATCF fallback**
- Claude fetches NHC ATCF advisory data, writes parser + `fetch_realtime_nhc()`, adds unit tests
- Your time: approving the approach (~5 min)

**0.4 — Implement Climatlas fallback**
- Claude restores fetcher from `backup-before-tropycal` branch, writes `fetch_realtime_climatlas()`, adds unit tests
- Your time: none beyond general session review

**0.5 — Implement cache fallback + "data delayed" banner**
- Claude writes cache write/read logic, `stale=True` flag, banner in template
- Your time: confirming the banner looks right visually (~5 min)

**0.6 — Wire up failover chain**
- Claude creates `get_realtime_data(basin)`, writes integration test mocking each source failure, verifies fallback chain works, reports results
- Your time: reviewing the test results (~5 min)

**0.7 — GitHub Actions publish workflow**
- Claude writes `.github/workflows/publish.yml` with cron, date-gate, and deploy steps
- Your time: enabling GitHub Pages in repo Settings, triggering first manual dispatch to confirm it fires (~15 min)

**0.8 — Enable GitHub Pages**
- Your time: toggling the setting in repo Settings → Pages, confirming the site loads (~10 min)

**Definition of Done — Phase 0:**
- [ ] Failover chain tested: each source can fail independently without breaking the run
- [ ] Cache fallback tested: site serves last known data + banner when all sources fail
- [ ] GitHub Actions cron runs and deploys successfully without manual intervention
- [ ] All existing 25 tests still pass

---

## Phase 1 — Dashboard Redesign

**Goal:** Replace the current single-page dashboard with the designed mockup, populated with real data via Jinja2 templates.

**Prerequisites:** Phase 0 complete.

### Tasks

**1.1 — Add Jinja2 to project**
- Claude adds `jinja2` to `requirements.txt`, creates `templates/` directory
- Your time: none

**1.2 — Convert mockup to Jinja2 template**
- Claude converts `data/ACE_Dashboard_Mockup.html` into `templates/dashboard.html` and `templates/base.html` with all hardcoded values replaced by template variables
- Your time: opening the rendered dashboard and confirming it looks right (~15 min), one round of feedback if anything is off

**1.3 — Update ace_tracker.py to render templates**
- Claude builds context dict, wires Jinja2 render, removes old HTML generation, verifies output numbers match script calculations
- Your time: none beyond visual check in 1.2

**1.4 — Add "Preliminary data" disclaimer**
- Claude adds both banners; "Data delayed" is conditional on `stale` flag
- Your time: confirming banners appear/disappear correctly (~5 min)

**1.5 — Test on mobile**
- Claude tests at 375px via browser dev tools and fixes any overflow or font issues
- Your time: opening the live site on your physical phone (~10 min) — Claude cannot test on your device

**Definition of Done — Phase 1:**
- [ ] Dashboard renders from real Python data (no hardcoded values in HTML)
- [ ] Both basins toggle correctly
- [ ] Mobile layout verified
- [ ] Disclaimer and data-delayed banner present and tested

---

## Phase 2 — Multi-Page Static Site

**Goal:** Expand from one page to a full site with History, Records, Compare, and About pages.

**Prerequisites:** Phase 1 complete.

### Tasks

**2.1 — Season Archive page**
- Claude builds `templates/history.html` with sortable columns (vanilla JS), current season highlighted, all Phase 1 metrics; spot-checks historical values against HURDAT2
- Your time: reviewing the page and spot-checking a few seasons you know well (~15 min)

**2.2 — Storm Records page**
- Claude builds `templates/records.html` with top 25 by ACE/PDI/peak wind/duration, basin filter toggle
- Your time: confirming the top storms look right (~10 min)

**2.3 — Basin Comparison page**
- Claude builds `templates/compare.html` with side-by-side year stats and CSS bar chart
- Your time: confirming layout and data (~10 min)

**2.4 — About / Methodology page**
- Claude writes `templates/about.html` with all metric definitions, NOAA thresholds, source links, Ko-fi placeholder
- Your time: reviewing methodology text for accuracy, adding your actual Ko-fi link (~15 min)

**2.5 — Navigation across all pages**
- Claude updates `templates/base.html`, verifies active state logic
- Your time: clicking through pages to confirm nav works (~5 min)

**2.6 — End-of-Season Recap page**
- Claude builds `templates/recap.html` with `--recap` flag trigger, "Season closed" banner, permanent output path
- Your time: approving the layout (~10 min)

**Definition of Done — Phase 2:**
- [ ] All 6 page types generating correctly
- [ ] Navigation links work across all pages
- [ ] Historical data accurate back to 1991

---

## Phase 3 — PDI, RI, and Landfall ACE

**Goal:** Add three new metrics that are calculable from existing HURDAT2 data with minimal new dependencies.

**Prerequisites:** Phase 2 complete.

### Tasks

**3.1 — PDI (Power Dissipation Index)**
- Claude adds `calculate_pdi(storm)`, wires into aggregates and pages, adds unit tests, verifies values against published PDI benchmarks and reports
- Your time: reviewing the verification report (~10 min)

**3.2 — Rapid Intensification count**
- Claude adds `count_ri_events(storm)`, tracks per storm and season, adds unit tests, cross-checks RI events against NHC records for a sample of storms
- Your time: reviewing results (~10 min)

**3.3 — Landfall ACE**
- Claude adds `calculate_landfall_ace(storm)`, checks HURDAT2 landfall flag availability via Tropycal, adds to Records page and unit tests
- Your time: approving (~5 min)

**Definition of Done — Phase 3:**
- [ ] All three metrics verified by Claude against NOAA HURDAT2 benchmarks, report reviewed and approved
- [ ] New unit tests written and passing
- [ ] Metrics visible on Dashboard and History pages

---

## Phase 4 — IKE / TIKE / HSI (2004+ only)

**Goal:** Add wind-field-based metrics using Extended Best Track data.

**Prerequisites:** Phase 3 complete. This phase has higher complexity and is not time-critical.

### Tasks

**4.1 — Integrate Extended Best Track data**
- Claude integrates RAMMB EBTRK, maps wind radii (R34/R50/R64) to storm objects, handles `None` for pre-2004 gaps
- Your time: reviewing approach (~10 min)

**4.2 — Implement IKE calculation**
- Claude implements Powell & Reinhold (2007) volume integral, validates output against NOAA/AOML IKE calculator for 5+ storms, adds unit tests with known values, produces comparison report
- Your time: reviewing the validation report before approving publication (~15 min)

**4.3 — Implement TIKE**
- Claude sums IKE across storm lifetime, adds to aggregates
- Your time: none beyond general review

**4.4 — Surface in UI**
- Claude adds IKE/TIKE columns with "N/A" for pre-2004, "2004+ only" disclosure in column headers, top-25 lists
- Your time: confirming the disclosure is prominent enough (~5 min)

**Definition of Done — Phase 4:**
- [ ] IKE values validated by Claude against NOAA/AOML calculator for 5+ storms, comparison report reviewed and approved
- [ ] Pre-2004 storms show "N/A" (not zeros or blanks)
- [ ] 2004+ limitation clearly disclosed in UI

---

## Phase 5 — Polish, Monetization, Custom Domain

**Goal:** Get the public site ready for sharing with the weather group.

**Prerequisites:** Phase 1 complete (can run concurrently with later phases).

### Tasks

**5.1 — Ko-fi integration**
- Claude adds Ko-fi button to footer and About page with a placeholder link
- Your time: replacing the placeholder with your actual Ko-fi URL (~2 min)

**5.2 — Custom domain**
- Claude adds `CNAME` file, documents exact DNS records to configure
- Your time: purchasing the domain, pointing DNS (~20 min + 24–48 hr propagation wait)

**5.3 — SEO basics**
- Claude adds meta description tags, title tags, sitemap.xml generation
- Your time: none

**5.4 — Final visual QA**
- Claude tests in desktop Chrome and browser dev tools across all pages, checks color consistency and external links, reports issues
- Your time: final walkthrough on your phone and in Safari (~15 min) — Claude cannot test on your physical device

---

## Testing Strategy

| Layer | Tool | When |
|---|---|---|
| Unit tests | `test_ace_tracker.py` | Every commit (existing CI) |
| New metric tests | Added to `test_ace_tracker.py` | Before merging each phase |
| Failover integration test | Claude mocks each source failure, verifies chain, reports | Phase 0 completion |
| Visual QA | Browser (real device) | Phase 1 and Phase 5 |
| Data accuracy verification | Claude fetches HURDAT2, compares output values, reports discrepancies | Phase 3 and 4 |

No test should be merged without passing all 25 existing tests first.

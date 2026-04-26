# ACE Tracker Web Dashboard — Requirements

## Functional Requirements

### F1 — Data & Metrics

**F1.1 Core Metrics (Phase 1)**
- Calculate and display ACE (Accumulated Cyclone Energy) per storm and per season
- Calculate and display PDI (Power Dissipation Index) per storm and per season
- Count and display Rapid Intensification (RI) events per storm (≥30 kt / 24 hrs) and per season
- Calculate and display Landfall ACE (ACE accumulated before first landfall only)
- All Phase 1 metrics must cover 1991 to present for both Atlantic and Eastern Pacific basins

**F1.2 Advanced Metrics (Phase 2 — 2004+ only)**
- Calculate IKE (Integrated Kinetic Energy) per storm using wind radii data
- Calculate TIKE (Track Integrated Kinetic Energy) as the lifetime sum of IKE per storm
- Display Hurricane Severity Index (HSI) per storm
- All Phase 2 metrics must clearly label "available from 2004 onward" for any entry before that year

**F1.3 Derived / Supporting Statistics**
- Season totals and per-storm breakdown for all metrics
- Historical rank of current season (by ACE) among all seasons since 1991
- Percent of normal (relative to 1991–2020 climatological mean)
- NOAA season classification (Below/Near/Above Normal/Extremely Active) per basin
- Top 3 analog seasons by ACE proximity
- Longest storm, strongest storm, most ACE-generating storm callouts
- Prior season final ACE for reference

### F2 — Data Sources & Failover

**F2.1** The system must attempt data sources in this priority order for current-season data:
1. Tropycal `realtime` module
2. NHC ATCF advisory feed (direct HTTP fetch)
3. Climatlas feed (HTTP fetch + parser)
4. Last cached copy (local JSON file written on last successful fetch)

**F2.2** Each source failure must be logged with error details.

**F2.3** If all live sources fail, the site must serve the last cached data with a visible "Data delayed — last updated [timestamp]" banner. The site must never go blank or display an error page to visitors.

**F2.4** A successful fetch from any source must overwrite the local cache file.

**F2.5** Historical data (completed seasons) uses only HURDAT2 via Tropycal. No failover needed — this dataset changes only once per year.

### F3 — Site Pages

**F3.1 Live Dashboard (`/`)**
- Current season stats for Atlantic and Eastern Pacific
- Basin toggle (Atlantic / Eastern Pacific)
- All Phase 1 metrics with season totals and storm breakdown
- ACE contribution bar chart per storm
- Season progress gauge (relative to Below/Near/Above/Extreme thresholds)
- Analog season comparison
- Season insights (key callouts in plain English)
- Data freshness timestamp
- "Preliminary data" disclaimer
- "Data delayed" banner (shown only when serving cached data)

**F3.2 Season Archive (`/history/`)**
- Sortable table of all seasons 1991–present
- Columns: Year, Basin, Named Storms, Hurricanes, Majors, ACE, PDI, RI Events, NOAA Classification, Rank
- Current season highlighted
- Above-average seasons visually distinguished

**F3.3 Storm Records (`/records/`)**
- Top 25 storms all-time by ACE
- Top 25 storms all-time by PDI
- Top 25 storms all-time by peak wind speed
- Top 25 storms all-time by duration
- Basin filter (Atlantic / Pacific / Both)

**F3.4 Basin Comparison (`/compare/`)**
- Side-by-side Atlantic vs Eastern Pacific for any selected year
- Historical ACE chart with both basins overlaid (1991–present)

**F3.5 End-of-Season Recap (`/recap/YYYY/`)**
- Generated once at season end, then permanently static
- Full season summary: all storms, all metrics, final NOAA classification
- Comparison to official NOAA final numbers once HURDAT2 is updated
- Most notable events in plain English
- "Season closed" banner

**F3.6 About / Methodology (`/about/`)**
- ACE formula and explanation
- PDI formula and explanation
- IKE/TIKE explanation with 2004+ data limitation disclosed
- RI event definition
- NOAA classification thresholds for both basins
- All data sources with links
- Contact / Ko-fi link

### F4 — Automation

**F4.1** The update script must run automatically on a cron schedule without manual intervention.

**F4.2** Cron schedule:
- Eastern Pacific active window: May 15 – November 30
- Atlantic active window: June 1 – November 30
- Frequency during active season: every 6 hours (0000, 0600, 1200, 1800 UTC)

**F4.3** The script must not run the realtime fetch outside the active season window. If triggered manually off-season, it must skip the realtime fetch, log a warning, and exit cleanly without overwriting the last cached data.

**F4.4** At the end of the Atlantic season (November 30), the cron must trigger a one-time end-of-season recap page generation.

**F4.5** Cron failures must not crash the site. The last successfully generated HTML must remain live.

### F5 — Monetization (Light)

**F5.1** A Ko-fi (or equivalent) donation link must appear on every page in the footer.

**F5.2** No intrusive ads. If Google AdSense is added, it must be limited to one banner unit per page, non-overlapping with content.

**F5.3** The site must remain fully functional without JavaScript for core content (ads/charts may degrade gracefully).

---

## Non-Functional Requirements

### NF1 — Performance
- All pages must load in under 2 seconds on a 4G mobile connection (static HTML has no backend latency)
- No external JavaScript frameworks (no React, Vue, etc.) — vanilla JS only
- No external CSS frameworks loaded from CDN (self-contained)
- Images optimized; SVGs preferred for charts

### NF2 — Reliability
- Site must serve content 100% of the time (cached fallback ensures this)
- Cron failures must not take the site down
- GitHub Pages SLA is sufficient given static-only architecture

### NF3 — Accuracy & Transparency
- All pages must display the data timestamp ("Last updated: [datetime]")
- Current-season pages must include "Preliminary data — subject to revision" disclaimer
- IKE/TIKE columns must clearly show "N/A" for pre-2004 storms, not zeros
- Formula methodology must be linked from every page footer

### NF4 — Design
- Dark theme across all pages (background ≈ #07090f, accent ≈ #38bdf8)
- Mobile-first responsive layout; must be usable on a 375px wide phone screen
- Storm categories color-coded consistently across all pages:
  - Cat 5: #ff1493 (pink)
  - Cat 4: #ef4444 (red)
  - Cat 3: #f97316 (orange)
  - Cat 2: #fbbf24 (yellow)
  - Cat 1: #34d399 (green)
  - TS: #38bdf8 (blue)
  - TD: #94a3b8 (gray)
- No emojis in UI elements (they render inconsistently across platforms)

### NF5 — Maintainability
- All HTML generated from Jinja2 templates (no hardcoded data in HTML)
- Existing test suite must continue to pass after all changes
- New metrics must have corresponding unit tests before merging
- Failover chain must be testable in isolation (each source mockable)

### NF6 — Security
- No user data collected, no authentication, no cookies
- No third-party analytics without user notice
- All external links open in new tab with `rel="noopener noreferrer"`
- HTTPS enforced via GitHub Pages / Cloudflare

---

## Out of Scope

The following are explicitly not in scope and should not be designed for:

- User accounts or personalization
- Real-time WebSocket / push notifications
- Storm track maps or satellite imagery
- Forecast data or model output
- Western Pacific (WPAC) or other non-Atlantic/E.Pacific basins (may be revisited)
- Mobile app
- Any backend API or server-side processing

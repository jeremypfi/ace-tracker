# ACE Tracker Web Dashboard — Roadmap

## Vision

A public, zero-cost, always-on hurricane tracking dashboard that serves both casual weather enthusiasts and serious storm watchers. The site updates automatically every 6 hours during hurricane season, never goes blank, and presents ACE and related metrics more clearly and completely than anything freely available today.

---

## Milestone Overview

```
Now ──────────────────────────────────────────────────────────── Future

  M1             M2             M3              M4           M5
  │              │              │               │             │
  ▼              ▼              ▼               ▼             ▼
Data &        Live           Multi-         Advanced       Community
Automation    Dashboard      Page Site      Metrics        & Growth
(Phase 0–1)  (Phase 1)      (Phase 2–3)    (Phase 4)      (Phase 5+)

 ~May 2026    ~Jun 2026      ~Jul 2026      Off-season     Future
```

---

## M1 — Data & Automation (Target: Before 2026 Hurricane Season)

**The foundation everything else depends on. Nothing should go public until this works.**

Deliverables:
- 3-source realtime failover chain (Tropycal → NHC ATCF → Climatlas)
- Cached fallback with "Data delayed" banner
- GitHub Actions cron running automatically during hurricane season (May 15 – Nov 30)
- Seasonal gating: cron deactivates in off-season, activates each May
- All existing 25 unit tests still passing

Why it matters: Automating on bad or stale data is worse than not automating. Get the data right first.

---

## M2 — Live Dashboard (Target: Early June 2026)

**The site goes public for the first time. Shared with the weather group.**

Deliverables:
- Redesigned dark-theme dashboard (based on `ACE_Dashboard_Mockup.html`)
- Jinja2-templated — all data populated by Python, no hardcoded values
- Atlantic and Eastern Pacific basins with toggle
- ACE hero card, stats grid, storm table, ACE bar chart
- Season progress gauge and analog comparison
- "Preliminary data" and "Data delayed" banners
- Ko-fi link in footer
- Accessible at a public URL (GitHub Pages, custom domain optional)

Why it matters: This is the public launch. Mobile-friendly, correct, and never broken.

---

## M3 — Multi-Page Site + Phase 1 Metrics (Target: Mid-Season 2026 or Off-Season)

**Transforms the dashboard into a full reference site worth bookmarking.**

Deliverables:
- Season Archive page (all years 1991+, sortable)
- Storm Records page (all-time top 25 by ACE, PDI, peak wind, duration)
- Basin Comparison page (Atlantic vs Pacific side-by-side)
- About / Methodology page (formulas, sources, Ko-fi)
- End-of-Season Recap page (generated November 30)
- New metrics live on all pages: PDI, RI Events, Landfall ACE
- Site navigation across all pages

Why it matters: One-off dashboards get visited once. A full records site gets bookmarked and revisited every season.

---

## M4 — Advanced Metrics: IKE / TIKE (Off-Season 2026–2027)

**Adds wind-field-based metrics that no other free public tool prominently tracks.**

Deliverables:
- Extended Best Track data integrated (RAMMB/CIRA, 2004+)
- IKE (Integrated Kinetic Energy) per storm and per season
- TIKE (Track Integrated Kinetic Energy) per storm
- All with clear "2004+ only" disclosure
- IKE/TIKE validated against NOAA/AOML published benchmarks
- New top-25 records lists for IKE and TIKE

Why it matters: IKE and TIKE capture storm size — a metric Saffir-Simpson and ACE both miss. This is a genuine differentiator vs. other public dashboards.

**Note:** This is deliberately scheduled for the off-season. IKE/TIKE calculation is complex; getting it wrong and publishing it publicly damages credibility. Better done carefully than quickly.

---

## M5 — Community & Growth (Ongoing, 2027+)

**Nice-to-haves that depend on actual audience size.**

Candidates (none committed):
- Discord bot posting automated season updates (already has Discord tab in existing Excel output)
- Custom domain with memorable name
- Google AdSense (only if monthly visits justify it — ~1,500+ visits/month)
- Email/RSS feed for season updates
- Western Pacific basin (if there's demand)
- Year-over-year animated ACE chart

These are not planned work — they're options to revisit once real traffic data exists. Build for the audience you have, not the one you hope for.

---

## Guiding Principles

**Data accuracy over feature count.**
A site that gets ACE wrong is worse than no site. Every new metric needs unit tests and a Claude-run verification against NOAA HURDAT2 before it goes live — results reviewed and approved before publishing.

**Never break what works.**
The existing Python script and 25 tests are the safety net. No phase should leave them in a broken state.

**Static is a feature, not a limitation.**
No database, no backend, no server means no downtime, no security surface, no hosting cost. Don't add complexity that undermines this.

**Seasonal discipline.**
The automation turns on and off with the season. An end-of-season recap is a deliberate moment. Don't let the tool become a year-round maintenance burden.

**Transparency builds trust.**
Every page discloses data limitations (preliminary data, pre-2004 wind radii gaps, data delays). Weather enthusiasts are sophisticated — they respect honesty more than false precision.

---

## Decision Log

| Date | Decision | Reason |
|---|---|---|
| Apr 2026 | Dark theme for dashboard | User preference; better for data-dense displays |
| Apr 2026 | Static site (no backend) | Zero cost, zero downtime, no security surface |
| Apr 2026 | GitHub Actions + GitHub Pages | Already have the repo; free tier sufficient |
| Apr 2026 | 3-source failover + cache | No single external source is reliable enough alone |
| Apr 2026 | PDI added to Phase 1 | Same data as ACE, trivial to implement alongside it |
| Apr 2026 | IKE/TIKE deferred to Phase 4 | Wind radii only available 2004+; complex calculation; off-season work |
| Apr 2026 | Genesis Potential Index excluded | Forecast metric, not historical tracking — out of scope |
| Apr 2026 | WPAC basin excluded for now | Scope control; revisit if audience requests it |

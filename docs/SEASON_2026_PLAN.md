# ACE Tracker — 2026 Season Deadline Plan

> **Note on estimates:** All times below reflect *your time* with Claude Code doing the implementation, verification, and testing. Claude handles coding, data spot-checks against NOAA, running the test suite, and reading CI logs. What takes your time is approving decisions, DNS/credentials work, testing on your physical phone, and final judgment calls. A task estimated at 30 min means 30 min of your focused attention.

---

## Deadlines

| Date | Event | Required State |
|---|---|---|
| **Today** | Apr 24, 2026 | Starting point |
| **May 15** | Eastern Pacific season opens | Site live, data auto-updating |
| **Jun 1** | Atlantic season opens | Full public launch, all core features |
| Off-season | Nov 30 – May 14 | Advanced metrics, Discord, IKE/TIKE |

**Bottom line:** With Claude Code doing the implementation, the entire pre-June 1 roadmap fits in **6–8 sessions of 2 hrs each**. May 15 and June 1 are both very comfortable. You are not in a rush.

---

## Division of Labor

### Claude handles
- Writing all code, templates, config files, parsers
- Running the test suite and reading results
- Data verification — fetching HURDAT2 directly, comparing our ACE/PDI output against NOAA values, flagging discrepancies with a report
- Checking GitHub Actions logs after a run
- Verifying rendered page numbers match script output
- Self-reviewing code before you see it

### You handle (irreducible)
| Task | Why only you can do it |
|---|---|
| DNS propagation wait | 24–48 hrs after domain registration, nothing skips this |
| Domain registration | Your payment, your account |
| Enabling GitHub Pages | Requires repo admin access |
| Approving changes before they go live | Your site, your call |
| Testing on your actual physical phone | Claude can't hold your phone |
| Getting the Discord webhook URL | Requires access to your Discord server |
| Final "I'm happy with this" sign-off | Judgment call that belongs to you |

Everything else — including data accuracy checks — Claude handles.

---

## Session Plan

Sessions are every other day, 2 hrs each. Total: **7 sessions** to full launch.

---

### Session 1 · Apr 25 · ~2 hrs · Automation Foundation

> **Prereq before Session 2:** Upgrade local Python from 3.9 (EOL Oct 2025) to 3.11 to match CI. Run `brew install python@3.11` or download from python.org. Confirm with `python3.11 --version` and `python3.11 -c "import tropycal"` before the realtime work in Session 2.

**What Claude does:** Writes the GitHub Actions `publish.yml` workflow, date-gating logic, GitHub Pages config.

**Your time goes to:**
- Reading and approving the workflow file (~15 min)
- Enabling GitHub Pages in repo Settings
- Triggering a manual workflow dispatch to test it fires
- Confirming the site loads at `github.io` URL
- Registering a domain (~20 min on Namecheap/Cloudflare Registrar)
- Configuring DNS A records + CNAME file

**End state:** Existing ACE dashboard is live at your domain and deploying automatically on a cron. Data is still HURDAT2-only — that's fine for now.

> **DNS note:** After pointing your domain at GitHub Pages, wait 24–48 hrs for propagation before HTTPS works. Register the domain in this session so the clock starts.

---

### Session 2 · Apr 27 · ~2 hrs · Realtime Data + Failover Chain

**What Claude does:** Writes `fetch_realtime_tropycal()`, `fetch_realtime_nhc()` (NHC ATCF parser), `fetch_realtime_climatlas()`, `get_realtime_data()` failover loop, cache-to-JSON fallback, and the "Data delayed" flag. Runs all 25 tests. Verifies each source against a known recent storm by fetching HURDAT2 and comparing values. Mocks source failures to confirm fallback chain works. Reports results.

**Your time goes to:**
- Reading Claude's verification report and approving it
- Deciding if the failover behavior is what you want

**End state:** Active storms update from a live source with two fallbacks. Site never goes blank. All tests green.

> **Decision point:** If Tropycal's realtime module doesn't cover active storms adequately, NHC ATCF is the fallback. Claude handles both and will tell you which one is working.

---

### Session 3 · Apr 29 · ~2 hrs · Dashboard Redesign

**What Claude does:** Adds Jinja2, creates `templates/` directory, converts `ACE_Dashboard_Mockup.html` into `templates/dashboard.html` with all variables wired to real Python data, removes old string-based HTML generation, adds "Preliminary data" and "Data delayed" banners. Verifies rendered numbers match script output. Runs test suite.

**Your time goes to:**
- Opening the rendered dashboard and deciding if it looks right visually
- Testing basin toggle (Atlantic ↔ Pacific)
- Opening on your phone — Claude cannot test on your physical device
- One round of revision feedback if anything looks off

**End state:** The new dark dashboard is live, auto-updating, and mobile-friendly. Both basins work.

---

### ✅ Checkpoint — May 14 (day before E. Pacific opens)

By this point you should have 3 sessions done and ~6 days of buffer remaining. Verify:

- [ ] GitHub Actions cron fires automatically on schedule
- [ ] Site live at your custom domain with HTTPS
- [ ] Realtime data fetch working (or cache fallback with banner)
- [ ] New dashboard design live
- [ ] All 25 tests passing

**If anything above is not checked: stop and fix it. Do not move to multi-page site until automation is solid.**

The remaining sessions (4–7) can happen any time between May 1–31. You're ahead of schedule.

---

### Session 4 · ~2 hrs · History + Records Pages

**What Claude does:** Creates `templates/base.html` with nav, `templates/history.html` (Season Archive, 1991+, sortable), `templates/records.html` (top 25 storms by ACE/wind/duration with basin filter).

**Claude also:** Spot-checks historical ACE values for several seasons against NOAA HURDAT2 and reports any discrepancies before you see the page.

**Your time goes to:**
- Reviewing the verification report
- Confirming sort works in your browser
- Mobile check on your phone

---

### Session 5 · ~2 hrs · Compare + About + Recap Pages

**What Claude does:** Creates `templates/compare.html` (Atlantic vs Pacific side-by-side), `templates/about.html` (methodology, formulas, Ko-fi link), `templates/recap.html` (end-of-season, triggered by `--recap` flag). Adds nav to all pages. Adds Ko-fi button to footer.

**Your time goes to:**
- Reviewing methodology text on the About page for accuracy
- Adding your actual Ko-fi link
- Checking navigation works across all pages

---

### Session 6 · ~1.5 hrs · PDI + RI Events + Landfall ACE

**What Claude does:** Adds `calculate_pdi()` (V³ formula), `count_ri_events()` (≥30 kt / 24 hrs), `calculate_landfall_ace()`, wires all three into season aggregates and page templates, writes unit tests. Fetches NOAA HURDAT2 to verify PDI values against published benchmarks for several storms. Verifies RI event counts against NHC records. Runs full test suite and reports.

**Your time goes to:**
- Reading the verification report
- Approving the new metrics for publishing

---

### Session 7 · ~1.5 hrs · SEO, Polish, Final QA

**What Claude does:** Adds `<meta>` description tags, `<title>` tags, `sitemap.xml` generation, any visual fixes from your feedback.

**Your time goes to:**
- Final cross-browser check (Chrome, Safari, Firefox)
- Full walkthrough of every page on desktop and mobile
- Confirming Ko-fi link works
- Writing a short post to share with your weather group

**End state:** Full site live. Share June 1. ✅

---

## ✅ June 1 Launch Checklist

- [ ] Live dashboard — Atlantic + Eastern Pacific, auto-updating every 6 hrs
- [ ] Season Archive, Records, Compare, About pages
- [ ] PDI, RI Events, Landfall ACE on all relevant pages
- [ ] "Preliminary data" disclaimer visible
- [ ] "Data delayed" banner tested
- [ ] Custom domain with HTTPS
- [ ] Ko-fi link in footer
- [ ] Mobile layout verified on a real phone
- [ ] All 25+ unit tests passing

---

## Off-Season Work (Nov 30, 2026 → May 14, 2027)

No deadline pressure. Do in order as interest allows.

### Session A · ~1 hr · End-of-Season Recap
Run `ace_tracker.py --recap` to generate the permanent 2026 recap page. Revisit in Jan–Feb 2027 once NOAA finalizes HURDAT2 to compare your values against official numbers.

### Sessions B–D · ~4–6 hrs · IKE / TIKE (2004+ only)
- Claude integrates RAMMB Extended Best Track wind radii data
- Claude implements IKE (Powell & Reinhold 2007 volume integral) and TIKE
- Claude validates output against NOAA/AOML IKE calculator for a sample of storms and produces a comparison report
- Your time: reviewing the validation report and approving before it goes live
- This is complex — do not rush it, no deadline

### Session E · ~30 min · Discord Webhook (Last Feature)

`generate_discord_text()` already writes the complete formatted message. The only remaining work:

1. In your Discord server: Settings → Integrations → Webhooks → New Webhook → Copy URL
2. In GitHub repo: Settings → Secrets → add `DISCORD_WEBHOOK_ATLANTIC` and `DISCORD_WEBHOOK_PACIFIC`
3. Claude adds 4 lines to `ace_tracker.py`:

```python
webhook = os.environ.get(f"DISCORD_WEBHOOK_{basin_key.upper()}")
if webhook:
    import requests
    requests.post(webhook, json={"content": discord_text})
```

4. Test with a manual workflow dispatch. Done.

The message content was already built when you created the Excel Discord tab. This is the last 30 minutes of work on the entire project.

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Tropycal realtime lacks active storm data | Medium | Medium | NHC ATCF fallback covers this; Claude writes both |
| Tropycal maintenance velocity — `pkg_resources`/3.12 bug unpatched 18+ months; realtime module may have similar gaps | Medium | Medium | Test realtime module explicitly in Session 2; if unreliable, promote NHC ATCF to primary source |
| GitHub Actions permissions issue | Low | Medium | Test with manual dispatch in Session 1 before trusting cron |
| DNS takes longer than 48 hrs | Low | Low | Register domain Session 1; wait passively while other work continues |
| IKE calculation harder than expected | High | Low | Off-season, no deadline, validate before publishing |
| Climatlas format changes mid-season | Low | Low | Cache fallback means site never goes blank |

---

## Data Source Reference

| Source | Role | Notes |
|---|---|---|
| Tropycal / HURDAT2 | Primary historical (1991+) | Post-season finalized data |
| Tropycal realtime | Primary current season (Source 1) | Assess reliability in Session 2; may demote to Source 2 |
| NHC ATCF feed | Fallback current season (Source 2) | Official NOAA feed, public domain |
| Climatlas (Dr. Maue) | Fallback current season (Source 3) | Prior working code in backup branch |
| Cache (local JSON) | Final fallback | Always succeeds; shows "data delayed" banner |
| CSU Tropical (Klotzbach/CSU) | Verification only | Useful for spot-checking ACE values; derived from NHC so not independent. Terms of use unclear — email CSU before adding as a live scrape source. RAMMB/CIRA (CSU affiliate) already in Phase 4 plan for IKE/TIKE wind radii. |

---

## What to Defer (Do Not Touch Before June 1)

- IKE / TIKE / Hurricane Severity Index
- Western Pacific basin
- Google AdSense (add only after real traffic data exists)
- Storm track maps or satellite imagery
- Any backend, database, or user accounts
- Discord webhook (30 min of work, zero urgency)

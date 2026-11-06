#!/usr/bin/env python3
"""
Atlantic & Eastern Pacific Hurricane ACE Tracker
=================================================
Tracks Accumulated Cyclone Energy (ACE) for both Atlantic and Eastern Pacific
hurricane seasons with storm-by-storm historical data from 1991 onward.

This is the CLI entrypoint. Data fetching and ACE calculation live in
ace_data.py; dashboard/history HTML rendering lives in ace_html.py.

Output:
- data/ACE_Dashboard.html  — current season dashboard (deployed to aceofcanes.com)
- data/history.html        — all-seasons history page
- data/records.html        — all-time-since-1991 storm records page
- data/what-is-ace.html    — ACE explainer and calculator
- data/api.html           — JSON API and RSS docs

Usage:
    python3 ace_tracker.py

Author: Built with Claude for JP
"""

import os
import shutil
import logging
from datetime import datetime, timezone

from ace_data import (
    BASINS,
    build_season_payload,
    build_completed_season_payload,
    ensure_unique_page_slugs,
    get_completed_seasons,
    STORM_PAGES_FIRST_YEAR,
    BACKUP_DATA,
    START_YEAR,
    _tropycal_basin_name,
    _build_track_dataset,
    parse_hurdat2,
    get_current_season,
    calculate_yearly_totals,
    calculate_yearly_stats,
    calculate_ace_pace,
    calculate_records_in_play,
    fetch_tcr_reports,
    generate_insights,
    generate_discord_text,
    generate_console_report,
)
from ace_html import (render_dashboard_html, generate_history_html, generate_records_html, generate_about_html,
                      generate_api_docs_html)
from ace_feeds import api_v1_json, build_rss, build_sitemap, API_V1_PATH, FEED_PATH
from ace_storm_pages import render_storm_page_html, storm_page_path
import ace_cards

# logging.basicConfig() lives in ace_data.py, which every import path here
# (directly or via ace_html) already pulls in — see the comment there.
logger = logging.getLogger(__name__)

# ===============================================================================
# CONFIGURATION
# ===============================================================================

OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
# Finished seasons' share cards never change, so they are kept here between
# runs (an Actions cache in publish.yml) instead of being redrawn: about
# 1,000 cards at ~0.2 s each (#158). None turns the cache off.
CARD_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "card_cache")



# ===============================================================================
# PROCESS A BASIN
# ===============================================================================

def process_basin(basin_key):
    basin = BASINS[basin_key]

    print("\n" + "=" * 50)
    print(f"{basin['name']} Hurricane ACE Tracker")
    print("=" * 50 + "\n")

    # Build one TrackDataset and share it between parse_hurdat2 (full history)
    # and get_current_season (latest season) — both used to fetch/parse the
    # same basin data independently, doubling the network + parse time per run.
    tropycal_basin = _tropycal_basin_name(basin_key)
    try:
        print(f"Loading {tropycal_basin} data via Tropycal (shared across historical + current season)...")
        shared_dataset = _build_track_dataset(basin_key)
    except Exception as e:
        logger.warning(f"Could not build shared TrackDataset for {basin_key}: {e}")
        shared_dataset = None

    # A dataset-build failure during the active season means we have no way
    # to get real current-season data. Continuing on would silently overwrite
    # the live dashboard with an empty/fallback season (this is exactly how
    # a NOAA HURDAT2 formatting glitch went unnoticed for days in Sept 2026 —
    # every layer caught the exception and substituted zeros). Fail the run
    # instead and leave the last known-good dashboard in place.
    today = datetime.now(timezone.utc).date()
    season_start_month, season_start_day = (6, 1) if basin_key == 'atlantic' else (5, 15)
    season_start = datetime(today.year, season_start_month, season_start_day).date()
    season_end = datetime(today.year, 11, 30).date()
    if shared_dataset is None and season_start <= today <= season_end:
        raise RuntimeError(
            f"Failed to build TrackDataset for {basin_key} during its active season "
            f"({season_start} to {season_end}) — refusing to publish empty/fallback "
            f"data over the live dashboard.")

    # Get historical data
    historical_storms = parse_hurdat2(basin_key, dataset=shared_dataset)

    if historical_storms:
        yearly_totals = calculate_yearly_totals(historical_storms)
        yearly_stats = calculate_yearly_stats(historical_storms)
        ace_pace = calculate_ace_pace(historical_storms, basin_key)
    else:
        yearly_totals = BACKUP_DATA[basin_key]['yearly_totals']
        yearly_stats = None
        ace_pace = None

    # Get current season
    current = get_current_season(basin_key, dataset=shared_dataset)

    # Finished seasons the dashboard no longer shows still need their storm
    # pages, or every link shared during the season 404s (#158). Off-season
    # the dashboard still shows last season, so this is empty until the new
    # season gets its first storm or its start date.
    completed_seasons = []
    if shared_dataset is not None:
        completed_seasons = get_completed_seasons(
            shared_dataset, [y for y in range(STORM_PAGES_FIRST_YEAR, today.year) if y != current['year']])

    # Generate insights
    insights = generate_insights(basin_key, current, yearly_totals, historical_storms, yearly_stats)
    records_in_play = calculate_records_in_play(historical_storms, basin_key, current['total'])

    # Generate discord text
    discord_text = generate_discord_text(basin_key, current, yearly_totals, insights)

    # Print console report
    print(generate_console_report(basin_key, current, yearly_totals, insights))

    # Print discord preview
    print(f"\n{'─' * 50}")
    print("  Discord Update Preview:")
    print(f"{'─' * 50}")
    print(discord_text)

    return {
        'basin_key': basin_key,
        'current': current,
        'completed_seasons': completed_seasons,
        'yearly_totals': yearly_totals,
        'yearly_stats': yearly_stats,
        'insights': insights,
        'records_in_play': records_in_play,
        'ace_pace': ace_pace,
        'historical_storms': historical_storms,
    }



def write_share_card(payloads, output_folder, generated_at=None):
    """Draw the live season share card into output_folder/og/. Returns
    (site-relative path, alt text), or (None, None) on any failure: a broken
    image must never fail the publish, so the page falls back to the static card."""
    try:
        rel_path = ace_cards.share_card_name(payloads, generated_at)
        full_path = os.path.join(output_folder, rel_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'wb') as f:
            f.write(ace_cards.render_share_card(payloads, generated_at))
        return rel_path, ace_cards.share_card_alt(payloads)
    except Exception as e:
        logger.error(f"Could not generate share card: {e}")
        print("  ✗ Error: Could not generate share card (using static preview)")
        return None, None



def _write_storm_card(p, s, output_folder, generated_at, card_cache, used):
    """Write one storm's share card and return its site-relative path. A
    finished season's card is copied from `card_cache` when there, and
    saved there when drawn."""
    image = ace_cards.storm_card_name(p, s, generated_at)
    full = os.path.join(output_folder, image)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    cached = os.path.join(card_cache, os.path.basename(image)) if card_cache and p.get('completed') else None
    if cached and os.path.isfile(cached) and os.path.getsize(cached) > 0:
        shutil.copyfile(cached, full)
        used[os.path.basename(image)] = True
        return image
    with open(full, 'wb') as f:
        f.write(ace_cards.render_storm_card(p, s, generated_at))
    if cached:
        try:
            os.makedirs(card_cache, exist_ok=True)
            shutil.copyfile(full, cached)
            used[os.path.basename(image)] = False
        except OSError as e:
            logger.warning(f"Could not cache share card {image}: {e}")
    return image


def _prune_card_cache(card_cache, used):
    """Drop cached cards this run did not use (a storm whose data changed
    gets a new name), so the cache holds exactly the current cards."""
    if not card_cache or not os.path.isdir(card_cache):
        return
    for name in os.listdir(card_cache):
        if name not in used:
            try:
                os.remove(os.path.join(card_cache, name))
            except OSError:
                pass


def write_storm_pages(payloads, output_folder, generated_at=None, card_cache=None):
    """Write one page (and share card) per storm of each payload under
    output_folder/storm/. Each storm is isolated: a failure skips that storm,
    never the publish. Returns the payloads that actually got pages, with
    the failed storms removed, for the sitemap."""
    storm_dir = os.path.join(output_folder, 'storm')
    shutil.rmtree(storm_dir, ignore_errors=True)
    os.makedirs(storm_dir, exist_ok=True)
    published = []
    used = {}  # cached card name -> True if copied, False if drawn this run
    for p in payloads:
        if p['preseason'] or p['is_backup']:
            continue
        ok = []
        for s in p['storms']:
            try:
                image = alt = None
                try:
                    image = _write_storm_card(p, s, output_folder, generated_at, card_cache, used)
                    alt = ace_cards.storm_card_alt(p, s)
                except Exception as e:
                    logger.error(f"Could not generate share card for {s['name']}: {e}")
                    image = alt = None
                page = render_storm_page_html(p, s, image, alt)  # render first: a failure must not leave an empty file
                with open(os.path.join(output_folder, storm_page_path(s)), 'w', encoding='utf-8') as f:
                    f.write(page)
                ok.append(s)
            except Exception as e:
                logger.error(f"Failed to write storm page for {s['name']}: {e}")
        if ok:
            published.append(dict(p, storms=ok))
    _prune_card_cache(card_cache, used)
    if card_cache:
        print(f"  ✓ Finished-season cards: {sum(used.values())} from cache, "
              f"{sum(1 for hit in used.values() if not hit)} drawn")
    return published


def write_sitemap(published, output_folder, base_path=None, generated_at=None):
    """data/sitemap.xml = the repo's static sitemap plus storm pages. On any
    failure the static sitemap is published unchanged."""
    base_path = base_path or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sitemap.xml')
    out_path = os.path.join(output_folder, 'sitemap.xml')
    with open(base_path, encoding='utf-8') as f:
        base = f.read()
    try:
        content = build_sitemap(base, published, generated_at)
    except Exception as e:
        logger.error(f"Could not add storm pages to the sitemap: {e}")
        content = base
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(content)
    return out_path



# ===============================================================================
# MAIN
# ===============================================================================

def main():
    print("\n" + "#" * 50)
    print("#" + " " * 48 + "#")
    print("#   HURRICANE ACE TRACKER - Atlantic & Pacific   #")
    print("#" + " " * 48 + "#")
    print("#" * 50)
    print(f"\nHistorical data from {START_YEAR} onward")
    print(f"ACE includes: TS + HU + SS statuses at synoptic times only")

    output_files = []
    basin_results = []

    # Process Atlantic
    result = process_basin('atlantic')
    if result:
        basin_results.append(result)

    # Process Pacific
    result = process_basin('pacific')
    if result:
        basin_results.append(result)

    # Per-storm NHC report links for the history page. Fetched once both
    # basins' live data is in, so this extra NHC request never competes
    # with the current-season and forecast-track downloads.
    for result in basin_results:
        storms = result.get('historical_storms')
        result['tcr_reports'] = fetch_tcr_reports(storms, result['basin_key']) if storms else {}

    # Generate HTML pages
    if basin_results:
        # One payload per basin, shared by the dashboard and the feeds so the
        # NHC cone/outlook fetches happen once per run.
        payloads = [build_season_payload(r) for r in basin_results]
        completed = [build_completed_season_payload(r['basin_key'], s)
                     for r in basin_results for s in r.get('completed_seasons', [])]
        ensure_unique_page_slugs(payloads + completed)
        share_image, share_alt = write_share_card(payloads, OUTPUT_FOLDER)
        if share_image:
            print(f"  ✓ Share card saved to: {os.path.join(OUTPUT_FOLDER, share_image)}")
        dashboard_html = render_dashboard_html(payloads, share_image, share_alt)
        dashboard_path = os.path.join(OUTPUT_FOLDER, 'ACE_Dashboard.html')
        try:
            with open(dashboard_path, 'w', encoding='utf-8') as f:
                f.write(dashboard_html)
            output_files.append(dashboard_path)
            print(f"\n  ✓ Dashboard saved to: {dashboard_path}")
        except (OSError, PermissionError) as e:
            logger.error(f"Failed to save dashboard {dashboard_path}: {e}")
            print(f"\n  ✗ Error: Could not save dashboard")

        for rel_path, build in ((API_V1_PATH, api_v1_json), (FEED_PATH, build_rss)):
            feed_path = os.path.join(OUTPUT_FOLDER, rel_path)
            try:
                os.makedirs(os.path.dirname(feed_path), exist_ok=True)
                with open(feed_path, 'w', encoding='utf-8') as f:
                    f.write(build(payloads))
                output_files.append(feed_path)
                print(f"  ✓ {rel_path} saved to: {feed_path}")
            except (OSError, PermissionError) as e:
                logger.error(f"Failed to save {feed_path}: {e}")
                print(f"  ✗ Error: Could not save {rel_path}")

        try:
            published = write_storm_pages(payloads + completed, OUTPUT_FOLDER, card_cache=CARD_CACHE)
            print(f"  ✓ {sum(len(p['storms']) for p in published)} storm pages saved to: "
                  f"{os.path.join(OUTPUT_FOLDER, 'storm')}")
            output_files.append(write_sitemap(published, OUTPUT_FOLDER))
        except (OSError, PermissionError) as e:
            logger.error(f"Failed to save storm pages / sitemap: {e}")
            print("  ✗ Error: Could not save storm pages / sitemap")

        history_html = generate_history_html(basin_results)
        history_path = os.path.join(OUTPUT_FOLDER, 'history.html')
        try:
            with open(history_path, 'w', encoding='utf-8') as f:
                f.write(history_html)
            output_files.append(history_path)
            print(f"  ✓ History page saved to: {history_path}")
        except (OSError, PermissionError) as e:
            logger.error(f"Failed to save history page {history_path}: {e}")
            print(f"  ✗ Error: Could not save history page")

        records_html = generate_records_html(basin_results)
        records_path = os.path.join(OUTPUT_FOLDER, 'records.html')
        try:
            with open(records_path, 'w', encoding='utf-8') as f:
                f.write(records_html)
            output_files.append(records_path)
            print(f"  ✓ Records page saved to: {records_path}")
        except (OSError, PermissionError) as e:
            logger.error(f"Failed to save records page {records_path}: {e}")
            print(f"  ✗ Error: Could not save records page")

        about_html = generate_about_html(basin_results)
        about_path = os.path.join(OUTPUT_FOLDER, 'what-is-ace.html')
        try:
            with open(about_path, 'w', encoding='utf-8') as f:
                f.write(about_html)
            output_files.append(about_path)
            print(f"  ✓ What-is-ACE page saved to: {about_path}")
        except (OSError, PermissionError) as e:
            logger.error(f"Failed to save what-is-ACE page {about_path}: {e}")
            print(f"  ✗ Error: Could not save what-is-ACE page")

        api_docs_path = os.path.join(OUTPUT_FOLDER, 'api.html')
        try:
            with open(api_docs_path, 'w', encoding='utf-8') as f:
                f.write(generate_api_docs_html())
            output_files.append(api_docs_path)
            print(f"  ✓ API docs page saved to: {api_docs_path}")
        except (OSError, PermissionError) as e:
            logger.error(f"Failed to save API docs page {api_docs_path}: {e}")
            print(f"  ✗ Error: Could not save API docs page")

    print("\n" + "=" * 50)
    print("All done! Dashboard updated.")
    if output_files:
        print(f"Files saved to: {OUTPUT_FOLDER}")
        for f in output_files:
            print(f"  → {os.path.basename(f)}")
    print("=" * 50)

    return output_files



if __name__ == "__main__":
    main()


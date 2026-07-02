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

Usage:
    python3 ace_tracker.py

Author: Built with Claude for JP
"""

import os
import logging
import tropycal.tracks as tracks

from ace_data import (
    BASINS,
    BACKUP_DATA,
    START_YEAR,
    _tropycal_basin_name,
    parse_hurdat2,
    get_current_season,
    calculate_yearly_totals,
    calculate_yearly_stats,
    generate_insights,
    generate_discord_text,
    generate_console_report,
)
from ace_html import generate_dashboard_html, generate_history_html

# logging.basicConfig() lives in ace_data.py, which every import path here
# (directly or via ace_html) already pulls in — see the comment there.
logger = logging.getLogger(__name__)

# ===============================================================================
# CONFIGURATION
# ===============================================================================

OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")



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
        shared_dataset = tracks.TrackDataset(basin=tropycal_basin, source='hurdat', include_btk=True)
    except Exception as e:
        logger.warning(f"Could not build shared TrackDataset for {basin_key}: {e}")
        shared_dataset = None

    # Get historical data
    historical_storms = parse_hurdat2(basin_key, dataset=shared_dataset)

    if historical_storms:
        yearly_totals = calculate_yearly_totals(historical_storms)
        yearly_stats = calculate_yearly_stats(historical_storms)
    else:
        yearly_totals = BACKUP_DATA[basin_key]['yearly_totals']
        yearly_stats = None

    # Get current season
    current = get_current_season(basin_key, dataset=shared_dataset)

    # Generate insights
    insights = generate_insights(basin_key, current, yearly_totals, historical_storms, yearly_stats)

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
        'yearly_totals': yearly_totals,
        'yearly_stats': yearly_stats,
        'insights': insights,
    }



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

    # Generate HTML pages
    if basin_results:
        dashboard_html = generate_dashboard_html(basin_results)
        dashboard_path = os.path.join(OUTPUT_FOLDER, 'ACE_Dashboard.html')
        try:
            with open(dashboard_path, 'w', encoding='utf-8') as f:
                f.write(dashboard_html)
            output_files.append(dashboard_path)
            print(f"\n  ✓ Dashboard saved to: {dashboard_path}")
        except (OSError, PermissionError) as e:
            logger.error(f"Failed to save dashboard {dashboard_path}: {e}")
            print(f"\n  ✗ Error: Could not save dashboard")

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


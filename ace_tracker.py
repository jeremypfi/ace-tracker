#!/usr/bin/env python3
"""
Atlantic & Eastern Pacific Hurricane ACE Tracker
=================================================
Tracks Accumulated Cyclone Energy (ACE) for both Atlantic and Eastern Pacific
hurricane seasons with storm-by-storm historical data from 1991 onward.

Creates two separate spreadsheets:
- ACE_Tracker_Atlantic.xlsx
- ACE_Tracker_Pacific.xlsx

Each spreadsheet contains 5 tabs:
- Summary
- Current Season Storms
- Historical Storms (1991-present)
- Yearly Totals
- Discord Update (copy/paste ready for Discord)

Usage:
    python3 ace_tracker.py

Author: Built with Claude for JP
"""

import re
import os
import logging
import urllib.request
from datetime import datetime, timedelta, timezone
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

BASINS = {
    'atlantic': {
        'name': 'Atlantic',
        'output_file': 'ACE_Tracker_Atlantic.xlsx',
        'hurdat2_url': 'https://www.nhc.noaa.gov/data/hurdat/hurdat2-1851-2024-040425.txt',
        'storm_id_prefix': 'AL',
        'climatlas_pattern': r'North Atlantic Basin',
        # Captures: name, max_wind (kt), ACE value — e.g. "Erin 05L (140, ACE=32.1975"
        'climatlas_storm_pattern': r'[\[> ]\s*([A-Z][a-z]+)\s+\d+L\s+\((\d+),\s*ACE=([0-9.*]+)',
        'climatlas_central_pattern': None,  # Atlantic has no central sub-basin
        'climatlas_central_storm_pattern': None,
        'normal_ace': 122.5,
        'noaa_thresholds': {
            'below_normal': 73,
            'near_normal_upper': 126,
            'above_normal_upper': 159,
        },
        'avg_named_storms': 14,
        'avg_hurricanes': 7,
        'avg_major_hurricanes': 3,
        'all_time_single_storm_ace': {'name': 'San Ciriaco (1899)', 'ace': 73.6},
    },
    'pacific': {
        'name': 'Eastern Pacific',
        'output_file': 'ACE_Tracker_Pacific.xlsx',
        'hurdat2_url': 'https://www.nhc.noaa.gov/data/hurdat/hurdat2-nepac-1949-2024-031725.txt',
        'storm_id_prefix': 'EP',
        'climatlas_pattern': 'Eastern North Pacific',
        'climatlas_storm_pattern': r'[\[> ]\s*([A-Z][a-z]+)\s+\d+E\s+\((\d+),\s*ACE=([0-9.*]+)',
        # Central Pacific storms (like Iona 01C) should be included in Pacific totals
        'climatlas_central_pattern': 'Central North Pacific',
        'climatlas_central_storm_pattern': r'[\[> ]\s*([A-Z][a-z]+)\s+\d+C\s+\((\d+),\s*ACE=([0-9.*]+)',
        'normal_ace': 132.0,
        'noaa_thresholds': {
            'below_normal': 73,
            'near_normal_upper': 126,
            'above_normal_upper': 159,
        },
        'avg_named_storms': 15,
        'avg_hurricanes': 8,
        'avg_major_hurricanes': 4,
        'all_time_single_storm_ace': {'name': 'Fico (1978)', 'ace': 62.8},
    }
}

CURRENT_SEASON_URL = "https://climatlas.com/tropical/"
START_YEAR = 1991

# ACE Calculation Constants
SYNOPTIC_TIMES = ['0000', '0600', '1200', '1800']
ACE_STATUSES = ['TS', 'HU', 'SS']  # Tropical Storm, Hurricane, Subtropical Storm
MIN_NAMED_STORM_WIND = 34  # knots
MAX_STORMS_DISCORD = 10  # Maximum storms shown in Discord update before summarizing

# =============================================================================
# BACKUP DATA (used when network is unavailable)
# =============================================================================

BACKUP_DATA = {
    'atlantic': {
        'year': 2025,
        'storms': {
            "Andrea": 0.735, "Barry": 0.405, "Chantal": 0.815, "Dexter": 2.4675,
            "Erin": 32.1975, "Fernand": 3.3725, "Gabrielle": 20.0475,
            "Humberto": 26.6875, "Imelda": 7.0125, "Jerry": 4.1075,
            "Karen": 0.64, "Lorenzo": 1.9975, "Melissa": 35.0175,
        },
        'yearly_totals': {
            2024: 161.6, 2023: 146.0, 2022: 95.0, 2021: 145.0, 2020: 180.0,
            2019: 133.0, 2018: 136.4, 2017: 225.0, 2016: 155.0, 2015: 65.0,
            2014: 67.0, 2013: 36.0, 2012: 133.0, 2011: 126.0, 2010: 165.0,
            2009: 53.0, 2008: 146.0, 2007: 74.0, 2006: 79.0, 2005: 245.0,
            2004: 227.0, 2003: 176.0, 2002: 67.0, 2001: 106.0, 2000: 119.0,
            1999: 177.0, 1998: 182.0, 1997: 41.0, 1996: 166.0, 1995: 228.0,
            1994: 32.0, 1993: 39.0, 1992: 75.0, 1991: 34.0,
        }
    },
    'pacific': {
        'year': 2025,
        'storms': {
            "Alvin": 1.465, "Barbara": 3.1025, "Cosme": 2.7775, "Dalila": 2.175,
            "Erick": 6.5475, "Flossie": 8.1075, "Gil": 4.125, "Henriette": 8.105,
            "Ivo": 3.405, "Juliette": 2.9975, "Kiko": 26.085, "Lorena": 3.7975,
            "Mario": 2.1075, "Narda": 14.30, "Octave": 9.0775, "Priscilla": 10.3075,
            "Raymond": 1.5075, "Sonia": 2.6225,
            "Iona": 9.185, "Keli": 0.98,  # Central Pacific storms
        },
        'yearly_totals': {
            2024: 75.0, 2023: 117.0, 2022: 97.0, 2021: 86.0, 2020: 137.0,
            2019: 91.0, 2018: 316.0, 2017: 107.0, 2016: 156.0, 2015: 252.0,
            2014: 173.0, 2013: 83.0, 2012: 113.0, 2011: 60.0, 2010: 66.0,
            2009: 119.0, 2008: 85.0, 2007: 49.0, 2006: 155.0, 2005: 136.0,
            2004: 113.0, 2003: 61.0, 2002: 113.0, 2001: 83.0, 2000: 75.0,
            1999: 56.0, 1998: 187.0, 1997: 167.0, 1996: 97.0, 1995: 52.0,
            1994: 145.0, 1993: 79.0, 1992: 183.0, 1991: 79.0,
        }
    }
}

# =============================================================================
# HELPER: Storm category from max wind (knots)
# =============================================================================

def get_category(max_wind):
    if max_wind >= 137:
        return "Cat 5"
    elif max_wind >= 113:
        return "Cat 4"
    elif max_wind >= 96:
        return "Cat 3"
    elif max_wind >= 83:
        return "Cat 2"
    elif max_wind >= 64:
        return "Cat 1"
    elif max_wind >= 34:
        return "TS"
    else:
        return "TD"


def is_major(max_wind):
    return max_wind >= 96


def get_noaa_classification(ace, basin_key):
    thresholds = BASINS[basin_key]['noaa_thresholds']
    if ace >= thresholds['above_normal_upper']:
        return "Extremely Active"
    elif ace >= thresholds['near_normal_upper']:
        return "Above Normal"
    elif ace >= thresholds['below_normal']:
        return "Near Normal"
    else:
        return "Below Normal"


def finalize_storm(storm):
    ace = 0.0
    for wind in storm['wind_readings']:
        ace += (wind ** 2) / 10000.0
    storm['ace'] = round(ace, 4)
    storm['category'] = get_category(storm['max_wind'])
    storm['is_major'] = is_major(storm['max_wind'])
    if storm['start_date'] and storm['end_date']:
        storm['duration_days'] = (storm['end_date'] - storm['start_date']).days + 1
    else:
        storm['duration_days'] = 0
    return storm

# =============================================================================
# HURDAT2 PARSING
# =============================================================================

def parse_hurdat2(basin_key):
    basin = BASINS[basin_key]
    url = basin['hurdat2_url']
    prefix = basin['storm_id_prefix']

    try:
        print(f"Downloading HURDAT2 database from NOAA...")
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as response:
            data = response.read().decode('utf-8')

        storms = []
        current_storm = None

        for line in data.strip().split('\n'):
            line = line.strip()
            if not line:
                continue

            # Header line
            if line.startswith(prefix) and ',' in line:
                if current_storm and current_storm['year'] >= START_YEAR:
                    storms.append(finalize_storm(current_storm))

                parts = line.split(',')
                storm_id = parts[0].strip()
                name = parts[1].strip()
                year = int(storm_id[4:8])

                current_storm = {
                    'id': storm_id,
                    'name': name if name else 'UNNAMED',
                    'year': year,
                    'max_wind': 0,
                    'wind_readings': [],
                    'start_date': None,
                    'end_date': None
                }

            # Also handle CP prefix for Central Pacific storms in the Pacific file
            elif basin_key == 'pacific' and line.startswith('CP') and ',' in line:
                if current_storm and current_storm['year'] >= START_YEAR:
                    storms.append(finalize_storm(current_storm))

                parts = line.split(',')
                storm_id = parts[0].strip()
                name = parts[1].strip()
                year = int(storm_id[4:8])

                current_storm = {
                    'id': storm_id,
                    'name': name if name else 'UNNAMED',
                    'year': year,
                    'max_wind': 0,
                    'wind_readings': [],
                    'start_date': None,
                    'end_date': None
                }

            # Data line
            elif current_storm and line[0].isdigit():
                parts = [p.strip() for p in line.split(',')]
                if len(parts) < 7:
                    continue

                try:
                    date_str = parts[0]
                    time_str = parts[1]
                    status = parts[3]
                    wind = int(parts[6])

                    # Only count synoptic times
                    if time_str not in SYNOPTIC_TIMES:
                        # Still track dates and max wind from non-synoptic times
                        if len(date_str) == 8:
                            date = datetime.strptime(date_str, '%Y%m%d')
                            if current_storm['start_date'] is None:
                                current_storm['start_date'] = date
                            current_storm['end_date'] = date
                        if wind > current_storm['max_wind']:
                            current_storm['max_wind'] = wind
                        continue

                    if len(date_str) == 8:
                        date = datetime.strptime(date_str, '%Y%m%d')
                        if current_storm['start_date'] is None:
                            current_storm['start_date'] = date
                        current_storm['end_date'] = date

                    if wind > current_storm['max_wind']:
                        current_storm['max_wind'] = wind

                    # ACE counts when:
                    # 1. Status is TS, HU, or SS (Subtropical Storm)
                    # 2. Wind speed >= 34 knots
                    # 3. Time is synoptic (already filtered above)
                    # Does NOT count TD, SD, EX, LO, WV, DB
                    if status in ACE_STATUSES and wind >= MIN_NAMED_STORM_WIND:
                        current_storm['wind_readings'].append(wind)

                except (ValueError, IndexError):
                    continue

        # Don't forget the last storm
        if current_storm and current_storm['year'] >= START_YEAR:
            storms.append(finalize_storm(current_storm))

        print(f"  ✓ Parsed {len(storms)} storms from {START_YEAR}-present")
        return storms

    except Exception as e:
        print(f"  ✗ Error downloading HURDAT2: {e}")
        print(f"  → Using backup data (yearly totals only)")
        return None

# =============================================================================
# CURRENT SEASON from climatlas.com
# =============================================================================

def _parse_section_storms(section_html, storm_pattern, excluded_names):
    """Parse storms from a section of HTML, returning dict with ACE and max_wind."""
    storms = {}
    for match in re.finditer(storm_pattern, section_html):
        name = match.group(1).strip().title()
        max_wind = int(match.group(2))
        ace_str = match.group(3).replace('*', '')
        ace = float(ace_str)

        if name in excluded_names:
            continue

        storms[name] = {'ace': ace, 'max_wind': max_wind}
    return storms


def _find_section(html, year, basin_header):
    """Find and extract a year+basin section from the climatlas HTML."""
    section_header_pattern = rf'\*?\*?{year}\s+{basin_header}'
    section_match = re.search(section_header_pattern, html)
    if not section_match:
        return None

    section_start = section_match.start()
    next_section = re.search(
        r'\*?\*?\d{4}\s+(?:North Atlantic|Eastern North Pacific|Central North Pacific|Western North Pacific|Northern Indian|Southern Hemisphere)',
        html[section_start + 10:]
    )
    section_end = (section_start + 10 + next_section.start()) if next_section else len(html)
    return html[section_start:section_end]


def get_current_season(basin_key):
    basin = BASINS[basin_key]
    current_year = datetime.now().year

    excluded_names = {'Ptc', 'Td', 'Sd', 'One', 'Two', 'Three', 'Four',
                      'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten',
                      'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen',
                      'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen', 'Twenty'}

    basin_headers = {
        'atlantic': r'North Atlantic Basin',
        'pacific': r'Eastern North Pacific',
    }
    basin_header = basin_headers[basin_key]
    storm_pattern = basin['climatlas_storm_pattern']

    try:
        print(f"Fetching current season data from climatlas.com...")
        req = urllib.request.Request(CURRENT_SEASON_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as response:
            html = response.read().decode('utf-8', errors='replace')

        for year in [current_year, current_year - 1]:
            section_html = _find_section(html, year, basin_header)
            if not section_html:
                continue

            storms = _parse_section_storms(section_html, storm_pattern, excluded_names)

            # For Pacific, also include Central Pacific storms
            if basin.get('climatlas_central_pattern') and basin.get('climatlas_central_storm_pattern'):
                central_section = _find_section(html, year, basin['climatlas_central_pattern'])
                if central_section:
                    central_storms = _parse_section_storms(
                        central_section,
                        basin['climatlas_central_storm_pattern'],
                        excluded_names
                    )
                    if central_storms:
                        print(f"  ✓ Found {len(central_storms)} Central Pacific storms")
                        storms.update(central_storms)

            if storms:
                total = round(sum(s['ace'] for s in storms.values()), 4)
                print(f"  ✓ Found {len(storms)} storms for {year} season")
                print(f"  ✓ Total ACE: {total:.2f}")

                ace_dict = {name: data['ace'] for name, data in storms.items()}

                return {
                    'year': year,
                    'storms': ace_dict,
                    'storm_details': storms,  # {name: {ace, max_wind}}
                    'total': total,
                }
            else:
                print(f"  ℹ {year} {basin['name']} section found but no storms yet")

        print(f"  ℹ No {current_year} storms found (likely off-season)")
        print(f"  → Using backup data...")
        return _backup_current(basin_key)

    except Exception as e:
        print(f"  ✗ Error fetching current season: {e}")
        print(f"  → Using backup data...")
        return _backup_current(basin_key)


def _backup_current(basin_key):
    backup = BACKUP_DATA[basin_key]
    storms = backup['storms']
    total = round(sum(storms.values()), 4)
    # Build storm_details from backup (no max_wind available)
    detail = {name: {'ace': ace, 'max_wind': 0} for name, ace in storms.items()}
    print(f"  ⚠ Using backup data for {backup['year']} season ({len(storms)} storms, ACE={total:.2f})")
    return {'year': backup['year'], 'storms': storms, 'storm_details': detail, 'total': total}


def build_current_storm_records(current):
    """Build storm detail records from climatlas data (like HURDAT2 records but from real-time data).
    Returns list of dicts compatible with historical_storms format."""
    records = []
    storm_details = current.get('storm_details', {})
    year = current['year']

    for name, data in storm_details.items():
        max_wind = data.get('max_wind', 0)
        ace = data.get('ace', 0)
        cat = get_category(max_wind)
        is_major = max_wind >= 96

        records.append({
            'name': name,
            'year': year,
            'max_wind': max_wind,
            'ace': ace,
            'category': cat,
            'is_major': is_major,
            'duration_days': 0,  # Not available from climatlas
            'wind_readings': [],
        })
    return records

# =============================================================================
# CALCULATE YEARLY TOTALS & STATISTICS
# =============================================================================

def calculate_yearly_totals(storms):
    totals = {}
    for storm in storms:
        year = storm['year']
        if year not in totals:
            totals[year] = 0.0
        totals[year] += storm['ace']
    for year in totals:
        totals[year] = round(totals[year], 2)
    return totals


def calculate_yearly_stats(storms):
    """Calculate detailed stats per year for insights."""
    stats = {}
    for storm in storms:
        year = storm['year']
        if year not in stats:
            stats[year] = {
                'named_storms': 0,
                'hurricanes': 0,
                'major_hurricanes': 0,
                'ace': 0.0,
                'ace_leader': None,
                'ace_leader_value': 0.0,
                'longest_storm': None,
                'longest_days': 0,
            }
        s = stats[year]
        s['named_storms'] += 1
        if storm['max_wind'] >= 64:
            s['hurricanes'] += 1
        if storm['max_wind'] >= 96:
            s['major_hurricanes'] += 1
        s['ace'] += storm['ace']
        if storm['ace'] > s['ace_leader_value']:
            s['ace_leader'] = storm['name']
            s['ace_leader_value'] = storm['ace']
        if storm['duration_days'] > s['longest_days']:
            s['longest_storm'] = storm['name']
            s['longest_days'] = storm['duration_days']

    for year in stats:
        stats[year]['ace'] = round(stats[year]['ace'], 2)
    return stats


def find_similar_seasons(target_ace, yearly_totals, exclude_year=None):
    """Find the 3 historical seasons with ACE closest to the target."""
    candidates = [(y, ace) for y, ace in yearly_totals.items() if y != exclude_year]
    candidates.sort(key=lambda x: abs(x[1] - target_ace))
    return candidates[:3]


# =============================================================================
# GENERATE SEASON INSIGHTS
# =============================================================================

def generate_insights(basin_key, current, yearly_totals, historical_storms, yearly_stats):
    """Generate interesting facts and insights for the dashboard and Discord."""
    basin = BASINS[basin_key]
    insights = []
    current_ace = current['total']
    current_year = current['year']
    storms = current['storms']

    # 1. ACE Leader
    if storms:
        leader_name = max(storms, key=storms.get)
        leader_ace = storms[leader_name]
        leader_pct = (leader_ace / current_ace * 100) if current_ace > 0 else 0
        insights.append(f"🌀 ACE Leader: {leader_name} with {leader_ace:.1f} ACE ({leader_pct:.0f}% of season total)")

    # 2. NOAA classification
    classification = get_noaa_classification(current_ace, basin_key)
    insights.append(f"📊 Season Classification: {classification} (ACE: {current_ace:.1f})")

    # 3. Similar historical seasons
    similar = find_similar_seasons(current_ace, yearly_totals, exclude_year=current_year)
    if similar:
        similar_str = ", ".join([f"{y} ({ace:.1f})" for y, ace in similar])
        insights.append(f"📈 Most Similar Seasons: {similar_str}")

    # 4. Historical ranking
    all_years = list(yearly_totals.items())
    all_years.append((current_year, current_ace))
    all_years.sort(key=lambda x: x[1], reverse=True)
    rank = next(i + 1 for i, (y, _) in enumerate(all_years) if y == current_year)
    total_seasons = len(all_years)
    insights.append(f"🏆 Historical Rank: #{rank} of {total_seasons} seasons since {START_YEAR}")

    # 5. Comparison to normal
    normal = basin['normal_ace']
    pct_of_normal = (current_ace / normal * 100) if normal > 0 else 0
    above_below = "above" if current_ace > normal else "below"
    insights.append(f"📉 {pct_of_normal:.0f}% of normal ({above_below} the {normal:.1f} average)")

    # 6. Major hurricane count (from current storms — HURDAT2 or climatlas)
    current_storms_detail = [s for s in historical_storms if s['year'] == current_year] if historical_storms else []
    if not current_storms_detail:
        current_storms_detail = build_current_storm_records(current)

    if current_storms_detail:
        major_count = sum(1 for s in current_storms_detail if s['is_major'])
        hurricane_count = sum(1 for s in current_storms_detail if s['max_wind'] >= 64)
        avg_major = basin['avg_major_hurricanes']
        avg_hurricanes = basin['avg_hurricanes']
        insights.append(f"🌀 Hurricanes: {hurricane_count} (season avg: {avg_hurricanes})")
        insights.append(f"⚡ Major Hurricanes: {major_count} (season avg: {avg_major})")

    # 7. % of ACE from top storm
    if storms and current_ace > 0:
        leader_name = max(storms, key=storms.get)
        leader_ace = storms[leader_name]
        leader_pct = leader_ace / current_ace * 100
        if leader_pct > 30:
            insights.append(f"💪 Top-heavy season: {leader_pct:.0f}% of all ACE from just {leader_name}")

    # 8. Number of storms vs average
    num_storms = len(storms)
    avg_storms = basin['avg_named_storms']
    insights.append(f"🌊 Named Storms: {num_storms} (season avg: {avg_storms})")

    # 9. Longest storm this season (only from HURDAT2 which has date ranges)
    if historical_storms:
        hurdat_current = [s for s in historical_storms if s['year'] == current_year]
        if hurdat_current:
            longest = max(hurdat_current, key=lambda s: s['duration_days'])
            if longest['duration_days'] > 0:
                insights.append(f"⏱️ Longest Storm: {longest['name']} ({longest['duration_days']} days)")

    # 10. Compare to same date last year
    last_year = current_year - 1
    if last_year in yearly_totals:
        last_year_total = yearly_totals[last_year]
        insights.append(f"📅 Last Year ({last_year}) Final Total: {last_year_total:.1f} ACE")

    # 11. All-time single storm record comparison
    record = basin['all_time_single_storm_ace']
    if storms:
        leader_name = max(storms, key=storms.get)
        leader_ace = storms[leader_name]
        pct_of_record = leader_ace / record['ace'] * 100
        if pct_of_record > 50:
            insights.append(f"🎯 {leader_name} at {pct_of_record:.0f}% of all-time single-storm record ({record['name']}: {record['ace']})")

    return insights

# =============================================================================
# GENERATE DISCORD UPDATE TEXT
# =============================================================================

def generate_discord_text(basin_key, current, yearly_totals, insights):
    """Generate copy/paste ready Discord update text."""
    basin = BASINS[basin_key]
    current_year = current['year']
    current_ace = current['total']
    storms = current['storms']
    now = datetime.now()

    lines = []
    lines.append(f"🌀 **{basin['name']} ACE Update** — {now.strftime('%B %d, %Y')}")
    lines.append("")

    # Storm list sorted by ACE descending
    if storms:
        sorted_storms = sorted(storms.items(), key=lambda x: x[1], reverse=True)

        # Show top storms
        shown = sorted_storms[:MAX_STORMS_DISCORD]
        remaining = sorted_storms[MAX_STORMS_DISCORD:]

        for name, ace in shown:
            lines.append(f"{name} = {ace:.1f}")

        if remaining:
            remaining_ace = sum(ace for _, ace in remaining)
            lines.append(f"+ {len(remaining)} other storms = {remaining_ace:.1f}")

    lines.append("")
    lines.append(f"**Total for {current_year} Season = {current_ace:.1f}**")

    # Comparison to last year (in JP's preferred format)
    last_year = current_year - 1
    if last_year in yearly_totals:
        lines.append(f"Total for {last_year} Season (Final) = {yearly_totals[last_year]:.1f}")

    # NOAA classification
    classification = get_noaa_classification(current_ace, basin_key)
    normal = basin['normal_ace']
    pct = (current_ace / normal * 100) if normal > 0 else 0
    lines.append(f"Season Status: {classification} ({pct:.0f}% of normal)")

    lines.append("")

    # Historical rank
    all_years = list(yearly_totals.items())
    all_years.append((current_year, current_ace))
    all_years.sort(key=lambda x: x[1], reverse=True)
    rank = next(i + 1 for i, (y, _) in enumerate(all_years) if y == current_year)
    total_seasons = len(all_years)
    lines.append(f"Historical Rank: #{rank} of {total_seasons} (since {START_YEAR})")

    # Top 3 similar seasons
    similar = find_similar_seasons(current_ace, yearly_totals, exclude_year=current_year)
    if similar:
        similar_str = ", ".join([f"{y} ({ace:.1f})" for y, ace in similar])
        lines.append(f"Similar Seasons: {similar_str}")

    # Fun facts (pick top 3 non-redundant insights)
    fact_insights = [i for i in insights if not any(skip in i for skip in ['Classification', 'Similar', 'Rank', 'of normal'])]
    if fact_insights:
        lines.append("")
        for fact in fact_insights[:3]:
            lines.append(fact)

    return "\n".join(lines)

# =============================================================================
# CREATE SPREADSHEET
# =============================================================================

def create_spreadsheet(basin_key, historical_storms, current, yearly_totals, yearly_stats, insights, discord_text):
    basin = BASINS[basin_key]
    current_year = current['year']
    current_ace = current['total']
    storms = current['storms']

    wb = Workbook()

    # --- Colors and styles ---
    header_font = Font(name='Arial', bold=True, color='FFFFFF', size=11)
    header_fill = PatternFill('solid', fgColor='1a2d4a')
    subheader_font = Font(name='Arial', bold=True, size=10)
    subheader_fill = PatternFill('solid', fgColor='d6e4f0')
    data_font = Font(name='Arial', size=10)
    highlight_fill = PatternFill('solid', fgColor='FFF2CC')
    major_fill = PatternFill('solid', fgColor='FFD7D7')
    insight_fill = PatternFill('solid', fgColor='E8F5E9')
    discord_fill = PatternFill('solid', fgColor='5865F2')
    discord_header_font = Font(name='Arial', bold=True, color='FFFFFF', size=12)
    discord_text_font = Font(name='Consolas', size=11)
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )

    def style_header_row(ws, row, max_col):
        for col in range(1, max_col + 1):
            cell = ws.cell(row=row, column=col)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center', wrap_text=True)
            cell.border = thin_border

    def style_data_cell(ws, row, col, value, fmt=None):
        cell = ws.cell(row=row, column=col, value=value)
        cell.font = data_font
        cell.border = thin_border
        if fmt:
            cell.number_format = fmt
        return cell

    # =========================================================================
    # TAB 1: SUMMARY
    # =========================================================================
    ws_summary = wb.active
    ws_summary.title = "Summary"
    ws_summary.sheet_properties.tabColor = "1a2d4a"

    # Title
    ws_summary['A1'] = f"{basin['name']} Hurricane Season {current_year}"
    ws_summary['A1'].font = Font(name='Arial', bold=True, size=16, color='1a2d4a')
    ws_summary.merge_cells('A1:D1')

    ws_summary['A2'] = f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}"
    ws_summary['A2'].font = Font(name='Arial', italic=True, size=9, color='666666')

    # Key stats section
    row = 4
    stats_headers = ['Metric', 'Value']
    for col, header in enumerate(stats_headers, 1):
        ws_summary.cell(row=row, column=col, value=header)
    style_header_row(ws_summary, row, 2)

    normal = basin['normal_ace']
    pct_normal = (current_ace / normal * 100) if normal > 0 else 0
    classification = get_noaa_classification(current_ace, basin_key)

    # Rankings
    all_years = list(yearly_totals.items())
    all_years.append((current_year, current_ace))
    all_years.sort(key=lambda x: x[1], reverse=True)
    rank = next(i + 1 for i, (y, _) in enumerate(all_years) if y == current_year)
    total_seasons = len(all_years)

    stats_data = [
        ("Season ACE Total", round(current_ace, 1)),
        ("Named Storms", len(storms)),
        ("Normal Season ACE (1991-2020)", normal),
        ("% of Normal", f"{pct_normal:.0f}%"),
        ("NOAA Classification", classification),
        (f"Historical Rank (since {START_YEAR})", f"#{rank} of {total_seasons}"),
    ]

    # Add major hurricane count — use climatlas storm_details if HURDAT2 doesn't have current year
    current_detail = [s for s in historical_storms if s['year'] == current_year] if historical_storms else []
    if not current_detail:
        # Build from climatlas data
        current_detail = build_current_storm_records(current)

    if current_detail:
        major_count = sum(1 for s in current_detail if s['is_major'])
        hurricane_count = sum(1 for s in current_detail if s['max_wind'] >= 64)
        stats_data.append(("Hurricanes", hurricane_count))
        stats_data.append(("Major Hurricanes (Cat 3+)", major_count))

    # Last year comparison
    last_year = current_year - 1
    if last_year in yearly_totals:
        stats_data.append((f"{last_year} Season Total (Final)", yearly_totals[last_year]))

    for i, (metric, value) in enumerate(stats_data):
        r = row + 1 + i
        style_data_cell(ws_summary, r, 1, metric)
        style_data_cell(ws_summary, r, 2, value)

    # Similar seasons
    row_after_stats = row + 1 + len(stats_data) + 2
    ws_summary.cell(row=row_after_stats, column=1, value="Similar Historical Seasons")
    ws_summary.cell(row=row_after_stats, column=1).font = Font(name='Arial', bold=True, size=12, color='1a2d4a')

    similar = find_similar_seasons(current_ace, yearly_totals, exclude_year=current_year)
    for col, header in enumerate(['Year', 'ACE', 'Difference'], 1):
        ws_summary.cell(row=row_after_stats + 1, column=col, value=header)
    style_header_row(ws_summary, row_after_stats + 1, 3)

    for i, (year, ace) in enumerate(similar):
        r = row_after_stats + 2 + i
        style_data_cell(ws_summary, r, 1, year, '0')
        style_data_cell(ws_summary, r, 2, round(ace, 1), '0.0')
        style_data_cell(ws_summary, r, 3, round(abs(ace - current_ace), 1), '0.0')

    # Season Insights section
    insight_row = row_after_stats + 2 + len(similar) + 2
    ws_summary.cell(row=insight_row, column=1, value="Season Insights")
    ws_summary.cell(row=insight_row, column=1).font = Font(name='Arial', bold=True, size=12, color='1a2d4a')

    for i, insight in enumerate(insights):
        r = insight_row + 1 + i
        cell = ws_summary.cell(row=r, column=1, value=insight)
        cell.font = data_font
        cell.fill = insight_fill
        ws_summary.merge_cells(start_row=r, start_column=1, end_row=r, end_column=4)

    # Column widths
    ws_summary.column_dimensions['A'].width = 35
    ws_summary.column_dimensions['B'].width = 20
    ws_summary.column_dimensions['C'].width = 15
    ws_summary.column_dimensions['D'].width = 15

    # =========================================================================
    # TAB 2: CURRENT SEASON STORMS
    # =========================================================================
    ws_storms = wb.create_sheet(f"{current_year} Storms")
    ws_storms.sheet_properties.tabColor = "ff6b35"

    headers = ['Storm', 'ACE', '% of Total', 'Category', 'Max Wind (kt)', 'Duration (days)']
    for col, header in enumerate(headers, 1):
        ws_storms.cell(row=1, column=col, value=header)
    style_header_row(ws_storms, 1, len(headers))

    sorted_storms = sorted(storms.items(), key=lambda x: x[1], reverse=True)

    # Try to match with historical_storms for extra detail, or use climatlas details
    storm_details = {}
    if historical_storms:
        for s in historical_storms:
            if s['year'] == current_year:
                storm_details[s['name'].title()] = s

    # If HURDAT2 doesn't have current year, build from climatlas data
    if not storm_details:
        for rec in build_current_storm_records(current):
            storm_details[rec['name']] = rec

    for i, (name, ace) in enumerate(sorted_storms):
        row = 2 + i
        pct = (ace / current_ace * 100) if current_ace > 0 else 0
        detail = storm_details.get(name, None)

        style_data_cell(ws_storms, row, 1, name)
        style_data_cell(ws_storms, row, 2, round(ace, 2), '0.00')
        style_data_cell(ws_storms, row, 3, round(pct, 1), '0.0"%"')

        if detail:
            cat_cell = style_data_cell(ws_storms, row, 4, detail['category'])
            style_data_cell(ws_storms, row, 5, detail['max_wind'], '0')
            # Duration: show N/A for current season storms from climatlas (no date data)
            dur = detail['duration_days']
            style_data_cell(ws_storms, row, 6, dur if dur > 0 else "N/A")
            if detail['is_major']:
                for c in range(1, len(headers) + 1):
                    ws_storms.cell(row=row, column=c).fill = major_fill
        else:
            style_data_cell(ws_storms, row, 4, "—")
            style_data_cell(ws_storms, row, 5, "—")
            style_data_cell(ws_storms, row, 6, "—")

    # Totals row
    total_row = 2 + len(sorted_storms)
    ws_storms.cell(row=total_row, column=1, value="TOTAL").font = Font(name='Arial', bold=True, size=10)
    ws_storms.cell(row=total_row, column=2, value=round(current_ace, 2))
    ws_storms.cell(row=total_row, column=2).font = Font(name='Arial', bold=True, size=10)
    ws_storms.cell(row=total_row, column=2).number_format = '0.00'
    ws_storms.cell(row=total_row, column=3, value="100%").font = Font(name='Arial', bold=True, size=10)

    for col in range(1, len(headers) + 1):
        ws_storms.cell(row=total_row, column=col).fill = PatternFill('solid', fgColor='D9E2F3')
        ws_storms.cell(row=total_row, column=col).border = thin_border

    ws_storms.column_dimensions['A'].width = 18
    ws_storms.column_dimensions['B'].width = 12
    ws_storms.column_dimensions['C'].width = 12
    ws_storms.column_dimensions['D'].width = 12
    ws_storms.column_dimensions['E'].width = 15
    ws_storms.column_dimensions['F'].width = 15

    # =========================================================================
    # TAB 3: HISTORICAL STORMS
    # =========================================================================
    ws_hist = wb.create_sheet("Historical Storms")
    ws_hist.sheet_properties.tabColor = "2ed573"

    if historical_storms:
        # Include current year storms from climatlas if not in HURDAT2
        has_current_year = any(s['year'] == current_year for s in historical_storms)
        all_storms = list(historical_storms)
        if not has_current_year:
            all_storms.extend(build_current_storm_records(current))

        hist_headers = ['Year', 'Name', 'Category', 'Max Wind (kt)', 'ACE', 'Duration (days)', 'Major?']
        for col, header in enumerate(hist_headers, 1):
            ws_hist.cell(row=1, column=col, value=header)
        style_header_row(ws_hist, 1, len(hist_headers))

        sorted_historical = sorted(all_storms, key=lambda s: (-s['year'], -s['ace']))
        for i, storm in enumerate(sorted_historical):
            row = 2 + i
            style_data_cell(ws_hist, row, 1, storm['year'], '0')
            style_data_cell(ws_hist, row, 2, storm['name'].title())
            style_data_cell(ws_hist, row, 3, storm['category'])
            style_data_cell(ws_hist, row, 4, storm['max_wind'], '0')
            style_data_cell(ws_hist, row, 5, round(storm['ace'], 2), '0.00')
            # Duration: show N/A for current season storms sourced from climatlas
            dur = storm['duration_days']
            style_data_cell(ws_hist, row, 6, dur if dur > 0 else "N/A")
            style_data_cell(ws_hist, row, 7, "Yes" if storm['is_major'] else "No")

            if storm['year'] == current_year:
                for c in range(1, len(hist_headers) + 1):
                    ws_hist.cell(row=row, column=c).fill = highlight_fill

        ws_hist.column_dimensions['A'].width = 10
        ws_hist.column_dimensions['B'].width = 18
        ws_hist.column_dimensions['C'].width = 12
        ws_hist.column_dimensions['D'].width = 15
        ws_hist.column_dimensions['E'].width = 12
        ws_hist.column_dimensions['F'].width = 15
        ws_hist.column_dimensions['G'].width = 10
    else:
        ws_hist.cell(row=1, column=1, value="Historical storm data unavailable (HURDAT2 download failed)")

    # =========================================================================
    # TAB 4: YEARLY TOTALS
    # =========================================================================
    ws_yearly = wb.create_sheet("Yearly Totals")
    ws_yearly.sheet_properties.tabColor = "ffc107"

    yearly_headers = ['Rank', 'Year', 'ACE', '% of Normal', 'Classification',
                      'Named Storms', 'Hurricanes', 'Major Hurricanes']
    for col, header in enumerate(yearly_headers, 1):
        ws_yearly.cell(row=1, column=col, value=header)
    style_header_row(ws_yearly, 1, len(yearly_headers))

    all_years_data = list(yearly_totals.items())
    all_years_data.append((current_year, current_ace))
    all_years_data.sort(key=lambda x: x[1], reverse=True)

    for i, (year, ace) in enumerate(all_years_data):
        row = 2 + i
        pct = (ace / basin['normal_ace'] * 100) if basin['normal_ace'] > 0 else 0
        classification = get_noaa_classification(ace, basin_key)

        style_data_cell(ws_yearly, row, 1, i + 1, '0')
        style_data_cell(ws_yearly, row, 2, year, '0')
        style_data_cell(ws_yearly, row, 3, round(ace, 1), '0.0')
        style_data_cell(ws_yearly, row, 4, f"{pct:.0f}%")
        style_data_cell(ws_yearly, row, 5, classification)

        # Add storm counts if we have stats
        if yearly_stats and year in yearly_stats:
            ys = yearly_stats[year]
            style_data_cell(ws_yearly, row, 6, ys['named_storms'], '0')
            style_data_cell(ws_yearly, row, 7, ys['hurricanes'], '0')
            style_data_cell(ws_yearly, row, 8, ys['major_hurricanes'], '0')
        elif year == current_year:
            # Use climatlas storm_details for current year
            cur_records = build_current_storm_records(current)
            style_data_cell(ws_yearly, row, 6, len(cur_records), '0')
            style_data_cell(ws_yearly, row, 7, sum(1 for s in cur_records if s['max_wind'] >= 64), '0')
            style_data_cell(ws_yearly, row, 8, sum(1 for s in cur_records if s['is_major']), '0')
        else:
            style_data_cell(ws_yearly, row, 6, "—")
            style_data_cell(ws_yearly, row, 7, "—")
            style_data_cell(ws_yearly, row, 8, "—")

        if year == current_year:
            for c in range(1, len(yearly_headers) + 1):
                ws_yearly.cell(row=row, column=c).fill = highlight_fill

    ws_yearly.column_dimensions['A'].width = 8
    ws_yearly.column_dimensions['B'].width = 10
    ws_yearly.column_dimensions['C'].width = 10
    ws_yearly.column_dimensions['D'].width = 12
    ws_yearly.column_dimensions['E'].width = 18
    ws_yearly.column_dimensions['F'].width = 14
    ws_yearly.column_dimensions['G'].width = 12
    ws_yearly.column_dimensions['H'].width = 16

    # =========================================================================
    # TAB 5: DISCORD UPDATE
    # =========================================================================
    ws_discord = wb.create_sheet("Discord Update")
    ws_discord.sheet_properties.tabColor = "5865F2"

    # Header
    ws_discord['A1'] = "Discord Update — Copy Everything Below"
    ws_discord['A1'].font = discord_header_font
    ws_discord['A1'].fill = discord_fill
    ws_discord.merge_cells('A1:D1')

    ws_discord['A2'] = "Select cells A4 through the end, then copy and paste into Discord"
    ws_discord['A2'].font = Font(name='Arial', italic=True, size=9, color='666666')

    # Discord text content — one line per row for easy copy/paste
    discord_lines = discord_text.split('\n')
    for i, line in enumerate(discord_lines):
        row = 4 + i
        cell = ws_discord.cell(row=row, column=1, value=line)
        cell.font = discord_text_font

    ws_discord.column_dimensions['A'].width = 80

    return wb

# =============================================================================
# CONSOLE REPORT
# =============================================================================

def generate_console_report(basin_key, current, yearly_totals, insights):
    basin = BASINS[basin_key]
    current_year = current['year']
    current_ace = current['total']
    storms = current['storms']

    lines = []
    lines.append(f"\n{'─' * 50}")
    lines.append(f"  {basin['name']} Season {current_year} — ACE: {current_ace:.1f}")
    lines.append(f"{'─' * 50}")

    if storms:
        sorted_storms = sorted(storms.items(), key=lambda x: x[1], reverse=True)
        lines.append(f"\n  {'Storm':<18} {'ACE':>8}  {'% of Total':>10}")
        lines.append(f"  {'─' * 40}")
        for name, ace in sorted_storms:
            pct = (ace / current_ace * 100) if current_ace > 0 else 0
            lines.append(f"  {name:<18} {ace:>8.2f}  {pct:>9.1f}%")
        lines.append(f"  {'─' * 40}")
        lines.append(f"  {'TOTAL':<18} {current_ace:>8.2f}  {'100.0%':>10}")

    lines.append(f"\n  Season Insights:")
    for insight in insights:
        lines.append(f"    {insight}")

    return "\n".join(lines)

# =============================================================================
# PROCESS A BASIN
# =============================================================================

def process_basin(basin_key):
    basin = BASINS[basin_key]

    print("\n" + "=" * 50)
    print(f"{basin['name']} Hurricane ACE Tracker")
    print("=" * 50 + "\n")

    # Get historical data
    historical_storms = parse_hurdat2(basin_key)

    if historical_storms:
        yearly_totals = calculate_yearly_totals(historical_storms)
        yearly_stats = calculate_yearly_stats(historical_storms)
    else:
        yearly_totals = BACKUP_DATA[basin_key]['yearly_totals']
        yearly_stats = None

    # Get current season
    current = get_current_season(basin_key)

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

    # Create spreadsheet
    print(f"\n{'─' * 50}")
    print("Creating spreadsheet...")

    wb = create_spreadsheet(basin_key, historical_storms, current, yearly_totals, yearly_stats, insights, discord_text)

    if wb:
        try:
            if not os.path.exists(OUTPUT_FOLDER):
                os.makedirs(OUTPUT_FOLDER)
                logger.info(f"Created output directory: {OUTPUT_FOLDER}")
        except OSError as e:
            logger.error(f"Failed to create directory {OUTPUT_FOLDER}: {e}")
            print(f"  ✗ Error: Could not create output folder")
            return None

        output_path = os.path.join(OUTPUT_FOLDER, basin['output_file'])
        try:
            wb.save(output_path)
            print(f"  ✓ Saved to: {output_path}")
        except (OSError, PermissionError) as e:
            logger.error(f"Failed to save {output_path}: {e}")
            print(f"  ✗ Error: Could not save {output_path}")
            return None

        if historical_storms:
            print(f"  ✓ {len(historical_storms)} storms in Historical Storms sheet")
            print(f"  ✓ {len(yearly_totals)} seasons in Yearly Totals sheet")

        print(f"  ✓ Discord Update tab ready for copy/paste")

        # Return data for dashboard
        return {
            'basin_key': basin_key,
            'current': current,
            'yearly_totals': yearly_totals,
            'insights': insights,
        }

    return None


# =============================================================================
# DASHBOARD HTML
# =============================================================================

def generate_dashboard_html(basin_data):
    """Generate a mobile-friendly HTML dashboard for both basins."""
    now = datetime.now()

    # Build storm rows for each basin
    def storm_rows_html(current):
        storms = current['storms']
        details = current.get('storm_details', {})
        total = current['total']
        sorted_storms = sorted(storms.items(), key=lambda x: x[1], reverse=True)
        rows = []
        for name, ace in sorted_storms:
            pct = (ace / total * 100) if total > 0 else 0
            wind = details.get(name, {}).get('max_wind', 0)
            cat = get_category(wind) if wind > 0 else '—'
            is_major = wind >= 96
            row_class = ' class="major"' if is_major else ''
            rows.append(f'<tr{row_class}><td>{name}</td><td>{ace:.1f}</td><td>{pct:.1f}%</td><td>{cat}</td><td>{wind if wind > 0 else "—"}</td></tr>')
        return '\n'.join(rows)

    def insight_items_html(insights):
        return '\n'.join(f'<li>{i}</li>' for i in insights)

    sections = []
    for bd in basin_data:
        if not bd:
            continue
        basin = BASINS[bd['basin_key']]
        current = bd['current']
        yearly_totals = bd['yearly_totals']
        insights = bd['insights']
        current_ace = current['total']
        current_year = current['year']
        normal = basin['normal_ace']
        pct_normal = (current_ace / normal * 100) if normal > 0 else 0
        classification = get_noaa_classification(current_ace, bd['basin_key'])

        # Storm counts from details
        details = current.get('storm_details', {})
        named = len(details)
        hurricanes = sum(1 for d in details.values() if d.get('max_wind', 0) >= 64)
        majors = sum(1 for d in details.values() if d.get('max_wind', 0) >= 96)

        # Historical rank
        all_years = list(yearly_totals.items()) + [(current_year, current_ace)]
        all_years.sort(key=lambda x: x[1], reverse=True)
        rank = next(i + 1 for i, (y, _) in enumerate(all_years) if y == current_year)
        total_seasons = len(all_years)

        # ACE gauge percentage (cap at 200% for display)
        gauge_pct = min(pct_normal, 200)

        sections.append(f'''
    <div class="basin-card" id="{bd['basin_key']}">
      <h2>{basin['name']} — {current_year} Season</h2>
      <div class="stats-grid">
        <div class="stat-box ace-total">
          <div class="stat-label">Season ACE</div>
          <div class="stat-value">{current_ace:.1f}</div>
          <div class="stat-sub">{pct_normal:.0f}% of normal ({normal})</div>
          <div class="gauge"><div class="gauge-fill" style="width:{gauge_pct/2}%"></div></div>
        </div>
        <div class="stat-box"><div class="stat-label">Classification</div><div class="stat-value small">{classification}</div></div>
        <div class="stat-box"><div class="stat-label">Named Storms</div><div class="stat-value">{named}</div></div>
        <div class="stat-box"><div class="stat-label">Hurricanes</div><div class="stat-value">{hurricanes}</div></div>
        <div class="stat-box major-box"><div class="stat-label">Major Hurricanes</div><div class="stat-value">{majors}</div></div>
        <div class="stat-box"><div class="stat-label">Rank (since {START_YEAR})</div><div class="stat-value">#{rank}<span class="stat-sub"> of {total_seasons}</span></div></div>
      </div>

      <h3>Storm Breakdown</h3>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Storm</th><th>ACE</th><th>%</th><th>Category</th><th>Wind (kt)</th></tr></thead>
          <tbody>
            {storm_rows_html(current)}
            <tr class="total-row"><td><b>TOTAL</b></td><td><b>{current_ace:.1f}</b></td><td><b>100%</b></td><td></td><td></td></tr>
          </tbody>
        </table>
      </div>

      <h3>Season Insights</h3>
      <ul class="insights">{insight_items_html(insights)}</ul>
    </div>''')

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Hurricane ACE Dashboard</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background:#0a1628; color:#e0e6ed; padding:12px; }}
  h1 {{ text-align:center; color:#4fc3f7; font-size:1.4em; margin:8px 0; }}
  .updated {{ text-align:center; color:#78909c; font-size:0.8em; margin-bottom:16px; }}
  .toggle {{ display:flex; justify-content:center; gap:8px; margin-bottom:16px; }}
  .toggle button {{ padding:8px 20px; border:1px solid #4fc3f7; background:transparent; color:#4fc3f7; border-radius:20px; cursor:pointer; font-size:0.9em; }}
  .toggle button.active {{ background:#4fc3f7; color:#0a1628; font-weight:bold; }}
  .basin-card {{ background:#132238; border-radius:12px; padding:16px; margin-bottom:16px; display:none; }}
  .basin-card.active {{ display:block; }}
  h2 {{ color:#4fc3f7; font-size:1.2em; margin-bottom:12px; border-bottom:1px solid #1e3a5f; padding-bottom:8px; }}
  h3 {{ color:#81d4fa; font-size:1em; margin:16px 0 8px; }}
  .stats-grid {{ display:grid; grid-template-columns:repeat(3,1fr); gap:8px; }}
  .stat-box {{ background:#1a2d4a; border-radius:8px; padding:10px; text-align:center; }}
  .stat-box.ace-total {{ grid-column:span 3; }}
  .stat-label {{ color:#78909c; font-size:0.75em; text-transform:uppercase; }}
  .stat-value {{ color:#fff; font-size:1.5em; font-weight:bold; }}
  .stat-value.small {{ font-size:1.1em; }}
  .stat-sub {{ color:#78909c; font-size:0.75em; }}
  .major-box {{ border:1px solid #ef5350; }}
  .major-box .stat-value {{ color:#ef5350; }}
  .gauge {{ height:6px; background:#1e3a5f; border-radius:3px; margin-top:6px; }}
  .gauge-fill {{ height:100%; background:linear-gradient(90deg,#4fc3f7,#29b6f6,#ef5350); border-radius:3px; transition:width 0.5s; }}
  .table-wrap {{ overflow-x:auto; }}
  table {{ width:100%; border-collapse:collapse; font-size:0.85em; }}
  th {{ background:#1a2d4a; color:#4fc3f7; padding:8px 6px; text-align:left; position:sticky; top:0; }}
  td {{ padding:6px; border-bottom:1px solid #1e3a5f; }}
  tr.major {{ background:#2a1a1a; }}
  tr.major td {{ color:#ef8a80; font-weight:bold; }}
  tr.total-row {{ background:#1a2d4a; }}
  .insights {{ list-style:none; padding:0; }}
  .insights li {{ background:#1a2d4a; padding:8px 10px; margin:4px 0; border-radius:6px; font-size:0.85em; border-left:3px solid #4fc3f7; }}
  .sources {{ background:#0d1b2a; border-top:1px solid #1e3a5f; margin-top:24px; padding:16px 12px; border-radius:8px; }}
  .sources h4 {{ color:#78909c; font-size:0.8em; text-transform:uppercase; margin-bottom:8px; }}
  .sources a {{ color:#4fc3f7; text-decoration:none; font-size:0.78em; }}
  .sources a:hover {{ text-decoration:underline; }}
  .sources p {{ color:#546e7a; font-size:0.75em; margin-top:8px; line-height:1.5; }}
  .sources ul {{ list-style:none; padding:0; margin:0; }}
  .sources li {{ color:#78909c; font-size:0.78em; margin:4px 0; padding-left:12px; position:relative; }}
  .sources li::before {{ content:"•"; position:absolute; left:0; color:#4fc3f7; }}
  @media(min-width:768px) {{ body {{ max-width:900px; margin:0 auto; padding:24px; }} .stats-grid {{ grid-template-columns:repeat(6,1fr); }} .stat-box.ace-total {{ grid-column:span 6; }} }}
</style>
</head>
<body>
<h1>🌀 Hurricane ACE Dashboard</h1>
<div class="updated">Updated: {now.strftime('%B %d, %Y at %I:%M %p')}</div>
<div class="toggle">
  <button class="active" onclick="show('atlantic',this)">Atlantic</button>
  <button onclick="show('pacific',this)">Eastern Pacific</button>
</div>
{''.join(sections)}
<div class="sources">
  <h4>Data Sources</h4>
  <ul>
    <li><a href="https://www.nhc.noaa.gov/data/#hurdat" target="_blank">NOAA HURDAT2</a> — Historical best-track data (1991–present) for storm tracks, wind speeds, and ACE calculations</li>
    <li><a href="https://climatlas.com/tropical/" target="_blank">Climatlas.com (Dr. Ryan Maue)</a> — Current season real-time storm data, max intensity, and ACE values from ATCF advisories</li>
    <li><a href="https://www.cpc.ncep.noaa.gov/products/outlooks/background_information.shtml" target="_blank">NOAA CPC</a> — Season classification thresholds and 1991–2020 climatological normals</li>
  </ul>
  <p>ACE (Accumulated Cyclone Energy) is calculated at 6-hourly synoptic times (0000/0600/1200/1800 UTC) for systems at tropical storm strength or higher (≥34 kt), including subtropical storms. Formula: ACE = Σ(V²<sub>max</sub>) × 10⁻⁴. Categories use the Saffir-Simpson scale in knots.</p>
</div>
<script>
document.querySelectorAll('.basin-card')[0]?.classList.add('active');
function show(id,btn) {{
  document.querySelectorAll('.basin-card').forEach(c=>c.classList.remove('active'));
  document.querySelectorAll('.toggle button').forEach(b=>b.classList.remove('active'));
  document.getElementById(id)?.classList.add('active');
  btn.classList.add('active');
}}
</script>
</body>
</html>'''
    return html

# =============================================================================
# MAIN
# =============================================================================

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
        output_files.append(os.path.join(OUTPUT_FOLDER, BASINS['atlantic']['output_file']))
        basin_results.append(result)

    # Process Pacific
    result = process_basin('pacific')
    if result:
        output_files.append(os.path.join(OUTPUT_FOLDER, BASINS['pacific']['output_file']))
        basin_results.append(result)

    # Generate dashboard HTML
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

    print("\n" + "=" * 50)
    print("All done! Spreadsheets and dashboard updated.")
    if output_files:
        print(f"Files saved to: {OUTPUT_FOLDER}")
        for f in output_files:
            print(f"  → {os.path.basename(f)}")
    print("=" * 50)

    return output_files


if __name__ == "__main__":
    main()

"""
ace_data.py
===========
Data fetching, ACE calculation, and plain-text report generation for the
ACE Tracker. Fetches historical + current-season storm data via Tropycal,
computes Accumulated Cyclone Energy, and builds Discord/console report text.
"""

import os
import json
import logging
from datetime import datetime, timedelta, timezone
import tropycal.tracks as tracks

# Configured here (not just in the ace_tracker.py entrypoint) so that any
# direct import of this module — e.g. test_ace_tracker.py, or a future
# standalone script — gets the same formatted log output the CLI does,
# matching the original monolith's behavior where importing any part of it
# ran this exactly once at module load.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ===============================================================================
# CONFIGURATION
# ===============================================================================

LANDFALL_CACHE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "landfall_cache.json")


BASINS = {
    'atlantic': {
        'name': 'Atlantic',
        'tropycal_basin': 'north_atlantic',  # Tropycal basin name
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
        'name': 'East &amp; Central Pacific',
        'tropycal_basin': 'east_pacific',  # Tropycal basin name — includes both EP and CP storms
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


START_YEAR = 1991

# ACE Calculation Constants

SYNOPTIC_TIMES = ['0000', '0600', '1200', '1800']

ACE_STATUSES = ['TS', 'HU', 'SS']  # Tropical Storm, Hurricane, Subtropical Storm

MIN_NAMED_STORM_WIND = 34  # knots

MAX_STORMS_DISCORD = 10  # Maximum storms shown in Discord update before summarizing


# ===============================================================================
# BACKUP DATA (used when network is unavailable)
# ===============================================================================

BACKUP_DATA = {
    'atlantic': {
        'year': 2026,
        'storms': {},
        'yearly_totals': {
            2025: 130.8, 2024: 161.6, 2023: 146.0, 2022: 95.0, 2021: 145.0, 2020: 180.0,
            2019: 133.0, 2018: 136.4, 2017: 225.0, 2016: 155.0, 2015: 65.0,
            2014: 67.0, 2013: 36.0, 2012: 133.0, 2011: 126.0, 2010: 165.0,
            2009: 53.0, 2008: 146.0, 2007: 74.0, 2006: 79.0, 2005: 245.0,
            2004: 227.0, 2003: 176.0, 2002: 67.0, 2001: 106.0, 2000: 119.0,
            1999: 177.0, 1998: 182.0, 1997: 41.0, 1996: 166.0, 1995: 228.0,
            1994: 32.0, 1993: 39.0, 1992: 75.0, 1991: 34.0,
        }
    },
    'pacific': {
        'year': 2026,
        'storms': {},
        'yearly_totals': {
            2025: 127.3, 2024: 75.0, 2023: 117.0, 2022: 97.0, 2021: 86.0, 2020: 137.0,
            2019: 91.0, 2018: 316.0, 2017: 107.0, 2016: 156.0, 2015: 252.0,
            2014: 173.0, 2013: 83.0, 2012: 113.0, 2011: 60.0, 2010: 66.0,
            2009: 119.0, 2008: 85.0, 2007: 49.0, 2006: 155.0, 2005: 136.0,
            2004: 113.0, 2003: 61.0, 2002: 113.0, 2001: 83.0, 2000: 75.0,
            1999: 56.0, 1998: 187.0, 1997: 167.0, 1996: 97.0, 1995: 52.0,
            1994: 145.0, 1993: 79.0, 1992: 183.0, 1991: 79.0,
        }
    }
}



# ===============================================================================
# HELPER: Storm category from max wind (knots)
# ===============================================================================

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



# ===============================================================================
# LANDFALL GEOCODER
# ===============================================================================

_landfall_readers = None



def _build_landfall_geocoder():
    """Load Natural Earth shapefiles for offline reverse geocoding. Cached after first call."""
    global _landfall_readers
    if _landfall_readers is not None:
        return _landfall_readers
    try:
        import cartopy.io.shapereader as shpreader
        states_shp = shpreader.natural_earth(resolution='10m', category='cultural',
                                              name='admin_1_states_provinces')
        countries_shp = shpreader.natural_earth(resolution='10m', category='cultural',
                                                name='admin_0_countries')
        # Pre-store records with bounds for fast bounding-box pre-filtering
        states = [(rec, rec.geometry.bounds)
                  for rec in shpreader.Reader(states_shp).records() if rec.geometry]
        countries = [(rec, rec.geometry.bounds)
                     for rec in shpreader.Reader(countries_shp).records() if rec.geometry]
        _landfall_readers = (states, countries)
    except Exception as _e:
        logger.warning(f"Could not load landfall shapefiles: {_e}")
        _landfall_readers = ([], [])
    return _landfall_readers



def _reverse_geocode(lat, lon):
    """Convert a coastal lat/lon to a human-readable location name.

    Uses a ~0.5-degree buffer so HURDAT2 landfall points that sit exactly on
    the coastline are captured by the nearest land polygon.
    """
    states, countries = _build_landfall_geocoder()
    if not states and not countries:
        return None
    try:
        from shapely.geometry import Point
        pt = Point(lon, lat)
        buf = 0.5  # ~55 km — enough to catch coastal landfall coordinates
        blon0, blat0 = lon - buf, lat - buf
        blon1, blat1 = lon + buf, lat + buf
        buffered = pt.buffer(buf)

        # State/province level (more specific) — pre-filter by bounding box
        best_attr, best_dist = None, float('inf')
        for rec, (minx, miny, maxx, maxy) in states:
            if minx > blon1 or maxx < blon0 or miny > blat1 or maxy < blat0:
                continue
            if rec.geometry.intersects(buffered):
                d = rec.geometry.distance(pt)
                if d < best_dist:
                    best_dist = d
                    best_attr = rec.attributes

        if best_attr:
            name = best_attr.get('name', '')
            country = best_attr.get('admin', '')
            if country == 'United States of America':
                return name
            if name and country:
                return f'{name}, {country}'
            return country or name or None

        # Country level fallback
        for rec, (minx, miny, maxx, maxy) in countries:
            if minx > blon1 or maxx < blon0 or miny > blat1 or maxy < blat0:
                continue
            if rec.geometry.intersects(buffered):
                return rec.attributes.get('NAME', None)

        return None
    except Exception:
        return None



def _load_landfall_cache():
    """Load the persisted landfall cache from disk. Returns {} on any failure."""
    try:
        if os.path.exists(LANDFALL_CACHE_PATH):
            with open(LANDFALL_CACHE_PATH, 'r') as f:
                raw = json.load(f)
            # JSON stores lists; convert inner lists back to tuples
            return {k: [tuple(x) for x in v] for k, v in raw.items()}
    except Exception as e:
        logger.warning(f"Could not load landfall cache: {e}")
    return {}



def _save_landfall_cache(cache):
    """Persist the landfall cache to disk."""
    try:
        # Convert tuples to lists for JSON serialisation
        serialisable = {k: [list(x) for x in v] for k, v in cache.items()}
        with open(LANDFALL_CACHE_PATH, 'w') as f:
            json.dump(serialisable, f, separators=(',', ':'))
        logger.info(f"Saved landfall cache ({len(cache)} entries)")
    except Exception as e:
        logger.warning(f"Could not save landfall cache: {e}")



def get_landfall_locations(storm_obj):
    """Return a deduplicated list of (location, category_at_landfall) tuples.

    Reads HURDAT2 'L' markers from storm_obj.special. Returns an empty list
    for fish storms (no landfall). Category reflects the storm's intensity at
    the moment of landfall, not its peak intensity.
    """
    try:
        special = list(storm_obj.special)
        lats = list(storm_obj.lat)
        lons = list(storm_obj.lon)
        vmax = list(storm_obj.vmax)
        locations = []
        seen = set()
        for i, sp in enumerate(special):
            if sp == 'L' and i < len(lats) and i < len(lons):
                loc = _reverse_geocode(float(lats[i]), float(lons[i]))
                wind = int(vmax[i]) if i < len(vmax) else 0
                cat = get_category(wind)
                key = (loc, cat)
                if loc and key not in seen:
                    seen.add(key)
                    locations.append((loc, cat))
        return locations
    except Exception:
        return []



def _detect_landfall_from_track(storm_obj):
    """Geographic fallback for landfall detection when HURDAT2 'L' markers are absent.

    NHC best track (BTK) data used during the active season often lacks the 'L'
    landfall markers that are only added in the post-season HURDAT2 analysis.
    This function fills the gap by checking whether synoptic-time track points
    cross from water to land using exact point-in-polygon containment (no buffer)
    to avoid false positives for storms that pass close to but stay offshore.
    """
    try:
        from shapely.geometry import Point

        states, countries = _build_landfall_geocoder()
        if not states and not countries:
            return []

        lats  = list(storm_obj.lat)
        lons  = list(storm_obj.lon)
        vmax  = list(storm_obj.vmax)
        times = list(storm_obj.time)

        def land_at(lat, lon):
            """Return (kind, attributes) if the point is over land, else None."""
            pt = Point(lon, lat)
            m  = 0.2  # bounding-box margin for performance pre-filter only
            for rec, (minx, miny, maxx, maxy) in states:
                if minx > lon + m or maxx < lon - m or miny > lat + m or maxy < lat - m:
                    continue
                if rec.geometry.contains(pt):
                    return 'state', rec.attributes
            for rec, (minx, miny, maxx, maxy) in countries:
                if minx > lon + m or maxx < lon - m or miny > lat + m or maxy < lat - m:
                    continue
                if rec.geometry.contains(pt):
                    return 'country', rec.attributes
            return None

        def loc_name(kind, attrs):
            if kind == 'state':
                name    = attrs.get('name', '')
                country = attrs.get('admin', '')
                if country == 'United States of America':
                    return name
                return f'{name}, {country}' if name and country else country or name
            return attrs.get('NAME', '')

        locations = []
        seen      = set()
        prev_land = None   # None = track just started; False = was over water

        for i in range(len(lats)):
            t = times[i]
            if hasattr(t, 'hour') and t.hour not in (0, 6, 12, 18):
                continue

            result    = land_at(float(lats[i]), float(lons[i]))
            over_land = result is not None

            # Only flag the first synoptic point over land after confirmed water
            if over_land and prev_land is False:
                kind, attrs = result
                loc  = loc_name(kind, attrs)
                wind = int(vmax[i]) if i < len(vmax) else 0
                cat  = get_category(wind)
                key  = (loc, cat)
                if loc and key not in seen:
                    seen.add(key)
                    locations.append((loc, cat))

            prev_land = over_land

        return locations

    except Exception:
        return []



# ===============================================================================
# TROPYCAL DATA FETCHING
# ===============================================================================

def _tropycal_basin_name(basin_key):
    """Get Tropycal basin name from configuration."""
    return BASINS[basin_key]['tropycal_basin']



def _extract_synoptic_winds(storm_obj):
    """Extract synoptic-time wind readings from a Tropycal Storm object.

    Returns list of wind speeds at 6-hourly synoptic times (00/06/12/18 UTC)
    for times when storm status is TS/HU/SS and wind >= 34 kt.
    Extratropical (EX) and other non-tropical phases are excluded per NHC methodology.
    """
    wind_readings = []

    try:
        times = storm_obj.time
        winds = storm_obj.vmax
        types = storm_obj.type if hasattr(storm_obj, 'type') and len(storm_obj.type) > 0 else []

        for i, time in enumerate(times):
            if time.hour in [0, 6, 12, 18]:
                wind = winds[i]
                status = str(types[i]) if i < len(types) else 'TS'
                if wind >= MIN_NAMED_STORM_WIND and status in ACE_STATUSES:
                    wind_readings.append(int(wind))
    except Exception as e:
        logger.warning(f"Error extracting synoptic winds: {e}")

    return wind_readings



def parse_hurdat2(basin_key, dataset=None):
    """Fetch historical storm data using Tropycal TrackDataset.

    Replaces manual HURDAT2 parsing with Tropycal library.
    Accepts an optional pre-built `dataset` (shared with get_current_season)
    to avoid downloading and parsing the same basin data twice per run.
    Returns list of storm dicts matching the existing data structure.
    """
    tropycal_basin = _tropycal_basin_name(basin_key)

    try:
        if dataset is None:
            logger.info(f"Loading {tropycal_basin} data from Tropycal TrackDataset...")
            print(f"Loading historical data via Tropycal (basin: {tropycal_basin})...")
            dataset = tracks.TrackDataset(
                basin=tropycal_basin,
                source='hurdat',
                include_btk=True
            )

        storms = []

        # Load landfall cache once — avoids re-geocoding 1,200+ historical storms
        lf_cache = _load_landfall_cache()
        lf_cache_dirty = False

        # Iterate through all years from START_YEAR to current
        current_year = datetime.now().year
        for year in range(START_YEAR, current_year + 1):
            try:
                season = dataset.get_season(year)

                # Process each storm in the season
                for storm_id in season.dict.keys():
                    try:
                        storm_obj = dataset.get_storm(storm_id)

                        # Extract storm attributes
                        storm_name = storm_obj.name.title() if storm_obj.name else 'UNNAMED'
                        storm_year = storm_obj.year

                        # Max wind while tropical/subtropical only — extratropical peaks
                        # don't count toward NHC hurricane classification (e.g. a storm
                        # peaking at 70kt as EX is not counted as a hurricane).
                        tropical_types = {'TD', 'TS', 'HU', 'SS', 'SD'}
                        if hasattr(storm_obj, 'type') and len(storm_obj.type) > 0:
                            trop_winds = [v for v, t in zip(storm_obj.vmax, storm_obj.type)
                                          if str(t) in tropical_types]
                            max_wind = int(max(trop_winds)) if trop_winds else (
                                int(max(storm_obj.vmax)) if len(storm_obj.vmax) > 0 else 0)
                        else:
                            max_wind = int(max(storm_obj.vmax)) if len(storm_obj.vmax) > 0 else 0

                        # Get start and end dates
                        start_date = storm_obj.time[0] if len(storm_obj.time) > 0 else None
                        end_date = storm_obj.time[-1] if len(storm_obj.time) > 0 else None

                        # Convert pandas Timestamp to datetime if needed
                        if start_date and hasattr(start_date, 'to_pydatetime'):
                            start_date = start_date.to_pydatetime()
                        if end_date and hasattr(end_date, 'to_pydatetime'):
                            end_date = end_date.to_pydatetime()

                        # Extract synoptic-time wind readings for ACE calculation
                        wind_readings = _extract_synoptic_winds(storm_obj)

                        # Landfall: use cache for completed seasons, compute otherwise
                        cache_key = str(storm_id)
                        if cache_key in lf_cache:
                            landfall = lf_cache[cache_key]
                        else:
                            landfall = get_landfall_locations(storm_obj)
                            lf_cache[cache_key] = landfall
                            lf_cache_dirty = True

                        # Build storm record
                        storm_record = {
                            'id': storm_id,
                            'name': storm_name,
                            'year': storm_year,
                            'max_wind': max_wind,
                            'wind_readings': wind_readings,
                            'start_date': start_date,
                            'end_date': end_date,
                            'landfall': landfall,
                        }

                        # Finalize storm (calculates ACE, category, duration)
                        storms.append(finalize_storm(storm_record))

                    except Exception as e:
                        logger.warning(f"Error processing storm {storm_id}: {e}")
                        continue

            except Exception as e:
                # Season might not exist or have no data
                logger.debug(f"No data for {year}: {e}")
                continue

        logger.info(f"Successfully loaded {len(storms)} storms from Tropycal")
        print(f"  ✓ Loaded {len(storms)} storms from {START_YEAR}-present via Tropycal")
        if lf_cache_dirty:
            _save_landfall_cache(lf_cache)
            cached_pct = round(sum(1 for s in storms if str(s['id']) in lf_cache) / len(storms) * 100) if storms else 0
            print(f"  ✓ Landfall cache updated ({len(lf_cache)} entries, {cached_pct}% hit rate this run)")
        else:
            print(f"  ✓ Landfall cache: all {len(lf_cache)} entries served from cache (0 geocoding calls)")
        return storms

    except Exception as e:
        logger.error(f"Error loading Tropycal data: {e}")
        print(f"  ✗ Error loading Tropycal data: {e}")
        print(f"  → Using backup data (yearly totals only)")
        return None



# ===============================================================================
# CURRENT SEASON from Tropycal
# ===============================================================================

def get_current_season(basin_key, dataset=None):
    """Fetch current season data using Tropycal.

    Uses TrackDataset with include_btk=True to get the most recent season data
    including preliminary best track data from NHC. Accepts an optional
    pre-built `dataset` (shared with parse_hurdat2) to avoid downloading and
    parsing the same basin data twice per run.

    Returns dict with: year, storms (name->ACE), storm_details (name->{ace, max_wind}), total
    """
    basin = BASINS[basin_key]
    tropycal_basin = _tropycal_basin_name(basin_key)
    current_year = datetime.now().year
    today = datetime.now().date()
    if basin_key == 'atlantic':
        season_start = datetime(current_year, 6, 1).date()
    else:
        season_start = datetime(current_year, 5, 15).date()
    season_end = datetime(current_year, 11, 30).date()
    in_active_season = season_start <= today <= season_end
    years_to_try = [current_year] if in_active_season else [current_year, current_year - 1]

    try:
        if dataset is None:
            logger.info(f"Fetching current season data via Tropycal...")
            print(f"Fetching current season data via Tropycal...")
            dataset = tracks.TrackDataset(
                basin=tropycal_basin,
                source='hurdat',
                include_btk=True
            )

        # Load landfall cache for geo fallback results (keyed by storm_id + last track date)
        cs_lf_cache = _load_landfall_cache()
        cs_lf_dirty = False

        # During active season only try current year; off-season also checks prior year
        for year in years_to_try:
            try:
                season = dataset.get_season(year)

                if not season.dict or len(season.dict) == 0:
                    continue

                storms = {}
                storm_details = {}

                # Process each storm in the season
                for storm_id in season.dict.keys():
                    try:
                        storm_obj = dataset.get_storm(storm_id)

                        # Get storm name
                        storm_name = storm_obj.name.title() if storm_obj.name else 'UNNAMED'

                        # Skip unnamed storms and numbered systems
                        if storm_name.upper() == 'UNNAMED':
                            continue

                        # Get ACE directly from Tropycal (if available)
                        # Tropycal calculates ACE for us
                        storm_ace = storm_obj.ace if hasattr(storm_obj, 'ace') and storm_obj.ace else 0.0

                        # Max wind while tropical/subtropical only (same logic as primary path)
                        tropical_types = {'TD', 'TS', 'HU', 'SS', 'SD'}
                        if hasattr(storm_obj, 'type') and len(storm_obj.type) > 0:
                            trop_winds = [v for v, t in zip(storm_obj.vmax, storm_obj.type)
                                          if str(t) in tropical_types]
                            max_wind = int(max(trop_winds)) if trop_winds else (
                                int(max(storm_obj.vmax)) if len(storm_obj.vmax) > 0 else 0)
                        else:
                            max_wind = int(max(storm_obj.vmax)) if len(storm_obj.vmax) > 0 else 0

                        # Skip TDs that never reached named-storm strength (e.g. Tropycal "One", "Two")
                        if max_wind < MIN_NAMED_STORM_WIND:
                            continue

                        # Extract synoptic-time track points for map visualization
                        track_points = []
                        try:
                            t_times = storm_obj.time
                            t_lats = storm_obj.lat
                            t_lons = storm_obj.lon
                            t_winds = storm_obj.vmax
                            t_types = storm_obj.type if hasattr(storm_obj, 'type') and len(storm_obj.type) > 0 else []
                            for ti in range(len(t_times)):
                                t = t_times[ti]
                                if hasattr(t, 'hour') and t.hour in [0, 6, 12, 18]:
                                    track_points.append({
                                        'lat': round(float(t_lats[ti]), 1),
                                        'lon': round(float(t_lons[ti]), 1),
                                        'wind': int(t_winds[ti]),
                                        'status': str(t_types[ti]) if ti < len(t_types) else 'TS',
                                        'time': t.strftime('%-m/%-d %HZ') if hasattr(t, 'strftime') else str(t),
                                    })
                        except Exception as _te:
                            logger.warning(f"Could not extract track for {storm_name}: {_te}")

                        # Detect if storm is currently active (last point within 48h)
                        is_active = False
                        try:
                            last_t = storm_obj.time[-1]
                            if hasattr(last_t, 'to_pydatetime'):
                                last_t = last_t.to_pydatetime()
                            if last_t.tzinfo is None:
                                last_t = last_t.replace(tzinfo=timezone.utc)
                            is_active = (datetime.now(timezone.utc) - last_t).total_seconds() < 48 * 3600
                        except Exception:
                            pass

                        # Start date string
                        start_date_str = '—'
                        try:
                            st = storm_obj.time[0]
                            if hasattr(st, 'to_pydatetime'):
                                st = st.to_pydatetime()
                            start_date_str = st.strftime('%-m/%-d')
                        except Exception:
                            pass

                        # Landfall detection: try HURDAT2 'L' markers first.
                        # BTK data often lacks them, so fall back to geographic
                        # track analysis. Cache geo results keyed by storm_id +
                        # last track timestamp so stale entries auto-invalidate
                        # when new track data arrives for an active storm.
                        landfall = get_landfall_locations(storm_obj)
                        if not landfall:
                            try:
                                last_t   = storm_obj.time[-1]
                                last_str = last_t.strftime('%Y%m%d%H') if hasattr(last_t, 'strftime') else str(last_t)[:13]
                            except Exception:
                                last_str = 'unknown'
                            geo_key = f"geo:{storm_id}:{last_str}"
                            if geo_key in cs_lf_cache:
                                landfall = cs_lf_cache[geo_key]
                            else:
                                landfall = _detect_landfall_from_track(storm_obj)
                                cs_lf_cache[geo_key] = landfall
                                cs_lf_dirty = True

                        # Store storm data
                        storms[storm_name] = storm_ace
                        storm_details[storm_name] = {
                            'ace': storm_ace,
                            'max_wind': max_wind,
                            'track_points': track_points,
                            'is_active': is_active,
                            'start_date': start_date_str,
                            'landfall': landfall,
                        }

                    except Exception as e:
                        logger.warning(f"Error processing storm {storm_id}: {e}")
                        continue

                if storms:
                    total = round(sum(storms.values()), 4)
                    logger.info(f"Found {len(storms)} storms for {year} season (ACE: {total:.2f})")
                    print(f"  ✓ Found {len(storms)} storms for {year} season")
                    print(f"  ✓ Total ACE: {total:.2f}")
                    if cs_lf_dirty:
                        _save_landfall_cache(cs_lf_cache)

                    return {
                        'year': year,
                        'storms': storms,
                        'storm_details': storm_details,
                        'total': total,
                    }

            except Exception as e:
                logger.debug(f"No data for {year} season: {e}")
                continue

        # No named storms found
        if in_active_season:
            logger.info(f"No storms yet for {current_year} season")
            print(f"  ℹ No storms yet for {current_year} season — returning empty season")
            return {'year': current_year, 'storms': {}, 'storm_details': {}, 'total': 0.0}
        logger.info(f"No {current_year} storms found (likely off-season)")
        print(f"  ℹ No {current_year} storms found (likely off-season)")
        print(f"  → Using backup data...")
        return _backup_current(basin_key)

    except Exception as e:
        logger.error(f"Error fetching current season: {e}")
        print(f"  ✗ Error fetching current season via Tropycal: {e}")
        if in_active_season:
            print(f"  → Returning empty {current_year} season")
            return {'year': current_year, 'storms': {}, 'storm_details': {}, 'total': 0.0}
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
    """Build storm detail records from current season data (Tropycal or backup).
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



# ===============================================================================
# CALCULATE YEARLY TOTALS & STATISTICS
# ===============================================================================

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
                'storms_list': [],
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
        if storm['category'] != 'TD':
            s['storms_list'].append({
                'name': storm['name'],
                'ace': round(storm['ace'], 2),
                'category': storm['category'],
                'max_wind': storm['max_wind'],
                'landfall': storm.get('landfall', []),
            })

    for year in stats:
        stats[year]['ace'] = round(stats[year]['ace'], 2)
        stats[year]['storms_list'].sort(key=lambda x: x['ace'], reverse=True)
    return stats



def find_similar_seasons(target_ace, yearly_totals, exclude_year=None):
    """Find the 3 historical seasons with ACE closest to the target."""
    candidates = [(y, ace) for y, ace in yearly_totals.items() if y != exclude_year]
    candidates.sort(key=lambda x: abs(x[1] - target_ace))
    return candidates[:3]



def calculate_same_date_stats(historical_storms, basin_key, target_date=None):
    """Compute historical averages for counts and ACE as of the same calendar
    date across all completed seasons since START_YEAR.

    For each historical year, only storms that had formed by the equivalent
    day-of-season are counted. ACE is prorated for storms still active on
    that date (elapsed fraction of storm duration × total ACE).

    Returns a dict with avg_named, avg_hurricanes, avg_majors, avg_ace,
    yearly_ace (year→same-date ACE, for similar-season lookup),
    day_of_season, and date_label.  Returns None if no data is available.
    """
    if target_date is None:
        target_date = datetime.now()

    if basin_key == 'atlantic':
        ssm, ssd = 6, 1   # June 1
    else:
        ssm, ssd = 5, 15  # May 15

    target_season_start = datetime(target_date.year, ssm, ssd)
    day_of_season = max(0, (target_date - target_season_start).days)
    date_label = target_date.strftime('%b %-d')
    current_year = target_date.year

    # Group historical storms by year, excluding current season
    storms_by_year = {}
    for s in historical_storms:
        y = s['year']
        if y == current_year:
            continue
        storms_by_year.setdefault(y, []).append(s)

    if not storms_by_year:
        return None

    sd_named = {}
    sd_hurricanes = {}
    sd_majors = {}
    sd_ace = {}

    for year, yr_storms in storms_by_year.items():
        hist_cutoff = datetime(year, ssm, ssd) + timedelta(days=day_of_season)
        named = hurricanes = majors = 0
        ace = 0.0

        for s in yr_storms:
            start = s.get('start_date')
            end   = s.get('end_date')
            if start is None:
                continue
            # Strip timezone so comparisons work
            if getattr(start, 'tzinfo', None):
                start = start.replace(tzinfo=None)
            if end and getattr(end, 'tzinfo', None):
                end = end.replace(tzinfo=None)

            if start > hist_cutoff:
                continue  # Storm hadn't formed yet

            named += 1
            if s['max_wind'] >= 64:
                hurricanes += 1
            if s['max_wind'] >= 96:
                majors += 1

            # Prorate ACE for storms still active at the cutoff
            storm_ace = s.get('ace', 0.0)
            if end is None or end <= hist_cutoff:
                ace += storm_ace
            else:
                total_days = max(1, (end - start).days)
                elapsed    = max(0, (hist_cutoff - start).days)
                ace += storm_ace * min(1.0, elapsed / total_days)

        sd_named[year]     = named
        sd_hurricanes[year] = hurricanes
        sd_majors[year]    = majors
        sd_ace[year]       = round(ace, 2)

    n = len(storms_by_year)
    return {
        'avg_named':     round(sum(sd_named.values())     / n, 1),
        'avg_hurricanes': round(sum(sd_hurricanes.values()) / n, 1),
        'avg_majors':    round(sum(sd_majors.values())    / n, 1),
        'avg_ace':       round(sum(sd_ace.values())       / n, 2),
        'yearly_ace':    sd_ace,
        'day_of_season': day_of_season,
        'date_label':    date_label,
    }



# ===============================================================================
# GENERATE SEASON INSIGHTS
# ===============================================================================

def generate_insights(basin_key, current, yearly_totals, historical_storms, yearly_stats):
    """Generate interesting facts and insights for the dashboard and Discord."""
    basin = BASINS[basin_key]
    insights = []
    current_ace = current['total']
    current_year = current['year']
    storms = current['storms']

    # Compute same-date historical stats once — used by multiple insights below
    sd = calculate_same_date_stats(historical_storms or [], basin_key) if historical_storms else None

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
    # Use same-date ACE when active enough to be meaningful; fall back to full-season
    if sd and sd['avg_ace'] >= 0.5:
        similar = find_similar_seasons(current_ace, sd['yearly_ace'], exclude_year=current_year)
        similar_links = ", ".join(
            f'<a href="history.html#{basin_key}-yr-{y}" class="sim-link">{y}</a> ({ace:.1f})'
            for y, ace in similar
        )
        insights.append(f"📈 Most Similar Seasons (through {sd['date_label']}): {similar_links}")
    else:
        similar = find_similar_seasons(current_ace, yearly_totals, exclude_year=current_year)
        if similar:
            similar_links = ", ".join(
                f'<a href="history.html#{basin_key}-yr-{y}" class="sim-link">{y}</a> ({ace:.1f})'
                for y, ace in similar
            )
            label = f" (early season — full-season comparison)" if sd else ""
            insights.append(f"📈 Most Similar Seasons: {similar_links}{label}")

    # 4. Historical ranking — pace rank (same-date) + full-season rank
    all_years_full = list(yearly_totals.items()) + [(current_year, current_ace)]
    all_years_full.sort(key=lambda x: x[1], reverse=True)
    full_rank = next(i + 1 for i, (y, _) in enumerate(all_years_full) if y == current_year)
    total_seasons = len(all_years_full)

    if sd:
        sd_with_current = dict(sd['yearly_ace'])
        sd_with_current[current_year] = current_ace
        all_years_sd = sorted(sd_with_current.items(), key=lambda x: x[1], reverse=True)
        pace_rank = next(i + 1 for i, (y, _) in enumerate(all_years_sd) if y == current_year)
        pace_total = len(all_years_sd)
        insights.append(
            f"🏆 Pace rank through {sd['date_label']}: #{pace_rank} of {pace_total} seasons "
            f"| Full-season rank: #{full_rank} of {total_seasons} (season in progress)"
        )
    else:
        insights.append(f"🏆 Historical Rank: #{full_rank} of {total_seasons} seasons since {START_YEAR}")

    # 5. Comparison to normal
    normal = basin['normal_ace']
    pct_of_normal = (current_ace / normal * 100) if normal > 0 else 0
    above_below = "above" if current_ace > normal else "below"
    insights.append(f"📉 {pct_of_normal:.0f}% of normal ({above_below} the {normal:.1f} average)")

    # 6. Hurricanes and major hurricanes — same-date avg alongside full-season avg
    current_storms_detail = [s for s in historical_storms if s['year'] == current_year] if historical_storms else []
    if not current_storms_detail:
        current_storms_detail = build_current_storm_records(current)

    if current_storms_detail:
        major_count    = sum(1 for s in current_storms_detail if s['is_major'])
        hurricane_count = sum(1 for s in current_storms_detail if s['max_wind'] >= 64)
        avg_hurricanes_full = basin['avg_hurricanes']
        avg_major_full      = basin['avg_major_hurricanes']

        if sd:
            insights.append(
                f"🌀 Hurricanes: {hurricane_count} "
                f"| avg through {sd['date_label']}: {sd['avg_hurricanes']:.1f} "
                f"| full season avg: {avg_hurricanes_full}"
            )
            insights.append(
                f"⚡ Major Hurricanes: {major_count} "
                f"| avg through {sd['date_label']}: {sd['avg_majors']:.1f} "
                f"| full season avg: {avg_major_full}"
            )
        else:
            insights.append(f"🌀 Hurricanes: {hurricane_count} (season avg: {avg_hurricanes_full})")
            insights.append(f"⚡ Major Hurricanes: {major_count} (season avg: {avg_major_full})")

    # 7. % of ACE from top storm
    if storms and current_ace > 0:
        leader_name = max(storms, key=storms.get)
        leader_ace = storms[leader_name]
        leader_pct = leader_ace / current_ace * 100
        if leader_pct > 30:
            insights.append(f"💪 Top-heavy season: {leader_pct:.0f}% of all ACE from just {leader_name}")

    # 8. Named storms — same-date avg alongside full-season avg
    num_storms = len(storms)
    avg_storms_full = basin['avg_named_storms']
    if sd:
        insights.append(
            f"🌊 Named Storms: {num_storms} "
            f"| avg through {sd['date_label']}: {sd['avg_named']:.1f} "
            f"| full season avg: {avg_storms_full}"
        )
    else:
        insights.append(f"🌊 Named Storms: {num_storms} (season avg: {avg_storms_full})")

    # 9. Longest storm this season
    if historical_storms:
        hurdat_current = [s for s in historical_storms if s['year'] == current_year]
        if hurdat_current:
            longest = max(hurdat_current, key=lambda s: s['duration_days'])
            if longest['duration_days'] > 0:
                insights.append(f"⏱️ Longest Storm: {longest['name']} ({longest['duration_days']} days)")

    # 10. Compare to last year's final total
    last_year = current_year - 1
    if last_year in yearly_totals:
        last_year_total = yearly_totals[last_year]
        insights.append(f"📅 Last Year ({last_year}) Final Total: {last_year_total:.1f} ACE")

    # 11. All-time single-storm record comparison
    record = basin['all_time_single_storm_ace']
    if storms:
        leader_name = max(storms, key=storms.get)
        leader_ace = storms[leader_name]
        pct_of_record = leader_ace / record['ace'] * 100
        if pct_of_record > 50:
            insights.append(f"🎯 {leader_name} at {pct_of_record:.0f}% of all-time single-storm record ({record['name']}: {record['ace']})")

    return insights



# ===============================================================================
# GENERATE DISCORD UPDATE TEXT
# ===============================================================================

def generate_discord_text(basin_key, current, yearly_totals, insights):
    """Generate copy/paste ready Discord update text."""
    basin = BASINS[basin_key]
    current_year = current['year']
    current_ace = current['total']
    storms = current['storms']
    now = datetime.now(timezone.utc)

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



# ===============================================================================
# CONSOLE REPORT
# ===============================================================================

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



# ===============================================================================
# NHC LIVE DATA FETCHING
# ===============================================================================

def fetch_nhc_disturbances(basin_key):
    """Fetch NHC Tropical Weather Outlook and return disturbances with Medium/High formation chances.

    Parses the NHC TWO XML feed (updated every 6 hours). Returns a list of dicts:
      {area, desc, level_48h, pct_48h, level_7d, pct_7d, nhc_url, issued}
    Returns [] on any failure or when nothing notable is active.
    """
    import re
    import urllib.request
    import xml.etree.ElementTree as ET

    feed_urls = {
        'atlantic': 'https://www.nhc.noaa.gov/xml/TWOAT.xml',
        'pacific':  'https://www.nhc.noaa.gov/xml/TWOEP.xml',
    }
    nhc_links = {
        'atlantic': 'https://www.nhc.noaa.gov/gtwo.php?basin=atl&fdays=5',
        'pacific':  'https://www.nhc.noaa.gov/gtwo.php?basin=epac&fdays=5',
    }
    url = feed_urls.get(basin_key)
    if not url:
        return []

    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'ACETracker/1.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode('utf-8', errors='replace')

        root = ET.fromstring(raw)
        desc_el = root.find('.//item/description')
        pub_el  = root.find('.//item/pubDate')
        if desc_el is None or not desc_el.text:
            return []

        text   = desc_el.text
        issued = pub_el.text.strip() if pub_el is not None and pub_el.text else ''

        # Preserve any HTML line-break tags as newlines before stripping others
        text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</(?:p|div|li)[^>]*>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'&amp;', '&', text)
        text = re.sub(r'&[a-z]+;', ' ', text)
        # NWS text products use 2+ spaces as line separators when served as plain text
        text = re.sub(r' {2,}', '\n', text)
        text = re.sub(r'\n{3,}', '\n\n', text)

        disturbances = []

        # Trim NOAA product header — find where actual outlook content begins
        for marker in ('For the ', 'Tropical Weather Outlook'):
            pos = text.find(marker)
            if pos >= 0:
                text = text[pos:]
                break

        # Split into per-disturbance blocks.
        # Numbered outlooks (multiple disturbances) use "1. Area:" markers.
        # Single-disturbance outlooks have no numbering.
        if re.search(r'\n\s*\d+\.\s', text):
            blocks = re.split(r'\n\s*(?=\d+\.\s)', text)
        else:
            blocks = [text]

        # Lines that are NOAA boilerplate, not geographic descriptions
        _header_pat = re.compile(
            r'^(000|[A-Z]{4,}\d+|Tropical Weather Outlook|NWS National|Forecaster\b|For the\b)',
            re.IGNORECASE)

        for block_idx, block in enumerate(blocks, 1):
            m48 = re.search(
                r'\*?\s*formation chance through 48 hours[.\s]+(\w+)[.\s]+(?:near\s+)?(\d+)\s*percent',
                block, re.IGNORECASE)
            m7d = re.search(
                r'\*?\s*formation chance through 7 days[.\s]+(\w+)[.\s]+(?:near\s+)?(\d+)\s*percent',
                block, re.IGNORECASE)
            if not m48:
                continue

            level_48h = m48.group(1).upper()
            pct_48h   = int(m48.group(2))
            level_7d  = m7d.group(1).upper() if m7d else 'LOW'
            pct_7d    = int(m7d.group(2))    if m7d else 0

            # Only alert for Medium (≥40%) or High (≥70%) in either window
            if pct_48h < 40 and pct_7d < 40:
                continue

            # Collect content lines (skip boilerplate headers)
            content_lines = [
                l.strip() for l in block.split('\n')
                if l.strip() and not _header_pat.match(l.strip())
            ]

            # Area label: look for "Geographic Name: description..." pattern,
            # or fall back to the first clean non-boilerplate line
            area_line = ''
            desc_lines = []
            for ln in content_lines:
                if re.search(r'formation chance', ln, re.IGNORECASE):
                    break
                # "Location Name: rest of text" — split on first colon
                colon_match = re.match(r'^([\w ,\-]{4,60}):\s*(.*)$', ln)
                if colon_match and not area_line:
                    area_line = colon_match.group(1).strip()
                    rest = colon_match.group(2).strip()
                    if rest:
                        desc_lines.append(rest)
                else:
                    stripped = re.sub(r'^\d+\.\s*', '', ln).strip()
                    if stripped and not area_line and len(stripped) > 4:
                        area_line = stripped[:100]
                    elif stripped:
                        desc_lines.append(stripped)
            desc = ' '.join(desc_lines)[:280]

            disturbances.append({
                'area':      area_line,
                'desc':      desc,
                'level_48h': level_48h,
                'pct_48h':   pct_48h,
                'level_7d':  level_7d,
                'pct_7d':    pct_7d,
                'nhc_url':   nhc_links[basin_key],
                'issued':    issued,
            })

        return disturbances

    except Exception as e:
        logger.warning(f"Could not fetch NHC TWO for {basin_key}: {e}")
        return []



# ===============================================================================
# FORECAST CONE FETCHING (NHC)
# ===============================================================================

NHC_BIN_PREFIXES = {
    'atlantic': ('AL',),
    'pacific':  ('EP', 'CP'),
}


def fetch_active_storm_cones(basin_key, storm_details):
    """Fetch and locally cache NHC forecast cone images for currently active storms.

    Downloads each active storm's 5-day cone PNG from NHC once per run and saves it
    under data/cones/, so the dashboard serves the image from our own domain instead
    of hotlinking NHC's graphics server on every visitor request. The cone image
    filename embeds the forecast advisory's update time, which we read from
    CurrentStorms.json rather than guessing.

    Returns a dict of storm_name -> relative path (e.g. 'cones/ep042026.png'),
    or {} if nothing is active or the fetch fails.
    """
    import urllib.request

    active_names = {name.upper() for name, d in storm_details.items() if d.get('is_active')}
    if not active_names:
        return {}

    try:
        req = urllib.request.Request(
            'https://www.nhc.noaa.gov/CurrentStorms.json',
            headers={'User-Agent': 'ACETracker/1.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        logger.warning(f"Could not fetch CurrentStorms.json: {e}")
        return {}

    prefixes = NHC_BIN_PREFIXES.get(basin_key, ())
    cone_dir = os.path.join('data', 'cones')
    images = {}

    for storm in data.get('activeStorms', []):
        bin_number = storm.get('binNumber', '')
        if not bin_number.startswith(prefixes):
            continue
        name = (storm.get('name') or '').upper()
        if name not in active_names:
            continue

        storm_id = storm.get('id', '')
        update_time = (storm.get('forecastGraphics') or {}).get('fileUpdateTime')
        if not storm_id or not update_time:
            continue

        try:
            ts = datetime.fromisoformat(update_time.replace('Z', '+00:00'))
            time_code = ts.strftime('%d%H%M')
            bin4 = storm_id[:4].upper()
            atcf_id = storm_id.upper()
            url = (f'https://www.nhc.noaa.gov/storm_graphics/{bin4}/refresh/'
                   f'{atcf_id}_5day_cone+png/{time_code}_5day_cone.png')

            img_req = urllib.request.Request(url, headers={'User-Agent': 'ACETracker/1.0'})
            with urllib.request.urlopen(img_req, timeout=15) as resp:
                img_bytes = resp.read()

            os.makedirs(cone_dir, exist_ok=True)
            filename = f'{storm_id.lower()}.png'
            with open(os.path.join(cone_dir, filename), 'wb') as f:
                f.write(img_bytes)

            for orig_name in storm_details:
                if orig_name.upper() == name:
                    images[orig_name] = f'cones/{filename}'
                    break
        except Exception as e:
            logger.warning(f"Could not fetch cone image for {name}: {e}")
            continue

    return images



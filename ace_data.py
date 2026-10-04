"""
ace_data.py
===========
Data fetching, ACE calculation, and plain-text report generation for the
ACE Tracker. Fetches historical + current-season storm data via Tropycal,
computes Accumulated Cyclone Energy, and builds Discord/console report text.
"""

import os
import re
import json
import logging
import tempfile
import urllib.request
from datetime import datetime, timedelta, timezone
import tropycal.tracks as tracks
from tropycal.tracks.tools import find_latest_hurdat_files

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
    },
    'pacific': {
        'name': 'East & Central Pacific',
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
    }
}


START_YEAR = 1991

# ACE Calculation Constants

SYNOPTIC_TIMES = ['0000', '0600', '1200', '1800']

ACE_STATUSES = ['TS', 'HU', 'SS']  # Tropical Storm, Hurricane, Subtropical Storm

MIN_NAMED_STORM_WIND = 34  # knots

MAX_STORMS_DISCORD = 10  # Maximum storms shown in Discord update before summarizing

# Curated deterministic models for the spaghetti-plot overlay on active storms.
# Verified against get_operational_forecasts() output — the full model list runs
# to ~280 members/models, which would be unreadable clutter on the map.
SPAGHETTI_MODELS = ['AVNO', 'EMX', 'UKX', 'CMC', 'HWRF', 'HMON', 'NVGM', 'OFCL']

# A model whose latest run trails the newest run shown by more than this is
# dropped from the map. When a model stops running for a storm, Tropycal keeps
# returning its last run (HWRF/HMON for Fay 2026: Sep 21 runs on Sep 27),
# which would be drawn beside current guidance as if it were current.
SPAGHETTI_MAX_RUN_LAG_HOURS = 24


# ===============================================================================
# BACKUP DATA (used when network is unavailable)
# ===============================================================================

BACKUP_DATA = {
    'atlantic': {
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



def get_season_projection(current_ace, basin_key, as_of_date=None):
    """Compute the daily ACE rate needed for the rest of the season to reach
    each not-yet-reached NOAA classification threshold by season end (Nov 30).

    Returns a list of {'label', 'threshold', 'daily_rate'} dicts, ordered from
    nearest to farthest threshold. Empty if the season has already ended or
    every threshold has already been reached.
    """
    if as_of_date is None:
        as_of_date = _utc_now().date()
    season_end = datetime(as_of_date.year, 11, 30).date()
    days_remaining = (season_end - as_of_date).days
    if days_remaining <= 0:
        return []

    thresholds = BASINS[basin_key]['noaa_thresholds']
    milestones = [
        ('Near Normal', thresholds['below_normal']),
        ('Above Normal', thresholds['near_normal_upper']),
        ('Extremely Active', thresholds['above_normal_upper']),
    ]
    projection = []
    for label, threshold in milestones:
        if current_ace >= threshold:
            continue
        projection.append({
            'label': label,
            'threshold': threshold,
            'daily_rate': round((threshold - current_ace) / days_remaining, 2),
        })
    return projection



def ace_from_winds(wind_readings):
    """ACE from synoptic-time wind readings: Σ(V²max) × 10⁻⁴.

    Single source of truth for the ACE formula — used for both historical
    storms (finalize_storm) and the current season, so the dashboard and
    history page can never disagree about the same storm.
    """
    return round(sum(w * w for w in wind_readings) / 10000.0, 4)



def finalize_storm(storm):
    storm['ace'] = ace_from_winds(storm['wind_readings'])
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
    except Exception as e:
        logger.warning(f"Could not reverse-geocode ({lat}, {lon}): {e}")
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



def _last_track_stamp(storm_obj):
    """Timestamp string of a storm's last track point.

    Used in cache keys that must auto-invalidate when a new advisory adds
    track data to an in-progress storm."""
    try:
        last_t = storm_obj.time[-1]
        return last_t.strftime('%Y%m%d%H') if hasattr(last_t, 'strftime') else str(last_t)[:13]
    except Exception:
        return 'unknown'



def _track_datetime(t):
    """A Tropycal track time as a naive UTC datetime, or None if unreadable."""
    try:
        if hasattr(t, 'to_pydatetime'):
            t = t.to_pydatetime()
        if not isinstance(t, datetime):
            return None
        if t.tzinfo is not None:
            t = t.astimezone(timezone.utc).replace(tzinfo=None)
        return t
    except Exception:
        return None


def latest_track_time(storm_objs):
    """The newest best-track point across `storm_objs`, as an ISO-8601 UTC
    string ('2026-09-27T00:00:00Z'), or None. This is how current the
    season's data really is, which can lag the page build by hours."""
    latest = None
    for storm_obj in storm_objs:
        try:
            t = _track_datetime(storm_obj.time[-1])
        except Exception:
            t = None
        if t and (latest is None or t > latest):
            latest = t
    return latest.strftime('%Y-%m-%dT%H:%M:%SZ') if latest else None



def _drop_stale_storm_keys(cache, storm_id, keep_key, prefix):
    """Remove outdated cache entries for one in-progress storm, scoped to one
    key family (`cur` or `geo`): the legacy bare-id key plus any
    `{prefix}:{id}:{timestamp}` keys other than `keep_key`. The two families
    cache different computations, so pruning never crosses between them.
    Returns True if anything was removed."""
    sid = str(storm_id)
    stale = [k for k in cache
             if k != keep_key and (k == sid or k.startswith(f"{prefix}:{sid}:"))]
    for k in stale:
        del cache[k]
    return bool(stale)



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
    except Exception as e:
        logger.warning(f"Could not read HURDAT2 landfall markers for {getattr(storm_obj, 'id', '?')}: {e}")
        return []



def _clean_landfalls(landfall):
    """Tidy a landfall list for display: collapse 'X, X' names where the
    region and country share a name (e.g. 'Puerto Rico, Puerto Rico'), and
    list each place once at the strongest category it was hit, keeping the
    order of first landfall. Also applied to cached entries, which predate it.
    """
    order = []
    best = {}
    for loc, cat in landfall or []:
        region, sep, country = loc.partition(', ')
        if sep and region == country:
            loc = region
        if loc not in best:
            order.append(loc)
            best[loc] = cat
        elif _CATEGORY_RANK.get(cat, -1) > _CATEGORY_RANK.get(best[loc], -1):
            best[loc] = cat
    return [(loc, best[loc]) for loc in order]



def _first_track_time(storm_obj, statuses, min_wind=0):
    """First track time with a status in `statuses` and wind >= `min_wind`
    (knots), or None if the track never gets there."""
    try:
        for t, status, wind in zip(storm_obj.time, storm_obj.type, storm_obj.vmax):
            if str(status) in statuses and wind >= min_wind:
                return t.to_pydatetime() if hasattr(t, 'to_pydatetime') else t
    except Exception as e:
        logger.warning(f"Could not read track times for {getattr(storm_obj, 'id', '?')}: {e}")
    return None


def _first_tropical_storm_time(storm_obj):
    """When a system first became a tropical or subtropical storm: its first
    track point with TS/HU/SS status. HURDAT2 tracks often begin days earlier
    as a low, depression, or extratropical system (Alex 2016's track starts
    Jan 7 as extratropical; it became a subtropical storm Jan 12). None for
    a depression that never strengthened.
    """
    return _first_track_time(storm_obj, ACE_STATUSES)



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

    except Exception as e:
        logger.warning(f"Could not detect landfall from track for {getattr(storm_obj, 'id', '?')}: {e}")
        return []



# ===============================================================================
# TROPYCAL DATA FETCHING
# ===============================================================================

def _tropycal_basin_name(basin_key):
    """Get Tropycal basin name from configuration."""
    return BASINS[basin_key]['tropycal_basin']



def _utc_now():
    """Current UTC time as a naive datetime.

    Storm timestamps from Tropycal are UTC but tz-naive, so this stays naive
    too (safe to subtract/compare against them and against other naive
    `datetime(y, m, d)` values) while still reflecting UTC wall-clock time —
    plain `datetime.now()` uses local server time, which causes off-by-one-day
    season-boundary bugs when run outside UTC (GitHub Actions runners happen
    to default to UTC, which is why this was never caught in CI).
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)



def _portable_strftime(dt, fmt):
    """strftime wrapper supporting %-m/%-d (no leading zero) portably.

    The %-m/%-d modifiers are glibc-specific (work on Linux/macOS, not
    guaranteed elsewhere), so build those fields manually instead.
    """
    fmt = fmt.replace('%-m', str(dt.month)).replace('%-d', str(dt.day))
    return dt.strftime(fmt)



def _drop_malformed_hurdat_rows(raw):
    """Split HURDAT2 text into the lines to keep and the storm IDs of any
    data rows dropped because their lat/lon fields aren't parseable (one ID
    per dropped row)."""
    dropped = []
    kept_lines = []
    storm_id = '?'
    for line in raw.splitlines():
        tokens = line.replace(' ', '').split(',')
        is_header = bool(tokens[0]) and tokens[0][0] in ('A', 'C', 'E')
        if is_header:
            storm_id = tokens[0]
        elif len(tokens) >= 6:
            lat, lon = tokens[4], tokens[5]
            lat_ok = ('N' in lat) or ('S' in lat)
            lon_ok = ('W' in lon) or ('E' in lon)
            if not (lat_ok and lon_ok):
                dropped.append(storm_id)
                continue
        kept_lines.append(line)
    return kept_lines, dropped


def _sanitize_hurdat_file(url):
    """Download a HURDAT2 master file and drop any data row whose lat/lon
    fields aren't cleanly parseable, returning a local file path.

    NOAA's master HURDAT2 file has shipped with malformed rows before (e.g.
    a merged lat+lon field for AL211969 in the Sept 2026 revision) that crash
    Tropycal's parser outright and take down the *entire* basin's data, not
    just the one bad storm. Dropping a handful of bad synoptic observations
    from a decades-old storm costs nothing; a crashed parser costs the whole
    dashboard. Raises on download failure so the caller can fall back to
    Tropycal's own 'fetch' path.
    """
    with urllib.request.urlopen(url, timeout=30) as resp:
        raw = resp.read().decode('utf-8', errors='replace')

    kept_lines, dropped = _drop_malformed_hurdat_rows(raw)
    if dropped:
        storm_ids = sorted(set(dropped))
        in_range = [sid for sid in storm_ids if sid[-4:].isdigit() and int(sid[-4:]) >= START_YEAR]
        impact = (f"affects {', '.join(in_range)}" if in_range
                  else f"all before {START_YEAR}, so no effect on this site's data")
        logger.warning(
            f"Dropped {len(dropped)} malformed row(s) with unparseable lat/lon "
            f"fields from HURDAT2 file ({url}): {', '.join(storm_ids)} ({impact})")

    fd, path = tempfile.mkstemp(prefix='hurdat2_sanitized_', suffix='.txt')
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write('\n'.join(kept_lines))
    return path



def _build_track_dataset(basin_key):
    """Build a Tropycal TrackDataset, pre-sanitizing the raw HURDAT2 file so
    a single malformed upstream row can't crash the parser for the whole
    basin (see _sanitize_hurdat_file). Falls back to Tropycal's own 'fetch'
    if the pre-sanitize step itself fails for any reason (e.g. network
    hiccup), preserving prior behavior.
    """
    tropycal_basin = _tropycal_basin_name(basin_key)
    url_kwargs = {}
    try:
        atl_url, pac_url = find_latest_hurdat_files()
        if tropycal_basin == 'north_atlantic':
            url_kwargs['atlantic_url'] = _sanitize_hurdat_file(atl_url)
        elif tropycal_basin == 'east_pacific':
            url_kwargs['pacific_url'] = _sanitize_hurdat_file(pac_url)
    except Exception as e:
        logger.warning(
            f"Could not pre-sanitize HURDAT2 file for {basin_key}, "
            f"falling back to Tropycal's own fetch: {e}")
        url_kwargs = {}

    return tracks.TrackDataset(
        basin=tropycal_basin,
        source='hurdat',
        include_btk=True,
        **url_kwargs,
    )



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
            dataset = _build_track_dataset(basin_key)

        storms = []

        # Load landfall cache once — avoids re-geocoding 1,200+ historical storms
        lf_cache = _load_landfall_cache()
        lf_cache_dirty = False

        # Iterate through all years from START_YEAR to current
        current_year = _utc_now().year
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

                        # Landfall: completed seasons cache by bare id (track data
                        # is immutable after post-season reanalysis). Current-season
                        # storms key by id + last track time so each new advisory
                        # invalidates the entry instead of serving stale landfalls.
                        if storm_year < current_year:
                            cache_key = str(storm_id)
                        else:
                            cache_key = f"cur:{storm_id}:{_last_track_stamp(storm_obj)}"
                            if _drop_stale_storm_keys(lf_cache, storm_id, cache_key, 'cur'):
                                lf_cache_dirty = True
                        if cache_key in lf_cache:
                            landfall = lf_cache[cache_key]
                        else:
                            landfall = get_landfall_locations(storm_obj)
                            lf_cache[cache_key] = landfall
                            lf_cache_dirty = True
                        landfall = _clean_landfalls(landfall)

                        # Build storm record
                        storm_record = {
                            'id': storm_id,
                            'name': storm_name,
                            'year': storm_year,
                            'max_wind': max_wind,
                            'wind_readings': wind_readings,
                            'start_date': start_date,
                            'end_date': end_date,
                            'formation_date': _first_tropical_storm_time(storm_obj),
                            'hurricane_date': _first_track_time(storm_obj, {'HU'}, 64),
                            'major_date': _first_track_time(storm_obj, {'HU'}, 96),
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
            _timestamped = {k.rsplit(':', 1)[0] + ':' for k in lf_cache if k.startswith('cur:')}
            cached_pct = round(sum(1 for s in storms
                                   if str(s['id']) in lf_cache or f"cur:{s['id']}:" in _timestamped)
                               / len(storms) * 100) if storms else 0
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

def _forecast_cycle_iso(cycle_key, fc):
    """A forecast's initialization time as 'YYYY-MM-DDTHH:00:00Z', from its
    'init' datetime or else its 'YYYYMMDDHH' cycle key; None if neither parses."""
    init = fc.get('init') if isinstance(fc, dict) else None
    if not isinstance(init, datetime):
        try:
            init = datetime.strptime(str(cycle_key), '%Y%m%d%H')
        except ValueError:
            return None
    return init.strftime('%Y-%m-%dT%H:00:00Z')


def _extract_spaghetti_tracks(storm_obj):
    """Latest-cycle forecast track per curated model, for the active-storm map overlay.

    Returns ({model_id: [{'lat', 'lon'}, ...]}, {model_id: cycle_iso}),
    omitting models that are absent or return no forward-looking (fhr >= 0)
    points for this storm/cycle — ICON was observed doing this during testing.
    The cycle time is shown with each track so old guidance is visibly old,
    and a model whose run is more than SPAGHETTI_MAX_RUN_LAG_HOURS older than
    the newest one is left out.
    """
    tracks_by_model = {}
    cycles_by_model = {}
    try:
        forecasts = storm_obj.get_operational_forecasts()
    except Exception as e:
        logger.debug(f"Could not fetch operational forecasts: {e}")
        return tracks_by_model, cycles_by_model

    for model in SPAGHETTI_MODELS:
        cycles = forecasts.get(model)
        if not cycles:
            continue
        try:
            latest_cycle = max(cycles.keys())
            fc = cycles[latest_cycle]
            lats, lons, fhrs = fc.get('lat', []), fc.get('lon', []), fc.get('fhr', [])
            points = [
                {'lat': round(float(lats[i]), 1), 'lon': round(float(lons[i]), 1)}
                for i in range(len(lats))
                if i < len(fhrs) and fhrs[i] >= 0
            ]
            if points:
                tracks_by_model[model] = points
                cycle = _forecast_cycle_iso(latest_cycle, fc)
                if cycle:
                    cycles_by_model[model] = cycle
        except Exception as e:
            logger.debug(f"Could not parse {model} forecast: {e}")
            continue

    if cycles_by_model:
        newest = max(datetime.strptime(c, '%Y-%m-%dT%H:%M:%SZ') for c in cycles_by_model.values())
        cutoff = newest - timedelta(hours=SPAGHETTI_MAX_RUN_LAG_HOURS)
        for model, cycle in list(cycles_by_model.items()):
            if datetime.strptime(cycle, '%Y-%m-%dT%H:%M:%SZ') < cutoff:
                logger.info(f"Dropping stale {model} run {cycle} (newest run {newest:%Y-%m-%d %HZ})")
                del cycles_by_model[model]
                del tracks_by_model[model]

    return tracks_by_model, cycles_by_model


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
    current_year = _utc_now().year
    today = _utc_now().date()
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
            dataset = _build_track_dataset(basin_key)

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
                season_storm_objs = []

                # Process each storm in the season
                for storm_id in season.dict.keys():
                    try:
                        storm_obj = dataset.get_storm(storm_id)
                        season_storm_objs.append(storm_obj)

                        # Get storm name
                        storm_name = storm_obj.name.title() if storm_obj.name else 'UNNAMED'

                        # Skip unnamed storms and numbered systems
                        if storm_name.upper() == 'UNNAMED':
                            continue

                        # ACE via our own synoptic-time method (same as the
                        # historical path) so the dashboard and history page
                        # always agree. Tropycal's value is a cross-check only.
                        storm_ace = ace_from_winds(_extract_synoptic_winds(storm_obj))
                        tropycal_ace = storm_obj.ace if hasattr(storm_obj, 'ace') and storm_obj.ace else 0.0
                        if tropycal_ace and abs(storm_ace - tropycal_ace) > 0.25:
                            logger.warning(
                                f"ACE cross-check mismatch for {storm_id}: "
                                f"computed {storm_ace:.2f} vs Tropycal {tropycal_ace:.2f}")

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
                                        'time': _portable_strftime(t, '%-m/%-d %HZ') if hasattr(t, 'strftime') else str(t),
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
                            start_date_str = _portable_strftime(st, '%-m/%-d')
                        except Exception:
                            pass

                        # Landfall detection: try HURDAT2 'L' markers first.
                        # BTK data often lacks them, so fall back to geographic
                        # track analysis. Cache geo results keyed by storm_id +
                        # last track timestamp so stale entries auto-invalidate
                        # when new track data arrives for an active storm.
                        landfall = get_landfall_locations(storm_obj)
                        landfall_estimated = not landfall
                        if not landfall:
                            geo_key = f"geo:{storm_id}:{_last_track_stamp(storm_obj)}"
                            if _drop_stale_storm_keys(cs_lf_cache, storm_id, geo_key, 'geo'):
                                cs_lf_dirty = True
                            if geo_key in cs_lf_cache:
                                landfall = cs_lf_cache[geo_key]
                            else:
                                landfall = _detect_landfall_from_track(storm_obj)
                                cs_lf_cache[geo_key] = landfall
                                cs_lf_dirty = True
                        landfall = _clean_landfalls(landfall)

                        # Spaghetti model tracks only matter (and are only
                        # worth the extra Tropycal call) while a storm is active.
                        spaghetti, spaghetti_cycles = (
                            _extract_spaghetti_tracks(storm_obj) if is_active else ({}, {}))

                        # Store storm data
                        storms[storm_name] = storm_ace
                        storm_details[storm_name] = {
                            'ace': storm_ace,
                            'max_wind': max_wind,
                            'track_points': track_points,
                            'is_active': is_active,
                            'start_date': start_date_str,
                            'landfall': landfall,
                            'landfall_estimated': landfall_estimated and bool(landfall),
                            'spaghetti': spaghetti,
                            'spaghetti_cycles': spaghetti_cycles,
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
                        'data_as_of': latest_track_time(season_storm_objs),
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
    """Fallback when Tropycal is unavailable/off-season. Yields the *real*
    current year (not a hardcoded one, which would go stale every January —
    see #98) with zero storms, plus an 'is_backup' flag so the dashboard can
    show a visible staleness banner instead of presenting this silently as
    live data.
    """
    backup = BACKUP_DATA[basin_key]
    storms = backup['storms']
    total = round(sum(storms.values()), 4)
    # Build storm_details from backup (no max_wind available)
    detail = {name: {'ace': ace, 'max_wind': 0} for name, ace in storms.items()}
    year = _utc_now().year
    print(f"  ⚠ Using backup data for {year} season ({len(storms)} storms, ACE={total:.2f})")
    return {'year': year, 'storms': storms, 'storm_details': detail, 'total': total, 'is_backup': True}



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



def rank_current_season(yearly_totals, current_year, current_ace):
    """Rank the in-progress season against history without double-counting.

    `yearly_totals` already contains the current year (parse_hurdat2 loads
    storms through the present), so the live total must OVERRIDE that entry
    rather than be appended alongside it — appending duplicates the year,
    inflates the season count by one, and can report the wrong rank.

    Returns (rank, total_seasons).
    """
    merged = {**yearly_totals, current_year: current_ace}
    ordered = sorted(merged.items(), key=lambda x: x[1], reverse=True)
    rank = next(i + 1 for i, (y, _) in enumerate(ordered) if y == current_year)
    return rank, len(ordered)



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
        if storm['category'] != 'TD':
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
                'id': storm.get('id'),
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



def made_ts_landfall(landfall):
    """True if any (location, category) landfall entry is at tropical-storm
    strength or stronger. A system that only crossed land as a depression
    does not count as a landfalling storm."""
    return any(entry[1] != 'TD' for entry in landfall or [] if len(entry) > 1)


def depression_only_landfalls(storms):
    """Named storms whose only landfalls were at depression strength: shown
    with a landfall in the storm table, but counted as fish storms in the
    landfall share. Explaining them keeps the two from looking contradictory."""
    return [s for s in storms
            if s.get('max_wind', 0) >= MIN_NAMED_STORM_WIND and s.get('landfall')
            and not made_ts_landfall(s.get('landfall'))]


def _depression_landfall_note(storms):
    """', including Boris, which reached Guerrero, Mexico only as a
    depression' (or several), or '' when there are none."""
    items = [f"{s.get('name', 'one storm')} ({s['landfall'][0][0]})" for s in depression_only_landfalls(storms)]
    if not items:
        return ''
    if len(items) == 1:
        name, place = items[0].rsplit(' (', 1)
        return f", including {name}, which reached {place[:-1]} only as a depression"
    return f", including {', '.join(items[:-1])} and {items[-1]}, which reached land only as depressions"


def landfall_ace_share(storms):
    """How a season's ACE splits between storms that made landfall at
    tropical-storm strength or stronger and "fish storms" (including storms
    that only crossed land as depressions). `storms` are dicts with 'ace',
    'max_wind' and 'landfall' (a list of (location, category); empty means
    no landfall).

    Returns {'landfall_pct', 'fish_pct', 'landfall_count', 'fish_count'},
    or None when the storms produced no ACE.
    """
    named = [s for s in storms if s.get('max_wind', 0) >= MIN_NAMED_STORM_WIND]
    total = sum(s.get('ace', 0.0) for s in named)
    if total <= 0:
        return None
    landfalling = [s for s in named if made_ts_landfall(s.get('landfall'))]
    landfall_pct = round(sum(s.get('ace', 0.0) for s in landfalling) / total * 100)
    return {
        'landfall_pct': landfall_pct,
        'fish_pct': 100 - landfall_pct,
        'landfall_count': len(landfalling),
        'fish_count': len(named) - len(landfalling),
    }


def average_landfall_share(yearly_stats, before_year):
    """Mean landfall share of ACE (percent) across completed seasons
    before `before_year`, or None without data."""
    shares = [landfall_ace_share(st.get('storms_list', []))
              for y, st in (yearly_stats or {}).items() if y < before_year]
    shares = [s['landfall_pct'] for s in shares if s]
    return round(sum(shares) / len(shares)) if shares else None



def find_similar_seasons(target_ace, yearly_totals, exclude_year=None):
    """Find the 3 historical seasons with ACE closest to the target."""
    candidates = [(y, ace) for y, ace in yearly_totals.items() if y != exclude_year]
    candidates.sort(key=lambda x: abs(x[1] - target_ace))
    return candidates[:3]



def find_highest_ace_storm(historical_storms):
    """The single storm with the highest ACE since START_YEAR.

    Computed dynamically from already-loaded data rather than a hardcoded
    reference value — a hardcoded "all-time" constant is exactly what went
    stale for the Pacific basin (see #117). Returns None if no data.
    """
    if not historical_storms:
        return None
    return max(historical_storms, key=lambda s: s['ace'])



def find_longest_lived_storm(historical_storms):
    """The storm with the longest duration since START_YEAR. None if no
    storm has duration data (e.g. missing start/end dates)."""
    dated = [s for s in historical_storms if s.get('duration_days', 0) > 0]
    if not dated:
        return None
    return max(dated, key=lambda s: s['duration_days'])



# Saffir-Simpson-plus-TS/TD ordering, for ranking landfall intensity strings
# produced by get_category().
_CATEGORY_RANK = {'TD': 0, 'TS': 1, 'Cat 1': 2, 'Cat 2': 3, 'Cat 3': 4, 'Cat 4': 5, 'Cat 5': 6}


def find_strongest_landfall(historical_storms):
    """The highest-category storm landfall since START_YEAR.

    Ties (e.g. multiple Cat 5 landfalls across different storms/years) are
    common, so this reports a `tied_count` of how many other landfalls
    share the top category rather than silently picking one arbitrarily.
    Returns None if no storm has landfall data.
    """
    hits = [(storm, loc, cat) for storm in historical_storms
            for loc, cat in storm.get('landfall', [])]
    if not hits:
        return None
    best_rank = max(_CATEGORY_RANK.get(cat, -1) for _, _, cat in hits)
    best_hits = [h for h in hits if _CATEGORY_RANK.get(h[2], -1) == best_rank]
    storm, loc, cat = best_hits[0]
    return {
        'name': storm['name'], 'year': storm['year'],
        'location': loc, 'category': cat,
        'tied_count': len(best_hits) - 1,
    }



def _formed_named_storms(historical_storms):
    """Named storms with a known formation date (first TS/SS/HU point).
    Depressions that never strengthened and unnamed storms are left out, so
    the forming records only ever name a real named storm."""
    return [s for s in historical_storms
            if s.get('formation_date') and s.get('name', '').upper() != 'UNNAMED']


def find_earliest_forming_storm(historical_storms):
    """The named storm that formed earliest in the calendar year since
    START_YEAR (e.g. a rare January/February formation), ranked by
    day-of-year rather than day-into-season so pre-season storms compare
    correctly. None if no storm has a formation date."""
    formed = _formed_named_storms(historical_storms)
    if not formed:
        return None
    return min(formed, key=lambda s: s['formation_date'].timetuple().tm_yday)



def find_latest_forming_storm(historical_storms):
    """The named storm that formed latest in the calendar year since
    START_YEAR (e.g. a rare December formation). None if no storm has a
    formation date."""
    formed = _formed_named_storms(historical_storms)
    if not formed:
        return None
    return max(formed, key=lambda s: s['formation_date'].timetuple().tm_yday)



def find_storms_on_this_day(historical_storms, target_date=None):
    """Historical storms whose active track (start_date through end_date)
    covered target_date's calendar month/day in a past year.

    Excludes target_date's own year — that season is shown separately on
    the dashboard, not as a "history" fact. Sorted by ACE, strongest first.
    """
    if target_date is None:
        target_date = _utc_now()
    current_year = target_date.year

    matches = []
    for storm in historical_storms:
        if storm['year'] == current_year:
            continue
        start = storm.get('start_date')
        end = storm.get('end_date')
        if not start or not end:
            continue
        d = start
        while d.date() <= end.date():
            if d.month == target_date.month and d.day == target_date.day:
                matches.append(storm)
                break
            d += timedelta(days=1)

    matches.sort(key=lambda s: s['ace'], reverse=True)
    return matches



def _storm_ace_at_cutoff(storm, cutoff):
    """ACE a storm had contributed as of `cutoff` (a naive datetime).

    0.0 if the storm hadn't formed yet by `cutoff`; the storm's full ACE if
    it had already ended by `cutoff`; otherwise a linear proration by
    elapsed/total days. Shared by calculate_same_date_stats (one date, many
    years) and calculate_ace_pace (many dates, few years) so both features
    can never independently drift on the same number.
    """
    start = storm.get('start_date')
    end = storm.get('end_date')
    if start is None:
        return 0.0
    if getattr(start, 'tzinfo', None):
        start = start.replace(tzinfo=None)
    if end and getattr(end, 'tzinfo', None):
        end = end.replace(tzinfo=None)
    if start > cutoff:
        return 0.0
    storm_ace = storm.get('ace', 0.0)
    if end is None or end <= cutoff:
        return storm_ace
    total_days = max(1, (end - start).days)
    elapsed = max(0, (cutoff - start).days)
    return storm_ace * min(1.0, elapsed / total_days)


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
        target_date = _utc_now()

    if basin_key == 'atlantic':
        ssm, ssd = 6, 1   # June 1
    else:
        ssm, ssd = 5, 15  # May 15

    target_season_start = datetime(target_date.year, ssm, ssd)
    day_of_season = max(0, (target_date - target_season_start).days)
    date_label = _portable_strftime(target_date, '%b %-d')
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
            # ACE accrues from the track start (only TS/HU/SS readings carry
            # any), but a storm only counts as named once it has formed.
            ace += _storm_ace_at_cutoff(s, hist_cutoff)

            formed = s.get('formation_date', s.get('start_date'))
            if formed is None or s.get('category') == 'TD':
                continue
            # Strip timezone so comparisons work
            if getattr(formed, 'tzinfo', None):
                formed = formed.replace(tzinfo=None)

            if formed > hist_cutoff:
                continue  # Storm hadn't formed yet

            named += 1
            if s['max_wind'] >= 64:
                hurricanes += 1
            if s['max_wind'] >= 96:
                majors += 1

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


# How close (days) the current date must be to a "latest first hurricane /
# major" record before the records-in-play panel mentions it.
RECORD_WATCH_DAYS = 14
# Fastest-to-100-ACE only shows up once a season is at least this far along.
FAST_100_MIN_ACE = 60


def _calendar_key(dt):
    """(month, day, hour) — compares dates across years without leap-year
    day-of-year drift."""
    return (dt.month, dt.day, dt.hour)


def _names_and_years(entries):
    """'Gustav (2002) and Humberto (2013)' from [(year, name), ...]."""
    parts = [f"{name.title()} ({year})" for year, name in sorted(entries)]
    return ' and '.join(parts) if len(parts) < 3 else ', '.join(parts[:-1]) + f', and {parts[-1]}'


def _date_reached_ace(storms, year, threshold):
    """First date in `year` when the season's cumulative ACE reached
    `threshold`, using the same proration as the same-date stats; None if
    it never did."""
    ends = [s['end_date'] for s in storms if s.get('end_date')]
    if not ends or sum(s.get('ace', 0.0) for s in storms) < threshold:
        return None
    day = datetime(year, 1, 1)
    last = max(e.replace(tzinfo=None) for e in ends)
    while day <= last:
        if sum(_storm_ace_at_cutoff(s, day) for s in storms) >= threshold:
            return day
        day += timedelta(days=1)
    return last


def _first_event_records(storms_by_year, current_storms, field, label, today, current_year):
    """Latest-first-hurricane / latest-first-major check for one basin."""
    firsts = {}
    for year, yr_storms in storms_by_year.items():
        dates = [(s[field], s['name']) for s in yr_storms if s.get(field)]
        if dates:
            firsts[year] = min(dates, key=lambda d: d[0])
    if not firsts:
        return None
    none_years = sorted(y for y in storms_by_year if y not in firsts)
    latest_key = max(_calendar_key(d) for d, _ in firsts.values())
    holders = [(y, n) for y, (d, n) in firsts.items() if _calendar_key(d) == latest_key]
    record_date = firsts[holders[0][0]][0]
    record_label = _portable_strftime(record_date, '%B %-d')
    holder_text = f"{_names_and_years(holders)}, {record_label}"
    none_note = ''
    if none_years:
        yrs = ', '.join(str(y) for y in none_years)
        none_note = f" ({yrs} had none at all.)"

    current = [s[field] for s in current_storms if s.get(field)]
    if current:
        first = min(current)
        if _calendar_key(first) > latest_key:
            return {
                'status': 'set',
                'title': f'Latest first {label} since {START_YEAR}',
                'detail': (f"This season's first {label} formed "
                           f"{_portable_strftime(first, '%B %-d')}. Previous latest: {holder_text}."),
            }
        return None

    record_this_year = datetime(current_year, record_date.month, record_date.day)
    days_left = (record_this_year.date() - today.date()).days
    if days_left < 0:
        return {
            'status': 'set',
            'title': f'Latest first {label} since {START_YEAR}',
            'detail': (f"No {label} yet this season, already later than any season since "
                       f"{START_YEAR} that had one. Previous latest: {holder_text}.{none_note}"),
        }
    if days_left <= RECORD_WATCH_DAYS:
        return {
            'status': 'in_play',
            'title': f'Latest first {label}',
            'detail': (f"No {label} yet this season. The latest first {label} since "
                       f"{START_YEAR} was {holder_text}, {days_left} day"
                       f"{'s' if days_left != 1 else ''} from now.{none_note}"),
        }
    return None


def calculate_records_in_play(historical_storms, basin_key, current_ace, target_date=None):
    """Season records the current season is setting or close to, compared
    with every completed season since START_YEAR: latest first hurricane,
    latest first major hurricane, lowest/highest ACE for the date, and
    fastest to 100 ACE. History only — never a forecast.

    Returns a list of {'status': 'set' | 'in_play', 'title', 'detail'}
    dicts; empty when nothing is notable.
    """
    if not historical_storms:
        return []
    today = target_date or _utc_now()
    current_year = today.year

    storms_by_year = {}
    for s in historical_storms:
        if START_YEAR <= s['year'] < current_year:
            storms_by_year.setdefault(s['year'], []).append(s)
    if not storms_by_year:
        return []
    current_storms = [s for s in historical_storms if s['year'] == current_year]

    records = []
    for field, label in (('hurricane_date', 'hurricane'), ('major_date', 'major hurricane')):
        rec = _first_event_records(storms_by_year, current_storms, field, label, today, current_year)
        if rec:
            records.append(rec)

    sd = calculate_same_date_stats(historical_storms, basin_key, today)
    if sd and sd['day_of_season'] >= 30:
        ranked = sorted(sd['yearly_ace'].items(), key=lambda kv: kv[1])
        n = len(ranked) + 1
        low_rank = 1 + sum(1 for _, ace in ranked if ace < current_ace)
        high_rank = 1 + sum(1 for _, ace in ranked if ace > current_ace)
        low_year, low_ace = ranked[0]
        high_year, high_ace = ranked[-1]
        through = f"through {sd['date_label']}"
        if low_rank == 1:
            records.append({
                'status': 'set',
                'title': f'Lowest ACE for the date since {START_YEAR}',
                'detail': f"{current_ace:.1f} ACE {through}. Previous low: {low_ace:.1f} in {low_year}.",
            })
        elif low_rank <= 3:
            records.append({
                'status': 'in_play',
                'title': 'Among the lowest ACE for the date',
                'detail': (f"{current_ace:.1f} ACE {through} ranks #{low_rank} lowest of {n} seasons. "
                           f"Record low: {low_ace:.1f} in {low_year}."),
            })
        if high_rank == 1:
            records.append({
                'status': 'set',
                'title': f'Most ACE for the date since {START_YEAR}',
                'detail': f"{current_ace:.1f} ACE {through}. Previous high: {high_ace:.1f} in {high_year}.",
            })
        elif high_rank <= 3:
            records.append({
                'status': 'in_play',
                'title': 'Among the most ACE for the date',
                'detail': (f"{current_ace:.1f} ACE {through} ranks #{high_rank} highest of {n} seasons. "
                           f"Record: {high_ace:.1f} in {high_year}."),
            })

    if current_ace >= FAST_100_MIN_ACE:
        reached = {}
        for year, yr_storms in storms_by_year.items():
            d = _date_reached_ace(yr_storms, year, 100)
            if d:
                reached[year] = d
        if reached:
            fastest_year = min(reached, key=lambda y: _calendar_key(reached[y]))
            fastest = reached[fastest_year]
            fastest_label = _portable_strftime(fastest, '%B %-d')
            if current_ace >= 100:
                mine = _date_reached_ace(current_storms, current_year, 100) or today
                if _calendar_key(mine) < _calendar_key(fastest):
                    records.append({
                        'status': 'set',
                        'title': f'Fastest to 100 ACE since {START_YEAR}',
                        'detail': (f"Reached 100 ACE by {_portable_strftime(mine, '%B %-d')}. "
                                   f"Previous fastest: {fastest_year}, {fastest_label}."),
                    })
            else:
                deadline = datetime(current_year, fastest.month, fastest.day)
                days_left = (deadline.date() - today.date()).days
                if days_left >= 0:
                    records.append({
                        'status': 'in_play',
                        'title': 'Fastest to 100 ACE',
                        'detail': (f"At {current_ace:.1f} ACE. The fastest season to 100 since "
                                   f"{START_YEAR} was {fastest_year}, reaching it {fastest_label} "
                                   f"({days_left} day{'s' if days_left != 1 else ''} from now)."),
                    })
    return records


def _percentile(sorted_values, pct):
    """Linear-interpolation percentile over an already-sorted list."""
    n = len(sorted_values)
    if n == 0:
        return 0.0
    if n == 1:
        return sorted_values[0]
    k = (n - 1) * (pct / 100)
    f, c = int(k), min(int(k) + 1, n - 1)
    if f == c:
        return sorted_values[f]
    return sorted_values[f] * (c - k) + sorted_values[c] * (k - f)


def calculate_ace_pace(historical_storms, basin_key, as_of_date=None):
    """Build day-by-day cumulative ACE curves for the dashboard pace chart:
    historical climatology (mean/p25/p75, excluding the current season),
    this season's own cumulative curve (prorated up to `as_of_date`, using
    the same proration logic as calculate_same_date_stats), and last
    season's complete curve.

    Returns None if there is no historical data to build a climatology from.
    """
    if as_of_date is None:
        as_of_date = _utc_now()

    if basin_key == 'atlantic':
        ssm, ssd = 6, 1   # June 1
    else:
        ssm, ssd = 5, 15  # May 15

    season_start = datetime(as_of_date.year, ssm, ssd)
    season_end = datetime(as_of_date.year, 11, 30)
    total_days = (season_end - season_start).days
    today_index = min(total_days, max(0, (as_of_date - season_start).days))

    storms_by_year = {}
    for s in historical_storms:
        storms_by_year.setdefault(s['year'], []).append(s)

    climatology_years = [y for y in storms_by_year if y < as_of_date.year]
    if not climatology_years:
        return None

    def cumulative_curve(year, storms):
        curve = []
        for d in range(total_days + 1):
            cutoff = datetime(year, ssm, ssd) + timedelta(days=d)
            curve.append(round(sum(_storm_ace_at_cutoff(s, cutoff) for s in storms), 2))
        return curve

    climatology_curves = [cumulative_curve(y, storms_by_year[y]) for y in climatology_years]

    climatology_mean = []
    climatology_p25 = []
    climatology_p75 = []
    for d in range(total_days + 1):
        day_values = sorted(curve[d] for curve in climatology_curves)
        climatology_mean.append(round(sum(day_values) / len(day_values), 2))
        climatology_p25.append(round(_percentile(day_values, 25), 2))
        climatology_p75.append(round(_percentile(day_values, 75), 2))

    current_year = as_of_date.year
    current_full = cumulative_curve(current_year, storms_by_year.get(current_year, []))
    current_season = [v if d <= today_index else None for d, v in enumerate(current_full)]

    last_year = current_year - 1
    last_season = cumulative_curve(last_year, storms_by_year[last_year]) if last_year in storms_by_year else None

    day_labels = [_portable_strftime(season_start + timedelta(days=d), '%b %-d') for d in range(total_days + 1)]

    return {
        'day_labels': day_labels,
        'climatology_mean': climatology_mean,
        'climatology_p25': climatology_p25,
        'climatology_p75': climatology_p75,
        'current_season': current_season,
        'last_season': last_season,
        'today_index': today_index,
        'current_year': current_year,
        'last_year': last_year,
        'years_used': len(climatology_years),
        'basin_key': basin_key,
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
    full_rank, total_seasons = rank_current_season(yearly_totals, current_year, current_ace)

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

    # 7b. Landfall share of ACE — how much of the season's energy came from
    # storms that hit land vs. fish storms. Uses current-season storm details
    # (their landfall list includes the geographic fallback for live tracks).
    details = [dict(d, name=n) for n, d in current.get('storm_details', {}).items()]
    share = landfall_ace_share(details)
    if share:
        avg_share = average_landfall_share(yearly_stats, current_year)
        avg_note = f" ({START_YEAR}–{current_year - 1} average: {avg_share}%)" if avg_share is not None else ""
        label = f"🏝️ Landfall share{' (estimated)' if any(d.get('landfall_estimated') for d in details) else ''}"
        fish = f"{share['fish_count']} fish storm{'s' if share['fish_count'] != 1 else ''}"
        td_note = _depression_landfall_note(details)
        if share['landfall_count'] == 0:
            insights.append(
                f"{label}: no storm has made landfall at tropical-storm strength or stronger{avg_note}, "
                f"so {'all ' if share['fish_count'] > 1 else ''}{share['fish_count']} "
                f"storm{'s' if share['fish_count'] != 1 else ''} count{'' if share['fish_count'] != 1 else 's'} "
                f"as {'fish storms' if share['fish_count'] != 1 else 'a fish storm'}{td_note}")
        else:
            insights.append(
                f"{label}: {share['landfall_pct']}% of season ACE came from the "
                f"{share['landfall_count']} storm{'s' if share['landfall_count'] != 1 else ''} that made landfall "
                f"at tropical-storm strength or stronger{avg_note}; {share['fish_pct']}% from {fish}{td_note}")

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

    # 11. Highest single-storm ACE since START_YEAR. Computed dynamically
    # from historical_storms rather than a hardcoded reference value -- the
    # previous hardcoded Pacific constant (Fico 1978, 62.8) had gone stale;
    # Ioke (2006, 85.3) is actually the higher storm. See #117. Framed as
    # "since START_YEAR" rather than "all-time" since pre-satellite-era
    # (pre-1970s) intensity estimates aren't a reliable apples-to-apples
    # comparison to modern storms.
    record = find_highest_ace_storm(historical_storms)
    if storms and record:
        leader_name = max(storms, key=storms.get)
        leader_ace = storms[leader_name]
        pct_of_record = leader_ace / record['ace'] * 100
        if pct_of_record > 50:
            insights.append(
                f"🎯 {leader_name} at {pct_of_record:.0f}% of the highest single-storm ACE "
                f"since {START_YEAR} ({record['name']} {record['year']}: {record['ace']:.1f})")

    # 12. On this day in hurricane history
    if historical_storms:
        on_this_day = find_storms_on_this_day(historical_storms)
        if on_this_day:
            top = on_this_day[0]
            others = len(on_this_day) - 1
            others_label = f" (+{others} more storm{'s' if others > 1 else ''} on this date since {START_YEAR})" if others > 0 else ""
            insights.append(
                f"📅 On This Day in History: {top['name']} ({top['year']}) was active — "
                f"{top['category']}, {top['ace']:.1f} ACE{others_label}"
            )

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
    rank, total_seasons = rank_current_season(yearly_totals, current_year, current_ace)
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

TCR_INDEX_URL = 'https://www.nhc.noaa.gov/TCR_StormReportsIndex.xml'


def parse_tcr_index(xml_text):
    """Parse NHC's Tropical Cyclone Report index into rows of
    {'name', 'url', 'year', 'basin'} ('basin' is 'atlantic' or 'pacific')."""
    import xml.etree.ElementTree as ET
    rows = []
    for row in ET.fromstring(xml_text).iter('row'):
        url = (row.findtext('StormReportURL') or '').strip()
        year = (row.findtext('Year') or '').strip()
        basin = (row.findtext('Basin') or '').strip().lower()
        if url.startswith('https://www.nhc.noaa.gov/') and year.isdigit() and basin in BASINS:
            rows.append({'name': (row.findtext('StormName') or '').strip(),
                         'url': url, 'year': int(year), 'basin': basin})
    return rows


def _tcr_row_storm_name(row):
    """'Hurricane Andrew (Atlantic)' -> 'andrew'; 'Tropical Storm (Unnamed)
    (Atlantic)' -> 'unnamed'."""
    import re
    name = re.sub(r'\s*\((Atlantic|Pacific)\)\s*$', '', row['name'], flags=re.I)
    words = re.sub(r'[()]', ' ', name).split()
    return words[-1].lower() if words else ''


def match_tcr_reports(rows, storms, basin_key):
    """Map storm id -> NHC report URL for one basin.

    1995+ reports are PDFs named by storm id (AL012005_Arlene.pdf, or both
    ids for a storm that crossed basins: AL022022_EP042022_Bonnie.pdf), so
    they match exactly. 1991-1994 reports are "storm wallet" folders named
    by storm name (sometimes cut to 8 letters, e.g. 'guillerm' for
    Guillermo), matched by year and name. Anything left (e.g. Andrew 1992's
    own page, or a crossover filed under the other basin's id) falls back to
    a year + name match, same basin first. Unnamed storms only match by id.
    Storms without a report are left out.
    """
    import re
    by_id = {}
    wallets = {}
    by_name = {}
    for r in rows:
        leaf = r['url'].rstrip('/').rsplit('/', 1)[-1]
        if leaf.lower().endswith('.pdf'):
            for sid in re.findall(r'[A-Z]{2}\d{6}', leaf.upper()):
                by_id.setdefault(sid, r['url'])
        elif r['basin'] == basin_key and '/storm_wallets/' in r['url']:
            wallets[(r['year'], leaf.lower())] = r['url']
        name = _tcr_row_storm_name(r)
        rank = 0 if r['basin'] == basin_key else 1
        key = (r['year'], name)
        if name and name != 'unnamed' and (key not in by_name or rank < by_name[key][0]):
            by_name[key] = (rank, r['url'])
    matched = {}
    for s in storms:
        sid = str(s.get('id', '')).upper()
        if sid in by_id:
            matched[sid] = by_id[sid]
            continue
        name = str(s.get('name', '')).lower()
        year = s.get('year')
        for (w_year, leaf), url in wallets.items():
            if w_year == year and (leaf == name or (len(leaf) >= 8 and name.startswith(leaf))):
                matched[sid] = url
                break
        else:
            if name != 'unnamed' and (year, name) in by_name:
                matched[sid] = by_name[(year, name)][1]
    return matched


_tcr_rows_cache = None


def fetch_tcr_reports(storms, basin_key):
    """Per-storm NHC Tropical Cyclone Report links ({storm id: url}) from
    NHC's report index, downloaded once per run and shared by both basins.
    Returns {} on any failure, so the history page falls back to the
    season-level report links."""
    global _tcr_rows_cache
    try:
        if _tcr_rows_cache is None:
            req = urllib.request.Request(TCR_INDEX_URL, headers={'User-Agent': 'ACETracker/1.0'})
            with urllib.request.urlopen(req, timeout=15) as resp:
                _tcr_rows_cache = parse_tcr_index(resp.read().decode('utf-8', errors='replace'))
        rows = _tcr_rows_cache
        matched = match_tcr_reports(rows, storms or [], basin_key)
        print(f"  ✓ NHC storm reports: {len(matched)} linked")
        return matched
    except Exception as e:
        logger.warning(f"Could not load NHC storm report index: {e}")
        print(f"  → NHC storm report index unavailable ({e}); using season links")
        return {}



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

        # "Active Systems:" lists storms already under advisories, not a
        # disturbance. In an unnumbered outlook it would otherwise become the
        # disturbance's area and description.
        text = re.sub(r'Active Systems:.*?(?:\n\s*\n|$)', '', text,
                      flags=re.IGNORECASE | re.DOTALL)

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
                stripped = re.sub(r'^\d+\.\s*', '', ln).strip()
                # "Location Name: rest of text" — split on first colon
                colon_match = re.match(r'^([\w ,\-()]{4,60}):\s*(.*)$', stripped)
                if colon_match and not area_line:
                    area_line = colon_match.group(1).strip()
                    rest = colon_match.group(2).strip()
                    if rest:
                        desc_lines.append(rest)
                else:
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
    'atlantic': ('AT',),
    'pacific':  ('EP', 'CP'),
}


def fetch_active_storm_cones(basin_key, storm_details):
    """Fetch and locally cache NHC forecast cone images for currently active storms.

    Downloads each active storm's 5-day cone PNG from NHC once per run and saves it
    under data/cones/, so the dashboard serves the image from our own domain instead
    of hotlinking NHC's graphics server on every visitor request. The cone image
    filename embeds the forecast advisory's update time, which we read from
    CurrentStorms.json rather than guessing.

    While fetching, also cross-checks the 48h last-track-point 'is_active' heuristic
    against NHC's live active-storm list and mutates storm_details in place to
    correct it — the heuristic alone leaves dissipated storms marked active for up
    to 48h after their final advisory (#95). If the fetch fails, is_active is left
    untouched (fail open) rather than losing active-storm UI to a transient outage.

    Returns a dict of storm_name -> relative path (e.g. 'cones/ep042026.png'),
    or {} if nothing is active or the fetch fails. Also records each cone's
    advisory time as storm_details[name]['cone_issued'] (ISO UTC).
    """
    import urllib.request

    candidate_names = {name.upper() for name, d in storm_details.items() if d.get('is_active')}
    if not candidate_names:
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

    live_active_names = {
        (storm.get('name') or '').upper()
        for storm in data.get('activeStorms', [])
        if (storm.get('binNumber') or '').startswith(prefixes)
    }

    for stale_name in candidate_names - live_active_names:
        for orig_name, details in storm_details.items():
            if orig_name.upper() == stale_name:
                details['is_active'] = False
                break

    active_names = candidate_names & live_active_names
    if not active_names:
        return {}

    cone_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'cones')
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
            # NHC's storm_graphics folder uses the ATCF basin+number for EP/CP storms,
            # but 'AT' (not 'AL') for Atlantic storms, e.g. al032026 -> AT03.
            graphics_prefix = 'AT' if basin_key == 'atlantic' else storm_id[:2].upper()
            bin4 = graphics_prefix + storm_id[2:4].upper()
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
                    issued = ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
                    storm_details[orig_name]['cone_issued'] = (
                        issued.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))
                    break
        except Exception as e:
            logger.warning(f"Could not fetch cone image for {name}: {e}")
            continue

    return images





# ===============================================================================
# SEASON PAYLOAD
# ===============================================================================

def build_season_payload(basin_data):
    """Everything a page, feed or API needs to describe one basin's current
    season, as plain data with no HTML in it.

    `basin_data` is one process_basin() result. This is the only place that
    does the render-time network fetches (cones, NHC outlook), so renderers
    stay pure and a second consumer can reuse the payload without refetching.
    The cone fetch must run before the storm list is read: it corrects
    `is_active` and sets `cone_issued` on storm_details in place.
    """
    basin_key = basin_data['basin_key']
    basin = BASINS[basin_key]
    current = basin_data['current']
    yearly_totals = basin_data['yearly_totals']
    year = current['year']
    total = current['total']
    details = current.get('storm_details', {})

    cone_images = fetch_active_storm_cones(basin_key, details)

    preseason = not current['storms'] and year == _utc_now().year
    rank = total_seasons = None
    if not preseason:
        rank, total_seasons = rank_current_season(yearly_totals, year, total)

    storms = []
    for name, ace in sorted(current['storms'].items(), key=lambda x: x[1], reverse=True):
        d = details.get(name, {})
        wind = d.get('max_wind', 0)
        is_active = d.get('is_active', False)
        # spaghetti was fetched under the pre-cross-check is_active heuristic,
        # so drop it if is_active was since corrected to False: a dissipated
        # storm's stale forecast isn't worth showing.
        spaghetti = d.get('spaghetti', {}) if is_active else {}
        storms.append({
            'name': name,
            'slug': name.lower().replace(' ', '-'),
            'page_slug': re.sub(r'[^a-z0-9]+', '-', f'{name}-{year}'.lower()).strip('-'),
            'ace': ace,
            'pct_of_season': (ace / total * 100) if total > 0 else 0,
            'max_wind': wind,
            'category': get_category(wind) if wind > 0 else '—',
            'is_major': wind >= 96,
            'is_active': is_active,
            'start_date': d.get('start_date', '—'),
            'landfall': d.get('landfall', []),
            'landfall_estimated': bool(d.get('landfall_estimated')),
            'track_points': d.get('track_points', []),
            'spaghetti': spaghetti,
            'spaghetti_cycles': {m: c for m, c in (d.get('spaghetti_cycles') or {}).items() if m in spaghetti},
            'cone_image': cone_images.get(name) if is_active else None,
            'cone_issued': d.get('cone_issued'),
        })

    return {
        'basin_key': basin_key,
        'basin_name': basin['name'],
        'year': year,
        'preseason': preseason,
        'is_backup': bool(current.get('is_backup')),
        'data_as_of': current.get('data_as_of'),
        'ace_total': total,
        'normal_ace': basin['normal_ace'],
        'pct_of_normal': (total / basin['normal_ace'] * 100) if basin['normal_ace'] > 0 else 0,
        'classification': get_noaa_classification(total, basin_key),
        'named_storms': len(details),
        'hurricanes': sum(1 for d in details.values() if d.get('max_wind', 0) >= 64),
        'major_hurricanes': sum(1 for d in details.values() if d.get('max_wind', 0) >= 96),
        'rank': rank,
        'total_seasons': total_seasons,
        'storms': storms,
        'insights': basin_data['insights'],
        'records_in_play': basin_data.get('records_in_play'),
        'ace_pace': basin_data.get('ace_pace'),
        'projection': get_season_projection(total, basin_key),
        'disturbances': fetch_nhc_disturbances(basin_key),
        'yearly_totals': yearly_totals,
    }


def ensure_unique_page_slugs(payloads):
    """Storm pages live at /storm/<page_slug>.html, so two storms must never
    share one. Names are unique per basin-year in practice; if a collision
    ever happens, the later storm gets its basin appended."""
    seen = set()
    for p in payloads:
        for s in p['storms']:
            if s['page_slug'] in seen:
                s['page_slug'] = f"{s['page_slug']}-{p['basin_key']}"
            seen.add(s['page_slug'])

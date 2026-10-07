"""
ace_html.py
===========
HTML rendering for the ACE Tracker dashboard and history pages. Consumes
data structures and functions from ace_data.py; contains no data-fetching
logic of its own except the NHC alert/cone fetches called mid-render from
generate_dashboard_html (kept at their original call sites intentionally).
"""

from html import escape as html_escape
import json
import logging
from datetime import datetime, timezone

from ace_data import (
    BASINS,
    SITE_URL,
    START_YEAR,
    get_category,
    get_noaa_classification,
    build_season_payload,
    find_highest_ace_storm,
    find_longest_lived_storm,
    find_strongest_landfall,
    find_earliest_forming_storm,
    find_latest_forming_storm,
    landfall_ace_share,
    depression_only_landfalls,
    average_landfall_share,
    _portable_strftime,
    MIN_NAMED_STORM_WIND,
)

from ace_assets import (
    BASE_CSS, NAV_CSS, HEADINGS_CSS, STORM_PANEL_CSS, CONE_CSS,
    WIND_JS, LIB_MISSING_JS, TRACK_MAP_JS, THEME_INIT_JS,
)

logger = logging.getLogger(__name__)

# ===============================================================================
# TRACK / STORM-LIST HTML HELPERS
# ===============================================================================

def _track_status_color(status, wind):
    """Return a hex color for a track point based on storm status and wind speed."""
    if status in ('HU',):
        if wind >= 137: return '#b71c1c'
        if wind >= 113: return '#ef5350'
        if wind >= 96:  return '#ff8a65'
        if wind >= 83:  return '#ffb74d'
        return '#ffe082'
    if status in ('TS', 'SS'): return '#81d4fa'
    return '#9e9e9e'  # TD / other



# HURDAT2 status codes spoken in the intensity bar's screen-reader label
_STAGE_NAMES = {
    'TD': 'tropical depression', 'TS': 'tropical storm', 'SD': 'subtropical depression',
    'SS': 'subtropical storm', 'EX': 'post-tropical', 'LO': 'low', 'DB': 'disturbance', 'WV': 'tropical wave',
}


def _intensity_bar_html(track_points):
    """Horizontal color bar showing intensity progression across all track points."""
    if not track_points:
        return ''
    segs = ''.join(
        f'<div class="intensity-seg" style="flex:1;background:{_track_status_color(p["status"],p["wind"])}" '
        f'data-status="{p["status"]}" data-wind-kt="{p["wind"]}" data-time="{p["time"]}" '
        f'title="{p["status"]} {p["wind"]}kt {p["time"]}"></div>'
        for p in track_points
    )
    # Screen readers get the stage sequence as text, since the segments are color-only.
    stages = []
    for p in track_points:
        stage = get_category(p['wind']) if p['status'] == 'HU' else _STAGE_NAMES.get(p['status'], p['status'])
        if not stages or stages[-1] != stage:
            stages.append(stage)
    label = html_escape('Intensity over time: ' + ' → '.join(stages))
    return f'<div class="intensity-bar" role="img" aria-label="{label}">{segs}</div>'



def _storm_report_link_html(name, url):
    """Small document icon linking to a storm's NHC Tropical Cyclone Report."""
    if not url:
        return ''
    label = html_escape(f'NHC report for {name}')
    return (f'<a class="ys-tcr" href="{html_escape(url)}" target="_blank" rel="noopener noreferrer" '
            f'title="{label}" aria-label="{label}">&#128196;</a>')


def _year_storm_list_html(storms_list, report_urls=None):
    """Inline HTML list of storms for the history page accordion.
    `report_urls` maps storm id (or name, for the in-progress season) to its
    NHC report URL."""
    if not storms_list:
        return '<p style="color:var(--muted);font-size:0.82em;padding:4px 0 2px">No named storms on record</p>'
    max_ace = storms_list[0]['ace'] if storms_list[0]['ace'] > 0 else 1
    rows = []
    for s in storms_list:
        bar_pct = round(s['ace'] / max_ace * 100)
        lf = s.get('landfall', [])
        if lf:
            lf_parts = [f'{html_escape(loc)} ({html_escape(cat)})' for loc, cat in lf]
            lf_html = f'<span class="ys-lf">{" · ".join(lf_parts)}</span>'
        else:
            lf_html = '<span class="ys-lf ys-fish" data-tip="A storm that never made landfall and just pissed off fish">Fish Storm</span>'
        rows.append(
            f'<div class="ys-row">'
            f'<span class="ys-name">{html_escape(s["name"])}'
            f'{_storm_report_link_html(s["name"], (report_urls or {}).get(s.get("id") or s["name"]))}{lf_html}</span>'
            f'<span class="ys-cat" data-tip="Peak intensity">{s["category"]}</span>'
            f'<span class="ys-ace">{s["ace"]:.1f}</span>'
            f'<div class="ys-bar"><div class="ys-bar-fill" style="width:{bar_pct}%"></div></div>'
            f'</div>'
        )
    return '\n'.join(rows)


def _landfall_share_html(storms_list):
    """One-line landfall vs. fish-storm ACE split for a season's panel."""
    share = landfall_ace_share(storms_list)
    if not share:
        return ''
    lf_n, fish_n = share['landfall_count'], share['fish_count']
    td_n = len(depression_only_landfalls(storms_list))
    td_note = (f', incl. {td_n} that reached land only as a depression{"s" if td_n != 1 else ""}'
               if td_n else '')
    return (f'<div class="yr-lfshare"><span class="lfs-bar" aria-hidden="true">'
            f'<span class="lfs-fill" style="width:{share["landfall_pct"]}%"></span></span>'
            f'<span>&#127965;&#65039; Landfalling (TS or stronger): <b>{share["landfall_pct"]}%</b> of ACE ({lf_n} storm{"s" if lf_n != 1 else ""})'
            f' &nbsp;·&nbsp; &#128031; Fish storms: <b>{share["fish_pct"]}%</b> ({fish_n}{td_note})</span></div>')


# NHC Tropical Cyclone Report (TCR) archive basins. The E/C Pacific tab combines
# two NHC/CPHC basins, so it links to both season pages.
TCR_BASINS = {
    'atlantic': [('atl', 'Atlantic')],
    'pacific': [('epac', 'Eastern Pacific'), ('cpac', 'Central Pacific')],
}


def _decade_label(year):
    """Decade bucket used by the history page filter, e.g. 1994 -> '1990s'."""
    return f'{year // 10 * 10}s'


def _nhc_tcr_links_html(year, basin_key, is_active=False):
    """Links to NHC's Tropical Cyclone Report index for a season (#50).

    Shown alongside the per-storm report icons as a fallback: NHC's report
    index misses some storms (mostly Central Pacific ones) and a new
    season's reports only appear months after each storm.
    """
    links = ' · '.join(
        f'<a href="https://www.nhc.noaa.gov/data/tcr/index.php?season={year}&amp;basin={code}" '
        f'target="_blank" rel="noopener noreferrer">{label} &#8599;</a>'
        for code, label in TCR_BASINS.get(basin_key, [])
    )
    if not links:
        return ''
    note = (' <span class="yr-tcr-note">(NHC publishes reports after each storm, '
            'so this season is still filling in)</span>') if is_active else ''
    return f'<div class="yr-tcr">&#128196; NHC storm reports for {year}: {links}{note}</div>'



SHARE_IMAGE_ALT = 'ACE Tracker: live hurricane season ACE for the Atlantic and E/C Pacific'


def _season_year(basin_data):
    """The season year the pages describe (for titles), falling back to the
    current UTC year when no basin data is available."""
    years = [bd['current']['year'] for bd in basin_data if bd and bd.get('current')]
    return max(years) if years else datetime.now(timezone.utc).year


def _share_image_meta(alt, image='ace_preview.png'):
    """Open Graph / Twitter image tags for the 1200x630 share card. `image`
    is a path relative to the site root."""
    alt = html_escape(alt)
    url = html_escape(f'https://aceofcanes.com/{image}')
    return (f'<meta property="og:image" content="{url}">\n'
            f'<meta property="og:image:width" content="1200">\n'
            f'<meta property="og:image:height" content="630">\n'
            f'<meta property="og:image:alt" content="{alt}">\n'
            f'<meta name="twitter:card" content="summary_large_image">')


# ===============================================================================
# DASHBOARD SECTIONS
# ===============================================================================

def _season_progress_html(basin_key, season_year):
    today = datetime.now(timezone.utc).date()
    if basin_key == 'atlantic':
        start = datetime(season_year, 6, 1).date()
        end = datetime(season_year, 11, 30).date()
    else:
        start = datetime(season_year, 5, 15).date()
        end = datetime(season_year, 11, 30).date()
    total_days = (end - start).days + 1
    # Past season or after Nov 30 — show full completed bar
    if today > end:
        return (
            f'<div class="season-prog">'
            f'<div class="season-prog-label">Day {total_days} of {total_days} &middot; Season complete</div>'
            f'<div class="season-prog-track"><div class="season-prog-fill" style="width:100%"></div></div>'
            f'</div>'
        )
    if today < start:
        days_until = (start - today).days
        label = f'Season begins {start.strftime("%B")} {start.day} — {days_until} day{"s" if days_until != 1 else ""} away'
        return f'<div class="season-prog offseason">{label}</div>'
    day_num = (today - start).days + 1
    pct = day_num / total_days * 100
    return (
        f'<div class="season-prog">'
        f'<div class="season-prog-label">Day {day_num} of {total_days} &middot; {pct:.0f}% complete</div>'
        f'<div class="season-prog-track"><div class="season-prog-fill" style="width:{pct:.1f}%"></div></div>'
        f'</div>'
    )



def _preseason_html(basin_key, yearly_totals, current_year):
    """HTML block for the no-storms-yet state: replaces storm table + insights."""
    basin = BASINS[basin_key]
    normal = basin['normal_ace']

    totals = list(yearly_totals.values())
    avg_ace = sum(totals) / len(totals) if totals else 0
    max_year = max(yearly_totals, key=yearly_totals.get)
    min_year = min(yearly_totals, key=yearly_totals.get)
    above_count = sum(1 for v in totals if v >= basin['noaa_thresholds']['near_normal_upper'])
    total_seasons = len(totals)
    last_year = current_year - 1
    last_ace = yearly_totals.get(last_year, 0)
    last_class = get_noaa_classification(last_ace, basin_key) if last_ace else 'N/A'

    if basin_key == 'atlantic':
        peak_note = "Activity typically peaks in August–September when Atlantic sea surface temperatures reach their annual high."
    else:
        peak_note = "The Eastern Pacific is often active earlier in the season, with storms possible as soon as May."

    facts = [
        f"📅 Last season ({last_year}): {last_ace:.1f} ACE — {last_class}",
        f"📊 Historical average: {avg_ace:.1f} ACE/season (NOAA normal: {normal})",
        f"🏆 Most active since {START_YEAR}: {max_year} ({yearly_totals[max_year]:.1f} ACE)",
        f"📉 Quietest since {START_YEAR}: {min_year} ({yearly_totals[min_year]:.1f} ACE)",
        f"🌀 {above_count} of {total_seasons} seasons since {START_YEAR} were Above Normal or stronger",
        f"☀️ {peak_note}",
    ]
    fact_items = '\n'.join(f'<li>{f}</li>' for f in facts)

    return f'''
      <div class="preseason-notice">
        <p>No named storms yet — the {current_year} season is underway but quiet so far.</p>
      </div>
      <h3>Did You Know?</h3>
      <ul class="insights">{fact_items}</ul>'''



def _ace_pace_html(pace, basin_key):
    """HTML chrome for the Season Pace chart. The chart itself and the
    summary stat row are populated client-side from ACE_PACE — see
    _renderPaceChart()/toggleTheme() JS below — so this only emits the
    canvas and placeholder stat boxes."""
    if not pace:
        return ''
    return f'''
      <h3>Season Pace</h3>
      <div class="pace-chart-wrap"><canvas id="pace-canvas-{basin_key}"></canvas></div>
      <div class="pace-stats-mini">
        <div class="meta-box"><div class="meta-label">ACE to Date</div><div class="meta-value" id="pace-todate-{basin_key}">—</div></div>
        <div class="meta-box"><div class="meta-label">Normal for Today</div><div class="meta-value" id="pace-normal-{basin_key}">—</div></div>
        <div class="meta-box"><div class="meta-label">vs. Normal</div><div class="meta-value" id="pace-pct-{basin_key}">—</div></div>
      </div>
      <p class="pace-caption">Historical range based on {pace['years_used']} seasons since {START_YEAR}.</p>'''



# ===============================================================================
# NHC ALERT BANNER
# ===============================================================================

def _parse_utc(value):
    """An ISO-8601 or RFC 822 timestamp string as an aware UTC datetime, or None."""
    from email.utils import parsedate_to_datetime
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        try:
            dt = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _utc_label(dt):
    return f"{dt:%b} {dt.day}, {dt:%Y} {dt:%H:%M} UTC"


def _timestamp_html(dt):
    """A <time> element plus a relative-time slot filled in client-side."""
    iso = dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    return (f'<time datetime="{iso}">{_utc_label(dt)}</time>'
            f' <span class="rel-time" data-ts="{iso}"></span>')


def _cycle_label(iso):
    """'00Z Sep 27' for a model cycle time, or '' if unreadable."""
    dt = _parse_utc(iso)
    return f"{dt:%H}Z {dt:%b} {dt.day}" if dt else ''


def _data_as_of_html(data_as_of, outlook_issued=''):
    """'Data as of' line for a basin: the newest best-track point (how current
    the ACE numbers really are, as opposed to when the page was built) and,
    when a disturbance banner is shown, when NHC issued that outlook."""
    parts = []
    track_dt = _parse_utc(data_as_of)
    if track_dt:
        parts.append(f'Best-track data as of {_timestamp_html(track_dt)}')
    outlook_dt = _parse_utc(outlook_issued)
    if outlook_dt:
        parts.append(f'NHC outlook issued {_timestamp_html(outlook_dt)}')
    if not parts:
        return ''
    return f'<p class="data-asof">{" &nbsp;·&nbsp; ".join(parts)}</p>'


def _stale_data_banner_html():
    """Warning banner shown when live data was unavailable and the dashboard
    is falling back to placeholder data (see BACKUP_DATA, #98)."""
    return (
        '<div class="nhc-alert">'
        '<div class="nhc-alert-hdr">⚠ Live storm data is temporarily unavailable</div>'
        '<div class="nhc-dist-desc">Showing placeholder data for this season — '
        'named storms and ACE totals below are not current. Check back shortly.</div>'
        '</div>'
    )



def _developing_alert_html(systems):
    """Banner for depressions and potential tropical cyclones under NHC
    advisories: they have left the outlook but could still become named storms."""
    if not systems:
        return ''
    rows = []
    for s in systems:
        wind = f' — {s["intensity_kt"]} kt' if s.get('intensity_kt') is not None else ''
        rows.append(
            f'<div class="nhc-dist">'
            f'<div class="nhc-dist-area">{html_escape(s["label"])}{wind}</div>'
            f'<div class="nhc-dist-desc">Under NHC advisories and could strengthen into a named storm.</div>'
            f'<a class="nhc-alert-link" href="{html_escape(s["advisory_url"])}" target="_blank" rel="noopener">'
            f'View NHC public advisory ↗</a>'
            f'</div>'
        )
    count = len(systems)
    noun = 'system' if count == 1 else 'systems'
    return (
        f'<div class="nhc-alert">'
        f'<div class="nhc-alert-hdr">⚠ {count} active {noun} could form into a named storm</div>'
        + ''.join(rows) +
        f'</div>'
    )


def _nhc_alert_html(disturbances):
    """Render the NHC tropical disturbance alert banner."""
    if not disturbances:
        return ''

    nhc_url = disturbances[0]['nhc_url']
    issued  = disturbances[0]['issued']
    count   = len(disturbances)
    noun    = 'area' if count == 1 else 'areas'

    def chance_badge(level, pct):
        if level == 'HIGH' or pct >= 70:
            color, dot = '#ef5350', '🔴'
        elif level == 'MEDIUM' or pct >= 40:
            color, dot = '#ffa726', '🟡'
        else:
            color, dot = '#9e9e9e', '⚪'
        return f'<span style="color:{color};font-weight:600">{dot} {pct}% ({level.title()})</span>'

    rows = []
    for i, d in enumerate(disturbances, 1):
        area = html_escape(d['area'] or f'Disturbance {i}')
        b48  = chance_badge(d['level_48h'], d['pct_48h'])
        b7d  = chance_badge(d['level_7d'],  d['pct_7d'])
        desc_html = f'<div class="nhc-dist-desc">{html_escape(d["desc"])}</div>' if d['desc'] else ''
        rows.append(
            f'<div class="nhc-dist">'
            f'<div class="nhc-dist-area">Disturbance {i} — {area}</div>'
            f'{desc_html}'
            f'<div class="nhc-dist-chances">48h: {b48} &nbsp;·&nbsp; 7-day: {b7d}</div>'
            f'</div>'
        )

    issued_html = f'<span class="nhc-issued">Outlook issued {html_escape(issued)}</span>' if issued else ''

    return (
        f'<div class="nhc-alert">'
        f'<div class="nhc-alert-hdr">⚠ NHC is monitoring {count} {noun} for potential tropical development</div>'
        + ''.join(rows) +
        f'<div class="nhc-alert-foot">'
        f'{issued_html}'
        f'<a class="nhc-alert-link" href="{nhc_url}" target="_blank" rel="noopener">'
        f'View NHC Tropical Weather Outlook ↗</a>'
        f'</div>'
        f'</div>'
    )


def _record_share_button(record, basin_key, basin_name, year):
    """Share button for one Records in Play item: a ready-to-post line plus a
    link to the basin's tab. Shares via the OS sheet on touch devices, else
    copies the post to the clipboard (see shareRecord() in the page JS)."""
    text = f'{record["title"]}: {record["detail"]} ({basin_name} {year})'
    url = f'{SITE_URL}/#{basin_key}'
    return (f'<button class="rip-share-btn" type="button" data-tip="Share this stat" '
            f'aria-label="Share: {html_escape(record["title"])}" '
            f'data-share-text="{html_escape(text)}" data-share-url="{html_escape(url)}" '
            f'onclick="shareRecord(event)">&#128279;</button>')


def _records_in_play_html(records, basin_key=None, basin_name='', year=None):
    """'Records in Play' panel: season records the current season is setting
    or close to, versus every season since START_YEAR. Omitted when empty.
    Share buttons appear when the basin is given."""
    if not records:
        return ''
    badges = {'set': ('rip-set', 'Record'), 'in_play': ('rip-watch', 'In play')}
    items = ''.join(
        f'<li class="rip-item"><span class="rip-badge {badges[r["status"]][0]}">{badges[r["status"]][1]}</span>'
        f'<span class="rip-body"><b>{html_escape(r["title"])}</b> {html_escape(r["detail"])}</span>'
        f'{_record_share_button(r, basin_key, basin_name, year) if basin_key else ""}</li>'
        for r in records)
    return f'''
      <h3>Records in Play</h3>
      <ul class="rip-list">{items}</ul>
      <p class="rip-caption">Compared with every season since {START_YEAR}. Based on history only, not a forecast.</p>'''



def _season_projection_html(projection):
    """Render the 'what would it take?' daily-ACE-rate projection widget."""
    if not projection:
        return ''

    rows = ''.join(
        f'<div class="proj-row">'
        f'<span class="proj-label">{html_escape(p["label"])} <span class="proj-threshold">(≥{p["threshold"]} ACE)</span></span>'
        f'<span class="proj-value">{p["daily_rate"]:.2f} ACE/day</span>'
        f'</div>'
        for p in projection
    )
    return f'''
      <h3>What Would It Take?</h3>
      <div class="projection-widget">
        <p class="projection-caption">Daily ACE rate needed for the rest of the season to reach each classification by Nov 30:</p>
        {rows}
      </div>'''


# NHC 'binNumber' prefixes for CurrentStorms.json entries, keyed by our basin_key



# ===============================================================================
# FULL DASHBOARD PAGE
# ===============================================================================

def generate_dashboard_html(basin_data):
    """Generate a mobile-friendly HTML dashboard for both basins."""
    return render_dashboard_html([build_season_payload(bd) for bd in basin_data if bd])


def _storm_track_entry(st):
    """Per-storm dict the map JS reads from ACE_TRACKS."""
    return {
        'name': st['name'],
        'active': st['is_active'],
        'start': st['start_date'],
        'ace': round(st['ace'], 1),
        'max_wind': st['max_wind'],
        'category': st['category'],
        'points': st['track_points'],
        'spaghetti': st['spaghetti'],
        'spaghetti_cycles': {m: _cycle_label(c) for m, c in st['spaghetti_cycles'].items()
                             if _cycle_label(c)},
    }


def _storm_panel_inner_html(st, asset_prefix=''):
    """Expanded panel for one storm: meta boxes, intensity bar, map, cone.
    `asset_prefix` is the path from the page to the site root ('' or '../').
    """
    name = st['name']
    ace = st['ace']
    pct = st['pct_of_season']
    wind = st['max_wind']
    cat = st['category']
    is_active = st['is_active']
    track_points = st['track_points']
    spaghetti = st['spaghetti']
    start_date = st['start_date']
    slug = st['slug']

    active_badge = '<div class="active-badge"><span class="active-pulse"></span> Active Storm</div>' if is_active else ''
    nhc_link = ('<div class="nhc-link"><a href="https://www.nhc.noaa.gov/" target="_blank" rel="noopener">'
                'View NHC Active Storms →</a></div>') if is_active else ''

    cone_img = ''
    if st['cone_image']:
        cone_dt = _parse_utc(st['cone_issued'])
        cone_alt = f'NHC forecast cone for {html_escape(name)}'
        cone_when = ''
        if cone_dt:
            cone_alt += f', advisory issued {_utc_label(cone_dt)}'
            cone_when = f' &middot; advisory issued {_timestamp_html(cone_dt)}'
        cone_img = (
            f'<div class="cone-graphic">'
            f'<img src="{html_escape(asset_prefix + st["cone_image"])}" alt="{cone_alt}" loading="lazy">'
            f'<div class="cone-credit">Forecast cone via <a href="https://www.nhc.noaa.gov/" target="_blank" rel="noopener">NHC</a>{cone_when}</div>'
            f'</div>'
        )

    ibar = _intensity_bar_html(track_points)
    legend = (
        '<div class="track-legend">'
        '<div class="legend-item"><div class="legend-dot" style="background:#9e9e9e"></div>TD</div>'
        '<div class="legend-item"><div class="legend-dot" style="background:#81d4fa"></div>TS/SS</div>'
        '<div class="legend-item"><div class="legend-dot" style="background:#ffe082"></div>Cat 1</div>'
        '<div class="legend-item"><div class="legend-dot" style="background:#ffb74d"></div>Cat 2</div>'
        '<div class="legend-item"><div class="legend-dot" style="background:#ff8a65"></div>Cat 3</div>'
        '<div class="legend-item"><div class="legend-dot" style="background:#ef5350"></div>Cat 4/5</div>'
        '</div>'
    ) if track_points else ''

    meta = (
        f'<div class="storm-meta">'
        f'<div class="meta-box"><div class="meta-label">Started</div><div class="meta-value">{start_date}</div></div>'
        f'<div class="meta-box"><div class="meta-label">Peak Intensity</div><div class="meta-value"><span class="wind-val-unit" data-kt="{wind}">{wind} kt</span></div><div class="meta-sub">{cat}</div></div>'
        f'<div class="meta-box"><div class="meta-label">ACE</div><div class="meta-value">{ace:.1f}</div><div class="meta-sub">{pct:.0f}% of season</div></div>'
        f'</div>'
    )

    spaghetti_toggle = (
        f'<label class="spaghetti-toggle">'
        f'<input type="checkbox" id="sptoggle-{slug}" checked onchange="_toggleSpaghetti(\'{slug}\')">'
        f' Show model forecast tracks</label>'
        f'<div class="track-legend spaghetti-legend" id="splegend-{slug}"></div>'
        f'<div class="sp-note">Latest run of each model (UTC), shown as published.</div>'
    ) if spaghetti else ''

    map_div = (
        f'<div class="track-map-wrap">'
        f'<div class="track-map" id="trmap-{slug}"></div>'
        f'<div class="track-map-skeleton" id="trskel-{slug}"><div class="skeleton-spinner"></div></div>'
        f'</div>'
        f'{spaghetti_toggle}'
    ) if track_points else (
        '<p style="color:var(--muted);font-size:0.82em;text-align:center;padding:8px 0">No track data available</p>')

    return f'{active_badge}{meta}{ibar}{legend}{map_div}{cone_img}{nhc_link}'


def render_dashboard_html(payloads, share_image=None, share_alt=None):
    """Render the dashboard from build_season_payload() results (no I/O here).
    `share_image` is the site-relative path of a generated share card; the
    static ace_preview.png is used without one."""
    now = datetime.now(timezone.utc)

    def storm_rows_html(storms):
        rows = []
        track_data = {}
        any_estimated = False
        for st in storms:
            name = st['name']
            ace = st['ace']
            pct = st['pct_of_season']
            wind = st['max_wind']
            cat = st['category']
            is_major = st['is_major']
            is_active = st['is_active']
            slug = st['slug']

            track_data[slug] = _storm_track_entry(st)

            landfall = st['landfall']
            if landfall:
                lf_cell = ' · '.join(f'{html_escape(loc)} ({html_escape(cat)})' for loc, cat in landfall)
                if st['landfall_estimated']:
                    any_estimated = True
                    lf_cell += (' <abbr class="lf-est" title="Estimated from the preliminary track; '
                                'NHC confirms landfalls in its post-season report">est.</abbr>')
            else:
                lf_cell = '<span class="dash-fish" data-tip="A storm that never made landfall and just pissed off fish">Fish Storm</span>'

            row_classes = 'storm-row'
            if is_major:
                row_classes += ' major'
            if is_active:
                row_classes += ' active-storm-row'

            active_dot = '<span class="active-pulse"></span> ' if is_active else ''
            panel_inner = _storm_panel_inner_html(st) + (
                f'<div class="storm-page-link"><a href="storm/{html_escape(st["page_slug"])}.html">Open {html_escape(name)} page &rarr;</a></div>')

            wind_cell = '—' if wind <= 0 else f"<span class='wind-val' data-kt='{wind}'>{wind}</span>"

            rows.append(
                f'<tr class="{row_classes}" id="storm-row-{slug}">'
                f'<td data-v="{html_escape(name)}"><button class="storm-name-btn" id="trbtn-{slug}" aria-expanded="false" aria-controls="trpanel-{slug}" onclick="toggleTrack(\'{slug}\')">'
                f'{active_dot}{html_escape(name)}<span class="storm-chevron">&#9658;</span></button>'
                f'<button class="storm-share-btn" type="button" data-tip="Copy link to this storm" '
                f'aria-label="Copy link to {html_escape(name)}" onclick="copyStormLink(event,\'{slug}\')">&#128279;</button></td>'
                f'<td data-v="{ace:.6f}">{ace:.1f}</td>'
                f'<td data-v="{pct:.4f}">{pct:.1f}%</td>'
                f'<td data-v="{wind}">{cat}</td>'
                f'<td data-v="{wind}">{wind_cell}</td>'
                f'<td class="lf-cell">{lf_cell}</td>'
                f'</tr>'
                f'<tr class="track-row" id="track-row-{slug}">'
                f'<td colspan="6"><div class="track-panel" id="trpanel-{slug}"><div class="track-inner">{panel_inner}</div></div></td>'
                f'</tr>'
            )
        note = ('<p class="table-note"><abbr class="lf-est">est.</abbr> Landfall estimated from the storm\'s '
                'preliminary track against coastlines. NHC confirms landfalls in its post-season Tropical '
                'Cyclone Report.</p>') if any_estimated else ''
        return '\n'.join(rows), track_data, note

    def insight_items_html(insights):
        return '\n'.join(f'<li>{i}</li>' for i in insights)

    sections = []
    all_track_data = {}
    all_pace_data = {}
    for bd in payloads:
        basin_key = bd['basin_key']
        current_ace = bd['ace_total']
        current_year = bd['year']
        normal = bd['normal_ace']
        pct_normal = bd['pct_of_normal']
        classification = bd['classification']
        named = bd['named_storms']
        hurricanes = bd['hurricanes']
        majors = bd['major_hurricanes']
        preseason = bd['preseason']

        if preseason:
            lower_section = _preseason_html(basin_key, bd['yearly_totals'], current_year)
        else:
            storm_html, track_data, landfall_note = storm_rows_html(bd['storms'])
            all_track_data.update(track_data)
            lower_section = f'''
      <h3>Storm Breakdown</h3>
      <div class="table-wrap">
        <table>
          <thead><tr>
            <th class="sort-th"><button type="button" class="sort-btn" onclick="sortDash(this,0,'s')">Storm <span class="sa" aria-hidden="true"></span></button></th>
            <th class="sort-th" aria-sort="descending"><button type="button" class="sort-btn" onclick="sortDash(this,1,'n')">ACE <span class="sa" aria-hidden="true">&#9660;</span></button></th>
            <th class="sort-th"><button type="button" class="sort-btn" onclick="sortDash(this,2,'n')">% <span class="sa" aria-hidden="true"></span></button></th>
            <th class="sort-th"><button type="button" class="sort-btn" onclick="sortDash(this,3,'n')">Category <span class="sa" aria-hidden="true"></span></button></th>
            <th class="sort-th"><button type="button" class="sort-btn" onclick="sortDash(this,4,'n')"><span class="wind-th-label" data-kt-label="Wind (kt)" data-mph-label="Wind (mph)" data-kmh-label="Wind (km/h)">Wind (kt)</span> <span class="sa" aria-hidden="true"></span></button></th>
            <th>Landfall</th>
          </tr></thead>
          <tbody id="storm-{basin_key}">
            {storm_html}
          </tbody>
          <tfoot>
            <tr class="total-row"><td><b>TOTAL</b></td><td><b>{current_ace:.1f}</b></td><td><b>100%</b></td><td></td><td></td><td></td></tr>
          </tfoot>
        </table>
      </div>
      {landfall_note}

      <h3>Season Insights</h3>
      <ul class="insights">{insight_items_html(bd['insights'])}</ul>
      {_records_in_play_html(bd['records_in_play'], basin_key, bd['basin_name'], current_year)}
      {_season_projection_html(bd['projection'])}'''

        gauge_pct = min(pct_normal, 200)

        if preseason:
            stats_grid = f'''
      <div class="stats-grid">
        <div class="stat-box ace-total">
          <div class="stat-label">Season ACE</div>
          <div class="stat-value">0.0</div>
          <div class="stat-sub">Season underway — no storms yet</div>
          <div class="gauge"><div class="gauge-fill" style="width:0%"></div></div>
        </div>
        <div class="stat-box"><div class="stat-label">Named Storms</div><div class="stat-value">0</div></div>
        <div class="stat-box"><div class="stat-label">Hurricanes</div><div class="stat-value">0</div></div>
        <div class="stat-box major-box"><div class="stat-label">Major Hurricanes</div><div class="stat-value">0</div></div>
      </div>'''
        else:
            rank, total_seasons = bd['rank'], bd['total_seasons']
            stats_grid = f'''
      <div class="stats-grid">
        <div class="stat-box ace-total">
          <div class="stat-label">Season ACE <span class="prelim" title="Preliminary: from NHC's real-time best track, revised in the post-season HURDAT2 release">preliminary</span></div>
          <div class="stat-value">{current_ace:.1f}</div>
          <div class="stat-sub">{pct_normal:.0f}% of normal ({normal})</div>
          <div class="gauge"><div class="gauge-fill" style="width:{gauge_pct/2}%"></div></div>
        </div>
        <div class="stat-box"><div class="stat-label">Classification</div><div class="stat-value small">{classification}</div></div>
        <div class="stat-box"><div class="stat-label">Named Storms</div><div class="stat-value">{named}</div></div>
        <div class="stat-box"><div class="stat-label">Hurricanes</div><div class="stat-value">{hurricanes}</div></div>
        <div class="stat-box major-box"><div class="stat-label">Major Hurricanes</div><div class="stat-value">{majors}</div></div>
        <div class="stat-box"><div class="stat-label">Rank (since {START_YEAR})</div><div class="stat-value">#{rank}<span class="stat-sub"> of {total_seasons}</span></div></div>
      </div>'''

        disturbances   = bd['disturbances']
        nhc_alert      = (_developing_alert_html(bd.get('developing_systems'))
                          + _nhc_alert_html(disturbances))
        stale_banner   = _stale_data_banner_html() if bd['is_backup'] else ''

        ace_pace = bd['ace_pace']
        pace_section = _ace_pace_html(ace_pace, basin_key)
        if ace_pace:
            all_pace_data[basin_key] = ace_pace

        sections.append(f'''
    <div class="basin-card{' active' if not sections else ''}" id="{basin_key}">
      <h2>{html_escape(bd['basin_name'])} — {current_year} Season</h2>
      {_season_progress_html(basin_key, current_year)}
      {stale_banner}
      {nhc_alert}
      {_data_as_of_html(bd['data_as_of'], disturbances[0]['issued'] if disturbances else '')}
      {stats_grid}
      {pace_section}
      {lower_section}
    </div>''')

    # Escape </ sequences so the JSON blobs can't break out of the <script> tag
    _track_json = json.dumps(all_track_data).replace('</', '<\\/')
    _pace_json = json.dumps(all_pace_data).replace('</', '<\\/')

    season_year = max((bd['year'] for bd in payloads), default=datetime.now(timezone.utc).year)
    page_title = f'{season_year} Hurricane Season ACE Tracker: Atlantic &amp; East Pacific | aceofcanes.com'
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="Track the {season_year} Atlantic and Eastern Pacific hurricane season ACE (Accumulated Cyclone Energy) in real time. Updated every 3 hours during hurricane season.">
<meta name="theme-color" content="#4fc3f7">
<link rel="canonical" href="https://aceofcanes.com/">
<link rel="alternate" type="application/rss+xml" title="Ace of Canes storm feed" href="feed.xml">
<meta property="og:type" content="website">
<meta property="og:site_name" content="ACE Tracker">
<meta property="og:url" content="https://aceofcanes.com/">
<meta property="og:title" content="{page_title}">
<meta property="og:description" content="Track Accumulated Cyclone Energy (ACE) for the {season_year} Atlantic and Eastern Pacific hurricane seasons in real time. Updated every 3 hours from official NOAA data.">
{_share_image_meta(share_alt or SHARE_IMAGE_ALT, share_image or 'ace_preview.png')}
<meta name="twitter:title" content="{page_title}">
<meta name="twitter:description" content="Track Accumulated Cyclone Energy (ACE) for the {season_year} Atlantic and Eastern Pacific hurricane seasons in real time. Updated every 3 hours from official NOAA data.">
<meta name="twitter:image" content="https://aceofcanes.com/{html_escape(share_image or 'ace_preview.png')}">
<link rel="icon" type="image/png" href="ace.png">
<link rel="stylesheet" href="vendor/leaflet-1.9.4/leaflet.css" integrity="sha384-sHL9NAb7lN7rfvG5lfHpm643Xkcjzp4jFvuavGOndn6pjVqS6ny56CAt3nsEVT4H" crossorigin="anonymous" media="print" onload="this.media='all'">
<noscript><link rel="stylesheet" href="vendor/leaflet-1.9.4/leaflet.css"></noscript>
<title>{page_title}</title>
<script>{THEME_INIT_JS}</script>
<style>
{BASE_CSS}
  .data-asof {{ text-align:center; color:var(--muted); font-size:0.8em; margin:0 0 10px; }}
  .data-asof time {{ color:var(--text); }}
  .build-time {{ color:var(--muted); font-size:0.85em; }}
  .prelim {{ font-size:0.72em; font-weight:600; text-transform:uppercase; letter-spacing:0.04em; color:var(--muted); border:1px solid var(--border); border-radius:4px; padding:0 4px; margin-left:4px; white-space:nowrap; }}
  .lf-est {{ font-size:0.85em; color:var(--muted); text-decoration:underline dotted; cursor:help; }}
  .table-note {{ font-size:0.75em; color:var(--muted); margin:6px 2px 0; }}
{NAV_CSS}
  .ace-explain {{ background:var(--box); border-radius:8px; padding:10px 14px; margin-bottom:14px; font-size:0.85em; }}
  .ace-explain summary {{ color:var(--accent); cursor:pointer; list-style:none; display:flex; align-items:center; gap:6px; min-height:44px; }}
  .ace-explain summary::-webkit-details-marker {{ display:none; }}
  .ace-explain summary::before {{ content:'ℹ'; font-size:1.1em; }}
  .ace-explain-hint {{ color:var(--muted); font-size:0.85em; }}
  .ace-explain p {{ color:var(--text); line-height:1.6; margin-top:8px; padding-top:8px; border-top:1px solid var(--border); }}
  .ace-explain p a, .ace-explain p a:visited {{ color:var(--accent); font-weight:600; text-decoration:underline; text-underline-offset:2px; }}
  .toggle {{ display:flex; justify-content:center; gap:8px; margin-bottom:16px; }}
  .toggle button {{ padding:8px 20px; border:1px solid var(--accent); background:transparent; color:var(--accent); border-radius:20px; cursor:pointer; font-size:0.9em; }}
  .toggle button.active {{ background:var(--accent); color:var(--bg); font-weight:bold; }}
  .basin-card {{ background:var(--card); border-radius:12px; padding:16px; margin-bottom:16px; display:none; }}
  .basin-card.active {{ display:block; }}
{HEADINGS_CSS}
  .nhc-alert {{ background:rgba(255,152,0,0.07); border:1px solid rgba(255,152,0,0.35); border-left:4px solid #ff9800; border-radius:8px; padding:10px 14px 8px; margin-bottom:14px; font-size:0.88em; }}
  [data-theme='light'] .nhc-alert {{ background:rgba(255,152,0,0.06); }}
  .nhc-alert-hdr {{ font-weight:700; color:#ff9800; margin-bottom:8px; font-size:0.95em; }}
  .nhc-dist {{ border-top:1px solid rgba(255,152,0,0.2); padding:7px 0 4px; }}
  .nhc-dist-area {{ font-weight:600; color:var(--text); margin-bottom:3px; }}
  .nhc-dist-desc {{ color:var(--muted); font-size:0.88em; line-height:1.4; margin-bottom:4px; }}
  .nhc-dist-chances {{ font-size:0.9em; }}
  .nhc-alert-foot {{ display:flex; justify-content:space-between; align-items:center; margin-top:8px; padding-top:6px; border-top:1px solid rgba(255,152,0,0.2); flex-wrap:wrap; gap:6px; }}
  .nhc-issued {{ color:var(--muted); font-size:0.82em; }}
  .nhc-alert-link {{ color:var(--accent); text-decoration:none; font-size:0.88em; font-weight:500; }}
  .nhc-alert-link:hover {{ text-decoration:underline; }}
  .stats-grid {{ display:flex; flex-wrap:wrap; gap:8px; }}
  .stat-box {{ background:var(--box); border-radius:8px; padding:10px; text-align:center; flex:1 1 100px; }}
  .stat-box.ace-total {{ flex:1 1 100%; }}
  .stat-label {{ color:var(--muted); font-size:0.75em; text-transform:uppercase; }}
  .stat-value {{ color:var(--text-strong); font-size:1.5em; font-weight:bold; }}
  .stat-value.small {{ font-size:1.1em; }}
  .stat-sub {{ color:var(--muted); font-size:0.75em; }}
  .major-box {{ border:1px solid var(--danger); }}
  .major-box .stat-value {{ color:var(--danger); }}
  .gauge {{ height:6px; background:var(--gauge-bg); border-radius:3px; margin-top:6px; }}
  .gauge-fill {{ height:100%; background:linear-gradient(90deg,var(--accent),var(--accent2),var(--danger)); border-radius:3px; transition:width 0.5s; }}
  .table-wrap {{ overflow-x:auto; background: linear-gradient(to right,var(--card) 20px,transparent 20px) left/20px 100%, linear-gradient(to left,var(--card) 20px,transparent 20px) right/20px 100%, linear-gradient(to right,rgba(0,0,0,0.18),transparent) left/16px 100%, linear-gradient(to left,rgba(0,0,0,0.18),transparent) right/16px 100%; background-repeat:no-repeat; background-attachment:local,local,scroll,scroll; }}
  table {{ width:100%; border-collapse:collapse; font-size:0.85em; }}
  th {{ background:var(--box); color:var(--accent); padding:8px 6px; text-align:left; position:sticky; top:0; }}
  th.sort-th {{ cursor:pointer; user-select:none; padding:10px 6px; }}
  .sort-btn {{ background:none; border:0; padding:0; font:inherit; color:inherit; cursor:pointer; text-align:inherit; white-space:inherit; }}
  th.sort-th:hover {{ color:var(--text-strong); }}
  .sa {{ font-size:0.7em; margin-left:2px; opacity:0.7; }}
  td {{ padding:6px; border-bottom:1px solid var(--border); color:var(--text); }}
  tr.major {{ background:var(--danger-bg); }}
  tr.major td {{ color:var(--danger-text); font-weight:bold; }}
  tr.total-row {{ background:var(--total-row); }}
  .insights {{ list-style:none; padding:0; }}
  .rip-list {{ list-style:none; padding:0; margin:0; }}
  .rip-item {{ display:flex; gap:10px; align-items:flex-start; background:var(--box); padding:8px 10px; margin:4px 0; border-radius:6px; font-size:0.85em; color:var(--text); }}
  .rip-badge {{ flex:none; font-size:0.72em; font-weight:700; text-transform:uppercase; letter-spacing:0.04em; padding:2px 7px; border-radius:10px; margin-top:1px; }}
  .rip-set {{ background:#c0392b; color:#fff; }}
  .rip-watch {{ background:#e67e22; color:#fff; }}
  .rip-share-btn {{ flex:none; margin-left:auto; background:none; border:none; color:var(--muted); cursor:pointer; font-size:0.95em; padding:0 2px; align-self:center; }}
  .rip-share-btn:hover {{ color:var(--accent); }}
  .rip-caption {{ font-size:0.75em; color:var(--muted); margin:4px 0 0; }}
  .insights li {{ background:var(--box); padding:8px 10px; margin:4px 0; border-radius:6px; font-size:0.85em; border-left:3px solid var(--accent); color:var(--text); }}
  .projection-widget {{ background:var(--box); border-radius:8px; padding:10px 12px; margin-top:6px; }}
  .projection-caption {{ color:var(--muted); font-size:0.78em; margin:0 0 8px; }}
  .proj-row {{ display:flex; justify-content:space-between; align-items:baseline; padding:5px 0; border-top:1px solid var(--border); font-size:0.88em; }}
  .proj-row:first-of-type {{ border-top:none; }}
  .proj-label {{ color:var(--text); }}
  .proj-threshold {{ color:var(--muted); font-size:0.85em; }}
  .proj-value {{ color:var(--text-strong); font-weight:bold; white-space:nowrap; }}
  .sources {{ background:var(--sources-bg); border-top:1px solid var(--border); margin-top:24px; padding:16px 12px; border-radius:8px; }}
  .sources h4 {{ color:var(--muted); font-size:0.8em; text-transform:uppercase; margin-bottom:8px; }}
  .sources a {{ color:var(--accent); text-decoration:none; font-size:0.78em; }}
  .sources a:hover {{ text-decoration:underline; }}
  .sources p {{ color:var(--muted-dark); font-size:0.75em; margin-top:8px; line-height:1.5; }}
  .sources ul {{ list-style:none; padding:0; margin:0; }}
  .sources li {{ color:var(--muted); font-size:0.78em; margin:4px 0; padding-left:12px; position:relative; }}
  .sources li::before {{ content:"•"; position:absolute; left:0; color:var(--accent); }}
  .sources code {{ font-size:0.9em; background:var(--box); padding:1px 4px; border-radius:3px; }}
  .disclaimer {{ margin-top:12px; padding:10px 12px; border-radius:6px; border-left:3px solid var(--muted); font-size:0.75em; color:var(--muted); line-height:1.5; }}
  .kofi-link {{ text-align:center; margin-top:14px; font-size:0.78em; }}
  .kofi-link a {{ color:var(--muted); text-decoration:none; }}
  .kofi-link a:hover {{ color:var(--accent); }}
  .season-prog {{ margin:-4px 0 14px; }}
  .season-prog-label {{ color:var(--muted); font-size:0.8em; margin-bottom:5px; text-align:center; }}
  .season-prog-track {{ height:6px; background:var(--gauge-bg); border-radius:3px; }}
  .season-prog-fill {{ height:100%; background:linear-gradient(90deg,var(--accent),var(--accent2)); border-radius:3px; transition:width 0.5s; }}
  .season-prog.offseason {{ color:var(--muted); font-size:0.8em; text-align:center; margin:-4px 0 14px; }}
  .preseason-notice {{ background:var(--box); border-radius:8px; padding:14px 16px; margin:12px 0; border-left:4px solid var(--accent); font-size:0.9em; color:var(--text); text-align:center; line-height:1.5; }}
  .sim-link {{ color:var(--accent); text-decoration:none; }}
  .sim-link:hover {{ text-decoration:underline; }}
  @media(min-width:768px) {{ body {{ max-width:900px; margin:0 auto; padding:24px; }} }}
  @media(min-width:1100px) {{ body {{ max-width:1100px; }} }}
  .storm-name-btn {{ background:none; border:none; color:var(--accent); cursor:pointer; font-size:inherit; padding:0; display:inline-flex; align-items:center; gap:4px; white-space:nowrap; text-decoration:underline dotted; }}
  .storm-name-btn:hover {{ color:var(--accent2); }}
  .storm-chevron {{ font-size:0.7em; display:inline-block; transition:transform 0.2s; color:var(--muted); margin-left:2px; }}
  .storm-name-btn.open .storm-chevron {{ transform:rotate(90deg); }}
  .storm-share-btn {{ background:none; border:none; color:var(--muted); cursor:pointer; font-size:0.85em; padding:0 0 0 8px; vertical-align:middle; }}
  .storm-share-btn:hover {{ color:var(--accent); }}
  .storm-row.storm-highlight {{ animation:storm-highlight-flash 2.5s ease-out; }}
  @keyframes storm-highlight-flash {{ 0%,15% {{ background:var(--accent); }} 100% {{ background:transparent; }} }}
  .lf-cell {{ font-size:0.85em; color:var(--text); }}
  .dash-fish {{ color:var(--muted); font-style:italic; cursor:help; }}
  .global-tip {{ display:none; position:fixed; top:0; left:0; background:var(--box); color:var(--text); border:1px solid var(--border); padding:5px 11px; border-radius:6px; font-size:0.82em; pointer-events:none; z-index:9999; max-width:320px; line-height:1.4; box-shadow:0 2px 8px rgba(0,0,0,0.4); }}
  .active-pulse {{ display:inline-block; width:7px; height:7px; border-radius:50%; background:#4caf50; box-shadow:0 0 0 0 rgba(76,175,80,0.7); animation:trpulse 1.5s infinite; flex-shrink:0; }}
  @keyframes trpulse {{ 0%{{box-shadow:0 0 0 0 rgba(76,175,80,0.7);}} 70%{{box-shadow:0 0 0 6px rgba(76,175,80,0);}} 100%{{box-shadow:0 0 0 0 rgba(76,175,80,0);}} }}
  tr.active-storm-row {{ border-left:3px solid #4caf50; }}
{STORM_PANEL_CSS}
  .pace-chart-wrap {{ position:relative; height:240px; margin:12px 0 4px; }}
  .pace-stats-mini {{ display:grid; grid-template-columns:repeat(3,1fr); gap:8px; margin:10px 0 4px; }}
  .pace-caption {{ color:var(--muted); font-size:0.78em; text-align:center; margin-top:2px; }}
  @media(min-width:768px) {{ .pace-chart-wrap {{ height:300px; }} }}
{CONE_CSS}
  .storm-page-link {{ font-size:0.85em; text-align:right; margin-top:8px; }}
  .storm-page-link a {{ color:var(--accent); text-decoration:none; }}
  .storm-page-link a:hover {{ text-decoration:underline; }}
</style>
</head>
<body>
<div class="header">
  <h1><img src="ace.png" class="logo" alt="" aria-hidden="true"> Hurricane ACE Dashboard</h1>
  <div class="header-actions">
    <button class="unit-btn" id="unitBtn" onclick="toggleWindUnit()" title="Wind speed unit" aria-label="Wind speed unit: kt">kt</button>
    <button class="theme-btn" id="themeBtn" onclick="toggleTheme()" aria-label="Toggle light and dark theme">☀</button>
  </div>
</div>
<div class="nav-link"><a href="history.html">📊 Season History ({START_YEAR}–present)</a><a href="records.html">🏆 Records</a><a href="what-is-ace.html">❓ What is ACE?</a></div>
<details class="ace-explain">
  <summary>What is ACE? <span class="ace-explain-hint">(tap to expand)</span></summary>
  <p>Accumulated Cyclone Energy (ACE) measures total hurricane season activity by combining storm intensity and duration. A major hurricane that lasts two weeks contributes far more than a brief tropical storm. NOAA uses seasonal ACE totals to classify years as <b>Below Normal</b> (&lt;73), <b>Near Normal</b> (73–126), <b>Above Normal</b> (126–159), or <b>Extremely Active</b> (159+). <a href="what-is-ace.html">More on ACE, plus a calculator →</a></p>
</details>
<div class="toggle">
  <button class="active" aria-pressed="true" onclick="show('atlantic',this)">Atlantic</button>
  <button aria-pressed="false" onclick="show('pacific',this)">E/C Pacific</button>
</div>
{''.join(sections)}
<div class="sources">
  <h4>Data Sources</h4>
  <ul>
    <li><a href="https://www.nhc.noaa.gov/data/#hurdat" target="_blank" rel="noopener noreferrer">NOAA HURDAT2</a> — Historical best-track data (1991–present) for storm tracks, wind speeds, and ACE calculations</li>
    <li><a href="https://www.nhc.noaa.gov/data/#hurdat" target="_blank" rel="noopener noreferrer">NHC Real-time Best Track</a> — Current season preliminary storm data fetched via Tropycal (<code>include_btk=True</code>); updated continuously during active storms</li>
    <li><a href="https://www.cpc.ncep.noaa.gov/products/outlooks/background_information.shtml" target="_blank" rel="noopener noreferrer">NOAA CPC</a> — Season classification thresholds and 1991–2020 climatological normals</li>
  </ul>
  <p>ACE (Accumulated Cyclone Energy) is calculated at 6-hourly synoptic times (0000/0600/1200/1800 UTC) for systems with status TS, HU, or SS and wind ≥34 kt — extratropical (EX) phases are excluded per NHC methodology. Formula: ACE = Σ(V²<sub>max</sub>) × 10⁻⁴. Categories use the Saffir-Simpson scale in knots.</p>
  <p><b>Basin note:</b> The East &amp; Central Pacific tab combines both the Eastern Pacific (NHC, east of 140°W) and Central Pacific (CPHC, 140°W–180°) basins, consistent with the NOAA HURDAT2 Northeast &amp; North Central Pacific dataset. NHC tracks these separately on their <a href="https://www.nhc.noaa.gov/data/tcr/" target="_blank" rel="noopener noreferrer">TCR pages</a> (epac / cpac).</p>
  <p class="disclaimer">⚠️ This site is maintained by a hurricane data enthusiast — not a meteorologist, forecaster, or weather professional of any kind. I just love the data. All information is sourced directly from official NOAA/NHC databases. For official forecasts, watches, warnings, and life-safety information, always refer to the <a href="https://www.nhc.noaa.gov/" target="_blank" rel="noopener noreferrer">National Hurricane Center</a>.</p>
  <p class="build-time">Page built {now.strftime('%B %d, %Y at %H:%M UTC')}. Updates every 3 hours. The data-as-of line above each basin's numbers shows how current the storm data is.</p>
  <p class="kofi-link"><a href="https://ko-fi.com/aceofcanes" target="_blank" rel="noopener noreferrer">☕ Support this project on Ko-fi</a></p>
</div>
<script>
function _relTimes(){{
  var now=Date.now();
  document.querySelectorAll('.rel-time[data-ts]').forEach(function(el){{
    var t=Date.parse(el.getAttribute('data-ts'));
    if(isNaN(t))return;
    var m=Math.max(0,Math.round((now-t)/60000)),s;
    if(m<1)s='just now';
    else if(m<60)s=m+' min ago';
    else if(m<48*60){{var h=Math.round(m/60);s=h+(h===1?' hour':' hours')+' ago';}}
    else s=Math.round(m/1440)+' days ago';
    el.textContent='('+s+')';
  }});
}}
_relTimes();setInterval(_relTimes,60000);
function show(id,btn) {{
  document.querySelectorAll('.basin-card').forEach(c=>c.classList.remove('active'));
  document.querySelectorAll('.toggle button').forEach(b=>{{b.classList.remove('active');b.setAttribute('aria-pressed','false');}});
  document.getElementById(id)?.classList.add('active');
  btn.classList.add('active');
  btn.setAttribute('aria-pressed','true');
  try{{history.replaceState(null,'','#'+id);}}catch(e){{}}
  _renderPaceChart(id);
}}
function toggleTheme() {{
  var h=document.documentElement;
  var light=h.getAttribute('data-theme')==='light';
  h.setAttribute('data-theme',light?'dark':'light');
  try{{localStorage.setItem('ace-theme',light?'dark':'light');}}catch(e){{}}
  document.getElementById('themeBtn').textContent=light?'☀':'☾';document.getElementById('themeBtn').setAttribute('aria-label',document.documentElement.getAttribute('data-theme')==='light'?'Switch to dark mode':'Switch to light mode');
  _restylePaceCharts();
}}
{WIND_JS}
function _copyText(text,done) {{
  if(navigator.clipboard&&navigator.clipboard.writeText) {{
    navigator.clipboard.writeText(text).then(function(){{done(true);}},function(){{done(false);}});
  }} else {{
    try {{
      var ta=document.createElement('textarea');
      ta.value=text;ta.style.position='fixed';ta.style.opacity='0';
      document.body.appendChild(ta);ta.select();document.execCommand('copy');document.body.removeChild(ta);
      done(true);
    }} catch(err) {{ done(false); }}
  }}
}}
function _flashBtn(btn,ok) {{
  var prev=btn.innerHTML;
  btn.innerHTML=ok?'&#10003;':'&#9888;';
  setTimeout(function(){{btn.innerHTML=prev;}},1400);
}}
function copyStormLink(e,slug) {{
  var url=location.origin+location.pathname+'#storm-row-'+slug;
  var btn=e.currentTarget;
  _copyText(url,function(ok){{_flashBtn(btn,ok);}});
}}
function shareRecord(e) {{
  var btn=e.currentTarget,text=btn.getAttribute('data-share-text'),url=btn.getAttribute('data-share-url');
  var viaClipboard=function(){{_copyText(text+' '+url,function(ok){{_flashBtn(btn,ok);}});}};
  if(navigator.share&&window.matchMedia&&window.matchMedia('(pointer:coarse)').matches) {{
    navigator.share({{text:text,url:url}}).catch(function(err){{if(!err||err.name!=='AbortError')viaClipboard();}});
  }} else {{
    viaClipboard();
  }}
}}
document.addEventListener('DOMContentLoaded',function() {{
  document.getElementById('themeBtn').textContent=document.documentElement.getAttribute('data-theme')==='light'?'☾':'☀';document.getElementById('themeBtn').setAttribute('aria-label',document.documentElement.getAttribute('data-theme')==='light'?'Switch to dark mode':'Switch to light mode');
  applyWindUnit();
  var hash=location.hash.replace('#','');
  var match=[].slice.call(document.querySelectorAll('.toggle button')).filter(function(b){{return(b.getAttribute('onclick')||'').indexOf("'"+hash+"'")>=0;}})[0];
  if(match) {{
    match.click();
  }} else if(hash.indexOf('storm-row-')===0) {{
    var row=document.getElementById(hash);
    if(row) {{
      var card=row.closest('.basin-card');
      var basinBtn=card&&[].slice.call(document.querySelectorAll('.toggle button')).filter(function(b){{return(b.getAttribute('onclick')||'').indexOf("'"+card.id+"'")>=0;}})[0];
      if(basinBtn)basinBtn.click();
      toggleTrack(hash.slice('storm-row-'.length));
      setTimeout(function(){{
        row.scrollIntoView({{behavior:'smooth',block:'center'}});
        row.classList.add('storm-highlight');
        setTimeout(function(){{row.classList.remove('storm-highlight');}},2500);
      }},60);
    }}
  }}
  var activeCard=document.querySelector('.basin-card.active');
  if(activeCard)_renderPaceChart(activeCard.id);
}});
var _ds={{}};
function sortDash(th,col,type){{
  var card=th.closest('.basin-card');
  var tbody=card.querySelector('tbody');
  var key=card.id+col;
  var asc=_ds[key]===undefined?false:!_ds[key];
  _ds[key]=asc;
  var rows=Array.from(tbody.querySelectorAll('tr.storm-row'));
  rows.sort(function(a,b){{
    var av=a.cells[col]?a.cells[col].getAttribute('data-v'):'';
    var bv=b.cells[col]?b.cells[col].getAttribute('data-v'):'';
    if(type==='n'){{av=parseFloat(av)||0;bv=parseFloat(bv)||0;}}
    if(av<bv)return asc?-1:1;
    if(av>bv)return asc?1:-1;
    return 0;
  }});
  rows.forEach(function(r){{
    tbody.appendChild(r);
    var slug=r.id.replace('storm-row-','');
    var tr=document.getElementById('track-row-'+slug);
    if(tr)tbody.appendChild(tr);
  }});
  card.querySelectorAll('.sort-th .sa').forEach(function(s,i){{s.innerHTML=i===col?(asc?'&#9650;':'&#9660;'):''}});
  card.querySelectorAll('th.sort-th').forEach(function(h,i){{if(i===col)h.setAttribute('aria-sort',asc?'ascending':'descending');else h.removeAttribute('aria-sort');}});
}}
var ACE_TRACKS={_track_json};
var ACE_PACE={_pace_json};
var _paceCharts={{}};
function _paceColors(){{
  var s=getComputedStyle(document.documentElement);
  var g=function(v){{return s.getPropertyValue(v).trim();}};
  return {{accent:g('--accent'),accent2:g('--accent2'),muted:g('--muted'),mutedDark:g('--muted-dark'),border:g('--border'),last:g('--pace-last')}};
}}
function _hexToRgba(hex,a){{
  var h=hex.replace('#','');
  if(h.length===3)h=h[0]+h[0]+h[1]+h[1]+h[2]+h[2];
  var r=parseInt(h.substring(0,2),16),g=parseInt(h.substring(2,4),16),b=parseInt(h.substring(4,6),16);
  return 'rgba('+r+','+g+','+b+','+a+')';
}}
{LIB_MISSING_JS}
function _renderPaceChart(basinKey){{
  if(_paceCharts[basinKey])return;
  var d=ACE_PACE[basinKey];
  var el=document.getElementById('pace-canvas-'+basinKey);
  if(!d||!el)return;
  if(typeof Chart==='undefined'){{el.style.display='none';_libMissing(el.parentNode,'Chart unavailable right now. The numbers below are unaffected.');return;}}
  var colors=_paceColors();
  var datasets=[
    {{label:'p75',data:d.climatology_p75,borderWidth:0,pointRadius:0,fill:false}},
    {{label:'p25',data:d.climatology_p25,borderWidth:0,pointRadius:0,fill:'-1',backgroundColor:_hexToRgba(colors.accent2,0.15)}},
    {{label:'Historical average',data:d.climatology_mean,borderColor:colors.muted,borderWidth:2,borderDash:[5,5],pointRadius:0}}
  ];
  if(d.last_season){{
    datasets.push({{label:'Last season',data:d.last_season,borderColor:colors.last,borderWidth:2.5,pointRadius:0}});
  }}
  datasets.push({{label:'This season',data:d.current_season,borderColor:colors.accent,borderWidth:3,pointRadius:0,spanGaps:false}});
  _paceCharts[basinKey]=new Chart(el,{{
    type:'line',
    data:{{labels:d.day_labels,datasets:datasets}},
    options:{{
      responsive:true,maintainAspectRatio:false,
      interaction:{{mode:'index',intersect:false}},
      plugins:{{
        legend:{{display:true,position:'top',labels:{{color:colors.muted,boxWidth:14,boxHeight:2,font:{{size:11}},filter:function(item){{return item.text!=='p75'&&item.text!=='p25';}}}}}},
        tooltip:{{filter:function(item){{return item.dataset.label!=='p75'&&item.dataset.label!=='p25';}}}}
      }},
      scales:{{
        x:{{ticks:{{color:colors.muted,autoSkip:true,maxTicksLimit:8}},grid:{{display:false}}}},
        y:{{ticks:{{color:colors.muted}},grid:{{color:colors.border}}}}
      }}
    }}
  }});
  _updatePaceStats(basinKey,d);
}}
function _updatePaceStats(basinKey,d){{
  var todate=d.current_season[d.today_index]||0;
  var normal=d.climatology_mean[d.today_index]||0;
  // normal===0 this early in the season doesn't mean "on pace" if there's
  // already ACE this season — it means the ratio isn't meaningful yet.
  var pctText;
  if(normal>0){{pctText=(todate/normal*100).toFixed(0)+'%';}}
  else if(todate>0){{pctText='—';}}
  else{{pctText='0%';}}
  var elT=document.getElementById('pace-todate-'+basinKey);
  var elN=document.getElementById('pace-normal-'+basinKey);
  var elP=document.getElementById('pace-pct-'+basinKey);
  if(elT)elT.textContent=todate.toFixed(1);
  if(elN)elN.textContent=normal.toFixed(1);
  if(elP)elP.textContent=pctText;
}}
function _restylePaceCharts(){{
  var colors=_paceColors();
  Object.keys(_paceCharts).forEach(function(basinKey){{
    var chart=_paceCharts[basinKey];
    chart.data.datasets.forEach(function(ds){{
      if(ds.label==='p25')ds.backgroundColor=_hexToRgba(colors.accent2,0.15);
      else if(ds.label==='Historical average')ds.borderColor=colors.muted;
      else if(ds.label==='Last season')ds.borderColor=colors.last;
      else if(ds.label==='This season')ds.borderColor=colors.accent;
    }});
    chart.options.plugins.legend.labels.color=colors.muted;
    chart.options.scales.x.ticks.color=colors.muted;
    chart.options.scales.y.ticks.color=colors.muted;
    chart.options.scales.y.grid.color=colors.border;
    chart.update();
  }});
}}
{TRACK_MAP_JS}
</script>
<script src="vendor/leaflet-1.9.4/leaflet.js" integrity="sha384-cxOPjt7s7Iz04uaHJceBmS+qpjv2JkIHNVcuOrM+YHwZOmJGBXI00mdUXEq65HTH" crossorigin="anonymous"></script>
<script src="vendor/chart.js-4.5.1/chart.umd.min.js" integrity="sha384-jb8JQMbMoBUzgWatfe6COACi2ljcDdZQ2OxczGA3bGNeWe+6DChMTBJemed7ZnvJ" crossorigin="anonymous"></script>
<div id="global-tip" class="global-tip"></div>
<script>
(function(){{
  var tip=document.getElementById('global-tip');
  function posFromEvent(e){{
    if(e.touches&&e.touches[0])return {{x:e.touches[0].clientX,y:e.touches[0].clientY}};
    if(typeof e.clientX==='number'&&(e.clientX||e.clientY))return {{x:e.clientX,y:e.clientY}};
    var r=e.currentTarget.getBoundingClientRect();
    return {{x:r.left+r.width/2,y:r.top}};
  }}
  function move(e){{
    var p=posFromEvent(e),w=tip.offsetWidth,h=tip.offsetHeight;
    var x=Math.min(p.x+14,window.innerWidth-w-8);
    var y=Math.max(p.y-h-8,8);
    tip.style.transform='translate('+x+'px,'+y+'px)';
  }}
  function show(e){{var t=e.currentTarget.getAttribute('data-tip');if(!t)return;tip.textContent=t;tip.style.display='block';move(e);}}
  function hide(){{tip.style.display='none';}}
  document.querySelectorAll('[data-tip]').forEach(function(el){{
    el.addEventListener('mouseenter',show);
    el.addEventListener('mousemove',move);
    el.addEventListener('mouseleave',hide);
    el.addEventListener('touchstart',show,{{passive:true}});
    el.addEventListener('touchend',hide);
    el.addEventListener('focus',show);
    el.addEventListener('blur',hide);
  }});
}})();
</script>
<!-- Cloudflare Web Analytics --><script defer src='https://static.cloudflareinsights.com/beacon.min.js' data-cf-beacon='{{"token": "775dfcf117b94ff59e3c118c330d02aa"}}'></script><!-- End Cloudflare Web Analytics -->
</body>
</html>'''
    return html



# ===============================================================================
# FULL HISTORY PAGE
# ===============================================================================

def generate_history_html(basin_data):
    """Generate a historical seasons summary page (all seasons since START_YEAR)."""
    now = datetime.now(timezone.utc)

    def _badge_class(ace_val, basin_key):
        c = get_noaa_classification(ace_val, basin_key)
        if 'Extreme' in c:
            return 'extreme', c
        if 'Above' in c:
            return 'above', c
        if 'Below' in c:
            return 'below', c
        return 'near', c

    basin_sections = []
    all_decades = set()
    for bd in basin_data:
        if not bd:
            continue
        basin = BASINS[bd['basin_key']]
        current = bd['current']
        yearly_totals = bd['yearly_totals']
        yearly_stats = bd.get('yearly_stats')
        current_year = current['year']
        normal = basin['normal_ace']

        # Per-storm NHC report links, keyed by storm id. The in-progress
        # season's storm list comes from current-season details (keyed by
        # name), so its storms are also looked up by name.
        report_urls = dict(bd.get('tcr_reports') or {})
        for storm in bd.get('historical_storms') or []:
            if storm['year'] == current_year and storm.get('id') in report_urls:
                report_urls[storm['name']] = report_urls[storm['id']]

        # Build per-year data from yearly_stats (HURDAT2 historical)
        years_data = {}
        if yearly_stats:
            for year, stats in yearly_stats.items():
                years_data[year] = {
                    'ace': round(stats['ace'], 1),
                    'named': stats['named_storms'],
                    'hurricanes': stats['hurricanes'],
                    'majors': stats['major_hurricanes'],
                    'leader': stats.get('ace_leader') or '—',
                    'storms_list': stats.get('storms_list', []),
                }
        else:
            for year, ace in yearly_totals.items():
                years_data[year] = {
                    'ace': round(ace, 1),
                    'named': '—', 'hurricanes': '—', 'majors': '—', 'leader': '—',
                    'storms_list': [],
                }

        # Override current year with live data (more up-to-date than HURDAT2)
        details = current.get('storm_details', {})
        current_storms = current.get('storms', {})
        current_ace = round(current['total'], 1)
        named = len(details)
        hurricanes = sum(1 for d in details.values() if d.get('max_wind', 0) >= 64)
        majors = sum(1 for d in details.values() if d.get('max_wind', 0) >= 96)
        leader = max(current_storms, key=current_storms.get) if current_storms else '—'
        # Add current year row if season is active or has storm activity
        today = datetime.now(timezone.utc).date()
        if bd['basin_key'] == 'atlantic':
            _season_start = datetime(current_year, 6, 1).date()
        else:
            _season_start = datetime(current_year, 5, 15).date()
        _season_end = datetime(current_year, 11, 30).date()
        _in_active_season = _season_start <= today <= _season_end and current_year == datetime.now(timezone.utc).year
        if current_ace > 0 or named > 0 or _in_active_season:
            current_storms_list = sorted(
                [{'name': n, 'ace': round(d.get('ace', 0), 2),
                  'category': get_category(d.get('max_wind', 0)), 'max_wind': d.get('max_wind', 0),
                  'landfall': d.get('landfall', [])}
                 for n, d in details.items()
                 if get_category(d.get('max_wind', 0)) != 'TD'],
                key=lambda x: x['ace'], reverse=True
            )
            years_data[current_year] = {
                'ace': current_ace,
                'named': named,
                'hurricanes': hurricanes,
                'majors': majors,
                'leader': leader,
                'active': True,
                'storms_list': current_storms_list,
            }

        # Compute ACE rank and top-5
        ranked = sorted(years_data.items(), key=lambda x: x[1]['ace'], reverse=True)
        ranks = {year: i + 1 for i, (year, _) in enumerate(ranked)}
        top5_years = {year for year, _ in ranked[:5]}
        total_seasons = len(years_data)
        max_ace = max(d['ace'] for d in years_data.values()) if years_data else 1

        # Average row values (using official NOAA 1991-2020 normals from BASINS config)
        avg_ace = normal
        avg_pct = 100
        avg_named = basin['avg_named_storms']
        avg_hurr = basin['avg_hurricanes']
        avg_major = basin['avg_major_hurricanes']

        # Classification sort key helper
        def _csort(bc):
            return {'below': 0, 'near': 1, 'above': 2, 'extreme': 3}.get(bc, 1)

        prelim_html = (' <span class="prelim" title="Preliminary: from NHC\'s real-time best track, '
                       'revised in the post-season HURDAT2 release">preliminary</span>')

        # Build table rows (year descending default)
        rows = []
        for year in sorted(years_data.keys(), reverse=True):
            d = years_data[year]
            ace = d['ace']
            pct = round(ace / normal * 100) if normal > 0 else 0
            bc, classification = _badge_class(ace, bd['basin_key'])
            rank = ranks[year]
            is_active = d.get('active', False)
            is_top5 = year in top5_years
            ace_bar_pct = round(ace / max_ace * 100, 1)
            row_cls = f'row-{bc}'
            if is_active:
                row_cls += ' row-current'
            if is_top5:
                row_cls += ' row-top5'
            active_label = ' <span class="active-dot" title="Season in progress">&#9679;</span>' if is_active else ''
            named_v = d['named'] if d['named'] != '—' else 0
            hurr_v = d['hurricanes'] if d['hurricanes'] != '—' else 0
            major_v = d['majors'] if d['majors'] != '—' else 0
            yr_key = f'{bd["basin_key"]}-yr-{year}'
            storm_list_html = _year_storm_list_html(d.get('storms_list', []), report_urls)
            tcr_html = _nhc_tcr_links_html(year, bd['basin_key'], is_active)
            decade = _decade_label(year)
            all_decades.add(decade)
            lfshare_html = _landfall_share_html(d.get('storms_list', []))
            rows.append(
                f'<tr class="{row_cls} yr-data-row" id="{yr_key}" data-decade="{decade}">'
                f'<td data-v="{year}" style="white-space:nowrap">'
                f'<button class="yr-expand-btn" id="yrbtn-{yr_key}" aria-expanded="false" aria-controls="yrpanel-{yr_key}" onclick="toggleYear(\'{yr_key}\')">'
                f'<b>{year}</b>{active_label}<span class="yr-chevron">&#9658;</span></button></td>'
                f'<td data-v="{ace:.4f}"><b>{ace:.1f}</b>{prelim_html if is_active else ""}<div class="ace-bar"><div class="ace-bar-fill" style="width:{ace_bar_pct}%"></div></div></td>'
                f'<td data-v="{pct}">{pct}%</td>'
                f'<td data-v="{_csort(bc)}"><span class="badge badge-{bc}">{classification}</span></td>'
                f'<td data-v="{named_v}">{d["named"]}</td>'
                f'<td data-v="{hurr_v}">{d["hurricanes"]}</td>'
                f'<td data-v="{major_v}">{d["majors"]}</td>'
                f'<td data-v="{html_escape(str(d["leader"]))}">{html_escape(str(d["leader"]))}</td>'
                f'<td data-v="{rank}">#{rank}&nbsp;/&nbsp;{total_seasons}</td>'
                f'</tr>'
                f'<tr class="yr-expand-row" id="yr-xrow-{yr_key}">'
                f'<td colspan="9"><div class="yr-panel" id="yrpanel-{yr_key}">'
                f'<div class="yr-panel-inner">{lfshare_html}{storm_list_html}{tcr_html}</div>'
                f'</div></td></tr>'
            )

        # Average row (goes in tfoot, not sorted)
        avg_bar_pct = round(avg_ace / max_ace * 100, 1)
        avg_row = (
            f'<tr class="row-avg">'
            f'<td>Avg (1991–2020)</td>'
            f'<td>{avg_ace:.1f}<div class="ace-bar"><div class="ace-bar-fill" style="width:{avg_bar_pct}%"></div></div></td>'
            f'<td>{avg_pct}%</td>'
            f'<td><span class="badge badge-near">Near Normal</span></td>'
            f'<td>{avg_named}</td>'
            f'<td>{avg_hurr}</td>'
            f'<td>{avg_major}</td>'
            f'<td>—</td>'
            f'<td>—</td>'
            f'</tr>'
        )

        lf_avg = average_landfall_share(yearly_stats, current_year)
        lf_avg_note = (f'<p class="season-note">&#127965;&#65039; On average since {START_YEAR}, <b>{lf_avg}%</b> of a season\'s ACE '
                       f'came from storms that made landfall at tropical-storm strength or stronger. Open a season to see its split.</p>') if lf_avg is not None else ''
        basin_sections.append(f'''
    <div class="basin-card{' active' if not basin_sections else ''}" id="{bd['basin_key']}">
      <h2>{html_escape(basin['name'])} — All Seasons ({START_YEAR}–{current_year})</h2>
      <p class="season-note">{total_seasons} seasons &nbsp;·&nbsp; ● = currently active &nbsp;·&nbsp; <span style="border-left:3px solid #f9a825;padding-left:4px;">gold border</span> = top 5 all-time ACE &nbsp;·&nbsp; click headers to sort &nbsp;<span class="decade-count" aria-live="polite"></span></p>
      {lf_avg_note}
      <div class="table-wrap">
        <table class="hist-table">
          <thead>
            <tr>
              <th class="sort-th" aria-sort="descending"><button type="button" class="sort-btn" onclick="sortHist(this,0,'n')">Year <span class="sa" aria-hidden="true">▼</span></button></th>
              <th class="sort-th"><button type="button" class="sort-btn" onclick="sortHist(this,1,'n')">ACE <span class="sa" aria-hidden="true"></span></button></th>
              <th class="sort-th"><button type="button" class="sort-btn" onclick="sortHist(this,2,'n')">% Normal <span class="sa" aria-hidden="true"></span></button></th>
              <th class="sort-th"><button type="button" class="sort-btn" onclick="sortHist(this,3,'n')">Classification <span class="sa" aria-hidden="true"></span></button></th>
              <th class="sort-th"><button type="button" class="sort-btn" onclick="sortHist(this,4,'n')">Named <span class="sa" aria-hidden="true"></span></button></th>
              <th class="sort-th"><button type="button" class="sort-btn" onclick="sortHist(this,5,'n')">Hurr. <span class="sa" aria-hidden="true"></span></button></th>
              <th class="sort-th"><button type="button" class="sort-btn" onclick="sortHist(this,6,'n')">Major <span class="sa" aria-hidden="true"></span></button></th>
              <th class="sort-th"><button type="button" class="sort-btn" onclick="sortHist(this,7,'s')">ACE Leader <span class="sa" aria-hidden="true"></span></button></th>
              <th class="sort-th"><button type="button" class="sort-btn" onclick="sortHist(this,8,'n')">Rank <span class="sa" aria-hidden="true"></span></button></th>
            </tr>
          </thead>
          <tbody id="hist-{bd['basin_key']}">{''.join(rows)}</tbody>
          <tfoot>{avg_row}</tfoot>
        </table>
      </div>
    </div>''')

    decade_buttons = ''.join(
        f'<button type="button" data-decade="{dec}" aria-pressed="false" onclick="filterDecade(\'{dec}\')">{dec}</button>'
        for dec in sorted(all_decades)
    )
    decade_filter_html = (
        '<div class="decade-filter" role="group" aria-label="Filter seasons by decade">'
        '<span class="decade-filter-label">Decade:</span>'
        '<button type="button" class="active" data-decade="all" aria-pressed="true" onclick="filterDecade(\'all\')">All</button>'
        f'{decade_buttons}</div>'
    ) if all_decades else ''

    season_year = _season_year(basin_data)
    page_title = f'Hurricane Season History ({START_YEAR}–{season_year}): ACE by Year | aceofcanes.com'
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="Compare every Atlantic and Eastern Pacific hurricane season from {START_YEAR} to {season_year} by ACE, storm counts, and NOAA activity classifications.">
<meta name="theme-color" content="#4fc3f7">
<link rel="canonical" href="https://aceofcanes.com/history.html">
<meta property="og:type" content="website">
<meta property="og:site_name" content="ACE Tracker">
<meta property="og:url" content="https://aceofcanes.com/history.html">
<meta property="og:title" content="{page_title}">
<meta property="og:description" content="Compare every Atlantic and Eastern Pacific hurricane season from 1991 to present by ACE, storm counts, and NOAA activity classifications.">
{_share_image_meta(SHARE_IMAGE_ALT)}
<meta name="twitter:title" content="{page_title}">
<meta name="twitter:description" content="Compare every Atlantic and Eastern Pacific hurricane season from 1991 to present by ACE, storm counts, and NOAA activity classifications.">
<meta name="twitter:image" content="https://aceofcanes.com/ace_preview.png">
<link rel="icon" type="image/png" href="ace.png">
<title>{page_title}</title>
<script>(function(){{try{{var t=localStorage.getItem('ace-theme');if(t==='light')document.documentElement.setAttribute('data-theme','light');else if(!t&&window.matchMedia&&window.matchMedia('(prefers-color-scheme: light)').matches)document.documentElement.setAttribute('data-theme','light');}}catch(e){{}}}})();</script>
<style>
  :root {{
    --bg:#0a1628; --card:#132238; --box:#1a2d4a; --accent:#4fc3f7;
    --text:#e0e6ed; --text-strong:#ffffff; --muted:#8aa0ab; --border:#1e3a5f;
    --sources-bg:#0d1b2a; --gauge-bg:#1e3a5f;
    --row-extreme:rgba(239,83,80,0.10); --row-above:rgba(255,143,0,0.10);
    --row-below:rgba(66,165,245,0.10); --row-near:transparent;
    --current-border:#4fc3f7; --active-dot:#4fc3f7;
    --badge-extreme:#c62828; --badge-above:#b45309; --badge-near:#546e7a; --badge-below:#1976d2;
  }}
  [data-theme="light"] {{
    --bg:#f0f4f8; --card:#ffffff; --box:#e8f0fe; --accent:#0277bd;
    --text:#1a2d4a; --text-strong:#0a1628; --muted:#4f6773; --border:#b0bec5;
    --sources-bg:#e2ecf7; --gauge-bg:#c9daf8;
    --row-extreme:rgba(198,40,40,0.07); --row-above:rgba(230,81,0,0.07);
    --row-below:rgba(21,101,192,0.07); --row-near:transparent;
    --current-border:#0277bd; --active-dot:#0277bd;
    --badge-extreme:#c62828; --badge-above:#b45309; --badge-near:#546e7a; --badge-below:#1565c0;
  }}
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  :focus-visible {{ outline:2px solid var(--accent); outline-offset:2px; }}
  body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background:var(--bg); color:var(--text); padding:12px; transition:background 0.2s,color 0.2s; }}
  .header {{ display:grid; grid-template-columns:1fr auto 1fr; align-items:center; margin:8px 0; padding:0 4px; }}
  h1 {{ grid-column:2; color:var(--accent); font-size:1.4em; text-align:center; display:flex; align-items:center; justify-content:center; gap:8px; }}
  .logo {{ height:1.5em; width:auto; vertical-align:middle; }}
  .theme-btn {{ grid-column:3; justify-self:end; background:transparent; border:1px solid var(--accent); color:var(--accent); border-radius:20px; padding:4px 10px; cursor:pointer; font-size:0.9em; }}
  .updated {{ text-align:center; color:var(--muted); font-size:0.8em; margin-bottom:8px; }}
  .nav-link {{ text-align:center; margin-bottom:12px; display:flex; justify-content:center; gap:8px; flex-wrap:wrap; }}
  .nav-link a {{ color:var(--accent); text-decoration:none; font-size:0.85em; border:1px solid var(--accent); border-radius:20px; padding:4px 14px; }}
  .nav-link a:hover {{ background:var(--accent); color:var(--bg); }}
  .ace-explain {{ background:var(--box); border-radius:8px; padding:10px 14px; margin-bottom:14px; font-size:0.85em; }}
  .ace-explain summary {{ color:var(--accent); cursor:pointer; list-style:none; display:flex; align-items:center; gap:6px; min-height:44px; }}
  .ace-explain summary::-webkit-details-marker {{ display:none; }}
  .ace-explain summary::before {{ content:'ℹ'; font-size:1.1em; }}
  .ace-explain-hint {{ color:var(--muted); font-size:0.85em; }}
  .ace-explain p {{ color:var(--text); line-height:1.6; margin-top:8px; padding-top:8px; border-top:1px solid var(--border); }}
  .ace-explain p a, .ace-explain p a:visited {{ color:var(--accent); font-weight:600; text-decoration:underline; text-underline-offset:2px; }}
  .toggle {{ display:flex; justify-content:center; gap:8px; margin-bottom:16px; }}
  .toggle button {{ padding:8px 20px; border:1px solid var(--accent); background:transparent; color:var(--accent); border-radius:20px; cursor:pointer; font-size:0.9em; }}
  .toggle button.active {{ background:var(--accent); color:var(--bg); font-weight:bold; }}
  .basin-card {{ background:var(--card); border-radius:12px; padding:16px; margin-bottom:16px; display:none; }}
  .basin-card.active {{ display:block; }}
  h2 {{ color:var(--accent); font-size:1.2em; margin-bottom:6px; border-bottom:1px solid var(--border); padding-bottom:8px; }}
  .season-note {{ color:var(--muted); font-size:0.78em; margin-bottom:12px; }}
  .table-wrap {{ overflow-x:auto; background: linear-gradient(to right,var(--card) 20px,transparent 20px) left/20px 100%, linear-gradient(to left,var(--card) 20px,transparent 20px) right/20px 100%, linear-gradient(to right,rgba(0,0,0,0.18),transparent) left/16px 100%, linear-gradient(to left,rgba(0,0,0,0.18),transparent) right/16px 100%; background-repeat:no-repeat; background-attachment:local,local,scroll,scroll; }}
  table {{ width:100%; border-collapse:collapse; font-size:0.85em; }}
  th {{ background:var(--box); color:var(--accent); padding:8px 6px; text-align:left; position:sticky; top:0; white-space:nowrap; }}
  th.sort-th {{ cursor:pointer; user-select:none; padding:10px 6px; white-space:nowrap; }}
  .sort-btn {{ background:none; border:0; padding:0; font:inherit; color:inherit; cursor:pointer; text-align:inherit; white-space:inherit; }}
  th.sort-th:hover {{ color:var(--text-strong); }}
  .sa {{ font-size:0.7em; margin-left:2px; opacity:0.7; }}
  .hist-table th:first-child, .hist-table td:first-child {{ position:sticky; left:0; z-index:1; background:var(--box); border-right:1px solid var(--border); }}
  .hist-table tbody td:first-child {{ background:var(--card); }}
  .row-top5 {{ border-left:3px solid #f9a825; }}
  .row-top5 td:first-child {{ background:var(--card); }}
  .row-avg {{ border-top:2px solid var(--border); font-style:italic; }}
  .row-avg td {{ color:var(--muted); }}
  .row-avg td:first-child {{ background:var(--box); }}
  .ace-bar {{ height:3px; background:var(--gauge-bg); border-radius:2px; margin-top:3px; }}
  .ace-bar-fill {{ height:100%; background:var(--accent); border-radius:2px; }}
  .legend {{ display:flex; flex-wrap:wrap; gap:6px; justify-content:center; margin-bottom:14px; padding:10px; background:var(--card); border-radius:8px; }}
  .legend .badge {{ font-size:0.8em; padding:3px 10px; }}
  td {{ padding:7px 6px; border-bottom:1px solid var(--border); color:var(--text); white-space:nowrap; }}
  tr:hover td {{ filter:brightness(1.12); }}
  .row-extreme {{ background:var(--row-extreme); }}
  .row-above {{ background:var(--row-above); }}
  .row-near {{ background:var(--row-near); }}
  .row-below {{ background:var(--row-below); }}
  .row-current {{ border-left:3px solid var(--current-border); }}
  .badge {{ display:inline-block; padding:2px 8px; border-radius:12px; font-size:0.78em; font-weight:600; color:#fff; white-space:nowrap; }}
  .badge-extreme {{ background:var(--badge-extreme); }}
  .badge-above {{ background:var(--badge-above); }}
  .badge-near {{ background:var(--badge-near); }}
  .badge-below {{ background:var(--badge-below); }}
  .active-dot {{ color:var(--active-dot); font-size:0.65em; vertical-align:middle; margin-left:3px; }}
  .prelim {{ font-size:0.68em; font-weight:600; text-transform:uppercase; letter-spacing:0.04em; color:var(--muted); border:1px solid var(--border); border-radius:4px; padding:0 3px; margin-left:4px; white-space:nowrap; }}
  .sources {{ background:var(--sources-bg); border-top:1px solid var(--border); margin-top:24px; padding:16px 12px; border-radius:8px; }}
  .sources h4 {{ color:var(--muted); font-size:0.8em; text-transform:uppercase; margin-bottom:8px; }}
  .sources a {{ color:var(--accent); text-decoration:none; font-size:0.78em; }}
  .sources a:hover {{ text-decoration:underline; }}
  .sources p {{ color:var(--muted); font-size:0.75em; margin-top:8px; line-height:1.5; }}
  .sources ul {{ list-style:none; padding:0; margin:0; }}
  .sources li {{ color:var(--muted); font-size:0.78em; margin:4px 0; padding-left:12px; position:relative; }}
  .sources li::before {{ content:"•"; position:absolute; left:0; color:var(--accent); }}
  .sources code {{ font-size:0.9em; background:var(--box); padding:1px 4px; border-radius:3px; }}
  .disclaimer {{ margin-top:12px; padding:10px 12px; border-radius:6px; border-left:3px solid var(--muted); font-size:0.75em; color:var(--muted); line-height:1.5; }}
  .kofi-link {{ text-align:center; margin-top:14px; font-size:0.78em; }}
  .kofi-link a {{ color:var(--muted); text-decoration:none; }}
  .kofi-link a:hover {{ color:var(--accent); }}
  @media(min-width:768px) {{ body {{ max-width:960px; margin:0 auto; padding:24px; }} }}
  @media(min-width:1100px) {{ body {{ max-width:1280px; }} }}
  .yr-expand-btn {{ background:none; border:none; color:var(--text-strong); cursor:pointer; font-size:inherit; padding:0; display:inline-flex; align-items:center; gap:4px; white-space:nowrap; width:100%; text-align:left; }}
  .yr-chevron {{ font-size:0.65em; color:var(--muted); display:inline-block; transition:transform 0.2s; margin-left:3px; }}
  .yr-expand-btn.open .yr-chevron {{ transform:rotate(90deg); }}
  .yr-expand-row td {{ padding:0; border-bottom:1px solid var(--border); }}
  .yr-panel {{ overflow:hidden; max-height:0; visibility:hidden; transition:max-height 0.3s ease, visibility 0s linear 0.3s; background:var(--sources-bg); }}
  .yr-panel.open {{ max-height:2000px; visibility:visible; transition:max-height 0.3s ease, visibility 0s; }}
  .yr-panel-inner {{ padding:8px 12px 10px; }}
  .yr-lfshare {{ display:flex; align-items:center; gap:10px; flex-wrap:wrap; font-size:0.8em; color:var(--muted); padding:2px 0 8px; margin-bottom:4px; border-bottom:1px solid var(--border); }}
  .yr-lfshare b {{ color:var(--text); }}
  .lfs-bar {{ display:inline-block; width:90px; height:8px; border-radius:4px; background:var(--border); overflow:hidden; flex:none; }}
  .lfs-fill {{ display:block; height:100%; background:#ffb74d; }}
  .ys-row {{ display:grid; grid-template-columns:110px 48px 46px 1fr; align-items:start; gap:6px; padding:5px 0; font-size:0.82em; border-bottom:1px solid var(--border); }}
  .ys-row:last-child {{ border-bottom:none; }}
  .ys-name {{ color:var(--text); font-weight:500; line-height:1.4; }}
  .ys-tcr {{ margin-left:5px; font-size:0.85em; text-decoration:none; opacity:0.75; }}
  .ys-tcr:hover, .ys-tcr:focus-visible {{ opacity:1; }}
  .ys-lf {{ display:block; font-size:0.82em; font-weight:400; color:var(--muted); font-style:italic; margin-top:1px; }}
  .ys-fish {{ color:var(--muted); opacity:0.7; cursor:help; }}
  .ys-cat {{ color:var(--muted); font-size:0.9em; cursor:help; text-decoration:underline dotted; text-underline-offset:2px; }}
  .global-tip {{ display:none; position:fixed; top:0; left:0; background:var(--box); color:var(--text); border:1px solid var(--border); padding:5px 11px; border-radius:6px; font-size:0.82em; pointer-events:none; z-index:9999; max-width:320px; line-height:1.4; box-shadow:0 2px 8px rgba(0,0,0,0.4); }}
  .ys-ace {{ color:var(--accent); font-weight:bold; text-align:right; }}
  .ys-bar {{ height:4px; background:var(--gauge-bg); border-radius:2px; }}
  .ys-bar-fill {{ height:100%; background:var(--accent); border-radius:2px; }}
  .yr-tcr {{ font-size:0.8em; color:var(--muted); padding:8px 0 2px; margin-top:4px; border-top:1px solid var(--border); white-space:normal; line-height:1.5; }}
  .yr-tcr a {{ color:var(--accent); text-decoration:none; }}
  .yr-tcr a:hover {{ text-decoration:underline; }}
  .yr-tcr-note {{ font-style:italic; }}
  .decade-filter {{ display:flex; flex-wrap:wrap; justify-content:center; align-items:center; gap:6px; margin-bottom:14px; }}
  .decade-filter-label {{ color:var(--muted); font-size:0.8em; }}
  .decade-filter button {{ padding:5px 14px; min-height:32px; border:1px solid var(--border); background:transparent; color:var(--text); border-radius:16px; cursor:pointer; font-size:0.82em; }}
  .decade-filter button:hover {{ border-color:var(--accent); color:var(--accent); }}
  .decade-filter button.active {{ background:var(--accent); border-color:var(--accent); color:var(--bg); font-weight:bold; }}
  .decade-filter button:focus-visible, .yr-tcr a:focus-visible {{ outline:2px solid var(--accent); outline-offset:2px; }}
  .decade-count {{ color:var(--accent); font-weight:600; }}
</style>
</head>
<body>
<div class="header">
  <h1><img src="ace.png" class="logo" alt="" aria-hidden="true"> Hurricane ACE History</h1>
  <button class="theme-btn" id="themeBtn" onclick="toggleTheme()" aria-label="Toggle light and dark theme">☀</button>
</div>
<div class="updated">Updated: {now.strftime('%B %d, %Y at %H:%M UTC')}</div>
<div class="nav-link"><a href="/">← Current Season</a><a href="records.html">🏆 Records</a><a href="what-is-ace.html">❓ What is ACE?</a></div>
<details class="ace-explain">
  <summary>What is ACE? <span class="ace-explain-hint">(tap to expand)</span></summary>
  <p>Accumulated Cyclone Energy (ACE) measures total hurricane season activity by combining storm intensity and duration. A major hurricane that lasts two weeks contributes far more than a brief tropical storm. NOAA uses seasonal ACE totals to classify years as <b>Below Normal</b> (&lt;73), <b>Near Normal</b> (73–126), <b>Above Normal</b> (126–159), or <b>Extremely Active</b> (159+). <a href="what-is-ace.html">More on ACE, plus a calculator →</a></p>
</details>
<div class="toggle">
  <button class="active" aria-pressed="true" onclick="show('atlantic',this)">Atlantic</button>
  <button aria-pressed="false" onclick="show('pacific',this)">E/C Pacific</button>
</div>
<div class="legend">
  <span class="badge badge-extreme">Extremely Active ≥159</span>
  <span class="badge badge-above">Above Normal 126–159</span>
  <span class="badge badge-near">Near Normal 73–126</span>
  <span class="badge badge-below">Below Normal &lt;73</span>
</div>
{decade_filter_html}
{''.join(basin_sections)}
<div class="sources">
  <h4>Data Sources</h4>
  <ul>
    <li><a href="https://www.nhc.noaa.gov/data/#hurdat" target="_blank" rel="noopener noreferrer">NOAA HURDAT2</a> — Official historical best-track database (1991–present) for all storm tracks, wind speeds, and ACE calculations</li>
    <li><a href="https://www.nhc.noaa.gov/data/#hurdat" target="_blank" rel="noopener noreferrer">NHC Real-time Best Track</a> — Current season preliminary storm data fetched via Tropycal (<code>include_btk=True</code>); updated continuously during active storms</li>
    <li><a href="https://www.cpc.ncep.noaa.gov/products/outlooks/background_information.shtml" target="_blank" rel="noopener noreferrer">NOAA CPC</a> — Season classification thresholds and 1991–2020 climatological normals</li>
  </ul>
  <p>ACE (Accumulated Cyclone Energy) is calculated at 6-hourly synoptic times (0000/0600/1200/1800 UTC) for systems with status TS, HU, or SS and wind ≥34 kt — extratropical (EX) phases are excluded per NHC methodology. Formula: ACE = Σ(V²<sub>max</sub>) × 10⁻⁴. Categories use the Saffir-Simpson scale in knots.</p>
  <p><b>Basin note:</b> The East &amp; Central Pacific tab combines both the Eastern Pacific (NHC, east of 140°W) and Central Pacific (CPHC, 140°W–180°) basins, consistent with the NOAA HURDAT2 Northeast &amp; North Central Pacific dataset. NHC tracks these separately on their <a href="https://www.nhc.noaa.gov/data/tcr/" target="_blank" rel="noopener noreferrer">TCR pages</a> (epac / cpac).</p>
  <p class="disclaimer">⚠️ This site is maintained by a hurricane data enthusiast — not a meteorologist, forecaster, or weather professional of any kind. I just love the data. All information is sourced directly from official NOAA/NHC databases. For official forecasts, watches, warnings, and life-safety information, always refer to the <a href="https://www.nhc.noaa.gov/" target="_blank" rel="noopener noreferrer">National Hurricane Center</a>.</p>
  <p class="kofi-link"><a href="https://ko-fi.com/aceofcanes" target="_blank" rel="noopener noreferrer">☕ Support this project on Ko-fi</a></p>
</div>
<script>
function show(id,btn) {{
  document.querySelectorAll('.basin-card').forEach(c=>c.classList.remove('active'));
  document.querySelectorAll('.toggle button').forEach(b=>{{b.classList.remove('active');b.setAttribute('aria-pressed','false');}});
  document.getElementById(id)?.classList.add('active');
  btn.classList.add('active');
  btn.setAttribute('aria-pressed','true');
  _syncHash();
}}
var _decade='all';
function _syncHash(){{
  var card=document.querySelector('.basin-card.active');
  var h=(card?card.id:'atlantic')+(_decade!=='all'?'&decade='+_decade:'');
  try{{history.replaceState(null,'','#'+h);}}catch(e){{}}
}}
function filterDecade(dec){{
  var btns=document.querySelectorAll('.decade-filter button');
  if(![].some.call(btns,function(b){{return b.getAttribute('data-decade')===dec;}}))return;
  btns.forEach(function(b){{
    var on=b.getAttribute('data-decade')===dec;
    b.classList.toggle('active',on);
    b.setAttribute('aria-pressed',on?'true':'false');
  }});
  document.querySelectorAll('.basin-card').forEach(function(card){{
    var shown=0,total=0;
    card.querySelectorAll('tr.yr-data-row').forEach(function(r){{
      var hide=dec!=='all'&&r.getAttribute('data-decade')!==dec;
      total++;if(!hide)shown++;
      r.hidden=hide;
      var x=document.getElementById('yr-xrow-'+r.id);
      if(x)x.hidden=hide;
    }});
    var c=card.querySelector('.decade-count');
    if(c)c.textContent=dec==='all'?'':'· Showing '+shown+' of '+total+' seasons ('+dec+')';
  }});
  _decade=dec;
  _syncHash();
}}
function toggleTheme() {{
  var h=document.documentElement;
  var light=h.getAttribute('data-theme')==='light';
  h.setAttribute('data-theme',light?'dark':'light');
  try{{localStorage.setItem('ace-theme',light?'dark':'light');}}catch(e){{}}
  document.getElementById('themeBtn').textContent=light?'☀':'☾';document.getElementById('themeBtn').setAttribute('aria-label',document.documentElement.getAttribute('data-theme')==='light'?'Switch to dark mode':'Switch to light mode');
}}
document.addEventListener('DOMContentLoaded',function() {{
  document.getElementById('themeBtn').textContent=document.documentElement.getAttribute('data-theme')==='light'?'☾':'☀';document.getElementById('themeBtn').setAttribute('aria-label',document.documentElement.getAttribute('data-theme')==='light'?'Switch to dark mode':'Switch to light mode');
  var parts=location.hash.replace('#','').split('&');
  var hash=parts[0];
  parts.slice(1).forEach(function(p){{if(p.indexOf('decade=')===0)filterDecade(p.slice(7));}});
  var match=hash?[].slice.call(document.querySelectorAll('.toggle button')).filter(function(b){{return(b.getAttribute('onclick')||'').indexOf("'"+hash+"'")>=0;}})[0]:null;
  if(match)match.click();
}});
var _hs={{}};
function sortHist(th,col,type){{
  var card=th.closest('.basin-card');
  var tbody=card.querySelector('tbody');
  var key=card.id+col;
  var asc=_hs[key]===undefined?false:!_hs[key];
  _hs[key]=asc;
  var rows=Array.from(tbody.querySelectorAll('tr.yr-data-row'));
  rows.sort(function(a,b){{
    var av=a.cells[col]?a.cells[col].getAttribute('data-v'):'';
    var bv=b.cells[col]?b.cells[col].getAttribute('data-v'):'';
    if(type==='n'){{av=parseFloat(av)||0;bv=parseFloat(bv)||0;}}
    if(av<bv)return asc?-1:1;
    if(av>bv)return asc?1:-1;
    return 0;
  }});
  rows.forEach(function(r){{
    tbody.appendChild(r);
    var xrow=document.getElementById('yr-xrow-'+r.id);
    if(xrow)tbody.appendChild(xrow);
  }});
  card.querySelectorAll('.sort-th .sa').forEach(function(s,i){{s.innerHTML=i===col?(asc?'&#9650;':'&#9660;'):''}});
  card.querySelectorAll('th.sort-th').forEach(function(h,i){{if(i===col)h.setAttribute('aria-sort',asc?'ascending':'descending');else h.removeAttribute('aria-sort');}});
}}
function toggleYear(key){{
  var panel=document.getElementById('yrpanel-'+key);
  var btn=document.getElementById('yrbtn-'+key);
  if(!panel)return;
  var open=panel.classList.contains('open');
  if(open){{panel.classList.remove('open');if(btn)btn.classList.remove('open');}}
  else{{panel.classList.add('open');if(btn)btn.classList.add('open');}}
  if(btn)btn.setAttribute('aria-expanded',open?'false':'true');
}}
</script>
<div id="global-tip" class="global-tip"></div>
<script>
(function(){{
  var tip=document.getElementById('global-tip');
  function posFromEvent(e){{
    if(e.touches&&e.touches[0])return {{x:e.touches[0].clientX,y:e.touches[0].clientY}};
    if(typeof e.clientX==='number'&&(e.clientX||e.clientY))return {{x:e.clientX,y:e.clientY}};
    var r=e.currentTarget.getBoundingClientRect();
    return {{x:r.left+r.width/2,y:r.top}};
  }}
  function move(e){{
    var p=posFromEvent(e),w=tip.offsetWidth,h=tip.offsetHeight;
    var x=Math.min(p.x+14,window.innerWidth-w-8);
    var y=Math.max(p.y-h-8,8);
    tip.style.transform='translate('+x+'px,'+y+'px)';
  }}
  function show(e){{var t=e.currentTarget.getAttribute('data-tip');if(!t)return;tip.textContent=t;tip.style.display='block';move(e);}}
  function hide(){{tip.style.display='none';}}
  document.querySelectorAll('[data-tip]').forEach(function(el){{
    el.addEventListener('mouseenter',show);
    el.addEventListener('mousemove',move);
    el.addEventListener('mouseleave',hide);
    el.addEventListener('touchstart',show,{{passive:true}});
    el.addEventListener('touchend',hide);
    el.addEventListener('focus',show);
    el.addEventListener('blur',hide);
  }});
}})();
</script>
<!-- Cloudflare Web Analytics --><script defer src='https://static.cloudflareinsights.com/beacon.min.js' data-cf-beacon='{{"token": "775dfcf117b94ff59e3c118c330d02aa"}}'></script><!-- End Cloudflare Web Analytics -->
</body>
</html>'''
    return html




# ===============================================================================
# RECORDS PAGE
# ===============================================================================

def _record_card_html(emoji, label, value, sub):
    sub_html = f'<div class="rc-sub">{sub}</div>' if sub else ''
    return (
        f'<div class="record-card">'
        f'<div class="rc-label">{emoji} {label}</div>'
        f'<div class="rc-value">{value}</div>'
        f'{sub_html}'
        f'</div>'
    )


def generate_records_html(basin_data):
    """Generate the all-time-since-START_YEAR storm records page.

    Records are computed dynamically from historical_storms rather than
    hardcoded -- a hardcoded "all-time" record constant is exactly what went
    stale for the Pacific single-storm ACE record (see #117), so this page
    is scoped to "since START_YEAR" throughout rather than "all-time":
    pre-satellite-era (pre-1970s) intensity estimates aren't a reliable
    apples-to-apples comparison to modern storms.
    """
    now = datetime.now(timezone.utc)

    basin_sections = []
    for bd in basin_data:
        if not bd:
            continue
        basin = BASINS[bd['basin_key']]
        historical_storms = bd.get('historical_storms') or []

        cards = []

        highest_ace = find_highest_ace_storm(historical_storms)
        if highest_ace:
            cards.append(_record_card_html(
                '🎯', 'Highest Single-Storm ACE',
                f"{html_escape(highest_ace['name'])} ({highest_ace['year']})",
                f"{highest_ace['ace']:.1f} ACE"))

        longest = find_longest_lived_storm(historical_storms)
        if longest:
            cards.append(_record_card_html(
                '⏱️', 'Longest-Lived Storm',
                f"{html_escape(longest['name'])} ({longest['year']})",
                f"{longest['duration_days']} days"))

        landfall = find_strongest_landfall(historical_storms)
        if landfall:
            tied_note = ''
            if landfall['tied_count'] > 0:
                plural = 's' if landfall['tied_count'] > 1 else ''
                tied_note = f" (+{landfall['tied_count']} other {landfall['category']} landfall{plural})"
            cards.append(_record_card_html(
                '🌊', 'Strongest Landfall',
                f"{html_escape(landfall['name'])} ({landfall['year']})",
                f"{landfall['category']} at {html_escape(landfall['location'])}{tied_note}"))

        earliest = find_earliest_forming_storm(historical_storms)
        if earliest:
            cards.append(_record_card_html(
                '📅', 'Earliest-Forming Storm',
                f"{html_escape(earliest['name'])} ({earliest['year']})",
                f"Formed {_portable_strftime(earliest['formation_date'], '%B %-d')}"))

        latest = find_latest_forming_storm(historical_storms)
        if latest:
            cards.append(_record_card_html(
                '📅', 'Latest-Forming Storm',
                f"{html_escape(latest['name'])} ({latest['year']})",
                f"Formed {_portable_strftime(latest['formation_date'], '%B %-d, %Y')}"))

        basin_sections.append(f'''
    <div class="basin-card{' active' if not basin_sections else ''}" id="{bd['basin_key']}">
      <h2>{html_escape(basin['name'])} — Records Since {START_YEAR}</h2>
      <p class="season-note">Scoped to {START_YEAR}–present, matching the rest of the site — pre-satellite-era storms (pre-1970s) aren't included since their intensity estimates aren't a reliable comparison to modern measurements.</p>
      <div class="records-grid">{''.join(cards)}</div>
    </div>''')

    season_year = _season_year(basin_data)
    page_title = f'Hurricane Records {START_YEAR}–{season_year}: Atlantic &amp; East Pacific | aceofcanes.com'
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="All-time hurricane records since 1991 for the Atlantic and Eastern Pacific: highest single-storm ACE, longest-lived storm, strongest landfall, and earliest/latest-forming named storms.">
<meta name="theme-color" content="#4fc3f7">
<link rel="canonical" href="https://aceofcanes.com/records.html">
<meta property="og:type" content="website">
<meta property="og:site_name" content="ACE Tracker">
<meta property="og:url" content="https://aceofcanes.com/records.html">
<meta property="og:title" content="{page_title}">
<meta property="og:description" content="All-time hurricane records since 1991 for the Atlantic and Eastern Pacific: highest single-storm ACE, longest-lived storm, strongest landfall, and earliest/latest-forming named storms.">
{_share_image_meta(SHARE_IMAGE_ALT)}
<meta name="twitter:title" content="{page_title}">
<meta name="twitter:description" content="All-time hurricane records since 1991 for the Atlantic and Eastern Pacific: highest single-storm ACE, longest-lived storm, strongest landfall, and earliest/latest-forming named storms.">
<meta name="twitter:image" content="https://aceofcanes.com/ace_preview.png">
<link rel="icon" type="image/png" href="ace.png">
<title>{page_title}</title>
<script>(function(){{try{{var t=localStorage.getItem('ace-theme');if(t==='light')document.documentElement.setAttribute('data-theme','light');else if(!t&&window.matchMedia&&window.matchMedia('(prefers-color-scheme: light)').matches)document.documentElement.setAttribute('data-theme','light');}}catch(e){{}}}})();</script>
<style>
  :root {{
    --bg:#0a1628; --card:#132238; --box:#1a2d4a; --accent:#4fc3f7;
    --text:#e0e6ed; --text-strong:#ffffff; --muted:#8aa0ab; --border:#1e3a5f;
    --sources-bg:#0d1b2a;
  }}
  [data-theme="light"] {{
    --bg:#f0f4f8; --card:#ffffff; --box:#e8f0fe; --accent:#0277bd;
    --text:#1a2d4a; --text-strong:#0a1628; --muted:#4f6773; --border:#b0bec5;
    --sources-bg:#e2ecf7;
  }}
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  :focus-visible {{ outline:2px solid var(--accent); outline-offset:2px; }}
  body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background:var(--bg); color:var(--text); padding:12px; transition:background 0.2s,color 0.2s; }}
  .header {{ display:grid; grid-template-columns:1fr auto 1fr; align-items:center; margin:8px 0; padding:0 4px; }}
  h1 {{ grid-column:2; color:var(--accent); font-size:1.4em; text-align:center; display:flex; align-items:center; justify-content:center; gap:8px; }}
  .logo {{ height:1.5em; width:auto; vertical-align:middle; }}
  .theme-btn {{ grid-column:3; justify-self:end; background:transparent; border:1px solid var(--accent); color:var(--accent); border-radius:20px; padding:4px 10px; cursor:pointer; font-size:0.9em; }}
  .updated {{ text-align:center; color:var(--muted); font-size:0.8em; margin-bottom:8px; }}
  .nav-link {{ text-align:center; margin-bottom:12px; display:flex; justify-content:center; gap:8px; flex-wrap:wrap; }}
  .nav-link a {{ color:var(--accent); text-decoration:none; font-size:0.85em; border:1px solid var(--accent); border-radius:20px; padding:4px 14px; }}
  .nav-link a:hover {{ background:var(--accent); color:var(--bg); }}
  .toggle {{ display:flex; justify-content:center; gap:8px; margin-bottom:16px; }}
  .toggle button {{ padding:8px 20px; border:1px solid var(--accent); background:transparent; color:var(--accent); border-radius:20px; cursor:pointer; font-size:0.9em; }}
  .toggle button.active {{ background:var(--accent); color:var(--bg); font-weight:bold; }}
  .basin-card {{ background:var(--card); border-radius:12px; padding:16px; margin-bottom:16px; display:none; }}
  .basin-card.active {{ display:block; }}
  h2 {{ color:var(--accent); font-size:1.2em; margin-bottom:6px; border-bottom:1px solid var(--border); padding-bottom:8px; }}
  .season-note {{ color:var(--muted); font-size:0.78em; margin-bottom:14px; }}
  .records-grid {{ display:grid; grid-template-columns:1fr; gap:10px; }}
  @media(min-width:600px) {{ .records-grid {{ grid-template-columns:1fr 1fr; }} }}
  .record-card {{ background:var(--box); border-radius:10px; padding:14px 16px; }}
  .rc-label {{ color:var(--muted); font-size:0.72em; text-transform:uppercase; margin-bottom:6px; }}
  .rc-value {{ color:var(--text-strong); font-size:1.05em; font-weight:bold; }}
  .rc-sub {{ color:var(--muted); font-size:0.85em; margin-top:4px; }}
  .sources {{ background:var(--sources-bg); border-top:1px solid var(--border); margin-top:24px; padding:16px 12px; border-radius:8px; }}
  .sources h4 {{ color:var(--muted); font-size:0.8em; text-transform:uppercase; margin-bottom:8px; }}
  .sources a {{ color:var(--accent); text-decoration:none; font-size:0.78em; }}
  .sources a:hover {{ text-decoration:underline; }}
  .sources p {{ color:var(--muted); font-size:0.75em; margin-top:8px; line-height:1.5; }}
  .sources ul {{ list-style:none; padding:0; margin:0; }}
  .sources li {{ color:var(--muted); font-size:0.78em; margin:4px 0; padding-left:12px; position:relative; }}
  .sources li::before {{ content:"•"; position:absolute; left:0; color:var(--accent); }}
  .disclaimer {{ margin-top:12px; padding:10px 12px; border-radius:6px; border-left:3px solid var(--muted); font-size:0.75em; color:var(--muted); line-height:1.5; }}
  .kofi-link {{ text-align:center; margin-top:14px; font-size:0.78em; }}
  .kofi-link a {{ color:var(--muted); text-decoration:none; }}
  .kofi-link a:hover {{ color:var(--accent); }}
  @media(min-width:768px) {{ body {{ max-width:960px; margin:0 auto; padding:24px; }} }}
  @media(min-width:1100px) {{ body {{ max-width:1280px; }} }}
</style>
</head>
<body>
<div class="header">
  <h1><img src="ace.png" class="logo" alt="" aria-hidden="true"> Hurricane Records</h1>
  <button class="theme-btn" id="themeBtn" onclick="toggleTheme()" aria-label="Toggle light and dark theme">☀</button>
</div>
<div class="updated">Updated: {now.strftime('%B %d, %Y at %H:%M UTC')}</div>
<div class="nav-link"><a href="/">← Current Season</a><a href="history.html">Season History</a><a href="what-is-ace.html">❓ What is ACE?</a></div>
<div class="toggle">
  <button class="active" aria-pressed="true" onclick="show('atlantic',this)">Atlantic</button>
  <button aria-pressed="false" onclick="show('pacific',this)">E/C Pacific</button>
</div>
{''.join(basin_sections)}
<div class="sources">
  <h4>Data Sources</h4>
  <ul>
    <li><a href="https://www.nhc.noaa.gov/data/#hurdat" target="_blank" rel="noopener noreferrer">NOAA HURDAT2</a> — Official historical best-track database (1991–present) for all storm tracks, wind speeds, and ACE calculations</li>
  </ul>
  <p>ACE (Accumulated Cyclone Energy) is calculated at 6-hourly synoptic times (0000/0600/1200/1800 UTC) for systems with status TS, HU, or SS and wind ≥34 kt. Formula: ACE = Σ(V²<sub>max</sub>) × 10⁻⁴. Landfall category reflects the storm's intensity at the moment of landfall, not its peak intensity.</p>
  <p class="disclaimer">⚠️ This site is maintained by a hurricane data enthusiast — not a meteorologist, forecaster, or weather professional of any kind. All information is sourced directly from official NOAA/NHC databases. For official forecasts, watches, warnings, and life-safety information, always refer to the <a href="https://www.nhc.noaa.gov/" target="_blank" rel="noopener noreferrer">National Hurricane Center</a>.</p>
  <p class="kofi-link"><a href="https://ko-fi.com/aceofcanes" target="_blank" rel="noopener noreferrer">☕ Support this project on Ko-fi</a></p>
</div>
<script>
function show(id,btn) {{
  document.querySelectorAll('.basin-card').forEach(c=>c.classList.remove('active'));
  document.querySelectorAll('.toggle button').forEach(b=>{{b.classList.remove('active');b.setAttribute('aria-pressed','false');}});
  document.getElementById(id)?.classList.add('active');
  btn.classList.add('active');
  btn.setAttribute('aria-pressed','true');
  try{{history.replaceState(null,'','#'+id);}}catch(e){{}}
}}
function toggleTheme() {{
  var h=document.documentElement;
  var light=h.getAttribute('data-theme')==='light';
  h.setAttribute('data-theme',light?'dark':'light');
  try{{localStorage.setItem('ace-theme',light?'dark':'light');}}catch(e){{}}
  document.getElementById('themeBtn').textContent=light?'☀':'☾';document.getElementById('themeBtn').setAttribute('aria-label',document.documentElement.getAttribute('data-theme')==='light'?'Switch to dark mode':'Switch to light mode');
}}
document.addEventListener('DOMContentLoaded',function() {{
  document.getElementById('themeBtn').textContent=document.documentElement.getAttribute('data-theme')==='light'?'☾':'☀';document.getElementById('themeBtn').setAttribute('aria-label',document.documentElement.getAttribute('data-theme')==='light'?'Switch to dark mode':'Switch to light mode');
  var hash=location.hash.replace('#','');
  var match=[].slice.call(document.querySelectorAll('.toggle button')).filter(function(b){{return(b.getAttribute('onclick')||'').indexOf("'"+hash+"'")>=0;}})[0];
  if(match)match.click();
}});
</script>
<!-- Cloudflare Web Analytics --><script defer src='https://static.cloudflareinsights.com/beacon.min.js' data-cf-beacon='{{"token": "775dfcf117b94ff59e3c118c330d02aa"}}'></script><!-- End Cloudflare Web Analytics -->
</body>
</html>'''
    return html



# ===============================================================================
# WHAT IS ACE? PAGE
# ===============================================================================

def _ace_fun_facts(basin_data):
    """Short facts drawn from the site's own data, per basin: busiest and
    quietest season, highest-ACE storm, and the current season so far."""
    facts = []
    for bd in basin_data:
        if not bd:
            continue
        basin = BASINS[bd['basin_key']]
        name = basin['name']
        current_year = bd['current']['year']
        completed = {y: a for y, a in (bd.get('yearly_totals') or {}).items() if y < current_year}
        if completed:
            top_year = max(completed, key=completed.get)
            low_year = min(completed, key=completed.get)
            facts.append(
                f"The busiest {html_escape(name)} season since {START_YEAR} was <b>{top_year}</b> at "
                f"<b>{completed[top_year]:.1f} ACE</b>, {completed[top_year] / basin['normal_ace']:.1f}× a normal "
                f"season. The quietest was <b>{low_year}</b> at <b>{completed[low_year]:.1f}</b>.")
        top_storm = find_highest_ace_storm(bd.get('historical_storms') or [])
        if top_storm:
            facts.append(
                f"The biggest single {html_escape(name)} storm since {START_YEAR} was "
                f"<b>{html_escape(top_storm['name'])} ({top_storm['year']})</b> with <b>{top_storm['ace']:.1f} ACE</b>, "
                f"{top_storm['ace'] / basin['normal_ace'] * 100:.0f}% of a whole normal season on its own.")
        cur = bd['current'].get('total', 0.0)
        facts.append(
            f"The {current_year} {html_escape(name)} season is at <b>{cur:.1f} ACE</b> so far "
            f"(preliminary; {get_noaa_classification(cur, bd['basin_key'])}). "
            f"<a href=\"/#{bd['basin_key']}\">See the live dashboard</a>.")
    return facts


def generate_about_html(basin_data):
    """Standalone "What is ACE?" explainer: formula, NOAA classification
    thresholds, a calculator, and facts from the site's own data."""
    now = datetime.now(timezone.utc)
    t = BASINS['atlantic']['noaa_thresholds']
    normal_atl = BASINS['atlantic']['normal_ace']
    facts = ''.join(f'<li>{f}</li>' for f in _ace_fun_facts(basin_data))
    facts_html = f'''
  <section class="card">
    <h2>From this site's data</h2>
    <ul class="facts">{facts}</ul>
  </section>''' if facts else ''
    description = ('What Accumulated Cyclone Energy (ACE) is, how it is calculated, how NOAA uses it to '
                   'classify hurricane seasons, plus an ACE calculator.')
    page_title = 'What Is ACE? Accumulated Cyclone Energy Explained | aceofcanes.com'

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="{description}">
<meta name="theme-color" content="#4fc3f7">
<link rel="canonical" href="https://aceofcanes.com/what-is-ace.html">
<meta property="og:type" content="article">
<meta property="og:site_name" content="ACE Tracker">
<meta property="og:url" content="https://aceofcanes.com/what-is-ace.html">
<meta property="og:title" content="{page_title}">
<meta property="og:description" content="{description}">
{_share_image_meta(SHARE_IMAGE_ALT)}
<meta name="twitter:title" content="{page_title}">
<meta name="twitter:description" content="{description}">
<meta name="twitter:image" content="https://aceofcanes.com/ace_preview.png">
<link rel="icon" type="image/png" href="ace.png">
<title>{page_title}</title>
<script>(function(){{try{{var t=localStorage.getItem('ace-theme');if(t==='light')document.documentElement.setAttribute('data-theme','light');else if(!t&&window.matchMedia&&window.matchMedia('(prefers-color-scheme: light)').matches)document.documentElement.setAttribute('data-theme','light');}}catch(e){{}}}})();</script>
<style>
  :root {{
    --bg:#0a1628; --card:#132238; --box:#1a2d4a; --accent:#4fc3f7;
    --text:#e0e6ed; --text-strong:#ffffff; --muted:#8aa0ab; --border:#1e3a5f;
    --sources-bg:#0d1b2a;
    --badge-extreme:#c62828; --badge-above:#b45309; --badge-near:#546e7a; --badge-below:#1976d2;
  }}
  [data-theme="light"] {{
    --bg:#f0f4f8; --card:#ffffff; --box:#e8f0fe; --accent:#0277bd;
    --text:#1a2d4a; --text-strong:#0a1628; --muted:#4f6773; --border:#b0bec5;
    --sources-bg:#e2ecf7;
  }}
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  :focus-visible {{ outline:2px solid var(--accent); outline-offset:2px; }}
  body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background:var(--bg); color:var(--text); padding:12px; line-height:1.55; transition:background 0.2s,color 0.2s; }}
  .header {{ display:grid; grid-template-columns:1fr auto 1fr; align-items:center; margin:8px 0; padding:0 4px; }}
  h1 {{ grid-column:2; color:var(--accent); font-size:1.4em; text-align:center; display:flex; align-items:center; justify-content:center; gap:8px; }}
  .logo {{ height:1.5em; width:auto; vertical-align:middle; }}
  .theme-btn {{ grid-column:3; justify-self:end; background:transparent; border:1px solid var(--accent); color:var(--accent); border-radius:20px; padding:4px 10px; cursor:pointer; font-size:0.9em; }}
  .updated {{ text-align:center; color:var(--muted); font-size:0.8em; margin-bottom:8px; }}
  .nav-link {{ text-align:center; margin-bottom:12px; display:flex; justify-content:center; gap:8px; flex-wrap:wrap; }}
  .nav-link a {{ color:var(--accent); text-decoration:none; font-size:0.85em; border:1px solid var(--accent); border-radius:20px; padding:4px 14px; }}
  .nav-link a:hover {{ background:var(--accent); color:var(--bg); }}
  .card {{ background:var(--card); border-radius:12px; padding:16px; margin-bottom:16px; }}
  h2 {{ color:var(--accent); font-size:1.15em; margin-bottom:10px; border-bottom:1px solid var(--border); padding-bottom:8px; }}
  .card p {{ margin:8px 0; font-size:0.92em; }}
  .card a {{ color:var(--accent); }}
  .formula {{ background:var(--box); border-radius:8px; padding:14px; text-align:center; font-size:1.25em; color:var(--text-strong); margin:10px 0; }}
  .formula small {{ display:block; font-size:0.62em; color:var(--muted); margin-top:6px; }}
  table {{ width:100%; border-collapse:collapse; font-size:0.9em; }}
  th, td {{ text-align:left; padding:8px 10px; border-bottom:1px solid var(--border); }}
  th {{ color:var(--muted); font-weight:600; font-size:0.85em; text-transform:uppercase; }}
  .badge {{ display:inline-block; padding:2px 10px; border-radius:10px; color:#fff; font-size:0.85em; font-weight:600; }}
  .b-below {{ background:var(--badge-below); }} .b-near {{ background:var(--badge-near); }}
  .b-above {{ background:var(--badge-above); }} .b-extreme {{ background:var(--badge-extreme); }}
  .calc label {{ display:block; font-size:0.85em; color:var(--muted); margin:10px 0 4px; }}
  .calc textarea, .calc select {{ width:100%; background:var(--box); color:var(--text-strong); border:1px solid var(--border); border-radius:8px; padding:10px; font-size:1em; font-family:inherit; }}
  .calc textarea {{ min-height:70px; resize:vertical; }}
  .calc-row {{ display:flex; gap:10px; flex-wrap:wrap; margin-top:10px; }}
  .calc-row button {{ background:transparent; border:1px solid var(--accent); color:var(--accent); border-radius:20px; padding:6px 14px; cursor:pointer; font-size:0.85em; }}
  .calc-row button:hover {{ background:var(--accent); color:var(--bg); }}
  .calc-out {{ background:var(--box); border-radius:8px; padding:12px 14px; margin-top:12px; }}
  .calc-ace {{ font-size:1.6em; font-weight:bold; color:var(--text-strong); }}
  .calc-note {{ font-size:0.82em; color:var(--muted); }}
  .facts {{ list-style:none; padding:0; }}
  .facts li {{ background:var(--box); border-left:3px solid var(--accent); border-radius:6px; padding:8px 10px; margin:6px 0; font-size:0.9em; }}
  .sources {{ background:var(--sources-bg); border-top:1px solid var(--border); margin-top:24px; padding:16px 12px; border-radius:8px; }}
  .sources h4 {{ color:var(--muted); font-size:0.8em; text-transform:uppercase; margin-bottom:8px; }}
  .sources a {{ color:var(--accent); text-decoration:none; font-size:0.78em; }}
  .sources p {{ color:var(--muted); font-size:0.75em; margin-top:8px; line-height:1.5; }}
  .sources p a {{ font-size:inherit; }}
  @media(min-width:768px) {{ body {{ max-width:860px; margin:0 auto; padding:24px; }} }}
</style>
</head>
<body>
<div class="header">
  <h1><img src="ace.png" class="logo" alt="" aria-hidden="true"> What Is ACE?</h1>
  <button class="theme-btn" id="themeBtn" onclick="toggleTheme()" aria-label="Toggle light and dark theme">☀</button>
</div>
<div class="updated">Updated: {now.strftime('%B %d, %Y at %H:%M UTC')}</div>
<div class="nav-link"><a href="/">← Current Season</a><a href="history.html">📊 Season History</a><a href="records.html">🏆 Records</a></div>

<section class="card">
  <h2>Accumulated Cyclone Energy</h2>
  <p><b>ACE</b> measures how much energy a storm, or a whole hurricane season, produced. It combines
  <b>how strong</b> storms were and <b>how long</b> they lasted. One long-lived major hurricane can out-score
  a dozen short, weak tropical storms, so ACE says more about a season than simply counting storms.</p>
  <div class="formula">ACE = Σ V<sub>max</sub>² × 10⁻⁴
    <small>V<sub>max</sub> is a storm's maximum sustained wind in knots, added up every 6 hours
    (00, 06, 12 and 18 UTC) while it is a tropical storm, subtropical storm, or hurricane (≥{MIN_NAMED_STORM_WIND} kt).</small></div>
  <p>Example: a 100 kt hurricane holding steady for one day counts 4 times: 4 × 100² × 10⁻⁴ = <b>4.0 ACE</b>.
  Because wind is squared, a 140 kt storm scores almost 2× as much per day as a 100 kt one.</p>
  <p>A season's ACE is the sum over all of its storms. Depressions and extratropical stages don't count.</p>
</section>

<section class="card">
  <h2>How NOAA classifies a season</h2>
  <p>NOAA uses these seasonal ACE ranges for both the Atlantic and the Eastern Pacific:</p>
  <table>
    <thead><tr><th>Classification</th><th>Season ACE</th></tr></thead>
    <tbody>
      <tr><td><span class="badge b-below">Below Normal</span></td><td>&lt; {t['below_normal']}</td></tr>
      <tr><td><span class="badge b-near">Near Normal</span></td><td>{t['below_normal']}–{t['near_normal_upper']}</td></tr>
      <tr><td><span class="badge b-above">Above Normal</span></td><td>{t['near_normal_upper']}–{t['above_normal_upper']}</td></tr>
      <tr><td><span class="badge b-extreme">Extremely Active</span></td><td>{t['above_normal_upper']}+</td></tr>
    </tbody>
  </table>
  <p>A normal Atlantic season (1991–2020 average) is about <b>{normal_atl}</b> ACE.</p>
</section>

<section class="card calc" id="calculator">
  <h2>ACE calculator</h2>
  <p>Enter a storm's maximum sustained wind for each 6-hour period, separated by commas or spaces.</p>
  <label for="calcWinds">Wind speed per 6-hour period</label>
  <textarea id="calcWinds" inputmode="decimal">35, 45, 60, 75, 90, 110, 120, 110, 90, 70, 50, 35</textarea>
  <label for="calcUnit">Units</label>
  <select id="calcUnit">
    <option value="kt">knots (kt)</option>
    <option value="mph">miles per hour (mph)</option>
    <option value="kmh">kilometers per hour (km/h)</option>
  </select>
  <div class="calc-row">
    <button type="button" onclick="calcPreset('ts')">Tropical storm, 2 days</button>
    <button type="button" onclick="calcPreset('major')">Major hurricane, 5 days</button>
    <button type="button" onclick="calcPreset('cat5')">Cat 5, 3 days</button>
  </div>
  <div class="calc-out" aria-live="polite">
    <div class="calc-ace" id="calcAce">—</div>
    <div class="calc-note" id="calcNote"></div>
  </div>
</section>
{facts_html}
<div class="sources">
  <h4>Sources</h4>
  <p><a href="https://www.cpc.ncep.noaa.gov/products/outlooks/background_information.shtml" target="_blank" rel="noopener noreferrer">NOAA Climate Prediction Center</a>: ACE definition and season classifications.
  <a href="https://www.nhc.noaa.gov/data/#hurdat" target="_blank" rel="noopener noreferrer">NOAA HURDAT2</a>: storm data used for this site's numbers ({START_YEAR}–present).</p>
  <p>This site is maintained by a hurricane data enthusiast, not a meteorologist. For forecasts, watches and warnings, always use the <a href="https://www.nhc.noaa.gov/" target="_blank" rel="noopener noreferrer">National Hurricane Center</a>.</p>
</div>
<script>
var CALC_NORMAL={normal_atl}, CALC_MIN_KT={MIN_NAMED_STORM_WIND};
var CALC_PRESETS={{ts:'40 45 50 50 50 45 40 35', major:'40 55 70 90 105 115 120 115 110 100 90 80 70 60 50 45 40 35 35 35', cat5:'100 120 140 150 150 145 140 130 120 110 100 90'}};
function calcPreset(k){{document.getElementById('calcWinds').value=CALC_PRESETS[k];document.getElementById('calcUnit').value='kt';calcAce();}}
function calcAce(){{
  var unit=document.getElementById('calcUnit').value;
  var toKt=unit==='mph'?0.868976:unit==='kmh'?0.539957:1;
  var vals=document.getElementById('calcWinds').value.split(/[\\s,;]+/).filter(function(s){{return s!=='';}});
  var sum=0, used=0, skipped=0, bad=0;
  vals.forEach(function(s){{
    var v=parseFloat(s);
    if(!isFinite(v)||v<0){{bad++;return;}}
    var kt=v*toKt;
    if(kt>=CALC_MIN_KT){{sum+=kt*kt;used++;}}else{{skipped++;}}
  }});
  var ace=sum/10000;
  document.getElementById('calcAce').textContent=ace.toFixed(2)+' ACE';
  var note=used+' of '+vals.length+' periods counted ('+(used*6/24).toFixed(2).replace(/\\.?0+$/,'')+' days as a storm)';
  if(skipped)note+='; '+skipped+' under '+CALC_MIN_KT+' kt not counted';
  if(bad)note+='; '+bad+' not a number';
  note+='. That is '+(ace/CALC_NORMAL*100).toFixed(1)+'% of a normal Atlantic season.';
  document.getElementById('calcNote').textContent=note;
}}
document.getElementById('calcWinds').addEventListener('input',calcAce);
document.getElementById('calcUnit').addEventListener('change',calcAce);
calcAce();
function toggleTheme() {{
  var h=document.documentElement;
  var light=h.getAttribute('data-theme')==='light';
  h.setAttribute('data-theme',light?'dark':'light');
  try{{localStorage.setItem('ace-theme',light?'dark':'light');}}catch(e){{}}
  document.getElementById('themeBtn').textContent=light?'☀':'☾';document.getElementById('themeBtn').setAttribute('aria-label',document.documentElement.getAttribute('data-theme')==='light'?'Switch to dark mode':'Switch to light mode');
}}
document.getElementById('themeBtn').textContent=document.documentElement.getAttribute('data-theme')==='light'?'☾':'☀';document.getElementById('themeBtn').setAttribute('aria-label',document.documentElement.getAttribute('data-theme')==='light'?'Switch to dark mode':'Switch to light mode');
</script>
<!-- Cloudflare Web Analytics --><script defer src='https://static.cloudflareinsights.com/beacon.min.js' data-cf-beacon='{{"token": "775dfcf117b94ff59e3c118c330d02aa"}}'></script><!-- End Cloudflare Web Analytics -->
</body>
</html>'''

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
    START_YEAR,
    get_category,
    get_noaa_classification,
    get_season_projection,
    fetch_nhc_disturbances,
    fetch_active_storm_cones,
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



def _intensity_bar_html(track_points):
    """Horizontal color bar showing intensity progression across all track points."""
    if not track_points:
        return ''
    segs = ''.join(
        f'<div class="intensity-seg" style="flex:1;background:{_track_status_color(p["status"],p["wind"])}" '
        f'title="{p["status"]} {p["wind"]}kt {p["time"]}"></div>'
        for p in track_points
    )
    return f'<div class="intensity-bar">{segs}</div>'



def _year_storm_list_html(storms_list):
    """Inline HTML list of storms for the history page accordion."""
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
            f'<span class="ys-name">{html_escape(s["name"])}{lf_html}</span>'
            f'<span class="ys-cat" data-tip="Peak intensity">{s["category"]}</span>'
            f'<span class="ys-ace">{s["ace"]:.1f}</span>'
            f'<div class="ys-bar"><div class="ys-bar-fill" style="width:{bar_pct}%"></div></div>'
            f'</div>'
        )
    return '\n'.join(rows)



# ===============================================================================
# DASHBOARD SECTIONS
# ===============================================================================

def _season_progress_html(basin_key, season_year):
    today = datetime.now().date()
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
    above_count = sum(1 for v in totals if v >= 127)
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

    issued_html = f'<span class="nhc-issued">Data as of {html_escape(issued)}</span>' if issued else ''

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


def _season_projection_html(current_ace, basin_key):
    """Render the 'what would it take?' daily-ACE-rate projection widget."""
    projection = get_season_projection(current_ace, basin_key)
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
    now = datetime.now(timezone.utc)

    def storm_rows_html(current, cone_images):
        storms = current['storms']
        details = current.get('storm_details', {})
        total = current['total']
        sorted_storms = sorted(storms.items(), key=lambda x: x[1], reverse=True)
        rows = []
        track_data = {}
        for name, ace in sorted_storms:
            d = details.get(name, {})
            pct = (ace / total * 100) if total > 0 else 0
            wind = d.get('max_wind', 0)
            cat = get_category(wind) if wind > 0 else '—'
            is_major = wind >= 96
            is_active = d.get('is_active', False)
            track_points = d.get('track_points', [])
            start_date = d.get('start_date', '—')
            slug = name.lower().replace(' ', '-')

            track_data[slug] = {
                'name': name,
                'active': is_active,
                'start': start_date,
                'ace': round(ace, 1),
                'max_wind': wind,
                'category': cat,
                'points': track_points,
            }

            landfall = d.get('landfall', [])
            if landfall:
                lf_cell = ' · '.join(f'{html_escape(loc)} ({html_escape(cat)})' for loc, cat in landfall)
            else:
                lf_cell = '<span class="dash-fish" data-tip="A storm that never made landfall and just pissed off fish">Fish Storm</span>'

            row_classes = 'storm-row'
            if is_major:
                row_classes += ' major'
            if is_active:
                row_classes += ' active-storm-row'

            active_dot = '<span class="active-pulse"></span> ' if is_active else ''
            active_badge = '<div class="active-badge"><span class="active-pulse"></span> Active Storm</div>' if is_active else ''
            nhc_link = ('<div class="nhc-link"><a href="https://www.nhc.noaa.gov/" target="_blank" rel="noopener">'
                        'View NHC Active Storms →</a></div>') if is_active else ''

            cone_img = ''
            if is_active and cone_images.get(name):
                cone_img = (
                    f'<div class="cone-graphic">'
                    f'<img src="{html_escape(cone_images[name])}" alt="NHC forecast cone for {html_escape(name)}" loading="lazy">'
                    f'<div class="cone-credit">Forecast cone via <a href="https://www.nhc.noaa.gov/" target="_blank" rel="noopener">NHC</a></div>'
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
                f'<div class="meta-box"><div class="meta-label">Peak Intensity</div><div class="meta-value">{wind} kt</div><div class="meta-sub">{cat}</div></div>'
                f'<div class="meta-box"><div class="meta-label">ACE</div><div class="meta-value">{ace:.1f}</div><div class="meta-sub">{pct:.0f}% of season</div></div>'
                f'</div>'
            )

            map_div = (
                f'<div class="track-map-wrap">'
                f'<div class="track-map" id="trmap-{slug}"></div>'
                f'<div class="track-map-skeleton" id="trskel-{slug}"><div class="skeleton-spinner"></div></div>'
                f'</div>'
            ) if track_points else (
                '<p style="color:var(--muted);font-size:0.82em;text-align:center;padding:8px 0">No track data available</p>')

            panel_inner = f'{active_badge}{meta}{ibar}{legend}{map_div}{cone_img}{nhc_link}'

            rows.append(
                f'<tr class="{row_classes}" id="storm-row-{slug}">'
                f'<td data-v="{html_escape(name)}"><button class="storm-name-btn" id="trbtn-{slug}" onclick="toggleTrack(\'{slug}\')">'
                f'{active_dot}{html_escape(name)}<span class="storm-chevron">&#9658;</span></button>'
                f'<button class="storm-share-btn" type="button" data-tip="Copy link to this storm" '
                f'aria-label="Copy link to {html_escape(name)}" onclick="copyStormLink(event,\'{slug}\')">&#128279;</button></td>'
                f'<td data-v="{ace:.6f}">{ace:.1f}</td>'
                f'<td data-v="{pct:.4f}">{pct:.1f}%</td>'
                f'<td data-v="{wind}">{cat}</td>'
                f'<td data-v="{wind}">{wind if wind > 0 else "—"}</td>'
                f'<td class="lf-cell">{lf_cell}</td>'
                f'</tr>'
                f'<tr class="track-row" id="track-row-{slug}">'
                f'<td colspan="6"><div class="track-panel" id="trpanel-{slug}"><div class="track-inner">{panel_inner}</div></div></td>'
                f'</tr>'
            )
        return '\n'.join(rows), track_data

    def insight_items_html(insights):
        return '\n'.join(f'<li>{i}</li>' for i in insights)

    sections = []
    all_track_data = {}
    all_pace_data = {}
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

        details = current.get('storm_details', {})
        cone_images = fetch_active_storm_cones(bd['basin_key'], details)
        named = len(details)
        hurricanes = sum(1 for d in details.values() if d.get('max_wind', 0) >= 64)
        majors = sum(1 for d in details.values() if d.get('max_wind', 0) >= 96)

        preseason = not current['storms'] and current_year == datetime.now().year

        if preseason:
            lower_section = _preseason_html(bd['basin_key'], yearly_totals, current_year)
        else:
            all_years = list(yearly_totals.items()) + [(current_year, current_ace)]
            all_years.sort(key=lambda x: x[1], reverse=True)
            rank = next(i + 1 for i, (y, _) in enumerate(all_years) if y == current_year)
            total_seasons = len(all_years)
            storm_html, track_data = storm_rows_html(current, cone_images)
            all_track_data.update(track_data)
            lower_section = f'''
      <h3>Storm Breakdown</h3>
      <div class="table-wrap">
        <table>
          <thead><tr>
            <th class="sort-th" onclick="sortDash(this,0,'s')">Storm <span class="sa"></span></th>
            <th class="sort-th" onclick="sortDash(this,1,'n')">ACE <span class="sa">&#9660;</span></th>
            <th class="sort-th" onclick="sortDash(this,2,'n')">% <span class="sa"></span></th>
            <th class="sort-th" onclick="sortDash(this,3,'n')">Category <span class="sa"></span></th>
            <th class="sort-th" onclick="sortDash(this,4,'n')">Wind (kt) <span class="sa"></span></th>
            <th>Landfall</th>
          </tr></thead>
          <tbody id="storm-{bd['basin_key']}">
            {storm_html}
          </tbody>
          <tfoot>
            <tr class="total-row"><td><b>TOTAL</b></td><td><b>{current_ace:.1f}</b></td><td><b>100%</b></td><td></td><td></td><td></td></tr>
          </tfoot>
        </table>
      </div>

      <h3>Season Insights</h3>
      <ul class="insights">{insight_items_html(insights)}</ul>
      {_season_projection_html(current_ace, bd['basin_key'])}'''

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
            all_years = list(yearly_totals.items()) + [(current_year, current_ace)]
            all_years.sort(key=lambda x: x[1], reverse=True)
            rank = next(i + 1 for i, (y, _) in enumerate(all_years) if y == current_year)
            total_seasons = len(all_years)
            stats_grid = f'''
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
      </div>'''

        disturbances   = fetch_nhc_disturbances(bd['basin_key'])
        nhc_alert      = _nhc_alert_html(disturbances)

        ace_pace = bd.get('ace_pace')
        pace_section = _ace_pace_html(ace_pace, bd['basin_key'])
        if ace_pace:
            all_pace_data[bd['basin_key']] = ace_pace

        sections.append(f'''
    <div class="basin-card" id="{bd['basin_key']}">
      <h2>{basin['name']} — {current_year} Season</h2>
      {_season_progress_html(bd['basin_key'], current_year)}
      {nhc_alert}
      {stats_grid}
      {pace_section}
      {lower_section}
    </div>''')

    # Escape </ sequences so the JSON blobs can't break out of the <script> tag
    _track_json = json.dumps(all_track_data).replace('</', '<\\/')
    _pace_json = json.dumps(all_pace_data).replace('</', '<\\/')

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="Track the current Atlantic and Eastern Pacific hurricane season ACE (Accumulated Cyclone Energy) in real time. Updated every 6 hours during hurricane season.">
<meta name="theme-color" content="#4fc3f7">
<link rel="canonical" href="https://aceofcanes.com/">
<meta property="og:type" content="website">
<meta property="og:site_name" content="ACE Tracker">
<meta property="og:url" content="https://aceofcanes.com/">
<meta property="og:title" content="Hurricane ACE Dashboard | aceofcanes.com">
<meta property="og:description" content="Track Accumulated Cyclone Energy (ACE) for the Atlantic and Eastern Pacific hurricane seasons in real time. Updated every 6 hours from official NOAA data.">
<meta property="og:image" content="https://aceofcanes.com/ace_preview.png">
<meta property="og:image:width" content="766">
<meta property="og:image:height" content="976">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Hurricane ACE Dashboard | aceofcanes.com">
<meta name="twitter:description" content="Track Accumulated Cyclone Energy (ACE) for the Atlantic and Eastern Pacific hurricane seasons in real time. Updated every 6 hours from official NOAA data.">
<meta name="twitter:image" content="https://aceofcanes.com/ace_preview.png">
<link rel="icon" type="image/png" href="ace.png">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha384-sHL9NAb7lN7rfvG5lfHpm643Xkcjzp4jFvuavGOndn6pjVqS6ny56CAt3nsEVT4H" crossorigin="anonymous" />
<title>Hurricane ACE Dashboard | aceofcanes.com</title>
<script>(function(){{try{{var t=localStorage.getItem('ace-theme');if(t==='light')document.documentElement.setAttribute('data-theme','light');}}catch(e){{}}}})();</script>
<style>
  :root {{
    --bg:#0a1628; --card:#132238; --box:#1a2d4a; --accent:#4fc3f7; --accent2:#29b6f6;
    --accent-h3:#81d4fa; --text:#e0e6ed; --text-strong:#ffffff; --muted:#78909c;
    --muted-dark:#546e7a; --border:#1e3a5f; --danger:#ef5350; --danger-bg:#2a1a1a;
    --danger-text:#ef8a80; --total-row:#1a2d4a; --sources-bg:#0d1b2a; --gauge-bg:#1e3a5f;
    --pace-last:#ffb74d;
  }}
  [data-theme="light"] {{
    --bg:#f0f4f8; --card:#ffffff; --box:#e8f0fe; --accent:#0277bd; --accent2:#0288d1;
    --accent-h3:#01579b; --text:#1a2d4a; --text-strong:#0a1628; --muted:#607d8b;
    --muted-dark:#455a64; --border:#b0bec5; --danger:#d32f2f; --danger-bg:#ffeaea;
    --danger-text:#c62828; --total-row:#e8f0fe; --sources-bg:#e2ecf7; --gauge-bg:#c9daf8;
    --pace-last:#e65100;
  }}
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background:var(--bg); color:var(--text); padding:12px; transition:background 0.2s,color 0.2s; }}
  .header {{ display:grid; grid-template-columns:1fr auto 1fr; align-items:center; margin:8px 0; padding:0 4px; }}
  h1 {{ grid-column:2; color:var(--accent); font-size:1.4em; text-align:center; display:flex; align-items:center; justify-content:center; gap:8px; }}
  .logo {{ height:1.5em; width:auto; vertical-align:middle; }}
  .theme-btn {{ grid-column:3; justify-self:end; background:transparent; border:1px solid var(--accent); color:var(--accent); border-radius:20px; padding:4px 10px; cursor:pointer; font-size:0.9em; }}
  .updated {{ text-align:center; color:var(--muted); font-size:0.8em; margin-bottom:8px; }}
  .nav-link {{ text-align:center; margin-bottom:12px; }}
  .nav-link a {{ color:var(--accent); text-decoration:none; font-size:0.85em; border:1px solid var(--accent); border-radius:20px; padding:4px 14px; }}
  .nav-link a:hover {{ background:var(--accent); color:var(--bg); }}
  .ace-explain {{ background:var(--box); border-radius:8px; padding:10px 14px; margin-bottom:14px; font-size:0.85em; }}
  .ace-explain summary {{ color:var(--accent); cursor:pointer; list-style:none; display:flex; align-items:center; gap:6px; min-height:44px; }}
  .ace-explain summary::-webkit-details-marker {{ display:none; }}
  .ace-explain summary::before {{ content:'ℹ'; font-size:1.1em; }}
  .ace-explain-hint {{ color:var(--muted); font-size:0.85em; }}
  .ace-explain p {{ color:var(--text); line-height:1.6; margin-top:8px; padding-top:8px; border-top:1px solid var(--border); }}
  .toggle {{ display:flex; justify-content:center; gap:8px; margin-bottom:16px; }}
  .toggle button {{ padding:8px 20px; border:1px solid var(--accent); background:transparent; color:var(--accent); border-radius:20px; cursor:pointer; font-size:0.9em; }}
  .toggle button.active {{ background:var(--accent); color:var(--bg); font-weight:bold; }}
  .basin-card {{ background:var(--card); border-radius:12px; padding:16px; margin-bottom:16px; display:none; }}
  .basin-card.active {{ display:block; }}
  h2 {{ color:var(--accent); font-size:1.2em; margin-bottom:12px; border-bottom:1px solid var(--border); padding-bottom:8px; }}
  h3 {{ color:var(--accent-h3); font-size:1em; margin:16px 0 8px; }}
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
  th.sort-th:hover {{ color:var(--text-strong); }}
  .sa {{ font-size:0.7em; margin-left:2px; opacity:0.7; }}
  td {{ padding:6px; border-bottom:1px solid var(--border); color:var(--text); }}
  tr.major {{ background:var(--danger-bg); }}
  tr.major td {{ color:var(--danger-text); font-weight:bold; }}
  tr.total-row {{ background:var(--total-row); }}
  .insights {{ list-style:none; padding:0; }}
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
  .global-tip {{ display:none; position:fixed; background:var(--card-bg,#1a1a2e); color:var(--text); border:1px solid var(--border); padding:5px 11px; border-radius:6px; font-size:0.82em; pointer-events:none; z-index:9999; max-width:320px; line-height:1.4; box-shadow:0 2px 8px rgba(0,0,0,0.4); }}
  .active-pulse {{ display:inline-block; width:7px; height:7px; border-radius:50%; background:#4caf50; box-shadow:0 0 0 0 rgba(76,175,80,0.7); animation:trpulse 1.5s infinite; flex-shrink:0; }}
  @keyframes trpulse {{ 0%{{box-shadow:0 0 0 0 rgba(76,175,80,0.7);}} 70%{{box-shadow:0 0 0 6px rgba(76,175,80,0);}} 100%{{box-shadow:0 0 0 0 rgba(76,175,80,0);}} }}
  tr.active-storm-row {{ border-left:3px solid #4caf50; }}
  .track-row td {{ padding:0; border-bottom:2px solid var(--border); }}
  .track-panel {{ overflow:hidden; max-height:0; transition:max-height 0.35s ease; background:var(--card); }}
  .track-panel.open {{ max-height:1500px; }}
  .track-inner {{ padding:12px 14px 14px; }}
  .track-map {{ height:320px; border-radius:8px; border:1px solid var(--border); margin-bottom:10px; }}
  .track-map-wrap {{ position:relative; margin-bottom:10px; }}
  .track-map-wrap .track-map {{ margin-bottom:0; }}
  .track-map-skeleton {{ position:absolute; inset:0; display:flex; align-items:center; justify-content:center; background:var(--box); border-radius:8px; border:1px solid var(--border); }}
  .skeleton-spinner {{ width:28px; height:28px; border-radius:50%; border:3px solid var(--border); border-top-color:var(--accent); animation:skeleton-spin 0.8s linear infinite; }}
  @keyframes skeleton-spin {{ to {{ transform:rotate(360deg); }} }}
  .storm-meta {{ display:grid; grid-template-columns:repeat(3,1fr); gap:8px; margin-bottom:10px; }}
  .meta-box {{ background:var(--box); border-radius:6px; padding:8px 10px; }}
  .meta-label {{ color:var(--muted); font-size:0.72em; text-transform:uppercase; }}
  .meta-value {{ color:var(--text-strong); font-size:0.95em; font-weight:bold; }}
  .meta-sub {{ color:var(--muted); font-size:0.72em; }}
  .active-badge {{ display:inline-flex; align-items:center; gap:5px; background:#0d2a14; border:1px solid #4caf50; border-radius:12px; padding:3px 8px; font-size:0.75em; color:#4caf50; margin-bottom:8px; }}
  .intensity-bar {{ display:flex; height:8px; border-radius:4px; overflow:hidden; margin-bottom:10px; }}
  .intensity-seg {{ flex-shrink:0; }}
  .track-legend {{ display:flex; flex-wrap:wrap; gap:6px; margin-bottom:8px; }}
  .legend-item {{ display:flex; align-items:center; gap:4px; font-size:0.72em; color:var(--muted); }}
  .legend-dot {{ width:9px; height:9px; border-radius:50%; flex-shrink:0; }}
  .nhc-link {{ font-size:0.78em; color:var(--muted); text-align:right; margin-top:6px; }}
  .nhc-link a {{ color:var(--accent); text-decoration:none; }}
  .nhc-link a:hover {{ text-decoration:underline; }}
  .pace-chart-wrap {{ position:relative; height:240px; margin:12px 0 4px; }}
  .pace-stats-mini {{ display:grid; grid-template-columns:repeat(3,1fr); gap:8px; margin:10px 0 4px; }}
  .pace-caption {{ color:var(--muted); font-size:0.78em; text-align:center; margin-top:2px; }}
  @media(min-width:768px) {{ .pace-chart-wrap {{ height:300px; }} }}
  .cone-graphic {{ margin-bottom:10px; }}
  .cone-graphic img {{ display:block; width:100%; height:auto; border-radius:8px; border:1px solid var(--border); }}
  .cone-credit {{ font-size:0.72em; color:var(--muted); text-align:center; margin-top:4px; }}
  .cone-credit a {{ color:var(--accent); text-decoration:none; }}
  .cone-credit a:hover {{ text-decoration:underline; }}
</style>
</head>
<body>
<div class="header">
  <h1><img src="ace.png" class="logo" alt="ACE"> Hurricane ACE Dashboard</h1>
  <button class="theme-btn" id="themeBtn" onclick="toggleTheme()">☀</button>
</div>
<div class="updated">Updated: {now.strftime('%B %d, %Y at %H:%M UTC')}</div>
<div class="nav-link"><a href="history.html">📊 Season History ({START_YEAR}–present)</a></div>
<details class="ace-explain">
  <summary>What is ACE? <span class="ace-explain-hint">(tap to expand)</span></summary>
  <p>Accumulated Cyclone Energy (ACE) measures total hurricane season activity by combining storm intensity and duration. A major hurricane that lasts two weeks contributes far more than a brief tropical storm. NOAA uses seasonal ACE totals to classify years as <b>Below Normal</b> (&lt;73), <b>Near Normal</b> (73–126), <b>Above Normal</b> (126–159), or <b>Extremely Active</b> (159+).</p>
</details>
<div class="toggle">
  <button class="active" onclick="show('atlantic',this)">Atlantic</button>
  <button onclick="show('pacific',this)">E/C Pacific</button>
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
  <p class="kofi-link"><a href="https://ko-fi.com/aceofcanes" target="_blank" rel="noopener noreferrer">☕ Support this project on Ko-fi</a></p>
</div>
<script>
document.querySelectorAll('.basin-card')[0]?.classList.add('active');
function show(id,btn) {{
  document.querySelectorAll('.basin-card').forEach(c=>c.classList.remove('active'));
  document.querySelectorAll('.toggle button').forEach(b=>b.classList.remove('active'));
  document.getElementById(id)?.classList.add('active');
  btn.classList.add('active');
  try{{history.replaceState(null,'','#'+id);}}catch(e){{}}
  _renderPaceChart(id);
}}
function toggleTheme() {{
  var h=document.documentElement;
  var light=h.getAttribute('data-theme')==='light';
  h.setAttribute('data-theme',light?'dark':'light');
  try{{localStorage.setItem('ace-theme',light?'dark':'light');}}catch(e){{}}
  document.getElementById('themeBtn').textContent=light?'☀':'☾';
  _restylePaceCharts();
}}
function copyStormLink(e,slug) {{
  var url=location.origin+location.pathname+'#storm-row-'+slug;
  var btn=e.currentTarget;
  function done(ok) {{
    var prev=btn.innerHTML;
    btn.innerHTML=ok?'&#10003;':'&#9888;';
    setTimeout(function(){{btn.innerHTML=prev;}},1400);
  }}
  if(navigator.clipboard&&navigator.clipboard.writeText) {{
    navigator.clipboard.writeText(url).then(function(){{done(true);}},function(){{done(false);}});
  }} else {{
    try {{
      var ta=document.createElement('textarea');
      ta.value=url;ta.style.position='fixed';ta.style.opacity='0';
      document.body.appendChild(ta);ta.select();document.execCommand('copy');document.body.removeChild(ta);
      done(true);
    }} catch(err) {{ done(false); }}
  }}
}}
document.addEventListener('DOMContentLoaded',function() {{
  document.getElementById('themeBtn').textContent=document.documentElement.getAttribute('data-theme')==='light'?'☾':'☀';
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
function _renderPaceChart(basinKey){{
  if(_paceCharts[basinKey])return;
  var d=ACE_PACE[basinKey];
  var el=document.getElementById('pace-canvas-'+basinKey);
  if(!d||!el||typeof Chart==='undefined')return;
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
var _trMaps={{}};
var _SC={{TD:'#9e9e9e',TS:'#81d4fa',SS:'#81d4fa'}};
function _tc(st,w){{
  if(st==='HU'){{if(w>=137)return'#b71c1c';if(w>=113)return'#ef5350';if(w>=96)return'#ff8a65';if(w>=83)return'#ffb74d';return'#ffe082';}}
  return _SC[st]||'#9e9e9e';
}}
function toggleTrack(slug){{
  var panel=document.getElementById('trpanel-'+slug);
  var btn=document.getElementById('trbtn-'+slug);
  if(!panel)return;
  var open=panel.classList.contains('open');
  if(open){{panel.classList.remove('open');if(btn)btn.classList.remove('open');return;}}
  panel.classList.add('open');
  if(btn)btn.classList.add('open');
  if(!_trMaps[slug]){{_trMaps[slug]=true;setTimeout(function(){{_buildMap(slug);}},25);}}
}}
function _hideTrackSkeleton(slug){{
  var sk=document.getElementById('trskel-'+slug);
  if(sk)sk.style.display='none';
}}
function _buildMap(slug){{
  var d=ACE_TRACKS[slug];
  var el=document.getElementById('trmap-'+slug);
  if(!d||!d.points||!d.points.length||!el||el._leaflet_id){{_hideTrackSkeleton(slug);return;}}
  var map=L.map(el,{{zoomControl:true,attributionControl:true}});
  var tiles=L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png',{{
    attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>',
    subdomains:'abcd',maxZoom:10
  }}).addTo(map);
  tiles.on('load',function(){{_hideTrackSkeleton(slug);}});
  setTimeout(function(){{_hideTrackSkeleton(slug);}},4000);
  var pts=d.points,lls=pts.map(function(p){{return[p.lat,p.lon];}});
  for(var i=0;i<pts.length-1;i++){{
    L.polyline([[pts[i].lat,pts[i].lon],[pts[i+1].lat,pts[i+1].lon]],{{color:_tc(pts[i].status,pts[i].wind),weight:5,opacity:1}}).addTo(map);
  }}
  pts.forEach(function(p,i){{
    var c=_tc(p.status,p.wind),last=(i===pts.length-1);
    var mk=L.circleMarker([p.lat,p.lon],{{radius:last?7:4,fillColor:c,color:last?'#fff':c,weight:last?2:1,fillOpacity:1,opacity:1}}).addTo(map);
    mk.bindTooltip('<b>'+d.name+'</b><br>'+p.time+'<br>'+p.status+' \xb7 '+p.wind+'kt',{{direction:'top',offset:[0,-6]}});
    if(last&&d.active)mk.bindPopup('<b>Current Position</b><br>'+p.time+'<br>'+p.status+' \xb7 '+p.wind+'kt',{{maxWidth:160}}).openPopup();
  }});
  if(lls.length)map.fitBounds(L.latLngBounds(lls),{{padding:[50,50],maxZoom:6}});
}}
</script>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" integrity="sha384-cxOPjt7s7Iz04uaHJceBmS+qpjv2JkIHNVcuOrM+YHwZOmJGBXI00mdUXEq65HTH" crossorigin="anonymous"></script>
<script src="https://unpkg.com/chart.js@4.5.1/dist/chart.umd.min.js" integrity="sha384-jb8JQMbMoBUzgWatfe6COACi2ljcDdZQ2OxczGA3bGNeWe+6DChMTBJemed7ZnvJ" crossorigin="anonymous"></script>
<div id="global-tip" class="global-tip"></div>
<script>
(function(){{
  var tip=document.getElementById('global-tip');
  function show(e){{var t=e.currentTarget.getAttribute('data-tip');if(!t)return;tip.textContent=t;tip.style.display='block';move(e);}}
  function move(e){{var x=e.clientX,y=e.clientY,w=tip.offsetWidth,h=tip.offsetHeight;tip.style.left=Math.min(x+14,window.innerWidth-w-8)+'px';tip.style.top=Math.max(y-h-8,8)+'px';}}
  function hide(){{tip.style.display='none';}}
  document.querySelectorAll('[data-tip]').forEach(function(el){{el.addEventListener('mouseenter',show);el.addEventListener('mousemove',move);el.addEventListener('mouseleave',hide);}});
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
    for bd in basin_data:
        if not bd:
            continue
        basin = BASINS[bd['basin_key']]
        current = bd['current']
        yearly_totals = bd['yearly_totals']
        yearly_stats = bd.get('yearly_stats')
        current_year = current['year']
        normal = basin['normal_ace']

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
        today = datetime.now().date()
        if bd['basin_key'] == 'atlantic':
            _season_start = datetime(current_year, 6, 1).date()
        else:
            _season_start = datetime(current_year, 5, 15).date()
        _season_end = datetime(current_year, 11, 30).date()
        _in_active_season = _season_start <= today <= _season_end and current_year == datetime.now().year
        if current_ace > 0 or named > 0 or _in_active_season:
            current_storms_list = sorted(
                [{'name': n, 'ace': round(d.get('ace', 0), 2),
                  'category': get_category(d.get('max_wind', 0)), 'max_wind': d.get('max_wind', 0)}
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
            storm_list_html = _year_storm_list_html(d.get('storms_list', []))
            rows.append(
                f'<tr class="{row_cls} yr-data-row" id="{yr_key}">'
                f'<td data-v="{year}" style="white-space:nowrap">'
                f'<button class="yr-expand-btn" id="yrbtn-{yr_key}" onclick="toggleYear(\'{yr_key}\')">'
                f'<b>{year}</b>{active_label}<span class="yr-chevron">&#9658;</span></button></td>'
                f'<td data-v="{ace:.4f}"><b>{ace:.1f}</b><div class="ace-bar"><div class="ace-bar-fill" style="width:{ace_bar_pct}%"></div></div></td>'
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
                f'<div class="yr-panel-inner">{storm_list_html}</div>'
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

        basin_sections.append(f'''
    <div class="basin-card" id="{bd['basin_key']}">
      <h2>{basin['name']} — All Seasons ({START_YEAR}–{current_year})</h2>
      <p class="season-note">{total_seasons} seasons &nbsp;·&nbsp; ● = currently active &nbsp;·&nbsp; <span style="border-left:3px solid #f9a825;padding-left:4px;">gold border</span> = top 5 all-time ACE &nbsp;·&nbsp; click headers to sort</p>
      <div class="table-wrap">
        <table class="hist-table">
          <thead>
            <tr>
              <th class="sort-th" onclick="sortHist(this,0,'n')">Year <span class="sa">▼</span></th>
              <th class="sort-th" onclick="sortHist(this,1,'n')">ACE <span class="sa"></span></th>
              <th class="sort-th" onclick="sortHist(this,2,'n')">% Normal <span class="sa"></span></th>
              <th class="sort-th" onclick="sortHist(this,3,'n')">Classification <span class="sa"></span></th>
              <th class="sort-th" onclick="sortHist(this,4,'n')">Named <span class="sa"></span></th>
              <th class="sort-th" onclick="sortHist(this,5,'n')">Hurr. <span class="sa"></span></th>
              <th class="sort-th" onclick="sortHist(this,6,'n')">Major <span class="sa"></span></th>
              <th class="sort-th" onclick="sortHist(this,7,'s')">ACE Leader <span class="sa"></span></th>
              <th class="sort-th" onclick="sortHist(this,8,'n')">Rank <span class="sa"></span></th>
            </tr>
          </thead>
          <tbody id="hist-{bd['basin_key']}">{''.join(rows)}</tbody>
          <tfoot>{avg_row}</tfoot>
        </table>
      </div>
    </div>''')

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="Compare every Atlantic and Eastern Pacific hurricane season from 1991 to present by ACE, storm counts, and NOAA activity classifications.">
<meta name="theme-color" content="#4fc3f7">
<link rel="canonical" href="https://aceofcanes.com/history.html">
<meta property="og:type" content="website">
<meta property="og:site_name" content="ACE Tracker">
<meta property="og:url" content="https://aceofcanes.com/history.html">
<meta property="og:title" content="Season History (1991–present) | aceofcanes.com">
<meta property="og:description" content="Compare every Atlantic and Eastern Pacific hurricane season from 1991 to present by ACE, storm counts, and NOAA activity classifications.">
<meta property="og:image" content="https://aceofcanes.com/ace_preview.png">
<meta property="og:image:width" content="766">
<meta property="og:image:height" content="976">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Season History (1991–present) | aceofcanes.com">
<meta name="twitter:description" content="Compare every Atlantic and Eastern Pacific hurricane season from 1991 to present by ACE, storm counts, and NOAA activity classifications.">
<meta name="twitter:image" content="https://aceofcanes.com/ace_preview.png">
<link rel="icon" type="image/png" href="ace.png">
<title>Season History (1991–present) | aceofcanes.com</title>
<script>(function(){{try{{var t=localStorage.getItem('ace-theme');if(t==='light')document.documentElement.setAttribute('data-theme','light');}}catch(e){{}}}})();</script>
<style>
  :root {{
    --bg:#0a1628; --card:#132238; --box:#1a2d4a; --accent:#4fc3f7;
    --text:#e0e6ed; --text-strong:#ffffff; --muted:#78909c; --border:#1e3a5f;
    --sources-bg:#0d1b2a; --gauge-bg:#1e3a5f;
    --row-extreme:rgba(239,83,80,0.10); --row-above:rgba(255,143,0,0.10);
    --row-below:rgba(66,165,245,0.10); --row-near:transparent;
    --current-border:#4fc3f7; --active-dot:#4fc3f7;
    --badge-extreme:#ef5350; --badge-above:#ff8f00; --badge-near:#546e7a; --badge-below:#1976d2;
  }}
  [data-theme="light"] {{
    --bg:#f0f4f8; --card:#ffffff; --box:#e8f0fe; --accent:#0277bd;
    --text:#1a2d4a; --text-strong:#0a1628; --muted:#607d8b; --border:#b0bec5;
    --sources-bg:#e2ecf7; --gauge-bg:#c9daf8;
    --row-extreme:rgba(198,40,40,0.07); --row-above:rgba(230,81,0,0.07);
    --row-below:rgba(21,101,192,0.07); --row-near:transparent;
    --current-border:#0277bd; --active-dot:#0277bd;
    --badge-extreme:#c62828; --badge-above:#e65100; --badge-near:#546e7a; --badge-below:#1565c0;
  }}
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background:var(--bg); color:var(--text); padding:12px; transition:background 0.2s,color 0.2s; }}
  .header {{ display:grid; grid-template-columns:1fr auto 1fr; align-items:center; margin:8px 0; padding:0 4px; }}
  h1 {{ grid-column:2; color:var(--accent); font-size:1.4em; text-align:center; display:flex; align-items:center; justify-content:center; gap:8px; }}
  .logo {{ height:1.5em; width:auto; vertical-align:middle; }}
  .theme-btn {{ grid-column:3; justify-self:end; background:transparent; border:1px solid var(--accent); color:var(--accent); border-radius:20px; padding:4px 10px; cursor:pointer; font-size:0.9em; }}
  .updated {{ text-align:center; color:var(--muted); font-size:0.8em; margin-bottom:8px; }}
  .nav-link {{ text-align:center; margin-bottom:12px; }}
  .nav-link a {{ color:var(--accent); text-decoration:none; font-size:0.85em; border:1px solid var(--accent); border-radius:20px; padding:4px 14px; }}
  .nav-link a:hover {{ background:var(--accent); color:var(--bg); }}
  .ace-explain {{ background:var(--box); border-radius:8px; padding:10px 14px; margin-bottom:14px; font-size:0.85em; }}
  .ace-explain summary {{ color:var(--accent); cursor:pointer; list-style:none; display:flex; align-items:center; gap:6px; min-height:44px; }}
  .ace-explain summary::-webkit-details-marker {{ display:none; }}
  .ace-explain summary::before {{ content:'ℹ'; font-size:1.1em; }}
  .ace-explain-hint {{ color:var(--muted); font-size:0.85em; }}
  .ace-explain p {{ color:var(--text); line-height:1.6; margin-top:8px; padding-top:8px; border-top:1px solid var(--border); }}
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
  .sources {{ background:var(--sources-bg); border-top:1px solid var(--border); margin-top:24px; padding:16px 12px; border-radius:8px; }}
  .sources h4 {{ color:var(--muted); font-size:0.8em; text-transform:uppercase; margin-bottom:8px; }}
  .sources a {{ color:var(--accent); text-decoration:none; font-size:0.78em; }}
  .sources a:hover {{ text-decoration:underline; }}
  .sources p {{ color:var(--muted-dark,#546e7a); font-size:0.75em; margin-top:8px; line-height:1.5; }}
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
  .yr-panel {{ overflow:hidden; max-height:0; transition:max-height 0.3s ease; background:var(--sources-bg); }}
  .yr-panel.open {{ max-height:2000px; }}
  .yr-panel-inner {{ padding:8px 12px 10px; }}
  .ys-row {{ display:grid; grid-template-columns:110px 48px 46px 1fr; align-items:start; gap:6px; padding:5px 0; font-size:0.82em; border-bottom:1px solid var(--border); }}
  .ys-row:last-child {{ border-bottom:none; }}
  .ys-name {{ color:var(--text); font-weight:500; line-height:1.4; }}
  .ys-lf {{ display:block; font-size:0.82em; font-weight:400; color:var(--muted); font-style:italic; margin-top:1px; }}
  .ys-fish {{ color:var(--muted); opacity:0.7; cursor:help; }}
  .ys-cat {{ color:var(--muted); font-size:0.9em; cursor:help; text-decoration:underline dotted; text-underline-offset:2px; }}
  .global-tip {{ display:none; position:fixed; background:var(--card-bg,#1a1a2e); color:var(--text); border:1px solid var(--border); padding:5px 11px; border-radius:6px; font-size:0.82em; pointer-events:none; z-index:9999; max-width:320px; line-height:1.4; box-shadow:0 2px 8px rgba(0,0,0,0.4); }}
  .ys-ace {{ color:var(--accent); font-weight:bold; text-align:right; }}
  .ys-bar {{ height:4px; background:var(--gauge-bg); border-radius:2px; }}
  .ys-bar-fill {{ height:100%; background:var(--accent); border-radius:2px; }}
</style>
</head>
<body>
<div class="header">
  <h1><img src="ace.png" class="logo" alt="ACE"> Hurricane ACE History</h1>
  <button class="theme-btn" id="themeBtn" onclick="toggleTheme()">☀</button>
</div>
<div class="updated">Updated: {now.strftime('%B %d, %Y at %H:%M UTC')}</div>
<div class="nav-link"><a href="index.html">← Current Season</a></div>
<details class="ace-explain">
  <summary>What is ACE? <span class="ace-explain-hint">(tap to expand)</span></summary>
  <p>Accumulated Cyclone Energy (ACE) measures total hurricane season activity by combining storm intensity and duration. A major hurricane that lasts two weeks contributes far more than a brief tropical storm. NOAA uses seasonal ACE totals to classify years as <b>Below Normal</b> (&lt;73), <b>Near Normal</b> (73–126), <b>Above Normal</b> (126–159), or <b>Extremely Active</b> (159+).</p>
</details>
<div class="toggle">
  <button class="active" onclick="show('atlantic',this)">Atlantic</button>
  <button onclick="show('pacific',this)">E/C Pacific</button>
</div>
<div class="legend">
  <span class="badge badge-extreme">Extremely Active ≥159</span>
  <span class="badge badge-above">Above Normal 126–159</span>
  <span class="badge badge-near">Near Normal 73–126</span>
  <span class="badge badge-below">Below Normal &lt;73</span>
</div>
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
document.querySelectorAll('.basin-card')[0]?.classList.add('active');
function show(id,btn) {{
  document.querySelectorAll('.basin-card').forEach(c=>c.classList.remove('active'));
  document.querySelectorAll('.toggle button').forEach(b=>b.classList.remove('active'));
  document.getElementById(id)?.classList.add('active');
  btn.classList.add('active');
  try{{history.replaceState(null,'','#'+id);}}catch(e){{}}
}}
function toggleTheme() {{
  var h=document.documentElement;
  var light=h.getAttribute('data-theme')==='light';
  h.setAttribute('data-theme',light?'dark':'light');
  try{{localStorage.setItem('ace-theme',light?'dark':'light');}}catch(e){{}}
  document.getElementById('themeBtn').textContent=light?'☀':'☾';
}}
document.addEventListener('DOMContentLoaded',function() {{
  document.getElementById('themeBtn').textContent=document.documentElement.getAttribute('data-theme')==='light'?'☾':'☀';
  var hash=location.hash.replace('#','');
  var match=[].slice.call(document.querySelectorAll('.toggle button')).filter(function(b){{return(b.getAttribute('onclick')||'').indexOf("'"+hash+"'")>=0;}})[0];
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
}}
function toggleYear(key){{
  var panel=document.getElementById('yrpanel-'+key);
  var btn=document.getElementById('yrbtn-'+key);
  if(!panel)return;
  var open=panel.classList.contains('open');
  if(open){{panel.classList.remove('open');if(btn)btn.classList.remove('open');}}
  else{{panel.classList.add('open');if(btn)btn.classList.add('open');}}
}}
</script>
<div id="global-tip" class="global-tip"></div>
<script>
(function(){{
  var tip=document.getElementById('global-tip');
  function show(e){{var t=e.currentTarget.getAttribute('data-tip');if(!t)return;tip.textContent=t;tip.style.display='block';move(e);}}
  function move(e){{var x=e.clientX,y=e.clientY,w=tip.offsetWidth,h=tip.offsetHeight;tip.style.left=Math.min(x+14,window.innerWidth-w-8)+'px';tip.style.top=Math.max(y-h-8,8)+'px';}}
  function hide(){{tip.style.display='none';}}
  document.querySelectorAll('[data-tip]').forEach(function(el){{el.addEventListener('mouseenter',show);el.addEventListener('mousemove',move);el.addEventListener('mouseleave',hide);}});
}})();
</script>
<!-- Cloudflare Web Analytics --><script defer src='https://static.cloudflareinsights.com/beacon.min.js' data-cf-beacon='{{"token": "775dfcf117b94ff59e3c118c330d02aa"}}'></script><!-- End Cloudflare Web Analytics -->
</body>
</html>'''
    return html



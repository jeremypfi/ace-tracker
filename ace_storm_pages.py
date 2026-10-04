"""
One static page per named storm of the current season, at
/storm/<page_slug>.html. Built from build_season_payload() results and the
same panel/map pieces the dashboard uses (ace_html, ace_assets).
"""

import json
from html import escape as html_escape

from ace_assets import (
    BASE_CSS, NAV_CSS, HEADINGS_CSS, STORM_PANEL_CSS, CONE_CSS, STORM_PAGE_CSS,
    WIND_JS, LIB_MISSING_JS, TRACK_MAP_JS, THEME_INIT_JS, LEAFLET_CSS_SRI, LEAFLET_JS_SRI,
)
from ace_data import START_YEAR, SITE_URL
from ace_html import (
    SHARE_IMAGE_ALT, _share_image_meta, _storm_panel_inner_html, _storm_track_entry,
    _parse_utc, _utc_label,
)

FISH_TIP = 'A storm that never made landfall and just pissed off fish'


def storm_page_path(storm):
    """Site-relative path of a storm's page."""
    return f"storm/{storm['page_slug']}.html"


def storm_page_url(storm):
    return f"{SITE_URL}/{storm_page_path(storm)}"


def _wind_phrase(storm):
    if storm['max_wind'] <= 0:
        return 'peak intensity unknown'
    return f"peaked at {storm['max_wind']} kt ({storm['category']})"


def _landfall_html(storm):
    if not storm['landfall']:
        return (f'<p><span class="dash-fish" title="{html_escape(FISH_TIP)}">Fish Storm</span>'
                ' &mdash; no landfall recorded.</p>')
    items = ''.join(f'<li>{html_escape(loc)} ({html_escape(cat)})</li>' for loc, cat in storm['landfall'])
    note = ('<p class="page-note">Estimated from the preliminary track; NHC confirms landfalls in its '
            'post-season Tropical Cyclone Report.</p>') if storm['landfall_estimated'] else ''
    return f'<ul class="lf-list">{items}</ul>{note}'


def _siblings_html(payload, storm):
    items = []
    for s in payload['storms']:
        current = ' aria-current="page"' if s['page_slug'] == storm['page_slug'] else ''
        items.append(f'<li><a href="{html_escape(s["page_slug"])}.html"{current}>{html_escape(s["name"])}</a></li>')
    return ''.join(items)


def render_storm_page_html(payload, storm, share_image=None, share_alt=None):
    """Full HTML for one storm. Pages sit one level below the site root, so
    local assets are reached through '../'."""
    name = html_escape(storm['name'])
    basin = payload['basin_name']
    year = payload['year']
    url = storm_page_url(storm)
    page_title = html_escape(f"{storm['name']} {year}: Track, ACE & Intensity ({basin}) | aceofcanes.com")
    description = html_escape(
        f"{storm['name']} ({basin} {year}) {_wind_phrase(storm)} and has produced {storm['ace']:.1f} ACE, "
        f"{storm['pct_of_season']:.0f}% of the season so far. Track map, intensity timeline and landfalls, "
        "updated every 3 hours from NOAA data.")
    image = share_image or 'ace_preview.png'
    alt = share_alt or SHARE_IMAGE_ALT
    status = 'Active now' if storm['is_active'] else 'No longer active'
    track_json = json.dumps({storm['slug']: _storm_track_entry(storm)}).replace('</', '<\\/')
    as_of = _parse_utc(payload['data_as_of'])
    as_of_html = (f'<p class="data-asof">Best-track data as of <time datetime="{as_of:%Y-%m-%dT%H:%M:%SZ}">'
                  f'{_utc_label(as_of)}</time></p>') if as_of else ''
    panel = _storm_panel_inner_html(storm, asset_prefix='../')
    slug = storm['slug']

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="{description}">
<meta name="theme-color" content="#4fc3f7">
<link rel="canonical" href="{html_escape(url)}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="ACE Tracker">
<meta property="og:url" content="{html_escape(url)}">
<meta property="og:title" content="{page_title}">
<meta property="og:description" content="{description}">
{_share_image_meta(alt, image)}
<meta name="twitter:title" content="{page_title}">
<meta name="twitter:description" content="{description}">
<meta name="twitter:image" content="{html_escape(f"{SITE_URL}/{image}")}">
<link rel="icon" type="image/png" href="../ace.png">
<link rel="alternate" type="application/rss+xml" title="Ace of Canes storm feed" href="../feed.xml">
<link rel="stylesheet" href="../vendor/leaflet-1.9.4/leaflet.css" integrity="{LEAFLET_CSS_SRI}" crossorigin="anonymous" media="print" onload="this.media='all'">
<noscript><link rel="stylesheet" href="../vendor/leaflet-1.9.4/leaflet.css"></noscript>
<title>{page_title}</title>
<script>{THEME_INIT_JS}</script>
<style>
{BASE_CSS}
{NAV_CSS}
{HEADINGS_CSS}
{STORM_PANEL_CSS}
{CONE_CSS}
{STORM_PAGE_CSS}
  .data-asof {{ color:var(--muted); font-size:0.8em; margin:0 0 10px; }}
  .data-asof time {{ color:var(--text); }}
  .dash-fish {{ color:var(--muted); font-style:italic; cursor:help; }}
</style>
</head>
<body>
<div class="container">
<div class="header">
  <h1><img src="../ace.png" class="logo" alt="" aria-hidden="true"> {name} {year}</h1>
  <div class="header-actions">
    <button class="unit-btn" id="unitBtn" onclick="toggleWindUnit()" title="Wind speed unit" aria-label="Wind speed unit: kt">kt</button>
    <button class="theme-btn" id="themeBtn" onclick="toggleTheme()" aria-label="Toggle light and dark theme">☀</button>
  </div>
</div>
<div class="nav-link"><a href="/">← Current Season</a><a href="../history.html">📊 Season History ({START_YEAR}–present)</a><a href="../records.html">🏆 Records</a><a href="../what-is-ace.html">❓ What is ACE?</a></div>
<main>
<div class="storm-card">
  <h2>{name}: {html_escape(basin)} {year}</h2>
  <p class="storm-sub">{status} · started {html_escape(str(storm['start_date']))}</p>
  <div class="track-inner" style="padding:0">{panel}</div>
  <div class="storm-actions">
    <button type="button" id="copyBtn" onclick="copyPageLink()">🔗 Copy link</button>
  </div>
  {as_of_html}
  <p class="page-note">Current-season values are preliminary (NHC real-time best track) and are revised in the post-season HURDAT2 release.</p>
</div>
<div class="storm-card">
  <h3 style="margin-top:0">Landfall</h3>
  {_landfall_html(storm)}
</div>
<div class="storm-card">
  <h3 style="margin-top:0">All {year} {html_escape(basin)} storms</h3>
  <ul class="sibling-list">{_siblings_html(payload, storm)}</ul>
  <p class="page-note"><a href="/#storm-row-{html_escape(slug)}" style="color:var(--accent)">See {name} in the {year} season table</a></p>
</div>
</main>
<div class="sources">
  Data: <a href="https://www.nhc.noaa.gov/data/#hurdat" target="_blank" rel="noopener noreferrer">NOAA NHC</a> best track via Tropycal.
  ACE = sum of squared 6-hourly wind speeds (knots) at tropical-storm strength or higher, divided by 10,000.
</div>
</div>
<script src="../vendor/leaflet-1.9.4/leaflet.js" integrity="{LEAFLET_JS_SRI}" crossorigin="anonymous"></script>
<script>
var ACE_TRACKS={track_json};
{LIB_MISSING_JS}
{WIND_JS}
{TRACK_MAP_JS}
function toggleTheme() {{
  var h=document.documentElement;
  var light=h.getAttribute('data-theme')==='light';
  h.setAttribute('data-theme',light?'dark':'light');
  try{{localStorage.setItem('ace-theme',light?'dark':'light');}}catch(e){{}}
  _themeBtn();
}}
function _themeBtn() {{
  var light=document.documentElement.getAttribute('data-theme')==='light';
  var b=document.getElementById('themeBtn');
  b.textContent=light?'☾':'☀';
  b.setAttribute('aria-label',light?'Switch to dark theme':'Switch to light theme');
}}
function copyPageLink() {{
  var btn=document.getElementById('copyBtn'),prev=btn.innerHTML;
  function done(ok){{btn.innerHTML=ok?'✓ Copied':'⚠ Copy failed';setTimeout(function(){{btn.innerHTML=prev;}},1400);}}
  if(navigator.clipboard&&navigator.clipboard.writeText){{
    navigator.clipboard.writeText(location.origin+location.pathname).then(function(){{done(true);}},function(){{done(false);}});
  }}else{{done(false);}}
}}
document.addEventListener('DOMContentLoaded',function(){{
  _themeBtn();
  applyWindUnit();
  _buildMap({json.dumps(slug)});
}});
</script>
</body>
</html>
'''

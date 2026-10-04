"""
Machine-readable outputs built from build_season_payload() results:
a versioned JSON API and an RSS feed. Pure functions, no I/O.

The JSON shape is a public contract. Add fields freely, but renaming or
removing one needs a new version path (api/v2/), not an edit to v1.
"""

import json
from datetime import datetime, timezone
from email.utils import format_datetime
from urllib.parse import quote
from xml.sax.saxutils import escape

SITE_URL = 'https://aceofcanes.com'
API_V1_PATH = 'api/v1/season.json'
FEED_PATH = 'feed.xml'
FEED_ITEM_LIMIT = 50

API_NOTE = ('Current-season values are preliminary (NHC real-time best track) and are '
            'revised in the post-season HURDAT2 release. Wind speeds are in knots.')


def _utc(dt=None):
    return dt or datetime.now(timezone.utc)


def _iso(dt):
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')


def build_api_v1(payloads, generated_at=None):
    """JSON-ready dict for api/v1/season.json."""
    basins = {}
    for p in payloads:
        basins[p['basin_key']] = {
            'name': p['basin_name'],
            'year': p['year'],
            'preseason': p['preseason'],
            'is_backup_data': p['is_backup'],
            'data_as_of': p['data_as_of'],
            'ace_total': round(p['ace_total'], 2),
            'normal_ace': p['normal_ace'],
            'pct_of_normal': round(p['pct_of_normal'], 1),
            'classification': p['classification'],
            'named_storms': p['named_storms'],
            'hurricanes': p['hurricanes'],
            'major_hurricanes': p['major_hurricanes'],
            'rank': p['rank'],
            'seasons_ranked': p['total_seasons'],
            'storms': [{
                'name': s['name'],
                'slug': s['slug'],
                'ace': round(s['ace'], 2),
                'pct_of_season': round(s['pct_of_season'], 1),
                'max_wind_kt': s['max_wind'],
                'category': s['category'],
                'is_major': s['is_major'],
                'is_active': s['is_active'],
                'start_date': s['start_date'],
                'landfalls': [{'location': loc, 'category': cat} for loc, cat in s['landfall']],
                'landfall_estimated': s['landfall_estimated'],
                'track': [{'lat': t['lat'], 'lon': t['lon'], 'wind_kt': t['wind'],
                           'status': t['status'], 'time': t['time']} for t in s['track_points']],
            } for s in p['storms']],
            'yearly_ace': {str(y): round(v, 2) for y, v in sorted(p['yearly_totals'].items())},
        }
    return {
        'version': 1,
        'generated_at': _iso(_utc(generated_at)),
        'source': 'NOAA NHC HURDAT2 and real-time best track, via Tropycal',
        'site': SITE_URL,
        'note': API_NOTE,
        'basins': basins,
    }


def api_v1_json(payloads, generated_at=None):
    return json.dumps(build_api_v1(payloads, generated_at), indent=2, ensure_ascii=False) + '\n'


def _storm_pub_date(storm, year, fallback):
    """Storm start_date is 'M/D' within the season year; '—' when unknown."""
    try:
        month, day = (int(x) for x in storm['start_date'].split('/'))
        return datetime(year, month, day, tzinfo=timezone.utc)
    except (ValueError, AttributeError):
        return fallback


def build_rss(payloads, generated_at=None):
    """RSS 2.0 feed with one item per named storm, newest first.

    The guid is fixed per storm, so readers announce each storm once; its
    ACE and peak wind in the description keep updating on later builds.
    """
    now = _utc(generated_at)
    entries = []
    for p in payloads:
        for s in p['storms']:
            pub = _storm_pub_date(s, p['year'], now)
            status = 'Active' if s['is_active'] else 'Inactive'
            wind = f"{s['max_wind']} kt ({s['category']})" if s['max_wind'] > 0 else 'unknown'
            if s['landfall']:
                label = 'landfall (estimated)' if s['landfall_estimated'] else 'landfall'
                lf = f"; {label}: " + ', '.join(f'{loc} ({cat})' for loc, cat in s['landfall'])
            else:
                lf = '; no landfall'
            desc = (f"{status}. Peak intensity {wind}. {s['ace']:.1f} ACE, "
                    f"{s['pct_of_season']:.0f}% of the {p['basin_name']} season so far "
                    f"({p['ace_total']:.1f} ACE total, {p['classification']}){lf}.")
            entries.append((pub, s['ace'], {
                'title': f"{s['name']} ({p['basin_name']} {p['year']})",
                'link': f"{SITE_URL}/#storm-row-{quote(s['slug'])}",
                'guid': f"aceofcanes:{p['basin_key']}:{p['year']}:{s['slug']}",
                'pub': pub,
                'desc': desc,
            }))
    entries.sort(key=lambda e: (e[0], e[1]), reverse=True)

    items = ''.join(
        '    <item>\n'
        f"      <title>{escape(e['title'])}</title>\n"
        f"      <link>{escape(e['link'])}</link>\n"
        f"      <guid isPermaLink=\"false\">{escape(e['guid'])}</guid>\n"
        f"      <pubDate>{format_datetime(e['pub'])}</pubDate>\n"
        f"      <description>{escape(e['desc'])}</description>\n"
        '    </item>\n'
        for _, _, e in entries[:FEED_ITEM_LIMIT])
    year = max((p['year'] for p in payloads), default=now.year)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
        '  <channel>\n'
        f'    <title>Ace of Canes: {year} Hurricane Season ACE</title>\n'
        f'    <link>{SITE_URL}/</link>\n'
        f'    <atom:link href="{SITE_URL}/{FEED_PATH}" rel="self" type="application/rss+xml"/>\n'
        '    <description>A new item for every named storm in the Atlantic and Eastern '
        'Pacific, with its Accumulated Cyclone Energy and the season total.</description>\n'
        '    <language>en-us</language>\n'
        f'    <lastBuildDate>{format_datetime(now)}</lastBuildDate>\n'
        f'{items}'
        '  </channel>\n'
        '</rss>\n')

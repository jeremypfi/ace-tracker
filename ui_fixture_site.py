#!/usr/bin/env python3
"""Build the whole site from fixtures, offline, for the Playwright suite (#47).

Usage: uv run python ui_fixture_site.py OUT_DIR

Runs ace_tracker.main() with Tropycal faked, every urllib request answered
from fixtures/ (anything else fails as offline), the clock frozen at
FROZEN_NOW and nothing written outside OUT_DIR. Same input, same pages, so
browser tests can name exact storms. The 2026-10-11 NHC snapshot gives three
storms with maps: Isaias and Rachel post-tropical, Simon active. Kyle, an
active Atlantic storm with no captured GIS layers, is added on top (#178).
"""
import io
import json
import logging
import os
import shutil
import socket
import sys
import urllib.error
from contextlib import ExitStack, redirect_stdout
from datetime import datetime, timedelta, timezone
from unittest import mock

import ace_cards
import ace_data
import ace_feeds
import ace_html
import ace_tracker
from smoke_test import check as smoke_check
from test_ace_tracker import FakeDataset, FakeStorm, _Resp

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(HERE, 'fixtures')
NHC_SNAPSHOT = os.path.join(FIXTURES, 'nhc_gis', '2026-10-11')
FROZEN_NOW = datetime(2026, 10, 11, 15, 0)  # naive UTC, like ace_data._utc_now()


class _FrozenMeta(type):
    # Fixture storms are built from real datetimes; ace_data checks
    # isinstance(t, datetime) against whatever name the module holds.
    def __instancecheck__(cls, obj):
        return isinstance(obj, datetime)


class FrozenDatetime(datetime, metaclass=_FrozenMeta):
    @classmethod
    def now(cls, tz=None):
        return FROZEN_NOW.replace(tzinfo=timezone.utc).astimezone(tz) if tz else FROZEN_NOW

    @classmethod
    def utcnow(cls):
        return FROZEN_NOW


def _track(start, hours, winds, lat, lon, dlat=0.6, dlon=-1.0, final=None):
    """Synoptic-time points every 6 h. `final` overrides the last point's type."""
    pts = []
    for i, w in enumerate(winds):
        kind = 'HU' if w >= 64 else 'TS' if w >= 34 else 'TD'
        if final and i == len(winds) - 1:
            kind = final
        pts.append((start + timedelta(hours=hours * i), kind, w, lat + dlat * i, lon + dlon * i))
    return pts


def current_storms():
    """2026 storms. IDs for Isaias, Rachel, Simon and Kyle match current_storms_json()."""
    return {
        'atlantic': [
            FakeStorm('AL012026', 'ARTHUR', _track(datetime(2026, 6, 20), 6, [35, 40, 45, 45, 40], 28.0, -78.0, 0.5, 0.4)),
            FakeStorm('AL062026', 'FAY', _track(datetime(2026, 9, 1), 6, [45, 60, 75, 90, 85, 70, 55], 18.0, -55.0)),
            FakeStorm('AL092026', 'ISAIAS', _track(datetime(2026, 10, 6), 6,
                                                   [35, 45, 55, 70, 85, 100, 100, 95, 80, 70, 60, 55, 50, 45, 40, 35, 35],
                                                   16.0, -62.0, 0.8, -0.9)),
            FakeStorm('AL112026', 'KYLE', _track(datetime(2026, 10, 10), 6,
                                                 [30, 35, 40, 45, 50, 55, 60], 24.0, -70.0, 0.5, -0.3)),
        ],
        'pacific': [
            FakeStorm('EP022026', 'BORIS', _track(datetime(2026, 7, 1), 6, [40, 45, 50, 45], 15.0, -100.0, 0.2, -0.5)),
            FakeStorm('EP182026', 'RACHEL', _track(datetime(2026, 10, 5), 6,
                                                   [35, 45, 60, 70, 75, 70, 60, 50, 45, 40, 35, 35, 30, 30, 30, 30, 30, 30, 30, 30, 30],
                                                   15.5, -105.0, 0.3, -0.7)),
            FakeStorm('EP202026', 'SIMON', _track(datetime(2026, 10, 9, 6), 6,
                                                  [35, 45, 55, 65, 75, 80, 85, 85, 85],
                                                  13.0, -108.0, 0.4, -0.6)),
        ],
    }


NAMES = ['ANA', 'BILL', 'CLAUDETTE', 'DANNY', 'ERIKA', 'FRED', 'GRACE', 'HENRI']


def historical_storms(basin_key):
    """Three storms a season, 1991-2025, from fixed arithmetic (no randomness)."""
    prefix, lon0 = ('AL', -50.0) if basin_key == 'atlantic' else ('EP', -105.0)
    storms = []
    for year in range(1991, 2026):
        for i in range(3):
            peak = 40 + (year * 7 + i * 29) % 110
            winds = [35, (35 + peak) // 2, peak, peak, (35 + peak) // 2, 35]
            name = NAMES[(year + i) % len(NAMES)]
            storms.append(FakeStorm(f'{prefix}{i + 1:02d}{year}', name,
                                    _track(datetime(year, 8 + i, 3 + i), 6, winds, 15.0 + i, lon0 - i * 5)))
    return storms


def spaghetti(storm):
    """Two model tracks per storm, anchored ahead of its last position."""
    lat, lon = storm.lat[-1], storm.lon[-1]
    tracks = {
        'OFCL': [{'lat': round(lat + 0.8 * k, 1), 'lon': round(lon - 1.0 * k, 1)} for k in range(1, 6)],
        'AVNO': [{'lat': round(lat + 1.0 * k, 1), 'lon': round(lon - 0.7 * k, 1)} for k in range(1, 6)],
    }
    return tracks, {'OFCL': '2026-10-11T12:00:00Z', 'AVNO': '2026-10-11T06:00:00Z'}


def _png():
    from PIL import Image
    buf = io.BytesIO()
    Image.new('RGB', (4, 4), (40, 40, 60)).save(buf, 'PNG')
    return buf.getvalue()


def _fixture(*parts):
    with open(os.path.join(*parts), 'rb') as f:
        return f.read()


# An active storm in the other basin, so the combined map (#178) spans both.
# Its bin has no captured layers, like a storm whose GIS lags its advisory.
KYLE_NHC = {
    'id': 'al112026', 'binNumber': 'AT5', 'name': 'Kyle', 'classification': 'TS', 'intensity': '60',
    'lastUpdate': '2026-10-11T12:00:00.000Z',
    'forecastGraphics': {'fileUpdateTime': '2026-10-11T11:50:00.000Z',
                         'url': 'https://www.nhc.noaa.gov/graphics_at5.shtml'},
}


def current_storms_json():
    """The 2026-10-11 snapshot plus Kyle."""
    data = json.loads(_fixture(NHC_SNAPSHOT, 'CurrentStorms.json'))
    data['activeStorms'].append(KYLE_NHC)
    return json.dumps(data).encode()


def fake_urlopen(req, timeout=None, **_):
    url = req.full_url if hasattr(req, 'full_url') else str(req)
    if url == 'https://www.nhc.noaa.gov/CurrentStorms.json':
        return _Resp(current_storms_json())
    if url.endswith('/xml/TWOAT.xml'):
        return _Resp(_fixture(FIXTURES, 'nhc_two_at_numbered.xml'))
    if url.endswith('/xml/TWOEP.xml'):
        return _Resp(_fixture(FIXTURES, 'nhc_two_ep_active_systems.xml'))
    if '/storm_graphics/' in url and url.endswith('.png'):
        return _Resp(_png())
    raise urllib.error.URLError(f'offline fixture build: {url}')


def build(out_dir, quiet=False):
    out_dir = os.path.abspath(out_dir)
    shutil.rmtree(out_dir, ignore_errors=True)
    os.makedirs(out_dir)
    current = current_storms()
    datasets = {b: FakeDataset(historical_storms(b) + current[b]) for b in ('atlantic', 'pacific')}
    for storms in current.values():
        for s in storms:
            s.year = 2026

    with ExitStack() as stack:
        patch = lambda *a, **k: stack.enter_context(mock.patch.object(*a, **k))
        for module in (ace_data, ace_html, ace_cards, ace_feeds, ace_tracker):
            patch(module, 'datetime', FrozenDatetime)
        stack.enter_context(mock.patch('urllib.request.urlopen', side_effect=fake_urlopen))
        # Backstop for anything that opens a socket without urlopen.
        patch(socket.socket, 'connect', side_effect=OSError('offline fixture build'))
        for module in (ace_data, ace_tracker):  # ace_tracker imports it by name
            patch(module, '_build_track_dataset', side_effect=lambda b: datasets[b])
        patch(ace_data, '_load_landfall_cache', return_value={})
        patch(ace_data, '_save_landfall_cache')
        patch(ace_data, 'get_landfall_locations',
              side_effect=lambda s: [('Florida', 'Cat 2')] if max(s.vmax) >= 96 else [])
        patch(ace_data, '_detect_landfall_from_track', return_value=[])
        patch(ace_data, '_extract_spaghetti_tracks', side_effect=spaghetti)
        patch(ace_data, 'CONE_DIR', os.path.join(out_dir, 'cones'))
        patch(ace_tracker, 'OUTPUT_FOLDER', out_dir)
        if quiet:
            stack.enter_context(redirect_stdout(io.StringIO()))
            logging.disable(logging.WARNING)
            stack.callback(logging.disable, logging.NOTSET)
        ace_tracker.main()

    # Mirror publish.yml's "Prepare for deployment" step.
    shutil.copytree(os.path.join(HERE, 'data', 'vendor'), os.path.join(out_dir, 'vendor'))
    shutil.copy(os.path.join(out_dir, 'ACE_Dashboard.html'), os.path.join(out_dir, 'index.html'))
    for name in ('robots.txt', 'ace.png', 'ace_preview.png'):
        shutil.copy(os.path.join(HERE, name), os.path.join(out_dir, name))
    problems = smoke_check(out_dir)
    if problems:
        raise RuntimeError('fixture site failed smoke_test:\n' + '\n'.join(problems))
    return out_dir


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    print(f'Fixture site built in {build(sys.argv[1])}')

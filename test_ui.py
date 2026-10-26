#!/usr/bin/env python3
"""Browser tests for behavior that needs real JS (#47). See CLAUDE.md > Testing.

Usage: uv run python test_ui.py        (one-time: uv pip install -r requirements-dev.txt
                                         && uv run python -m playwright install chromium)

Pages come from ui_fixture_site.py: the 2026-10-11 fixture season, built
offline into a temp dir and served on localhost. The browser never reaches
the internet: the OpenFreeMap style is answered with a one-layer stand-in so
MapLibre still initializes, and every other outside request gets an empty 200.
Every test fails on any console error or warning (Chrome's own WebGL driver
notices excepted: they come from headless GPU emulation, not page code).
"""
import functools
import http.server
import json
import os
import tempfile
import threading
import time
import unittest
import urllib.parse

from playwright.sync_api import expect, sync_playwright

import ace_data
import ui_fixture_site

BASEMAP_STYLE = json.dumps({
    'version': 8, 'sources': {},
    'layers': [{'id': 'background', 'type': 'background', 'paint': {'background-color': '#0b1220'}}],
})
PHONE = {'width': 390, 'height': 844}
GL_DRIVER_NOISE = 'GL Driver Message'

_site = _server = _pw = _browser = None


def setUpModule():
    global _site, _server, _pw, _browser
    _site = tempfile.TemporaryDirectory(prefix='ace_ui_')
    ui_fixture_site.build(_site.name, quiet=True)
    handler = functools.partial(_QuietHandler, directory=_site.name)
    _server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    threading.Thread(target=_server.serve_forever, daemon=True).start()
    _pw = sync_playwright().start()
    _browser = _pw.chromium.launch()


def tearDownModule():
    _browser.close()
    _pw.stop()
    _server.shutdown()
    _server.server_close()
    _site.cleanup()


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


NHC_GIS_HOST = 'https://mapservices.weather.noaa.gov/'
# Simon (EP5) is the fixture's one active storm. No swath was captured, so it
# comes back empty like a missing layer.
_SIMON_IDS = ace_data.nhc_gis_layer_ids('EP5')
SIMON_GIS = {_SIMON_IDS[key]: f'EP5_{name}.geojson' for key, name in {
    'points': 'forecast_points', 'cone': 'forecast_cone', 'track': 'forecast_track', 'warnings': 'watch_warning',
    'radii': 'forecast_wind_radii'}.items()}


def _nhc_gis_body(url):
    layer_id = int(url.split('/MapServer/')[1].split('/')[0])
    name = SIMON_GIS.get(layer_id)
    if not name:
        return json.dumps({'type': 'FeatureCollection', 'features': []})
    with open(os.path.join(ui_fixture_site.NHC_SNAPSHOT, name)) as f:
        data = json.load(f)
    if 'where=tau%3D0' in url:  # what the service does with the page's filter
        data['features'] = [x for x in data['features'] if x['properties'].get('tau') == 0]
    return json.dumps(data)


def _route(route):
    url = route.request.url
    if url.startswith('http://127.0.0.1:'):
        route.continue_()
    elif url.startswith('https://tiles.openfreemap.org/styles/'):
        route.fulfill(status=200, content_type='application/json', body=BASEMAP_STYLE)
    elif url.startswith(NHC_GIS_HOST):
        route.fulfill(status=200, content_type='application/json', body=_nhc_gis_body(url),
                      headers={'access-control-allow-origin': '*'})
    else:
        route.fulfill(status=200, body='')


class UITestCase(unittest.TestCase):
    """Each test gets a fresh browser context with the clock pinned to the
    fixture's 'now', so relative times like '3h ago' are stable."""

    def open(self, path='index.html', routes=(), init_script=None, **context_args):
        """`routes`: extra (url pattern, handler) pairs, set before the page loads
        and taking precedence over the offline defaults. `init_script` runs
        before any page script."""
        context_args.setdefault('viewport', {'width': 1280, 'height': 900})
        self.context = _browser.new_context(**context_args)
        self.addCleanup(self.context.close)
        self.context.route('**/*', _route)
        for pattern, handler in routes:
            self.context.route(pattern, handler)
        page = self.context.new_page()
        self.console = []
        page.on('console', self._on_console)
        page.on('pageerror', lambda e: self.console.append(f'pageerror: {e}'))
        page.clock.set_fixed_time(ui_fixture_site.FROZEN_NOW.isoformat() + 'Z')
        if init_script:
            page.add_init_script(init_script)
        page.goto(f'http://127.0.0.1:{_server.server_port}/{path}')
        self.page = page
        return page

    def _on_console(self, msg):
        if msg.type in ('error', 'warning') and GL_DRIVER_NOISE not in msg.text:
            self.console.append(f'{msg.type}: {msg.text}')

    # Chrome's own log line for a request that a test fails on purpose. Page
    # code can't suppress it; tests that fail requests set allow_failed_loads.
    FAILED_LOAD = 'error: Failed to load resource: '
    allow_failed_loads = False

    def page_errors(self):
        return [m for m in self.console if not (self.allow_failed_loads and m.startswith(self.FAILED_LOAD))]

    def tearDown(self):
        if getattr(self, 'console', None) and self.page_errors():
            self.fail('console errors/warnings:\n' + '\n'.join(self.page_errors()))

    def assert_map_drawn(self, slug):
        """The track map for `slug` has its OpenFreeMap GL basemap loaded (our
        stand-in style, so the request went to OpenFreeMap) and its track paths.
        The skeleton alone proves nothing: a 4 s timer hides it even on failure."""
        self.page.wait_for_function(
            """slug => { const map = window._trMapObjs && _trMapObjs[slug];
                         if (!map) return false;
                         let gl = null;
                         map.eachLayer(l => { if (l.getMaplibreMap) gl = l.getMaplibreMap(); });
                         return gl && gl.isStyleLoaded() && gl.getStyle().layers[0].id === 'background'
                             && document.querySelectorAll('#trmap-' + slug + ' path.leaflet-interactive').length > 0; }""",
            arg=slug, timeout=10000)
        expect(self.page.locator(f'#trskel-{slug}')).to_be_hidden()

    def no_horizontal_scroll(self):
        return self.page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')


class TestDashboardTabs(UITestCase):

    def test_hash_selects_basin(self):
        page = self.open('index.html#pacific')
        self.assertIn('active', page.locator('#pacific').get_attribute('class'))
        self.assertNotIn('active', page.locator('#atlantic').get_attribute('class'))
        self.assertEqual(page.locator('.toggle button[aria-pressed="true"]').get_attribute('onclick'),
                         "show('pacific',this)")

    def test_clicking_tab_switches_basin_and_hash(self):
        page = self.open()
        page.locator(""".toggle button[onclick="show('pacific',this)"]""").click()
        expect(page.locator('#pacific')).to_be_visible()
        expect(page.locator('#atlantic')).to_be_hidden()
        self.assertEqual(page.evaluate('location.hash'), '#pacific')

    def test_storm_link_opens_its_basin_and_map(self):
        page = self.open('index.html#storm-row-simon')
        expect(page.locator('#pacific')).to_be_visible()
        expect(page.locator('#trbtn-simon')).to_have_attribute('aria-expanded', 'true')
        self.assert_map_drawn('simon')


class TestTrackMaps(UITestCase):

    def test_accordion_opens_and_closes(self):
        page = self.open()
        page.locator('#trbtn-fay').click()
        expect(page.locator('#trpanel-fay')).to_be_visible()
        expect(page.locator('#trbtn-fay')).to_have_attribute('aria-expanded', 'true')
        self.assert_map_drawn('fay')
        page.locator('#trbtn-fay').click()
        expect(page.locator('#trbtn-fay')).to_have_attribute('aria-expanded', 'false')
        expect(page.locator('#trpanel-fay')).to_be_hidden()

    def test_several_maps_in_a_row_each_draw(self):
        # Only the first map per page was checked before #184, and the second broke.
        page = self.open()
        page.locator('#trbtn-isaias').click()
        self.assert_map_drawn('isaias')
        page.locator(""".toggle button[onclick="show('pacific',this)"]""").click()
        for slug in ('rachel', 'simon'):
            page.locator(f'#trbtn-{slug}').click()
            self.assert_map_drawn(slug)

    def test_active_storm_model_tracks_toggle(self):
        page = self.open('index.html#storm-row-simon')
        self.assert_map_drawn('simon')
        paths = lambda: page.locator('#trmap-simon path.leaflet-interactive').count()
        with_models = paths()
        self.assertIn('Official', page.locator('#splegend-simon').inner_text())
        page.locator('#sptoggle-simon').uncheck()
        self.assertLess(paths(), with_models)
        page.locator('#sptoggle-simon').check()
        self.assertEqual(paths(), with_models)


class TestNhcAdvisoryLayers(UITestCase):
    """Live NHC GIS layers on active storms' maps (#169)."""

    def test_active_storm_draws_cone_warnings_and_radii(self):
        page = self.open('index.html#storm-row-simon')
        self.assert_map_drawn('simon')
        legend = page.locator('#nhclegend-simon')
        for label in ('Forecast cone', 'Hurricane Warning', 'Hurricane Watch', '34 kt winds', '64 kt winds'):
            expect(legend).to_contain_text(label)
        # The OFCL model track already shows NHC's forecast, and no swath was captured.
        self.assertNotIn('NHC forecast track', legend.inner_text())
        self.assertNotIn('swath', legend.inner_text())
        for pane in ('cone', 'radii', 'warnings'):
            self.assertGreater(page.locator(f'#trmap-simon .leaflet-nhc-{pane}-pane path').count(), 0, pane)
        expect(page.locator('#trmap-simon .leaflet-control-attribution')).to_contain_text('Advisory layers: NHC')

    def test_service_down_leaves_map_as_before(self):
        self.allow_failed_loads = True
        for failure in ('abort', 'http500', 'arcgis_error'):
            with self.subTest(failure=failure):
                hits = []

                def fail(route, failure=failure):
                    hits.append(route.request.url)
                    if failure == 'abort':
                        route.abort('connectionfailed')
                    elif failure == 'http500':
                        route.fulfill(status=500, body='', headers={'access-control-allow-origin': '*'})
                    else:
                        route.fulfill(status=200, content_type='application/json',
                                      body='{"error":{"code":400,"message":"Invalid query"}}',
                                      headers={'access-control-allow-origin': '*'})
                page = self.open('index.html#pacific', routes=[(NHC_GIS_HOST + '**', fail)])
                page.locator('#trbtn-simon').click()
                for slug in ('simon', 'active'):
                    self.assert_map_drawn(slug)
                page.wait_for_timeout(300)
                for slug in ('simon', 'active'):
                    expect(page.locator(f'#nhclegend-{slug}')).to_be_hidden()
                    self.assertEqual(page.locator(f'#trmap-{slug} [class*="leaflet-nhc-"] path').count(), 0)
                    self.assertNotIn('NHC', page.locator(f'#trmap-{slug} .leaflet-control-attribution').inner_text())
                # Simon's map: 4 (OFCL stands in for the track). Active map: 6 each for Kyle and
                # Simon (forecast points too, for the proximity readout).
                self.assertEqual(len(hits), 16)
                page.wait_for_timeout(200)  # Chrome's failed-load lines arrive late
                self.assertEqual(self.page_errors(), [])  # the next open() resets it

    def test_inactive_storms_make_no_requests(self):
        page = self.open('index.html#pacific')
        rachel = {f'/MapServer/{i}/' for i in ace_data.nhc_gis_layer_ids('EP3').values()}
        seen = []
        page.on('request', lambda r: any(i in r.url for i in rachel) and seen.append(r.url))
        page.locator('#trbtn-rachel').click()  # post-tropical in the fixture
        self.assert_map_drawn('rachel')
        self.assertEqual(page.locator('#nhclegend-rachel').count(), 0)
        self.assertEqual(seen, [])


class TestActiveStormsMap(UITestCase):
    """The dashboard's combined map (#178): Kyle (Atlantic, no GIS layers) and Simon (Pacific)."""

    def last_position(self, slug):
        return self.page.evaluate('s => { const p = ACE_TRACKS[s].points; return [p[p.length-1].lat, p[p.length-1].lon]; }', slug)

    def test_both_basins_on_one_map(self):
        page = self.open()
        self.assert_map_drawn('active')
        self.assertEqual(page.locator('#trmap-active .leaflet-overlay-pane path.leaflet-interactive').count(), 2)
        for slug in ('kyle', 'simon'):
            self.assertTrue(page.evaluate('ll => _trMapObjs.active.getBounds().contains(ll)', self.last_position(slug)), slug)
        # Simon's layers draw, including NHC's own forecast track (no model tracks on this map);
        # Kyle's come back empty and just leave his marker.
        legend = page.locator('#nhclegend-active')
        for label in ('Forecast cone', 'NHC forecast track', 'Hurricane Warning', '34 kt winds'):
            expect(legend).to_contain_text(label)
        expect(page.locator('#trmap-active .leaflet-control-attribution')).to_contain_text('Advisory layers: NHC')

    def test_storm_link_opens_its_row_in_the_other_basin(self):
        page = self.open()
        expect(page.locator('#atlantic')).to_be_visible()
        link = page.locator('#active-storms a[href="#storm-row-simon"]')
        link.click()
        expect(page.locator('#pacific')).to_be_visible()
        expect(page.locator('#trbtn-simon')).to_have_attribute('aria-expanded', 'true')
        self.assert_map_drawn('simon')
        link.click()  # opens, never toggles shut
        expect(page.locator('#trbtn-simon')).to_have_attribute('aria-expanded', 'true')

    def test_phone_width(self):
        page = self.open(viewport=PHONE)
        self.assert_map_drawn('active')
        self.assertTrue(self.no_horizontal_scroll())
        self.assertLessEqual(page.locator('#trmap-active').bounding_box()['width'], PHONE['width'])


def _place(lat, lon, kind, **address):
    address.setdefault('country', 'United States')
    address.setdefault('country_code', 'us')
    return {'lat': str(lat), 'lon': str(lon), 'addresstype': kind, 'address': address,
            'display_name': ', '.join(v for k, v in address.items() if k != 'country_code')}


# What Nominatim answered on 2026-10-25, trimmed to the fields the page reads.
GEOCODER = {
    'austin tx': [_place(30.27, -97.74, 'city', city='Austin', county='Travis County', state='Texas'),
                  _place(29.89, -96.24, 'county', county='Austin County', state='Texas')],
    'springfield': [_place(39.80, -89.64, 'city', city='Springfield', state='Illinois'),
                    _place(42.10, -72.59, 'city', city='Springfield', state='Massachusetts'),
                    _place(37.21, -93.29, 'city', city='Springfield', state='Missouri')],
    '78701': [_place(30.27, -97.74, 'postcode', postcode='78701', city='Austin', state='Texas')],
    'nowhere': [],
}


class TestLocationInput(UITestCase):
    """Location search, geolocation and pin drop on the active-storms map (#179).
    Nominatim is mocked; 'boom' makes it fail."""

    def open(self, path='index.html', **kwargs):
        self.geocoded = []

        def geocoder(route):
            self.geocoded.append((time.monotonic(), route.request.url))
            q = urllib.parse.parse_qs(urllib.parse.urlparse(route.request.url).query)['q'][0]
            if q == 'boom':
                route.fulfill(status=500, body='', headers={'access-control-allow-origin': '*'})
            else:
                route.fulfill(status=200, content_type='application/json', body=json.dumps(GEOCODER[q.lower()]),
                              headers={'access-control-allow-origin': '*'})
        page = super().open(path, routes=[('https://nominatim.openstreetmap.org/**', geocoder)], **kwargs)
        self.assert_map_drawn('active')
        return page

    def search(self, text):
        self.page.locator('#loc-q').fill(text)
        self.page.locator('#loc-q').press('Enter')

    def pins(self):
        return self.page.locator('#trmap-active .loc-pin').count()

    def in_view(self, latlon):
        return self.page.evaluate('ll => _trMapObjs.active.getBounds().contains(ll)', latlon)

    def test_city_search_pins_it_and_fits_the_storms(self):
        page = self.open()
        self.search('Austin TX')
        expect(page.locator('#loc-msg')).to_have_text('Showing Austin, Texas.')  # Austin County dropped
        self.assertEqual(self.pins(), 1)
        expect(page.locator('#loc-picks')).to_be_hidden()
        self.assertTrue(self.in_view([30.27, -97.74]))
        for slug in ('kyle', 'simon'):
            ll = page.evaluate('s => { const p = ACE_TRACKS[s].points; return [p[p.length-1].lat, p[p.length-1].lon]; }', slug)
            self.assertTrue(self.in_view(ll), slug)
        self.assertNotIn('30.2', page.evaluate('location.href'))
        self.assertNotIn('Austin', page.evaluate('location.href'))
        page.locator('#loc-clear').click()
        self.assertEqual(self.pins(), 0)
        expect(page.locator('#loc-clear')).to_be_hidden()

    def test_ambiguous_name_offers_a_pick_list(self):
        page = self.open()
        self.search('Springfield')
        picks = page.locator('#loc-picks .loc-pick')
        expect(picks).to_have_count(3)
        expect(picks.first).to_be_focused()
        page.keyboard.press('Tab')
        page.keyboard.press('Tab')
        expect(picks.nth(2)).to_have_text('Springfield, Missouri')
        page.keyboard.press('Enter')
        expect(page.locator('#loc-msg')).to_have_text('Showing Springfield, Missouri.')
        expect(page.locator('#loc-picks')).to_be_hidden()
        self.assertTrue(self.in_view([37.21, -93.29]))

    def test_zip_searches_the_us_only(self):
        page = self.open()
        self.search('78701')
        expect(page.locator('#loc-msg')).to_have_text('Showing 78701, Austin, Texas.')
        self.assertIn('countrycodes=us', self.geocoded[0][1])

    def test_no_match_and_service_down_keep_the_map(self):
        self.allow_failed_loads = True
        page = self.open()
        self.search('nowhere')
        expect(page.locator('#loc-msg')).to_contain_text('No place found for "nowhere"')
        self.search('boom')
        expect(page.locator('#loc-msg')).to_contain_text('not responding')
        self.assertEqual(self.pins(), 0)
        self.assertEqual(page.locator('#trmap-active .leaflet-overlay-pane path.leaflet-interactive').count(), 2)
        # Nominatim's usage policy: at most one request a second.
        self.assertGreaterEqual(self.geocoded[1][0] - self.geocoded[0][0], 0.95)

    def test_use_my_location(self):
        page = self.open(geolocation={'latitude': 25.77, 'longitude': -80.19}, permissions=['geolocation'])
        page.locator('#loc-geo').click()
        expect(page.locator('#loc-msg')).to_have_text('Showing your current location.')
        self.assertTrue(self.in_view([25.77, -80.19]))
        self.assertEqual(self.geocoded, [])  # coordinates never go to the geocoder

    def test_use_my_location_denied(self):
        page = self.open()
        page.evaluate("""() => { navigator.geolocation.getCurrentPosition = (ok, fail) =>
                                    fail({code: 1, message: 'User denied Geolocation'}); }""")
        page.locator('#loc-geo').click()
        expect(page.locator('#loc-msg')).to_contain_text('Location access is off')
        self.assertEqual(self.pins(), 0)

    def test_tap_map_drops_pin_but_storm_marker_opens_its_row(self):
        page = self.open()
        box = page.locator('#trmap-active').bounding_box()
        page.mouse.click(box['x'] + box['width'] - 60, box['y'] + box['height'] - 60)
        expect(page.locator('#loc-msg')).to_contain_text('Showing Dropped pin (')
        self.assertEqual(self.pins(), 1)
        page.locator('#loc-clear').click()
        pt = page.evaluate("""() => { const p = ACE_TRACKS.simon.points.at(-1);
                                      return _trMapObjs.active.latLngToContainerPoint([p.lat, p.lon]); }""")
        page.mouse.click(box['x'] + pt['x'], box['y'] + pt['y'])
        expect(page.locator('#trbtn-simon')).to_have_attribute('aria-expanded', 'true')
        self.assertEqual(self.pins(), 0)

    def test_remembered_location_comes_back_without_a_search(self):
        page = self.open()
        page.locator('#loc-remember').check()
        self.search('Austin TX')
        expect(page.locator('#loc-msg')).to_have_text('Showing Austin, Texas.')
        page.reload()
        self.assert_map_drawn('active')
        expect(page.locator('#loc-msg')).to_have_text('Showing Austin, Texas.')
        expect(page.locator('#loc-remember')).to_be_checked()
        self.assertEqual(self.pins(), 1)
        self.assertEqual(len(self.geocoded), 1)
        page.locator('#loc-remember').uncheck()
        self.assertIsNone(page.evaluate("localStorage.getItem('ace-location')"))


class TestProximityGeometry(UITestCase):
    """The readout's inline geometry helpers (#180), run in the page."""

    def test_helpers(self):
        page = self.open()
        km = page.evaluate('_kmBetween(30.27, -97.74, 25.77, -80.19)')  # Austin to Miami
        self.assertAlmostEqual(km / 1.609344, 1110, delta=15)
        self.assertEqual(page.evaluate('_compass(_bearing(30.27, -97.74, 25.77, -80.19))'), 'ESE')
        self.assertEqual(page.evaluate('_compass(_bearing(25.77, -80.19, 40.71, -74.01))'), 'NNE')
        square = '[[-1,-1],[1,-1],[1,1],[-1,1],[-1,-1]]'
        self.assertTrue(page.evaluate(f'_inRing(0, 0, {square})'))
        self.assertFalse(page.evaluate(f'_inRing(2, 0, {square})'))
        self.assertTrue(page.evaluate('_inRing(0, 179.5, [[-179,-1],[179,-1],[179,1],[-179,1],[-179,-1]])'))  # across 180
        self.assertEqual(page.evaluate('_segNearest([0,0],[-1,1],[1,1])'), [0.5, 1])
        self.assertEqual(page.evaluate('_segNearest([5,0],[-1,1],[1,1])')[0], 1)
        # validtime is UTC; the label's local date can sit in the previous month.
        self.assertEqual(page.evaluate("new Date(_nhcTime({fldatelbl:'2026-10-31 07:00 PM Sat CDT', validtime:'01/0000'})).toISOString()"),
                         '2026-11-01T00:00:00.000Z')
        self.assertEqual(page.evaluate("_catName('HU', 100)"), 'Category 3 hurricane')


class TestProximityReadout(UITestCase):
    """Distances from a pin to every active storm (#180). Kyle has no NHC layers."""

    def pin(self, lat, lon, label):
        self.page.evaluate('p => _locSet(p)', {'lat': lat, 'lon': lon, 'label': label})

    def items(self):
        return self.page.locator('#loc-readout .prox-item')

    def open(self, path='index.html', **kwargs):
        kwargs.setdefault('timezone_id', 'America/Chicago')
        page = super().open(path, **kwargs)
        self.assert_map_drawn('active')
        expect(page.locator('#nhclegend-active')).to_contain_text('Forecast cone')  # Simon's layers are in
        return page

    def test_nearest_first_across_basins_with_fallback(self):
        page = self.open()
        expect(page.locator('#loc-readout')).to_be_hidden()
        self.pin(25.77, -80.19, 'Miami, Florida')
        expect(self.items()).to_have_count(2)
        self.assertEqual([self.items().nth(i).get_attribute('data-slug') for i in range(2)], ['kyle', 'simon'])
        expect(page.locator('#loc-readout .prox-title')).to_have_text('Distance from Miami, Florida')
        kyle = self.items().nth(0)
        expect(kyle).to_contain_text('Distance to the center only')
        expect(kyle).to_contain_text('Tropical storm')
        self.assertRegex(kyle.locator('.prox-dist').inner_text(), r'^[0-9,]+ mi [NESW]{1,3}$')
        simon = self.items().nth(1)  # ~3,500 km away: no closer detail
        expect(simon).to_contain_text('Not forecast to come within ~932 mi.')
        expect(simon).not_to_contain_text('inside the forecast cone')
        expect(simon).not_to_contain_text('Tropical-storm-force winds are')
        expect(page.locator('#loc-readout .prox-disclaimer')).to_contain_text('Not for safety decisions')
        # One labeled line per storm.
        self.assertEqual(page.locator('#trmap-active .leaflet-tooltip.dist-tip').count(), 2)

    def test_inside_the_cone_with_closest_approach_time(self):
        page = self.open()
        self.pin(21.0, -106.6, 'Puerto Vallarta area')  # Simon's 24 h forecast point
        simon = page.locator('#loc-readout .prox-item[data-slug="simon"]')
        expect(simon).to_contain_text('You are inside the forecast cone.')
        # 24 h after the 11/1800 UTC advisory point is Mon 18 UTC: 1 PM in Chicago.
        expect(simon).to_contain_text('Forecast to pass over or near you around Mon 1 PM.')
        self.pin(21.0, -105.0, 'Inland, 165 km east')
        self.assertRegex(simon.inner_text(), r'Forecast to pass ~[0-9]+ mi [NESW]{1,3} of you around Mon [0-9]+ [AP]M[.]')
        self.assertRegex(simon.inner_text(), r'(Inside the|Tropical-storm-force winds are ~)')

    def test_distances_follow_the_unit_toggle(self):
        page = self.open()
        self.pin(25.77, -80.19, 'Miami, Florida')
        first = self.items().nth(0).locator('.prox-dist')
        self.assertIn(' mi ', first.inner_text())  # miles by default, though wind is in knots
        page.locator('#unitBtn').click()  # mph
        self.assertIn(' mi ', first.inner_text())
        page.locator('#unitBtn').click()  # km/h
        self.assertIn(' km ', first.inner_text())
        self.assertIn(' km', page.locator('#trmap-active .dist-tip').first.inner_text())

    def test_clearing_removes_readout_and_lines(self):
        page = self.open()
        self.pin(25.77, -80.19, 'Miami, Florida')
        expect(self.items()).to_have_count(2)
        page.locator('#loc-clear').click()
        expect(page.locator('#loc-readout')).to_be_hidden()
        expect(page.locator('#trmap-active .dist-tip')).to_have_count(0)  # after Leaflet's 200 ms fade

    def test_nhc_down_falls_back_to_center_distance(self):
        self.allow_failed_loads = True
        page = super().open('index.html', timezone_id='America/Chicago',
                            routes=[(NHC_GIS_HOST + '**', lambda r: r.abort('connectionfailed'))])
        self.assert_map_drawn('active')
        self.pin(21.0, -106.6, 'Puerto Vallarta area')
        for slug in ('kyle', 'simon'):
            expect(page.locator(f'#loc-readout .prox-item[data-slug="{slug}"]')).to_contain_text('Distance to the center only')


class TestNearestStormBadge(UITestCase):
    """Dashboard badge from a remembered location (#181). From Miami, Kyle is nearest."""

    MIAMI = "localStorage.setItem('ace-location', JSON.stringify({lat: 25.77, lon: -80.19, label: 'Miami, Florida'}));"
    badge = property(lambda self: self.page.locator('#near-badge'))

    def test_saved_location_shows_nearest_storm(self):
        page = self.open(init_script=self.MIAMI)
        expect(self.badge).to_be_visible()
        link = self.badge.locator('a')
        self.assertRegex(link.inner_text(), r'^Kyle, [0-9,]+ mi [NESW]{1,3}$')
        self.assertEqual(link.get_attribute('href'), '#active-storms')
        self.assert_map_drawn('active')
        readout = page.locator('#loc-readout .prox-item[data-slug="kyle"] .prox-dist')
        self.assertEqual(link.inner_text(), 'Kyle, ' + readout.inner_text())
        page.locator('#unitBtn').click()
        page.locator('#unitBtn').click()  # km/h
        self.assertRegex(link.inner_text(), r'^Kyle, [0-9,]+ km [NESW]{1,3}$')

    def test_forget_location(self):
        page = self.open(init_script=self.MIAMI)
        self.assert_map_drawn('active')
        expect(page.locator('#trmap-active .loc-pin')).to_have_count(1)
        self.badge.get_by_role('button', name='Forget location').click()
        expect(self.badge).to_be_hidden()
        expect(page.locator('#trmap-active .loc-pin')).to_have_count(0)
        expect(page.locator('#loc-readout')).to_be_hidden()
        self.assertIsNone(page.evaluate("localStorage.getItem('ace-location')"))

    def test_hidden_without_a_remembered_location(self):
        page = self.open()
        self.assert_map_drawn('active')
        expect(self.badge).to_be_hidden()
        page.evaluate("_locSet({lat: 25.77, lon: -80.19, label: 'Miami, Florida'})")  # not remembered
        expect(self.badge).to_be_hidden()
        page.locator('#loc-remember').check()
        expect(self.badge).to_be_visible()
        page.locator('#loc-remember').uncheck()
        expect(self.badge).to_be_hidden()

    def test_storage_blocked(self):
        page = self.open(init_script="""Object.defineProperty(window, 'localStorage',
            {get() { throw new DOMException('blocked', 'SecurityError'); }});""")
        self.assert_map_drawn('active')
        expect(self.badge).to_be_hidden()
        page.evaluate("_locSet({lat: 25.77, lon: -80.19, label: 'Miami, Florida'})")
        page.locator('#loc-remember').check()  # can't save, but this page still knows it
        expect(self.badge).to_contain_text('Nearest storm: Kyle')

    def test_hidden_when_no_storm_is_active(self):
        # The section only renders with an active storm, so blank the list as the page assigns it.
        self.open(init_script=self.MIAMI + """
            Object.defineProperty(window, 'ACE_ACTIVE', {configurable: true,
                set(v) { Object.defineProperty(window, 'ACE_ACTIVE', {value: [], writable: true}); }});""")
        self.page.wait_for_load_state('load')
        expect(self.badge).to_be_hidden()


class TestShareButtons(UITestCase):

    def test_storm_link_copies_to_clipboard(self):
        page = self.open(permissions=['clipboard-read', 'clipboard-write'])
        btn = page.locator('#storm-row-fay .storm-share-btn')
        btn.click()
        expect(btn).to_have_text('✓')  # set once the async clipboard write resolves
        self.assertEqual(page.evaluate('navigator.clipboard.readText()'),
                         f'http://127.0.0.1:{_server.server_port}/index.html#storm-row-fay')

    def test_record_share_uses_clipboard_on_desktop(self):
        page = self.open(permissions=['clipboard-read', 'clipboard-write'])
        btn = page.locator('#atlantic .rip-share-btn').first
        btn.click()
        expect(btn).to_have_text('✓')
        copied = page.evaluate('navigator.clipboard.readText()')
        self.assertEqual(copied, f"{btn.get_attribute('data-share-text')} {btn.get_attribute('data-share-url')}")

    def test_record_share_uses_web_share_on_touch(self):
        page = self.open(viewport=PHONE, has_touch=True, is_mobile=True)
        page.evaluate("""() => { window._shared = null;
                                 navigator.share = d => { window._shared = d; return Promise.resolve(); }; }""")
        btn = page.locator('#atlantic .rip-share-btn').first
        btn.tap()
        page.wait_for_function('window._shared !== null')
        self.assertEqual(page.evaluate('window._shared'),
                         {'text': btn.get_attribute('data-share-text'), 'url': btn.get_attribute('data-share-url')})


class TestToggles(UITestCase):

    def test_wind_unit_cycles_and_persists(self):
        page = self.open()
        peak = page.locator('#trpanel-isaias .wind-val-unit').first  # data-kt="100", in a collapsed panel
        self.assertEqual(peak.text_content(), '100 kt')
        page.locator('#unitBtn').click()
        after = peak.text_content()
        self.assertRegex(after, r'^\d+ (mph|km/h)$')
        page.reload()
        expect(page.locator('#trpanel-isaias .wind-val-unit').first).to_have_text(after)

    def test_theme_toggles_and_persists(self):
        page = self.open(color_scheme='dark')
        self.assertNotEqual(page.evaluate("document.documentElement.getAttribute('data-theme')"), 'light')
        page.locator('#themeBtn').click()
        self.assertEqual(page.evaluate("document.documentElement.getAttribute('data-theme')"), 'light')
        page.reload()
        self.assertEqual(page.evaluate("document.documentElement.getAttribute('data-theme')"), 'light')


class TestStormPage(UITestCase):

    def test_phone_layout_map_and_cone(self):
        page = self.open('storm/simon-2026.html', viewport=PHONE)
        self.assert_map_drawn('simon')
        self.assertTrue(self.no_horizontal_scroll())
        cone = page.locator('img[src="../cones/ep202026.png"]')
        cone.scroll_into_view_if_needed()  # loading="lazy"
        page.wait_for_function('img => img.complete && img.naturalWidth > 0', arg=cone.element_handle())

    def test_marker_tooltip_shows_markup_in_a_name_as_text(self):
        # Rewrites Simon's name as the page assigns ACE_TRACKS, before the map reads it.
        page = self.open('storm/simon-2026.html', init_script="""
            Object.defineProperty(window, 'ACE_TRACKS', {configurable: true,
                set(v) { v.simon.name = '<img src=x onerror="window.pwned=1">Simon';
                         Object.defineProperty(window, 'ACE_TRACKS', {value: v, writable: true}); }});""")
        self.assert_map_drawn('simon')
        page.evaluate("""() => { let mk = null;
            _trMapObjs.simon.eachLayer(l => { if (l instanceof L.CircleMarker && l.getTooltip()) mk = l; });
            mk.openTooltip(); }""")
        tip = page.locator('#trmap-simon .leaflet-tooltip', has_text='Simon')
        expect(tip).to_contain_text('<img src=x')
        self.assertEqual(tip.locator('img').count(), 0)
        self.assertIsNone(page.evaluate('window.pwned'))

    def test_no_horizontal_scroll_at_phone_width(self):
        for path in ('index.html', 'history.html', 'records.html', 'what-is-ace.html', 'api.html',
                     'storm/isaias-2026.html'):
            with self.subTest(path=path):
                self.open(path, viewport=PHONE)
                self.assertTrue(self.no_horizontal_scroll(), f'{path} scrolls sideways at 390 px')


class TestNoJavaScript(UITestCase):

    def test_dashboard_shows_default_basin_storms(self):
        page = self.open(java_script_enabled=False)
        self.assertTrue(page.locator('#atlantic').is_visible())
        self.assertFalse(page.locator('#active-storms').is_visible())  # would be an empty map box
        for name in ('Arthur', 'Fay', 'Isaias'):
            self.assertTrue(page.locator(f'#storm-row-{name.lower()}').is_visible(), name)

    @unittest.expectedFailure
    def test_pacific_reachable_without_js(self):
        # Known gap (2026-10-18): the basin toggle and storm panels need JS, so
        # a no-JS visitor only ever sees the Atlantic card. Drop the decorator
        # once there's a fallback; until then an "unexpected success" means it was fixed.
        page = self.open(java_script_enabled=False)
        page.locator(""".toggle button[onclick="show('pacific',this)"]""").click()
        expect(page.locator('#pacific')).to_be_visible(timeout=1000)

    def test_storm_page_shows_details(self):
        page = self.open('storm/simon-2026.html', java_script_enabled=False)
        self.assertIn('Simon', page.locator('h1').inner_text())
        self.assertTrue(page.locator('.storm-card').first.is_visible())


if __name__ == '__main__':
    unittest.main(verbosity=2)

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
import unittest

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
    'cone': 'forecast_cone', 'track': 'forecast_track', 'warnings': 'watch_warning',
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

    def open(self, path='index.html', routes=(), **context_args):
        """`routes`: extra (url pattern, handler) pairs, set before the page loads
        and taking precedence over the offline defaults."""
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
        page.goto(f'http://127.0.0.1:{_server.server_port}/{path}')
        self.page = page
        return page

    def _on_console(self, msg):
        if msg.type in ('error', 'warning') and GL_DRIVER_NOISE not in msg.text:
            self.console.append(f'{msg.type}: {msg.text}')

    def tearDown(self):
        if getattr(self, 'console', None):
            self.fail('console errors/warnings:\n' + '\n'.join(self.console))

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
                # Simon's map: 4 (OFCL stands in for the track). Active map: 5 each for Kyle and Simon.
                self.assertEqual(len(hits), 14)
                self.assertEqual(self.console, [])  # the next open() resets it

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

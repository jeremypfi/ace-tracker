"""Structural checks on the built site folder before it deploys (#157).

Usage: python smoke_test.py data
Exits 1 and lists every problem if anything is missing, empty or unparseable.
Checks are structural (exists / parses / non-empty / counts match), never
value-based, so a quiet season or odd numbers can't fail a publish.
"""
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

from ace_assets import BASEMAP

SITE = 'https://aceofcanes.com/'
PAGES = ('index.html', 'ACE_Dashboard.html', 'history.html', 'records.html', 'what-is-ace.html', 'api.html')
OG_IMAGE = re.compile(r'<meta property="og:image" content="([^"]+)"')
VENDOR_REF = re.compile(r'(?:src|href)="(?:\.\./)?(vendor/[^"]+)"')


def _read(root, rel):
    path = os.path.join(root, rel)
    if not os.path.isfile(path) or os.path.getsize(path) == 0:
        return None
    with open(path, encoding='utf-8') as f:
        return f.read()


def _og_image(html):
    m = OG_IMAGE.search(html)
    return m.group(1)[len(SITE):] if m and m.group(1).startswith(SITE) else None


def _nonempty(root, rel):
    path = os.path.join(root, rel)
    return os.path.isfile(path) and os.path.getsize(path) > 0


def check(root):
    problems = []

    for page in PAGES:
        if _read(root, page) is None:
            problems.append(f'{page} missing or empty')

    dash = _read(root, 'ACE_Dashboard.html') or ''
    card = _og_image(dash)
    if not card or not card.startswith('og/season-') or not _nonempty(root, card):
        problems.append(f'dashboard share card missing (og:image -> {card})')
    for ref in sorted(set(VENDOR_REF.findall(dash))):
        if not _nonempty(root, ref):
            problems.append(f'{ref} referenced by the dashboard but missing')
    for key in ('js', 'css', 'plugin'):
        if not _nonempty(root, f'vendor/{BASEMAP[key]}'):
            problems.append(f'vendor/{BASEMAP[key]} (map basemap) missing')

    for rel in ('feed.xml', 'sitemap.xml'):
        try:
            ET.parse(os.path.join(root, rel))
        except (OSError, ET.ParseError) as e:
            problems.append(f'{rel} not well-formed: {e}')

    try:
        season = json.loads(_read(root, 'api/v1/season.json') or '')
    except ValueError as e:
        return problems + [f'api/v1/season.json does not parse: {e}']
    if season.get('version') != 1:
        problems.append(f"season.json version is {season.get('version')!r}, expected 1")
    basins = season.get('basins', {})
    storms = []
    for name in ('atlantic', 'pacific'):
        if name not in basins:
            problems.append(f'season.json has no {name} basin')
        else:
            storms += basins[name].get('storms', [])

    for storm in storms:
        page = storm.get('url', '')[len(SITE):]
        html = _read(root, page)
        if html is None:
            problems.append(f"{storm.get('name')}: page {page or '(no url)'} missing or empty")
            continue
        card = _og_image(html)
        if not card or not card.startswith('og/storm-') or not _nonempty(root, card):
            problems.append(f"{storm['name']}: share card missing (og:image -> {card})")

    try:
        locs = [el.text for el in ET.parse(os.path.join(root, 'sitemap.xml')).iter()
                if el.tag.endswith('loc')]
        in_sitemap = sum(1 for loc in locs if loc and '/storm/' in loc)
        if in_sitemap != len(storms):
            problems.append(f'sitemap lists {in_sitemap} storm pages, season.json has {len(storms)} storms')
    except (OSError, ET.ParseError):
        pass  # already reported above

    return problems


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else 'data'
    problems = check(root)
    if problems:
        print(f'Smoke test FAILED ({len(problems)} problems):')
        for p in problems:
            print(f'  - {p}')
        sys.exit(1)
    print('Smoke test passed.')


if __name__ == '__main__':
    main()

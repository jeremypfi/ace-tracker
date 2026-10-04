"""
Open Graph share card (1200x630) with the live season numbers, drawn with
Pillow from build_season_payload() results. Pure: returns bytes and a
content-addressed filename, writes nothing.

Chat apps and Twitter cache an image by URL, so the filename carries a hash
of what the card shows. The URL (and so the preview) only changes when the
numbers do.
"""

import hashlib
import io
import os
from datetime import datetime, timezone

import matplotlib
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from ace_html import _track_status_color

WIDTH, HEIGHT = 1200, 630
CARD_ART = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ace.png')
# matplotlib ships DejaVu, so the card renders the same on a laptop and in CI.
_FONT_DIR = os.path.join(matplotlib.get_data_path(), 'fonts', 'ttf')

BG_TOP_LEFT, BG_BOTTOM_RIGHT = (18, 41, 65), (10, 21, 35)
TEXT, MUTED, ACCENT = (232, 238, 246), (150, 170, 190), (79, 195, 247)
ACCENT_BY_BASIN = {'atlantic': (255, 112, 67), 'pacific': (0, 194, 160)}
SHORT_NAME = {'atlantic': 'ATLANTIC', 'pacific': 'E/C PACIFIC'}


def _font(size, bold=False):
    return ImageFont.truetype(os.path.join(_FONT_DIR, 'DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'), size)


def _content(payloads, as_of):
    """The text the card displays, one dict per basin. Doubles as the hash key."""
    return [{
        'basin_key': p['basin_key'],
        'year': p['year'],
        'ace': f"{p['ace_total']:.1f}",
        'classification': 'No storms yet' if p['preseason'] else p['classification'],
        'detail': ('Season underway' if p['preseason'] else
                   f"{p['named_storms']} named {'storm' if p['named_storms'] == 1 else 'storms'}"
                   f" · #{p['rank']} of {p['total_seasons']} since 1991"),
        'date': as_of.strftime('%b %-d, %Y'),
    } for p in payloads]


def share_card_name(payloads, generated_at=None):
    """'og/season-<hash>.png', stable while the displayed numbers are unchanged."""
    content = _content(payloads, generated_at or datetime.now(timezone.utc))
    digest = hashlib.sha1(repr(content).encode()).hexdigest()[:10]
    return f'og/season-{digest}.png'


def _gradient():
    # Diagonal blend, built from a small image and scaled up (cheap and smooth).
    small = Image.new('RGB', (2, 2))
    small.putpixel((0, 0), BG_TOP_LEFT)
    small.putpixel((1, 1), BG_BOTTOM_RIGHT)
    mid = tuple((a + b) // 2 for a, b in zip(BG_TOP_LEFT, BG_BOTTOM_RIGHT))
    small.putpixel((1, 0), mid)
    small.putpixel((0, 1), mid)
    return small.resize((WIDTH, HEIGHT), Image.BILINEAR)


def _spaced(draw, xy, text, font, fill, spacing):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + spacing


def _paste_card(img):
    art = Image.open(CARD_ART).convert('RGB')
    # ace.png has opaque black corners, so cut our own rounded ones.
    mask = Image.new('L', art.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, art.width - 1, art.height - 1), radius=44, fill=255)
    art.putalpha(mask)
    art.thumbnail((350, 446), Image.LANCZOS)
    pad = 40
    layer = Image.new('RGBA', (art.width + 2 * pad, art.height + 2 * pad), (0, 0, 0, 0))
    shadow = Image.new('RGBA', layer.size, (0, 0, 0, 0))
    shadow.paste((0, 0, 0, 150), (pad + 6, pad + 14), art.getchannel('A'))
    layer = Image.alpha_composite(layer, shadow.filter(ImageFilter.GaussianBlur(14)))
    layer.alpha_composite(art, (pad, pad))
    layer = layer.rotate(5, resample=Image.BICUBIC, expand=True)
    img.paste(layer, (30, (HEIGHT - layer.height) // 2), layer)


def render_share_card(payloads, generated_at=None):
    """PNG bytes for the season share card."""
    as_of = generated_at or datetime.now(timezone.utc)
    img = _gradient()
    _paste_card(img)
    draw = ImageDraw.Draw(img)

    left = 500
    _spaced(draw, (left, 52), 'ACE OF CANES', _font(22, bold=True), ACCENT, 5)
    year = max((p['year'] for p in payloads), default=as_of.year)
    draw.text((left, 90), f'{year} Hurricane Season', font=_font(46, bold=True), fill=TEXT)

    rows = _content(payloads, as_of)
    row_h = 150
    top = 175
    for i, row in enumerate(rows[:2]):
        y = top + i * row_h
        color = ACCENT_BY_BASIN.get(row['basin_key'], ACCENT)
        draw.rounded_rectangle((left, y + 6, left + 8, y + row_h - 34), radius=4, fill=color)
        _spaced(draw, (left + 28, y), SHORT_NAME.get(row['basin_key'], row['basin_key'].upper()),
                _font(20, bold=True), MUTED, 3)
        draw.text((left + 26, y + 26), row['ace'], font=_font(78, bold=True), fill=color)
        ace_w = draw.textlength(row['ace'], font=_font(78, bold=True))
        draw.text((left + 26 + ace_w + 14, y + 44), 'ACE', font=_font(28, bold=True), fill=MUTED)
        draw.text((left + 26 + ace_w + 14, y + 82), row['classification'], font=_font(26, bold=True), fill=TEXT)
        draw.text((left + 28, y + 112), row['detail'], font=_font(20), fill=MUTED)

    draw.text((left, HEIGHT - 84), 'aceofcanes.com', font=_font(26, bold=True), fill=ACCENT)
    draw.text((left, HEIGHT - 46), f"Updated {as_of.strftime('%b %-d, %Y')} · preliminary NHC data",
              font=_font(18), fill=MUTED)

    out = io.BytesIO()
    img.save(out, 'PNG', optimize=True)
    return out.getvalue()


def share_card_alt(payloads):
    parts = [f"{SHORT_NAME.get(p['basin_key'], p['basin_key']).title()} {p['ace_total']:.1f} ACE ({p['classification']})"
             for p in payloads]
    return 'Ace of Canes season ACE: ' + '; '.join(parts) if parts else 'Ace of Canes season ACE'


# ===============================================================================
# PER-STORM CARD
# ===============================================================================

def _storm_content(payload, storm, as_of):
    wind = storm['max_wind']
    return {
        'name': storm['name'],
        'basin_key': payload['basin_key'],
        'year': payload['year'],
        'ace': f"{storm['ace']:.1f}",
        'pct': f"{storm['pct_of_season']:.0f}",
        'peak': f"{wind} kt · {storm['category']}" if wind > 0 else 'Peak unknown',
        'active': storm['is_active'],
        'landfall': ', '.join(loc for loc, _ in storm['landfall']) or 'No landfall',
        'points': [(t['lat'], t['lon'], t['status'], t['wind']) for t in storm['track_points']],
        'date': as_of.strftime('%b %-d, %Y'),
    }


def storm_card_name(payload, storm, generated_at=None):
    """'og/storm-<page_slug>-<hash>.png', stable while the card's content is."""
    content = _storm_content(payload, storm, generated_at or datetime.now(timezone.utc))
    digest = hashlib.sha1(repr(content).encode()).hexdigest()[:10]
    return f"og/storm-{storm['page_slug']}-{digest}.png"


def _unwrap_lons(lons):
    out = [lons[0]]
    for lon in lons[1:]:
        while lon - out[-1] > 180:
            lon -= 360
        while lon - out[-1] < -180:
            lon += 360
        out.append(lon)
    return out


def _draw_track(draw, box, points):
    """Storm path in `box`, colored by intensity, equal-scale lat/lon."""
    x0, y0, x1, y1 = box
    draw.rounded_rectangle(box, radius=22, fill=(11, 24, 40), outline=(30, 58, 95), width=2)
    if not points:
        draw.text(((x0 + x1) / 2, (y0 + y1) / 2), 'No track data', font=_font(24), fill=MUTED, anchor='mm')
        return
    import math
    lats = [p[0] for p in points]
    lons = _unwrap_lons([p[1] for p in points])
    mid_lat = (min(lats) + max(lats)) / 2
    xs = [lon * math.cos(math.radians(mid_lat)) for lon in lons]
    span_x = max(max(xs) - min(xs), 4.0)
    span_y = max(max(lats) - min(lats), 4.0)
    pad = 44
    scale = min((x1 - x0 - 2 * pad) / span_x, (y1 - y0 - 2 * pad) / span_y)
    cx, cy = (max(xs) + min(xs)) / 2, (max(lats) + min(lats)) / 2
    to_px = lambda x, lat: ((x0 + x1) / 2 + (x - cx) * scale, (y0 + y1) / 2 - (lat - cy) * scale)
    pix = [to_px(x, lat) for x, lat in zip(xs, lats)]

    def hex_rgb(h):
        return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
    for i in range(len(pix) - 1):
        draw.line([pix[i], pix[i + 1]], fill=hex_rgb(_track_status_color(points[i][2], points[i][3])), width=7)
    for (px, py), pt in zip(pix, points):
        r = 5
        draw.ellipse((px - r, py - r, px + r, py + r), fill=hex_rgb(_track_status_color(pt[2], pt[3])))
    lx, ly = pix[-1]
    draw.ellipse((lx - 9, ly - 9, lx + 9, ly + 9), outline=(255, 255, 255), width=3)


def render_storm_card(payload, storm, generated_at=None):
    """PNG bytes for one storm's share card."""
    as_of = generated_at or datetime.now(timezone.utc)
    c = _storm_content(payload, storm, as_of)
    img = _gradient()
    draw = ImageDraw.Draw(img)
    _draw_track(draw, (40, 50, 470, 580), c['points'])

    left = 520
    color = ACCENT_BY_BASIN.get(c['basin_key'], ACCENT)
    _spaced(draw, (left, 52), 'ACE OF CANES', _font(22, bold=True), ACCENT, 5)
    name_font = _font(72, bold=True)
    name = c['name']
    while draw.textlength(name, font=name_font) > WIDTH - left - 40 and len(name) > 3:
        name = name[:-2] + '…'
    draw.text((left, 92), name, font=name_font, fill=TEXT)
    basin = SHORT_NAME.get(c['basin_key'], c['basin_key']).title()
    draw.text((left, 182), f"{basin} {c['year']}", font=_font(30), fill=MUTED)
    if c['active']:
        draw.ellipse((left, 246, left + 16, 262), fill=(76, 175, 80))
        _spaced(draw, (left + 28, 241), 'ACTIVE NOW', _font(22, bold=True), (76, 175, 80), 3)

    draw.text((left, 290), c['ace'], font=_font(96, bold=True), fill=color)
    ace_w = draw.textlength(c['ace'], font=_font(96, bold=True))
    draw.text((left + ace_w + 16, 336), 'ACE', font=_font(32, bold=True), fill=MUTED)
    draw.text((left, 410), f"{c['pct']}% of the season so far", font=_font(24), fill=TEXT)
    draw.text((left, 452), f"Peak {c['peak']}", font=_font(24, bold=True), fill=TEXT)
    lf = c['landfall']
    if draw.textlength(lf, font=_font(22)) > WIDTH - left - 40:
        lf = lf[:40].rstrip(', ') + '…'
    draw.text((left, 492), lf if lf == 'No landfall' else f'Landfall: {lf}', font=_font(22), fill=MUTED)

    draw.text((left, HEIGHT - 84), 'aceofcanes.com', font=_font(26, bold=True), fill=ACCENT)
    draw.text((left, HEIGHT - 46), f"Updated {c['date']} · preliminary NHC data", font=_font(18), fill=MUTED)

    out = io.BytesIO()
    img.save(out, 'PNG', optimize=True)
    return out.getvalue()


def storm_card_alt(payload, storm):
    wind = f"peak {storm['max_wind']} kt ({storm['category']})" if storm['max_wind'] > 0 else 'peak unknown'
    return (f"{storm['name']} {payload['year']}: {storm['ace']:.1f} ACE, "
            f"{storm['pct_of_season']:.0f}% of the {payload['basin_name']} season, {wind}")

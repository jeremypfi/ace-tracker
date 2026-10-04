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

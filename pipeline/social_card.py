"""Weekend social card: a 1200x630 branded image of the weekend's top events,
regenerated each build. Used as the this-weekend page's og:image, embedded in
the Friday digest, and postable as-is to local Facebook groups."""

import json
import os

from PIL import Image, ImageDraw, ImageFont

from pipeline.feeds import weekend_events

W, H = 1200, 630
BLUE = (37, 99, 235)
BLUE_DARK = (29, 78, 216)
WHITE = (255, 255, 255)
BLUE_PALE = (191, 219, 254)

# Runner (Ubuntu) first, then local Windows fallbacks
_FONT_CANDIDATES = [
    '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    'C:/Windows/Fonts/segoeuib.ttf',
    'C:/Windows/Fonts/arialbd.ttf',
]
_FONT_REG_CANDIDATES = [
    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    'C:/Windows/Fonts/segoeui.ttf',
    'C:/Windows/Fonts/arial.ttf',
]


def _font(candidates, size):
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _truncate(draw, text, font, max_width):
    if draw.textlength(text, font=font) <= max_width:
        return text
    while text and draw.textlength(text + '…', font=font) > max_width:
        text = text[:-1].rstrip()
    return text + '…'


def generate_weekend_card(events_file, output_dir, area_config):
    with open(events_file, 'r', encoding='utf-8') as f:
        events = json.load(f)

    area_name = area_config['name']
    friday, sunday, picked = weekend_events(events)
    fri_label = friday.strftime('%b %d').replace(' 0', ' ')
    sun_label = (sunday.strftime('%d') if friday.month == sunday.month
                 else sunday.strftime('%b %d')).lstrip('0')
    range_label = f"{fri_label}–{sun_label}"

    img = Image.new('RGB', (W, H), BLUE)
    d = ImageDraw.Draw(img)
    # Subtle vertical gradient
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=tuple(
            int(BLUE[i] + (BLUE_DARK[i] - BLUE[i]) * t) for i in range(3)))

    f_eyebrow = _font(_FONT_CANDIDATES, 34)
    f_title = _font(_FONT_CANDIDATES, 72)
    f_event = _font(_FONT_CANDIDATES, 36)
    f_meta = _font(_FONT_REG_CANDIDATES, 28)
    f_footer = _font(_FONT_CANDIDATES, 30)

    x = 70
    d.text((x, 56), 'THIS WEEKEND · ' + range_label.upper(), font=f_eyebrow, fill=BLUE_PALE)
    d.text((x, 100), f'in {area_name}', font=f_title, fill=WHITE)

    # Round-robin across the weekend days so a busy Friday doesn't crowd
    # Saturday and Sunday off the card
    by_day = {}
    for date_val, ev in picked:
        by_day.setdefault(date_val, []).append(ev)
    shown = []
    i = 0
    while len(shown) < 5 and any(len(v) > i for v in by_day.values()):
        for date_val in sorted(by_day):
            if i < len(by_day[date_val]) and len(shown) < 5:
                shown.append((date_val, by_day[date_val][i]))
        i += 1
    shown.sort(key=lambda p: p[0])

    y = 220
    for date_val, ev in shown:
        d.text((x, y + 4), date_val.strftime('%a').upper(), font=f_meta, fill=BLUE_PALE)
        d.text((x + 100, y), _truncate(d, ev['title'], f_event, W - x - 180), font=f_event, fill=WHITE)
        y += 58

    if not picked:
        d.text((x, y), 'Markets, music, festivals & more', font=f_event, fill=WHITE)

    extra = len(picked) - len(shown)
    if extra > 0:
        d.text((x + 100, y + 2), f'+ {extra} more this weekend…', font=f_meta, fill=BLUE_PALE)

    d.rectangle([0, H - 74, W, H], fill=(23, 46, 128))
    d.text((x, H - 56), 'localspothq.com', font=f_footer, fill=WHITE)

    out_file = os.path.join(output_dir, 'weekend-card.png')
    img.save(out_file)
    print(f">> Weekend card: {len(picked)} events ({range_label}) -> {out_file}")
    return out_file

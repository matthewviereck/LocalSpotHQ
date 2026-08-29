"""Steel City Coffeehouse & Brewery event scraper.

History: this venue was scraped via Bandsintown, then via Squarespace markup.
Both are dead as of 2026-08-29 — Bandsintown serves a 403 bot wall to any
plain HTTP client, and the venue has migrated to Square Online, which renders
the page client-side so there is no event markup in the fetched HTML.

What IS in the HTML is the page's rich-text source: a Quill-style delta
(a flat list of {"insert": "..."} ops) embedded in the Square Online payload.
Reconstructing that gives the page's plain text in authoring order, which for
this venue follows a consistent shape — one block per show:

    Friday, September 4th          <- date line opens the block
    7:00 pm
    $12 Advance General Admission
    ...description...
    The Regulars, Darth Brandon    <- the show title CLOSES the block
    Tight Spiral & Morning Person
    Saturday, September 12th       <- next block begins

So a block runs from one date line to the next, and its trailing non-empty
lines are the title. This is hand-authored prose, not structured data, so the
parser is deliberately conservative: anything it cannot confidently read is
skipped rather than guessed at, and a zero-event parse falls back to cache.
"""

import json
import os
import re
import html
from datetime import datetime

import requests

from scrapers.http_headers import BROWSER_HEADERS

TARGET_URL = "https://www.steelcityphx.com/concerts-and-events"

VENUE_INFO = {
    "name": "Steel City Coffeehouse & Brewery",
    "location": {"lat": 40.1305, "lng": -75.5148}
}

MONTHS = ('January', 'February', 'March', 'April', 'May', 'June', 'July',
          'August', 'September', 'October', 'November', 'December')
MONTH_ABBR = {m[:3].lower(): m for m in MONTHS}

# "Friday, September 4th" / "Sat, Sept 12" / "September 18th"
DATE_RE = re.compile(
    r'^(?:(?:Mon|Tues?|Wed(?:nes)?|Thurs?|Fri|Satur?|Sun)[a-z]*\s*,?\s*)?'
    r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sept?|Oct|Nov|Dec)[a-z]*\.?\s+'
    r'(\d{1,2})(?:st|nd|rd|th)?'
    r'(?:\s*,?\s*(\d{4}))?\s*$',
    re.I,
)
TIME_RE = re.compile(r'^\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?$', re.I)
PRICE_RE = re.compile(r'\$\s?\d+(?:\.\d{2})?')

# Delta op: {"insert":"<json string>"}
INSERT_RE = re.compile(r'\{"insert":("(?:[^"\\]|\\.)*")')

# Lines that are page furniture, never part of a show title. The venue repeats
# a standing footer (ticketing terms, seating advice) after the LAST show on the
# page, so the title walker skips these rather than stopping at them.
BOILERPLATE = re.compile(
    r'ticketing fee|ticketing terms|convenience fee|keep your email|'
    r'digital ticket|ticket sales are final|ticket purchaser|door list|'
    r'seating is first come|reserved seating for parties|seating of choice|'
    r'seating together|doors? (?:open|always open)|happy hour|come hungry|'
    r'learn more|get on the list|general event info|parking in phoenixville|'
    r'will sell out|buy your ticket|special show menu|'
    r'advance general admission|day of show|^day of$|^about |transfer your tick',
    re.I,
)

# How many trailing furniture lines to skip before giving up on finding a title.
MAX_FOOTER_SKIP = 14


def _reconstruct_text(page_html):
    """Rebuild the page's authored plain text from its Quill delta ops."""
    ops = INSERT_RE.findall(page_html)
    if not ops:
        return []
    try:
        text = ''.join(json.loads(op) for op in ops)
    except ValueError:
        return []
    text = html.unescape(text).replace(' ', ' ')
    return [line.strip() for line in text.split('\n')]


def _parse_date(line, today):
    """'Friday, September 4th' -> 'September 4, 2026'. Year inferred if absent."""
    m = DATE_RE.match(line)
    if not m:
        return None
    mon_key = m.group(1)[:3].lower()
    month = MONTH_ABBR.get(mon_key)
    if not month:
        return None
    day = int(m.group(2))
    if not 1 <= day <= 31:
        return None
    year = int(m.group(3)) if m.group(3) else None
    if year is None:
        # No year on the page: assume the next occurrence of this month/day.
        year = today.year
        try:
            if datetime(year, MONTHS.index(month) + 1, day).date() < today.date():
                year += 1
        except ValueError:
            return None
    try:
        datetime(year, MONTHS.index(month) + 1, day)
    except ValueError:
        return None
    return f"{month} {day}, {year}"


def _is_furniture(line):
    return bool(
        BOILERPLATE.search(line)
        or TIME_RE.match(line)
        or (PRICE_RE.search(line) and len(line) < 60)
    )


def _clean_title(lines):
    """Join the trailing lines of a block into one title, or return None.

    Walks backwards: the show title closes its block. Standing page footer
    lines after the final show are skipped, not treated as the end of the walk.
    """
    picked = []
    skipped = 0
    for line in reversed(lines):
        if not line:
            if picked:
                break
            continue
        if _is_furniture(line):
            if picked:
                break
            skipped += 1
            if skipped > MAX_FOOTER_SKIP:
                return None
            continue
        # A long sentence is description, not a title.
        if not picked and len(line) > 120:
            skipped += 1
            if skipped > MAX_FOOTER_SKIP:
                return None
            continue
        picked.append(line)
        if len(' '.join(picked)) > 90:
            break
    if not picked:
        return None
    title = ' '.join(reversed(picked))
    title = re.sub(r'\s+', ' ', title).strip(' ,&-')
    # A title is a name, not a paragraph.
    if not 2 < len(title) <= 120 or title.count('.') > 2:
        return None
    return title


def scrape_steel_city(output_file='steel_city_events.json'):
    """Scrape upcoming shows from the venue's Square Online page."""
    print(f">> Connecting to {TARGET_URL}...")
    try:
        response = requests.get(TARGET_URL, headers=BROWSER_HEADERS, timeout=30)
    except requests.RequestException as e:
        print(f"   ! Connection error: {e}")
        _fallback(output_file)
        return

    if response.status_code != 200:
        print(f"   ! Failed to load page (status {response.status_code})")
        _fallback(output_file)
        return

    lines = _reconstruct_text(response.text)
    if not lines:
        print("   ! No rich-text payload found - page format changed")
        _fallback(output_file)
        return

    today = datetime.now()

    # Index every date line, then treat each as opening a block.
    date_idx = [(i, _parse_date(l, today)) for i, l in enumerate(lines)]
    date_idx = [(i, d) for i, d in date_idx if d]
    if not date_idx:
        print("   ! No date lines found in page text - format changed")
        _fallback(output_file)
        return

    events = []
    seen = set()
    for n, (start, date_str) in enumerate(date_idx):
        end = date_idx[n + 1][0] if n + 1 < len(date_idx) else len(lines)
        block = lines[start + 1:end]

        title = _clean_title(block)
        if not title:
            continue

        time_str = next((l for l in block if TIME_RE.match(l)), '')
        raw_date = f"{date_str} {time_str.upper()}".strip()

        # Shows list several tiers (advance / day-of / reserved). The lowest is
        # the entry price, which is what a listing should quote. The $2 ticket
        # fee is not a ticket tier, so it is excluded.
        amounts = sorted(
            {float(p.replace('$', '').replace(' ', '')) for p in PRICE_RE.findall(' '.join(block))}
            - {2.0, 2.00}
        )
        price = f"${amounts[0]:g}" if amounts else 'Check Link'

        key = (title.lower(), date_str)
        if key in seen:
            continue
        seen.add(key)

        events.append({
            "id": "sc_" + re.sub(r'[^a-z0-9]+', '', title.lower())[:24] + '_'
                  + re.sub(r'[^0-9]', '', date_str),
            "type": "event",
            "title": title,
            "venue_info": VENUE_INFO,
            "raw_date_string": raw_date,
            "attributes": {
                "category": "Live Music",
                "vibes": ["Live Music", "Coffeehouse", "Brewery"],
                "price": price,
            },
            "media": {"image": ""},
            "action_link": TARGET_URL,
        })

    if not events:
        print("   ! Page loaded but no events extracted")
        _fallback(output_file)
        return

    os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(events, f, indent=2, ensure_ascii=False)

    print(f">> Done! Saved {len(events)} events to {output_file}")


def _fallback(output_file):
    """If scrape fails and a cached file exists, leave it. Otherwise write empty."""
    if os.path.exists(output_file):
        print(f"   Using cached {output_file}")
    else:
        os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump([], f)
        print(f"   Wrote empty {output_file}")


if __name__ == "__main__":
    scrape_steel_city()

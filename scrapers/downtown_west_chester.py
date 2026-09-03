"""Scrape the Downtown West Chester events calendar via its public JSON API.

downtownwestchester.com runs The Events Calendar (WordPress), which exposes a
REST endpoint at /wp-json/tribe/events/v1/events. That is a far better source
than HTML scraping: it returns start/end times, cost, venue and image as
structured fields, and it is the single densest event feed in either area
(600+ upcoming entries).

Two things about it are worth knowing before editing this file:

1. It sits behind the same bot wall as the venue sites - a bare
   `User-Agent: Mozilla/5.0` gets 403. Use BROWSER_HEADERS. It also rate
   limits (429) if you page through it without pausing, hence PAGE_PAUSE.

2. Roughly 40% of the calendar is recurring bar programming - quizzo,
   karaoke, music bingo, pub pong, poker night. Real events, but not what
   someone opens LocalSpot to find, and shipping them would bury the
   festivals and shows. SKIP_TITLE_PATTERNS drops them.

This scraper is the authoritative source for anything on that calendar. The
Claude discovery routine (.claude/skills/discover-events) deliberately does
NOT re-list these - pipeline.merge dedupes on normalized title + date, and
two sources phrasing the same event slightly differently defeats that.
"""

import html
import json
import os
import re
import time
from datetime import datetime, timedelta

import requests

from scrapers.http_headers import BROWSER_HEADERS

API_URL = "https://www.downtownwestchester.com/wp-json/tribe/events/v1/events"

HORIZON_DAYS = 120
PER_PAGE = 50
MAX_PAGES = 20
PAGE_PAUSE = 1.5  # the API 429s without this

DEFAULT_LOCATION = {"lat": 39.9601, "lng": -75.6055}  # Downtown West Chester

VENUE_COORDS = {
    "downtown west chester": (39.9601, -75.6055),
    "uptown! knauer performing arts center": (39.9646, -75.6044),
    "chester county history center": (39.9645, -75.6046),
    "west chester railroad": (39.9596, -75.5983),
    "chestnut & church streets": (39.9628, -75.6072),
    "gay street": (39.9605, -75.6055),
    "west chester university": (39.9490, -75.6013),
    "ginkgo arts": (39.9592, -75.6053),
    "the green house": (39.9604, -75.6053),
    "penn's table restaurant": (39.9604, -75.6062),
    "hop fidelity": (39.9591, -75.6070),
    "side bar & restaurant": (39.9605, -75.6045),
    "artillery brewing company": (39.9563, -75.6030),
    "align.space": (39.9592, -75.6053),
    "windisch studios": (39.9606, -75.6058),
    "turks head wines": (39.9617, -75.6068),
    "turks head cafe": (39.9613, -75.6060),
    "chester county art association": (39.9604, -75.6118),
    "stove & tap": (39.9605, -75.6079),
    "wonderhouse": (39.9608, -75.6027),
    "cutter & cannon": (39.9606, -75.6035),
    "manje caribbean cuisine": (39.9614, -75.6003),
    "the refinery hair studio": (39.9591, -75.6065),
    "true by kristy": (39.9592, -75.6066),
    "tiger snake vintage": (39.9591, -75.6047),
    "la chic boutique": (39.9604, -75.6047),
}

# Recurring bar programming. Real, but ~40% of the feed by volume.
SKIP_TITLE_PATTERNS = re.compile(
    r'\b(quizzo|trivia|karaoke|music bingo|pub pong|poker night|'
    r'permanent jewelry|open mic night)\b',
    re.IGNORECASE,
)

# The calendar's own categories are useless for us - nearly every event is
# tagged "Things To Do" - so category comes from the title. Order matters:
# first match wins, so the specific patterns sit above the generic ones.
_CATEGORY_RULES = [
    (r'growers market|farmers market', 'Farmers Market'),
    (r'festival|cook-?off|oktoberfest|mushroom|county fair', 'Festival'),
    (r'comedy|improv|laugh|stand-?up|better than bacon', 'Comedy'),
    # 'walks' plural on purpose: it catches "Saturday Morning Walks" without
    # stealing "Walking Tour", which belongs to Art & Culture further down.
    (r'5k|10k|run/walk|run & walk|marathon|yoga|race|\bwalks\b', 'Sports'),
    (r'jazz|concert|tribute|orchestra|quartet|quintet|band\b|dj\s|vinyl|'
     r'songwriter|acoustic|dueling pianos|album release|live music', 'Live Music'),
    (r'train ride|foliage express|kids|children|family|movie monday|'
     r'story time|art sprouts|soldiers & trains', 'Kids & Family'),
    (r'beer garden|wine|brewery|brews|tasting|chef|restaurant|'
     r'food truck|cocktail|cabernet|uncorked|chianti|grapes|vineyard|'
     r'sommelier|whiskey|bourbon|cigar', 'Food & Drink'),
    (r'musical|theatre|theater|broadway', 'Theater'),
    (r'gallery|walking tour|history|museum|film|documentary|story slam|'
     r'exhibit|art of|open studio|scavenger hunt|terrarium|workshop',
     'Art & Culture'),
    (r'first friday|parade|homecoming|market|meeting|book club',
     'Community Event'),
]
CATEGORY_RULES = [(re.compile(p, re.IGNORECASE), c) for p, c in _CATEGORY_RULES]

MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


def _clean(text):
    """Tribe returns HTML-entity-encoded strings (Kildare&#8217;s)."""
    return html.unescape(str(text or '')).replace('’', "'").strip()


def _parse_dt(value):
    try:
        return datetime.strptime(str(value)[:19], '%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError):
        return None


def _raw_date_string(start, end):
    """Format as the rest of the pipeline expects: 'Sep 20, 2026' or a range.

    This MUST match the format the discovery routine writes - pipeline.merge
    dedupes on normalized title + raw_date_string, so 'Sep 20, 2026' and
    'September 20, 2026' would ship the same event twice.
    """
    s = f"{MONTHS[start.month - 1]} {start.day}, {start.year}"
    if not end or end.date() <= start.date():
        return s
    if end.year == start.year and end.month == start.month:
        return f"{MONTHS[start.month - 1]} {start.day} - {end.day}, {end.year}"
    if end.year == start.year:
        return (f"{MONTHS[start.month - 1]} {start.day} - "
                f"{MONTHS[end.month - 1]} {end.day}, {end.year}")
    return s


def _category(title):
    for pattern, category in CATEGORY_RULES:
        if pattern.search(title):
            return category
    return 'Community Event'


def _price(cost):
    cost = _clean(cost).replace('–', '-').replace('—', '-')
    return re.sub(r'\s+', ' ', cost)


def _time_label(start, all_day):
    if all_day or not start:
        return ''
    hour = start.hour % 12 or 12
    suffix = 'AM' if start.hour < 12 else 'PM'
    if start.minute:
        return f"{hour}:{start.minute:02d} {suffix}"
    return f"{hour} {suffix}"


def _location(venue_name):
    lat, lng = VENUE_COORDS.get(venue_name.lower(), (None, None))
    if lat is None:
        return dict(DEFAULT_LOCATION)
    return {"lat": lat, "lng": lng}


def _slug(title):
    return re.sub(r'[^a-z0-9]+', '_', title.lower()).strip('_')[:40]


def _build_event(raw):
    title = _clean(raw.get('title'))
    if not title or SKIP_TITLE_PATTERNS.search(title):
        return None

    start = _parse_dt(raw.get('start_date'))
    if not start:
        return None
    end = _parse_dt(raw.get('end_date'))
    all_day = bool(raw.get('all_day'))

    venue_raw = raw.get('venue') or {}
    venue_name = _clean(venue_raw.get('venue')) or 'Downtown West Chester'
    city = _clean(venue_raw.get('city')) or 'West Chester'

    attributes = {"category": _category(title), "vibes": []}
    price = _price(raw.get('cost'))
    if price:
        attributes['price'] = price
        if price.lower() == 'free':
            attributes['vibes'].append('Free')
    time_label = _time_label(start, all_day)
    if time_label:
        attributes['time'] = time_label

    image = ''
    if isinstance(raw.get('image'), dict):
        image = raw['image'].get('url') or ''

    return {
        "id": f"dwc_{_slug(title)}_{start.strftime('%Y%m%d')}",
        "type": "event",
        "title": title,
        "venue_info": {
            "name": f"{venue_name}, {city}",
            "location": _location(venue_name),
        },
        "raw_date_string": _raw_date_string(start, end),
        "attributes": attributes,
        "media": {"image": image},
        "action_link": (raw.get('url')
                        or 'https://www.downtownwestchester.com/events/'),
    }


def scrape_downtown_west_chester(output_file='downtown_wc_events.json'):
    """Pull upcoming events from the Downtown West Chester calendar API."""
    today = datetime.now().date()
    horizon = today + timedelta(days=HORIZON_DAYS)
    print(f">> Querying {API_URL} ({today} -> {horizon})...")

    headers = dict(BROWSER_HEADERS)
    headers['Accept'] = 'application/json'

    events, skipped, page = [], 0, 1
    while page <= MAX_PAGES:
        params = {
            'per_page': PER_PAGE,
            'page': page,
            'start_date': today.isoformat(),
            'end_date': horizon.isoformat(),
        }
        try:
            response = requests.get(API_URL, params=params,
                                    headers=headers, timeout=30)
        except requests.RequestException as e:
            print(f"   ! Connection error on page {page}: {e}")
            break

        if response.status_code == 404 and page > 1:
            break  # Tribe returns 404 past the last page
        if response.status_code != 200:
            print(f"   ! HTTP {response.status_code} on page {page}")
            break

        try:
            batch = response.json().get('events', [])
        except ValueError:
            print(f"   ! Page {page} was not JSON (bot wall?)")
            break
        if not batch:
            break

        for raw in batch:
            built = _build_event(raw)
            if built:
                events.append(built)
            else:
                skipped += 1

        print(f"   page {page}: {len(batch)} raw")
        page += 1
        time.sleep(PAGE_PAUSE)

    # A reachable API that yields nothing means the shape changed or a wall
    # served us a shell. Keep the last-good file rather than blanking the area.
    if not events:
        print("   ! No events extracted")
        _fallback(output_file)
        return

    os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(events, f, indent=2, ensure_ascii=False)

    print(f">> Done! Saved {len(events)} events to {output_file} "
          f"({skipped} filtered as recurring bar programming)")


def _fallback(output_file):
    if os.path.exists(output_file):
        print(f"   Using cached {output_file}")
    else:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump([], f)
        print(f"   Wrote empty {output_file}")


if __name__ == "__main__":
    scrape_downtown_west_chester()

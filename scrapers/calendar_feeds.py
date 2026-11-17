"""Read the event calendars that local places already publish.

A direct feed beats AI discovery for any place that has one: it lists every
event with a real date and start time, every build, instead of whatever a web
search happens to surface that day. The 2026-11-14 survey of about fifty
Phoenixville area publishers (vault: LocalSpotHQ hub) found four formats worth
reading, and a fifth (Wix) came on 2026-11-16, all handled here:

  ics          iCalendar subscribe feeds. LibCal (the county library system)
               and LiveWhale (Ursinus) expand every occurrence themselves.
  squarespace  A Squarespace events page with ?format=json appended.
  elfsight     The Elfsight "Event Calendar" widget's settings, which carry
               the full event list (Phoenixville First's calendar).
  fooevents    The FooEvents calendar a WooCommerce site prints into its page
               as JSON (SoulJoel's).
  wix          A Wix Events page: the event list rides in the page's
               "wix-warmup-data" JSON (The Barn Yard, Collegeville). Many
               small local sites are Wix, so one reader covers them all.

Each feed is one entry in an area config's `scrapers` list, with its settings
under `options.feed`, so every feed gets its own output file, its own
last-good fallback and its own line in scripts/check_scraper_health.py:

    {"module": "scrapers.calendar_feeds", "function": "scrape_feed",
     "output_file": "scraped/feed_phoenixville_library.json",
     "options": {"feed": {"id": "phoenixville_library", "format": "ics", ...}}}

Feed settings (all but id, format and url are optional):

  id                short name, used in event ids and the health report
  url               the feed (for elfsight, the page that embeds the widget)
  widget            elfsight widget id
  link              public calendar page, for events with no link of their own
  venue             {"name", "lat", "lng"}: where events are when the feed
                    does not say, and the coordinates geo routing uses
  venue_template    "{room}, Ursinus College, Collegeville": build the venue
                    name from the feed's LOCATION
  strip_location    regex removed from LOCATION before it fills {room}
  include_categories / exclude_categories   ICS CATEGORIES filters
  exclude_title     regex; matching titles are dropped
  require_location  regex the event's location must match (drops off-site
                    events a venue sells tickets for)
  max_repeats       drop a title that occurs more than this many times in
                    the window: weekly storytimes, ESL classes and line
                    dancing nights are real, but they bury the weekend's
                    one-off events, and the weekly bar nights are already
                    filtered the same way for West Chester
  horizon_days      how far ahead to read (default 90)
  category          fixed category; otherwise category_map, then the title
  category_map      {regex: category} matched against the feed's own
                    CATEGORIES ("preschool|family": "Kids & Family")
  vibes             tags added to every event
  title_fixes       {"Phoenixivlle": "Phoenixville"}: literal fixes for a
                    typo in the source, which would otherwise win over a
                    correctly spelled discovery copy of the same event
  may_be_empty      the health check reports this feed but does not fail
                    the run when it has nothing upcoming (a seasonal
                    calendar between seasons)

Times: every feed is read as US Eastern. UTC stamps (ICS "Z", Squarespace
epoch milliseconds) are converted with the US daylight saving rule rather
than zoneinfo, which has no time zone data on a bare Windows Python.
"""

import html
import json
import os
import re
from datetime import datetime, timedelta

import requests

from scrapers.downtown_west_chester import _category, _raw_date_string, _time_label
from scrapers.http_headers import BROWSER_HEADERS

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HORIZON_DAYS = 90
TIMEOUT = 30

MONTH_WORDS = (r'jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|'
               r'july?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|'
               r'nov(?:ember)?|dec(?:ember)?')
# "(November 25th)", "(Special Thursday Bingo)" stays: only a parenthetical
# that names a date is dropped when counting how often a title repeats.
_DATE_PAREN = re.compile(r'\((?:[^)]*\b(?:' + MONTH_WORDS + r')\b[^)]*)\)', re.I)
_DATE_WORDS = re.compile(r'\b(?:' + MONTH_WORDS + r')\.?\s+\d{1,2}(?:st|nd|rd|th)?\b', re.I)
_CANCELLED = re.compile(r'\b(?:cancel+ed|postponed)\b', re.I)
# An online program is not a local event, whatever calendar lists it.
_ONLINE = re.compile(r'^(?:virtual|online|zoom|webinar)\b', re.I)
# Checked before the shared West Chester title rules, which miss these.
_TITLE_RULES = [
    (re.compile(r'\bcomedian\b', re.I), 'Comedy'),
    (re.compile(r'recital|ensemble|\bchoir\b|chorale|caroling', re.I), 'Live Music'),
]


# --------------------------------------------------------------------------
# Time
# --------------------------------------------------------------------------

def _first_sunday_on_or_after(d):
    return d + timedelta(days=(6 - d.weekday()) % 7)


def eastern_from_utc(utc):
    """Naive UTC datetime -> naive US Eastern wall time.

    Daylight time runs from the second Sunday in March at 2 AM EST (07:00
    UTC) to the first Sunday in November at 2 AM EDT (06:00 UTC).
    """
    start = _first_sunday_on_or_after(datetime(utc.year, 3, 8)).replace(hour=7)
    end = _first_sunday_on_or_after(datetime(utc.year, 11, 1)).replace(hour=6)
    return utc + timedelta(hours=-4 if start <= utc < end else -5)


def _from_epoch_ms(ms):
    return eastern_from_utc(datetime(1970, 1, 1) + timedelta(milliseconds=int(ms)))


# --------------------------------------------------------------------------
# Text
# --------------------------------------------------------------------------

def _clean(text):
    """Entities decoded, odd spaces and curly apostrophes flattened."""
    text = html.unescape(str(text or ''))
    text = text.replace(' ', ' ').replace(' ', ' ').replace('\xa0', ' ')
    text = text.replace('’', "'").replace('‘', "'")
    return re.sub(r'\s+', ' ', text).strip()


def _slug(text):
    return re.sub(r'[^a-z0-9]+', '_', text.lower()).strip('_')[:32]


def repeat_key(title):
    """A title with its date words removed, for counting weekly programs."""
    t = _DATE_PAREN.sub(' ', title.lower())
    t = _DATE_WORDS.sub(' ', t)
    t = re.sub(r'\d+', ' ', t)
    return re.sub(r'[^a-z]+', ' ', t).strip()


# --------------------------------------------------------------------------
# Parsers: each returns a list of "items", one dict per occurrence:
#   title, start (datetime), end (datetime|None), all_day, location,
#   categories (list), link, image, status
# --------------------------------------------------------------------------

def _ics_unescape(value):
    return (value.replace('\\n', ' ').replace('\\N', ' ').replace('\\,', ',')
            .replace('\\;', ';').replace('\\\\', '\\'))


def _ics_datetime(value, params):
    """(datetime, all_day) from an ICS DTSTART/DTEND value."""
    value = value.strip()
    if 'VALUE=DATE' in params.upper() or re.fullmatch(r'\d{8}', value):
        return datetime.strptime(value[:8], '%Y%m%d'), True
    m = re.fullmatch(r'(\d{8}T\d{4})(\d{2})?(Z)?', value)
    if not m:
        return None, False
    dt = datetime.strptime(m.group(1), '%Y%m%dT%H%M')
    if m.group(3):
        dt = eastern_from_utc(dt)
    # A TZID or a floating time is local wall time already. Every feed read
    # here is a Pennsylvania calendar, so TZID is not consulted.
    return dt, False


def parse_ics(text):
    """VEVENTs of an iCalendar document. RRULE masters are skipped (and
    counted): the feeds read here expand their own occurrences, and the one
    feed surveyed that does not (Google Calendar) was not worth reading."""
    text = re.sub(r'\r?\n[ \t]', '', text)
    items, skipped_rrule = [], 0
    for block in re.findall(r'BEGIN:VEVENT(.*?)END:VEVENT', text, re.S):
        props = {}
        for line in block.splitlines():
            m = re.match(r'([A-Z-]+)((?:;[^:]*)?):(.*)', line)
            if m and m.group(1) not in props:
                props[m.group(1)] = (m.group(2), m.group(3))
        if 'RRULE' in props:
            skipped_rrule += 1
            continue
        if 'DTSTART' not in props:
            continue
        start, all_day = _ics_datetime(props['DTSTART'][1], props['DTSTART'][0])
        if not start:
            continue
        end = None
        if 'DTEND' in props:
            end, _ = _ics_datetime(props['DTEND'][1], props['DTEND'][0])
            if end and all_day:
                end -= timedelta(days=1)  # DTEND of a date is exclusive
        get = lambda k: _ics_unescape(props.get(k, ('', ''))[1])  # noqa: E731
        items.append({
            'title': _clean(get('SUMMARY')),
            'start': start, 'end': end, 'all_day': all_day,
            'location': _clean(get('LOCATION')),
            'categories': [c.strip() for c in get('CATEGORIES').split(',') if c.strip()],
            'link': get('URL').strip(),
            'image': '',
            'status': get('STATUS').strip().upper(),
        })
    if skipped_rrule:
        print(f"   ({skipped_rrule} repeating entries skipped)")
    return items


def parse_squarespace(data, base_url=''):
    """Upcoming items of a Squarespace events collection (?format=json)."""
    items = []
    for it in data.get('upcoming') or []:
        if not it.get('startDate'):
            continue
        loc = it.get('location') or {}
        place = ', '.join(p for p in (_clean(loc.get('addressTitle')),
                                      _clean(loc.get('addressLine1'))) if p)
        link = it.get('fullUrl') or ''
        if link.startswith('/'):
            link = base_url.rstrip('/') + link
        items.append({
            'title': _clean(it.get('title')),
            'start': _from_epoch_ms(it['startDate']),
            'end': _from_epoch_ms(it['endDate']) if it.get('endDate') else None,
            'all_day': False,
            'location': place,
            'location_coords': ((loc.get('markerLat'), loc.get('markerLng'))
                                if place else None),
            'categories': list(it.get('categories') or []),
            'link': link,
            'image': it.get('assetUrl') or '',
            'status': '',
        })
    return items


def _elfsight_when(value):
    """(datetime, has_time) from an Elfsight start/end, which is either
    {"type": "datetime", "date": "2026-12-12", "time": "13:00"}, a date-only
    dict, or (older entries) epoch milliseconds."""
    if isinstance(value, (int, float)):
        return _from_epoch_ms(value), True
    if not isinstance(value, dict) or not value.get('date'):
        return None, False
    try:
        day = datetime.strptime(value['date'], '%Y-%m-%d')
    except ValueError:
        return None, False
    if value.get('type') == 'datetime' and value.get('time'):
        try:
            hh, mm = (int(x) for x in value['time'].split(':')[:2])
            return day.replace(hour=hh, minute=mm), True
        except ValueError:
            pass
    return day, False


_HREF = re.compile(r'href="(https?://[^"]+)"', re.I)
# Placeholder place names that say nothing about where an event is.
_VAGUE_PLACE = re.compile(r'^(?:various|see description|tba|tbd)\b', re.I)


def parse_elfsight(data, widget):
    """Events of an Elfsight Event Calendar widget. Repeating entries are
    skipped (counted): the calendar surveyed lists each holiday date as its
    own entry, and its only repeats were the farmers market (already a
    recurring event) and a summer car show."""
    try:
        settings = data['data']['widgets'][widget]['data']['settings']
    except (KeyError, TypeError):
        return []
    places = {p.get('id'): p for p in settings.get('locations') or []}
    items, repeats = [], 0
    for ev in settings.get('events') or []:
        if (ev.get('repeatPeriod') or 'noRepeat') != 'noRepeat':
            repeats += 1
            continue
        start, has_time = _elfsight_when(ev.get('start'))
        if not start:
            continue
        end, _ = _elfsight_when(ev.get('end'))
        place = next((places[i] for i in ev.get('location') or [] if i in places), None)
        location = ''
        if place:
            location = ', '.join(p for p in (_clean(place.get('name')),
                                             _clean(place.get('address'))) if p)
        desc_link = _HREF.search(ev.get('description') or '')
        image = (ev.get('coverImage') or {}).get('url') or ''
        items.append({
            'title': _clean(ev.get('name')),
            'start': start, 'end': end, 'all_day': not has_time,
            'location': location,
            'categories': [],
            'link': desc_link.group(1) if desc_link else '',
            'image': image,
            'status': '',
        })
    if repeats:
        print(f"   ({repeats} repeating entries skipped)")
    return items


_FOO_OBJ = re.compile(r"var\s+localObj\s*=\s*'((?:[^'\\]|\\.)*)'", re.S)


def parse_fooevents(page):
    """Events from the FooEvents calendar JSON a WooCommerce page embeds as a
    JavaScript string: var localObj = '{"0": {...}, "1": {...}, ...}';"""
    m = _FOO_OBJ.search(page)
    if not m:
        return []
    try:
        # Two layers: a JS string literal, holding JSON.
        literal = m.group(1).replace("\\'", "'")
        obj = json.loads(json.loads('"' + literal + '"'))
    except ValueError:
        return []
    items = []
    for key, ev in obj.items():
        if not key.isdigit() or not isinstance(ev, dict):
            continue
        try:
            start = datetime.strptime(str(ev.get('start'))[:19], '%Y-%m-%dT%H:%M:%S')
        except ValueError:
            continue
        items.append({
            'title': _clean(ev.get('title')),
            'start': start, 'end': None, 'all_day': bool(ev.get('allDay')),
            'location': _clean(ev.get('location')),
            'categories': [],
            'link': ev.get('url') or '',
            'image': '',
            'status': '',
        })
    return items


_WIX_DATA = re.compile(r'<script[^>]*id="wix-warmup-data"[^>]*>(.*?)</script>', re.S)
_WIX_CANCELED = 3   # Wix event status: 0 scheduled, 1 started, 2 ended, 3 canceled
_WIX_ONLINE = 1     # Wix location type: 0 venue, 1 online


def _wix_utc(value):
    try:
        return eastern_from_utc(datetime.strptime(str(value)[:19], '%Y-%m-%dT%H:%M:%S'))
    except ValueError:
        return None


def parse_wix(page, base_url=''):
    """Events of a Wix Events list, from the JSON a Wix page carries in its
    "wix-warmup-data" script. The events sit a few levels down (appsWarmupData,
    then the app, then the widget), so any dict shaped like an event is taken,
    once per id. Times are UTC ISO stamps. A widget that pages its list says
    hasMore; only the first page is read and the log says so."""
    m = _WIX_DATA.search(page)
    if not m:
        return []
    try:
        data = json.loads(m.group(1))
    except ValueError:
        return []

    found, more = [], False

    def walk(node):
        nonlocal more
        if isinstance(node, dict):
            if 'scheduling' in node and 'title' in node and 'slug' in node:
                found.append(node)
                return
            if node.get('hasMore') is True:
                more = True
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(data)
    items, seen = [], set()
    for ev in found:
        if ev.get('id') in seen:
            continue
        seen.add(ev.get('id'))
        config = (ev.get('scheduling') or {}).get('config') or {}
        if config.get('scheduleTbd'):
            continue
        start = _wix_utc(config.get('startDate'))
        if not start:
            continue
        end = _wix_utc(config.get('endDate')) if config.get('endDate') else None
        loc = ev.get('location') or {}
        if loc.get('type') == _WIX_ONLINE:
            location = 'Online'
        else:
            address = re.sub(r',\s*(?:USA|United States)$', '', _clean(loc.get('address')))
            location = ', '.join(p for p in (_clean(loc.get('name')), address) if p)
        coords = loc.get('coordinates') or {}
        items.append({
            'title': _clean(ev.get('title')),
            'start': start, 'end': end, 'all_day': False,
            'location': location,
            'location_coords': ((coords.get('lat'), coords.get('lng'))
                                if coords.get('lat') is not None else None),
            'categories': [c.get('name', '') for c in ev.get('categories') or []
                           if isinstance(c, dict)],
            'link': (base_url.rstrip('/') + '/event-details/' + ev['slug']) if ev.get('slug') else '',
            'image': (ev.get('mainImage') or {}).get('url') or '',
            'status': 'CANCELLED' if ev.get('status') == _WIX_CANCELED else '',
        })
    if more:
        print("   (the Wix list has more pages; only the first was read)")
    return items


# --------------------------------------------------------------------------
# Filtering and shaping
# --------------------------------------------------------------------------

def _town_coords():
    """Roster towns of every area config: name (lowercase) -> (lat, lng)."""
    towns = {}
    config_dir = os.path.join(REPO, 'config')
    for name in os.listdir(config_dir):
        if not name.endswith('.json'):
            continue
        try:
            with open(os.path.join(config_dir, name), encoding='utf-8') as f:
                cfg = json.load(f)
        except (OSError, ValueError):
            continue
        if not isinstance(cfg, dict):
            continue
        for town in cfg.get('towns') or []:
            towns[town['name'].lower()] = (town['lat'], town['lng'])
    return towns


def _near(a, b, miles=10):
    try:
        return abs(float(a[0]) - b[0]) * 69 < miles and abs(float(a[1]) - b[1]) * 53 < miles
    except (TypeError, ValueError):
        return False


def _venue(item, feed, towns):
    """(venue name, {"lat", "lng"}) for an item, or None when the item is
    somewhere the area rosters don't know."""
    default = feed.get('venue') or {}
    name = default.get('name', '')
    coords = (default.get('lat'), default.get('lng'))
    location = item.get('location', '')

    if feed.get('venue_template') and location:
        room = re.sub(feed.get('strip_location') or r'^$', '', location).strip(' ,')
        if room:
            name = feed['venue_template'].format(room=room)
    elif (feed['format'] in ('squarespace', 'elfsight', 'wix') and location
          and not _VAGUE_PLACE.search(location)):
        # These feeds name a place per event; a street address that names a
        # roster town gives its coordinates, and one naming another town
        # means the event is outside the area. The town is the LAST roster
        # name in the address: "Valley Forge Rd, Phoenixville" is Phoenixville.
        name = re.sub(r',?\s*PA\s*\d{5}$', '', location).strip(' ,')
        found = [(m.start(), t) for t in towns
                 for m in re.finditer(r'\b' + re.escape(t) + r'\b', location.lower())]
        town = max(found)[1] if found else None
        if town:
            coords = towns[town]
        elif re.search(r',\s*[A-Z][a-z]+(?: [A-Z][a-z]+)*,?\s*(?:PA|NJ|DE|MD|NY)\b', location):
            return None
        if item.get('location_coords') and _near(item['location_coords'], coords):
            coords = tuple(float(c) for c in item['location_coords'])

    if coords[0] is None:
        return None
    return name, {'lat': coords[0], 'lng': coords[1]}


def select_items(items, feed, today=None):
    """Apply a feed's filters. Returns (kept, dropped_count)."""
    today = (today or datetime.now()).replace(hour=0, minute=0, second=0, microsecond=0)
    horizon = today + timedelta(days=int(feed.get('horizon_days', HORIZON_DAYS)))
    include = {c.lower() for c in feed.get('include_categories') or []}
    exclude = {c.lower() for c in feed.get('exclude_categories') or []}
    title_re = re.compile(feed['exclude_title'], re.I) if feed.get('exclude_title') else None
    where_re = re.compile(feed['require_location'], re.I) if feed.get('require_location') else None

    kept = []
    for it in items:
        cats = {c.lower() for c in it.get('categories') or []}
        last = it.get('end') or it['start']
        if (not it['title'] or last < today or it['start'] >= horizon
                or it.get('status') == 'CANCELLED' or _CANCELLED.search(it['title'])
                or _ONLINE.search(it.get('location', ''))
                or (include and not cats & include) or (cats & exclude)
                or (title_re and title_re.search(it['title']))
                or (where_re and not where_re.search(it.get('location', '')))):
            continue
        kept.append(it)

    limit = feed.get('max_repeats')
    if limit:
        counts = {}
        for it in kept:
            counts[repeat_key(it['title'])] = counts.get(repeat_key(it['title']), 0) + 1
        kept = [it for it in kept if counts[repeat_key(it['title'])] <= int(limit)]

    return kept, len(items) - len(kept)


def to_event(item, feed, towns):
    """One pipeline event (the shape every scraper writes), or None."""
    placed = _venue(item, feed, towns)
    if not placed:
        return None
    venue_name, location = placed
    start, end = item['start'], item.get('end')
    # A same-day end is a time range, not a run; only a later date makes one.
    run_end = end if end and end.date() > start.date() else None

    category = feed.get('category')
    if not category:
        # The feed's own categories first ("Preschool" is Kids & Family
        # whatever the title says), then the title rules West Chester uses.
        cats = ', '.join(item.get('categories') or [])
        category = next((c for pattern, c in (feed.get('category_map') or {}).items()
                         if cats and re.search(pattern, cats, re.I)), None)
    if not category:
        category = next((c for pattern, c in _TITLE_RULES if pattern.search(item['title'])),
                        None) or _category(item['title'])
    attributes = {
        'category': category,
        'vibes': list(feed.get('vibes') or []),
    }
    time_label = _time_label(start, item.get('all_day'))
    if time_label:
        attributes['time'] = time_label
    if re.search(r'\bfree\b', item['title'], re.I):
        attributes['price'] = 'Free'

    return {
        'id': f"{feed['id']}_{_slug(item['title'])}_{start:%Y%m%d%H%M}",
        'type': 'event',
        'title': item['title'],
        'venue_info': {'name': venue_name, 'location': location},
        'raw_date_string': _raw_date_string(start, run_end),
        'attributes': attributes,
        'media': {'image': item.get('image') or ''},
        'action_link': item.get('link') or feed.get('link') or feed.get('url', ''),
    }


def build_events(items, feed, today=None):
    """Filter a feed's items and shape them as pipeline events."""
    for old, new in (feed.get('title_fixes') or {}).items():
        for it in items:
            it['title'] = it['title'].replace(old, new)
    kept, dropped = select_items(items, feed, today=today)
    towns = _town_coords()
    events, seen, outside = [], set(), 0
    for it in kept:
        ev = to_event(it, feed, towns)
        if not ev:
            outside += 1
            continue
        if ev['id'] in seen:
            continue
        seen.add(ev['id'])
        events.append(ev)
    events.sort(key=lambda e: e['id'].rsplit('_', 1)[-1])
    return events, dropped, outside


# --------------------------------------------------------------------------
# Fetch and write
# --------------------------------------------------------------------------

def fetch_items(feed):
    """Download a feed and parse it. Raises on HTTP or format trouble."""
    fmt = feed['format']
    headers = dict(BROWSER_HEADERS)
    if fmt in ('squarespace', 'elfsight'):
        headers['Accept'] = 'application/json'
    url = feed['url']
    params = None
    if fmt == 'elfsight':
        params = {'page': url, 'w': feed['widget']}
        url = 'https://core.service.elfsight.com/p/boot/'
    elif fmt == 'squarespace' and 'format=json' not in url:
        url += ('&' if '?' in url else '?') + 'format=json'

    response = requests.get(url, params=params, headers=headers, timeout=TIMEOUT)
    if response.status_code != 200:
        raise ValueError(f"HTTP {response.status_code}")

    if fmt == 'ics':
        if 'BEGIN:VCALENDAR' not in response.text[:500]:
            raise ValueError('not an iCalendar feed')
        return parse_ics(response.text)
    if fmt == 'squarespace':
        base = re.match(r'https?://[^/]+', feed['url']).group(0)
        return parse_squarespace(response.json(), base)
    if fmt == 'elfsight':
        return parse_elfsight(response.json(), feed['widget'])
    if fmt == 'fooevents':
        return parse_fooevents(response.text)
    if fmt == 'wix':
        base = re.match(r'https?://[^/]+', feed['url']).group(0)
        return parse_wix(response.text, base)
    raise ValueError(f"unknown feed format {fmt!r}")


def scrape_feed(output_file, feed):
    """Read one published calendar into a scraped events file."""
    print(f">> Reading {feed['id']} ({feed['format']}) from {feed['url']}...")
    try:
        items = fetch_items(feed)
    except (requests.RequestException, ValueError) as e:
        print(f"   ! {feed['id']}: {e}")
        _fallback(output_file)
        return

    # Nothing parsed at all means the format moved or a wall served a shell;
    # keep the last good file. Items that all filter out is a real answer.
    if not items:
        print(f"   ! {feed['id']}: feed loaded but nothing could be read from it")
        _fallback(output_file)
        return

    events, dropped, outside = build_events(items, feed)
    os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(events, f, indent=2, ensure_ascii=False)
    print(f">> Done! {feed['id']}: {len(events)} events from {len(items)} entries "
          f"({dropped} filtered, {outside} outside the area)")


def _fallback(output_file):
    if os.path.exists(output_file):
        print(f"   Using cached {output_file}")
    else:
        os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump([], f)
        print(f"   Wrote empty {output_file}")

import json
import os
from datetime import datetime, timedelta
import re


def parse_date_advanced(date_string):
    """Parse various date formats and return a datetime object."""
    try:
        date_string = re.sub(r'\s+', ' ', date_string.strip())

        if ' - ' in date_string or '- ' in date_string:
            date_string = date_string.split(' - ')[0].strip()
            date_string = date_string.split('- ')[0].strip()

        match = re.match(r'([A-Za-z]+)\s+(\d+)(?:,?\s+(\d{4}))?', date_string)
        if match:
            month_name = match.group(1)
            day = int(match.group(2))
            year = int(match.group(3)) if match.group(3) else datetime.now().year

            month_map = {
                'Jan': 1, 'January': 1, 'Feb': 2, 'February': 2,
                'Mar': 3, 'March': 3, 'Apr': 4, 'April': 4,
                'May': 5, 'Jun': 6, 'June': 6, 'Jul': 7, 'July': 7,
                'Aug': 8, 'August': 8, 'Sep': 9, 'Sept': 9, 'September': 9,
                'Oct': 10, 'October': 10, 'Nov': 11, 'November': 11,
                'Dec': 12, 'December': 12
            }
            month = month_map.get(month_name, 1)
            return datetime(year, month, day)

    except Exception as e:
        print(f"   ! Date parse error for '{date_string}': {e}")
        return None

    return None


# The display date is the client's grouping key: "Jul 11" and "July 11"
# render as two separate day sections, so every emitted month name must
# collapse to one canonical form.
_MONTH_CANON = {
    'jan': 'Jan', 'january': 'Jan', 'feb': 'Feb', 'february': 'Feb',
    'mar': 'Mar', 'march': 'Mar', 'apr': 'Apr', 'april': 'Apr', 'may': 'May',
    'jun': 'Jun', 'june': 'Jun', 'jul': 'Jul', 'july': 'Jul',
    'aug': 'Aug', 'august': 'Aug', 'sep': 'Sep', 'sept': 'Sep', 'september': 'Sep',
    'oct': 'Oct', 'october': 'Oct', 'nov': 'Nov', 'november': 'Nov',
    'dec': 'Dec', 'december': 'Dec',
}


def _canon_month(name):
    return _MONTH_CANON.get(name.lower(), name)


# Times arrive two ways: recurring events carry attributes.time ("9am-12pm"),
# while scraped and discovered events tack it onto the date string
# ("July 20, 2026 7:00 PM"). Normalize both to a compact "7pm" / "9am-12pm".
_TIME_IN_DATE = re.compile(
    r'\b(\d{1,2})(?::(\d{2}))?\s*([ap])\.?m\.?\b', re.IGNORECASE)


def _tidy_time(hour, minute, meridiem):
    hour = int(hour)
    if hour == 0:
        hour = 12
    suffix = meridiem.lower() + 'm'
    if minute and minute != '00':
        return f"{hour}:{minute}{suffix}"
    return f"{hour}{suffix}"


def extract_time(event):
    """Best available start time for an event, or '' when none is known."""
    stated = (event.get('attributes') or {}).get('time')
    if stated:
        # Already human-readable from the recurring config; just tighten spacing.
        return re.sub(r'\s*-\s*', '-', str(stated).strip())

    match = _TIME_IN_DATE.search(str(event.get('raw_date_string', '')))
    if match:
        return _tidy_time(match.group(1), match.group(2), match.group(3))
    return ''


# Sources fill the price field with these when they don't actually know it.
# Showing "Check Link" reads as information and isn't — better to show nothing
# and let the row's link speak for itself.
_PRICE_PLACEHOLDERS = re.compile(
    r'^(check\s*(link|website|site)?|varies|tba|tbd|see\s+website|n/?a)\.?$',
    re.IGNORECASE)


def extract_price(event):
    """Price string from source attributes, normalized for display."""
    price = (event.get('attributes') or {}).get('price')
    if not price:
        return ''
    price = str(price).strip()
    if _PRICE_PLACEHOLDERS.match(price):
        return ''
    # Collapse the many ways sources say "free" into one label.
    if re.fullmatch(r'free(\s+(entry|admission))?!?', price, re.IGNORECASE):
        return 'Free'
    # Discovery has emitted mangled amounts ("5 advance / 0 at door" for
    # "$25 advance / $30 at door"). A ticket price that names a tier but
    # carries no currency symbol lost its digits somewhere upstream — showing
    # it is worse than showing nothing, since the number reads as real.
    if re.search(r'\d', price) and '$' not in price \
            and re.search(r'advance|door|adv\b|gate', price, re.IGNORECASE):
        return ''
    return price


def _richness(event):
    """
    Rank two copies of the same event. Mirrors merge._richness but reads the
    already-transformed shape.

    Series identity outranks everything: discovery keeps rediscovering the
    recurring events under slightly different titles ("Phoenixville Farmers
    Market - Saturday"), and if one of those wins the dedupe it takes the
    series key with it, so the app can no longer fold the run into one row.
    Then time and price, which are what the reader decides on, then image/link.
    """
    return (bool(event.get('series')),
            bool(event.get('time')), bool(event.get('price')),
            'placehold.co' not in event.get('img', ''), bool(event.get('link')))


def format_date_display(date_string):
    """Convert date string to readable display format."""
    try:
        date_string = re.sub(r'\s+', ' ', date_string.strip())

        if ' - ' in date_string or '- ' in date_string:
            date_string = date_string.replace('- ', ' - ').replace(' -', ' - ')
            parts = date_string.split(' - ')

            if len(parts) == 2:
                start = parts[0].strip()
                end = parts[1].strip()

                start_match = re.match(r'([A-Za-z]+)\s+(\d+)', start)
                if start_match:
                    start_month = _canon_month(start_match.group(1))
                    start_day = int(start_match.group(2))

                    if re.match(r'^\d+', end):
                        end_day = int(re.match(r'^\d+', end).group())
                        return f"{start_month} {start_day}-{end_day}"

                    end_match = re.match(r'([A-Za-z]+)\s+(\d+)', end)
                    if end_match:
                        end_month = _canon_month(end_match.group(1))
                        end_day = int(end_match.group(2))
                        return f"{start_month} {start_day} - {end_month} {end_day}"

        single_match = re.match(r'([A-Za-z]+)\s+(\d+)', date_string)
        if single_match:
            month = _canon_month(single_match.group(1))
            day = int(single_match.group(2))
            return f"{month} {day}"

        current_year = str(datetime.now().year)
        return date_string.replace(f', {current_year}', '').replace(f' {current_year}', '')

    except Exception as e:
        print(f"   ! Date format error for '{date_string}': {e}")
        return date_string


def get_date_category(event_date):
    """Categorize event into time buckets for filtering."""
    if not event_date:
        return 'later'

    now = datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)
    week_end = today + timedelta(days=7)
    next_week_end = today + timedelta(days=14)
    month_end = today.replace(day=1) + timedelta(days=32)
    month_end = month_end.replace(day=1) - timedelta(days=1)

    if event_date.date() == today.date():
        return 'today'
    elif event_date.date() == tomorrow.date():
        return 'tomorrow'
    elif event_date < week_end:
        return 'this_week'
    elif event_date < next_week_end:
        return 'next_week'
    elif event_date <= month_end:
        return 'this_month'
    else:
        return 'later'


def get_smart_label(event_date):
    """Generate human-friendly labels like 'Today', 'Tomorrow', etc."""
    if not event_date:
        return ""

    now = datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)
    week_end = today + timedelta(days=7)

    if event_date.date() == today.date():
        return "Today"
    elif event_date.date() == tomorrow.date():
        return "Tomorrow"
    elif event_date < week_end:
        return "This Week"
    else:
        return ""


from pipeline.slugs import venue_key  # noqa: E402  (no cycle: slugs imports only analytics)

_TITLE_STOPWORDS = {'the', 'a', 'an', 'at', 'of', 'in', 'on', 'with', 'and', 'for', 'to'}


def _title_tokens(title):
    # Years and ordinals never distinguish two events on the same date -
    # "WCU Homecoming 2026" and "WCU Homecoming & Family Weekend" are one
    # event, and "29th Annual Kennett Brewfest" is "Kennett Brewfest".
    # Left in, the year is the one token that fails the 100% overlap rule.
    t = re.sub(r'\b(?:19|20)\d{2}\b', ' ', title.lower())
    t = re.sub(r'\b\d+(?:st|nd|rd|th)\b', ' ', t)
    words = re.findall(r'[a-z0-9]+', t)
    return frozenset(w for w in words if w not in _TITLE_STOPWORDS)


def fuzzy_dedupe(events):
    """Merge near-duplicate events: same parsed date, one title's tokens a
    subset of the other's ("First Friday - July" vs "First Friday - Downtown
    Phoenixville (July)"), or nearly so (>=85% of the smaller title's tokens,
    4-token minimum - "Reads & Co Presents Lisa Scottoline..." vs "Lisa
    Scottoline: ... Live Author Event"). The threshold must stay above 0.80:
    same-series events like "CIRQUE du BLOBFEST: Costume Contest" vs
    "...: Blob Ball - Annual Costume Gala" overlap at exactly 0.80 and are
    distinct. Keeps the richer copy. Undated events are skipped - they all
    share a sentinel timestamp and would over-merge.

    A title match alone is not enough when the titles differ a lot in
    length: an umbrella listing ("West Chester Comedy Festival", "WCU
    Homecoming") is a token-subset of every one of its sub-events ("...:
    Friday Headliner Show at Windish Studios", "WCU Homecoming Football:
    Golden Rams vs. Millersville"), and those are distinct events at
    distinct venues. So a lopsided pair (smaller title under 3/4 the size of
    the larger) only merges when both copies sit at the same venue - which
    is exactly what the same event from two sources looks like. Known cost:
    one show under two venue names ("Paranormal Cirque" at the Expo Center
    vs "...Specter - Horror Circus" at "Paranormal Cirque Big Top") now
    lists twice. A duplicate row beats a vanished event."""
    by_date = {}
    for ev in events:
        by_date.setdefault(ev['_sort_date'], []).append(ev)

    removed = 0
    result = []
    for ts, group in by_date.items():
        if ts == 9999999999 or len(group) == 1:
            result.extend(group)
            continue
        kept = []  # list of [tokens, event, richness]
        for ev in group:
            tokens = _title_tokens(ev['title'])
            richness = _richness(ev)
            merged = False
            for entry in kept:
                small, large = (tokens, entry[0]) if len(tokens) <= len(entry[0]) else (entry[0], tokens)
                overlap = len(small & large) / len(small) if small else 0
                similar = (len(small) >= 2 and overlap == 1.0) or (len(small) >= 4 and overlap >= 0.85)
                close = (len(small) / len(large) >= 0.75 if large else False) \
                    or venue_key(ev.get('loc')) == venue_key(entry[1].get('loc'))
                if similar and close:
                    removed += 1
                    if richness > entry[2]:
                        entry[0], entry[1], entry[2] = tokens, ev, richness
                    merged = True
                    break
            if not merged:
                kept.append([tokens, ev, richness])
        result.extend(entry[1] for entry in kept)

    if removed:
        print(f"   Removed {removed} near-duplicate events (fuzzy title match)")
    return result


def transform_events(input_file, output_file):
    """Transform scraped events with date parsing, filtering, and categorization."""
    print(f">> Reading {input_file}...")

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            scraped_data = json.load(f)
    except FileNotFoundError:
        print(f"   ! Error: {input_file} not found!")
        return []

    print(f">> Transforming {len(scraped_data)} events...")

    transformed_events = []
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    for event in scraped_data:
        try:
            raw_date = event.get("raw_date_string", "TBA")
            event_datetime = parse_date_advanced(raw_date)

            # Skip past events
            if event_datetime and event_datetime < today:
                continue

            display_date = format_date_display(raw_date)
            smart_label = get_smart_label(event_datetime) if event_datetime else ""
            date_category = get_date_category(event_datetime) if event_datetime else 'later'

            transformed = {
                "title": event.get("title", "Untitled Event"),
                "date": display_date,
                "date_label": smart_label,
                "date_category": date_category,
                "type": event.get("attributes", {}).get("category", "Event"),
                "loc": event.get("venue_info", {}).get("name", "Unknown Venue"),
                # Set by pipeline/geo.py from venue coordinates. The app groups
                # and filters on this rather than re-parsing the venue string.
                "town": event.get("town", ""),
                "time": extract_time(event),
                "price": extract_price(event),
                # Weekly series identity, set by pipeline/recurring.py
                "series": (event.get("attributes") or {}).get("series", ""),
                "cadence": (event.get("attributes") or {}).get("cadence", ""),
                "weekday": (event.get("attributes") or {}).get("weekday", ""),
                "img": event.get("media", {}).get("image", "https://placehold.co/400x300?text=No+Image"),
                "link": event.get("action_link", ""),
                "_sort_date": event_datetime.timestamp() if event_datetime else 9999999999
            }

            transformed_events.append(transformed)

        except Exception as e:
            print(f"   ! Skipped event '{event.get('title', 'unknown')}': {e}")

    # Second dedupe pass: sources may write the same date differently
    # ("June 17 - September 2" vs "Jun 17 - Sep 2"), which slips past the
    # merge-level dedupe. After parsing they share a timestamp, so dedupe on
    # normalized title + parsed date, preferring the copy with a real image.
    best = {}
    order = []
    for ev in transformed_events:
        key = re.sub(r'[^a-z0-9]', '', ev['title'].lower()) + '|' + str(ev['_sort_date'])
        richness = ('placehold.co' not in ev['img'], bool(ev['link']))
        if key not in best:
            best[key] = (ev, richness)
            order.append(key)
        elif richness > best[key][1]:
            best[key] = (ev, richness)
    if len(best) < len(transformed_events):
        print(f"   Removed {len(transformed_events) - len(best)} duplicate events (post-parse)")
    transformed_events = [best[k][0] for k in order]

    transformed_events = fuzzy_dedupe(transformed_events)

    # Sort by date. Keep _sort_date in the serialized output so downstream consumers
    # (e.g. inject.py building Event JSON-LD) can derive an ISO startDate without
    # re-parsing the display string.
    transformed_events.sort(key=lambda x: x["_sort_date"])

    os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(transformed_events, f, indent=2, ensure_ascii=False)

    print(f">> SUCCESS! Transformed {len(transformed_events)} upcoming events")
    print(f">> Saved to: {output_file}")
    return transformed_events


if __name__ == "__main__":
    transform_events('all_events.json', 'events_formatted.json')

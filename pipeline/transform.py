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
                'Aug': 8, 'August': 8, 'Sep': 9, 'September': 9,
                'Oct': 10, 'October': 10, 'Nov': 11, 'November': 11,
                'Dec': 12, 'December': 12
            }
            month = month_map.get(month_name, 1)
            return datetime(year, month, day)

    except Exception as e:
        print(f"   ! Date parse error for '{date_string}': {e}")
        return None

    return None


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
                    start_month = start_match.group(1)
                    start_day = int(start_match.group(2))

                    if re.match(r'^\d+', end):
                        end_day = int(re.match(r'^\d+', end).group())
                        return f"{start_month} {start_day}-{end_day}"

                    end_match = re.match(r'([A-Za-z]+)\s+(\d+)', end)
                    if end_match:
                        end_month = end_match.group(1)
                        end_day = int(end_match.group(2))
                        return f"{start_month} {start_day} - {end_month} {end_day}"

        single_match = re.match(r'([A-Za-z]+)\s+(\d+)', date_string)
        if single_match:
            month = single_match.group(1)
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


_TITLE_STOPWORDS = {'the', 'a', 'an', 'at', 'of', 'in', 'on', 'with', 'and', 'for', 'to'}


def _title_tokens(title):
    words = re.findall(r'[a-z0-9]+', title.lower())
    return frozenset(w for w in words if w not in _TITLE_STOPWORDS)


def fuzzy_dedupe(events):
    """Merge near-duplicate events: same parsed date, one title's tokens a
    subset of the other's ("First Friday - July" vs "First Friday - Downtown
    Phoenixville (July)"). Keeps the richer copy. Undated events are skipped -
    they all share a sentinel timestamp and would over-merge."""
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
            richness = ('placehold.co' not in ev['img'], bool(ev['link']))
            merged = False
            for entry in kept:
                small, large = (tokens, entry[0]) if len(tokens) <= len(entry[0]) else (entry[0], tokens)
                if len(small) >= 2 and small <= large:
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

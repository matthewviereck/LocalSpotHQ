import json
import os
from datetime import datetime, timedelta


def generate_recurring_events(config_file, output_file):
    """
    Generate recurring events from a config JSON file.
    Config defines weekly, monthly, and festival events with dates and metadata.
    """
    print(">> Generating recurring events...")

    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)

    events = []

    for event_def in config.get('events', []):
        event_type = event_def.get('type')

        if event_type == 'weekly':
            new_events = _generate_weekly(event_def)
        elif event_type == 'monthly':
            new_events = _generate_monthly(event_def)
        elif event_type == 'festival':
            new_events = _generate_festival(event_def)
        else:
            print(f"   ! Unknown event type: {event_type}")
            continue

        events.extend(new_events)
        print(f"   Added {len(new_events)} {event_def.get('title', 'unknown')} events")

    os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(events, f, indent=2, ensure_ascii=False)

    print(f"\n>> SUCCESS! Generated {len(events)} recurring events")
    print(f">> Saved to: {output_file}")
    return events


_WEEKDAYS = {'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
             'friday': 4, 'saturday': 5, 'sunday': 6}


def _today():
    return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)


def _nth_weekday_of_month(year, month, weekday, nth):
    first = datetime(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    return first + timedelta(days=offset + 7 * (nth - 1))


def _generate_weekly(event_def):
    """Generate weekly recurring events.

    Rolling form ("weekday" + optional "horizon_days", parity with the PHP
    builder): next occurrence through today + horizon, so the calendar never
    runs dry at a fixed end_date. Unlike PHP's 'next Saturday', today itself
    is included - the market should still be listed on its own morning.
    Legacy form: fixed "start_date"/"end_date".
    """
    events = []
    if 'weekday' in event_def:
        today = _today()
        weekday = _WEEKDAYS[event_def['weekday'].lower()]
        start = today + timedelta(days=(weekday - today.weekday()) % 7)
        end = today + timedelta(days=event_def.get('horizon_days', 364))
    else:
        start = datetime.strptime(event_def['start_date'], '%Y-%m-%d')
        end = datetime.strptime(event_def['end_date'], '%Y-%m-%d')
    current = start

    while current <= end:
        month = current.month
        # Determine season-specific time
        time_info = event_def.get('time', '')
        for season in event_def.get('seasons', []):
            months = season.get('months', [])
            if month in months:
                time_info = season.get('time', time_info)
                break

        event = {
            "id": f"{event_def['id_prefix']}_{current.strftime('%Y%m%d')}",
            "type": "event",
            "title": event_def['title'],
            "venue_info": {
                "name": event_def['venue'],
                "location": event_def.get('location', {})
            },
            "raw_date_string": current.strftime("%b %d, %Y"),
            "attributes": {
                "category": event_def.get('category', 'Event'),
                "vibes": event_def.get('vibes', []),
                "price": event_def.get('price', ''),
                "time": time_info
            },
            "media": {"image": event_def.get('image', '')},
            "action_link": event_def.get('link', '')
        }
        events.append(event)
        current += timedelta(days=7)

    return events


def _generate_monthly(event_def):
    """Generate monthly recurring events.

    Rolling form ("nth" + "weekday" + optional "horizon_months"): the nth
    <weekday> of each month from this month through the horizon, skipping
    dates already past. Legacy form: explicit "dates" list.
    """
    events = []

    date_entries = event_def.get('dates', [])
    if 'nth' in event_def and 'weekday' in event_def:
        today = _today()
        weekday = _WEEKDAYS[event_def['weekday'].lower()]
        date_entries = []
        for i in range(event_def.get('horizon_months', 12) + 1):
            year = today.year + (today.month - 1 + i) // 12
            month = (today.month - 1 + i) % 12 + 1
            d = _nth_weekday_of_month(year, month, weekday, event_def['nth'])
            if d >= today:
                date_entries.append(d.strftime('%Y-%m-%d'))

    for date_entry in date_entries:
        if isinstance(date_entry, str):
            date_str = date_entry
            subtitle = ""
        else:
            date_str = date_entry['date']
            subtitle = date_entry.get('subtitle', '')

        event_date = datetime.strptime(date_str, '%Y-%m-%d')
        month_name = event_date.strftime("%B")

        title = event_def.get('title_template', event_def.get('title', ''))
        title = title.replace('{month_name}', month_name)
        if subtitle:
            title = f"{title} - {subtitle}"

        # Check for special overrides
        special_vibes = list(event_def.get('vibes', []))
        for override in event_def.get('overrides', []):
            if override.get('month') == event_date.month:
                if override.get('extra_vibes'):
                    special_vibes.extend(override['extra_vibes'])

        event = {
            "id": f"{event_def['id_prefix']}_{event_date.strftime('%Y%m%d')}",
            "type": "event",
            "title": title,
            "venue_info": {
                "name": event_def['venue'],
                "location": event_def.get('location', {})
            },
            "raw_date_string": event_date.strftime("%b %d, %Y"),
            "attributes": {
                "category": event_def.get('category', 'Community Event'),
                "vibes": special_vibes,
                "price": event_def.get('price', 'Free'),
                "time": event_def.get('time', '')
            },
            "media": {"image": event_def.get('image', '')},
            "action_link": event_def.get('link', '')
        }
        events.append(event)

    return events


def _generate_festival(event_def):
    """Generate multi-day festival events.

    Rule form ("rule": {month, nth, weekday} with per-day "offset"s): anchors
    the festival to e.g. the second Friday of July for this year and next, so
    the config never goes stale. Legacy form: explicit "date" per day.
    """
    events = []

    days = event_def.get('days', [])
    if 'rule' in event_def:
        rule = event_def['rule']
        today = _today()
        rolled = []
        for year in (today.year, today.year + 1):
            anchor = _nth_weekday_of_month(
                year, rule['month'], _WEEKDAYS[rule['weekday'].lower()], rule['nth'])
            for day in days:
                d = anchor + timedelta(days=day.get('offset', 0))
                if d >= today:
                    rolled.append({'date': d.strftime('%Y-%m-%d'),
                                   'title': day.get('title', ''),
                                   'time': day.get('time', '')})
        days = rolled

    for day in days:
        event_date = datetime.strptime(day['date'], '%Y-%m-%d')

        event = {
            "id": f"{event_def['id_prefix']}_{event_date.strftime('%Y%m%d')}",
            "type": "event",
            "title": day.get('title', event_def.get('title', '')),
            "venue_info": {
                "name": event_def['venue'],
                "location": event_def.get('location', {})
            },
            "raw_date_string": event_date.strftime("%b %d, %Y"),
            "attributes": {
                "category": event_def.get('category', 'Festival'),
                "vibes": event_def.get('vibes', []),
                "price": event_def.get('price', 'Varies'),
                "time": day.get('time', '')
            },
            "media": {"image": event_def.get('image', '')},
            "action_link": event_def.get('link', '')
        }
        events.append(event)

    return events


if __name__ == "__main__":
    generate_recurring_events(
        'data/phoenixville/recurring_events_config.json',
        'data/phoenixville/recurring_events.json'
    )

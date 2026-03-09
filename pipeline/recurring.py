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


def _generate_weekly(event_def):
    """Generate weekly recurring events."""
    events = []
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
    """Generate monthly recurring events from explicit date list."""
    events = []

    for date_entry in event_def.get('dates', []):
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
    """Generate multi-day festival events."""
    events = []

    for day in event_def.get('days', []):
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

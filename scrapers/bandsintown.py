"""Scrape events from a Bandsintown public venue page.

The authenticated rest.bandsintown.com v4 API returns 403 for unregistered
app_ids, but the public venue pages embed upcoming events as schema.org
MusicEvent JSON-LD, which is stable and needs no key.
"""

import json
import re
import zlib
from datetime import datetime

import requests

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml',
}


def scrape_bandsintown_venue(venue_id, venue_info, fallback_url, id_prefix, default_vibes):
    """Return a list of raw events (scraper schema), or None on fetch failure."""
    url = f"https://www.bandsintown.com/v/{venue_id}"
    print(f">> Trying Bandsintown venue page {url}...")

    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
    except requests.RequestException as e:
        print(f"   ! Bandsintown unavailable: {e}")
        return None
    if response.status_code != 200:
        print(f"   ! Bandsintown returned status {response.status_code}")
        return None

    blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>',
                        response.text, re.S)
    events = []
    seen = set()
    for block in blocks:
        try:
            data = json.loads(block)
        except ValueError:
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            types = item.get('@type', [])
            if isinstance(types, str):
                types = [types]
            if 'MusicEvent' not in types and 'Event' not in types:
                continue

            title = (item.get('name') or '').strip()
            if not title:
                continue
            # Bandsintown names events "Artist @ Venue" - keep just the artist
            at = title.rfind(' @ ')
            if at > 0:
                title = title[:at].strip()

            start = item.get('startDate', '')
            try:
                date_text = datetime.fromisoformat(start).strftime('%B %d, %Y %I:%M %p').replace(' 0', ' ')
            except ValueError:
                date_text = 'Check website'

            key = f"{title}|{date_text}"
            if key in seen:
                continue
            seen.add(key)

            img = item.get('image', '')
            if isinstance(img, list):
                img = img[0] if img else ''

            events.append({
                'id': f"{id_prefix}{zlib.crc32((title + date_text).encode('utf-8'))}",
                'type': 'event',
                'title': title,
                'venue_info': venue_info,
                'raw_date_string': date_text,
                'attributes': {
                    'category': 'Live Music',
                    'vibes': default_vibes,
                    'price': 'Check Link'
                },
                'media': {'image': img},
                'action_link': item.get('url', fallback_url)
            })
            print(f"   + {title} ({date_text})")

    return events

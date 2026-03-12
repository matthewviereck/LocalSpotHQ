import requests
from bs4 import BeautifulSoup
import json
import os

TARGET_URL = "https://www.steelcityphx.com/concerts-and-events"

VENUE_INFO = {
    "name": "Steel City Coffeehouse & Brewery",
    "location": {"lat": 40.1305, "lng": -75.5148}
}


def scrape_steel_city(output_file='steel_city_events.json'):
    """Scrape events from Steel City Coffeehouse & Brewery website."""
    print(f">> Connecting to {TARGET_URL}...")

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        response = requests.get(TARGET_URL, headers=headers, timeout=30)
    except requests.RequestException as e:
        print(f"   ! Connection error: {e}")
        _fallback(output_file)
        return

    if response.status_code != 200:
        print(f"   ! Failed to load page (status {response.status_code})")
        # Try Squarespace JSON endpoint as fallback
        if _try_squarespace_json(output_file, headers):
            return
        _fallback(output_file)
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    extracted_events = []

    # Strategy 1: Squarespace eventlist format
    event_cards = soup.find_all('article', class_='eventlist-event')
    if not event_cards:
        # Strategy 2: Squarespace summary block format
        event_cards = soup.find_all('div', class_='summary-item')
    if not event_cards:
        # Strategy 3: Generic event containers
        event_cards = soup.find_all('div', class_='eventlist--upcoming')
        if event_cards:
            event_cards = event_cards[0].find_all('article')
    if not event_cards:
        # Strategy 4: Any article tags in main content
        main = soup.find('main') or soup.find('div', id='content') or soup
        event_cards = main.find_all('article')

    print(f">> Found {len(event_cards)} events. Processing...")

    for card in event_cards:
        try:
            # Title extraction - try multiple selectors
            title_tag = (
                card.find('h1', class_='eventlist-title') or
                card.find('h2', class_='eventlist-title') or
                card.find('a', class_='eventlist-title-link') or
                card.find('h1') or card.find('h2') or card.find('h3')
            )
            title = title_tag.text.strip() if title_tag else None
            if not title:
                continue

            # Link
            link_tag = (
                card.find('a', class_='eventlist-title-link') or
                card.find('a', class_='eventlist-button') or
                card.find('a', href=True)
            )
            link = link_tag['href'] if link_tag else "#"
            if link.startswith('/'):
                link = f"https://www.steelcityphx.com{link}"

            # Date
            date_tag = (
                card.find('time', class_='event-date') or
                card.find('time') or
                card.find('span', class_='eventlist-datetag-startdate') or
                card.find('li', class_='eventlist-meta-date') or
                card.find('span', class_='event-date')
            )
            date_text = date_tag.text.strip() if date_tag else "Check website"
            if date_tag and date_tag.get('datetime'):
                date_text = date_tag['datetime']

            # Image
            img_tag = card.find('img')
            img_src = ""
            if img_tag:
                img_src = img_tag.get('data-src', img_tag.get('src', ''))

            clean_event = {
                "id": f"sc_{abs(hash(title))}",
                "type": "event",
                "title": title,
                "venue_info": VENUE_INFO,
                "raw_date_string": date_text,
                "attributes": {
                    "category": "Live Music",
                    "vibes": ["Live Music", "Coffeehouse", "Brewery"],
                    "price": "Check Link"
                },
                "media": {"image": img_src},
                "action_link": link
            }

            extracted_events.append(clean_event)
            print(f"   OK Scraped: {title}")

        except Exception as e:
            print(f"   ! Error parsing a card: {e}")

    os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(extracted_events, f, indent=2, ensure_ascii=False)

    print(f">> Done! Saved {len(extracted_events)} events to {output_file}")


def _try_squarespace_json(output_file, headers):
    """Try Squarespace JSON API endpoint."""
    json_url = f"{TARGET_URL}?format=json"
    try:
        response = requests.get(json_url, headers=headers, timeout=30)
        if response.status_code != 200:
            return False

        data = response.json()
        items = data.get('items', data.get('upcoming', []))
        if not items:
            return False

        extracted_events = []
        for item in items:
            title = item.get('title', '').strip()
            if not title:
                continue

            start_date = item.get('startDate', item.get('publishOn', ''))
            url_slug = item.get('fullUrl', item.get('urlId', ''))
            if url_slug and not url_slug.startswith('http'):
                url_slug = f"https://www.steelcityphx.com{url_slug}"

            img_src = ''
            if item.get('assetUrl'):
                img_src = item['assetUrl']

            clean_event = {
                "id": f"sc_{abs(hash(title))}",
                "type": "event",
                "title": title,
                "venue_info": VENUE_INFO,
                "raw_date_string": str(start_date),
                "attributes": {
                    "category": "Live Music",
                    "vibes": ["Live Music", "Coffeehouse", "Brewery"],
                    "price": "Check Link"
                },
                "media": {"image": img_src},
                "action_link": url_slug or TARGET_URL
            }
            extracted_events.append(clean_event)
            print(f"   OK Scraped (JSON): {title}")

        os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(extracted_events, f, indent=2, ensure_ascii=False)

        print(f">> Done! Saved {len(extracted_events)} events to {output_file}")
        return True

    except Exception:
        return False


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

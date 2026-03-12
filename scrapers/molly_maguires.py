import requests
from bs4 import BeautifulSoup
import json
import os

TARGET_URL = "https://www.mollymaguiresphoenixville.com/events/"

VENUE_INFO = {
    "name": "Molly Maguire's Irish Pub",
    "location": {"lat": 40.1317, "lng": -75.5149}
}


def scrape_molly_maguires(output_file='molly_maguires_events.json'):
    """Scrape events from Molly Maguire's Irish Pub website."""
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
        _fallback(output_file)
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    extracted_events = []

    # Strategy 1: Common event listing containers
    event_cards = soup.find_all('div', class_='event-item')
    if not event_cards:
        event_cards = soup.find_all('div', class_='event-card')
    if not event_cards:
        event_cards = soup.find_all('article', class_='event')
    if not event_cards:
        # Strategy 2: WordPress event plugins (The Events Calendar, etc.)
        event_cards = soup.find_all('div', class_='tribe-events-calendar-list__event')
    if not event_cards:
        event_cards = soup.find_all('article', class_='tribe_events')
    if not event_cards:
        # Strategy 3: Generic - look for repeated structures with dates
        event_cards = soup.find_all('div', class_='event')
    if not event_cards:
        # Strategy 4: Squarespace summary items
        event_cards = soup.find_all('div', class_='summary-item')
    if not event_cards:
        # Strategy 5: Any article or list items in main content
        main = soup.find('main') or soup.find('div', class_='content') or soup
        event_cards = main.find_all('article')
        if not event_cards:
            event_cards = main.find_all('li', class_=lambda c: c and 'event' in c.lower() if c else False)

    print(f">> Found {len(event_cards)} events. Processing...")

    for card in event_cards:
        try:
            # Title - try multiple selectors
            title_tag = (
                card.find('h2') or card.find('h3') or card.find('h1') or
                card.find('a', class_=lambda c: c and 'title' in c.lower() if c else False) or
                card.find('span', class_=lambda c: c and 'title' in c.lower() if c else False)
            )
            title = title_tag.text.strip() if title_tag else None
            if not title:
                continue

            # Link
            link_tag = card.find('a', href=True)
            link = link_tag['href'] if link_tag else TARGET_URL
            if link.startswith('/'):
                link = f"https://www.mollymaguiresphoenixville.com{link}"

            # Date
            date_tag = (
                card.find('time') or
                card.find('span', class_=lambda c: c and 'date' in c.lower() if c else False) or
                card.find('div', class_=lambda c: c and 'date' in c.lower() if c else False) or
                card.find('p', class_=lambda c: c and 'date' in c.lower() if c else False)
            )
            date_text = date_tag.text.strip() if date_tag else "Check website"
            if date_tag and date_tag.get('datetime'):
                date_text = date_tag['datetime']

            # Image
            img_tag = card.find('img')
            img_src = ""
            if img_tag:
                img_src = img_tag.get('data-src', img_tag.get('src', ''))

            # Determine category from content
            text_lower = title.lower()
            if any(w in text_lower for w in ['karaoke', 'dj', 'dance']):
                category = "Nightlife"
                vibes = ["Nightlife", "Irish Pub"]
            elif any(w in text_lower for w in ['trivia', 'quiz']):
                category = "Trivia"
                vibes = ["Trivia", "Irish Pub"]
            elif any(w in text_lower for w in ['irish session', 'trad']):
                category = "Irish Music"
                vibes = ["Irish Music", "Traditional", "Irish Pub"]
            else:
                category = "Live Music"
                vibes = ["Live Music", "Irish Pub"]

            clean_event = {
                "id": f"mm_{abs(hash(title + date_text))}",
                "type": "event",
                "title": title,
                "venue_info": VENUE_INFO,
                "raw_date_string": date_text,
                "attributes": {
                    "category": category,
                    "vibes": vibes,
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
    scrape_molly_maguires()

import requests
from bs4 import BeautifulSoup
import json
import os

TARGET_URL = "https://phillyexpocenter.com/events/"

VENUE_INFO = {
    "name": "Greater Philadelphia Expo Center",
    "location": {"lat": 40.123, "lng": -75.450}
}


def scrape_oaks(output_file='oaks_events.json'):
    """Scrape events from Greater Philadelphia Expo Center."""
    print(f">> Connecting to {TARGET_URL}...")

    headers = {'User-Agent': 'Mozilla/5.0'}
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
    event_cards = soup.find_all('article', class_='mec-event-article')
    print(f">> Found {len(event_cards)} events. Processing...")

    extracted_events = []

    for card in event_cards:
        try:
            title_tag = card.find('h4', class_='mec-event-title').find('a')
            title = title_tag.text.strip()
            link = title_tag['href']

            start_span = card.find('span', class_='mec-start-date-label')
            end_span = card.find('span', class_='mec-end-date-label')
            date_text = ""
            if start_span:
                date_text += start_span.text.strip()
            if end_span:
                date_text += end_span.text.strip()

            img_tag = card.find('div', class_='mec-event-image')
            img_src = ""
            if img_tag:
                img = img_tag.find('img')
                if img:
                    img_src = img.get('src', '')

            loc_tag = card.find('div', class_='mec-event-loc-place')
            location = loc_tag.text.strip() if loc_tag else "Expo Center"

            clean_event = {
                "id": f"oaks_{abs(hash(title))}",
                "type": "event",
                "title": title,
                "venue_info": VENUE_INFO,
                "raw_date_string": date_text,
                "attributes": {
                    "category": "Expo",
                    "vibes": ["Family Friendly", "Large Crowd", location],
                    "price": "Check Link"
                },
                "media": {"image": img_src},
                "action_link": link
            }

            extracted_events.append(clean_event)
            print(f"   OK Scraped: {title} ({date_text})")

        except Exception as e:
            print(f"   ! Skipped an item: {e}")

    os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(extracted_events, f, indent=2, ensure_ascii=False)

    print(f">> Done! Saved {len(extracted_events)} events to {output_file}")


def _fallback(output_file):
    """If scrape fails and a cached file exists, leave it. Otherwise write empty."""
    if os.path.exists(output_file):
        print(f"   Using cached {output_file}")
    else:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump([], f)
        print(f"   Wrote empty {output_file}")


if __name__ == "__main__":
    scrape_oaks()

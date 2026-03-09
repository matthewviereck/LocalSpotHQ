import requests
from bs4 import BeautifulSoup
import json
import os

TARGET_URL = "https://thecolonialtheatre.com/events/"

VENUE_INFO = {
    "name": "The Colonial Theatre",
    "location": {"lat": 40.132, "lng": -75.513}
}


def scrape_colonial(output_file='colonial_events.json'):
    """Scrape events from The Colonial Theatre website."""
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
    event_cards = soup.find_all('div', class_='eventrow')
    print(f">> Found {len(event_cards)} events. Processing...")

    extracted_events = []

    for card in event_cards:
        try:
            title_tag = card.find('h3', class_='eventrow-title')
            title = title_tag.text.strip() if title_tag else "Unknown Event"
            clean_title = title.replace("Rising Sun Presents ", "").replace("The Colonial Presents ", "")

            btn_tag = card.find('a', class_='btn')
            link = btn_tag['href'] if btn_tag else "#"

            date_tag = card.find('time', class_='eventrow-date')
            date_text = date_tag.text.strip() if date_tag else "Check website"

            img_tag = card.find('div', class_='eventrow-img')
            img_src = ""
            if img_tag:
                img = img_tag.find('img')
                if img:
                    img_src = img.get('data-src', img.get('src', ''))

            tag_elem = card.find('a', class_='eventrow-tag')
            category = tag_elem.text.strip() if tag_elem else "General"

            clean_event = {
                "id": f"col_{abs(hash(clean_title))}",
                "type": "event",
                "title": clean_title,
                "venue_info": VENUE_INFO,
                "raw_date_string": date_text,
                "attributes": {
                    "category": category,
                    "vibes": [category, "Historic Venue"]
                },
                "media": {"image": img_src},
                "action_link": link
            }

            extracted_events.append(clean_event)
            print(f"   OK Scraped: {clean_title}")

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
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump([], f)
        print(f"   Wrote empty {output_file}")


if __name__ == "__main__":
    scrape_colonial()

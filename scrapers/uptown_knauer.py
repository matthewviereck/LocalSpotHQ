import requests
from bs4 import BeautifulSoup
import hashlib
import json
import re
import os

TARGET_URL = "https://uptownwestchester.org"

VENUE_INFO = {
    "name": "Uptown Knauer Performing Arts Center",
    "location": {"lat": 39.9607, "lng": -75.6055}
}

CATEGORY_MAP = {
    "comedy-event": "Comedy",
    "dance-event": "Dance",
    "film-event": "Film",
    "music-event": "Live Music",
    "theatre-event": "Theatre",
    "family-event": "Family",
    "fundraising": "Fundraising",
    "variety-event": "Variety",
    "special-events-event": "Special Event",
    "speaker": "Speaker",
}


def scrape_uptown(output_file='uptown_events.json'):
    """Scrape events from Uptown Knauer Performing Arts Center."""
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

    # Extract event detail page URLs from the homepage source
    # These appear in the JavaScript config and inline content
    event_slugs = re.findall(
        r'https://uptownwestchester\.org/pf/([\w-]+)/',
        response.text
    )
    event_slugs = list(dict.fromkeys(event_slugs))  # deduplicate, preserve order
    print(f">> Found {len(event_slugs)} event URLs. Scraping detail pages...")

    extracted_events = []

    for slug in event_slugs:
        try:
            event = _scrape_detail_page(slug, headers)
            if event:
                extracted_events.append(event)
                print(f"   OK Scraped: {event['title']}")
        except Exception as e:
            print(f"   ! Error scraping {slug}: {e}")

    # A loaded page with zero extracted events means the layout changed or a
    # bot wall served a shell - don't overwrite the committed fallback data.
    if not extracted_events:
        print("   ! Page loaded but no events extracted")
        _fallback(output_file)
        return

    os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(extracted_events, f, indent=2, ensure_ascii=False)

    print(f">> Done! Saved {len(extracted_events)} events to {output_file}")


def _scrape_detail_page(slug, headers):
    """Scrape an individual event detail page at /pf/{slug}/."""
    url = f"{TARGET_URL}/pf/{slug}/"
    response = requests.get(url, headers=headers, timeout=30)
    if response.status_code != 200:
        return None

    soup = BeautifulSoup(response.text, 'html.parser')

    # Title from <h1> or page title
    title = ""
    h1 = soup.find('h1')
    if h1:
        title = h1.get_text(strip=True)
    if not title:
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text(strip=True).split('|')[0].strip()

    if not title:
        return None

    # Date — look for text containing month names near "Show Time" or in content
    date_text = ""
    for text_block in soup.find_all(['p', 'div', 'span', 'h2', 'h3', 'h4']):
        txt = text_block.get_text(strip=True)
        # Match patterns like "March 11 @ 7:30 PM" or "March 11, 2026"
        date_match = re.search(
            r'((?:January|February|March|April|May|June|July|August|September|October|November|December)'
            r'\s+\d{1,2}(?:\s*[@,]\s*\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))?(?:\s*,?\s*\d{4})?)',
            txt
        )
        if date_match:
            date_text = date_match.group(1).strip()
            # Clean up: remove time portion for raw_date_string
            date_only = re.match(
                r'((?:January|February|March|April|May|June|July|August|September|October|November|December)'
                r'\s+\d{1,2}(?:\s*,?\s*\d{4})?)',
                date_text
            )
            if date_only:
                date_text = date_only.group(1)
            break

    # Image — main content image
    img_src = ""
    for img in soup.find_all('img', src=re.compile(r'/wp-content/uploads/')):
        src = img.get('src', '')
        # Skip tiny thumbnails
        if 'thegem' not in src or '850' in src or '600' in src:
            img_src = src
            break
    if not img_src:
        for img in soup.find_all('img', src=re.compile(r'/wp-content/uploads/')):
            img_src = img.get('src', '')
            break

    # Ticket link
    ticket_link = ""
    ticket_tag = soup.find('a', href=re.compile(r'ovationtix\.com'))
    if ticket_tag:
        ticket_link = ticket_tag['href']
    if not ticket_link:
        ticket_link = url

    # Category from body classes or content
    category = "Event"
    body = soup.find('body')
    if body:
        body_classes = body.get('class', [])
        for cls in body_classes:
            for cat_class, cat_name in CATEGORY_MAP.items():
                if cat_class in cls:
                    category = cat_name
                    break

    # Also try to find category in breadcrumbs or tags
    for tag_el in soup.find_all(['a', 'span'], class_=re.compile(r'tag|category|genre')):
        tag_text = tag_el.get_text(strip=True)
        if tag_text in CATEGORY_MAP.values():
            category = tag_text
            break

    return {
        "id": f"upt_{hashlib.md5(title.encode('utf-8')).hexdigest()[:12]}",
        "type": "event",
        "title": title,
        "venue_info": VENUE_INFO,
        "raw_date_string": date_text if date_text else "Check website",
        "attributes": {
            "category": category,
            "vibes": [category, "Performing Arts"]
        },
        "media": {"image": img_src},
        "action_link": ticket_link
    }


def _fallback(output_file):
    """If scrape fails and a cached file exists, leave it. Otherwise write empty."""
    if os.path.exists(output_file):
        print(f"   Using cached {output_file}")
    else:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump([], f)
        print(f"   Wrote empty {output_file}")


if __name__ == "__main__":
    scrape_uptown()

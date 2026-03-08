import requests
from bs4 import BeautifulSoup
import json
import re

# --- CONFIGURATION ---
TARGET_URL = "https://phillyexpocenter.com/events/"
OUTPUT_FILE = "oaks_events.json"

def scrape_oaks():
    print(f">> Connecting to {TARGET_URL}...")
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(TARGET_URL, headers=headers)
    
    if response.status_code != 200:
        print("X Failed to load page.")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 1. Find the container for the list (specifically the list view)
    # The site uses "mec-event-article" for each item
    event_cards = soup.find_all('article', class_='mec-event-article')

    print(f">> Found {len(event_cards)} events. Processing...")

    extracted_events = []

    for card in event_cards:
        try:
            # A. Extract Title
            title_tag = card.find('h4', class_='mec-event-title').find('a')
            title = title_tag.text.strip()
            link = title_tag['href']

            # B. Extract Date (The Tricky Part)
            # They use two formats:
            # 1. Single Span: <span class="mec-start-date-label">Feb 06 - 08 2026</span>
            # 2. Multi Span: <span class="start">Feb 26</span> <span class="end"> - Mar 01</span>
            
            start_span = card.find('span', class_='mec-start-date-label')
            end_span = card.find('span', class_='mec-end-date-label')
            
            date_text = ""
            if start_span:
                date_text += start_span.text.strip()
            if end_span:
                date_text += end_span.text.strip()
            
            # C. Extract Image
            img_tag = card.find('div', class_='mec-event-image').find('img')
            img_src = img_tag['src'] if img_tag else ""

            # D. Extract Hall/Location (e.g., "HALL A")
            loc_tag = card.find('div', class_='mec-event-loc-place')
            location = loc_tag.text.strip() if loc_tag else "Expo Center"

            # --- BUILD JSON ---
            clean_event = {
                "id": f"oaks_{abs(hash(title))}",
                "type": "event",
                "title": title,
                "venue_info": {
                    "name": "Greater Philadelphia Expo Center",
                    "location": { "lat": 40.123, "lng": -75.450 } # Hardcoded Oaks coords
                },
                "raw_date_string": date_text, 
                "attributes": {
                    "category": "Expo", # Default category
                    "vibes": ["Family Friendly", "Large Crowd", location], # Add Hall as a vibe
                    "price": "Check Link"
                },
                "media": {
                    "image": img_src
                },
                "action_link": link
            }
            
            extracted_events.append(clean_event)
            print(f"   OK Scraped: {title} ({date_text})")

        except Exception as e:
            print(f"   ! Skipped an item: {e}")

    # 3. Save to JSON
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(extracted_events, f, indent=2, ensure_ascii=False)
    
    print(f">> Done! Saved {len(extracted_events)} events to {OUTPUT_FILE}")

if __name__ == "__main__":
    scrape_oaks()

import requests
from bs4 import BeautifulSoup
import json

# --- CONFIGURATION ---
TARGET_URL = "https://thecolonialtheatre.com/events/" 
OUTPUT_FILE = "colonial_events.json"

def scrape_colonial():
    print(f">> Connecting to {TARGET_URL}...")
    
    # 1. Get the HTML
    headers = {'User-Agent': 'Mozilla/5.0'} 
    response = requests.get(TARGET_URL, headers=headers)
    
    if response.status_code != 200:
        print("X Failed to load page.")
        return

    # 2. Parse the HTML
    soup = BeautifulSoup(response.text, 'html.parser')
    
    extracted_events = []

    # --- UPDATED SELECTORS ---
    # The Colonial uses 'eventrow' for their event cards
    event_cards = soup.find_all('div', class_='eventrow')

    print(f">> Found {len(event_cards)} events. Processing...")

    for card in event_cards:
        try:
            # A. Extract Title
            title_tag = card.find('h3', class_='eventrow-title')
            title = title_tag.text.strip() if title_tag else "Unknown Event"
            
            # Remove "Rising Sun Presents" or "The Colonial Presents" if present to clean it up
            clean_title = title.replace("Rising Sun Presents ", "").replace("The Colonial Presents ", "")
            
            # B. Extract Link
            # They have a specific button for tickets
            btn_tag = card.find('a', class_='btn')
            link = btn_tag['href'] if btn_tag else "#"

            # C. Extract Date (Text)
            date_tag = card.find('time', class_='eventrow-date')
            date_text = date_tag.text.strip() if date_tag else "Check website"

            # D. Extract Image (Handle Lazy Loading)
            # The real image is often in 'data-src' not 'src'
            img_tag = card.find('div', class_='eventrow-img').find('img')
            img_src = ""
            if img_tag:
                if 'data-src' in img_tag.attrs:
                    img_src = img_tag['data-src']
                else:
                    img_src = img_tag['src']

            # E. Extract Tags (e.g., "Live Music", "Comedy")
            tag_elem = card.find('a', class_='eventrow-tag')
            category = tag_elem.text.strip() if tag_elem else "General"

            # --- BUILD JSON ---
            clean_event = {
                "id": f"col_{abs(hash(clean_title))}",
                "type": "event",
                "title": clean_title,
                "venue_info": {
                    "name": "The Colonial Theatre",
                    "location": { "lat": 40.132, "lng": -75.513 }
                },
                "raw_date_string": date_text, 
                "attributes": {
                    "category": category,
                    "vibes": [category, "Historic Venue"] # Simple logic for now
                },
                "media": {
                    "image": img_src
                },
                "action_link": link
            }
            
            extracted_events.append(clean_event)
            print(f"   OK Scraped: {clean_title}")

        except Exception as e:
            print(f"   ! Error parsing a card: {e}")

    # 3. Save to JSON
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(extracted_events, f, indent=2, ensure_ascii=False)
    
    print(f">> Done! Saved {len(extracted_events)} events to {OUTPUT_FILE}")

if __name__ == "__main__":
    scrape_colonial()

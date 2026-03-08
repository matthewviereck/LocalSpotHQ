import json
from datetime import datetime, timedelta

def generate_recurring_events(output_file='recurring_events.json'):
    """
    Generate recurring Phoenixville events:
    - Farmers Market (every Saturday)
    - First Fridays (first Friday of each month)
    - Blobfest (annual festival)
    """
    
    events = []
    
    print(">> Generating recurring events...")
    
    # ========================================
    # 1. PHOENIXVILLE FARMERS MARKET
    # ========================================
    print("   Generating Farmers Market events...")
    
    # Generate every Saturday from now until end of 2026
    start_date = datetime(2026, 2, 7)  # First Saturday after today
    end_date = datetime(2026, 12, 26)  # Last Saturday before end of year
    
    current_date = start_date
    saturday_count = 0
    
    while current_date <= end_date:
        # Determine season and time
        month = current_date.month
        if 5 <= month <= 11:  # May-November: Main season
            time_info = "9am-12pm"
            season = "Main Season"
        else:  # Dec-April: Winter hours
            time_info = "10am-12pm"
            season = "Winter Hours"
        
        event = {
            "id": f"farmers_market_{current_date.strftime('%Y%m%d')}",
            "type": "event",
            "title": "Phoenixville Farmers Market",
            "venue_info": {
                "name": "Under Gay Street Bridge",
                "location": {
                    "lat": 40.1304,
                    "lng": -75.5155
                }
            },
            "raw_date_string": current_date.strftime("%b %d, %Y"),
            "attributes": {
                "category": "Farmers Market",
                "vibes": [
                    "Family Friendly",
                    "Outdoor",
                    "Local",
                    season
                ],
                "price": "Free Entry",
                "time": time_info
            },
            "media": {
                "image": "https://images.unsplash.com/photo-1488459716781-31db52582fe9?auto=format&fit=crop&w=600&q=80"
            },
            "action_link": "https://www.phoenixvillefarmersmarket.org"
        }
        
        events.append(event)
        saturday_count += 1
        
        # Move to next Saturday
        current_date += timedelta(days=7)
    
    print(f"   Added {saturday_count} Farmers Market events")
    
    # ========================================
    # 2. FIRST FRIDAY PHOENIXVILLE
    # ========================================
    print("   Generating First Friday events...")
    
    # First Fridays: May through December 2026
    first_friday_months = [
        (2026, 2, 7),   # Feb 6 (already passed, so Feb 7)
        (2026, 3, 6),   # Mar 6
        (2026, 4, 3),   # Apr 3
        (2026, 5, 1),   # May 1
        (2026, 6, 5),   # Jun 5
        (2026, 7, 3),   # Jul 3
        (2026, 8, 7),   # Aug 7
        (2026, 9, 4),   # Sep 4
        (2026, 10, 2),  # Oct 2
        (2026, 11, 6),  # Nov 6
        (2026, 12, 4),  # Dec 4
    ]
    
    for year, month, day in first_friday_months:
        event_date = datetime(year, month, day)
        month_name = event_date.strftime("%B")
        
        # Special description for December (Tree Lighting)
        if month == 12:
            description = "Tree Lighting Ceremony with Santa!"
            special = "Tree Lighting"
        else:
            description = "Live music, craft vendors, open-air dining"
            special = "Street Festival"
        
        event = {
            "id": f"first_friday_{event_date.strftime('%Y%m%d')}",
            "type": "event",
            "title": f"First Friday - {month_name}",
            "venue_info": {
                "name": "Downtown Phoenixville",
                "location": {
                    "lat": 40.1304,
                    "lng": -75.5155
                }
            },
            "raw_date_string": event_date.strftime("%b %d, %Y"),
            "attributes": {
                "category": "Community Event",
                "vibes": [
                    "Family Friendly",
                    "Live Music",
                    "Food & Drink",
                    special
                ],
                "price": "Free",
                "time": "5:30pm-8:30pm"
            },
            "media": {
                "image": "https://images.unsplash.com/photo-1533174072545-7a4b6ad7a6c3?auto=format&fit=crop&w=600&q=80"
            },
            "action_link": "http://www.phoenixvillefirst.org/first-fridays"
        }
        
        events.append(event)
    
    print(f"   Added {len(first_friday_months)} First Friday events")
    
    # ========================================
    # 3. BLOBFEST 2026
    # ========================================
    print("   Generating Blobfest events...")
    
    # Blobfest: July 10-12, 2026
    blobfest_days = [
        {
            "date": datetime(2026, 7, 10),
            "title": "Blobfest - Opening Night",
            "description": "Film screenings & run-out",
            "time": "Evening"
        },
        {
            "date": datetime(2026, 7, 11),
            "title": "Blobfest - Street Fair",
            "description": "Street fair, vendors, live music, costume contest",
            "time": "All Day"
        },
        {
            "date": datetime(2026, 7, 12),
            "title": "Blobfest - 5K/10K/Half Marathon",
            "description": "Blobfest races & closing events",
            "time": "7am Start"
        }
    ]
    
    for blob_event in blobfest_days:
        event = {
            "id": f"blobfest_{blob_event['date'].strftime('%Y%m%d')}",
            "type": "event",
            "title": blob_event["title"],
            "venue_info": {
                "name": "The Colonial Theatre & Downtown",
                "location": {
                    "lat": 40.1304,
                    "lng": -75.5155
                }
            },
            "raw_date_string": blob_event["date"].strftime("%b %d, %Y"),
            "attributes": {
                "category": "Festival",
                "vibes": [
                    "Family Friendly",
                    "Cult Classic",
                    "Horror",
                    "Community"
                ],
                "price": "Varies",
                "time": blob_event["time"]
            },
            "media": {
                "image": "https://images.unsplash.com/photo-1574267432644-f610246f25be?auto=format&fit=crop&w=600&q=80"
            },
            "action_link": "https://thecolonialtheatre.com/blobfest/"
        }
        
        events.append(event)
    
    print(f"   Added {len(blobfest_days)} Blobfest events")
    
    # ========================================
    # SAVE TO FILE
    # ========================================
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(events, f, indent=2, ensure_ascii=False)
    
    total = len(events)
    print(f"\n>> SUCCESS! Generated {total} recurring events")
    print(f">> Saved to: {output_file}")
    
    # Summary
    print(f"\n>> Summary:")
    print(f"   Farmers Markets: {saturday_count}")
    print(f"   First Fridays: {len(first_friday_months)}")
    print(f"   Blobfest: {len(blobfest_days)}")
    print(f"   TOTAL: {total} events")
    
    return events

if __name__ == "__main__":
    generate_recurring_events()

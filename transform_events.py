import json
from datetime import datetime, timedelta
import re

def parse_date_advanced(date_string):
    """
    Parse various date formats and return a datetime object.
    Examples:
    - "Feb 5, 2026" → datetime(2026, 2, 5)
    - "Feb 06 - 08 2026" → datetime(2026, 2, 6)
    - "Feb 26 2026- Mar 01 2026" → datetime(2026, 2, 26)
    """
    try:
        # Remove extra spaces
        date_string = re.sub(r'\s+', ' ', date_string.strip())
        
        # Handle range formats - extract the START date
        if ' - ' in date_string or '- ' in date_string:
            date_string = date_string.split(' - ')[0].strip()
            date_string = date_string.split('- ')[0].strip()
        
        # Parse single date: "Feb 5, 2026" or "Feb 5 2026" or "Feb 5"
        # Match: Month Day, Year OR Month Day Year OR Month Day
        match = re.match(r'([A-Za-z]+)\s+(\d+)(?:,?\s+(\d{4}))?', date_string)
        if match:
            month_name = match.group(1)
            day = int(match.group(2))
            year = int(match.group(3)) if match.group(3) else 2026  # Default to 2026
            
            # Convert month name to number
            month_map = {
                'Jan': 1, 'January': 1,
                'Feb': 2, 'February': 2,
                'Mar': 3, 'March': 3,
                'Apr': 4, 'April': 4,
                'May': 5,
                'Jun': 6, 'June': 6,
                'Jul': 7, 'July': 7,
                'Aug': 8, 'August': 8,
                'Sep': 9, 'September': 9,
                'Oct': 10, 'October': 10,
                'Nov': 11, 'November': 11,
                'Dec': 12, 'December': 12
            }
            month = month_map.get(month_name, 1)
            
            return datetime(year, month, day)
    
    except Exception as e:
        print(f"   ! Date parse error for '{date_string}': {e}")
        return None
    
    # Fallback
    return None

def format_date_display(date_string):
    """
    Convert date string to readable format.
    Examples:
    - "Feb 5, 2026" → "Feb 5"
    - "Feb 06 - 08 2026" → "Feb 6-8"
    - "Feb 26 2026- Mar 01 2026" → "Feb 26 - Mar 1"
    """
    try:
        # Remove extra spaces
        date_string = re.sub(r'\s+', ' ', date_string.strip())
        
        # Handle range formats: "Feb 06 - 08 2026" or "Feb 26 2026- Mar 01 2026"
        if ' - ' in date_string or '- ' in date_string:
            # Clean up the dash spacing
            date_string = date_string.replace('- ', ' - ').replace(' -', ' - ')
            parts = date_string.split(' - ')
            
            if len(parts) == 2:
                start = parts[0].strip()
                end = parts[1].strip()
                
                # Parse start date
                start_match = re.match(r'([A-Za-z]+)\s+(\d+)', start)
                if start_match:
                    start_month = start_match.group(1)
                    start_day = int(start_match.group(2))
                    
                    # Parse end date
                    # Case 1: "08 2026" (same month)
                    if re.match(r'^\d+', end):
                        end_day = int(re.match(r'^\d+', end).group())
                        return f"{start_month} {start_day}-{end_day}"
                    
                    # Case 2: "Mar 01 2026" (different month)
                    end_match = re.match(r'([A-Za-z]+)\s+(\d+)', end)
                    if end_match:
                        end_month = end_match.group(1)
                        end_day = int(end_match.group(2))
                        return f"{start_month} {start_day} - {end_month} {end_day}"
        
        # Handle single date: "Feb 5, 2026" or "Feb 07 2026"
        single_match = re.match(r'([A-Za-z]+)\s+(\d+)', date_string)
        if single_match:
            month = single_match.group(1)
            day = int(single_match.group(2))  # Remove leading zeros
            return f"{month} {day}"
        
        # Fallback: return as-is but cleaned
        return date_string.replace(', 2026', '').replace(' 2026', '')
    
    except Exception as e:
        print(f"   ! Date format error for '{date_string}': {e}")
        return date_string

def get_date_category(event_date):
    """
    Categorize event into time buckets for smart filtering.
    Returns: 'today', 'tomorrow', 'this_week', 'next_week', 'this_month', 'later'
    """
    if not event_date:
        return 'later'
    
    now = datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)
    week_end = today + timedelta(days=7)
    next_week_end = today + timedelta(days=14)
    month_end = today.replace(day=1) + timedelta(days=32)
    month_end = month_end.replace(day=1) - timedelta(days=1)
    
    if event_date.date() == today.date():
        return 'today'
    elif event_date.date() == tomorrow.date():
        return 'tomorrow'
    elif event_date < week_end:
        return 'this_week'
    elif event_date < next_week_end:
        return 'next_week'
    elif event_date <= month_end:
        return 'this_month'
    else:
        return 'later'

def get_smart_label(event_date):
    """
    Generate human-friendly labels like "Tonight", "Tomorrow", etc.
    """
    if not event_date:
        return ""
    
    now = datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)
    week_end = today + timedelta(days=7)
    
    if event_date.date() == today.date():
        return "Today"
    elif event_date.date() == tomorrow.date():
        return "Tomorrow"
    elif event_date < week_end:
        return "This Week"
    else:
        return ""

def transform_events(input_file='all_events.json', output_file='events_formatted.json'):
    """
    Transform scraped events with enhanced date parsing and categorization.
    """
    
    print(f">> Reading {input_file}...")
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            scraped_data = json.load(f)
    except FileNotFoundError:
        print(f"X Error: {input_file} not found!")
        print("   Make sure you've run the scrapers and merge_data.py first.")
        return
    
    print(f">> Transforming {len(scraped_data)} events with smart date parsing...")
    
    transformed_events = []
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    for event in scraped_data:
        try:
            raw_date = event.get("raw_date_string", "TBA")
            
            # Parse date into datetime object
            event_datetime = parse_date_advanced(raw_date)
            
            # Skip past events
            if event_datetime and event_datetime < today:
                print(f"   Skipping past event: {event.get('title', 'unknown')}")
                continue
            
            # Format display date
            display_date = format_date_display(raw_date)
            
            # Get smart label
            smart_label = get_smart_label(event_datetime) if event_datetime else ""
            
            # Get category
            date_category = get_date_category(event_datetime) if event_datetime else 'later'
            
            # Transform to expected format
            transformed = {
                "title": event.get("title", "Untitled Event"),
                "date": display_date,
                "date_label": smart_label,  # NEW: "Today", "Tomorrow", etc.
                "date_category": date_category,  # NEW: For filtering
                "type": event.get("attributes", {}).get("category", "Event"),
                "loc": event.get("venue_info", {}).get("name", "Unknown Venue"),
                "img": event.get("media", {}).get("image", "https://placehold.co/400x300?text=No+Image"),
                "link": event.get("action_link", "")
            }
            
            # Add sort date for later sorting
            if event_datetime:
                transformed["_sort_date"] = event_datetime.timestamp()
            else:
                transformed["_sort_date"] = 9999999999  # Far future
            
            transformed_events.append(transformed)
            
        except Exception as e:
            print(f"   ! Skipped event '{event.get('title', 'unknown')}': {e}")
    
    # Sort by date (earliest first)
    transformed_events.sort(key=lambda x: x["_sort_date"])
    
    # Remove the temporary sort field
    for event in transformed_events:
        del event["_sort_date"]
    
    # Save transformed data
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(transformed_events, f, indent=2, ensure_ascii=False)
    
    print(f">> SUCCESS! Transformed {len(transformed_events)} upcoming events")
    print(f">> Saved to: {output_file}")
    print(f"\n>> Sample output:")
    if transformed_events:
        sample = transformed_events[0]
        print(f"   Title: {sample['title']}")
        print(f"   Date: {sample['date']}")
        print(f"   Label: {sample['date_label']}")
        print(f"   Category: {sample['date_category']}")
    
    return transformed_events

if __name__ == "__main__":
    transform_events()

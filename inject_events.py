import json
import re

def inject_events_into_html(
    events_file='events_formatted.json',
    dining_file='dining_curated.json',
    outings_file='outings_curated.json',
    plans_file='curated_plans.json',
    input_html='phoenixville.html',
    output_html='phoenixville_updated.html'
):
    """
    Replace the hardcoded eventsData, diningData, outingsData, and plansData arrays in phoenixville.html
    """
    
    print(f">> Reading events from {events_file}...")
    with open(events_file, 'r', encoding='utf-8') as f:
        events = json.load(f)
    
    print(f">> Reading dining from {dining_file}...")
    try:
        with open(dining_file, 'r', encoding='utf-8') as f:
            dining = json.load(f)
    except FileNotFoundError:
        print(f"   ! Warning: {dining_file} not found, skipping dining data")
        dining = None
    
    print(f">> Reading outings from {outings_file}...")
    try:
        with open(outings_file, 'r', encoding='utf-8') as f:
            outings = json.load(f)
    except FileNotFoundError:
        print(f"   ! Warning: {outings_file} not found, skipping outings data")
        outings = None
    
    print(f">> Reading curated plans from {plans_file}...")
    try:
        with open(plans_file, 'r', encoding='utf-8') as f:
            plans = json.load(f)
    except FileNotFoundError:
        print(f"   ! Warning: {plans_file} not found, skipping plans data")
        plans = None
    
    print(f">> Reading HTML template from {input_html}...")
    with open(input_html, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Convert events to JavaScript format (ensure_ascii=False to avoid unicode escapes)
    events_js = json.dumps(events, indent=12, ensure_ascii=False)  # 12 spaces for proper indentation
    
    # Find and replace the eventsData array
    # Pattern: const eventsData = [...];
    pattern = r'const eventsData = \[[\s\S]*?\];'
    
    replacement = f'const eventsData = {events_js};'
    
    # Check if pattern exists
    if not re.search(pattern, html_content):
        print("X Error: Could not find 'const eventsData = [...]' in HTML file")
        print("   Make sure the HTML file has the expected format")
        return False
    
    # Perform replacement
    html_content = re.sub(pattern, replacement, html_content, count=1)
    
    # Replace dining data if available
    if dining:
        dining_js = json.dumps(dining, indent=12, ensure_ascii=False)
        dining_pattern = r'const diningData = \[[\s\S]*?\];'
        dining_replacement = f'const diningData = {dining_js};'
        
        if re.search(dining_pattern, html_content):
            html_content = re.sub(dining_pattern, dining_replacement, html_content, count=1)
            print(f"   Injected {len(dining)} dining spots")
        else:
            print("   ! Warning: Could not find 'const diningData' in HTML")
    
    # Replace outings data if available
    if outings:
        outings_js = json.dumps(outings, indent=12, ensure_ascii=False)
        outings_pattern = r'const outingsData = \[[\s\S]*?\];'
        outings_replacement = f'const outingsData = {outings_js};'
        
        if re.search(outings_pattern, html_content):
            html_content = re.sub(outings_pattern, outings_replacement, html_content, count=1)
            print(f"   Injected {len(outings)} outings")
        else:
            print("   ! Warning: Could not find 'const outingsData' in HTML")
    
    # Replace curated plans data if available
    if plans:
        plans_js = json.dumps(plans, indent=12, ensure_ascii=False)
        plans_pattern = r'const plansData = \[[\s\S]*?\];'
        plans_replacement = f'const plansData = {plans_js};'
        
        if re.search(plans_pattern, html_content):
            html_content = re.sub(plans_pattern, plans_replacement, html_content, count=1)
            print(f"   Injected {len(plans)} curated plans")
        else:
            print("   ! Warning: Could not find 'const plansData' in HTML")
    
    # Write updated HTML
    with open(output_html, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f">> SUCCESS!")
    print(f"   Injected {len(events)} events into {output_html}")
    if dining:
        print(f"   Injected {len(dining)} dining spots into {output_html}")
    if outings:
        print(f"   Injected {len(outings)} outings into {output_html}")
    if plans:
        print(f"   Injected {len(plans)} curated plans into {output_html}")
    print(f"   File is ready to use!")
    
    return True

if __name__ == "__main__":
    inject_events_into_html()

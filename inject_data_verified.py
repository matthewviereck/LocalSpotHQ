import json
import re

def inject_all_data():
    """
    Inject events, dining, outings, and curated plans into phoenixville.html
    with detailed verification
    """
    
    print("="*60)
    print("INJECTING DATA INTO HTML")
    print("="*60)
    
    # 1. Load all JSON data
    print("\n1. LOADING JSON DATA...")
    print("-"*60)
    
    with open('events_formatted.json', 'r', encoding='utf-8') as f:
        events = json.load(f)
    print(f">> Loaded {len(events)} events")
    
    with open('dining_curated.json', 'r', encoding='utf-8') as f:
        dining = json.load(f)
    print(f">> Loaded {len(dining)} dining spots")
    
    with open('outings_curated.json', 'r', encoding='utf-8') as f:
        outings = json.load(f)
    print(f">> Loaded {len(outings)} outings")
    
    with open('curated_plans.json', 'r', encoding='utf-8') as f:
        plans = json.load(f)
    print(f">> Loaded {len(plans)} curated plans")
    
    # 2. Load HTML template
    print("\n2. LOADING HTML TEMPLATE...")
    print("-"*60)
    
    with open('phoenixville.html', 'r', encoding='utf-8') as f:
        html = f.read()
    print(f">> Loaded HTML template ({len(html)} characters)")
    
    # 3. Convert to JavaScript format
    print("\n3. CONVERTING TO JAVASCRIPT...")
    print("-"*60)
    
    events_js = json.dumps(events, indent=12, ensure_ascii=False)
    dining_js = json.dumps(dining, indent=12, ensure_ascii=False)
    outings_js = json.dumps(outings, indent=12, ensure_ascii=False)
    plans_js = json.dumps(plans, indent=12, ensure_ascii=False)
    
    print(f">> Converted all data to JavaScript format")
    
    # 4. Inject events
    print("\n4. INJECTING EVENTS DATA...")
    print("-"*60)
    
    pattern = r'const eventsData = \[[\s\S]*?\];'
    replacement = f'const eventsData = {events_js};'
    
    if re.search(pattern, html):
        html = re.sub(pattern, replacement, html, count=1)
        print(f">> SUCCESS: Injected {len(events)} events")
    else:
        print(">> ERROR: Could not find eventsData pattern!")
        return False
    
    # 5. Inject dining
    print("\n5. INJECTING DINING DATA...")
    print("-"*60)
    
    pattern = r'const diningData = \[[\s\S]*?\];'
    replacement = f'const diningData = {dining_js};'
    
    if re.search(pattern, html):
        html = re.sub(pattern, replacement, html, count=1)
        print(f">> SUCCESS: Injected {len(dining)} dining spots")
    else:
        print(">> ERROR: Could not find diningData pattern!")
        return False
    
    # 6. Inject outings
    print("\n6. INJECTING OUTINGS DATA...")
    print("-"*60)
    
    pattern = r'const outingsData = \[[\s\S]*?\];'
    replacement = f'const outingsData = {outings_js};'
    
    if re.search(pattern, html):
        html = re.sub(pattern, replacement, html, count=1)
        print(f">> SUCCESS: Injected {len(outings)} outings")
    else:
        print(">> ERROR: Could not find outingsData pattern!")
        return False
    
    # 7. Inject curated plans
    print("\n7. INJECTING CURATED PLANS DATA...")
    print("-"*60)
    
    pattern = r'const plansData = \[[\s\S]*?\];'
    replacement = f'const plansData = {plans_js};'
    
    if re.search(pattern, html):
        html = re.sub(pattern, replacement, html, count=1)
        print(f">> SUCCESS: Injected {len(plans)} curated plans")
    else:
        print(">> WARNING: Could not find plansData pattern")
    
    # 8. Save
    print("\n8. SAVING UPDATED HTML...")
    print("-"*60)
    
    with open('phoenixville_updated.html', 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f">> Saved to phoenixville_updated.html ({len(html)} characters)")
    
    # 9. Verify
    print("\n9. VERIFICATION...")
    print("-"*60)
    
    with open('phoenixville_updated.html', 'r', encoding='utf-8') as f:
        verify_html = f.read()
    
    verified = True
    if len(events) > 0:
        first_event_title = events[0]['title']
        if first_event_title in verify_html:
            print(f">> Events data verified (found '{first_event_title}')")
        else:
            print(f">> ERROR: Events data NOT found!")
            verified = False
    
    if len(dining) > 0:
        first_dining_title = dining[0]['title']
        if first_dining_title in verify_html:
            print(f">> Dining data verified (found '{first_dining_title}')")
        else:
            print(f">> ERROR: Dining data NOT found!")
            verified = False
    
    if len(plans) > 0:
        first_plan_title = plans[0]['title']
        if first_plan_title in verify_html:
            print(f">> Plans data verified (found '{first_plan_title}')")
        else:
            print(f">> ERROR: Plans data NOT found!")
            verified = False
    
    print("\n" + "="*60)
    if verified:
        print("SUCCESS! All data injected into phoenixville_updated.html")
    else:
        print("WARNING: Some data may not have been injected correctly")
    print("="*60)
    print("\nNext step:")
    print("  Run: py fix_app_landing_v2.py")
    
    return verified

if __name__ == "__main__":
    try:
        inject_all_data()
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()

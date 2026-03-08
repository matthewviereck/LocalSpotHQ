import os
import json

def diagnose_pipeline():
    """
    Check if all required files exist and have data
    """
    
    print("="*60)
    print("LOCALSPOT PIPELINE DIAGNOSTIC")
    print("="*60)
    
    # Files that should exist after running update_localspot.py
    required_files = {
        'recurring_events.json': 'Recurring events (Farmers Market, First Friday, etc.)',
        'colonial_events.json': 'Colonial Theatre events',
        'oaks_events.json': 'Expo Center events',
        'all_events.json': 'Merged events',
        'events_formatted.json': 'Formatted events with dates',
        'dining_curated.json': 'Dining spots',
        'outings_curated.json': 'Activities/outings',
        'curated_plans.json': 'Day plans',
        'phoenixville.html': 'Template HTML',
        'phoenixville_updated.html': 'Generated HTML with data'
    }
    
    print("\n1. CHECKING FILES...")
    print("-" * 60)
    
    missing_files = []
    empty_files = []
    
    for filename, description in required_files.items():
        if os.path.exists(filename):
            size = os.path.getsize(filename)
            if size > 0:
                print(f"✓ {filename:<30} {size:>10} bytes - {description}")
                
                # Check if JSON files have data
                if filename.endswith('.json'):
                    try:
                        with open(filename, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if isinstance(data, list):
                                item_count = len(data)
                                if item_count == 0:
                                    print(f"  ⚠️  WARNING: {filename} has 0 items!")
                                    empty_files.append(filename)
                                else:
                                    print(f"  → Contains {item_count} items")
                    except Exception as e:
                        print(f"  ✗ ERROR reading {filename}: {e}")
            else:
                print(f"✗ {filename:<30} EMPTY FILE!")
                empty_files.append(filename)
        else:
            print(f"✗ {filename:<30} NOT FOUND!")
            missing_files.append(filename)
    
    print("\n2. SUMMARY")
    print("-" * 60)
    
    if not missing_files and not empty_files:
        print("✓ All files present and have data!")
        print("\nYour pipeline is working correctly.")
        print("If app.html still shows no data, the issue is with:")
        print("  - The inject script not running")
        print("  - Or phoenixville_updated.html not being created")
    else:
        if missing_files:
            print(f"\n✗ MISSING FILES ({len(missing_files)}):")
            for f in missing_files:
                print(f"  - {f}")
            print("\nThese files should be created by update_localspot.py")
            print("Run: py update_localspot.py")
        
        if empty_files:
            print(f"\n⚠️  EMPTY FILES ({len(empty_files)}):")
            for f in empty_files:
                print(f"  - {f}")
            print("\nThese files exist but have no data.")
    
    print("\n3. RECOMMENDED ACTIONS")
    print("-" * 60)
    
    if missing_files or empty_files:
        print("Run these commands in order:")
        print("  1. py generate_recurring_events.py")
        print("  2. py scrape_colonial_v2.py")
        print("  3. py scape_oaks.py")
        print("  4. py merge_data.py")
        print("  5. py transform_events.py")
        print("  6. py create_dining_list.py")
        print("  7. py create_outings_list.py")
        print("  8. py create_curated_plans.py")
        print("  9. py inject_events.py")
        print("\nOR just run: py update_localspot.py (runs all 9)")
    else:
        print("Everything looks good!")
        print("Next steps:")
        print("  1. Run: py fix_app_landing_v2.py")
        print("  2. Upload app.html to Hostinger")
    
    print("\n" + "="*60)
    print("DIAGNOSTIC COMPLETE")
    print("="*60)

if __name__ == "__main__":
    diagnose_pipeline()

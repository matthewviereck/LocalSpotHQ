#!/usr/bin/env python3
"""
LocalSpot Data Pipeline
=======================
This script automates the entire data pipeline:
1. Scrapes events from Colonial Theatre & Philly Expo Center
2. Merges the data
3. Transforms it into the correct format
4. Injects it into phoenixville.html

Usage:
    python update_localspot.py

The script will create:
- colonial_events.json (raw scraped data)
- oaks_events.json (raw scraped data)
- all_events.json (merged raw data)
- events_formatted.json (transformed for website)
- phoenixville_updated.html (ready to deploy!)
"""

import subprocess
import os
import sys

def run_script(script_name, description):
    """Run a Python script and handle errors"""
    print(f"\n{'='*60}")
    print(f">> STEP: {description}")
    print(f"{'='*60}")
    
    if not os.path.exists(script_name):
        print(f"X Error: {script_name} not found!")
        return False
    
    try:
        result = subprocess.run(
            ['python', script_name],
            capture_output=True,
            text=True,
            check=True
        )
        print(result.stdout)
        if result.stderr:
            print("! Warnings:", result.stderr)
        return True
    except subprocess.CalledProcessError as e:
        print(f"X Error running {script_name}:")
        print(e.stdout)
        print(e.stderr)
        return False

def main():
    print("""
    ============================================================
                                                           
                LocalSpot Data Pipeline                    
             Automated Event Aggregation System             
                                                           
    ============================================================
    """)
    
    scripts = [
        ('generate_recurring_events.py', '1. Generating Recurring Events (Farmers Market, First Fridays, etc.)'),
        ('scrape_colonial_v2.py', '2. Scraping Colonial Theatre Events'),
        ('scape_oaks.py', '3. Scraping Philly Expo Center Events'),
        ('merge_data.py', '4. Merging All Event Data'),
        ('transform_events.py', '5. Transforming Data Format'),
        ('create_dining_list.py', '6. Creating Curated Dining List'),
        ('create_outings_list.py', '7. Creating Curated Outings List'),
        ('create_curated_plans.py', '8. Creating Curated Day Plans'),
        ('inject_events.py', '9. Injecting All Data into Website')
    ]
    
    success_count = 0
    
    for script, description in scripts:
        if run_script(script, description):
            success_count += 1
        else:
            print(f"\nX Pipeline stopped at: {description}")
            print(f"   Please fix {script} and try again.")
            sys.exit(1)
    
    print(f"\n{'='*60}")
    print(f">> SUCCESS! All {success_count}/{len(scripts)} steps completed!")
    print(f"{'='*60}")
    print("\n>> Generated Files:")
    print("   * recurring_events.json")
    print("   * colonial_events.json")
    print("   * oaks_events.json")
    print("   * all_events.json")
    print("   * events_formatted.json")
    print("   * dining_curated.json")
    print("   * outings_curated.json")
    print("   * curated_plans.json")
    print("   * phoenixville_updated.html ** (READY TO DEPLOY)")
    
    print("\n>> Next Steps:")
    print("   1. Open phoenixville_updated.html in a browser to test")
    print("   2. If it looks good, rename it to phoenixville.html")
    print("   3. Upload to your web host!")
    
    print("\n>> Pro Tip:")
    print("   Run this script weekly to keep your events up-to-date!")
    print("   You can automate it with a cron job or GitHub Actions.\n")

if __name__ == "__main__":
    main()

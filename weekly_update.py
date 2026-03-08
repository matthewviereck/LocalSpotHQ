"""
WEEKLY UPDATE SCRIPT FOR LOCALSPOT
Run this once per week to refresh all events and generate app.html
"""

import subprocess
import os

def run_command(command, description):
    """Run a command and show progress"""
    print(f"\n{'='*60}")
    print(f"STEP: {description}")
    print('='*60)
    
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"✓ SUCCESS: {description}")
        if result.stdout:
            print(result.stdout)
    else:
        print(f"✗ ERROR: {description}")
        if result.stderr:
            print(result.stderr)
        return False
    
    return True

def weekly_update():
    """
    Complete weekly update process:
    1. Scrape fresh events
    2. Generate all data
    3. Inject into HTML
    4. Remove landing page
    5. Ready to upload!
    """
    
    print("\n" + "="*60)
    print("LOCALSPOT WEEKLY UPDATE")
    print("="*60)
    print("\nThis will:")
    print("  1. Scrape Colonial Theatre events")
    print("  2. Scrape Expo Center events")
    print("  3. Merge all events")
    print("  4. Format dates")
    print("  5. Inject all data into HTML")
    print("  6. Remove landing page")
    print("  7. Generate app.html ready to upload")
    print("\n" + "="*60)
    
    input("\nPress ENTER to start or Ctrl+C to cancel...")
    
    # List of commands to run in order
    steps = [
        ("py generate_recurring_events.py", "Generate recurring events"),
        ("py scrape_colonial_v2.py", "Scrape Colonial Theatre"),
        ("py scape_oaks.py", "Scrape Expo Center"),
        ("py merge_data.py", "Merge all events"),
        ("py transform_events.py", "Format event dates"),
        ("py create_dining_list.py", "Generate dining data"),
        ("py create_outings_list.py", "Generate activities"),
        ("py create_curated_plans.py", "Generate curated plans"),
        ("py inject_data_verified.py", "Inject data into HTML"),
        ("py fix_app_landing_v2.py", "Remove landing page"),
    ]
    
    success_count = 0
    
    for command, description in steps:
        if run_command(command, description):
            success_count += 1
        else:
            print(f"\n✗ Failed at: {description}")
            print("Fix the error above and try again.")
            return False
    
    # Final summary
    print("\n" + "="*60)
    print("✓ WEEKLY UPDATE COMPLETE!")
    print("="*60)
    print(f"\nCompleted {success_count}/{len(steps)} steps successfully")
    print("\n📤 NEXT STEP:")
    print("   Upload 'app.html' to Hostinger")
    print("   Location: public_html/app.html")
    print("\n✨ Your site will have fresh events!")
    print("="*60)
    
    return True

if __name__ == "__main__":
    try:
        weekly_update()
    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()

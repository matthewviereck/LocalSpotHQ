import json
import os

# --- FILES TO MERGE ---
files_to_merge = [
    "colonial_events.json",
    "oaks_events.json",
    "recurring_events.json"  # NEW: Add recurring local events
]

output_file = "all_events.json"
master_list = []

print(">> Merging data files...")

for filename in files_to_merge:
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"   OK Loaded {len(data)} events from {filename}")
                master_list.extend(data) # Add these events to the master list
        except Exception as e:
            print(f"   ! Error reading {filename}: {e}")
    else:
        print(f"   X File not found: {filename} (Did you run the scraper?)")

# --- SORTING (OPTIONAL) ---
# It's nice to sort them by date so they appear in order on your site
# This is a basic string sort, which works okay for "YYYY-MM-DD" but might be rough for "Feb 12"
# We will leave it as-is for now to avoid breaking complex date formats.

# --- SAVE ---
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(master_list, f, indent=2, ensure_ascii=False)

print(f"\n>> SUCCESS! Merged {len(master_list)} total events into '{output_file}'")
print(f">> Next Step: Transform and inject into HTML")

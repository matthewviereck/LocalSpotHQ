import json
import os


def merge_events(source_files, output_file):
    """Merge multiple event JSON files into one combined file."""
    master_list = []

    print(">> Merging data files...")

    for filepath in source_files:
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    print(f"   OK Loaded {len(data)} events from {os.path.basename(filepath)}")
                    master_list.extend(data)
            except Exception as e:
                print(f"   ! Error reading {filepath}: {e}")
        else:
            print(f"   X File not found: {filepath}")

    os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(master_list, f, indent=2, ensure_ascii=False)

    print(f"\n>> SUCCESS! Merged {len(master_list)} total events into {output_file}")
    return master_list


if __name__ == "__main__":
    # Standalone usage for backward compatibility
    merge_events(
        source_files=[
            "colonial_events.json",
            "oaks_events.json",
            "recurring_events.json"
        ],
        output_file="all_events.json"
    )

import json
import os
import re

from pipeline.geo import route_area_events


def _dedupe_key(event):
    """Same event from two sources: match on normalized title + raw date."""
    title = re.sub(r'[^a-z0-9]', '', str(event.get('title', '')).lower())
    date = re.sub(r'[^a-z0-9]', '', str(event.get('raw_date_string', '')).lower())
    return f"{title}|{date}"


def _richness(event):
    """
    Rank duplicates: prefer the copy carrying a start time, then a price,
    then a real image, then a link. Time and price lead because they're the
    fields a reader actually decides on and the sparsest across sources.
    """
    attrs = event.get('attributes') or {}
    img = (event.get('media') or {}).get('image') or ''
    has_img = bool(img) and 'placehold.co' not in img
    has_time = bool(attrs.get('time')) or bool(
        re.search(r'\d{1,2}(:\d{2})?\s*[ap]\.?m\.?',
                  str(event.get('raw_date_string', '')), re.IGNORECASE))
    # Series identity first — see transform._richness for why losing it hurts.
    return (bool(attrs.get('series')), has_time, bool(attrs.get('price')),
            has_img, bool(event.get('action_link')))


def dedupe_events(events):
    best = {}
    order = []
    for event in events:
        key = _dedupe_key(event)
        if key not in best:
            best[key] = event
            order.append(key)
        elif _richness(event) > _richness(best[key]):
            best[key] = event
    return [best[k] for k in order]


def merge_events(source_files, output_file, area_config=None):
    """
    Merge multiple event JSON files into one combined file.

    With an area_config that defines a `towns` roster, each event is tagged
    with its nearest town and anything outside the roster is dropped, so an
    area's feed matches the towns it claims in its tagline.
    """
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

    before = len(master_list)
    master_list = dedupe_events(master_list)
    if len(master_list) < before:
        print(f"   Removed {before - len(master_list)} duplicate events")

    if area_config:
        master_list = route_area_events(master_list, area_config)

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

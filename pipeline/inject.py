import json
import re
import os
from datetime import datetime, timezone


def _build_structured_data(area_config, events):
    """Build JSON-LD: a WebPage and a list of upcoming Events.

    Returns a string of one or more <script type="application/ld+json"> blocks,
    safe to drop directly into the HTML <head>.
    """
    meta = (area_config or {}).get('meta', {}) if area_config else {}
    area_name = (area_config or {}).get('name', '') if area_config else ''
    canonical_url = meta.get('canonical_url', '')

    web_page = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": meta.get('title', ''),
        "description": meta.get('description', ''),
        "url": canonical_url,
        "isPartOf": {
            "@type": "WebSite",
            "name": "LocalSpot HQ",
            "url": "https://www.localspothq.com"
        },
        "about": {
            "@type": "Place",
            "name": area_name,
            "address": {
                "@type": "PostalAddress",
                "addressRegion": "PA",
                "addressCountry": "US"
            }
        }
    }

    event_items = []
    for ev in (events or []):
        if not isinstance(ev, dict):
            continue
        title = ev.get('title') or ev.get('name')
        # transform.py outputs `_sort_date` as a Unix timestamp; fall back to ISO fields
        # for forward-compatibility if the upstream schema gains one.
        start_iso = ev.get('start_iso') or ev.get('date_iso')
        if not start_iso and ev.get('_sort_date'):
            try:
                ts = float(ev['_sort_date'])
                # The sentinel value 9999999999 means "no parseable date" — skip those
                if ts < 9_000_000_000:
                    start_iso = datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()
            except (TypeError, ValueError):
                pass
        if not title or not start_iso:
            continue
        item = {
            "@context": "https://schema.org",
            "@type": "Event",
            "name": title,
            "startDate": start_iso,
            "eventStatus": "https://schema.org/EventScheduled",
            "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
        }
        if ev.get('end_iso'):
            item["endDate"] = ev["end_iso"]
        if ev.get('img'):
            item["image"] = ev["img"]
        if ev.get('link'):
            item["url"] = ev["link"]
        location_name = ev.get('loc') or ev.get('venue')
        if location_name:
            item["location"] = {
                "@type": "Place",
                "name": location_name,
                "address": {
                    "@type": "PostalAddress",
                    "addressLocality": area_name or location_name,
                    "addressRegion": "PA",
                    "addressCountry": "US"
                }
            }
        event_items.append(item)

    blocks = [f'<script type="application/ld+json">\n{json.dumps(web_page, indent=4)}\n</script>']
    if event_items:
        blocks.append(
            f'<script type="application/ld+json">\n{json.dumps(event_items, indent=4)}\n</script>'
        )
    return "\n    ".join(blocks)


def inject_all_data(events_file, dining_file, outings_file, plans_file,
                    template_file, output_file, area_config=None):
    """
    Inject events, dining, outings, and curated plans data into HTML template.
    Optionally substitutes area-specific placeholders from area_config.
    """
    print("=" * 60)
    print("INJECTING DATA INTO HTML")
    print("=" * 60)

    # 1. Load all JSON data
    print("\n1. Loading JSON data...")
    events = _load_json(events_file, "events")
    dining = _load_json(dining_file, "dining spots")
    outings = _load_json(outings_file, "outings")
    plans = _load_json(plans_file, "curated plans")

    # 2. Load HTML template
    print("\n2. Loading HTML template...")
    with open(template_file, 'r', encoding='utf-8') as f:
        html = f.read()
    print(f"   Loaded template ({len(html)} characters)")

    # 3. Substitute area placeholders if config provided
    if area_config:
        print("\n3. Substituting area placeholders...")
        meta = area_config.get('meta', {})
        build_timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        structured_data = _build_structured_data(area_config, events)
        replacements = {
            '{{AREA_NAME}}': area_config.get('name', ''),
            '{{AREA_TAGLINE}}': area_config.get('tagline', ''),
            '{{META_TITLE}}': meta.get('title', ''),
            '{{META_DESCRIPTION}}': meta.get('description', ''),
            '{{META_KEYWORDS}}': meta.get('keywords', ''),
            '{{OG_IMAGE}}': meta.get('og_image', ''),
            '{{CANONICAL_URL}}': meta.get('canonical_url', ''),
            '{{BUILD_TIMESTAMP}}': build_timestamp,
            '{{STRUCTURED_DATA}}': structured_data,
        }
        for placeholder, value in replacements.items():
            if placeholder in html:
                html = html.replace(placeholder, value)
                print(f"   Replaced {placeholder}")
        # Warn for any leftover placeholders (catches typos and missing config keys)
        leftover = re.findall(r'\{\{[A-Z_]+\}\}', html)
        if leftover:
            print(f"   WARNING: unsubstituted placeholders remain: {sorted(set(leftover))}")

    # 4. Convert to JS and inject
    data_injections = [
        ('eventsData', events, 'events'),
        ('diningData', dining, 'dining spots'),
        ('outingsData', outings, 'outings'),
        ('plansData', plans, 'curated plans'),
    ]

    step = 4
    for var_name, data, label in data_injections:
        print(f"\n{step}. Injecting {label}...")
        pattern = rf'const {var_name} = \[[\s\S]*?\];'
        data_js = json.dumps(data, indent=12, ensure_ascii=False)
        replacement = f'const {var_name} = {data_js};'

        if re.search(pattern, html):
            html = re.sub(pattern, replacement, html, count=1)
            print(f"   SUCCESS: Injected {len(data)} {label}")
        else:
            print(f"   WARNING: Could not find {var_name} pattern!")
        step += 1

    # 5. Save
    print(f"\n{step}. Saving...")
    os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"   Saved to {output_file} ({len(html)} characters)")

    # 6. Verify
    _verify(output_file, events, dining, plans)

    return True


def _load_json(filepath, label):
    """Load a JSON file and print count."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"   Loaded {len(data)} {label} from {os.path.basename(filepath)}")
        return data
    except FileNotFoundError:
        print(f"   WARNING: {filepath} not found, using empty list")
        return []


def _verify(output_file, events, dining, plans):
    """Quick verification that data was injected."""
    print("\nVerification...")
    with open(output_file, 'r', encoding='utf-8') as f:
        html = f.read()

    checks = [
        (events, "Events"),
        (dining, "Dining"),
        (plans, "Plans"),
    ]
    all_ok = True
    for data, label in checks:
        if data and data[0].get('title'):
            if data[0]['title'] in html:
                print(f"   {label} verified (found '{data[0]['title']}')")
            else:
                print(f"   WARNING: {label} data may not have been injected!")
                all_ok = False

    if all_ok:
        print("\nSUCCESS! All data injected.")
    else:
        print("\nWARNING: Some data may not have been injected correctly.")


if __name__ == "__main__":
    inject_all_data(
        events_file='events_formatted.json',
        dining_file='dining_curated.json',
        outings_file='outings_curated.json',
        plans_file='curated_plans.json',
        template_file='phoenixville.html',
        output_file='phoenixville_updated.html'
    )

import json
import re
import os


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
        replacements = {
            '{{AREA_NAME}}': area_config.get('name', ''),
            '{{AREA_TAGLINE}}': area_config.get('tagline', ''),
            '{{META_TITLE}}': meta.get('title', ''),
            '{{META_DESCRIPTION}}': meta.get('description', ''),
            '{{META_KEYWORDS}}': meta.get('keywords', ''),
            '{{OG_IMAGE}}': meta.get('og_image', ''),
            '{{CANONICAL_URL}}': meta.get('canonical_url', ''),
        }
        for placeholder, value in replacements.items():
            if placeholder in html:
                html = html.replace(placeholder, value)
                print(f"   Replaced {placeholder}")

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

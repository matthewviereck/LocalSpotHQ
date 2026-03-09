"""
LocalSpot Pipeline Runner

Usage:
    python pipeline/run.py --area phoenixville     # Run for one area
    python pipeline/run.py --all                   # Run for all enabled areas
"""

import argparse
import json
import importlib
import os
import sys

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from pipeline.recurring import generate_recurring_events
from pipeline.merge import merge_events
from pipeline.transform import transform_events
from pipeline.inject import inject_all_data
from pipeline.postprocess import remove_landing_page


def load_area_config(area_id):
    """Load the config file for a specific area."""
    config_path = os.path.join(PROJECT_ROOT, 'config', f'{area_id}.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_areas_registry():
    """Load the master areas registry."""
    registry_path = os.path.join(PROJECT_ROOT, 'config', 'areas.json')
    with open(registry_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def run_area(area_id):
    """Run the full pipeline for a single area."""
    print(f"\n{'='*60}")
    print(f"LOCALSPOT PIPELINE: {area_id.upper()}")
    print(f"{'='*60}")

    config = load_area_config(area_id)
    data_dir = os.path.join(PROJECT_ROOT, 'data', area_id)
    output_dir = os.path.join(PROJECT_ROOT, 'output', area_id)

    # Ensure directories exist
    os.makedirs(os.path.join(data_dir, 'scraped'), exist_ok=True)
    os.makedirs(os.path.join(data_dir, 'generated'), exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    # Step 1: Generate recurring events
    rec_cfg = config.get('recurring_events')
    if rec_cfg:
        print(f"\n--- Step 1: Generate recurring events ---")
        config_file = os.path.join(data_dir, rec_cfg['config_file'])
        rec_output = os.path.join(data_dir, rec_cfg['output_file'])
        generate_recurring_events(config_file, rec_output)

    # Step 2: Run scrapers
    print(f"\n--- Step 2: Run scrapers ---")
    for scraper_cfg in config.get('scrapers', []):
        try:
            mod = importlib.import_module(scraper_cfg['module'])
            func = getattr(mod, scraper_cfg['function'])
            output_file = os.path.join(data_dir, scraper_cfg['output_file'])
            func(output_file=output_file)
        except Exception as e:
            print(f"   ! Scraper {scraper_cfg['module']} failed: {e}")
            # Continue — merge will use cached data if available

    # Step 3: Merge all event sources
    print(f"\n--- Step 3: Merge events ---")
    source_files = [os.path.join(data_dir, s) for s in config['merge_sources']]
    merged_output = os.path.join(data_dir, 'generated', 'all_events.json')
    merge_events(source_files, merged_output)

    # Step 4: Transform (date parsing, filtering, categorization)
    print(f"\n--- Step 4: Transform events ---")
    formatted_output = os.path.join(data_dir, 'generated', 'events_formatted.json')
    transform_events(merged_output, formatted_output)

    # Step 5: Inject data into HTML template
    print(f"\n--- Step 5: Inject data into template ---")
    template_path = os.path.join(PROJECT_ROOT, 'templates', 'app_template.html')
    static = config['static_data']
    intermediate_html = os.path.join(output_dir, 'app_intermediate.html')
    inject_all_data(
        events_file=formatted_output,
        dining_file=os.path.join(data_dir, static['dining']),
        outings_file=os.path.join(data_dir, static['outings']),
        plans_file=os.path.join(data_dir, static['plans']),
        template_file=template_path,
        output_file=intermediate_html,
        area_config=config
    )

    # Step 6: Post-process (remove landing page, add autoload)
    print(f"\n--- Step 6: Post-process ---")
    final_output = os.path.join(output_dir, 'index.html')
    remove_landing_page(intermediate_html, final_output)

    # Cleanup intermediate
    if os.path.exists(intermediate_html):
        os.remove(intermediate_html)

    print(f"\n{'='*60}")
    print(f"DONE! Output: {final_output}")
    print(f"{'='*60}")
    print(f"\nNext: Upload to Hostinger at public_html/{config['deploy']['remote_path']}")

    return True


def main():
    parser = argparse.ArgumentParser(description='LocalSpot Pipeline Runner')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--area', type=str, help='Run pipeline for a specific area (e.g., phoenixville)')
    group.add_argument('--all', action='store_true', help='Run pipeline for all enabled areas')
    args = parser.parse_args()

    if args.all:
        registry = load_areas_registry()
        for area in registry['areas']:
            if area.get('enabled', False):
                try:
                    run_area(area['id'])
                except Exception as e:
                    print(f"\n! ERROR processing {area['id']}: {e}")
                    import traceback
                    traceback.print_exc()
    else:
        try:
            run_area(args.area)
        except Exception as e:
            print(f"\n! ERROR: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    main()

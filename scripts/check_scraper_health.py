"""Fail loudly when a venue scraper has gone dark.

Every scraper falls back to its last-good file when a fetch or parse fails
("Using cached ..."). That keeps a bad day from gutting the site, but it also
means a permanently broken scraper is invisible: the build stays green and the
site just quietly stops carrying that venue.

That is exactly what happened to Uptown Knauer — it 403'd from ~2026-03-11 to
2026-08-29 and nothing said so, while West Chester's only scraper contributed
zero live events for five months.

This script checks each *active* scraper (the ones actually listed in an area
config) and reports how many genuinely upcoming events its output file holds.
A scraper with none has either broken or lost its venue, and the run goes red.

Run it AFTER the deploy step: a dark venue should be shouted about, but it
should not stop 190-odd good events from shipping.
"""

import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.transform import parse_date_advanced  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _future_count(path):
    """How many events in this file are dated today or later."""
    if not os.path.exists(path):
        return None, 'MISSING'
    try:
        with open(path, encoding='utf-8-sig') as f:
            events = json.load(f)
    except (ValueError, OSError) as e:
        return None, f'UNREADABLE ({type(e).__name__})'

    today = datetime.now().date()
    future = 0
    for event in events:
        parsed = parse_date_advanced(event.get('raw_date_string', ''))
        if parsed and parsed.date() >= today:
            future += 1
    return future, f'{len(events)} cached'


def main():
    areas_path = os.path.join(REPO, 'config', 'areas.json')
    with open(areas_path, encoding='utf-8') as f:
        areas = json.load(f)

    area_ids = [a['id'] for a in areas['areas'] if a.get('enabled', True)] \
        if isinstance(areas, dict) and 'areas' in areas \
        else [k for k, v in areas.items() if v.get('enabled', True)]

    rows = []
    dark = []
    for area_id in area_ids:
        cfg_path = os.path.join(REPO, 'config', f'{area_id}.json')
        if not os.path.exists(cfg_path):
            continue
        with open(cfg_path, encoding='utf-8') as f:
            cfg = json.load(f)
        # Mirrors pipeline/run.py: data lives at data/<area_id>/
        data_dir = os.path.join(REPO, 'data', area_id)

        for scraper in cfg.get('scrapers', []):
            out = os.path.join(data_dir, scraper['output_file'])
            future, note = _future_count(out)
            name = scraper['module'].replace('scrapers.', '')
            rows.append((area_id, name, future, note))
            if not future:
                dark.append(f'{area_id}/{name}')

    width = max((len(r[1]) for r in rows), default=10)
    lines = ['', 'Scraper health (upcoming events per active scraper):', '']
    for area_id, name, future, note in rows:
        mark = 'OK  ' if future else 'DARK'
        count = '-' if future is None else str(future)
        lines.append(f'  {mark} {area_id:14s} {name:{width}s} {count:>4s} upcoming   ({note})')
    lines.append('')

    report = '\n'.join(lines)
    print(report)

    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary, 'a', encoding='utf-8') as f:
            f.write(f'```{report}```\n')

    if dark:
        print(f'FAIL: {len(dark)} scraper(s) returning nothing upcoming: '
              f'{", ".join(dark)}')
        print('The site still deployed. Fix the scraper or retire it from the '
              'area config so this check reflects reality.')
        return 1

    print(f'All {len(rows)} active scrapers are returning upcoming events.')
    return 0


if __name__ == '__main__':
    sys.exit(main())

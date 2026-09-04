"""One-off: rebuild each area's slug registry from git history.

Before pipeline/slugs.py existed, every slug was a pure function of the title
and nothing recorded which URLs had been published. The committed source
files (discovered_events.json and the tracked scraper outputs) carry that
history: walk every commit, compute the legacy slug of every dated event, and
register it with the commit dates it appeared in. The first real build then
redirects or stubs every old URL instead of leaving it a 404.

Idempotent - merges into an existing registry, never clobbers first_seen.

    python scripts/seed_slug_registry.py            # all enabled areas
    python scripts/seed_slug_registry.py --dry-run  # report only
"""

import argparse
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from pipeline.slugs import REGISTRY_FILE, SlugRegistry, legacy_slug  # noqa: E402
from pipeline.transform import parse_date_advanced  # noqa: E402


def _git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT).decode('utf-8', 'replace')


def _tracked(paths):
    tracked = set(_git('ls-files', '--', *paths).split())
    return [p for p in paths if p.replace(os.sep, '/') in tracked]


def seed_area(area_id, dry_run=False):
    with open(os.path.join(ROOT, 'config', f'{area_id}.json'), encoding='utf-8') as f:
        config = json.load(f)
    data_dir = f"data/{area_id}"  # forward slashes: these are git paths, not OS paths
    sources = _tracked([f"{data_dir}/{s}" for s in config.get('merge_sources', [])])
    registry = SlugRegistry(os.path.join(ROOT, 'data', area_id, REGISTRY_FILE))
    before = len(registry.slugs)

    seen = {}  # slug -> {title, venue, date, first_seen, last_seen}
    for src in sources:
        commits = [c.split() for c in _git('log', '--format=%h %ad', '--date=short', '--', src).splitlines() if c]
        for sha, day in reversed(commits):  # oldest first so first_seen is honest
            try:
                events = json.loads(_git('show', f'{sha}:{src}'))
            except (subprocess.CalledProcessError, json.JSONDecodeError):
                continue
            for ev in events:
                title = ev.get('title', '')
                d = parse_date_advanced(ev.get('raw_date_string', ''))
                slug = legacy_slug(title)
                if not slug or d is None:
                    continue
                rec = seen.setdefault(slug, {'first_seen': day, 'last_seen': day})
                rec['first_seen'] = min(rec['first_seen'], day)
                # Sources are walked one file at a time, so only let a newer
                # sighting overwrite the descriptive fields.
                if day >= rec['last_seen']:
                    rec.update(title=title, venue=(ev.get('venue_info') or {}).get('name', ''),
                               date=d.date().isoformat(), last_seen=day)
        print(f"   {src}: {len(commits)} commits")

    added = 0
    for slug, rec in seen.items():
        existing = registry.slugs.get(slug)
        if existing is None:
            registry.slugs[slug] = dict(rec)
            added += 1
        else:
            existing['first_seen'] = min(existing.get('first_seen', rec['first_seen']), rec['first_seen'])
    print(f">> {area_id}: {len(seen)} historical slugs, {added} new, registry {before} -> {len(registry.slugs)}")
    if not dry_run:
        registry.save()
        print(f"   wrote {registry.path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    with open(os.path.join(ROOT, 'config', 'areas.json'), encoding='utf-8') as f:
        areas = [a['id'] for a in json.load(f)['areas'] if a.get('enabled')]
    for area_id in areas:
        seed_area(area_id, dry_run=args.dry_run)


if __name__ == '__main__':
    main()

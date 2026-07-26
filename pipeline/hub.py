"""
Build the hub page (site root) from web/index.html with live per-area numbers.

The counts and taglines on the hub were hand-written and drifted — it still
advertised "95+ Events" for an area carrying 173. Everything it claims about an
area is derived here from that area's built data, so the hub can't go stale
again.

Run after every area has been built:
    python pipeline/hub.py
"""

import json
import os
import re
import sys
from datetime import date

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from pipeline.geo import derive_tagline


def _load(path, default=None):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default if default is not None else []


def area_stats(area_id):
    """Event/dining/outing counts and derived tagline for one area."""
    data_dir = os.path.join(PROJECT_ROOT, 'data', area_id)
    config = _load(os.path.join(PROJECT_ROOT, 'config', f'{area_id}.json'), {})
    events = _load(os.path.join(data_dir, 'generated', 'events_formatted.json'))
    return {
        'slug': config.get('slug', area_id),
        'name': config.get('name', area_id),
        'events': len(events),
        'dining': len(_load(os.path.join(data_dir, 'dining.json'))),
        'outings': len(_load(os.path.join(data_dir, 'outings.json'))),
        'plans': len(_load(os.path.join(data_dir, 'plans.json'))),
        'tagline': derive_tagline(events, config) or config.get('tagline', ''),
    }


def _replace_card(html, stats):
    """
    Rewrite one area card's tagline and stat pills in place.

    Anchored on the card's own href so the two cards can't be confused, and so
    a layout change fails loudly (card not found) instead of silently editing
    the wrong block.
    """
    anchor = f'href="/{stats["slug"]}/"'
    start = html.find(anchor)
    if start == -1:
        print(f"   ! Hub card for {stats['slug']} not found - left unchanged")
        return html, False

    # The card ends at the closing </a>; confine every edit to that slice.
    end = html.find('</a>', start)
    if end == -1:
        return html, False
    card = html[start:end]

    tagline_html = ' &bull; '.join(stats['tagline'].split(' • '))
    card_new, n_tag = re.subn(
        r'(<p class="text-slate-500 text-sm mb-4">)[^<]*(</p>)',
        lambda m: m.group(1) + tagline_html + m.group(2),
        card, count=1)

    def pill(pattern, value, noun):
        nonlocal card_new
        card_new = re.sub(pattern,
                          lambda m: m.group(1) + f'{value} {noun}' + m.group(2),
                          card_new, count=1)

    pill(r'(<span class="bg-blue-50[^"]*">)[^<]*(</span>)', stats['events'], 'Events')
    pill(r'(<span class="bg-amber-50[^"]*">)[^<]*(</span>)', stats['dining'], 'Restaurants')
    pill(r'(<span class="bg-purple-50[^"]*">)[^<]*(</span>)', stats['outings'], 'Activities')

    if not n_tag:
        print(f"   ! Hub tagline for {stats['slug']} not matched")
    return html[:start] + card_new + html[end:], True


def build_sitemap_index(output_file=None):
    """
    Emit a sitemap index at the site root pointing at each area's sitemap.

    The hand-written root sitemap.xml listed 3 URLs and was last read by Google
    in March, so only 2 pages were ever indexed while ~220 live pages sat in
    per-area sitemaps nothing referenced. An index means the one sitemap
    already registered in Search Console reaches all of them, and stays correct
    as areas and events come and go.
    """
    registry = _load(os.path.join(PROJECT_ROOT, 'config', 'areas.json'), {})
    today = date.today().isoformat()

    entries = []
    for area in registry.get('areas', []):
        if not area.get('enabled'):
            continue
        config = _load(os.path.join(PROJECT_ROOT, 'config', f"{area['id']}.json"), {})
        base = config.get('meta', {}).get('canonical_url', '').rstrip('/')
        if not base:
            continue
        entries.append(f"  <sitemap>\n    <loc>{base}/sitemap.xml</loc>\n"
                       f"    <lastmod>{today}</lastmod>\n  </sitemap>")

    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           + '\n'.join(entries) + '\n</sitemapindex>\n')

    output_file = output_file or os.path.join(PROJECT_ROOT, 'output', 'sitemap.xml')
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(xml)
    print(f">> Sitemap index: {len(entries)} area sitemaps -> {output_file}")
    return output_file


def build_robots(output_file=None):
    """robots.txt naming every sitemap, so crawlers find them without GSC."""
    registry = _load(os.path.join(PROJECT_ROOT, 'config', 'areas.json'), {})
    lines = ['User-agent: *', 'Allow: /', '',
             'Sitemap: https://www.localspothq.com/sitemap.xml']
    for area in registry.get('areas', []):
        if not area.get('enabled'):
            continue
        config = _load(os.path.join(PROJECT_ROOT, 'config', f"{area['id']}.json"), {})
        base = config.get('meta', {}).get('canonical_url', '').rstrip('/')
        if base:
            lines.append(f'Sitemap: {base}/sitemap.xml')

    output_file = output_file or os.path.join(PROJECT_ROOT, 'output', 'robots.txt')
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print(f">> robots.txt: {len(lines) - 4} area sitemaps -> {output_file}")
    return output_file


def build_hub(output_file=None):
    registry = _load(os.path.join(PROJECT_ROOT, 'config', 'areas.json'), {})
    areas = [a for a in registry.get('areas', []) if a.get('enabled')]

    source = os.path.join(PROJECT_ROOT, 'web', 'index.html')
    with open(source, 'r', encoding='utf-8') as f:
        html = f.read()

    all_stats = [area_stats(a['id']) for a in areas]
    for stats in all_stats:
        html, ok = _replace_card(html, stats)
        if ok:
            print(f"   {stats['name']}: {stats['events']} events, "
                  f"{stats['dining']} dining, {stats['outings']} activities")

    # The meta description repeats the totals; keep it consistent.
    totals = {k: sum(s[k] for s in all_stats)
              for k in ('events', 'dining', 'outings', 'plans')}
    html = re.sub(
        r'\d+\+? events, \d+ restaurants, \d+ activities, \d+ curated plans\.',
        f"{totals['events']} events, {totals['dining']} restaurants, "
        f"{totals['outings']} activities, {totals['plans']} curated plans.",
        html, flags=re.IGNORECASE)

    output_file = output_file or os.path.join(PROJECT_ROOT, 'output', 'index.html')
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f">> Hub page: {output_file} "
          f"({totals['events']} events across {len(all_stats)} areas)")
    return output_file


if __name__ == '__main__':
    build_hub()
    build_sitemap_index()
    build_robots()

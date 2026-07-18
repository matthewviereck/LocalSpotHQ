"""Dead-link checker: HEAD-check every unique event and dining link across
all enabled areas. Report-only (exit 0 always) - results land in the GitHub
Actions step summary via stdout markdown."""

import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; LocalSpotHQ-linkcheck/1.0)'}


def collect_links():
    links = {}  # url -> list of "area: title"
    with open(os.path.join(ROOT, 'config', 'areas.json'), encoding='utf-8') as f:
        areas = [a for a in json.load(f)['areas'] if a.get('enabled')]
    for area in areas:
        area_id = area['id']
        sources = [
            os.path.join(ROOT, 'data', area_id, 'generated', 'events_formatted.json'),
            os.path.join(ROOT, 'data', area_id, 'dining.json'),
            os.path.join(ROOT, 'data', area_id, 'outings.json'),
        ]
        for path in sources:
            if not os.path.exists(path):
                continue
            with open(path, encoding='utf-8') as f:
                for item in json.load(f):
                    url = (item.get('link') or '').strip()
                    if url.startswith('http'):
                        links.setdefault(url, []).append(f"{area_id}: {item.get('title', '?')[:50]}")
    return links


def check(url):
    try:
        r = requests.head(url, headers=HEADERS, timeout=15, allow_redirects=True)
        # Some servers reject HEAD; retry those with a light GET
        if r.status_code in (403, 405, 501):
            r = requests.get(url, headers=HEADERS, timeout=15, stream=True)
            r.close()
        return url, r.status_code
    except requests.RequestException as e:
        return url, type(e).__name__


def main():
    links = collect_links()
    print(f"Checking {len(links)} unique links...", file=sys.stderr)

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = dict(pool.map(check, links))

    # 403 is usually a bot wall and 429 a rate limit - neither means the page
    # is gone for a human, so report them separately from real breakage
    dead = {u: s for u, s in results.items() if not isinstance(s, int) or s >= 400}
    hard_dead = {u: s for u, s in dead.items() if s not in (403, 429)}

    print(f"## Link check: {len(links)} checked, {len(hard_dead)} broken, "
          f"{len(dead) - len(hard_dead)} bot-walled or rate-limited\n")
    if hard_dead:
        print("| Status | Link | Used by |")
        print("|--------|------|---------|")
        for url, status in sorted(hard_dead.items(), key=lambda kv: str(kv[1])):
            used = '; '.join(links[url][:2])
            print(f"| {status} | {url[:80]} | {used} |")
    else:
        print("All links healthy.")


if __name__ == '__main__':
    main()

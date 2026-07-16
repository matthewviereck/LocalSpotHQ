"""Per-event SEO pages + area sitemap.

Each dated event gets /events/<slug>/index.html with Event JSON-LD - the
long-tail search surface one aggregate page can't rank for. Slugs are
title-only (matching the app's #event= deep links); recurring events that
share a title (52 Farmers Markets) collapse to ONE page for their next
occurrence rather than a pile of near-duplicate thin pages.
"""

import html
import json
import os
import re
import shutil
from datetime import datetime, date

from pipeline.feeds import _event_date


def _slug(title):
    return re.sub(r'^-|-$', '', re.sub(r'[^a-z0-9]+', '-', title.lower()))


def _event_page(ev, d, area_config):
    area_name = area_config['name']
    base_url = area_config['meta']['canonical_url'].rstrip('/')
    og_image = area_config['meta'].get('og_image', '')
    slug = _slug(ev['title'])
    canonical = f"{base_url}/events/{slug}/"

    title = ev['title']
    loc = ev.get('loc', area_name)
    typ = ev.get('type', 'Event')
    date_label = d.strftime('%A, %B %d, %Y').replace(' 0', ' ')
    img = ev.get('img', '')
    real_img = img and 'placehold.co' not in img

    page_title = f"{title} - {date_label}"
    description = (f"{title} on {date_label} at {loc}, {area_name} PA area. "
                   f"Details, times and links on LocalSpot.")

    json_ld = {
        "@context": "https://schema.org",
        "@type": "Event",
        "name": title,
        "startDate": d.isoformat(),
        "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
        "eventStatus": "https://schema.org/EventScheduled",
        "location": {
            "@type": "Place",
            "name": loc,
            "address": {"@type": "PostalAddress", "addressLocality": area_name,
                        "addressRegion": "PA", "addressCountry": "US"}
        },
        "organizer": {"@type": "Organization", "name": "LocalSpot HQ", "url": "https://www.localspothq.com/"},
        "url": ev.get('link') or canonical
    }
    if real_img:
        json_ld["image"] = [img]

    out_link = (f'<p><a class="cta" href="{html.escape(ev["link"])}" rel="nofollow">'
                f'Tickets &amp; details &rarr;</a></p>') if ev.get('link') else ''
    img_html = (f'<img src="{html.escape(img)}" alt="{html.escape(title)}" '
                f'referrerpolicy="no-referrer" loading="lazy">') if real_img else ''

    return slug, f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(page_title)} | LocalSpot {html.escape(area_name)}</title>
<meta name="description" content="{html.escape(description)}">
<meta name="robots" content="index, follow">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="website">
<meta property="og:url" content="{canonical}">
<meta property="og:title" content="{html.escape(page_title)}">
<meta property="og:description" content="{html.escape(description)}">
<meta property="og:image" content="{html.escape(img if real_img else og_image)}">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">{json.dumps(json_ld, ensure_ascii=False)}</script>
<style>
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;max-width:680px;margin:0 auto;padding:24px 16px;color:#0f172a;line-height:1.5}}
h1{{font-size:1.5rem;margin:8px 0 4px}}
.sub{{color:#64748b;margin-top:0}}
img{{max-width:100%;border-radius:12px;margin-top:12px}}
a{{color:#2563eb;text-decoration:none}}
a:hover{{text-decoration:underline}}
.crumb{{font-size:0.85rem;color:#94a3b8}}
.cta{{display:inline-block;margin-top:16px;background:#2563eb;color:#fff;padding:10px 18px;border-radius:10px;font-weight:700}}
footer{{margin-top:32px;color:#94a3b8;font-size:0.8rem}}
</style>
</head>
<body>
<p class="crumb"><a href="{base_url}/">LocalSpot {html.escape(area_name)}</a> &rsaquo; Events</p>
<h1>{html.escape(title)}</h1>
<p class="sub">{date_label} &middot; {html.escape(loc)}{' &middot; ' + html.escape(typ) if typ and typ != 'Event' else ''}</p>
{img_html}
{out_link}
<p><a href="{base_url}/#event={slug}">See this event in the {html.escape(area_name)} app &rarr;</a></p>
<footer>LocalSpot HQ &middot; updated {date.today().isoformat()}</footer>
</body>
</html>
"""


def generate_event_pages(events_file, output_dir, area_config):
    with open(events_file, 'r', encoding='utf-8') as f:
        events = json.load(f)

    events_dir = os.path.join(output_dir, 'events')
    # Regenerate from scratch so pages for past/removed events don't linger
    # (the deploy rsync uses --delete, so they disappear from the server too)
    if os.path.isdir(events_dir):
        shutil.rmtree(events_dir)

    seen = set()
    pages = []
    for ev in events:
        d = _event_date(ev)
        if not d:
            continue
        slug, page = _event_page(ev, d, area_config)
        if not slug or slug in seen:
            continue  # recurring titles collapse to their next occurrence
        seen.add(slug)
        page_dir = os.path.join(events_dir, slug)
        os.makedirs(page_dir, exist_ok=True)
        with open(os.path.join(page_dir, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(page)
        pages.append(slug)

    print(f">> Event pages: {len(pages)} -> {events_dir}")
    return pages


def generate_area_sitemap(output_dir, area_config, event_slugs):
    base_url = area_config['meta']['canonical_url'].rstrip('/')
    today = date.today().isoformat()

    def url(loc, freq, priority):
        return (f"  <url>\n    <loc>{loc}</loc>\n    <lastmod>{today}</lastmod>\n"
                f"    <changefreq>{freq}</changefreq>\n    <priority>{priority}</priority>\n  </url>")

    entries = [
        url(f"{base_url}/", 'daily', '1.0'),
        url(f"{base_url}/this-weekend/", 'daily', '0.9'),
    ]
    entries.extend(url(f"{base_url}/events/{slug}/", 'weekly', '0.6') for slug in event_slugs)

    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           + '\n'.join(entries) + '\n</urlset>\n')

    out_file = os.path.join(output_dir, 'sitemap.xml')
    with open(out_file, 'w', encoding='utf-8') as f:
        f.write(xml)
    print(f">> Area sitemap: {len(entries)} URLs -> {out_file}")
    return out_file

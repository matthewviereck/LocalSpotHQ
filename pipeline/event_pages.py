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
from pipeline.analytics import GA_SNIPPET


def _slug(title):
    return re.sub(r'^-|-$', '', re.sub(r'[^a-z0-9]+', '-', title.lower()))


# Google renders roughly 60 characters of <title> before truncating. Every one
# of these pages used to blow through that: the old pattern spent ~26 chars on
# "Saturday, October 24, 2026" and another ~25 on "| LocalSpot Phoenixville"
# before the event name started, so 100% of pages truncated mid-name and the
# brand suffix - which no one is searching for - was never even visible.
TITLE_BUDGET = 60
DESC_BUDGET = 158

# Long event names usually carry a subtitle after one of these; the head is the
# part people actually search for.
_TITLE_SEPS = (' – ', ' — ', ' -- ', ': ', ' - ', ' | ', ' w/ ', ' feat. ', ' featuring ')


# Words a trimmed title must not end on - "... Victoria Aveyard, Author of"
# reads like a bug, "... Victoria Aveyard" reads like a title.
_DANGLING = {'and', 'or', 'of', 'with', 'the', 'a', 'an', 'at', 'by', 'for',
             'in', 'on', 'to', 'from', 'presents', 'present', 'feat', 'feat.',
             'ft', 'ft.', 'featuring', 'plus', 'vs', 'vs.'}


def _tidy_end(text):
    """Strip trailing punctuation and connector words left by a cut."""
    prev = None
    while text and text != prev:
        prev = text
        text = text.rstrip(' ,;:&+-–—|/')
        last = text.rsplit(' ', 1)[-1] if ' ' in text else ''
        if last and last.lower() in _DANGLING:
            text = text[: -len(last)].rstrip()
    return text


def _short_title(name, budget):
    """Trim an event name to fit `budget`, preferring a natural break."""
    name = ' '.join(name.split())
    if len(name) <= budget:
        return name
    for sep in _TITLE_SEPS:
        head = _tidy_end(name.split(sep)[0].strip())
        if head and len(head) <= budget:
            return head
    cut = _tidy_end(name[:budget].rsplit(' ', 1)[0])
    # A cut that lands just past a comma leaves a fragment ("Victoria Aveyard,
    # Author"); backing up to the comma reads like a name again, as long as it
    # does not cost most of the title.
    if ',' in cut:
        head = _tidy_end(cut.rsplit(',', 1)[0])
        if len(head) >= budget * 0.6:
            return head
    return cut or name[:budget].strip()


def _price_note(price):
    """'Free' / '$12' / '' from the messy free-text price field."""
    p = (price or '').strip()
    if not p:
        return ''
    if p.lower().startswith('free'):
        return 'Free'
    m = re.search(r'\$\s?\d+(?:\.\d{2})?', p)
    return m.group(0).replace(' ', '') if m else ''


def _offer(price, url):
    """Schema.org Offer, so the price can surface in the rich result."""
    p = (price or '').strip()
    if p.lower().startswith('free'):
        amount = '0'
    else:
        m = re.search(r'\$\s?(\d+(?:\.\d{2})?)', p)
        if not m:
            return None
        amount = m.group(1)
    return {
        "@type": "Offer",
        "price": amount,
        "priceCurrency": "USD",
        "availability": "https://schema.org/InStock",
        "url": url,
    }


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

    town = (ev.get('town') or '').strip()
    when = (ev.get('time') or '').strip()
    price_note = _price_note(ev.get('price'))

    # "Sat Aug 29" - %-d is not portable to Windows, so build the day by hand.
    short_date = f"{d.strftime('%a %b')} {d.day}"

    # The town is the highest-value token in a local search, but repeating it
    # when it is already in the name ("Phoenixville Punk Rock Flea Market")
    # just burns budget.
    show_town = bool(town) and town.lower() not in title.lower()
    tail = f" — {town}, {short_date}" if show_town else f" — {short_date}"
    page_title = _short_title(title, max(24, TITLE_BUDGET - len(tail))) + tail

    # Lead the snippet with what a searcher actually wants to know - when,
    # where, how much - instead of the old boilerplate that read identically
    # on all 176 pages.
    long_date = f"{d.strftime('%A, %B')} {d.day}"
    facts = [f"{long_date} at {when}" if when else long_date]
    facts.append(loc if (not town or town.lower() in loc.lower()) else f"{loc}, {town}")
    if price_note:
        facts.append('Free admission' if price_note == 'Free' else price_note)
    where = town or area_name
    context = (f"{typ} in {where}, PA." if typ and typ != 'Event'
               else f"Things to do in {where}, PA.")
    description = f"{' · '.join(facts)}. {context} Full details and tickets."
    if len(description) > DESC_BUDGET:
        description = f"{' · '.join(facts)}. {context}"[:DESC_BUDGET].rstrip(' ·,-')

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
        "url": ev.get('link') or canonical
    }
    if real_img:
        json_ld["image"] = [img]
    # `organizer: LocalSpot HQ` used to sit here and was simply false - we
    # aggregate these events, we don't run them. Dropped rather than guessed
    # at; `offers` is the recommended field that actually earns something,
    # since the price can render in the event rich result.
    offer = _offer(ev.get('price'), ev.get('link') or canonical)
    if offer:
        json_ld["offers"] = offer

    out_link = (f'<p><a class="cta" href="{html.escape(ev["link"])}" rel="nofollow">'
                f'Tickets &amp; details &rarr;</a></p>') if ev.get('link') else ''
    img_html = (f'<img src="{html.escape(img)}" alt="{html.escape(title)}" '
                f'referrerpolicy="no-referrer" loading="lazy">') if real_img else ''

    return slug, f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
{GA_SNIPPET}
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(page_title)}</title>
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


def generate_area_sitemap(output_dir, area_config, event_slugs, guide_slugs=()):
    base_url = area_config['meta']['canonical_url'].rstrip('/')
    today = date.today().isoformat()

    def url(loc, freq, priority):
        return (f"  <url>\n    <loc>{loc}</loc>\n    <lastmod>{today}</lastmod>\n"
                f"    <changefreq>{freq}</changefreq>\n    <priority>{priority}</priority>\n  </url>")

    entries = [
        url(f"{base_url}/", 'daily', '1.0'),
        url(f"{base_url}/this-weekend/", 'daily', '0.9'),
    ]
    entries.extend(url(f"{base_url}/guides/{slug}/", 'monthly', '0.8') for slug in guide_slugs)
    entries.extend(url(f"{base_url}/events/{slug}/", 'weekly', '0.6') for slug in event_slugs)

    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           + '\n'.join(entries) + '\n</urlset>\n')

    out_file = os.path.join(output_dir, 'sitemap.xml')
    with open(out_file, 'w', encoding='utf-8') as f:
        f.write(xml)
    print(f">> Area sitemap: {len(entries)} URLs -> {out_file}")
    return out_file

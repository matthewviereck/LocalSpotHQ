"""Generate SEO/subscription artifacts from formatted events:
- this-weekend/index.html : crawlable static page of the upcoming weekend
- events.ics              : subscribable calendar feed
"""

import json
import os
import hashlib
import html
from datetime import datetime, timedelta, date

TBA_SENTINEL = 9999999999


def _event_date(ev):
    """Calendar date of an event (None for undated)."""
    ts = ev.get('_sort_date', TBA_SENTINEL)
    if ts == TBA_SENTINEL:
        return None
    return datetime.fromtimestamp(ts).date()


def weekend_range(today=None):
    """Upcoming Fri-Sun, or the current weekend if today is Fri/Sat/Sun."""
    today = today or date.today()
    dow = today.weekday()  # Mon=0 .. Sun=6
    if dow >= 4:  # Fri/Sat/Sun
        friday = today - timedelta(days=dow - 4)
    else:
        friday = today + timedelta(days=4 - dow)
    return friday, friday + timedelta(days=2)


def weekend_events(events, today=None):
    """Dated events falling on the upcoming weekend (today onwards)."""
    friday, sunday = weekend_range(today)
    today = today or date.today()
    start = max(friday, today)
    picked = []
    for ev in events:
        d = _event_date(ev)
        if d and start <= d <= sunday:
            picked.append((d, ev))
    picked.sort(key=lambda p: (p[0], p[1]['title'].lower()))
    return friday, sunday, picked


def generate_this_weekend_page(events_file, output_dir, area_config):
    with open(events_file, 'r', encoding='utf-8') as f:
        events = json.load(f)

    area_name = area_config['name']
    base_url = area_config['meta']['canonical_url'].rstrip('/')
    canonical = f"{base_url}/this-weekend/"
    # The generated weekend card (pipeline/social_card.py) beats a generic
    # stock photo when this page gets shared
    og_image = f"{base_url}/weekend-card.png"

    friday, sunday, picked = weekend_events(events)
    fri_label = f"{friday.strftime('%B')} {friday.day}"
    sun_label = f"{sunday.day}" if friday.month == sunday.month else f"{sunday.strftime('%B')} {sunday.day}"
    range_label = f"{fri_label}–{sun_label}, {sunday.year}"

    title = f"Things to Do in {area_name} This Weekend ({range_label})"
    description = (f"{len(picked)} events happening in and around {area_name} PA this weekend, "
                   f"{range_label}: festivals, live music, markets, family activities. Updated daily.")

    # Group by day
    by_day = {}
    for d, ev in picked:
        by_day.setdefault(d, []).append(ev)

    sections = []
    for d in sorted(by_day):
        rows = []
        for ev in by_day[d]:
            t = html.escape(ev['title'])
            loc = html.escape(ev.get('loc', ''))
            typ = html.escape(ev.get('type', ''))
            link = ev.get('link', '')
            title_html = f'<a href="{html.escape(link)}" rel="nofollow">{t}</a>' if link else t
            meta = ' &middot; '.join(x for x in (loc, typ if typ != 'Event' else '') if x)
            rows.append(f'<li><strong>{title_html}</strong><br><span class="meta">{meta}</span></li>')
        day_label = d.strftime('%A, %B %d').replace(' 0', ' ')
        sections.append(f'<h2>{day_label}</h2>\n<ul>\n' + '\n'.join(rows) + '\n</ul>')

    if not sections:
        sections = [f'<p>No events listed for this weekend yet — check the <a href="{base_url}/">full {area_name} events calendar</a>.</p>']

    # JSON-LD ItemList of Events
    items = []
    for i, (d, ev) in enumerate(picked, 1):
        item = {
            "@type": "ListItem",
            "position": i,
            "item": {
                "@type": "Event",
                "name": ev['title'],
                "startDate": d.isoformat(),
                "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
                "location": {"@type": "Place", "name": ev.get('loc', area_name),
                             "address": {"@type": "PostalAddress", "addressRegion": "PA", "addressCountry": "US"}}
            }
        }
        if ev.get('link'):
            item['item']['url'] = ev['link']
        items.append(item)
    json_ld = json.dumps({
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": title,
        "numberOfItems": len(picked),
        "itemListElement": items
    }, ensure_ascii=False)

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)} | LocalSpot</title>
<meta name="description" content="{html.escape(description)}">
<meta name="robots" content="index, follow">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="website">
<meta property="og:url" content="{canonical}">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(description)}">
<meta property="og:image" content="{og_image}">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">{json_ld}</script>
<style>
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;max-width:680px;margin:0 auto;padding:24px 16px;color:#0f172a;line-height:1.5}}
h1{{font-size:1.6rem;margin-bottom:4px}}
.sub{{color:#64748b;margin-top:0}}
h2{{font-size:1.1rem;margin:28px 0 8px;border-bottom:2px solid #e2e8f0;padding-bottom:4px}}
ul{{list-style:none;padding:0;margin:0}}
li{{padding:10px 0;border-bottom:1px solid #f1f5f9}}
a{{color:#2563eb;text-decoration:none}}
a:hover{{text-decoration:underline}}
.meta{{color:#64748b;font-size:0.85rem}}
.cta{{display:inline-block;margin-top:24px;background:#2563eb;color:#fff;padding:10px 18px;border-radius:10px;font-weight:700}}
footer{{margin-top:32px;color:#94a3b8;font-size:0.8rem}}
</style>
</head>
<body>
<h1>Things to Do in {html.escape(area_name)} This Weekend</h1>
<p class="sub">{range_label} &middot; {len(picked)} events &middot; updated daily</p>
{os.linesep.join(sections)}
<a class="cta" href="{base_url}/">See all {html.escape(area_name)} events &rarr;</a>
<p><a href="{base_url}/events.ics">&#128197; Subscribe to the {html.escape(area_name)} events calendar</a></p>
<footer>LocalSpot HQ &middot; generated {datetime.now().strftime('%Y-%m-%d')}</footer>
</body>
</html>
"""
    out_dir = os.path.join(output_dir, 'this-weekend')
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, 'index.html')
    with open(out_file, 'w', encoding='utf-8') as f:
        f.write(page)
    print(f">> This Weekend page: {len(picked)} events -> {out_file}")
    return out_file


def _ics_escape(text):
    return (text.replace('\\', '\\\\').replace(';', '\\;')
                .replace(',', '\\,').replace('\n', '\\n'))


def _ics_fold(line):
    """Fold lines >75 octets per RFC 5545."""
    out = []
    while len(line.encode('utf-8')) > 73:
        cut = 73
        while len(line[:cut].encode('utf-8')) > 73:
            cut -= 1
        out.append(line[:cut])
        line = ' ' + line[cut:]
    out.append(line)
    return '\r\n'.join(out)


def generate_ics(events_file, output_dir, area_config):
    with open(events_file, 'r', encoding='utf-8') as f:
        events = json.load(f)

    area_name = area_config['name']
    now_utc = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')

    lines = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//LocalSpot HQ//' + area_name + ' Events//EN',
        'CALSCALE:GREGORIAN',
        'METHOD:PUBLISH',
        f'X-WR-CALNAME:{_ics_escape(area_name)} Events (LocalSpot)',
        'X-WR-TIMEZONE:America/New_York',
    ]

    count = 0
    for ev in events:
        d = _event_date(ev)
        if not d:
            continue
        uid = hashlib.md5((ev['title'] + d.isoformat()).encode('utf-8')).hexdigest()
        lines.append('BEGIN:VEVENT')
        lines.append(f'UID:{uid}@localspothq.com')
        lines.append(f'DTSTAMP:{now_utc}')
        lines.append(f'DTSTART;VALUE=DATE:{d.strftime("%Y%m%d")}')
        lines.append(f'DTEND;VALUE=DATE:{(d + timedelta(days=1)).strftime("%Y%m%d")}')
        lines.append(_ics_fold(f'SUMMARY:{_ics_escape(ev["title"])}'))
        if ev.get('loc'):
            lines.append(_ics_fold(f'LOCATION:{_ics_escape(ev["loc"])}'))
        if ev.get('link'):
            lines.append(_ics_fold(f'URL:{ev["link"]}'))
        lines.append('END:VEVENT')
        count += 1

    lines.append('END:VCALENDAR')

    out_file = os.path.join(output_dir, 'events.ics')
    with open(out_file, 'w', encoding='utf-8', newline='') as f:
        f.write('\r\n'.join(lines) + '\r\n')
    print(f">> ICS feed: {count} events -> {out_file}")
    return out_file

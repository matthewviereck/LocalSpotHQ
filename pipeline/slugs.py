"""Stable URLs for event pages.

Event page slugs used to be a pure function of the title. Discovery re-titles
events freely ("WCU Homecoming Weekend" -> "WCU Homecoming 2026" -> "WCU
Homecoming & Family Weekend" in one week), the build regenerates every page
from scratch, and the deploy rsyncs with --delete - so each rename turned a
ranked URL into a 404 and started a fresh one from zero. Search Console held
106 such 404s on 2026-09-03, including the two highest-impression pages of
that week.

This module makes the URL outlive the title:

* `data/<area>/slug_registry.json` (committed; CI writes it back after each
  build) records every slug ever published with the event's venue, date and
  latest title.
* `assign_slugs` gives each event its registered slug when one matches -
  exactly, or the same venue + same date + a similar title (a rename), or
  the same venue + the same year-stripped title (an annual repeat) - and
  only mints a new slug when nothing does. New slugs drop standalone years
  so "Blobfest 2027" can inherit "Blobfest 2026"'s URL.
* `emit_retired` handles every registered slug that is NOT in the build:
  301 to the live page it was superseded by, a "this event has passed"
  stub while the event is recent, 410 once it is long gone. Nothing that
  was ever a URL returns a 404 again.
"""

import html
import json
import os
import re
from datetime import date, datetime, timedelta

from pipeline.analytics import GA_SNIPPET

REGISTRY_FILE = 'slug_registry.json'

# A registered slug at the same venue on the same date is the same event if
# this share of the smaller title's tokens survives in the other. 0.5 lets
# "WCU Homecoming 2026" claim "WCU Homecoming Weekend" and "Josh Blue: The
# Road Dog Tour" claim "Josh Blue", while two different comedians at the same
# venue share too little to cross it.
SIMILARITY = 0.5

# Lifecycle of a retired URL, counted from the event's (last) date.
STUB_INDEX_DAYS = 30   # stub stays indexable: stale search results still land somewhere useful
STUB_DAYS = 90         # then noindex,follow until here
GONE_DAYS = 730        # then 410 until here, after which the record is dropped

_STOP = {'the', 'a', 'an', 'and', 'or', 'of', 'at', 'in', 'on', 'with', 'to',
         'for', 'by', 'from', 'live', 'presents', 'feat', 'featuring', 'vs',
         'w', 'ft', 'free', 'event', 'events', 'night', 'day', 'annual',
         'weekend', 'pa', 'downtown'}


def legacy_slug(title):
    """The pre-registry slug: exactly what the old pages were published under."""
    return re.sub(r'^-|-$', '', re.sub(r'[^a-z0-9]+', '-', str(title or '').lower()))


def title_slug(title):
    """Slug for a NEW event: the legacy form minus standalone years, capped."""
    s = legacy_slug(title)
    s = re.sub(r'(?:^|-)(?:19|20)\d{2}(?=-|$)', '', s)
    s = re.sub(r'-{2,}', '-', s).strip('-')
    return (s or legacy_slug(title))[:80].rstrip('-')


def _tokens(title):
    t = str(title or '').lower()
    t = re.sub(r'\b(?:19|20)\d{2}\b', ' ', t)          # years
    t = re.sub(r'\b\d+(?:st|nd|rd|th)\b', ' ', t)      # ordinals: 29th annual
    return frozenset(w for w in re.findall(r'[a-z0-9]+', t) if w not in _STOP)


def similarity(a, b):
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / min(len(ta), len(tb))


def title_key(title):
    """Year- and noise-free identity of a title, for annual repeats."""
    return ' '.join(sorted(_tokens(title)))


def venue_key(loc):
    """'Colonial Theatre, Phoenixville' and 'Colonial Theatre' are one venue."""
    first = re.split(r',|\(', str(loc or ''))[0]
    key = re.sub(r'[^a-z0-9]', '', first.lower())
    return '' if key in ('', 'unknownvenue', 'tba') else key


def _event_date(ev):
    ts = ev.get('_sort_date')
    if not isinstance(ts, (int, float)) or ts >= 9e9:
        return None
    return datetime.fromtimestamp(ts).date()


class SlugRegistry:
    def __init__(self, path):
        self.path = path
        self.slugs = {}
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                self.slugs = json.load(f).get('slugs', {})

    def save(self):
        os.makedirs(os.path.dirname(self.path) or '.', exist_ok=True)
        data = {'version': 1, 'slugs': dict(sorted(self.slugs.items()))}
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=1, ensure_ascii=False)
            f.write('\n')

    def record(self, slug, title, venue, d, seen):
        """Upsert: first_seen is sticky, everything else follows the latest build."""
        rec = self.slugs.get(slug)
        if rec is None:
            rec = self.slugs[slug] = {'first_seen': seen}
        rec['title'] = title
        rec['venue'] = venue
        rec['date'] = d.isoformat()
        rec['last_seen'] = seen
        if 'first_seen' not in rec:
            rec['first_seen'] = seen
        return rec

    def _by_venue(self):
        index = {}
        for slug, rec in self.slugs.items():
            vk = venue_key(rec.get('venue'))
            if vk:
                index.setdefault(vk, []).append((slug, rec))
        return index

    def match(self, title, venue, d, exclude, by_venue=None):
        """The registered slug this event should keep, or None.

        Exact slug first: a URL that is live stays live. Otherwise a record at
        the same venue that is either the same date with a similar title (a
        rename) or the same year-stripped title (an annual repeat); the
        oldest such URL wins, since it has had longest to earn its ranking.
        """
        exact = [s for s in (legacy_slug(title), title_slug(title))
                 if s in self.slugs and s not in exclude]
        if exact:
            return min(exact, key=lambda s: self.slugs[s].get('first_seen', ''))

        vk = venue_key(venue)
        if not vk:
            return None
        tk = title_key(title)
        iso = d.isoformat() if d else None
        by_venue = by_venue if by_venue is not None else self._by_venue()
        cands = []
        for slug, rec in by_venue.get(vk, []):
            if slug in exclude:
                continue
            same_day = iso is not None and rec.get('date') == iso
            if (same_day and similarity(title, rec.get('title', '')) >= SIMILARITY) \
                    or (tk and tk == title_key(rec.get('title', ''))):
                cands.append(slug)
        if not cands:
            return None
        return min(cands, key=lambda s: self.slugs[s].get('first_seen', ''))


def assign_slugs(events_file, registry, today=None):
    """Give every event in the formatted file a `slug`, pinned by the registry.

    Rewrites the file in place so the app (via inject) and the event pages
    read the same URL. Returns the events. Undated events get a slug too -
    the app links every event - but only dated ones get a page or a record.
    """
    today = (today or date.today()).isoformat()
    with open(events_file, 'r', encoding='utf-8') as f:
        events = json.load(f)

    by_venue = registry._by_venue()
    used = set()
    by_title = {}  # same title in one build = one page (52 Farmers Markets, a 3-day festival)
    pinned = renamed = 0
    for ev in events:
        title = ev.get('title', '')
        d = _event_date(ev)
        if d is None:
            ev['slug'] = title_slug(title)
            continue
        tkey = legacy_slug(title)
        if tkey in by_title:
            ev['slug'] = by_title[tkey]
            continue
        slug = registry.match(title, ev.get('loc', ''), d, exclude=used, by_venue=by_venue)
        if slug is None:
            slug = title_slug(title)
        elif slug not in (legacy_slug(title), title_slug(title)):
            renamed += 1
        else:
            pinned += 1
        ev['slug'] = slug
        by_title[tkey] = slug
        if slug in used:
            continue
        used.add(slug)
        rec = registry.record(slug, title, ev.get('loc', ''), d, today)
        # keep the venue index current for later events in this same build
        vk = venue_key(ev.get('loc', ''))
        if vk and all(s != slug for s, _ in by_venue.get(vk, [])):
            by_venue.setdefault(vk, []).append((slug, rec))

    with open(events_file, 'w', encoding='utf-8') as f:
        json.dump(events, f, indent=2, ensure_ascii=False)
    print(f">> Slugs: {len(used)} live ({pinned} kept, {renamed} pinned through a rename)")
    return events


def _stub_page(slug, rec, area_config, indexable):
    area_name = area_config['name']
    base_url = area_config['meta']['canonical_url'].rstrip('/')
    canonical = f"{base_url}/events/{slug}/"
    title = rec.get('title', slug.replace('-', ' ').title())
    venue = rec.get('venue', '')
    try:
        d = date.fromisoformat(rec['date'])
        when = f"{d.strftime('%A, %B')} {d.day}, {d.year}"
    except (KeyError, ValueError):
        d, when = None, ''
    if d and d < date.today():
        lede = f"This event took place on {when}" + (f" at {html.escape(venue)}" if venue else '') + "."
        page_title = f"{title} — past event"
    else:
        lede = "This listing is no longer available" + (f" ({when})" if when else '') + "."
        page_title = f"{title} — no longer listed"
    robots = 'index, follow' if indexable else 'noindex, follow'
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
{GA_SNIPPET}
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(page_title)}</title>
<meta name="description" content="{html.escape(lede)} See what's on now in {html.escape(area_name)}, PA.">
<meta name="robots" content="{robots}">
<link rel="canonical" href="{canonical}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;600;700&family=Newsreader:opsz,wght@6..72,400;6..72,600&display=swap">
<link rel="stylesheet" href="../../localspot.css">
<style>
body{{max-width:680px;margin:0 auto;padding:24px 16px}}
.crumb{{font-size:13px;color:var(--ink-faint)}}
.crumb a{{color:var(--ink-faint);text-decoration:none}}
.sub{{color:var(--ink-soft);margin-top:2px;font-size:15px}}
a{{color:var(--cool)}}
.cta{{display:inline-block;margin-top:16px;background:var(--ink);color:var(--paper);
padding:10px 18px;border-radius:var(--radius);font-weight:600;font-family:var(--display);
text-decoration:none}}
footer{{margin-top:32px;padding-top:16px;border-top:1px solid var(--rule);
color:var(--ink-faint);font-size:13px}}
</style>
</head>
<body>
<p class="crumb"><a href="{base_url}/">LocalSpot {html.escape(area_name)}</a> &rsaquo; Events</p>
<h1>{html.escape(title)}</h1>
<p class="sub">{lede}</p>
<p>Many local events come back around each year — when this one is announced again, it will be listed here.</p>
<p><a class="cta" href="{base_url}/this-weekend/">What's on this weekend in {html.escape(area_name)} &rarr;</a></p>
<p><a href="{base_url}/#events">All upcoming {html.escape(area_name)} events</a></p>
<footer>LocalSpot HQ &middot; updated {date.today().isoformat()}</footer>
</body>
</html>
"""


def emit_retired(registry, events, output_dir, area_config, today=None):
    """Redirect, stub or 410 every registered slug missing from this build.

    Writes output/<area>/.htaccess (rewrite rules) and stub pages under
    events/<slug>/. Also prunes records past GONE_DAYS. Call AFTER the event
    pages are generated - the events dir is rebuilt from scratch each run.
    """
    today = today or date.today()
    base_url = area_config['meta']['canonical_url'].rstrip('/')
    live = {}
    for ev in events:
        d = _event_date(ev)
        if d is None or not ev.get('slug') or ev['slug'] in live:
            continue
        live[ev['slug']] = (ev.get('title', ''), venue_key(ev.get('loc', '')),
                            d.isoformat(), title_key(ev.get('title', '')))

    redirects, gone, stubs, pruned = [], [], [], []
    for slug, rec in list(registry.slugs.items()):
        if slug in live:
            continue
        try:
            last = date.fromisoformat(rec.get('date', ''))
        except ValueError:
            last = today
        age = (today - last).days

        vk, tk = venue_key(rec.get('venue')), title_key(rec.get('title', ''))
        target = None
        if vk:
            for lslug, (ltitle, lvk, ldate, ltk) in live.items():
                if lvk != vk:
                    continue
                if (ldate == rec.get('date') and similarity(rec.get('title', ''), ltitle) >= SIMILARITY) \
                        or (tk and tk == ltk):
                    target = lslug
                    break
        if target:
            redirects.append((slug, target))
        elif age <= STUB_DAYS:
            # Indexable only for an event that actually happened recently -
            # a listing dropped before its date has nothing worth ranking.
            indexable = 0 <= age <= STUB_INDEX_DAYS
            stubs.append((slug, indexable))
            page_dir = os.path.join(output_dir, 'events', slug)
            os.makedirs(page_dir, exist_ok=True)
            with open(os.path.join(page_dir, 'index.html'), 'w', encoding='utf-8') as f:
                f.write(_stub_page(slug, rec, area_config, indexable=indexable))
        elif age <= GONE_DAYS:
            gone.append(slug)
        else:
            pruned.append(slug)
            del registry.slugs[slug]

    lines = [
        "# Generated by pipeline/slugs.py - do not edit by hand.",
        "# Old event URLs: 301 to the page that replaced them, 410 once the",
        "# event is long gone. Recently ended events keep a stub page instead.",
        "RewriteEngine On",
    ]
    for old, new in sorted(redirects):
        lines.append(f"RewriteRule ^events/{re.escape(old)}/?$ {base_url}/events/{new}/ [R=301,L]")
    for old in sorted(gone):
        lines.append(f"RewriteRule ^events/{re.escape(old)}/?$ - [G,L]")
    with open(os.path.join(output_dir, '.htaccess'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')

    print(f">> Retired slugs: {len(redirects)} redirected, {len(stubs)} stubbed "
          f"({sum(1 for _, i in stubs if i)} indexable), {len(gone)} gone (410), {len(pruned)} pruned")
    return {'redirects': redirects, 'stubs': stubs, 'gone': gone, 'pruned': pruned}

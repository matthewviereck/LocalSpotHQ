---
name: discover-events
description: Research real upcoming events on the web for the LocalSpot areas (West Chester and Phoenixville) and write them to each area's discovered_events.json. Use when asked to find, refresh, or top up local events, or when running the daily event discovery routine.
---

# Event discovery for LocalSpot

Find real, verifiable upcoming events for the two LocalSpot areas and write
them into the files the build pipeline merges. This is the judgment layer that
sits on top of the deterministic scrapers.

## What this routine is and is not responsible for

The site gets events from three places. Know which is which before you start,
because duplicating a scraper's work actively makes the site worse.

| Source | Owns | Runs |
|---|---|---|
| `scrapers/` | Venue and calendar feeds that can be parsed reliably | Every build |
| This routine | Everything a scraper can't reach | On demand / daily |
| `recurring_events_config.json` | Standing weekly items | Every build |

**Do not re-list events from `downtownwestchester.com`.** `scrapers/downtown_west_chester.py`
pulls that calendar's JSON API in full every build, with start times, prices
and images this routine cannot match. Likewise, don't re-list Uptown Knauer
(`scrapers/uptown_knauer.py`), the Colonial Theatre, Philly Expo/Oaks, or
Steel City — all scraped.

The reason is **wasted effort, not broken output**. The pipeline dedupes three
times — `merge.py` on title + raw date string, `transform.py` again on title +
*parsed* date, then `fuzzy_dedupe` on token overlap for the same date — so
near-duplicates do get collapsed. What overlap actually costs you is the whole
run: researching 80 events by hand to contribute 8 new ones is a slow, failure-
prone way to spend a routine, and the scraper's copy is better anyway (it
carries start times, prices and images that research rarely recovers).

So: your job is the venues and organizations that have no clean feed.

## Where to look

### West Chester area
Roster towns: West Chester, Exton, Malvern, Chester Springs, Downingtown,
Coatesville, Kennett Square, Chadds Ford.

- Longwood Gardens (Kennett Square) — marquee events and festivals only, not
  daily admission
- The Mushroom Festival (Kennett Square)
- Chester County History Center
- American Helicopter Museum
- West Chester University public events, homecoming, family weekend
- Brandywine River Museum, Brandywine Valley venues
- West Chester Railroad special rides
- QVC Studio Park
- Daily Local News and VISTA Today event coverage

### Phoenixville area
Roster towns: Phoenixville, Mont Clare, Kimberton, Oaks, Valley Forge,
Collegeville, Trappe, Skippack, Spring City, Royersford, Limerick, Pottstown.

- Molly Maguires and other Bridge Street venues (Bandsintown is a dead source —
  403s any plain HTTP client — so these need manual research)
- Phoenixville First Friday, Firebird Festival, Dogwood Festival
- Kimberton Fair, Valley Forge National Historical Park programming
- Rivercrest / Spring City / Royersford borough events
- Pottstown and Limerick community calendars

Search beyond this list. It is a floor, not a ceiling.

## Rules

- **Never invent an event.** Every entry needs a concrete upcoming date and a
  source link you actually fetched and read. If you could not verify it, it
  does not go in the file.
- Skip past dates. Check today's date first.
- **Expect a small file, and don't pad it.** Once the scrapers are excluded
  there is genuinely not much left in West Chester — a first pass in
  September 2026 found 81 events and only 8 survived the overlap check
  (Longwood, the Mushroom Festival, the Helicopter Museum). That is a success,
  not a shortfall. Phoenixville is the larger share, since it has no calendar
  API and only three venue scrapers.
- Quality over volume — one real festival beats ten bar trivia nights. Never
  add a marginal event to hit a number.
- Prefer events with broad appeal. Skip recurring pub programming (quizzo,
  karaoke, music bingo); the scrapers already filter these out deliberately.
- Each area's file is a **full overwrite** owned by this routine. Re-verify
  rather than blindly carrying yesterday's entries forward — dates and
  festival end dates do change.

## Output files

- West Chester: `data/west_chester/scraped/discovered_events.json`
- Phoenixville: `data/phoenixville/scraped/discovered_events.json`

Both are gitignored, so committing them needs `git add -f`.

## Schema

A JSON array of objects in exactly this shape:

```json
{
  "id": "discovered_<short_slug>_<YYYYMMDD of event date>",
  "type": "event",
  "title": "Event Title",
  "venue_info": {
    "name": "Venue Name, Town",
    "location": {"lat": 39.9601, "lng": -75.6055}
  },
  "raw_date_string": "Sep 17, 2026",
  "attributes": {
    "category": "Live Music",
    "vibes": ["Free", "Outdoor"],
    "price": "Free"
  },
  "media": {"image": ""},
  "action_link": "https://verified-source-url"
}
```

**`raw_date_string` format** — use this exact shape. `transform.py` parses
looser forms fine (Phoenixville's routine writes `"September 5, 2026 8:00 PM"`
and nothing breaks), so this is hygiene rather than a hard requirement, but
matching it lets duplicates collapse at the first pass instead of the third.
Put the time in `attributes.time`, not in the date string.

- Single day: `"Sep 17, 2026"`
- Range in one month: `"Sep 12 - 13, 2026"`
- Range across months: `"Oct 16 - Nov 15, 2026"`
- Months always abbreviated: Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec

**`category`** must be one of: Live Music, Theater, Festival, Community Event,
Farmers Market, Comedy, Expo, Kids & Family, Food & Drink, Art & Culture, Sports.

**`venue_info.location`** should be the real venue coordinates when you know
them. `pipeline/geo.py` routes every event to its nearest roster town and
**drops anything outside the area radius**, so a lazy default can silently
delete the event from the build. Venue *names* are not trusted for routing —
only coordinates. Fall back to downtown West Chester (39.9601, -75.6055) or
downtown Phoenixville (40.1304, -75.5149) only when you genuinely can't find
better.

Include `attributes.time` and `attributes.price` whenever the source states
them. `merge.py` ranks duplicate copies of an event by richness and prefers the
one carrying a time, then a price — so these fields decide which version ships.

## Finishing

1. Validate the file parses:
   ```
   python -c "import json; json.load(open(r'data/west_chester/scraped/discovered_events.json', encoding='utf-8'))"
   ```
2. Sanity-check the merge picks it up:
   ```
   python pipeline/run.py --area west_chester
   ```
3. Stage with `-f` (the directory is gitignored):
   ```
   git add -f data/west_chester/scraped/discovered_events.json
   ```
4. Commit as `Daily WC discovery: <N> events (<YYYY-MM-DD>)` (or
   `Daily PHX discovery: ...`).
5. `git pull --rebase --autostash origin master`, then `git push origin master`.
   Rebase and retry once if rejected.

The GitHub Actions workflow builds and deploys at 10:15 UTC daily, so anything
pushed before then reaches the live site the same morning.

Touch nothing else in the repo.

# LocalSpot - Automated Local Event Aggregator

## Project Overview
LocalSpot scrapes events from local venues (Colonial Theatre, Philly Expo Center), generates recurring events, and injects everything into a mobile-first HTML web app deployed to Hostinger.

## Tech Stack
- **Language**: Python 3
- **Dependencies**: `requests`, `beautifulsoup4` (install via `pip install -r requirements.txt`)
- **Frontend**: Static HTML + Tailwind CSS + vanilla JS (no framework)
- **Hosting**: Hostinger (shared hosting, PHP cron backup)

## Key Architecture
The project has two parallel implementations:
1. **Modular pipeline** (`pipeline/`, `scrapers/`, `config/`) - config-driven, supports multiple areas
2. **Root-level standalone scripts** - backward-compatible user-facing scripts

### Data Flow
```
Scrapers (scrapers/) → Raw JSON (data/*/scraped/)
Recurring events (pipeline/recurring.py) → recurring_events.json
  → merge (pipeline/merge.py) → all_events.json
  → transform (pipeline/transform.py) → events_formatted.json
  → inject into HTML template (pipeline/inject.py)
  → postprocess (pipeline/postprocess.py)
  → app.html (ready to deploy)
```

## Important Commands
```bash
# Install dependencies
pip install -r requirements.txt

# Run full pipeline (modular)
python pipeline/run.py --area phoenixville

# Run full pipeline (user-friendly wrapper)
python weekly_update.py

# Run individual steps
python scrapers/colonial_theatre.py
python scrapers/philly_expo.py
python pipeline/merge.py --area phoenixville
python pipeline/transform.py --area phoenixville
python pipeline/inject.py --area phoenixville
```

## Project Structure
- `config/` - Area configs (areas.json, phoenixville.json)
- `pipeline/` - Modular pipeline: run.py, recurring.py, merge.py, geo.py, transform.py, inject.py, postprocess.py, hub.py
- `scrapers/` - Web scrapers: colonial_theatre.py, philly_expo.py
- `templates/` - HTML template (app_template.html)
- `web/` - Static web files (index.html, robots.txt, sitemap.xml, submit.html)
- `data/phoenixville/` - Area data: dining.json, outings.json, plans.json, recurring config
- `deploy/` - PHP auto-update for Hostinger cron
- `archive/` - Historical phase completion docs

## Configuration
- `config/areas.json` - Registry of geographic areas (phoenixville and west_chester both enabled)
- `config/phoenixville.json` - Area-specific config (scrapers, data paths, deploy paths, metadata, town roster)
- `data/phoenixville/recurring_events_config.json` - Recurring event definitions

## Town rosters and geographic routing
Each area config carries a `towns` roster (name + lat/lng) and a `geo` block
(`radius_miles`, `tagline_towns`). `pipeline/geo.py` assigns every event to its
nearest roster town and drops anything outside the area — venue *names* are not
trusted, because discovery labels venues things like
"Eagleview Town Center, Exton (near Phoenixville)".

`run.py` pools all areas' `merge_sources` before routing, so an event one area's
discovery found still reaches the area whose roster actually claims it. The
header tagline is derived from the towns that have events, not hardcoded.
A town may set `dining_group` to share a neighbor's restaurant pool
(Mont Clare -> Phoenixville).

## Notes
- Scrapers use requests + BeautifulSoup with 30s timeouts. **Use
  `scrapers/http_headers.BROWSER_HEADERS`, not an ad-hoc `Mozilla/5.0`** — a
  bare UA gets a 403 from some venue hosts (this silently killed Uptown Knauer
  for five months).
- A failing scraper falls back to its last-good file rather than blanking the
  site, which also makes breakage invisible. `scripts/check_scraper_health.py`
  runs after deploy and fails the workflow when an active scraper has no
  upcoming events. Retire a dead scraper from the area config rather than
  leaving it to fail — the check is only honest if the config is.
- Bandsintown is a dead source (403 bot wall for any plain HTTP client).
  `scrapers/molly_maguires.py` is retired for this reason; AI discovery covers
  that venue instead.
- Date parsing is custom regex-based (no dateutil dependency)
- HTML injection uses regex find/replace on `const eventsData = [...]` patterns
- `deploy/auto_update.php` is a legacy server-side reimplementation. Since the
  2026-07-16 cutover it sees the `deploy/CUTOVER` marker and only sends the
  Friday digest — GitHub Actions owns the build and deploy. It has no town
  routing, so don't revive it without porting `pipeline/geo.py`.
- Events carry `time` and `price` when a source supplies them. Colonial, Oaks
  and Uptown publish neither (times live in AgileTicketing/OvationTix widgets),
  so those come from recurring config and discovery only.
- Root-level JSON files (all_events.json, etc.) are deprecated; pipeline uses `data/` subdirectories

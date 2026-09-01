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
- **Design system (2026 redesign, branch `redesign-2026`):** all four page
  generators — the app template, `event_pages.py`, `guides.py` and `feeds.py` —
  link one hand-authored stylesheet, `assets/localspot.css`, which
  `postprocess.ship_design_css()` copies into every area's output. There is no
  Tailwind and no build step; edit the CSS directly. Before this, the app used
  Tailwind-CDN-compiled-to-`app.css` while each generated page carried its own
  ad-hoc inline CSS, so the site had four unrelated looks.
- The app's nav is Today / Events / News / Explore / Community. Dining was
  deliberately demoted out of the nav into a short reference inside "Explore".
- `data/<area>/town.json` holds civic info, schools and evergreen town facts;
  it is injected as `townData`. A missing file just renders those blocks empty.
- **The community board is emitted into the build** by `pipeline/community.py`,
  not uploaded by hand: the deploy rsyncs `output/<area>/` with `--delete`, so
  anything not written into the build is removed from the server. Posts are
  moderated — `community_moderate.php` needs `community_token.txt` one level
  ABOVE the docroot, and fails closed (503) when that file is absent.
- `deploy/auto_update.php` is a legacy server-side reimplementation. Since the
  2026-07-16 cutover it sees the `deploy/CUTOVER` marker and only sends the
  Friday digest — GitHub Actions owns the build and deploy. It has no town
  routing, so don't revive it without porting `pipeline/geo.py`.
- Events carry `time` and `price` when a source supplies them. Colonial, Oaks
  and Uptown publish neither (times live in AgileTicketing/OvationTix widgets),
  so those come from recurring config and discovery only.
- Root-level JSON files (all_events.json, etc.) are deprecated; pipeline uses `data/` subdirectories

## Vault: log meaningful work without being asked

This repo's hub note is:

    C:\Users\matth\Documents\Second Brain MV\01 Projects\LocalSpotHQ\LocalSpotHQ.md

**Sessions in this repo do not load the vault's CLAUDE.md** - only this file -
so nothing else will remind you the vault exists. Treat updating the hub as
part of finishing a piece of work, not a separate task the user has to ask for.

**Log to "Notes & decisions"** (newest first, dated) when you:
- ship something users see, or deploy
- make a decision with a rationale worth not re-litigating
- find a bug whose *cause* would be expensive to rediscover
- discover a constraint about how the system actually behaves

**Tick or add "Next actions"** when work opens or closes one.

**Do NOT log** routine commits, refactors with no decision in them, or anything
the git log already answers. The hub is for *why*; the diff is the *what*. A hub
full of noise is as useless as an empty one.

**Also append one line to that day's note** in `05 Daily Notes/YYYY-MM-DD.md`
linking to `[[LocalSpotHQ]]`, so the day reads as a record of what happened.

Record the reusable lesson, not just the incident. "A path expression copied
between files at different directory depths is silently wrong" is worth keeping;
"fixed community.php" is not.

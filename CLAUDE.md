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
- `pipeline/` - Modular pipeline: run.py, recurring.py, merge.py, transform.py, inject.py, postprocess.py
- `scrapers/` - Web scrapers: colonial_theatre.py, philly_expo.py
- `templates/` - HTML template (app_template.html)
- `web/` - Static web files (index.html, robots.txt, sitemap.xml, submit.html)
- `data/phoenixville/` - Area data: dining.json, outings.json, plans.json, recurring config
- `deploy/` - PHP auto-update for Hostinger cron
- `archive/` - Historical phase completion docs

## Configuration
- `config/areas.json` - Registry of geographic areas (phoenixville enabled, west_chester disabled)
- `config/phoenixville.json` - Area-specific config (scrapers, data paths, deploy paths, metadata)
- `data/phoenixville/recurring_events_config.json` - Recurring event definitions

## Notes
- Scrapers use requests + BeautifulSoup with User-Agent headers and 30s timeouts
- Date parsing is custom regex-based (no dateutil dependency)
- HTML injection uses regex find/replace on `const eventsData = [...]` patterns
- The PHP version in `deploy/auto_update.php` is a full reimplementation for server-side cron
- Root-level JSON files (all_events.json, etc.) are deprecated; pipeline uses `data/` subdirectories

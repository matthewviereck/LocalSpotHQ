# LocalSpot - Automated Local Event Aggregator

A beautiful, mobile-first web app that aggregates local events from multiple venues and presents them in an easy-to-browse interface.

## 🎯 What This Does

LocalSpot automatically scrapes event data from:
- **The Colonial Theatre** (Phoenixville) - concerts, comedy, films
- **Greater Philadelphia Expo Center** (Oaks) - expos, shows, conventions

Then transforms and displays this data in a sleek, filterable web interface.

## 📁 Project Structure

```
localspot/
│
├── 🌐 WEBSITE FILES
│   ├── index.html                    # Landing page (region selector)
│   ├── phoenixville.html            # Main app (after updates)
│   └── phoenixville_updated.html    # Generated output ⭐
│
├── 🔧 SCRAPING SCRIPTS
│   ├── scrape_colonial_v2.py        # Scrapes Colonial Theatre
│   ├── scape_oaks.py                # Scrapes Philly Expo Center
│   ├── debug_colonial.py            # Debug tool for Colonial
│   └── debug_oaks.py                # Debug tool for Oaks
│
├── 🔄 DATA PROCESSING
│   ├── merge_data.py                # Combines all scraped data
│   ├── transform_events.py          # Converts to website format
│   └── inject_events.py             # Injects data into HTML
│
├── 📊 DATA FILES
│   ├── colonial_events.json         # Raw Colonial data
│   ├── oaks_events.json             # Raw Oaks data
│   ├── all_events.json              # Merged raw data
│   └── events_formatted.json        # Website-ready data ⭐
│
└── 🚀 AUTOMATION
    └── update_localspot.py           # Run everything at once!
```

## 🚀 Quick Start

### Option 1: Full Automation (Recommended)
Run everything with one command:
```bash
python3 update_localspot.py
```

This will:
1. Scrape both venues
2. Merge the data
3. Transform it
4. Inject it into your HTML
5. Output: `phoenixville_updated.html` ready to deploy!

### Option 2: Manual Steps
If you need more control:

```bash
# 1. Scrape events
python3 scrape_colonial_v2.py
python3 scape_oaks.py

# 2. Merge data
python3 merge_data.py

# 3. Transform to website format
python3 transform_events.py

# 4. Inject into HTML
python3 inject_events.py
```

## 📋 Data Flow

```
Colonial Theatre Website     Philly Expo Website
        |                            |
        v                            v
scrape_colonial_v2.py       scape_oaks.py
        |                            |
        v                            v
colonial_events.json        oaks_events.json
        |                            |
        └────────────┬───────────────┘
                     v
            merge_data.py
                     |
                     v
            all_events.json
                     |
                     v
         transform_events.py
                     |
                     v
        events_formatted.json
                     |
                     v
          inject_events.py
                     |
                     v
      phoenixville_updated.html ⭐
```

## 🛠️ How Each Script Works

### 1. Scrapers (`scrape_*.py`)
- Use `requests` + `BeautifulSoup` to fetch HTML
- Parse event cards from venue websites
- Extract: title, date, image, link, category
- Output: JSON file with raw data

### 2. Merger (`merge_data.py`)
- Reads multiple JSON files
- Combines into single array
- Output: `all_events.json`

### 3. Transformer (`transform_events.py`)
- Converts data schema to match website needs
- Parses dates into readable format ("Feb 5", "Feb 6-8")
- Sorts events chronologically
- Output: `events_formatted.json`

### 4. Injector (`inject_events.py`)
- Reads `phoenixville.html` template
- Finds the `const eventsData = [...]` array
- Replaces it with transformed data
- Output: `phoenixville_updated.html`

## 🎨 Website Features

**Three Main Tabs:**
- **Events** - Browse concerts, shows, expos
- **Dining** - Local restaurants (manually curated for now)
- **Outings** - Curated itineraries with step-by-step guides

**Functionality:**
- 🔍 Search across all content
- 🏷️ Filter by category/type
- 📱 Mobile-first responsive design
- 🗺️ Location badges (Phoenixville, Oaks, Collegeville)
- 🎯 Click to open event links

## 🔮 Future Enhancements

### Short Term
- [ ] Add more venues (West Chester theaters, King of Prussia)
- [ ] Automated dining data (Google Places API?)
- [ ] Better date parsing (handle recurring events)
- [ ] "Happening this weekend" badge

### Medium Term
- [ ] Deploy as static site (Netlify/Vercel)
- [ ] GitHub Actions for daily auto-updates
- [ ] User favorites (localStorage)
- [ ] Export to calendar (.ics files)

### Long Term
- [ ] Backend API (Django/Flask)
- [ ] User accounts + personalized recommendations
- [ ] Event submission form for local businesses
- [ ] Mobile app (React Native)

## 🐛 Debugging

If a scraper isn't working:

1. **Run the debug script:**
   ```bash
   python3 debug_colonial.py  # or debug_oaks.py
   ```

2. **Open the HTML file it creates** (e.g., `colonial_debug.html`)

3. **Search for a known event** in the raw HTML

4. **Find the CSS class** containing that event

5. **Update the scraper** with the correct selector

## 📅 Keeping Data Fresh

Events change constantly. Options for staying updated:

**Manual:**
```bash
python3 update_localspot.py
```

**Automated (Weekly):**
Add to your crontab:
```bash
# Run every Monday at 8am
0 8 * * 1 cd /path/to/localspot && python3 update_localspot.py
```

**GitHub Actions (Recommended for hosted sites):**
Create `.github/workflows/update-events.yml` to auto-update on schedule.

## 🤝 Contributing

Want to add a new venue?

1. Create `scrape_VENUENAME.py` following the existing patterns
2. Add it to `merge_data.py` in the `files_to_merge` list
3. Run `update_localspot.py`
4. Done!

## 📄 License

MIT License - Feel free to use and modify!

## 🙏 Credits

Built with:
- Python (requests, BeautifulSoup4)
- Tailwind CSS
- Font Awesome icons
- Unsplash images

---

**Questions?** Open an issue or contact hello@localspotapp.com

# 🔄 WEEKLY MAINTENANCE GUIDE

## Super Simple Weekly Update

### **Every Week (Takes 2 Minutes):**

1. **Run the update script:**
   ```bash
   cd LocalSpotHQ
   py weekly_update.py
   ```

2. **Upload to Hostinger:**
   - Go to Hostinger File Manager
   - Navigate to `public_html`
   - Delete old `app.html`
   - Upload new `app.html`

3. **Done!** ✅

---

## What the Script Does

The `weekly_update.py` script runs ALL these steps automatically:

1. ✅ Generate recurring events (Farmers Market, First Friday, etc.)
2. ✅ Scrape Colonial Theatre for new shows
3. ✅ Scrape Expo Center for new events
4. ✅ Merge all events together
5. ✅ Format dates properly
6. ✅ Include dining list (19 restaurants)
7. ✅ Include activities list (19 outings)
8. ✅ Include curated plans (13 day plans)
9. ✅ Inject everything into HTML
10. ✅ Remove the landing page

**Result:** Fresh `app.html` ready to upload!

---

## When to Update

**Recommended:** Once per week (Sunday or Monday)

**Why weekly?**
- Colonial Theatre adds new shows
- Expo Center posts new events
- Keeps your site fresh and relevant

**Can do more often?** Yes! Run anytime you want fresh data.

---

## Files You Need (One Time Setup)

Make sure these are in your `LocalSpotHQ` folder:

**Update Scripts (download once):**
- ✅ `weekly_update.py` (the main script - runs everything)
- ✅ `add_date_filters.py` (only need to run once - already done)
- ✅ `inject_data_verified.py` (called by weekly_update)
- ✅ `fix_app_landing_v2.py` (called by weekly_update)

**Pipeline Scripts (you already have these):**
- ✅ `generate_recurring_events.py`
- ✅ `scrape_colonial_v2.py`
- ✅ `scape_oaks.py`
- ✅ `merge_data.py`
- ✅ `transform_events.py`
- ✅ `create_dining_list.py`
- ✅ `create_outings_list.py`
- ✅ `create_curated_plans.py`

**Template:**
- ✅ `phoenixville.html` (template with date filters)

---

## Troubleshooting

### Script shows error?
- Check internet connection (needs to scrape websites)
- Make sure all scripts are in LocalSpotHQ folder
- Run `py diagnose_pipeline.py` to check files

### Upload not working?
- Make sure you're in `public_html` folder
- Delete old `app.html` first
- Check file uploaded successfully (should be ~150KB)

### Site still shows old events?
- Clear browser cache (Ctrl + Shift + Delete)
- Try in incognito mode
- Check you uploaded to correct folder

---

## Quick Reference

**Weekly Update:**
```bash
cd LocalSpotHQ
py weekly_update.py
```

**Check Everything is OK:**
```bash
py diagnose_pipeline.py
```

**Manual Update (if weekly_update fails):**
```bash
py generate_recurring_events.py
py scrape_colonial_v2.py
py scape_oaks.py
py merge_data.py
py transform_events.py
py create_dining_list.py
py create_outings_list.py
py create_curated_plans.py
py inject_data_verified.py
py fix_app_landing_v2.py
```

---

## File You Upload

After running `weekly_update.py`, upload:
- **`app.html`** → Goes to Hostinger `public_html/app.html`

**Don't upload:**
- ❌ `phoenixville.html` (template)
- ❌ `phoenixville_updated.html` (has landing page)
- ❌ Any `.py` files
- ❌ Any `.json` files

---

## One-Time Tasks (Already Done)

You only needed to do these once:
- ✅ Add date filters (`py add_date_filters.py`)
- ✅ Create template
- ✅ Set up scrapers
- ✅ Upload `index.html`, `sitemap.xml`, `robots.txt`

**You never need to run these again!**

---

## Remember

✨ **One command = Fresh site**
```bash
py weekly_update.py
```

Then upload `app.html` and you're done! 🚀

---

## Support

If something breaks:
- Run `py diagnose_pipeline.py` to see what's wrong
- Check error messages
- Make sure internet is working
- Restart command prompt and try again

---

**That's it! Keep LocalSpot fresh with one command per week.** 💙

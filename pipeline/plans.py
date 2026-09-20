"""Plans: ready-made itineraries (/plans/<slug>/) rendered from
data/<area>/plans.json. A plan is a timed sequence of stops (dinner, a show,
a nightcap) with a budget and tips. They are evergreen like guides and rank
for intent searches ("date night in Phoenixville"), which is why each one is
its own page rather than a tile with nowhere to go."""

import html
import json
import os
import shutil
from datetime import date
from pipeline.analytics import GA_SNIPPET


def load_plans(plans_file):
    if not plans_file or not os.path.exists(plans_file):
        return []
    with open(plans_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def plan_slug(plan):
    """URL slug for a plan. The data uses snake_case ids; URLs use hyphens.
    An explicit `slug` wins so a renamed plan can keep its URL."""
    return plan.get('slug') or plan['id'].replace('_', '-')


_STYLE = """
body{max-width:680px;margin:0 auto;padding:24px 16px}
.crumb{font-size:13px;color:var(--ink-faint)}
.crumb a{color:var(--ink-faint);text-decoration:none}
.sub{color:var(--ink-soft);margin-top:2px;font-size:15px}
h1{font-size:clamp(26px,5vw,36px)}
main,article{font-family:var(--article);font-size:18px;line-height:1.65}
article h2{font-family:var(--display);font-size:22px;margin:1.7em 0 .5em}
article a{color:var(--cool)}
.facts{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;
font-family:var(--body);font-size:14px;margin:18px 0 6px;padding:0;list-style:none}
.facts li{background:var(--surface);border-radius:var(--radius);padding:10px 12px}
.facts b{display:block;font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:var(--ink-faint)}
ol.steps{list-style:none;padding:0;margin:0}
ol.steps li{position:relative;padding:0 0 22px 28px;border-left:2px solid var(--rule);margin-left:8px}
ol.steps li:last-child{padding-bottom:6px}
ol.steps li::before{content:"";position:absolute;left:-7px;top:8px;width:12px;height:12px;
border-radius:50%;background:var(--now);border:2px solid var(--paper)}
.when{font-family:var(--display);font-weight:700;font-size:14px;color:var(--ink-soft)}
.what{font-family:var(--display);font-weight:600;font-size:19px;margin:2px 0}
.meta{font-family:var(--body);font-size:13px;color:var(--ink-faint);margin:0 0 4px}
.notes{margin:0;font-size:16px}
.tip{font-family:var(--body);font-size:15px;background:var(--now-wash);
border-left:3px solid var(--now);border-radius:0 var(--radius) var(--radius) 0;
padding:14px 16px;margin:0 0 1.2em;color:var(--ink-soft)}
ul.plans{list-style:none;padding:0}
ul.plans li{margin-bottom:1.1em}
ul.plans a{font-family:var(--display);font-weight:600;font-size:19px;color:var(--cool)}
footer{margin-top:32px;padding-top:16px;border-top:1px solid var(--rule);
color:var(--ink-faint);font-size:13px}
"""


def _head(title, description, canonical, area_name, og_type, depth, extra_meta='', json_ld=None):
    up = '../' * depth
    ld = (f'<script type="application/ld+json">{json.dumps(json_ld, ensure_ascii=False)}</script>\n'
          if json_ld else '')
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
{GA_SNIPPET}
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(description)}">
<meta name="robots" content="index, follow, max-image-preview:large">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="LocalSpot {html.escape(area_name)}">
<meta property="og:url" content="{canonical}">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(description)}">
{extra_meta}{ld}<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;600;700&family=Newsreader:opsz,wght@6..72,400;6..72,600&display=swap">
<link rel="icon" type="image/png" sizes="192x192" href="{up}icon-192.png">
<link rel="apple-touch-icon" href="{up}icon-180.png">
<link rel="stylesheet" href="{up}localspot.css">
<style>{_STYLE}</style>
</head>
"""


def _step_html(step):
    when = html.escape(str(step.get('time', '')))
    what = html.escape(step.get('activity', ''))
    bits = [step.get('type', ''), step.get('duration', ''), step.get('cost', '')]
    meta = ' &middot; '.join(html.escape(str(b)) for b in bits if b)
    notes = html.escape(step.get('notes', ''))
    return (f'<li><span class="when">{when}</span>'
            f'<p class="what">{what}</p>'
            + (f'<p class="meta">{meta}</p>' if meta else '')
            + (f'<p class="notes">{notes}</p>' if notes else '')
            + '</li>')


def _plan_page(plan, area_config):
    area_name = area_config['name']
    base_url = area_config['meta']['canonical_url'].rstrip('/')
    slug = plan_slug(plan)
    canonical = f"{base_url}/plans/{slug}/"
    title = plan['title']
    description = plan.get('description', '')
    updated = plan.get('updated', date.today().isoformat())
    published = plan.get('published', updated)
    # Stock placeholder images are not shown on the page; og:image falls back
    # to the area card so the share preview still carries a real image.
    og_image = area_config['meta'].get('og_image', '')
    seo_title = plan.get('seo_title', f"{title} in {area_name}")

    json_ld = [{
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": description,
        "datePublished": published,
        "dateModified": updated,
        "image": [og_image] if og_image else [],
        "author": {"@type": "Organization", "name": "LocalSpot HQ", "url": "https://www.localspothq.com/"},
        "publisher": {"@type": "Organization", "name": "LocalSpot HQ"},
        "mainEntityOfPage": canonical
    }, {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": f"LocalSpot {area_name}", "item": f"{base_url}/"},
            {"@type": "ListItem", "position": 2, "name": "Plans", "item": f"{base_url}/plans/"},
            {"@type": "ListItem", "position": 3, "name": title, "item": canonical}
        ]
    }]

    facts = []
    for label, key in (('Takes', 'duration'), ('Budget', 'budget'), ('About', 'total_cost')):
        if plan.get(key):
            facts.append(f'<li><b>{label}</b>{html.escape(str(plan[key]))}</li>')
    if plan.get('best_for'):
        facts.append(f'<li><b>Best for</b>{html.escape(", ".join(plan["best_for"]))}</li>')
    facts_html = f'<ul class="facts">{"".join(facts)}</ul>' if facts else ''

    steps_html = '\n'.join(_step_html(s) for s in plan.get('itinerary', []))
    tips = plan.get('tips', '')
    tips_html = f'<p class="tip">{html.escape(tips)}</p>' if tips else ''

    extra = (f'<meta property="og:image" content="{html.escape(og_image)}">\n' if og_image else '') + \
            f'<meta property="article:published_time" content="{published}">\n' \
            f'<meta property="article:modified_time" content="{updated}">\n' \
            '<meta name="twitter:card" content="summary_large_image">\n'
    head = _head(f"{seo_title} | LocalSpot {area_name}", description, canonical, area_name,
                 'article', depth=2, extra_meta=extra, json_ld=json_ld)

    return head + f"""<body>
<p class="crumb"><a href="{base_url}/">LocalSpot {html.escape(area_name)}</a> &rsaquo; <a href="../">Plans</a></p>
<h1>{html.escape(title)}</h1>
<p class="sub">{html.escape(plan.get('category', 'Plan'))} &middot; updated {updated}</p>
<article>
<p>{html.escape(description)}</p>
{facts_html}
<h2>The plan</h2>
<ol class="steps">
{steps_html}
</ol>
{tips_html}
<p class="meta">Hours, prices and showtimes change. Check the venue before you go, and if something here is wrong, <a href="{base_url}/#community">tell us</a>.</p>
</article>
<footer>LocalSpot HQ &middot; <a href="../">All plans</a> &middot; <a href="{base_url}/">Everything happening in {html.escape(area_name)} &rarr;</a></footer>
</body>
</html>
"""


def _plans_index(plans, area_config):
    area_name = area_config['name']
    base_url = area_config['meta']['canonical_url'].rstrip('/')
    canonical = f"{base_url}/plans/"

    by_cat = {}
    for p in plans:
        by_cat.setdefault(p.get('category', 'Plans'), []).append(p)
    groups = []
    for cat, items in by_cat.items():
        cards = '\n'.join(
            f"""<li><a href="{plan_slug(p)}/">{html.escape(p['title'])}</a>
  <p class="sub">{html.escape(p.get('duration', ''))}{' &middot; ' if p.get('duration') and p.get('budget') else ''}{html.escape(p.get('budget', ''))} &middot; {html.escape(p.get('description', ''))}</p></li>"""
            for p in items)
        groups.append(f'<h2>{html.escape(cat)}</h2>\n<ul class="plans">\n{cards}\n</ul>')

    title = f"{area_name} Date Nights, Family Days &amp; Weekend Plans | LocalSpot"
    description = (f"Ready-made plans for {area_name}, PA: date nights, kids' days out, "
                   f"weekend itineraries and seasonal outings, each with times, stops and a budget.")
    head = _head(html.unescape(title), description, canonical, area_name, 'website', depth=1)
    return head + f"""<body>
<p class="crumb"><a href="{base_url}/">LocalSpot {html.escape(area_name)}</a> &rsaquo; Plans</p>
<h1>Plans</h1>
<p class="sub">Pick one and go. Each plan is a timed sequence of stops with a rough budget.</p>
<article>
{chr(10).join(groups)}
</article>
<footer>LocalSpot HQ &middot; <a href="{base_url}/">Everything happening in {html.escape(area_name)} &rarr;</a></footer>
</body>
</html>
"""


def generate_plan_pages(plans_file, output_dir, area_config):
    plans = load_plans(plans_file)

    plans_dir = os.path.join(output_dir, 'plans')
    if os.path.isdir(plans_dir):
        shutil.rmtree(plans_dir)

    slugs = []
    for plan in plans:
        slug = plan_slug(plan)
        page_dir = os.path.join(plans_dir, slug)
        os.makedirs(page_dir, exist_ok=True)
        with open(os.path.join(page_dir, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(_plan_page(plan, area_config))
        slugs.append(slug)

    if slugs:
        with open(os.path.join(plans_dir, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(_plans_index(plans, area_config))

    print(f">> Plan pages: {len(slugs)} -> {plans_dir}")
    return slugs

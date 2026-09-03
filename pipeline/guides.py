"""Local Guides: evergreen long-form pages (/guides/<slug>/) rendered from
data/<area>/guides.json. These are curation pieces - festival guides, ranked
lists - not news; they change rarely and rank for long-tail searches."""

import html
import json
import os
import shutil
from datetime import date
from pipeline.analytics import GA_SNIPPET


def load_guides(guides_file):
    if not guides_file or not os.path.exists(guides_file):
        return []
    with open(guides_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def _guide_page(guide, area_config):
    area_name = area_config['name']
    base_url = area_config['meta']['canonical_url'].rstrip('/')
    canonical = f"{base_url}/guides/{guide['slug']}/"
    title = guide['title']
    description = guide.get('description', '')
    img = guide.get('img', area_config['meta'].get('og_image', ''))
    updated = guide.get('updated', date.today().isoformat())
    published = guide.get('published', updated)
    # <title> is what the SERP shows and is capped at ~60 chars; the H1 and
    # og:title keep the editorial title, which can run longer.
    seo_title = guide.get('seo_title', title)

    json_ld = [{
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": description,
        "datePublished": published,
        "dateModified": updated,
        "image": [img] if img else [],
        "author": {"@type": "Organization", "name": "LocalSpot HQ", "url": "https://www.localspothq.com/"},
        "publisher": {"@type": "Organization", "name": "LocalSpot HQ"},
        "mainEntityOfPage": canonical
    }, {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": f"LocalSpot {area_name}", "item": f"{base_url}/"},
            {"@type": "ListItem", "position": 2, "name": "Guides", "item": f"{base_url}/guides/"},
            {"@type": "ListItem", "position": 3, "name": title, "item": canonical}
        ]
    }]

    sections_html = '\n'.join(
        f"<h2>{html.escape(s['heading'])}</h2>\n{s['html']}"
        for s in guide.get('sections', []))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
{GA_SNIPPET}
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(seo_title)} | LocalSpot {html.escape(area_name)}</title>
<meta name="description" content="{html.escape(description)}">
<meta name="robots" content="index, follow, max-image-preview:large">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="LocalSpot {html.escape(area_name)}">
<meta property="article:published_time" content="{published}">
<meta property="article:modified_time" content="{updated}">
<meta property="og:url" content="{canonical}">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(description)}">
<meta property="og:image" content="{html.escape(img)}">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">{json.dumps(json_ld, ensure_ascii=False)}</script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;600;700&family=Newsreader:opsz,wght@6..72,400;6..72,600&display=swap">
<link rel="stylesheet" href="../../localspot.css">
<style>
body{{max-width:680px;margin:0 auto;padding:24px 16px}}
.crumb{{font-size:13px;color:var(--ink-faint)}}
.crumb a{{color:var(--ink-faint);text-decoration:none}}
.sub{{color:var(--ink-soft);margin-top:2px;font-size:15px}}
img.hero{{border-radius:var(--radius-lg);margin:16px 0}}
h1{{font-size:clamp(26px,5vw,36px)}}
main,article{{font-family:var(--article);font-size:18px;line-height:1.65}}
article h2{{font-family:var(--display);font-size:22px;margin:1.7em 0 .5em}}
article a{{color:var(--cool)}}
ol li,ul li{{margin-bottom:.5em}}
.tip{{font-family:var(--body);font-size:15px;background:var(--now-wash);
border-left:3px solid var(--now);border-radius:0 var(--radius) var(--radius) 0;
padding:14px 16px;margin:0 0 1.2em;color:var(--ink-soft)}}
.rank{{font-family:var(--display);font-weight:700}}
footer{{margin-top:32px;padding-top:16px;border-top:1px solid var(--rule);
color:var(--ink-faint);font-size:13px}}
</style>
</head>
<body>
<p class="crumb"><a href="{base_url}/">LocalSpot {html.escape(area_name)}</a> &rsaquo; Guides</p>
<h1>{html.escape(title)}</h1>
<p class="sub">{html.escape(guide.get('category', 'Local Guide'))} &middot; updated {updated}</p>
{f'<img class="hero" src="{html.escape(img)}" alt="{html.escape(title)}" referrerpolicy="no-referrer">' if img else ''}
{sections_html}
<footer>LocalSpot HQ &middot; <a href="{base_url}/">Everything happening in {html.escape(area_name)} &rarr;</a></footer>
</body>
</html>
"""


def _guides_index(guides, area_config):
    """Index at /guides/ so the set has a linkable home of its own."""
    area_name = area_config['name']
    base_url = area_config['meta']['canonical_url'].rstrip('/')
    canonical = f"{base_url}/guides/"

    cards = '\n'.join(
        f"""<li>
  <a href="{g['slug']}/">{html.escape(g['title'])}</a>
  <p class="sub">{html.escape(g.get('category', 'Local Guide'))} &middot; {html.escape(g.get('description', ''))}</p>
</li>""" for g in guides)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
{GA_SNIPPET}
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(area_name)} Local Guides: Festivals, Food &amp; Things to Do | LocalSpot</title>
<meta name="description" content="In-depth guides to {html.escape(area_name)}, PA: festival how-tos, ranked restaurant lists and seasonal things to do, written locally and kept current.">
<meta name="robots" content="index, follow">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="website">
<meta property="og:url" content="{canonical}">
<meta property="og:title" content="{html.escape(area_name)} Local Guides | LocalSpot">
<meta property="og:description" content="Festival how-tos, ranked restaurant lists and seasonal things to do in {html.escape(area_name)}, PA.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;600;700&family=Newsreader:opsz,wght@6..72,400;6..72,600&display=swap">
<link rel="stylesheet" href="../localspot.css">
<style>
body{{max-width:680px;margin:0 auto;padding:24px 16px}}
.crumb{{font-size:13px;color:var(--ink-faint)}}
.crumb a{{color:var(--ink-faint);text-decoration:none}}
.sub{{color:var(--ink-soft);margin-top:2px;font-size:15px}}
img.hero{{border-radius:var(--radius-lg);margin:16px 0}}
h1{{font-size:clamp(26px,5vw,36px)}}
main,article{{font-family:var(--article);font-size:18px;line-height:1.65}}
article h2{{font-family:var(--display);font-size:22px;margin:1.7em 0 .5em}}
article a{{color:var(--cool)}}
ol li,ul li{{margin-bottom:.5em}}
.tip{{font-family:var(--body);font-size:15px;background:var(--now-wash);
border-left:3px solid var(--now);border-radius:0 var(--radius) var(--radius) 0;
padding:14px 16px;margin:0 0 1.2em;color:var(--ink-soft)}}
.rank{{font-family:var(--display);font-weight:700}}
footer{{margin-top:32px;padding-top:16px;border-top:1px solid var(--rule);
color:var(--ink-faint);font-size:13px}}
</style>
</head>
<body>
<p class="crumb"><a href="{base_url}/">LocalSpot {html.escape(area_name)}</a> &rsaquo; Guides</p>
<h1>Local Guides</h1>
<ul>
{cards}
</ul>
<footer>LocalSpot HQ &middot; <a href="{base_url}/">Everything happening in {html.escape(area_name)} &rarr;</a></footer>
</body>
</html>
"""


def generate_guide_pages(guides_file, output_dir, area_config):
    guides = load_guides(guides_file)

    guides_dir = os.path.join(output_dir, 'guides')
    if os.path.isdir(guides_dir):
        shutil.rmtree(guides_dir)

    slugs = []
    for guide in guides:
        page_dir = os.path.join(guides_dir, guide['slug'])
        os.makedirs(page_dir, exist_ok=True)
        with open(os.path.join(page_dir, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(_guide_page(guide, area_config))
        slugs.append(guide['slug'])

    # Only emit the index when there's something to list; the footer link is
    # likewise suppressed for areas with no guides yet.
    if slugs:
        with open(os.path.join(guides_dir, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(_guides_index(guides, area_config))

    print(f">> Guide pages: {len(slugs)} -> {guides_dir}")
    return slugs

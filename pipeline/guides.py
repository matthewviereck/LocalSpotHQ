"""Local Guides: evergreen long-form pages (/guides/<slug>/) rendered from
data/<area>/guides.json. These are curation pieces - festival guides, ranked
lists - not news; they change rarely and rank for long-tail searches."""

import html
import json
import os
import shutil
from datetime import date


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

    json_ld = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": description,
        "dateModified": updated,
        "image": [img] if img else [],
        "author": {"@type": "Organization", "name": "LocalSpot HQ", "url": "https://www.localspothq.com/"},
        "publisher": {"@type": "Organization", "name": "LocalSpot HQ"},
        "mainEntityOfPage": canonical
    }

    sections_html = '\n'.join(
        f"<h2>{html.escape(s['heading'])}</h2>\n{s['html']}"
        for s in guide.get('sections', []))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)} | LocalSpot {html.escape(area_name)}</title>
<meta name="description" content="{html.escape(description)}">
<meta name="robots" content="index, follow">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="article">
<meta property="og:url" content="{canonical}">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(description)}">
<meta property="og:image" content="{html.escape(img)}">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">{json.dumps(json_ld, ensure_ascii=False)}</script>
<style>
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;max-width:680px;margin:0 auto;padding:24px 16px;color:#0f172a;line-height:1.65}}
h1{{font-size:1.8rem;line-height:1.25;margin:8px 0 4px}}
h2{{font-size:1.25rem;margin:32px 0 8px}}
.sub{{color:#64748b;margin-top:0;font-size:0.9rem}}
img.hero{{max-width:100%;border-radius:14px;margin:14px 0}}
a{{color:#2563eb;text-decoration:none}}
a:hover{{text-decoration:underline}}
.crumb{{font-size:0.85rem;color:#94a3b8}}
ol li,ul li{{margin-bottom:10px}}
.tip{{background:#eff6ff;border:1px solid #bfdbfe;border-radius:12px;padding:14px 16px;margin:16px 0}}
.rank{{font-weight:800;color:#2563eb}}
footer{{margin-top:40px;color:#94a3b8;font-size:0.8rem;border-top:1px solid #e2e8f0;padding-top:14px}}
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

    print(f">> Guide pages: {len(slugs)} -> {guides_dir}")
    return slugs

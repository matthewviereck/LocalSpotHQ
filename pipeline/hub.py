"""
Build the site root (output/index.html) from the areas' built data.

Until 2026-09-20 the root was the pre-redesign Tailwind template
(web/index.html) with its counts patched in by regex: a startup landing page
("Connect in Real Life", a feature grid, stat pills) that showed nothing that
was actually happening and did not share the town apps' design. Now the root
is rendered here, from the same events and stylesheet the town apps use: a
masthead, each town's next few events, one signup card with a town picker, and
the list of towns. It is the page the network plan needs the root to be: one
block per town, and nothing that has to be rewritten when a town is added.

Run after every area has been built:
    python pipeline/hub.py
"""

import html as _html
import json
import os
import shutil
import sys
from datetime import date, datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from pipeline.analytics import GA_SNIPPET
from pipeline.geo import derive_tagline

SITE_URL = 'https://www.localspothq.com/'
REGION = 'Chester County'
CONTACT = 'contact@localspothq.com'
EVENTS_PER_TOWN = 6
UNDATED = 9e9


def _load(path, default=None):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default if default is not None else []


def area_block(area_id):
    """Everything the root needs to know about one town, from its built data."""
    data_dir = os.path.join(PROJECT_ROOT, 'data', area_id)
    config = _load(os.path.join(PROJECT_ROOT, 'config', f'{area_id}.json'), {})
    events = _load(os.path.join(data_dir, 'generated', 'events_formatted.json'))
    guides = _load(os.path.join(data_dir, 'guides.json'))
    return {
        'slug': config.get('slug', area_id),
        'name': config.get('name', area_id),
        'tagline': derive_tagline(events, config) or config.get('tagline', ''),
        'events': events,
        'guides': [{'slug': g.get('slug', ''), 'title': g.get('title', '')} for g in guides if g.get('slug')],
    }


def upcoming(events, n=EVENTS_PER_TOWN):
    """The next n dated events, soonest first. Runs already open ("Now
    through ...") count as today. Undated rows never make the front page."""
    dated = [e for e in events if isinstance(e.get('_sort_date'), (int, float)) and e['_sort_date'] < UNDATED]
    dated.sort(key=lambda e: e['_sort_date'])
    return dated[:n]


def _short_date(ev, today):
    label = (ev.get('date') or '').strip()
    if label.lower().startswith('now through'):
        return 'Now'
    d = datetime.fromtimestamp(ev['_sort_date']).date()
    if d == today:
        return 'Today'
    return f"{d.strftime('%b')} {d.day}"


def _row(area_slug, ev, today):
    href = f"/{area_slug}/events/{ev['slug']}/" if ev.get('slug') else f"/{area_slug}/"
    meta = ' · '.join(x for x in (ev.get('time', ''), ev.get('loc', '')) if x)
    return (f'<a class="row" href="{_html.escape(href)}">'
            f'<span class="row-time">{_html.escape(_short_date(ev, today))}</span>'
            f'<span class="row-body"><span class="row-title">{_html.escape(ev.get("title", ""))}</span>'
            f'<span class="row-meta">{_html.escape(meta)}</span></span></a>')


def _town_section(block, today):
    slug, name = block['slug'], block['name']
    rows = ''.join(_row(slug, ev, today) for ev in upcoming(block['events']))
    if not rows:
        rows = '<div class="empty"><strong>Nothing listed yet</strong>New events land every morning.</div>'
    links = [f'<a href="/{slug}/">Everything in {_html.escape(name)}</a>',
             f'<a href="/{slug}/this-weekend/">This weekend</a>']
    if block['guides']:
        links.append(f'<a href="/{slug}/guides/">Guides</a>')
    links.append(f'<a href="/{slug}/events.ics">Calendar feed</a>')
    tagline = _html.escape(block['tagline']) if block['tagline'] else ''
    return f"""
        <section class="town" id="{_html.escape(slug)}">
            <div class="section-head">
                <h2>{_html.escape(name)}</h2>
                <a class="more" href="/{slug}/">Everything in {_html.escape(name)} &rarr;</a>
            </div>
            {f'<p class="meta town-tagline">{tagline}</p>' if tagline else ''}
            <div class="card card-pad">{rows}</div>
            <p class="townlinks">{' &middot; '.join(links)}</p>
        </section>"""


def render_hub(blocks, today=None):
    """Pure renderer: a list of area blocks in, the root page out."""
    today = today or date.today()
    names = [b['name'] for b in blocks]
    joined = ' and '.join(names) if len(names) <= 2 else ', '.join(names[:-1]) + ', and ' + names[-1]
    title = f"What's on in {REGION} this week | LocalSpot"
    description = (f"Events in {joined}, PA, gathered from the venues every morning: "
                   f"concerts, markets, festivals, shows, and things to do this weekend.")
    dateline = today.strftime('%A, %B %d').replace(' 0', ' ')
    options = ''.join(f'<option value="{_html.escape(b["name"])}">{_html.escape(b["name"])}</option>' for b in blocks)
    towns_strip = ' &middot; '.join(f'<a href="/{b["slug"]}/">{_html.escape(b["name"])}</a>' for b in blocks)
    sections = ''.join(_town_section(b, today) for b in blocks)
    json_ld = {"@context": "https://schema.org", "@type": "WebSite", "name": "LocalSpot",
               "url": SITE_URL, "description": description}

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
{GA_SNIPPET}
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_html.escape(title)}</title>
<meta name="description" content="{_html.escape(description)}">
<meta name="robots" content="index, follow">
<link rel="canonical" href="{SITE_URL}">
<meta property="og:type" content="website">
<meta property="og:url" content="{SITE_URL}">
<meta property="og:title" content="{_html.escape(title)}">
<meta property="og:description" content="{_html.escape(description)}">
<meta property="og:image" content="{SITE_URL}images/og-image.png">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">{json.dumps(json_ld, ensure_ascii=False)}</script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;600;700&family=Newsreader:opsz,wght@6..72,400;6..72,600&display=swap">
<link rel="icon" type="image/png" sizes="192x192" href="/icon-192.png">
<link rel="apple-touch-icon" href="/icon-180.png">
<link rel="stylesheet" href="/localspot.css">
<style>
.topbar {{ position: sticky; top: 0; z-index: 40; background: var(--chrome); border-bottom: 1px solid var(--rule); }}
.topbar-in {{ max-width: var(--wrap-wide); margin: 0 auto; padding: 10px 16px; display: flex; align-items: center; gap: 12px; }}
.brand {{ font-family: var(--display); font-weight: 700; font-size: 18px; letter-spacing: -.02em; text-decoration: none; color: var(--ink); display: flex; align-items: center; gap: 7px; }}
.brand-mark {{ width: 22px; height: 22px; border-radius: 5px; background: var(--now); padding: 3px; box-sizing: border-box; flex: none; }}
.brand-town {{ font-family: var(--display); font-size: 12px; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; color: var(--ink-faint); padding-top: 3px; }}
.topbar-actions {{ margin-left: auto; display: flex; gap: 8px; align-items: center; }}
main {{ padding-top: 22px; }}
.masthead {{ padding: 4px 0 18px; }}
.masthead h1 {{ font-size: clamp(26px, 6.5vw, 38px); }}
.masthead .dateline {{ font-family: var(--display); font-size: 12px; font-weight: 600; letter-spacing: .12em; text-transform: uppercase; color: var(--now); margin: 0 0 6px; }}
.town-tagline {{ margin: -6px 0 12px; }}
.townlinks {{ font-size: 14px; margin: 10px 0 0; color: var(--ink-faint); }}
.townlinks a {{ color: var(--ink-soft); }}
.signup-pick {{ display: grid; gap: 8px; grid-template-columns: 1fr; }}
@media (min-width: 560px) {{ .signup-pick {{ grid-template-columns: auto 1fr auto; }} }}
.signup-pick select {{ font-family: var(--body); font-size: 16px; padding: 9px 12px; border: 1px solid var(--rule); border-radius: var(--radius); background: var(--surface); color: var(--ink); }}
.signup-pick input {{ min-width: 0; font-family: var(--body); font-size: 16px; padding: 9px 12px; border: 1px solid var(--rule); border-radius: var(--radius); background: var(--surface); color: var(--ink); }}
footer {{ border-top: 1px solid var(--rule); margin-top: 36px; padding: 22px 0 30px; font-size: 13px; color: var(--ink-faint); }}
footer a {{ color: var(--ink-soft); }}
.footlinks {{ display: flex; flex-wrap: wrap; gap: 14px; margin-bottom: 10px; }}
</style>
</head>
<body>

<header class="topbar">
    <div class="topbar-in">
        <a class="brand" href="/"><svg class="brand-mark" viewBox="0 0 24 24" aria-hidden="true"><path fill="#fff" d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5a2.5 2.5 0 1 1 0-5 2.5 2.5 0 0 1 0 5z"/></svg>LocalSpot</a>
        <span class="brand-town">{_html.escape(REGION)}</span>
        <div class="topbar-actions">
            <a class="btn btn-sm" href="/submit.html">Submit an event</a>
        </div>
    </div>
</header>

<main class="wrap">
    <div class="masthead">
        <p class="dateline">{_html.escape(dateline)}</p>
        <h1>What&rsquo;s on in {_html.escape(REGION)} this week</h1>
        <p class="lede">Events in {_html.escape(joined)}, gathered from the venues every morning. Pick your town.</p>
        <p class="meta" style="margin-top:8px;">{towns_strip}</p>
    </div>

    <div class="stack stack-lg">
        {sections}

        <section id="signup">
            <div class="card card-pad">
                <p class="eyebrow">The Thursday email</p>
                <p class="meta" style="margin:6px 0 10px;">What&rsquo;s on in your town this week, every Thursday morning. One click to leave.</p>
                <form class="signup-pick" id="signup-form">
                    <select id="signup-town" aria-label="Town">{options}</select>
                    <input type="email" id="signup-email" placeholder="you@example.com" required autocomplete="email" aria-label="Email address">
                    <button type="submit" class="btn btn-primary">Sign up</button>
                </form>
                <p class="meta" id="signup-done" hidden>You&rsquo;re on the list. First email arrives Thursday.</p>
            </div>
        </section>

        <section id="towns">
            <div class="section-head"><h2>Towns</h2></div>
            <p class="meta">{towns_strip}. More towns are coming. Want yours? Write to <a href="mailto:{CONTACT}">{CONTACT}</a>.</p>
        </section>
    </div>
</main>

<footer class="wrap">
    <div class="footlinks">
        {towns_strip}
        <a href="/submit.html">Submit an event</a>
        <a href="mailto:{CONTACT}">{CONTACT}</a>
    </div>
    <p class="meta">LocalSpot HQ &middot; Viereck Group LLC &middot; updated {today.isoformat()}</p>
</footer>

<script>
(function () {{
    var f = document.getElementById("signup-form");
    if (!f) return;
    f.addEventListener("submit", function (ev) {{
        ev.preventDefault();
        var i = document.getElementById("signup-email"), t = document.getElementById("signup-town"),
            b = f.querySelector("button"), d = document.getElementById("signup-done");
        var email = (i.value || "").trim();
        if (!email) return;
        b.disabled = true;
        fetch("/subscribe.php", {{ method: "POST", headers: {{ "Content-Type": "application/json" }},
               body: JSON.stringify({{ email: email, source: t.value || "hub" }}) }})
            .then(function (r) {{ return r.json(); }})
            .then(function (o) {{ if (!o.success) throw new Error(o.error || "failed"); f.hidden = true; d.hidden = false; }})
            .catch(function () {{ b.disabled = false; d.textContent = "Couldn't sign you up just now. Try again in a minute."; d.hidden = false; }});
    }});
}})();
</script>
</body>
</html>
"""


def build_hub(output_file=None):
    registry = _load(os.path.join(PROJECT_ROOT, 'config', 'areas.json'), {})
    areas = [a for a in registry.get('areas', []) if a.get('enabled')]
    blocks = [area_block(a['id']) for a in areas]
    html = render_hub(blocks)

    output_file = output_file or os.path.join(PROJECT_ROOT, 'output', 'index.html')
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    for b in blocks:
        print(f"   {b['name']}: {len(b['events'])} events, {len(upcoming(b['events']))} on the front page")
    print(f">> Hub page: {output_file} ({len(blocks)} towns)")
    return output_file


def emit_root_css(output_dir=None):
    """The root page links /localspot.css; each area ships its own copy inside
    its folder, so the root needs one at the docroot too."""
    output_dir = output_dir or os.path.join(PROJECT_ROOT, 'output')
    os.makedirs(output_dir, exist_ok=True)
    shutil.copy(os.path.join(PROJECT_ROOT, 'assets', 'localspot.css'), os.path.join(output_dir, 'localspot.css'))
    print(f">> Root stylesheet: localspot.css -> {output_dir}")


def build_sitemap_index(output_file=None):
    """
    Emit a sitemap index at the site root pointing at each area's sitemap.

    The hand-written root sitemap.xml listed 3 URLs and was last read by Google
    in March, so only 2 pages were ever indexed while ~220 live pages sat in
    per-area sitemaps nothing referenced. An index means the one sitemap
    already registered in Search Console reaches all of them, and stays correct
    as areas and events come and go.
    """
    registry = _load(os.path.join(PROJECT_ROOT, 'config', 'areas.json'), {})
    today = date.today().isoformat()

    entries = []
    for area in registry.get('areas', []):
        if not area.get('enabled'):
            continue
        config = _load(os.path.join(PROJECT_ROOT, 'config', f"{area['id']}.json"), {})
        base = config.get('meta', {}).get('canonical_url', '').rstrip('/')
        if not base:
            continue
        entries.append(f"  <sitemap>\n    <loc>{base}/sitemap.xml</loc>\n"
                       f"    <lastmod>{today}</lastmod>\n  </sitemap>")

    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           + '\n'.join(entries) + '\n</sitemapindex>\n')

    output_file = output_file or os.path.join(PROJECT_ROOT, 'output', 'sitemap.xml')
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(xml)
    print(f">> Sitemap index: {len(entries)} area sitemaps -> {output_file}")
    return output_file


def build_robots(output_file=None):
    """robots.txt naming every sitemap, so crawlers find them without GSC."""
    registry = _load(os.path.join(PROJECT_ROOT, 'config', 'areas.json'), {})
    lines = ['User-agent: *', 'Allow: /', '',
             'Sitemap: https://www.localspothq.com/sitemap.xml']
    for area in registry.get('areas', []):
        if not area.get('enabled'):
            continue
        config = _load(os.path.join(PROJECT_ROOT, 'config', f"{area['id']}.json"), {})
        base = config.get('meta', {}).get('canonical_url', '').rstrip('/')
        if base:
            lines.append(f'Sitemap: {base}/sitemap.xml')

    output_file = output_file or os.path.join(PROJECT_ROOT, 'output', 'robots.txt')
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print(f">> robots.txt: {len(lines) - 4} area sitemaps -> {output_file}")
    return output_file


ROOT_ICONS = ['favicon.ico', 'icon-192.png', 'icon-180.png', 'icon-512.png']


def emit_root_icons(output_dir=None):
    """Copy the site icon set to the docroot. Each area ships its own copy for
    its PWA scope, but the hub page (and any browser probing /favicon.ico)
    needs them at the root too, or the hub shows a blank tab icon while the
    area pages show the map pin."""
    output_dir = output_dir or os.path.join(PROJECT_ROOT, 'output')
    os.makedirs(output_dir, exist_ok=True)
    src_dir = os.path.join(PROJECT_ROOT, 'assets', 'pwa')
    for name in ROOT_ICONS:
        shutil.copy(os.path.join(src_dir, name), os.path.join(output_dir, name))
    print(f">> Root icons: {', '.join(ROOT_ICONS)} -> {output_dir}")


if __name__ == '__main__':
    build_hub()
    emit_root_css()
    emit_root_icons()
    build_sitemap_index()
    build_robots()

"""Emit each area's "Promote this event" page (output/<area>/promote/).

The offer: a paid pin to the top of the town feed for `days` days, a slot at
the top of the Thursday email, and one post on the area's Facebook page.

How the money and the pin connect, none of it through the build:
  1. Every event page links to  /<area>/promote/?event=<slug>
  2. That page sends the buyer to the Stripe Payment Link from
     config/promote.json with  ?client_reference_id=<area-slug>__<event-slug>
     (event slugs never contain an underscore, so the split is unambiguous)
  3. Stripe POSTs checkout.session.completed to /promote_webhook.php, which
     appends the purchase to ../promoted_log.json (private) and rewrites
     /promoted.json (public, active pins only: {area, slug, from, until})
  4. The app, and the Thursday digest, read /promoted.json at run time and
     put those events first with a "Promoted" chip

So a purchase is live within seconds, not at the next 6:15 AM build, and the
build never has to know who paid. While payment_link is empty the page still
ships: it explains the offer and collects interest through /subscribe.php.
"""

import html
import json
import os

from pipeline.analytics import GA_SNIPPET

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(_ROOT, 'config', 'promote.json')
DEFAULTS = {'price_label': '$19', 'days': 7, 'payment_link': '', 'contact_email': ''}


def load_promote_config(path=CONFIG_FILE):
    cfg = dict(DEFAULTS)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        cfg.update({k: v for k, v in data.items() if k in DEFAULTS})
    return cfg


def reference_id(area_slug, event_slug):
    """The client_reference_id Stripe hands back to the webhook."""
    return f"{area_slug}__{event_slug}"


def _catalog(events):
    """slug -> {title, date} for the events currently on the site, so the
    promote page can name the event the buyer tapped through from."""
    out = {}
    for ev in events:
        slug = ev.get('slug')
        if slug and slug not in out:
            out[slug] = {'title': ev.get('title', ''), 'date': ev.get('date', ''),
                         'loc': ev.get('loc', '')}
    return out


def generate_promote_page(events_file, output_dir, area_config, promote=None):
    promote = promote or load_promote_config()
    area_name = area_config['name']
    area_slug = area_config.get('slug') or area_config.get('id', '')
    base_url = area_config['meta']['canonical_url'].rstrip('/')
    canonical = f"{base_url}/promote/"
    price = promote['price_label']
    days = int(promote['days'])
    link = (promote.get('payment_link') or '').strip()
    contact = (promote.get('contact_email') or '').strip()

    events = []
    if events_file and os.path.exists(events_file):
        with open(events_file, 'r', encoding='utf-8') as f:
            events = json.load(f)
    catalog = _catalog(events)

    title = f"Promote your event in {area_name} | LocalSpot"
    description = (f"Put your event at the top of LocalSpot {area_name} for {days} days, "
                   f"in the Thursday email and on the Facebook page. {price}, no account needed.")

    if link:
        pay_block = f"""<p><a class="cta" id="pay" href="{html.escape(link)}">Promote it for {html.escape(price)} &rarr;</a></p>
<p class="meta">Secure checkout by Stripe. Card, Apple Pay or Google Pay. You get a receipt by email.</p>"""
    else:
        pay_block = f"""<div class="card card-pad">
<p class="eyebrow">Opening soon</p>
<p class="meta" style="margin:6px 0 10px;">Promotion is not switched on yet. Leave your email and we'll tell you the day it is live.</p>
<form class="signup" id="signup-form"><input type="email" id="signup-email" placeholder="you@example.com" required autocomplete="email" aria-label="Email address"><button type="submit" class="btn btn-primary">Tell me</button></form>
<p class="meta" id="signup-done" hidden>Got it. You'll hear from us when promotion opens.</p>
</div>"""

    contact_html = (f'<p class="meta">Questions or a refund: <a href="mailto:{html.escape(contact)}">{html.escape(contact)}</a>.</p>'
                    if contact else '')

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
{GA_SNIPPET}
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(description)}">
<meta name="robots" content="index, follow">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="website">
<meta property="og:url" content="{canonical}">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(description)}">
<meta property="og:image" content="{html.escape(area_config['meta'].get('og_image', ''))}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;600;700&family=Newsreader:opsz,wght@6..72,400;6..72,600&display=swap">
<link rel="icon" type="image/png" sizes="192x192" href="../icon-192.png">
<link rel="apple-touch-icon" href="../icon-180.png">
<link rel="stylesheet" href="../localspot.css">
<style>
body{{max-width:680px;margin:0 auto;padding:24px 16px}}
.crumb{{font-size:13px;color:var(--ink-faint)}}
.crumb a{{color:var(--ink-faint);text-decoration:none}}
.sub{{color:var(--ink-soft);margin-top:2px;font-size:15px}}
a{{color:var(--cool)}}
.cta{{display:inline-block;margin-top:8px;background:var(--now);color:#fff;
padding:12px 20px;border-radius:var(--radius);font-weight:600;font-family:var(--display);
text-decoration:none;font-size:16px}}
.pick{{margin:20px 0}}
.pick .title{{font-family:var(--display);font-size:20px;font-weight:600;margin:4px 0 2px}}
ul.gets{{padding-left:20px;line-height:1.6}}
h2{{font-size:18px;margin-top:28px}}
footer{{margin-top:32px;padding-top:16px;border-top:1px solid var(--rule);
color:var(--ink-faint);font-size:13px}}
</style>
</head>
<body>
<p class="crumb"><a href="{base_url}/">LocalSpot {html.escape(area_name)}</a> &rsaquo; Promote</p>
<h1>Promote your event</h1>
<p class="sub">{html.escape(price)} puts it at the top of {html.escape(area_name)} for {days} days.</p>

<div class="card card-pad pick" id="pick">
<p class="eyebrow">Your event</p>
<p class="title" id="pick-title">Pick an event first</p>
<p class="meta" id="pick-meta">Find it on <a href="{base_url}/#events">the events list</a> and tap <strong>Promote this event</strong> on its page. Not listed yet? <a href="../submit.html">Add it free</a> first; it shows up after the next morning build.</p>
</div>

{pay_block}

<h2>What you get</h2>
<ul class="gets">
<li><strong>Pinned at the top</strong> of Today and Events on LocalSpot {html.escape(area_name)} for {days} days, marked "Promoted".</li>
<li><strong>First in the Thursday email</strong> to everyone signed up for {html.escape(area_name)}.</li>
<li><strong>One post</strong> on the LocalSpot {html.escape(area_name)} Facebook page.</li>
</ul>

<h2>How it works</h2>
<ul class="gets">
<li>The pin goes live the moment payment clears and runs {days} days from today, including today.</li>
<li>Your listing itself stays exactly as it is. Promotion changes where it sits, not what it says.</li>
<li>One event per purchase. Promoting a second event is a second purchase.</li>
</ul>
{contact_html}

<footer>LocalSpot HQ &middot; <a href="{base_url}/">Everything happening in {html.escape(area_name)} &rarr;</a></footer>

<script>
(function () {{
    var catalog = {json.dumps(catalog, ensure_ascii=False)};
    var areaSlug = {json.dumps(area_slug)};
    var payLink = {json.dumps(link)};
    var slug = (new URLSearchParams(location.search).get("event") || "").replace(/[^a-z0-9-]/g, "");
    var ev = slug ? catalog[slug] : null;
    var t = document.getElementById("pick-title"), m = document.getElementById("pick-meta");
    if (ev) {{
        t.textContent = ev.title;
        m.textContent = [ev.date, ev.loc].filter(Boolean).join(" \\u00b7 ");
        var pay = document.getElementById("pay");
        if (pay && payLink) {{
            pay.href = payLink + (payLink.indexOf("?") > -1 ? "&" : "?")
                     + "client_reference_id=" + encodeURIComponent(areaSlug + "__" + slug);
        }}
    }} else {{
        var pay2 = document.getElementById("pay");
        if (pay2) {{ pay2.style.opacity = "0.5"; pay2.setAttribute("aria-disabled", "true");
                   pay2.addEventListener("click", function (e) {{ e.preventDefault(); t.scrollIntoView(); }}); }}
    }}
    var f = document.getElementById("signup-form");
    if (f) {{
        f.addEventListener("submit", function (e) {{
            e.preventDefault();
            var i = document.getElementById("signup-email"), b = f.querySelector("button"), d = document.getElementById("signup-done");
            var email = (i.value || "").trim();
            if (!email) return;
            b.disabled = true;
            fetch("/subscribe.php", {{ method: "POST", headers: {{ "Content-Type": "application/json" }},
                   body: JSON.stringify({{ email: email, source: ("promote:" + (slug || areaSlug)).slice(0, 50) }}) }})
                .then(function (r) {{ return r.json(); }})
                .then(function (o) {{ if (!o.success) throw new Error(o.error || "failed"); f.hidden = true; d.hidden = false; }})
                .catch(function () {{ b.disabled = false; d.textContent = "That didn't go through. Try again in a minute."; d.hidden = false; }});
        }});
    }}
}})();
</script>
</body>
</html>
"""
    out_dir = os.path.join(output_dir, 'promote')
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(page)
    print(f">> Promote page: {canonical} ({'pay link set' if link else 'no pay link, interest form'})")
    return 'promote'

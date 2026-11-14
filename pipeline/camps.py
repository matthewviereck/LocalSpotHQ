"""Summer camp week planner (/camps/), rendered from data/<area>/camps.json.

One page: every day camp near the area for the coming summer, laid out week by
week. A parent taps the weeks they want; the strip at the top shows the gaps,
the season estimate and the next sign up date. Picks stay in the parent's own
browser (localStorage). No accounts, nothing about a child is sent anywhere.

The data is hand checked. Each camp carries the page its facts came from and
the date read. Until a camp posts the new season, its last season's weeks are
moved onto the new grid as the same week of summer (plus 364 days, so Monday
stays Monday) and drawn dashed, labelled as last year's schedule.

The page is noindex and left out of the sitemap until the data file says
"live": true, so merging the branch never puts a half-filled page in search.
Clicks out to each camp are counted in GA4 (event `camp_click`, param
`camp_id`) from the production hostname only, so camps can be sent their own
number at the end of the sign up season.
"""

import html
import json
import os
import shutil
from datetime import date, timedelta

from pipeline.analytics import GA_SNIPPET

INDEX_DIR = 'camps'
DAY_LABEL = {'full': 'Full day', 'half': 'Half day', 'both': 'Full or half day'}


def load_camps(camps_file):
    if not camps_file or not os.path.exists(camps_file):
        return None
    with open(camps_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def grid_weeks(data):
    start = date.fromisoformat(data['grid_start'])
    return [start + timedelta(weeks=i) for i in range(int(data['grid_weeks']))]


def camp_weeks(camp, data):
    """(indexes on the grid, weeks outside it). Last season's Mondays move to
    the same week of summer this season: +364 days keeps the weekday."""
    season = int(data['season'])
    shift = timedelta(days=364 * (season - int(camp['weeks_year'])))
    grid = grid_weeks(data)
    index = {d: i for i, d in enumerate(grid)}
    on, off = [], 0
    for iso in camp['weeks']:
        d = date.fromisoformat(iso) + shift
        if d in index:
            on.append(index[d])
        else:
            off += 1
    return sorted(set(on)), off


def basis(camp, data):
    if int(camp['weeks_year']) == int(data['season']):
        return 'posted' if camp.get('year_printed', True) else 'noyear'
    return 'last'


def validate(data):
    """Problems that would put a wrong fact or a broken week on the page."""
    problems = []
    seen = set()
    grid = grid_weeks(data)
    if grid[0].weekday() != 0:
        problems.append('grid_start is not a Monday')
    for c in data.get('camps', []):
        cid = c.get('id', '?')
        cp = []
        if cid in seen:
            cp.append('duplicate id')
        seen.add(cid)
        for field in ('name', 'town', 'ages', 'day', 'hours', 'price', 'signup',
                      'link', 'source', 'checked', 'weeks', 'weeks_year'):
            if c.get(field) in (None, '', []):
                cp.append(f'missing {field}')
        if c.get('day') not in DAY_LABEL:
            cp.append('day must be full, half or both')
        for url_field in ('link', 'source'):
            if not str(c.get(url_field, '')).startswith('https://'):
                cp.append(f'{url_field} is not an https link')
        for iso in c.get('weeks', []):
            try:
                if date.fromisoformat(iso).weekday() != 0:
                    cp.append(f'week {iso} is not a Monday')
            except ValueError:
                cp.append(f'week {iso} is not a date')
        if c.get('key_date'):
            try:
                date.fromisoformat(c['key_date'])
            except ValueError:
                cp.append('key_date is not a date')
            if not c.get('key_date_label'):
                cp.append('key_date without a label')
        pw = c.get('price_week')
        if pw is not None and (isinstance(pw, bool) or not isinstance(pw, (int, float))):
            cp.append('price_week must be a number or null')
        if not cp and not camp_weeks(c, data)[0]:
            cp.append('no week falls on the grid')
        problems.extend(f'{cid}: {p}' for p in cp)
    return problems


def _short(d):
    return f"{d.strftime('%b')} {d.day}"


def _long(iso):
    d = date.fromisoformat(iso)
    return f"{d.strftime('%B')} {d.day}, {d.year}"


def _card(camp, data, grid):
    e = html.escape
    on, off = camp_weeks(camp, data)
    b = basis(camp, data)
    status = {
        'posted': ('posted', f"{data['season']} dates posted"),
        'noyear': ('posted', f"{data['season']} dates (no year on the page)"),
        'last': ('last', f"{camp['weeks_year']} schedule; {data['season']} not posted yet"),
    }[b]
    weeks = []
    for i, d in enumerate(grid):
        label = _short(d)
        if i in on:
            weeks.append(f'<button type="button" class="wk {b}" data-w="{i}" aria-pressed="false" '
                         f'aria-label="Week of {label}: add">{label}</button>')
        else:
            weeks.append(f'<span class="wk none" aria-hidden="true">{label}</span>')
    extra = (f'<p class="extra">Also runs {off} week{"s" if off != 1 else ""} outside this grid.</p>'
             if off else '')
    rules = []
    if camp.get('whole_session'):
        rules.append('Whole session only: picking one week picks them all.')
    if camp.get('min_weeks'):
        rules.append(f"Sold in blocks of {camp['min_weeks']} weeks or more.")
    rule_html = f'<p class="rule">{" ".join(e(r) for r in rules)}</p>' if rules else ''
    featured = '<span class="tag feat">Featured</span>' if camp.get('featured') else ''
    note = f'<p class="note">{e(camp["note"])}</p>' if camp.get('note') else ''
    attrs = {
        'data-id': camp['id'], 'data-town': camp['town'], 'data-day': camp['day'],
        'data-amin': camp.get('age_min') if camp.get('age_min') is not None else '',
        'data-amax': camp.get('age_max') if camp.get('age_max') is not None else '',
        'data-price': camp.get('price_week') if camp.get('price_week') is not None else '',
        'data-weeks': ' '.join(str(i) for i in on),
    }
    attr_html = ' '.join(f'{k}="{e(str(v))}"' for k, v in attrs.items())
    return f"""<article class="camp" id="camp-{e(camp['id'])}" {attr_html}>
  <div class="tags">{featured}<span class="tag {status[0]}">{e(status[1])}</span><span class="tag">{e(DAY_LABEL[camp['day']])}</span></div>
  <h2><a href="{e(camp['link'])}" data-out="link" target="_blank" rel="noopener">{e(camp['name'])}</a></h2>
  <p class="where">{e(camp['town'])} &middot; {camp['miles']} mi &middot; {e(camp.get('place', ''))}</p>
  <dl>
    <dt>Ages</dt><dd>{e(camp['ages'])}</dd>
    <dt>Hours</dt><dd>{e(camp['hours'])}</dd>
    <dt>Before and after care</dt><dd>{e(camp.get('care') or 'Not posted')}</dd>
    <dt>Price</dt><dd>{e(camp['price'])}</dd>
    <dt>Sign up</dt><dd>{e(camp['signup'])}</dd>
  </dl>
  {note}
  <div class="weeks" role="group" aria-label="Weeks {e(camp['name'])} runs">{''.join(weeks)}</div>
  {extra}{rule_html}
  <p class="src">Checked {_long(camp['checked'])} &middot; <a href="{e(camp['source'])}" data-out="source" target="_blank" rel="noopener">source</a> &middot; run by {e(camp.get('organizer', camp['name']))}</p>
</article>"""


def _client_data(data, grid):
    camps = []
    for c in data['camps']:
        on, _ = camp_weeks(c, data)
        camps.append({
            'id': c['id'], 'name': c['name'], 'day': c['day'], 'weeks': on,
            'price': c.get('price_week'), 'whole': bool(c.get('whole_session')),
            'min': c.get('min_weeks') or 1, 'keyDate': c.get('key_date'),
            'keyLabel': c.get('key_date_label', ''), 'link': c['link'],
        })
    return {
        'season': data['season'],
        'weeks': [{'iso': d.isoformat(), 'label': _short(d)} for d in grid],
        'camps': camps,
    }


_STYLE = """
body{max-width:var(--wrap);margin:0 auto;padding:24px 16px 120px}
.crumb{font-size:13px;color:var(--ink-faint)}
.crumb a{color:var(--ink-faint);text-decoration:none}
h1{font-size:clamp(26px,5vw,36px);margin:.2em 0 .3em}
.lede{font-size:16px;color:var(--ink-soft);line-height:1.55;margin:0 0 .8em}
.small{font-size:13px;color:var(--ink-faint);line-height:1.5}
.plan{position:sticky;top:0;z-index:5;background:var(--paper);padding:10px 0 12px;
  border-bottom:1px solid var(--rule);margin:16px 0 12px}
.strip{display:grid;grid-template-columns:repeat(11,1fr);gap:3px}
.strip button{font:600 11px/1.1 var(--body);padding:6px 0;border:1px solid var(--rule);
  border-radius:6px;background:var(--surface);color:var(--ink-soft);cursor:pointer;min-height:44px}
.strip button b{display:block;font-size:13px;color:var(--ink)}
.strip button.cov{background:var(--good-wash);border-color:var(--good);color:var(--good)}
.strip button.cov b{color:var(--good)}
.strip button.halfcov{background:var(--good-wash);border-style:dashed}
.strip button.sel{outline:2px solid var(--now);outline-offset:1px}
.line{margin:8px 0 0;font-size:14px;color:var(--ink-soft)}
.line strong{color:var(--ink)}
.detail{font-size:14px;color:var(--ink-soft);line-height:1.5;margin:0 0 14px}
.detail p{margin:0 0 4px}
.detail p:empty{display:none}
.detail strong{color:var(--ink)}
.warn{color:var(--ink)}
.next{font-size:13px}
.filters{display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin:0 0 12px}
@media (min-width:560px){.filters{grid-template-columns:repeat(4,1fr)}}
.filters label{font-size:12px;color:var(--ink-faint);display:block}
.filters select{width:100%;font:15px var(--body);padding:8px;border:1px solid var(--rule);
  border-radius:8px;background:var(--paper);color:var(--ink);min-height:40px}
.bar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:0 0 14px;font-size:14px;color:var(--ink-soft)}
.bar button{font:600 13px var(--body);padding:8px 12px;border-radius:8px;border:1px solid var(--rule);
  background:var(--paper);color:var(--ink);cursor:pointer;min-height:40px}
.camp{background:var(--surface);border-radius:var(--radius-lg);padding:16px;margin:0 0 14px}
.camp h2{font-size:20px;margin:6px 0 2px;line-height:1.25}
.camp h2 a{color:var(--ink);text-decoration:none}
.camp h2 a:hover{text-decoration:underline}
.where{font-size:13px;color:var(--ink-faint);margin:0 0 8px}
.tags{display:flex;flex-wrap:wrap;gap:6px}
.tag{font:600 11px var(--body);letter-spacing:.02em;padding:3px 8px;border-radius:999px;
  background:var(--paper);color:var(--ink-soft);border:1px solid var(--rule)}
.tag.posted{background:var(--good-wash);color:var(--good);border-color:transparent}
.tag.last{background:var(--surface-sunk);color:var(--ink-soft);border-color:transparent}
.tag.feat{background:var(--now-wash);color:var(--now);border-color:transparent}
dl{display:grid;grid-template-columns:max-content 1fr;gap:4px 12px;font-size:14px;margin:8px 0}
dt{color:var(--ink-faint)}
dd{margin:0;color:var(--ink)}
.note{font-size:14px;color:var(--ink-soft);margin:6px 0 10px;line-height:1.5}
.weeks{display:grid;grid-template-columns:repeat(6,1fr);gap:4px;margin:8px 0 4px}
@media (min-width:560px){.weeks{grid-template-columns:repeat(11,1fr)}}
.wk{font:600 12px var(--body);text-align:center;padding:9px 0;border-radius:6px;min-height:40px;
  display:flex;align-items:center;justify-content:center}
button.wk{border:1.5px solid var(--now);background:var(--paper);color:var(--now);cursor:pointer}
button.wk.last{border-style:dashed}
button.wk[aria-pressed="true"]{background:var(--now);color:var(--paper)}
.wk.none{color:var(--ink-faint);opacity:.45;border:1px solid transparent;text-decoration:line-through}
.extra,.rule{font-size:12px;color:var(--ink-faint);margin:4px 0 0}
.rule{color:var(--ink-soft)}
.src{font-size:12px;color:var(--ink-faint);margin:8px 0 0}
.src a{color:inherit}
.key{display:flex;flex-wrap:wrap;gap:6px 14px;font-size:12px;color:var(--ink-faint);margin:0 0 10px}
.key span{display:inline-flex;align-items:center;gap:5px}
.key i{display:inline-block;width:18px;height:12px;border-radius:3px;border:1.5px solid var(--now)}
.key i.d{border-style:dashed}
.key i.p{background:var(--now)}
.empty{padding:24px;text-align:center;color:var(--ink-soft);background:var(--surface);border-radius:var(--radius-lg)}
footer{margin-top:32px;padding-top:16px;border-top:1px solid var(--rule);color:var(--ink-faint);font-size:13px}
footer a{color:var(--ink-faint)}
.printonly{display:none}
@media print{
  body{max-width:none;padding:0;font-size:12px}
  .plan{position:static;border:0}
  .filters,.bar,.key,.lede,.crumb,footer,.extra,.note,.strip,.noprint{display:none!important}
  .camp{break-inside:avoid;background:none;border:1px solid #999;padding:10px;margin:0 0 8px}
  .camp:not(.picked){display:none!important}
  .wk.none{display:none}
  button.wk:not([aria-pressed="true"]){display:none}
  button.wk[aria-pressed="true"]{background:none;color:#000;border:1px solid #000}
  .camp h2 a::after{content:" " attr(href);font:400 10px var(--body);color:#444;word-break:break-all}
  .printonly{display:block}
}
"""


_SCRIPT = r"""<script>
(function(){
var D = __DATA__;
var LIVE = /(^|\.)localspothq\.com$/.test(location.hostname);
var KEY = "campPlanner:" + D.season;
function load(){ try { return JSON.parse(localStorage.getItem(KEY) || "null"); } catch(e){ return null; } }
function save(){ try { localStorage.setItem(KEY, JSON.stringify(st)); } catch(e){} }
// Counted only on the real site, so test clicks never reach a camp's number.
function track(name, p){
  if (LIVE && typeof gtag === "function") { p.transport_type = "beacon"; gtag("event", name, p); }
  else (window.__campEvents = window.__campEvents || []).push([name, p]);
}
var byId = {}; D.camps.forEach(function(c){ byId[c.id] = c; });
var st = load() || {};
st.picks = st.picks || {}; st.f = st.f || {};
Object.keys(st.picks).forEach(function(id){ if (!byId[id]) delete st.picks[id]; });

var cards = [].slice.call(document.querySelectorAll(".camp"));
var strip = document.getElementById("strip");
var fAge = document.getElementById("f-age"), fTown = document.getElementById("f-town"),
    fDay = document.getElementById("f-day"), fMax = document.getElementById("f-max");
var shown = document.getElementById("shown"), empty = document.getElementById("empty");
var weekNote = document.getElementById("weeknote");

function money(n){ return "$" + n.toLocaleString("en-US"); }
function picksOf(id){ return st.picks[id] || []; }

function setPick(id, w, on){
  var c = byId[id], cur = picksOf(id).slice();
  var ws = c.whole ? c.weeks : [w];
  ws.forEach(function(x){
    var i = cur.indexOf(x);
    if (on && i < 0) cur.push(x);
    if (!on && i >= 0) cur.splice(i, 1);
  });
  if (cur.length) st.picks[id] = cur.sort(function(a,b){return a-b;}); else delete st.picks[id];
  if (on) track("camp_pick", {camp_id: id, week: D.weeks[w].iso});
  save(); draw();
}

function summary(){
  var cover = D.weeks.map(function(){ return {n:0, full:0}; });
  var total = 0, unpriced = 0, ids = Object.keys(st.picks);
  ids.forEach(function(id){
    var c = byId[id];
    picksOf(id).forEach(function(w){
      cover[w].n++; if (c.day !== "half") cover[w].full++;
      if (c.price == null) unpriced++; else total += c.price;
    });
  });
  return {cover: cover, total: total, unpriced: unpriced, ids: ids};
}

function nextDates(ids){
  var today = new Date().toISOString().slice(0,10);
  var pool = ids.length ? ids.map(function(id){ return byId[id]; }) : D.camps;
  return pool.filter(function(c){ return c.keyDate && c.keyDate >= today; })
    .sort(function(a,b){ return a.keyDate < b.keyDate ? -1 : 1; }).slice(0, 3);
}

function fmtDate(iso){
  var d = new Date(iso + "T12:00:00");
  return d.toLocaleDateString("en-US", {month:"short", day:"numeric"});
}

function draw(){
  var s = summary(), covered = 0;
  [].forEach.call(strip.children, function(b, i){
    var cv = s.cover[i];
    if (cv.n) covered++;
    b.classList.toggle("cov", cv.n > 0);
    b.classList.toggle("halfcov", cv.n > 0 && !cv.full);
    b.classList.toggle("sel", st.f.week === i);
    b.setAttribute("aria-label", "Week of " + D.weeks[i].label + ": " +
      (cv.n ? (cv.full ? "covered" : "half day only") : "open") + ". Show camps that week.");
  });
  var any = s.ids.length > 0;
  document.getElementById("s-cov").textContent = covered + " of " + D.weeks.length + " weeks covered";
  document.getElementById("s-line").textContent = any
    ? "· about " + money(s.total) + (s.unpriced ? " +" : "")
    : "· tap the weeks you want below";
  document.getElementById("s-gap").textContent = any && covered < D.weeks.length
    ? "Still open: " + D.weeks.filter(function(_, i){ return !s.cover[i].n; }).map(function(w){ return w.label; }).join(", ") + ". Tap a week in the strip to see who runs it."
    : "";
  document.getElementById("s-total").innerHTML = any
    ? "Season estimate <strong>" + money(s.total) + "</strong> at full day, non member prices" +
      (s.unpriced ? ", plus " + s.unpriced + " week" + (s.unpriced > 1 ? "s" : "") + " with no price posted" : "") + "."
    : "";
  var dbl = D.weeks.filter(function(_, i){ return s.cover[i].full > 1; }).map(function(w){ return w.label; });
  document.getElementById("s-dbl").textContent = dbl.length
    ? "Two full day camps the week of " + dbl.join(", ") + ". Check that is what you meant." : "";
  var nd = nextDates(s.ids);
  document.getElementById("s-next").textContent = nd.length
    ? "Coming up: " + nd.map(function(c){ return fmtDate(c.keyDate) + ", " + c.name + " " + c.keyLabel; }).join("; ") + "."
    : "";

  var age = fAge.value === "" ? null : +fAge.value, town = fTown.value, day = fDay.value,
      max = fMax.value === "" ? null : +fMax.value, wk = st.f.week, n = 0;
  cards.forEach(function(el){
    var amin = el.dataset.amin === "" ? null : +el.dataset.amin,
        amax = el.dataset.amax === "" ? null : +el.dataset.amax,
        price = el.dataset.price === "" ? null : +el.dataset.price,
        weeks = el.dataset.weeks.split(" ").map(Number);
    var ok = (age == null || ((amin == null || age >= amin) && (amax == null || age <= amax)))
      && (!town || el.dataset.town === town)
      && (!day || el.dataset.day === day || el.dataset.day === "both")
      && (max == null || price == null || price <= max)
      && (wk == null || weeks.indexOf(wk) >= 0);
    el.hidden = !ok; if (ok) n++;
    var mine = picksOf(el.dataset.id);
    el.classList.toggle("picked", mine.length > 0);
    [].forEach.call(el.querySelectorAll("button.wk"), function(b){
      var on = mine.indexOf(+b.dataset.w) >= 0;
      b.setAttribute("aria-pressed", on ? "true" : "false");
      b.setAttribute("aria-label", "Week of " + D.weeks[+b.dataset.w].label + (on ? ": remove" : ": add"));
    });
  });
  shown.textContent = n + " of " + cards.length + " camps";
  empty.hidden = n > 0;
  weekNote.hidden = wk == null;
  if (wk != null) document.getElementById("weeklabel").textContent = D.weeks[wk].label;
}

[fAge, fTown, fDay, fMax].forEach(function(sel){
  var k = sel.id.slice(2);
  if (st.f[k] != null && [].some.call(sel.options, function(o){ return o.value === String(st.f[k]); })) sel.value = String(st.f[k]);
  sel.addEventListener("change", function(){ st.f[k] = sel.value; save(); draw(); });
});
[].forEach.call(strip.children, function(b, i){
  b.addEventListener("click", function(){ st.f.week = st.f.week === i ? null : i; save(); draw(); });
});
document.getElementById("clearweek").addEventListener("click", function(){ st.f.week = null; save(); draw(); });
document.getElementById("clearall").addEventListener("click", function(){
  if (!Object.keys(st.picks).length || confirm("Clear every week you picked?")) { st.picks = {}; save(); draw(); }
});
document.getElementById("print").addEventListener("click", function(){ window.print(); });
cards.forEach(function(el){
  el.addEventListener("click", function(ev){
    var b = ev.target.closest("button.wk");
    if (b) { setPick(el.dataset.id, +b.dataset.w, b.getAttribute("aria-pressed") !== "true"); return; }
    var a = ev.target.closest("a[data-out]");
    if (a) track("camp_click", {camp_id: el.dataset.id, link_type: a.dataset.out});
  });
});
draw();
})();
</script>"""


def _page(data, area_config):
    e = html.escape
    area_name = area_config['name']
    base_url = area_config['meta']['canonical_url'].rstrip('/')
    canonical = f"{base_url}/{INDEX_DIR}/"
    season = data['season']
    grid = grid_weeks(data)
    camps = sorted(data['camps'], key=lambda c: (not c.get('featured'), c['miles'], c['name']))
    live = bool(data.get('live'))
    robots = 'index, follow' if live else 'noindex, follow'
    title = f"Summer Camps Near {area_name} {season}: Week by Week Planner"
    description = (f"Plan summer {season} week by week: {len(camps)} day camps near {area_name}, PA "
                   f"with ages, hours, prices and sign up dates, each checked by hand.")
    towns = sorted({c['town'] for c in camps})
    strip = ''.join(f'<button type="button"><b>{d.day}</b>{d.strftime("%b")}</button>' for d in grid)
    ages = ''.join(f'<option value="{a}">{a}</option>' for a in range(3, 16))
    town_opts = ''.join(f'<option value="{e(t)}">{e(t)}</option>' for t in towns)
    cards = '\n'.join(_card(c, data, grid) for c in camps)
    client = json.dumps(_client_data(data, grid), ensure_ascii=False).replace('</', '<\\/')
    last_day = grid[-1] + timedelta(days=4)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
{GA_SNIPPET}
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{e(title)} | LocalSpot</title>
<meta name="description" content="{e(description)}">
<meta name="robots" content="{robots}">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="LocalSpot {e(area_name)}">
<meta property="og:url" content="{canonical}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(description)}">
<meta property="og:image" content="{e(area_config['meta'].get('og_image', ''))}">
<meta name="twitter:card" content="summary_large_image">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;600;700&family=Newsreader:opsz,wght@6..72,400;6..72,600&display=swap">
<link rel="icon" type="image/png" sizes="192x192" href="../icon-192.png">
<link rel="apple-touch-icon" href="../icon-180.png">
<link rel="stylesheet" href="../localspot.css">
<style>{_STYLE}</style>
</head>
<body>
<p class="crumb"><a href="{base_url}/">LocalSpot {e(area_name)}</a> &rsaquo; Summer camps</p>
<h1>Summer camps near {e(area_name)}, {season}</h1>
<p class="lede">Day camps near {e(area_name)} laid out week by week, {_short(grid[0])} to {_short(last_day)}. Tap the weeks you want on any camp; the strip below shows which weeks are covered, the season estimate and the next sign up date. Your picks stay in this browser and nowhere else.</p>
<p class="small">Most camps post {season} dates between December and February. Until a camp does, its weeks show last summer's schedule with a dashed outline. Every camp lists the page we read and the day we checked it; confirm with the camp before you pay.</p>

<section class="plan" aria-label="Your summer">
  <p class="printonly"><strong>Summer {season} plan</strong> &middot; from {e(canonical)}</p>
  <div class="strip" id="strip">{strip}</div>
  <p class="line"><strong id="s-cov"></strong> <span id="s-line"></span></p>
</section>
<div class="detail" aria-live="polite">
  <p id="s-total"></p>
  <p id="s-gap"></p>
  <p id="s-dbl" class="warn"></p>
  <p id="s-next" class="next"></p>
</div>

<div class="filters noprint">
  <div><label for="f-age">Child's age</label><select id="f-age"><option value="">Any age</option>{ages}</select></div>
  <div><label for="f-town">Town</label><select id="f-town"><option value="">All towns</option>{town_opts}</select></div>
  <div><label for="f-day">Day</label><select id="f-day"><option value="">Full or half</option><option value="full">Full day</option><option value="half">Half day</option></select></div>
  <div><label for="f-max">Price a week</label><select id="f-max"><option value="">Any price</option><option value="200">Up to $200</option><option value="300">Up to $300</option><option value="400">Up to $400</option><option value="500">Up to $500</option></select></div>
</div>
<div class="bar noprint">
  <span id="shown"></span>
  <span id="weeknote" hidden>&middot; running the week of <strong id="weeklabel"></strong> <button type="button" id="clearweek">Show all weeks</button></span>
  <button type="button" id="print">Print my plan</button>
  <button type="button" id="clearall">Clear picks</button>
</div>
<div class="key noprint"><span><i></i>{season} week</span><span><i class="d"></i>last summer's week</span><span><i class="p"></i>picked</span></div>

{cards}
<p class="empty" id="empty" hidden>No camp matches those filters. Try another age, town or price.</p>

<footer>LocalSpot HQ &middot; camp details checked {_long(data['updated'])} &middot; <a href="{base_url}/">Everything happening in {e(area_name)} &rarr;</a></footer>
{_SCRIPT.replace('__DATA__', client)}
</body>
</html>
"""


def generate_camp_pages(camps_file, output_dir, area_config):
    """Write /camps/ when the area has a camps file. Returns True only when
    the data says live, so the sitemap lists the page only then."""
    out = os.path.join(output_dir, INDEX_DIR)
    if os.path.isdir(out):
        shutil.rmtree(out)
    data = load_camps(camps_file)
    if not data or not data.get('camps'):
        return False
    problems = validate(data)
    if problems:
        raise ValueError('camps.json: ' + '; '.join(problems))
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(_page(data, area_config))
    live = bool(data.get('live'))
    print(f">> Camp planner: {len(data['camps'])} camps, {'live' if live else 'noindex (not live)'} -> {out}")
    return live

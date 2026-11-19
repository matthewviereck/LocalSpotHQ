"""Summer camp week planner (/camps/), rendered from data/<area>/camps.json.

One page: every day camp near the area for the coming summer, laid out week by
week. A parent taps the weeks they want; the strip at the top shows the gaps,
the season estimate and the next sign up date. Picks are saved in the parent's
own browser (localStorage) and never sent anywhere: no accounts, no pick
events, nothing about a child.

The data is hand checked. Each camp carries the page its facts came from and
the date read. Until a camp posts the new season, its last season's weeks are
moved onto the new grid as the same week of summer (plus 364 days, so Monday
stays Monday) and drawn dashed, labelled as last year's schedule.

The page is noindex and left out of the sitemap until the data file says
"live": true, so merging the branch never puts a half-filled page in search.
Clicks through to each camp's own page are counted in GA4 (event `camp_click`,
param `camp_id`), only when the page is live and on the production hostname,
so camps can be sent their own number at the end of the sign up season.

The planner's logic (restoring saved picks, totals, overlaps, minimum weeks,
filters, dates) lives in LOGIC_JS as plain functions with no DOM, so
tests/test_camp_pages.py can run it under Node.
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
    the same week of summer this season: +364 days keeps the weekday. A camp
    with no dates posted (weeks_year null) has no weeks."""
    if camp.get('weeks_year') is None:
        return [], 0
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
    if camp.get('weeks_year') is None:
        return 'none'
    if int(camp['weeks_year']) == int(data['season']):
        return 'posted' if camp.get('year_printed', True) else 'noyear'
    return 'last'


def _is_date(value):
    try:
        date.fromisoformat(str(value))
        return True
    except ValueError:
        return False


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate(data):
    """Problems that would put a wrong fact or a broken week on the page."""
    problems = []
    seen = set()
    grid = grid_weeks(data)
    if grid[0].weekday() != 0:
        problems.append('grid_start is not a Monday')
    if not _is_date(data.get('updated')):
        problems.append('updated is not a date')
    for c in data.get('camps', []):
        cid = c.get('id', '?')
        cp = []
        if cid in seen:
            cp.append('duplicate id')
        seen.add(cid)
        dated = c.get('weeks_year') is not None
        required = ['name', 'town', 'ages', 'hours', 'price', 'signup', 'link', 'source', 'checked']
        if dated:
            required += ['day', 'weeks']
        elif c.get('weeks'):
            cp.append('weeks given but weeks_year is null')
        for field in required:
            if c.get(field) in (None, '', []):
                cp.append(f'missing {field}')
        if c.get('day') not in DAY_LABEL and (dated or c.get('day') is not None):
            cp.append('day must be full, half or both')
        for url_field in ('link', 'source'):
            if not str(c.get(url_field, '')).startswith('https://'):
                cp.append(f'{url_field} is not an https link')
        if c.get('checked') and not _is_date(c['checked']):
            cp.append('checked is not a date')
        if not _is_number(c.get('miles')):
            cp.append('miles must be a number')
        if _is_number(c.get('weeks_year')) and c['weeks_year'] > int(data['season']):
            cp.append('weeks_year is after the season')
        amin, amax = c.get('age_min'), c.get('age_max')
        for name, v in (('age_min', amin), ('age_max', amax)):
            if v is not None and not _is_number(v):
                cp.append(f'{name} must be a number or null')
        if _is_number(amin) and _is_number(amax) and amin > amax:
            cp.append('age_min is above age_max')
        for iso in c.get('weeks', []):
            if not _is_date(iso):
                cp.append(f'week {iso} is not a date')
            elif date.fromisoformat(iso).weekday() != 0:
                cp.append(f'week {iso} is not a Monday')
        if c.get('key_date'):
            if not _is_date(c['key_date']):
                cp.append('key_date is not a date')
            if not c.get('key_date_label'):
                cp.append('key_date without a label')
        for name in ('price_week', 'price_half', 'min_weeks'):
            v = c.get(name)
            if v is not None and not _is_number(v):
                cp.append(f'{name} must be a number or null')
        if not cp and dated and not camp_weeks(c, data)[0]:
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
        'none': ('last', 'No dates posted yet'),
    }[b]
    weeks = []
    for i, d in enumerate(grid):
        label = _short(d)
        if i in on:
            weeks.append(f'<button type="button" class="wk {b}" data-w="{i}" aria-pressed="false" '
                         f'aria-label="Week of {label}: add">{label}</button>')
        else:
            weeks.append(f'<span class="wk none" aria-hidden="true">{label}</span>')
    weeks_html = (f'<div class="weeks" role="group" aria-label="Weeks {e(camp["name"])} runs">{"".join(weeks)}</div>'
                  if on else '')
    day_tag = f'<span class="tag">{e(DAY_LABEL[camp["day"]])}</span>' if camp.get('day') in DAY_LABEL else ''
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
    return f"""<article class="camp" id="camp-{e(camp['id'])}" data-id="{e(camp['id'])}">
  <div class="tags">{featured}<span class="tag {status[0]}">{e(status[1])}</span>{day_tag}</div>
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
  {weeks_html}
  {extra}{rule_html}
  <p class="src">Checked {_long(camp['checked'])} &middot; <a href="{e(camp['source'])}" data-out="source" target="_blank" rel="noopener">source</a> &middot; run by {e(camp.get('organizer', camp['name']))}</p>
</article>"""


def client_data(data):
    """What the page script needs, and all it gets."""
    grid = grid_weeks(data)
    camps = []
    for c in data['camps']:
        on, _ = camp_weeks(c, data)
        camps.append({
            'id': c['id'], 'name': c['name'], 'town': c['town'], 'day': c['day'], 'weeks': on,
            'amin': c.get('age_min'), 'amax': c.get('age_max'),
            'price': c.get('price_week'), 'priceHalf': c.get('price_half'),
            'whole': bool(c.get('whole_session')), 'min': c.get('min_weeks') or 1,
            'keyDate': c.get('key_date'), 'keyLabel': c.get('key_date_label', ''),
        })
    return {
        'season': data['season'],
        'live': bool(data.get('live')),
        'weeks': [{'iso': d.isoformat(), 'label': _short(d)} for d in grid],
        'camps': camps,
    }


_STYLE = """
body{max-width:var(--wrap);margin:0 auto;padding:24px 16px 120px}
.crumb{font-size:13px;color:var(--ink-soft)}
.crumb a{color:var(--ink-soft);text-decoration:none}
h1{font-size:clamp(26px,5vw,36px);margin:.2em 0 .3em}
.lede{font-size:16px;color:var(--ink-soft);line-height:1.55;margin:0 0 .8em}
.small{font-size:13px;color:var(--ink-soft);line-height:1.5}
.plan{position:sticky;top:0;z-index:5;background:var(--paper);padding:10px 0 12px;
  border-bottom:1px solid var(--rule);margin:16px 0 12px}
.strip{display:grid;grid-template-columns:repeat(11,1fr);gap:3px}
.strip button{position:relative;font:600 11px/1.1 var(--body);padding:6px 0;border:1px solid var(--rule);
  border-radius:6px;background:var(--surface);color:var(--ink-soft);cursor:pointer;min-height:44px}
.strip button b{display:block;font-size:13px;color:var(--ink)}
.strip button.cov{background:var(--good-wash);border-color:var(--good);color:var(--good)}
.strip button.cov b{color:var(--good)}
.strip button.halfcov{border-style:dashed}
.strip button.dbl::after{content:"2";position:absolute;top:-6px;right:-5px;width:16px;height:16px;
  border-radius:50%;background:var(--ink);color:var(--paper);font:700 10px/16px var(--body);text-align:center}
.strip button[aria-pressed="true"]{outline:2px solid var(--now);outline-offset:1px}
.line{margin:8px 0 0;font-size:14px;color:var(--ink-soft)}
.line strong{color:var(--ink)}
.detail{font-size:14px;color:var(--ink-soft);line-height:1.5;margin:0 0 14px}
.detail p{margin:0 0 4px}
.detail p:empty{display:none}
.detail strong,.warn{color:var(--ink)}
.next{font-size:13px}
.filters{display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin:0 0 12px}
@media (min-width:560px){.filters{grid-template-columns:repeat(4,1fr)}}
.filters label{font-size:12px;color:var(--ink-soft);display:block}
.filters select{width:100%;font:15px var(--body);padding:8px;border:1px solid var(--rule);
  border-radius:8px;background:var(--paper);color:var(--ink);min-height:40px}
.bar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:0 0 14px;font-size:14px;color:var(--ink-soft)}
.bar button{font:600 13px var(--body);padding:8px 12px;border-radius:8px;border:1px solid var(--rule);
  background:var(--paper);color:var(--ink);cursor:pointer;min-height:40px}
.camp{background:var(--surface);border-radius:var(--radius-lg);padding:16px;margin:0 0 14px}
.camp h2{font-size:20px;margin:6px 0 2px;line-height:1.25}
.camp h2 a{color:var(--ink);text-decoration:none}
.camp h2 a:hover{text-decoration:underline}
.where{font-size:13px;color:var(--ink-soft);margin:0 0 8px}
.tags{display:flex;flex-wrap:wrap;gap:6px}
.tag{font:600 11px var(--body);letter-spacing:.02em;padding:3px 8px;border-radius:999px;
  background:var(--paper);color:var(--ink-soft);border:1px solid var(--rule)}
.tag.posted{background:var(--good-wash);color:var(--good);border-color:transparent}
.tag.last{background:var(--surface-sunk);color:var(--ink-soft);border-color:transparent}
.tag.feat{background:var(--now-wash);color:var(--now);border-color:transparent}
dl{display:grid;grid-template-columns:max-content 1fr;gap:4px 12px;font-size:14px;margin:8px 0}
dt{color:var(--ink-soft)}
dd{margin:0;color:var(--ink);min-width:0}
.note{font-size:14px;color:var(--ink-soft);margin:6px 0 10px;line-height:1.5}
.weeks{display:grid;grid-template-columns:repeat(6,1fr);gap:4px;margin:8px 0 4px}
@media (min-width:560px){.weeks{grid-template-columns:repeat(11,1fr)}}
.wk{font:600 12px var(--body);text-align:center;padding:9px 0;border-radius:6px;min-height:40px;
  display:flex;align-items:center;justify-content:center}
button.wk{border:1.5px solid var(--now);background:var(--paper);color:var(--now);cursor:pointer}
button.wk.last{border-style:dashed}
button.wk[aria-pressed="true"]{background:var(--now);color:var(--paper)}
.wk.none{color:var(--ink-faint);opacity:.45;border:1px solid transparent;text-decoration:line-through}
.extra,.rule{font-size:12px;color:var(--ink-soft);margin:4px 0 0}
.src{font-size:12px;color:var(--ink-soft);margin:8px 0 0}
.src a{color:inherit}
.key{display:flex;flex-wrap:wrap;gap:6px 14px;font-size:12px;color:var(--ink-soft);margin:0 0 10px}
.key span{display:inline-flex;align-items:center;gap:5px}
.key i{display:inline-block;width:18px;height:12px;border-radius:3px;border:1.5px solid var(--now)}
.key i.d{border-style:dashed}
.key i.p{background:var(--now)}
h2.section{font-size:20px;margin:28px 0 4px;line-height:1.25}
.empty{padding:24px;text-align:center;color:var(--ink-soft);background:var(--surface);border-radius:var(--radius-lg)}
footer{margin-top:32px;padding-top:16px;border-top:1px solid var(--rule);color:var(--ink-soft);font-size:13px}
footer a{color:var(--ink-soft)}
.printonly{display:none}
button:focus-visible,select:focus-visible,a:focus-visible{outline:2px solid var(--now);outline-offset:2px}
@media print{
  body{max-width:none;padding:0;font-size:12px;background:#fff!important;color:#000!important}
  body *{color:#000!important;background:transparent!important}
  .plan{position:static;border:0}
  .filters,.bar,.key,.lede,.small,.crumb,footer,.extra,.note,.strip,.noprint,.nodates{display:none!important}
  .camp{break-inside:avoid;border:1px solid #999;padding:10px;margin:0 0 8px}
  .camp:not(.picked){display:none!important}
  .camp.picked[hidden]{display:block!important}
  .wk.none{display:none}
  button.wk:not([aria-pressed="true"]){display:none}
  button.wk[aria-pressed="true"]{border:1px solid #000}
  .camp h2 a::after{content:" " attr(href);font:400 10px var(--body);word-break:break-all}
  .printonly{display:block}
}
"""


# Plain functions, no DOM: the page uses them and the tests run them in Node.
LOGIC_JS = r"""
function weekIndex(D, iso){
  for (var i = 0; i < D.weeks.length; i++) if (D.weeks[i].iso === iso) return i;
  return -1;
}
function campById(D){ var m = {}; D.camps.forEach(function(c){ m[c.id] = c; }); return m; }
// Saved state may be stale (a camp changed its weeks or left the list) or not ours at all.
function sanitize(raw, D){
  var by = campById(D), st = {picks: {}, f: {}};
  if (!raw || typeof raw !== "object") return st;
  if (raw.f && typeof raw.f === "object") {
    ["age", "town", "day", "max"].forEach(function(k){ if (typeof raw.f[k] === "string") st.f[k] = raw.f[k]; });
    if (typeof raw.f.week === "number" && raw.f.week >= 0 && raw.f.week < D.weeks.length) st.f.week = raw.f.week;
  }
  var p = raw.picks;
  if (p && typeof p === "object") Object.keys(p).forEach(function(id){
    var c = by[id];
    if (!c || !Array.isArray(p[id])) return;
    var keep = p[id].filter(function(iso, k, a){
      var i = weekIndex(D, iso);
      return i >= 0 && c.weeks.indexOf(i) >= 0 && a.indexOf(iso) === k;
    });
    if (keep.length) st.picks[id] = keep.sort();
  });
  return st;
}
function toggle(picks, c, D, w, on){
  var out = {};
  Object.keys(picks).forEach(function(k){ out[k] = picks[k].slice(); });
  var cur = out[c.id] || [];
  (c.whole ? c.weeks : [w]).forEach(function(i){
    var iso = D.weeks[i].iso, at = cur.indexOf(iso);
    if (on && at < 0) cur.push(iso);
    if (!on && at >= 0) cur.splice(at, 1);
  });
  if (cur.length) out[c.id] = cur.sort(); else delete out[c.id];
  return out;
}
function summarize(picks, D){
  var by = campById(D), total = 0, unpriced = 0, short = [];
  var cover = D.weeks.map(function(){ return {n: 0, full: 0}; });
  Object.keys(picks).forEach(function(id){
    var c = by[id], have = 0;
    if (!c) return;
    picks[id].forEach(function(iso){
      var i = weekIndex(D, iso);
      if (i < 0) return;
      have++; cover[i].n++;
      if (c.day !== "half") cover[i].full++;
      if (c.price == null) unpriced++; else total += c.price;
    });
    if (have && have < c.min) short.push({name: c.name, min: c.min, have: have});
  });
  function weeksWhere(test){ var out = []; cover.forEach(function(cv, i){ if (test(cv)) out.push(i); }); return out; }
  return {
    any: Object.keys(picks).length > 0, cover: cover, total: total, unpriced: unpriced, short: short,
    covered: weeksWhere(function(cv){ return cv.n > 0; }).length,
    open: weeksWhere(function(cv){ return cv.n === 0; }),
    halfOnly: weeksWhere(function(cv){ return cv.n > 0 && cv.full === 0; }),
    // Two half days can be a morning and an afternoon; any pair with a full day clashes.
    overlap: weeksWhere(function(cv){ return cv.n > 1 && cv.full > 0; })
  };
}
function isoToday(d){
  function two(n){ return (n < 10 ? "0" : "") + n; }
  return d.getFullYear() + "-" + two(d.getMonth() + 1) + "-" + two(d.getDate());
}
function nextDates(picks, D, today){
  var by = campById(D), ids = Object.keys(picks).filter(function(id){ return by[id]; });
  var pool = ids.length ? ids.map(function(id){ return by[id]; }) : D.camps;
  return pool.filter(function(c){ return c.keyDate && c.keyDate >= today; })
    .sort(function(a, b){ return a.keyDate < b.keyDate ? -1 : a.keyDate > b.keyDate ? 1 : 0; })
    .slice(0, 3);
}
function priceFor(c, day){
  if (day === "full") return c.price;
  if (day === "half") return c.priceHalf != null ? c.priceHalf : c.price;
  if (c.priceHalf != null && c.price != null) return Math.min(c.price, c.priceHalf);
  return c.price;
}
function matches(c, f){
  var age = f.age ? +f.age : null, max = f.max ? +f.max : null;
  if (age != null && ((c.amin != null && age < c.amin) || (c.amax != null && age > c.amax))) return false;
  if (f.town && c.town !== f.town) return false;
  if (f.day && c.day && c.day !== f.day && c.day !== "both") return false;
  if (max != null) { var p = priceFor(c, f.day); if (p != null && p > max) return false; }
  if (f.week != null && c.weeks.indexOf(f.week) < 0) return false;
  return true;
}
"""


_SCRIPT = r"""<script>
(function(){
var D = __DATA__;
__LOGIC__
// Counted only when the page is live and on the real site, so tests never reach a camp's number.
var LIVE = D.live && /(^|\.)localspothq\.com$/.test(location.hostname);
var KEY = "campPlanner:" + D.season;
function load(){ try { return JSON.parse(localStorage.getItem(KEY) || "null"); } catch(e){ return null; } }
function save(){ try { localStorage.setItem(KEY, JSON.stringify(st)); } catch(e){} }
function track(name, p){
  if (LIVE && typeof gtag === "function") { p.transport_type = "beacon"; gtag("event", name, p); }
  else (window.__campEvents = window.__campEvents || []).push([name, p]);
}
var st = sanitize(load(), D), byId = campById(D);

var cards = [].slice.call(document.querySelectorAll(".camp"));
var strip = document.getElementById("strip");
var sel = {age: document.getElementById("f-age"), town: document.getElementById("f-town"),
           day: document.getElementById("f-day"), max: document.getElementById("f-max")};
var shown = document.getElementById("shown"), empty = document.getElementById("empty");
var weekNote = document.getElementById("weeknote");

function money(n){ return "$" + n.toLocaleString("en-US"); }
function labels(ix){ return ix.map(function(i){ return D.weeks[i].label; }).join(", "); }
function text(id, s){ document.getElementById(id).textContent = s; }
function fmtDate(iso){
  return new Date(iso + "T12:00:00").toLocaleDateString("en-US", {month: "short", day: "numeric"});
}
function filters(){
  return {age: sel.age.value, town: sel.town.value, day: sel.day.value, max: sel.max.value, week: st.f.week};
}

function draw(){
  var s = summarize(st.picks, D);
  [].forEach.call(strip.children, function(b, i){
    var cv = s.cover[i], clash = s.overlap.indexOf(i) >= 0, on = st.f.week === i;
    b.classList.toggle("cov", cv.n > 0);
    b.classList.toggle("halfcov", cv.n > 0 && cv.full === 0);
    b.classList.toggle("dbl", clash);
    b.setAttribute("aria-pressed", on ? "true" : "false");
    b.setAttribute("aria-label", "Week of " + D.weeks[i].label + ": " +
      (cv.n === 0 ? "open" : clash ? cv.n + " camps booked" : cv.full ? "covered" : "half day only") +
      ". Show only camps that run that week.");
  });

  text("s-cov", s.covered + " of " + D.weeks.length + " weeks covered");
  text("s-line", !s.any ? "· tap the weeks you want below"
    : "· " + (s.total ? "about " + money(s.total) + (s.unpriced ? "+" : "") : "no prices posted") +
      (s.overlap.length ? " · " + s.overlap.length + " week" + (s.overlap.length > 1 ? "s" : "") + " double booked" : ""));
  var total = document.getElementById("s-total");
  total.textContent = "";
  if (s.any && s.total) {
    total.appendChild(document.createTextNode("Season estimate "));
    var strong = document.createElement("strong"); strong.textContent = money(s.total); total.appendChild(strong);
    total.appendChild(document.createTextNode(
      (s.unpriced ? ", plus " + s.unpriced + " week" + (s.unpriced > 1 ? "s" : "") + " with no price posted" : "") +
      ". It uses the full day price where a camp offers both, at non member and non resident rates."));
  } else if (s.any) {
    total.textContent = "No price is posted yet for the weeks you picked.";
  }
  text("s-gap", !s.any ? "" : (s.open.length
      ? "Still open: " + labels(s.open) + ". Tap a week in the strip to see who runs it. " : "") +
    (s.halfOnly.length ? "Half day only: " + labels(s.halfOnly) + "." : ""));
  text("s-dbl", s.overlap.length ? "More than one camp the week of " + labels(s.overlap) +
    ", at least one of them full day. Check that is what you meant." : "");
  text("s-short", s.short.map(function(x){
    return x.name + " is sold in blocks of " + x.min + " weeks or more; you picked " + x.have + ".";
  }).join(" "));
  var nd = nextDates(st.picks, D, isoToday(new Date()));
  text("s-next", nd.length ? "Coming up: " + nd.map(function(c){
    return fmtDate(c.keyDate) + ", " + c.name + " " + c.keyLabel; }).join("; ") + "." : "");

  var f = filters(), n = 0, unpricedShown = 0;
  cards.forEach(function(el){
    var c = byId[el.dataset.id], ok = matches(c, f);
    el.hidden = !ok;
    if (ok) { n++; if (priceFor(c, f.day) == null) unpricedShown++; }
    var mine = (st.picks[c.id] || []).map(function(iso){ return weekIndex(D, iso); });
    el.classList.toggle("picked", mine.length > 0);
    [].forEach.call(el.querySelectorAll("button.wk"), function(b){
      var w = +b.dataset.w, on = mine.indexOf(w) >= 0;
      b.setAttribute("aria-pressed", on ? "true" : "false");
      b.setAttribute("aria-label", "Week of " + D.weeks[w].label + (on ? ": remove" : ": add"));
    });
  });
  shown.textContent = n + " of " + cards.length + " camps" +
    (f.max && unpricedShown ? " (" + unpricedShown + " with no price posted)" : "");
  empty.hidden = n > 0;
  var nodates = document.getElementById("nodates");
  if (nodates) nodates.hidden = !nodates.querySelector(".camp:not([hidden])");
  weekNote.hidden = f.week == null;
  if (f.week != null) text("weeklabel", D.weeks[f.week].label);
}

Object.keys(sel).forEach(function(k){
  var s = sel[k];
  if (st.f[k] != null && [].some.call(s.options, function(o){ return o.value === st.f[k]; })) s.value = st.f[k];
  s.addEventListener("change", function(){ st.f[k] = s.value; save(); draw(); });
});
[].forEach.call(strip.children, function(b, i){
  b.addEventListener("click", function(){ st.f.week = st.f.week === i ? null : i; save(); draw(); });
});
document.getElementById("clearweek").addEventListener("click", function(){ st.f.week = null; save(); draw(); });
// Two taps, no browser dialog: the first arms the button for a few seconds.
var clearBtn = document.getElementById("clearall"), armed = null;
clearBtn.addEventListener("click", function(){
  if (!Object.keys(st.picks).length) return;
  if (armed) { clearTimeout(armed); armed = null; clearBtn.textContent = "Clear picks"; st.picks = {}; save(); draw(); return; }
  clearBtn.textContent = "Tap again to clear all";
  armed = setTimeout(function(){ armed = null; clearBtn.textContent = "Clear picks"; }, 4000);
});
document.getElementById("print").addEventListener("click", function(){ window.print(); });
cards.forEach(function(el){
  el.addEventListener("click", function(ev){
    var b = ev.target.closest("button.wk");
    if (b) {
      st.picks = toggle(st.picks, byId[el.dataset.id], D, +b.dataset.w, b.getAttribute("aria-pressed") !== "true");
      save(); draw(); return;
    }
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
    strip = ''.join(f'<button type="button" aria-pressed="false"><b>{d.day}</b>{d.strftime("%b")}</button>'
                    for d in grid)
    ages = ''.join(f'<option value="{a}">{a}</option>' for a in range(3, 16))
    town_opts = ''.join(f'<option value="{e(t)}">{e(t)}</option>' for t in towns)
    cards = '\n'.join(_card(c, data, grid) for c in camps if basis(c, data) != 'none')
    undated = [c for c in camps if basis(c, data) == 'none']
    nodates = ''
    if undated:
        nodates = (f'<section id="nodates" class="nodates" aria-labelledby="nodates-h">\n'
                   f'<h2 class="section" id="nodates-h">Also near {e(area_name)}: no {season} dates posted yet</h2>\n'
                   f'<p class="small">These camps don\'t post their weeks online, or haven\'t yet. Call them or check '
                   f'their pages; we add their weeks to the planner when they post.</p>\n'
                   + '\n'.join(_card(c, data, grid) for c in undated) + '\n</section>')
    client = json.dumps(client_data(data), ensure_ascii=False).replace('</', '<\\/')
    script = _SCRIPT.replace('__LOGIC__', LOGIC_JS).replace('__DATA__', client)
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
<meta property="og:site_name" content="LocalSpot">
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
<p class="lede">Day camps near {e(area_name)} laid out week by week, {_short(grid[0])} to {_short(last_day)}. Tap the weeks you want on any camp; the strip below shows which weeks are covered, the season estimate and the next sign up date.</p>
<p class="small">Your picks are saved in this browser and are not sent to us. We do count clicks through to each camp's own page, so we can tell camps how many families found them.</p>
<p class="small">Most camps post {season} dates between December and February. Until a camp does, its weeks show last summer's schedule with a dashed outline. Every camp lists the page we read and the day we checked it; confirm with the camp before you pay.</p>

<section class="plan" aria-label="Your summer">
  <p class="printonly"><strong>Summer {season} plan</strong> &middot; from {e(canonical)}</p>
  <div class="strip" id="strip">{strip}</div>
  <p class="line" aria-live="polite"><strong id="s-cov"></strong> <span id="s-line"></span></p>
</section>
<div class="detail">
  <p id="s-total"></p>
  <p id="s-gap"></p>
  <p id="s-dbl" class="warn"></p>
  <p id="s-short" class="warn"></p>
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
{nodates}

<footer>LocalSpot &middot; camp details checked {_long(data['updated'])} &middot; <a href="{base_url}/">Everything happening in {e(area_name)} &rarr;</a></footer>
{script}
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

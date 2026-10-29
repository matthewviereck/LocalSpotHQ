"""The weekend case: a small whodunit set around town, one a week, out on
Thursday for the Facebook Page post and the weekend. Rendered from
data/<area>/cases.json. The Daily Dunnit generator makes each grid and its
clues (solution first, true clues, solver-pruned to one answer that needs no
guess); a person writes the scene, the teaser and the reveal.

    /<area>/weekend-case/          the live case, then the archive
    /<area>/weekend-case/<slug>/   every published case, for good

A case is live from its `publish` date (a Thursday; the 6:15 AM build puts it
up before the 7:50 post task reads the site) until the next one. A case whose
date is still ahead is never written into the build: its answer ships inside
the page, and the deploy publishes whatever is in output/.

Settings rule: real public places only (parks, trails, streets), invented
people, and never a real business as the scene of anything.
"""

import base64
import html
import itertools
import json
import os
import shutil
from datetime import date

from pipeline.analytics import GA_SNIPPET
from pipeline.event_pages import SIGNUP_HTML

INDEX_DIR = 'weekend-case'


def load_cases(cases_file):
    if not cases_file or not os.path.exists(cases_file):
        return []
    with open(cases_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def published(cases, today=None):
    """Cases whose Thursday has come, oldest first."""
    today = (today or date.today()).isoformat()
    return sorted((c for c in cases if c['publish'] <= today), key=lambda c: c['publish'])


def upcoming(cases, today=None):
    today = (today or date.today()).isoformat()
    return sorted((c for c in cases if c['publish'] > today), key=lambda c: c['publish'])


def live_case(cases_file, today=None):
    """The case on the site right now, or None. Used by the app footer and the
    weekend page to link to it."""
    pub = published(load_cases(cases_file), today)
    return pub[-1] if pub else None


def _day_label(iso):
    d = date.fromisoformat(iso)
    return f"{d.strftime('%A, %B')} {d.day}"  # %-d is not portable to Windows


def _name(case, suspect_id):
    return next(s['name'] for s in case['suspects'] if s['id'] == suspect_id)


# ---------------------------------------------------------------- checking

def _holds(clue, a, order):
    """True, False, or None when a category the clue needs is not assigned yet."""
    t = clue['type']
    if t in ('direct', 'negative', 'either'):
        col = a.get(clue['c'])
        if col is None:
            return None
        v = col[clue['s']]
        if t == 'direct':
            return v == clue['v']
        if t == 'negative':
            return v != clue['v']
        return v in (clue['v1'], clue['v2'])
    if t in ('link', 'neglink'):
        c1, c2 = a.get(clue['c1']), a.get(clue['c2'])
        if c1 is None or c2 is None:
            return None
        who = next(s for s, v in c1.items() if v == clue['v1'])
        return (c2[who] == clue['v2']) == (t == 'link')
    if t in ('before', 'gap'):
        col = a.get(clue['c'])
        if col is None:
            return None
        i1, i2 = order[clue['c']][col[clue['s1']]], order[clue['c']][col[clue['s2']]]
        return i1 < i2 if t == 'before' else i2 - i1 == clue['d']
    raise ValueError(f"unknown clue type {t}")


def count_solutions(case, limit=2):
    """Brute-force count of grids that satisfy every clue, stopping at
    `limit`. An independent check on the generator: a published case must
    come back 1."""
    suspects = [s['id'] for s in case['suspects']]
    cats = case['categories']
    clues = [c['logic'] for c in case['clues']]
    order = {c['id']: {v: i for i, v in enumerate(c['values'])} for c in cats}
    found = 0
    a = {}

    def rec(k):
        nonlocal found
        if found >= limit:
            return
        if k == len(cats):
            found += 1
            return
        cat = cats[k]
        for perm in itertools.permutations(cat['values']):
            a[cat['id']] = dict(zip(suspects, perm))
            if all(_holds(cl, a, order) is not False for cl in clues):
                rec(k + 1)
            if found >= limit:
                break
        a.pop(cat['id'], None)

    rec(0)
    return found


# ---------------------------------------------------------------- rendering

_STYLE = """
body{max-width:680px;margin:0 auto;padding:24px 16px 48px}
.crumb{font-size:13px;color:var(--ink-faint)}
.crumb a{color:var(--ink-faint);text-decoration:none}
h1{font-size:clamp(26px,5vw,36px);margin:.2em 0 .3em}
h2{font-family:var(--display);font-size:15px;text-transform:uppercase;letter-spacing:.06em;color:var(--ink-soft);margin:28px 0 10px}
.scene{font-family:var(--article);font-size:18px;line-height:1.6}
.scene p{margin:0 0 .8em}
.question{font-family:var(--display);font-weight:700;font-size:20px;color:var(--now);margin:.4em 0 0}
.howto{margin:16px 0;font-size:15px}
.howto ul{margin:8px 0 10px;padding-left:20px}
.howto li{margin:4px 0}
.linkish{background:none;border:0;padding:0;font:inherit;font-size:13px;color:var(--cool);text-decoration:underline;cursor:pointer}
.tabs{display:flex;gap:6px;margin:0 0 8px}
.tabs button{flex:1;padding:8px 4px;border:1px solid var(--rule);background:var(--paper);color:var(--ink);
border-radius:var(--radius);font:600 14px var(--body);cursor:pointer}
.tabs button[aria-selected="true"]{background:var(--ink);color:var(--paper);border-color:var(--ink)}
.gridwrap{overflow-x:auto}
table.grid{border-collapse:collapse;width:100%;table-layout:fixed;font-family:var(--body);font-size:13px;background:var(--surface);border-radius:var(--radius)}
table.grid th,table.grid td{border:1px solid var(--rule);text-align:center;padding:4px 2px}
table.grid th{font-weight:600;color:var(--ink-soft);font-size:11px;line-height:1.2;-webkit-hyphens:auto;hyphens:auto}
table.grid th.who{width:21%}
table.grid td.name{text-align:left;font-weight:700;padding-left:8px;font-size:14px;color:var(--ink)}
table.grid td.cell{height:40px;font-size:19px;cursor:pointer;user-select:none;-webkit-tap-highlight-color:transparent}
table.grid td.cell.no{color:var(--ink-faint)}
table.grid td.cell.yes{color:var(--good);background:var(--good-wash);font-weight:700}
table.grid td.cell:focus-visible{outline:2px solid var(--now);outline-offset:-2px}
.gridfoot{margin:6px 0 0;text-align:right}
ol.clues{padding-left:24px;margin:0;font-size:16px;line-height:1.5}
ol.clues li{margin:0 0 10px;cursor:pointer}
ol.clues li.done{color:var(--ink-faint);text-decoration:line-through}
.accuse{margin-top:24px}
.accuse .pick{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}
.accuse select{font:16px var(--body);padding:8px 10px;border-radius:var(--radius);border:1px solid var(--rule);background:var(--paper);color:var(--ink);min-width:12em}
#result{margin-top:14px}
#result p{margin:0 0 10px}
.share{white-space:pre-wrap;overflow-wrap:anywhere;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:14px;background:var(--surface-sunk);border-radius:var(--radius);padding:12px 14px;margin:10px 0}
table.answer{border-collapse:collapse;width:100%;font-size:14px;margin:8px 0}
table.answer th,table.answer td{border-bottom:1px solid var(--rule);padding:6px 4px;text-align:left}
table.answer tr.culprit td{font-weight:700;color:var(--now)}
ul.archive{list-style:none;padding:0;margin:0}
ul.archive li{margin:0 0 12px}
ul.archive a{font-family:var(--display);font-weight:600;font-size:18px;color:var(--cool)}
.signup-card{margin-top:28px}
footer{margin-top:32px;padding-top:16px;border-top:1px solid var(--rule);color:var(--ink-faint);font-size:13px}
footer a{color:var(--ink-faint)}
"""


def _head(title, description, canonical, area_name, depth, robots='index, follow', og_image=''):
    up = '../' * depth
    image = f'<meta property="og:image" content="{html.escape(og_image)}">\n' if og_image else ''
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
{GA_SNIPPET}
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(description)}">
<meta name="robots" content="{robots}">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="LocalSpot {html.escape(area_name)}">
<meta property="og:url" content="{canonical}">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(description)}">
{image}<meta name="twitter:card" content="summary_large_image">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;600;700&family=Newsreader:opsz,wght@6..72,400;6..72,600&display=swap">
<link rel="icon" type="image/png" sizes="192x192" href="{up}icon-192.png">
<link rel="apple-touch-icon" href="{up}icon-180.png">
<link rel="stylesheet" href="{up}localspot.css">
<style>{_STYLE}</style>
</head>
"""


def _signup(area_config):
    area_slug = area_config.get('slug') or area_config.get('id', '')
    return (SIGNUP_HTML.replace('__AREA__', html.escape(area_config.get('name', '')))
                       .replace('__SOURCE__', f"weekend-case:{area_slug}"))


def _answer_blob(case):
    """The answer, base64 over ASCII-only JSON, so a glance at the page source
    does not spoil it. Not a secret: anyone determined can decode it."""
    rows = [{'name': s['name'], 'culprit': s['id'] == case['culprit'],
             'cells': [case['solution'][c['id']][s['id']] for c in case['categories']]}
            for s in case['suspects']]
    data = {'culprit': case['culprit'], 'name': _name(case, case['culprit']),
            'reveal': case['reveal'], 'labels': [c['label'] for c in case['categories']], 'rows': rows}
    return base64.b64encode(json.dumps(data, ensure_ascii=True).encode('ascii')).decode('ascii')


def _client_data(case, share_url):
    return {
        'number': case['number'],
        'slug': case['slug'],
        'suspects': [{'id': s['id'], 'name': s['name']} for s in case['suspects']],
        'categories': [{'id': c['id'], 'label': c['label'], 'question': c['question'],
                        'values': c['values'], 'short': c.get('short') or c['values']}
                       for c in case['categories']],
        'shareUrl': share_url,
        'answer': _answer_blob(case),
    }


# The page script. Kept out of the f-strings so its braces stay readable;
# __DATA__ is replaced with the case's JSON.
_SCRIPT = r"""<script>
(function(){
var C = __DATA__;
var LIVE = /(^|\.)localspothq\.com$/.test(location.hostname);
var KEY = "wc:" + C.slug;
function load(k){ try { return JSON.parse(localStorage.getItem(k) || "null"); } catch(e){ return null; } }
function save(k, v){ try { localStorage.setItem(k, JSON.stringify(v)); } catch(e){} }
// Solvers are counted in GA4 only on the real site, so test plays never inflate the read.
function track(name, extra){
  var p = {case_number: C.number};
  for (var k in extra) p[k] = extra[k];
  if (LIVE && typeof gtag === "function") gtag("event", name, p);
  else (window.__caseEvents = window.__caseEvents || []).push([name, p]);
}

var st = load(KEY) || {marks:{}, struck:[], wrong:0, guesses:"", done:null, started:false, secs:0};
st.auto = st.auto || {};   // cell -> the ✓ that crossed it out for you
var cat = C.categories[0].id, t0 = null, timerId = null;
var grid = document.getElementById("grid");

var howto = document.getElementById("howto");
if (!load("wc:howto")) howto.hidden = false;
document.getElementById("howto-ok").onclick = function(){ howto.hidden = true; save("wc:howto", 1); };
document.getElementById("howto-open").onclick = function(){ howto.hidden = false; howto.scrollIntoView({behavior:"smooth"}); };

// The clock runs from load while the page is in view, so someone who works it
// out on paper and only names a suspect still gets a real time. case_start
// waits for a first tap, so it counts people who played, not page views.
function secs(){ return st.secs + (t0 ? Math.floor((Date.now() - t0) / 1000) : 0); }
function clock(s){ return Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0"); }
function tick(){ document.getElementById("timer").textContent = clock(secs()); }
function run(){
  if (st.done || t0 || document.hidden) return;
  t0 = Date.now();
  timerId = setInterval(tick, 500);
}
function pause(){ if (t0){ st.secs = secs(); t0 = null; clearInterval(timerId); save(KEY, st); } tick(); }
function engage(){
  run();
  if (!st.started){ st.started = true; save(KEY, st); track("case_start", {}); }
}
document.addEventListener("visibilitychange", function(){ if (document.hidden) pause(); else run(); });
window.addEventListener("pagehide", pause);
window.addEventListener("pageshow", run);

var tabs = document.getElementById("tabs");
C.categories.forEach(function(c){
  var b = document.createElement("button");
  b.type = "button"; b.textContent = c.label; b.setAttribute("role", "tab");
  b.onclick = function(){ cat = c.id; render(); };
  b.dataset.cat = c.id;
  tabs.appendChild(b);
});

function render(){
  var c = C.categories.filter(function(x){ return x.id === cat; })[0];
  [].forEach.call(tabs.children, function(b){ b.setAttribute("aria-selected", b.dataset.cat === cat ? "true" : "false"); });
  document.getElementById("grid-q").textContent = c.question;
  var h = '<tr><th class="who"></th>' + c.short.map(function(v){ return "<th>" + esc(v) + "</th>"; }).join("") + "</tr>";
  C.suspects.forEach(function(s){
    h += '<tr><td class="name">' + esc(s.name) + "</td>" + c.values.map(function(v, i){
      var k = cat + "|" + s.id + "|" + i, m = st.marks[k] || "";
      var label = s.name + ", " + c.values[i] + ": " + (m === "yes" ? "yes" : m === "no" ? "no" : "blank");
      return '<td class="cell ' + m + '" data-k="' + k + '" role="button" tabindex="0" aria-label="' + label + '">' + (m === "yes" ? "&#10003;" : m === "no" ? "&#10007;" : "") + "</td>";
    }).join("") + "</tr>";
  });
  grid.innerHTML = h;
}

// Tap cycles blank, no, yes. A yes crosses out the blanks left in its row and
// column; clearing that yes takes those crosses back off. A cross you tap
// yourself is yours from then on.
function fill(kk, from){ if (kk !== from && !st.marks[kk]){ st.marks[kk] = "no"; st.auto[kk] = from; } }
function unfill(from){
  for (var kk in st.auto) if (st.auto[kk] === from){ if (st.marks[kk] === "no") delete st.marks[kk]; delete st.auto[kk]; }
}
function tap(k){
  engage();
  var m = st.marks[k] || "";
  var next = m === "" ? "no" : m === "no" ? "yes" : "";
  delete st.auto[k];
  if (m === "yes") unfill(k);
  if (next) st.marks[k] = next; else delete st.marks[k];
  if (next === "yes"){
    var p = k.split("|"), c = C.categories.filter(function(x){ return x.id === p[0]; })[0];
    C.suspects.forEach(function(s){ fill(p[0] + "|" + s.id + "|" + p[2], k); });
    c.values.forEach(function(v, i){ fill(p[0] + "|" + p[1] + "|" + i, k); });
  }
  save(KEY, st); render();
}
grid.addEventListener("click", function(e){ var td = e.target.closest("td.cell"); if (td) tap(td.dataset.k); });
grid.addEventListener("keydown", function(e){
  var td = e.target.closest("td.cell");
  if (!td || (e.key !== "Enter" && e.key !== " ")) return;
  e.preventDefault();
  var k = td.dataset.k;
  tap(k);
  grid.querySelector('td[data-k="' + k + '"]').focus();
});

// Two taps to wipe every tab, so a stray tap never costs anyone their notes.
var clearBtn = document.getElementById("clear"), clearTimer = null;
clearBtn.onclick = function(){
  if (!clearTimer){
    clearBtn.textContent = "Tap again to clear every mark";
    clearTimer = setTimeout(function(){ clearTimer = null; clearBtn.textContent = "Clear grid"; }, 3000);
    return;
  }
  clearTimeout(clearTimer); clearTimer = null; clearBtn.textContent = "Clear grid";
  st.marks = {}; st.auto = {}; save(KEY, st); render();
};

var clues = document.querySelectorAll("#clues li");
[].forEach.call(clues, function(li, i){
  if (st.struck.indexOf(i) >= 0) li.classList.add("done");
  li.onclick = function(){
    engage();
    li.classList.toggle("done");
    st.struck = [].map.call(clues, function(x, j){ return x.classList.contains("done") ? j : -1; }).filter(function(j){ return j >= 0; });
    save(KEY, st);
  };
});

function esc(s){ var d = document.createElement("div"); d.textContent = s; return d.innerHTML; }
function answer(){ return JSON.parse(atob(C.answer)); }

function showAnswer(a, solved){
  var r = document.getElementById("result");
  var rows = a.rows.map(function(row){
    return '<tr' + (row.culprit ? ' class="culprit"' : "") + "><td>" + esc(row.name) + "</td>" + row.cells.map(function(c){ return "<td>" + esc(c) + "</td>"; }).join("") + "</tr>";
  }).join("");
  var html = a.reveal.map(function(p){ return "<p>" + esc(p) + "</p>"; }).join("");
  html += '<table class="answer"><tr><th></th>' + a.labels.map(function(l){ return "<th>" + esc(l) + "</th>"; }).join("") + "</tr>" + rows + "</table>";
  if (solved){
    var card = "LocalSpot Weekend Case #" + C.number + " 🔎\nSolved in " + clock(st.done.secs) + " " + st.guesses + "\n" + C.shareUrl;
    html += '<div class="share" id="card">' + esc(card) + '</div><button type="button" class="btn btn-primary" id="share">Share your time</button> <span class="meta" id="shared"></span>';
  }
  r.innerHTML = html;
  document.getElementById("pick").hidden = true;
  var sb = document.getElementById("share");
  if (sb) sb.onclick = function(){
    var text = document.getElementById("card").textContent, done = document.getElementById("shared");
    if (navigator.share) navigator.share({text: text}).catch(function(){});
    else if (navigator.clipboard) navigator.clipboard.writeText(text).then(function(){ done.textContent = "Copied."; }, function(){});
  };
}

// After two wrong names the answer is on offer, and stays on offer after a reload.
function giveUp(){ return st.wrong >= 2 && !st.done ? '<p><button type="button" class="linkish" id="giveup">Show me the answer</button></p>' : ""; }
function wireGiveUp(){
  var g = document.getElementById("giveup");
  if (g) g.onclick = function(){
    pause(); st.done = {solved: false, secs: secs()}; save(KEY, st);
    track("case_reveal", {wrong: st.wrong});
    showAnswer(answer(), false);
  };
}

var sel = document.getElementById("who");
document.getElementById("accuse").onclick = function(){
  if (!sel.value || st.done) return;
  engage();
  var a = answer(), r = document.getElementById("result");
  if (sel.value === a.culprit){
    pause();
    st.guesses += "🟩";
    st.done = {solved: true, secs: secs()};
    save(KEY, st);
    track("case_solve", {seconds: st.done.secs, wrong: st.wrong});
    showAnswer(a, true);
  } else {
    st.wrong++; st.guesses += "🟥"; save(KEY, st);
    var name = sel.options[sel.selectedIndex].text;
    r.innerHTML = "<p>Not " + esc(name) + ". " + esc(name) + " can account for the morning, and is a little hurt you asked. Back to the grid.</p>" + giveUp();
    wireGiveUp();
  }
};

render(); tick();
if (st.done) showAnswer(answer(), st.done.solved);
else { document.getElementById("result").innerHTML = giveUp(); wireGiveUp(); run(); }
})();
</script>"""


def _case_body(case, area_config, others, live):
    """The playable case; `others` are the other published cases, for the
    archive list."""
    area_name = area_config['name']
    base_url = area_config['meta']['canonical_url'].rstrip('/')
    index_url = f"{base_url}/{INDEX_DIR}/"
    culprit_place = case['solution']['place'][case['culprit']]
    scene = '\n'.join(f'<p>{html.escape(p)}</p>' for p in case['scene'])
    clues = '\n'.join(f'<li>{html.escape(c["text"])}</li>' for c in case['clues'])
    options = '\n'.join(f'<option value="{html.escape(s["id"])}">{html.escape(s["name"])}</option>'
                        for s in case['suspects'])
    n = {3: 'Three', 4: 'Four', 5: 'Five', 6: 'Six'}.get(len(case['suspects']), str(len(case['suspects'])))
    dims = ', '.join(c['label'].lower() for c in case['categories'])

    archive = ''
    if others:
        items = '\n'.join(
            f'<li><a href="{index_url}{c["slug"]}/">No. {c["number"]}: {html.escape(c["title"])}</a>'
            f'<p class="meta">{_day_label(c["publish"])}. {html.escape(c["teaser"])}</p></li>'
            for c in reversed(others))
        archive = f'<h2>{"Earlier cases" if live else "More cases"}</h2>\n<ul class="archive">\n{items}\n</ul>'

    # The share card carries the bare address, the way people type it.
    share_url = index_url.split('://', 1)[-1].removeprefix('www.')
    data = json.dumps(_client_data(case, share_url), ensure_ascii=False).replace('</', '<\\/')
    eyebrow = "This weekend's case" if live else "From the archive"
    return f"""<body>
<p class="crumb"><a href="{base_url}/">LocalSpot {html.escape(area_name)}</a> &rsaquo; <a href="{index_url}">The weekend case</a></p>
<p class="eyebrow eyebrow-now">{eyebrow} &middot; No. {case['number']} &middot; {_day_label(case['publish'])}</p>
<h1>{html.escape(case['title'])}</h1>
<button type="button" class="linkish" id="howto-open">How to play</button>

<div class="card card-pad howto" id="howto" hidden>
<p class="eyebrow">How to play</p>
<ul>
<li>{n} suspects were out. Each was at a different place, at a different hour, carrying a different thing. Nobody shares.</li>
<li>Read what the neighbors say. Every statement is true, and together they are enough. No guessing needed.</li>
<li>Use the grid for notes: tap a square once for &#10007;, twice for &#10003;, a third time to clear. The tabs switch between {dims}.</li>
<li>Tap a statement to cross it off once you have used it.</li>
<li>When you know who was at {html.escape(culprit_place)}, name them at the bottom.</li>
</ul>
<button type="button" class="btn btn-primary btn-sm" id="howto-ok">Got it</button>
</div>

<article class="scene">
{scene}
</article>
<p class="question">{html.escape(case['question'])}</p>

<div class="section-head"><h2>Your notes</h2><span class="meta" id="timer">0:00</span></div>
<div class="tabs" id="tabs" role="tablist"></div>
<p class="meta" id="grid-q"></p>
<div class="gridwrap"><table class="grid" id="grid"></table></div>
<p class="gridfoot"><button type="button" class="linkish" id="clear">Clear grid</button></p>
<noscript><p class="meta">The notes grid needs JavaScript. The statements below are all you need.</p></noscript>

<h2>What the neighbors say</h2>
<ol class="clues" id="clues">
{clues}
</ol>

<section class="card card-pad accuse">
<p class="eyebrow">{html.escape(case['question'])}</p>
<div class="pick" id="pick">
<select id="who" aria-label="Who was it?"><option value="">Pick a name</option>
{options}
</select>
<button type="button" class="btn btn-primary" id="accuse">Name them</button>
</div>
<div id="result" aria-live="polite"></div>
</section>

{_signup(area_config)}

{archive}

<footer>A new case every Thursday &middot; <a href="{base_url}/this-weekend/">This weekend in {html.escape(area_name)}</a> &middot; <a href="{base_url}/">Everything happening in {html.escape(area_name)} &rarr;</a></footer>
{_SCRIPT.replace('__DATA__', data)}
</body>
</html>
"""


def _case_page(case, area_config, others, live, at_index):
    area_name = area_config['name']
    base_url = area_config['meta']['canonical_url'].rstrip('/')
    here = f"{base_url}/{INDEX_DIR}/" + ('' if at_index else f"{case['slug']}/")
    title = (f"The Weekend Case: {case['title']} | LocalSpot {area_name}" if at_index else
             f"Weekend Case No. {case['number']}: {case['title']} | LocalSpot {area_name}")
    head = _head(title, case['teaser'], here, area_name, depth=1 if at_index else 2,
                 og_image=area_config['meta'].get('og_image', ''))
    return head + _case_body(case, area_config, others, live)


def _teaser_page(next_case, area_config):
    """Before the first case: a page that says when it starts. Kept out of the
    sitemap and the search index; nothing links to it until a case is live."""
    area_name = area_config['name']
    base_url = area_config['meta']['canonical_url'].rstrip('/')
    here = f"{base_url}/{INDEX_DIR}/"
    when = f"Thursday, {_day_label(next_case['publish']).split(', ', 1)[1]}" if next_case else 'soon'
    head = _head(f"The Weekend Case | LocalSpot {area_name}",
                 f"A small mystery set around {area_name}, out every Thursday.",
                 here, area_name, depth=1, robots='noindex, follow')
    return head + f"""<body>
<p class="crumb"><a href="{base_url}/">LocalSpot {html.escape(area_name)}</a> &rsaquo; The weekend case</p>
<h1>The weekend case</h1>
<article class="scene">
<p>A small mystery set around {html.escape(area_name)}, out every Thursday. Something goes missing, five neighbors were out, and what they say is enough to work out who did it. About ten minutes, no guessing.</p>
<p>The first case opens {when}.</p>
</article>
{_signup(area_config)}
<footer><a href="{base_url}/this-weekend/">This weekend in {html.escape(area_name)}</a> &middot; <a href="{base_url}/">Everything happening in {html.escape(area_name)} &rarr;</a></footer>
</body>
</html>
"""


def generate_case_pages(cases_file, output_dir, area_config, today=None):
    """Write the live case, the archive and the teaser. Returns the published
    slugs for the sitemap; an empty list means nothing is live yet."""
    cases = load_cases(cases_file)
    out = os.path.join(output_dir, INDEX_DIR)
    if os.path.isdir(out):
        shutil.rmtree(out)
    if not cases:
        return []

    pub = published(cases, today)
    os.makedirs(out, exist_ok=True)
    if not pub:
        nxt = upcoming(cases, today)
        with open(os.path.join(out, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(_teaser_page(nxt[0] if nxt else None, area_config))
        print(f">> Weekend case: none live yet, teaser -> {out}")
        return []

    live = pub[-1]
    for case in pub:
        page_dir = os.path.join(out, case['slug'])
        os.makedirs(page_dir, exist_ok=True)
        others = [c for c in pub if c is not case]
        with open(os.path.join(page_dir, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(_case_page(case, area_config, others, case is live, at_index=False))
    with open(os.path.join(out, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(_case_page(live, area_config, pub[:-1], True, at_index=True))

    print(f">> Weekend case: No. {live['number']} live, {len(pub)} published -> {out}")
    return [c['slug'] for c in pub]

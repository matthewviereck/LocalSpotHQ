"""Check discovered events against the pages they cite, before they commit.

The discovery routine has shipped last year's events more than once, because a
venue listing prints "Sep 19" with no year and a carried-forward file quietly
re-dates it. The tells are cheap (see the 2026-09-04 vault entry): the event's
year should appear next to its month/day on the source page, and when the page
prints a weekday it must match the weekday that date falls on this year.

This script does the deterministic half. For every event in an area's
discovered_events.json it fetches `action_link`, finds the event's month/day on
the page, and reports one finding per event:

  strong  WRONG_YEAR        the page pairs that month/day with a different year
          WEEKDAY_MISMATCH  the page's weekday does not fit the date this year
          PAST              the date has already passed
  weak    NOT_ON_PAGE       the month/day never appears (listing pages paginate,
                            so this is a prompt to look, not a verdict)
          NO_YEAR_ON_PAGE   month/day found, but no year and no weekday nearby
  blocked FETCH_403 / FETCH_404 / FETCH_ERROR   needs a browser or is dead
  ok      YEAR_CONFIRMED    the page prints the same year
          WEEKDAY_CONFIRMED no year printed, but the weekday fits this year

Report-only: exit 0 always unless --strict, which exits 1 on any strong
finding. The event-verifier agent reads the JSON and does the judgment half
for weak and blocked items.

    python scripts/verify_discovered.py --area west_chester
    python scripts/verify_discovered.py --area phoenixville --changed --json
"""

import argparse
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import requests
from bs4 import BeautifulSoup

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from scrapers.http_headers import BROWSER_HEADERS  # noqa: E402

MONTHS = {
    'jan': 1, 'january': 1, 'feb': 2, 'february': 2, 'mar': 3, 'march': 3,
    'apr': 4, 'april': 4, 'may': 5, 'jun': 6, 'june': 6, 'jul': 7, 'july': 7,
    'aug': 8, 'august': 8, 'sep': 9, 'sept': 9, 'september': 9,
    'oct': 10, 'october': 10, 'nov': 11, 'november': 11, 'dec': 12, 'december': 12,
}
MONTH_WORDS = {
    1: ['january', 'jan'], 2: ['february', 'feb'], 3: ['march', 'mar'],
    4: ['april', 'apr'], 5: ['may'], 6: ['june', 'jun'], 7: ['july', 'jul'],
    8: ['august', 'aug'], 9: ['september', 'sept', 'sep'], 10: ['october', 'oct'],
    11: ['november', 'nov'], 12: ['december', 'dec'],
}
WEEKDAYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

_RECORD_DATE = re.compile(
    r'([A-Za-z]+)\.?\s+(\d{1,2})(?:\s*[-–]\s*(?:([A-Za-z]+)\.?\s+)?\d{1,2})?,?\s+(\d{4})')
# Between a month/day and its year the page may print "th", a range end,
# "through", or punctuation - but not a time or a sentence.
_YEAR_AFTER = re.compile(
    r'^(?:\s*(?:,|\.|-|–|—|/|&|to|through|thru|and|until|\d{1,2}(?:st|nd|rd|th)?)\s*){0,5}(20\d\d)\b')
_WEEKDAY_BEFORE = re.compile(r'\b(mon|tue|wed|thu|fri|sat|sun)[a-z]*\.?,?\s*$')


def parse_record_date(raw):
    """(year, month, day) from a discovered event's raw_date_string, else None."""
    m = _RECORD_DATE.search(raw or '')
    if not m:
        return None
    month = MONTHS.get(m.group(1).lower())
    if not month:
        return None
    year = int(m.group(4))
    # "Nov 20 - Jan 10, 2027": the single year belongs to the range's end, so
    # a range that runs backwards through the calendar starts the year before.
    end_month = MONTHS.get((m.group(3) or '').lower())
    if end_month and end_month < month:
        year -= 1
    try:
        return date(year, month, int(m.group(2)))
    except ValueError:
        return None


def fetch(url):
    """(status, text) - status is an int, 'error' or 'skip'."""
    if not url or not url.startswith('http'):
        return 'skip', ''
    try:
        r = requests.get(url, headers=BROWSER_HEADERS, timeout=20, allow_redirects=True)
    except requests.RequestException as e:
        return 'error', str(e)[:120]
    if r.status_code != 200:
        return r.status_code, ''
    soup = BeautifulSoup(r.text, 'html.parser')
    for tag in soup(['script', 'style', 'noscript']):
        tag.decompose()
    text = soup.get_text(' ')
    return 200, re.sub(r'\s+', ' ', text).lower()


def scan_page(text, when):
    """Look for `when`'s month/day on the page; return (finding, detail)."""
    words = '|'.join(MONTH_WORDS[when.month])
    day = when.day
    textual = re.compile(r'\b(?:%s)\.?\s+%d(?:st|nd|rd|th)?\b(?!\s*[:/])' % (words, day))
    numeric = re.compile(r'\b0?%d/0?%d/(20\d\d|\d\d)\b' % (when.month, day))
    iso = re.compile(r'\b(20\d\d)-%02d-%02d\b' % (when.month, day))

    years, weekdays, hits = [], [], 0
    for m in textual.finditer(text):
        hits += 1
        after = _YEAR_AFTER.match(text[m.end():m.end() + 40])
        if after:
            years.append(int(after.group(1)))
        before = _WEEKDAY_BEFORE.search(text[max(0, m.start() - 16):m.start()])
        if before:
            weekdays.append(before.group(1))
    for m in numeric.finditer(text):
        hits += 1
        y = int(m.group(1))
        years.append(y if y > 99 else 2000 + y)
    for m in iso.finditer(text):
        hits += 1
        years.append(int(m.group(1)))

    if hits == 0:
        return 'NOT_ON_PAGE', 'month/day not found in page text'
    if when.year in years:
        return 'YEAR_CONFIRMED', 'page prints %d next to the date' % when.year
    if years:
        seen = sorted(set(years))
        return 'WRONG_YEAR', 'page pairs this date with %s, not %d' % (
            '/'.join(str(y) for y in seen), when.year)

    expected = WEEKDAYS[when.weekday()][:3]
    if weekdays:
        if expected in weekdays:
            return 'WEEKDAY_CONFIRMED', 'page says %s, which fits %d' % (
                WEEKDAYS[when.weekday()], when.year)
        fits = [y for y in range(when.year - 2, when.year + 3)
                if _safe_weekday(y, when.month, when.day) == weekdays[0]]
        return 'WEEKDAY_MISMATCH', 'page says %s; in %d that date is a %s (a %s fits %s)' % (
            weekdays[0], when.year, WEEKDAYS[when.weekday()], weekdays[0],
            '/'.join(str(y) for y in fits) or 'no nearby year')
    return 'NO_YEAR_ON_PAGE', 'month/day found %d time(s), no year or weekday beside it' % hits


def _safe_weekday(y, m, d):
    try:
        return WEEKDAYS[date(y, m, d).weekday()][:3]
    except ValueError:
        return None


SEVERITY = {
    'WRONG_YEAR': 'strong', 'WEEKDAY_MISMATCH': 'strong', 'PAST': 'strong',
    'BAD_DATE': 'strong',
    'NOT_ON_PAGE': 'weak', 'NO_YEAR_ON_PAGE': 'weak',
    'YEAR_CONFIRMED': 'ok', 'WEEKDAY_CONFIRMED': 'ok',
}


def severity(finding):
    if finding.startswith('FETCH_') or finding == 'NO_LINK':
        return 'blocked'
    return SEVERITY.get(finding, 'weak')


def changed_ids(path):
    """Ids new or re-dated since HEAD; None when there is no committed copy."""
    rel = os.path.relpath(path, ROOT).replace('\\', '/')
    try:
        old = subprocess.run(['git', 'show', 'HEAD:' + rel], cwd=ROOT, capture_output=True,
                             text=True, encoding='utf-8', check=True).stdout
        before = {e['id']: e.get('raw_date_string') for e in json.loads(old)}
    except (subprocess.CalledProcessError, ValueError):
        return None
    with open(path, encoding='utf-8') as f:
        now = json.load(f)
    return {e['id'] for e in now if before.get(e['id']) != e.get('raw_date_string')}


def verify(area, only_changed=False, today=None):
    today = today or date.today()
    path = os.path.join(ROOT, 'data', area, 'scraped', 'discovered_events.json')
    with open(path, encoding='utf-8') as f:
        events = json.load(f)
    subset = changed_ids(path) if only_changed else None
    if subset is not None:
        events = [e for e in events if e['id'] in subset]

    urls = {e.get('action_link', '') for e in events}
    with ThreadPoolExecutor(max_workers=8) as pool:
        pages = dict(zip(urls, pool.map(fetch, urls)))

    results = []
    for e in events:
        when = parse_record_date(e.get('raw_date_string', ''))
        row = {'id': e['id'], 'title': e.get('title', ''), 'date': e.get('raw_date_string', ''),
               'venue': (e.get('venue_info') or {}).get('name', ''), 'url': e.get('action_link', '')}
        if when is None:
            row.update(finding='BAD_DATE', detail='raw_date_string has no parseable Mon DD, YYYY')
        elif when < today:
            row.update(finding='PAST', detail='%s is before today (%s)' % (when.isoformat(), today.isoformat()))
        else:
            status, text = pages.get(row['url'], ('skip', ''))
            if status == 'skip':
                row.update(finding='NO_LINK', detail='action_link is not an http URL')
            elif status == 'error':
                row.update(finding='FETCH_ERROR', detail=text)
            elif status != 200:
                row.update(finding='FETCH_%s' % status, detail='source returned HTTP %s' % status)
            else:
                finding, detail = scan_page(text, when)
                row.update(finding=finding, detail=detail)
        row['severity'] = severity(row['finding'])
        results.append(row)
    return results


def markdown(area, results):
    order = ['strong', 'blocked', 'weak', 'ok']
    counts = {s: sum(1 for r in results if r['severity'] == s) for s in order}
    out = ['## Discovered-event check: %s' % area, '',
           '%d events - strong %d, blocked %d, weak %d, ok %d' % (
               len(results), counts['strong'], counts['blocked'], counts['weak'], counts['ok']), '']
    for sev in order[:3]:
        rows = [r for r in results if r['severity'] == sev]
        if not rows:
            continue
        out += ['### %s (%d)' % (sev, len(rows)), '',
                '| id | title | date | finding | detail |', '|---|---|---|---|---|']
        for r in rows:
            out.append('| `%s` | %s | %s | **%s** | %s |' % (
                r['id'], r['title'][:50], r['date'], r['finding'], r['detail']))
        out.append('')
    return '\n'.join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--area', required=True)
    ap.add_argument('--changed', action='store_true',
                    help='only events new or re-dated since the committed file')
    ap.add_argument('--json', action='store_true', help='print JSON instead of markdown')
    ap.add_argument('--strict', action='store_true', help='exit 1 on any strong finding')
    args = ap.parse_args()

    results = verify(args.area, only_changed=args.changed)
    if args.json:
        print(json.dumps(results, indent=1))
    else:
        print(markdown(args.area, results))
    if args.strict and any(r['severity'] == 'strong' for r in results):
        sys.exit(1)


if __name__ == '__main__':
    main()

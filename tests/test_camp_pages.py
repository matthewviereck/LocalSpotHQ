"""Camp week planner (pipeline/camps.py): the real data file is valid, last
season's weeks land on the right Mondays, and the page stays out of search
until the data says live.

    python -m unittest tests.test_camp_pages
"""

import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from pipeline import camps, event_pages  # noqa: E402

AREA = {'name': 'Testville', 'slug': 'testville',
        'meta': {'canonical_url': 'https://example.com/testville/',
                 'og_image': 'https://example.com/og.png'}}

CAMP = {
    'id': 'test-camp', 'name': 'Camp <Test> & Co', 'organizer': 'Test Rec', 'town': 'Testville',
    'place': '1 Main St', 'miles': 1.0, 'ages': '5 to 12', 'age_min': 5, 'age_max': 12,
    'day': 'full', 'hours': '9 to 4', 'care': 'Not posted', 'price': '$300 a week',
    'price_week': 300, 'weeks_year': 2026,
    'weeks': ['2026-06-15', '2026-08-24', '2026-08-31'],
    'signup': 'Not posted', 'key_date': None, 'key_date_label': '',
    'link': 'https://example.org/camp?a=1&b=2', 'source': 'https://example.org/source',
    'checked': '2026-11-13', 'note': 'A <b>note</b>',
}
DATA = {'live': False, 'season': 2027, 'grid_start': '2027-06-14', 'grid_weeks': 11,
        'updated': '2026-11-13', 'camps': [CAMP]}


class RealData(unittest.TestCase):
    def test_phoenixville_file_is_valid(self):
        data = camps.load_camps(os.path.join(ROOT, 'data', 'phoenixville', 'camps.json'))
        self.assertIsNotNone(data)
        self.assertEqual(camps.validate(data), [])
        self.assertEqual(len({c['id'] for c in data['camps']}), len(data['camps']))

    def test_every_camp_has_a_source_and_a_check_date(self):
        data = camps.load_camps(os.path.join(ROOT, 'data', 'phoenixville', 'camps.json'))
        for c in data['camps']:
            self.assertTrue(c['source'].startswith('https://'), c['id'])
            date.fromisoformat(c['checked'])


class Weeks(unittest.TestCase):
    def test_grid_is_eleven_mondays_from_june_14(self):
        grid = camps.grid_weeks(DATA)
        self.assertEqual(len(grid), 11)
        self.assertEqual(grid[0], date(2027, 6, 14))
        self.assertEqual(grid[-1], date(2027, 8, 23))
        self.assertTrue(all(d.weekday() == 0 for d in grid))

    def test_last_season_moves_to_the_same_week_of_summer(self):
        # 2026-06-15 + 364 days = 2027-06-14 (week 0); 2026-08-24 -> 2027-08-23
        # (week 10); 2026-08-31 -> 2027-08-30 falls past the grid.
        on, off = camps.camp_weeks(CAMP, DATA)
        self.assertEqual(on, [0, 10])
        self.assertEqual(off, 1)
        self.assertEqual(camps.basis(CAMP, DATA), 'last')

    def test_this_season_weeks_are_used_as_posted(self):
        c = dict(CAMP, weeks_year=2027, weeks=['2027-06-21', '2027-07-05'])
        self.assertEqual(camps.camp_weeks(c, DATA), ([1, 3], 0))
        self.assertEqual(camps.basis(c, DATA), 'posted')
        self.assertEqual(camps.basis(dict(c, year_printed=False), DATA), 'noyear')


class Validate(unittest.TestCase):
    def check(self, **change):
        d = copy.deepcopy(DATA)
        d['camps'][0].update(change)
        return camps.validate(d)

    def test_good_row_passes(self):
        self.assertEqual(camps.validate(DATA), [])

    def test_bad_rows_are_caught(self):
        self.assertTrue(self.check(weeks=['2026-06-16']))          # a Tuesday
        self.assertTrue(self.check(source=''))
        self.assertTrue(self.check(link='http://insecure.example'))
        self.assertTrue(self.check(day='morning'))
        self.assertTrue(self.check(price_week='300'))
        self.assertTrue(self.check(price_half='150'))
        self.assertTrue(self.check(key_date='2027-01-20', key_date_label=''))
        self.assertTrue(self.check(weeks=['2026-09-07']))           # nothing on the grid
        self.assertTrue(self.check(checked='Nov 13'))
        self.assertTrue(self.check(miles=None))
        self.assertTrue(self.check(weeks_year=2028))
        self.assertTrue(self.check(age_min=13, age_max=5))

    def test_invalid_file_fails_the_build(self):
        tmp = tempfile.mkdtemp()
        try:
            d = copy.deepcopy(DATA)
            d['camps'][0]['weeks'] = ['not a date']
            path = os.path.join(tmp, 'camps.json')
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(d, f)
            with self.assertRaises(ValueError):
                camps.generate_camp_pages(path, tmp, AREA)
        finally:
            shutil.rmtree(tmp)


class Page(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def build(self, data):
        path = os.path.join(self.tmp, 'camps.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f)
        live = camps.generate_camp_pages(path, self.tmp, AREA)
        with open(os.path.join(self.tmp, 'camps', 'index.html'), encoding='utf-8') as f:
            return live, f.read()

    def test_not_live_is_noindex_and_left_out_of_the_sitemap(self):
        live, page = self.build(DATA)
        self.assertFalse(live)
        self.assertIn('content="noindex, follow"', page)
        event_pages.generate_area_sitemap(self.tmp, AREA, [], camps_live=live)
        with open(os.path.join(self.tmp, 'sitemap.xml'), encoding='utf-8') as f:
            self.assertNotIn('/camps/', f.read())

    def test_live_is_indexed_and_in_the_sitemap(self):
        live, page = self.build(dict(DATA, live=True))
        self.assertTrue(live)
        self.assertIn('content="index, follow"', page)
        event_pages.generate_area_sitemap(self.tmp, AREA, [], camps_live=live)
        with open(os.path.join(self.tmp, 'sitemap.xml'), encoding='utf-8') as f:
            self.assertIn('https://example.com/testville/camps/', f.read())

    def test_text_is_escaped_and_facts_are_on_the_page(self):
        _, page = self.build(DATA)
        self.assertIn('Camp &lt;Test&gt; &amp; Co', page)
        self.assertNotIn('<b>note</b>', page)
        self.assertIn('href="https://example.org/camp?a=1&amp;b=2"', page)
        self.assertIn('href="https://example.org/source"', page)
        self.assertIn('Checked November 13, 2026', page)
        self.assertIn('2026 schedule; 2027 not posted yet', page)
        self.assertIn('Also runs 1 week outside this grid.', page)
        self.assertIn('G-FXMDYPK8KZ', page)

    def test_weeks_offered_are_buttons_and_the_rest_are_not(self):
        _, page = self.build(DATA)
        self.assertEqual(page.count('<button type="button" class="wk'), 2)
        self.assertEqual(page.count('class="wk none"'), 9)

    def test_clicks_are_counted_only_when_live_on_the_real_host(self):
        _, page = self.build(DATA)
        self.assertIn('var LIVE = D.live && /(^|\\.)localspothq\\.com$/.test(location.hostname);', page)
        self.assertIn('"live": false', page)
        self.assertIn('track("camp_click"', page)

    def test_picks_never_leave_the_browser_and_the_page_says_so(self):
        _, page = self.build(DATA)
        self.assertNotIn('camp_pick', page)
        self.assertEqual(page.count('track('), 2)   # the definition and camp_click
        self.assertIn('Your picks are saved in this browser and are not sent to us.', page)
        self.assertNotIn('nowhere else', page)

    def test_page_script_parses(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('node not installed')
        _, page = self.build(DATA)
        script = page.rsplit('<script>', 1)[1].split('</script>', 1)[0]
        path = os.path.join(self.tmp, 'page.js')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(script)
        run = subprocess.run([node, '--check', path], capture_output=True, text=True, timeout=60)
        self.assertEqual(run.returncode, 0, run.stderr)

    def test_no_file_means_no_page(self):
        self.assertFalse(camps.generate_camp_pages(os.path.join(self.tmp, 'none.json'), self.tmp, AREA))
        self.assertFalse(os.path.exists(os.path.join(self.tmp, 'camps')))


# The planner's logic, run in Node against a small fixture. Each check names
# the review finding it guards (stale picks, overlaps, minimum weeks, dates).
LOGIC_TESTS = r"""
function eq(a, b, msg){
  if (JSON.stringify(a) !== JSON.stringify(b))
    throw new Error(msg + ": got " + JSON.stringify(a) + ", want " + JSON.stringify(b));
}
var W = ["2027-06-14", "2027-06-21", "2027-06-28", "2027-07-05"];
function camp(id, day, weeks, extra){
  var c = {id: id, name: id, town: "A", day: day, weeks: weeks, amin: null, amax: null,
           price: null, priceHalf: null, whole: false, min: 1, keyDate: null, keyLabel: ""};
  for (var k in extra) c[k] = extra[k];
  return c;
}
var D = {season: 2027, live: false, weeks: W.map(function(iso){ return {iso: iso, label: iso.slice(5)}; }), camps: [
  camp("full", "full", [0, 1, 2, 3], {amin: 5, amax: 12, price: 300, keyDate: "2026-12-01", keyLabel: "early bird ends"}),
  camp("half", "half", [0, 1], {amin: 3, price: 150, town: "B", keyDate: "2027-01-20", keyLabel: "opens"}),
  camp("half2", "half", [0], {price: 100}),
  camp("both", "both", [2], {price: 600, priceHalf: 250}),
  camp("whole", "full", [1, 2], {price: 170, whole: true}),
  camp("block", "full", [0, 1, 2, 3], {price: 600, min: 2}),
  camp("free", "full", [3], {})
]};
var by = campById(D);

// Saved state: junk, stale weeks, duplicates, unknown camps and bad filters are dropped.
eq(sanitize(null, D), {picks: {}, f: {}}, "null state");
eq(sanitize("junk", D), {picks: {}, f: {}}, "string state");
eq(sanitize({picks: {full: [W[1], W[0], W[0], "2027-09-06", 3], gone: [W[0]], half: [W[2]], whole: "x"},
             f: {age: "7", town: 5, week: 99}}, D),
   {picks: {full: [W[0], W[1]]}, f: {age: "7"}}, "stale and bad picks");
eq(sanitize({picks: {}, f: {week: 2}}, D).f, {week: 2}, "week filter kept when on the grid");

// Whole session camps pick and drop every week together.
var p = toggle({}, by.whole, D, 1, true);
eq(p, {whole: [W[1], W[2]]}, "whole session on");
eq(toggle(p, by.whole, D, 2, false), {}, "whole session off");

// Totals, coverage, overlaps.
var s = summarize({full: [W[0], W[1]], half: [W[0]]}, D);
eq([s.total, s.unpriced, s.covered, s.open, s.overlap, s.halfOnly], [750, 0, 2, [2, 3], [0], []], "full plus half");
s = summarize({half: [W[0]], half2: [W[0]]}, D);
eq([s.overlap, s.halfOnly, s.covered], [[], [0], 1], "two half days are not an overlap");
s = summarize({free: [W[3]]}, D);
eq([s.total, s.unpriced, s.any], [0, 1, true], "unpriced only");
eq(summarize({block: [W[0]]}, D).short, [{name: "block", min: 2, have: 1}], "below the minimum");
eq(summarize({block: [W[0], W[1]]}, D).short, [], "at the minimum");
eq(summarize({full: ["2030-01-07"]}, D).covered, 0, "a stale week counts for nothing");

// Dates use the local day, not UTC (11:30 PM on Nov 20 is still Nov 20).
eq(isoToday(new Date(2026, 10, 20, 23, 30)), "2026-11-20", "local today");
eq(nextDates({}, D, "2026-12-01").map(function(c){ return c.id; }), ["full", "half"], "due today still shows");
eq(nextDates({}, D, "2026-12-02").map(function(c){ return c.id; }), ["half"], "past dates drop");
eq(nextDates({half: [W[0]]}, D, "2026-11-13").map(function(c){ return c.id; }), ["half"], "only picked camps");

// Filters: age, town, day, price (half day price when it exists), week.
eq(matches(by.full, {age: "4"}), false, "too young");
eq(matches(by.half, {age: "4"}), true, "no upper age");
eq(matches(by.half, {town: "A"}), false, "town");
eq(matches(by.full, {day: "half"}), false, "full day hidden for half");
eq(matches(by.both, {day: "half", max: "300"}), true, "half day price under the cap");
eq(matches(by.both, {day: "full", max: "300"}), false, "full day price over the cap");
eq(matches(by.both, {max: "300"}), true, "either day uses the lower price");
eq(matches(by.free, {max: "200"}), true, "no price posted stays visible");
eq(matches(by.half, {week: 2}), false, "week filter");
console.log("OK");
"""


class PlannerLogic(unittest.TestCase):
    def test_logic_in_node(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('node not installed')
        tmp = tempfile.mkdtemp()
        try:
            path = os.path.join(tmp, 'logic.js')
            with open(path, 'w', encoding='utf-8') as f:
                f.write(camps.LOGIC_JS + '\n' + LOGIC_TESTS)
            run = subprocess.run([node, path], capture_output=True, text=True, timeout=60)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertIn('OK', run.stdout)
        finally:
            shutil.rmtree(tmp)


if __name__ == '__main__':
    unittest.main()

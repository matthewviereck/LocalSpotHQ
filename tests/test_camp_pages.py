"""Camp week planner (pipeline/camps.py): the real data file is valid, last
season's weeks land on the right Mondays, and the page stays out of search
until the data says live.

    python -m unittest tests.test_camp_pages
"""

import copy
import json
import os
import shutil
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
        self.assertTrue(self.check(key_date='2027-01-20', key_date_label=''))
        self.assertTrue(self.check(weeks=['2026-09-07']))           # nothing on the grid

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

    def test_clicks_are_counted_only_on_the_live_host(self):
        _, page = self.build(DATA)
        self.assertIn('localspothq\\.com$/.test(location.hostname)', page)
        self.assertIn('track("camp_click"', page)

    def test_no_file_means_no_page(self):
        self.assertFalse(camps.generate_camp_pages(os.path.join(self.tmp, 'none.json'), self.tmp, AREA))
        self.assertFalse(os.path.exists(os.path.join(self.tmp, 'camps')))


if __name__ == '__main__':
    unittest.main()

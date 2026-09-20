"""The site root (pipeline/hub.py): rendered from town data, not a template.

    python -m unittest tests.test_hub
"""

import os
import sys
import unittest
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline import hub  # noqa: E402


def _ev(title, slug, d, loc='The Hall', time='7pm', label=None):
    ts = datetime(d.year, d.month, d.day).timestamp()
    return {'title': title, 'slug': slug, 'loc': loc, 'time': time, '_sort_date': ts,
            'date': label or f"{d.strftime('%b')} {d.day}"}


TODAY = date(2026, 9, 20)


def _blocks():
    return [
        {'slug': 'phoenixville', 'name': 'Phoenixville', 'tagline': 'Phoenixville • Oaks',
         'events': [_ev('Undated Thing', 'undated', TODAY) | {'_sort_date': 9999999999},
                    _ev('Car Show', 'car-show', date(2026, 9, 22)),
                    _ev('Film Fest', 'film-fest', TODAY, label='Now through Sep 20'),
                    _ev('Farmers Market', 'farmers-market', TODAY)],
         'guides': [{'slug': 'fall', 'title': 'Fall'}]},
        {'slug': 'west-chester', 'name': 'West Chester', 'tagline': '',
         'events': [], 'guides': []},
    ]


class RootPage(unittest.TestCase):
    def setUp(self):
        self.html = hub.render_hub(_blocks(), TODAY)

    def test_every_town_gets_a_section_with_its_events_soonest_first(self):
        self.assertIn('id="phoenixville"', self.html)
        self.assertIn('id="west-chester"', self.html)
        i_today = self.html.index('/phoenixville/events/farmers-market/')
        i_later = self.html.index('/phoenixville/events/car-show/')
        self.assertLess(i_today, i_later)
        self.assertNotIn('undated', self.html)               # undated rows stay off the front page
        self.assertIn('>Now<', self.html)                    # an open run reads "Now", not a date
        self.assertIn('>Today<', self.html)

    def test_empty_town_still_renders(self):
        self.assertIn('Nothing listed yet', self.html)
        self.assertNotIn('/west-chester/guides/', self.html)  # no guides link without guides
        self.assertIn('/phoenixville/guides/', self.html)

    def test_signup_has_a_town_picker_and_posts_to_subscribe(self):
        self.assertIn('id="signup-town"', self.html)
        self.assertIn('<option value="Phoenixville">', self.html)
        self.assertIn('<option value="West Chester">', self.html)
        self.assertIn('/subscribe.php', self.html)

    def test_no_startup_copy_and_shared_stylesheet(self):
        for phrase in ('Connect in', 'Real Life', 'Why LocalSpot', 'Break free', 'tailwind'):
            self.assertNotIn(phrase, self.html)
        self.assertIn('href="/localspot.css"', self.html)
        self.assertIn('G-FXMDYPK8KZ', self.html)
        self.assertIn('Viereck Group LLC', self.html)


if __name__ == '__main__':
    unittest.main()

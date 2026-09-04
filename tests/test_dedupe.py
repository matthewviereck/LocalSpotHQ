"""Regression tests for the near-duplicate rules in pipeline/transform.py.

    python -m unittest tests.test_dedupe
"""

import os
import sys
import unittest
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline import transform  # noqa: E402
from scrapers.downtown_west_chester import _time_label  # noqa: E402


def _ev(title, img='', time='', loc='West Chester University, West Chester'):
    return {'title': title, 'img': img or 'https://placehold.co/400x300', 'link': '',
            'time': time, 'price': '', 'series': '', 'loc': loc,
            '_sort_date': datetime(2026, 9, 25).timestamp()}


class Dedupe(unittest.TestCase):
    def test_year_and_ordinal_are_not_distinguishing(self):
        self.assertEqual(transform._title_tokens('WCU Homecoming 2026'), {'wcu', 'homecoming'})
        self.assertEqual(transform._title_tokens('29th Annual Kennett Brewfest'),
                         {'annual', 'kennett', 'brewfest'})
        # a year glued to letters is a word, not a year
        self.assertIn('1920s', transform._title_tokens('Roaring 1920s Night'))

    def test_homecoming_from_two_feeds_is_one_event(self):
        feed = _ev('WCU Homecoming 2026', img='https://example.com/homecoming.jpg')
        discovery = _ev('WCU Homecoming & Family Weekend')
        kept = transform.fuzzy_dedupe([feed, discovery])
        self.assertEqual([e['title'] for e in kept], ['WCU Homecoming 2026'])

    def test_umbrella_event_does_not_swallow_sub_events_at_other_venues(self):
        umbrella = _ev('West Chester Comedy Festival 2026', loc='Downtown West Chester, West Chester')
        show = _ev('West Chester Comedy Festival: Friday Headliner Show at Windish Studios',
                   loc='Windish Studios, West Chester')
        game = _ev('WCU Homecoming Football: Golden Rams vs. Millersville', loc='Farrell Stadium, West Chester')
        homecoming = _ev('WCU Homecoming 2026')
        self.assertEqual(len(transform.fuzzy_dedupe([umbrella, show])), 2)
        self.assertEqual(len(transform.fuzzy_dedupe([homecoming, game])), 2)

    def test_same_venue_cross_source_copies_merge(self):
        # "First Friday - July" vs "First Friday - Downtown Phoenixville (July)"
        a = _ev('First Friday - July', loc='Downtown Phoenixville')
        b = _ev('First Friday - Downtown Phoenixville (July)', loc='Downtown Phoenixville, Phoenixville')
        self.assertEqual(len(transform.fuzzy_dedupe([a, b])), 1)

    def test_distinct_same_series_events_stay_distinct(self):
        a = _ev('CIRQUE du BLOBFEST: Costume Contest')
        b = _ev('CIRQUE du BLOBFEST: Blob Ball - Annual Costume Gala')
        self.assertEqual(len(transform.fuzzy_dedupe([a, b])), 2)

    def test_midnight_start_is_not_a_time(self):
        self.assertEqual(_time_label(datetime(2026, 9, 25, 0, 0), all_day=False), '')
        self.assertEqual(_time_label(datetime(2026, 9, 25, 19, 30), all_day=False), '7:30 PM')


if __name__ == '__main__':
    unittest.main()

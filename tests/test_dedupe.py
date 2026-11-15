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


SOULJOELS = "SoulJoel's at SunnyBrook, 50 SunnyBrook Rd, Pottstown"


def _src(title, src, loc=SOULJOELS, town='Pottstown', time='8pm', end_iso=''):
    ev = _ev(title, time=time, loc=loc)
    ev.update({'_src': src, 'town': town, 'end_iso': end_iso})
    return ev


class CrossSourceDedupe(unittest.TestCase):
    """A venue's own calendar and discovery word one show differently
    (pipeline/transform._same_listing_across_sources)."""

    def test_two_sources_naming_one_show_merge_and_the_venue_copy_wins(self):
        disc = _src("Billy Gardell – Live Stand-Up Comedy at SoulJoel's", 'discovered_events.json',
                    time='8:00 PM')
        feed = _src("Comedian Billy Gardell returns to SoulJoel's", 'feed_souljoels.json', time='8 PM')
        for order in ([disc, feed], [feed, disc]):
            kept = transform.fuzzy_dedupe(order)
            self.assertEqual([e['title'] for e in kept], ["Comedian Billy Gardell returns to SoulJoel's"])

    def test_three_shared_name_words_merge(self):
        a = _src('Circle Mirror Transformation by Annie Baker', 'feed_phoenixville_first.json',
                 loc='Phoenixville Recreation Center, 501 Franklin Ave, Phoenixville', town='Phoenixville')
        b = _src('Circle Mirror Transformation – Site Unseen Theatre at Phoenixville Rec',
                 'discovered_events.json', loc='Phoenixville Recreation Center, Phoenixville', town='Phoenixville')
        self.assertEqual(len(transform.fuzzy_dedupe([a, b])), 1)

    def test_one_naming_word_is_enough_when_it_is_the_whole_name(self):
        a = _src('Phoenixivlle Firebird Festival', 'feed_phoenixville_first.json',
                 loc='Reservoir Park, 601 Franklin Ave, Phoenixville', town='Phoenixville')
        b = _src('Phoenixville Firebird Festival 2026', 'discovered_events.json',
                 loc='Downtown Phoenixville', town='Phoenixville')
        self.assertEqual(len(transform.fuzzy_dedupe([a, b])), 1)

    def test_santa_is_not_a_name(self):
        a = _src('Santa at the Square', 'downtown_wc_events.json',
                 loc='Market Square, West Chester', town='West Chester')
        b = _src("Santa's Express 2026", 'discovered_events.json',
                 loc='West Chester Railroad, West Chester', town='West Chester')
        self.assertEqual(len(transform.fuzzy_dedupe([a, b])), 2)

    def test_one_source_never_merges_with_itself(self):
        a = _src("Free Music Open Mic hosted inside Gatsby's Pub", 'feed_souljoels.json', time='7pm')
        b = _src("Comedy Open Mic at SoulJoel's", 'feed_souljoels.json', time='7pm')
        self.assertEqual(len(transform.fuzzy_dedupe([a, b])), 2)

    def test_same_name_in_another_town_is_another_event(self):
        a = _src('Christmas Tree Lighting', 'feed_spring_city_library.json',
                 loc='Spring City Public Library, 245 Broad St, Spring City', town='Spring City')
        b = _src('Kimberton Christmas Tree Lighting', 'discovered_events.json',
                 loc='Kimberton Fire Company, Kimberton', town='Kimberton')
        self.assertEqual(len(transform.fuzzy_dedupe([a, b])), 2)

    def test_holiday_words_are_not_a_name(self):
        a = _src("New Year's Eve Double Headliner Comedy Show", 'feed_souljoels.json')
        b = _src("New Year's Eve at SunnyBrook Ballroom w/ The Uptown Band", 'discovered_events.json')
        self.assertEqual(len(transform.fuzzy_dedupe([a, b])), 2)

    def test_a_festival_run_keeps_its_one_night_shows(self):
        run = _src('BLOBFEST 2027', 'recurring_events.json', loc='The Colonial Theatre', town='Phoenixville',
                   end_iso='2027-07-11')
        night = _src('Blobfest - Opening Night', 'colonial_events.json', loc='The Colonial Theatre',
                     town='Phoenixville')
        self.assertEqual(len(transform.fuzzy_dedupe([run, night])), 2)

    def test_events_without_a_source_keep_the_old_rules(self):
        a = _ev("Billy Gardell – Live Stand-Up Comedy at SoulJoel's", loc=SOULJOELS)
        b = _ev("Comedian Billy Gardell returns to SoulJoel's", loc=SOULJOELS)
        self.assertEqual(len(transform.fuzzy_dedupe([a, b])), 2)


if __name__ == '__main__':
    unittest.main()

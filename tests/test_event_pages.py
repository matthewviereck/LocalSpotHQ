"""Regression tests for the crawl paths on event pages (pipeline/event_pages.py).

    python -m unittest tests.test_event_pages
"""

import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline import event_pages  # noqa: E402

AREA = {'name': 'Testville', 'meta': {'canonical_url': 'https://example.com/testville/'}}


def _ev(title, loc, town, d, slug=None):
    ts = datetime(d.year, d.month, d.day).timestamp()
    return {'title': title, 'loc': loc, 'town': town, '_sort_date': ts,
            'slug': slug or event_pages._slug(title), 'img': '', 'link': '', 'type': 'Event'}


class RelatedLinks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _catalog(self):
        d = date(2026, 10, 3)
        return [
            _ev('Rocky Horror', 'Colonial Theatre', 'Phoenixville', d),
            _ev('Comedy at the Colonial', 'Colonial Theatre, Phoenixville', 'Phoenixville', date(2026, 10, 10)),
            _ev('Blobfest', 'Colonial Theatre', 'Phoenixville', date(2027, 7, 9)),
            _ev('Farmers Market', 'Reeves Park', 'Phoenixville', date(2026, 10, 4)),
            _ev('Car Show', 'Main Street', 'Collegeville', date(2026, 10, 4)),
            _ev('Fall Fest', 'Borough Hall', 'Downingtown', date(2026, 10, 5)),
            _ev('Craft Fair', 'Library', 'Pottstown', date(2026, 10, 6)),
            _ev('Trivia', 'Pub', 'Phoenixville', date(2026, 12, 1)),
        ]

    def test_same_venue_then_same_town_then_nearest(self):
        cat = [(e['slug'], e, datetime.fromtimestamp(e['_sort_date']).date()) for e in self._catalog()]
        slug, ev, d = cat[0]
        picks = [r[0] for r in event_pages._pick_related(slug, ev, d, cat)]
        # venue first (both Colonial spellings), then Phoenixville by date, never itself
        self.assertEqual(picks[:2], ['comedy-at-the-colonial', 'blobfest'])
        self.assertEqual(picks[2:4], ['farmers-market', 'trivia'])
        self.assertEqual(len(picks), event_pages.RELATED_COUNT)
        self.assertNotIn('rocky-horror', picks)

    def test_pages_link_hub_related_and_breadcrumb(self):
        events_file = os.path.join(self.tmp, 'events.json')
        with open(events_file, 'w', encoding='utf-8') as f:
            json.dump(self._catalog(), f)
        out = os.path.join(self.tmp, 'out')
        os.makedirs(out)
        pages = event_pages.generate_event_pages(events_file, out, AREA)
        self.assertEqual(len(pages), 8)
        with open(os.path.join(out, 'events', 'rocky-horror', 'index.html'), encoding='utf-8') as f:
            page = f.read()
        self.assertIn('href="https://example.com/testville/events/comedy-at-the-colonial/"', page)
        self.assertIn('<h2 class="more">More at Colonial Theatre</h2>', page)
        self.assertIn('href="https://example.com/testville/this-weekend/"', page)
        self.assertIn('"@type": "BreadcrumbList"', page)
        self.assertNotIn('href="https://example.com/testville/events/rocky-horror/"', page.split('<body>')[1])
        with open(os.path.join(out, 'events', 'car-show', 'index.html'), encoding='utf-8') as f:
            self.assertIn('<h2 class="more">More in Collegeville</h2>', f.read())


class SearchTitles(unittest.TestCase):
    AREA = {'name': 'West Chester', 'meta': {'canonical_url': 'https://example.com/wc/',
            'title_expansions': {'WCU': 'West Chester University'}}}

    def _title(self, title, town='West Chester', d=date(2026, 9, 27)):
        _, page = event_pages._event_page(_ev(title, 'West Chester University', town, d), d, self.AREA)
        return page.split('<title>')[1].split('</title>')[0]

    def test_abbreviation_expanded_and_town_not_repeated(self):
        # "west chester university homecoming 2026": 345 impressions, 0 clicks on 9/27
        self.assertEqual(self._title('WCU Homecoming 2026'),
                         'West Chester University Homecoming 2026 — Sun Sep 27')

    def test_whole_word_only(self):
        self.assertIn('WCUX Open Mic', self._title('WCUX Open Mic'))

    def test_expansion_dropped_when_it_would_force_a_cut(self):
        long = 'WCU Theatre: Sacco and Vanzetti, A Tragedia'
        self.assertTrue(self._title(long, town='').startswith(long))

    def test_town_kept_when_the_trim_cuts_it_out_of_the_name(self):
        # the expanded name holds "West Chester", but only in the part the trim drops
        self.assertEqual(self._title("Sacco & Vanzetti: A Tragedia dell'Arte (WCU Theatre)",
                                     d=date(2026, 11, 19)),
                         'Sacco &amp; Vanzetti — West Chester, Thu Nov 19')

    def test_h1_and_structured_data_keep_the_listing_name(self):
        _, page = event_pages._event_page(_ev('WCU Homecoming 2026', 'West Chester University',
                                              'West Chester', date(2026, 9, 27)), date(2026, 9, 27), self.AREA)
        self.assertIn('"name": "WCU Homecoming 2026"', page)

    def test_areas_without_expansions_unchanged(self):
        d = date(2026, 9, 27)
        _, page = event_pages._event_page(_ev('WCU Homecoming 2026', 'Campus', 'West Chester', d), d, AREA)
        self.assertIn('<title>WCU Homecoming 2026 — West Chester, Sun Sep 27</title>', page)


if __name__ == '__main__':
    unittest.main()

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


if __name__ == '__main__':
    unittest.main()

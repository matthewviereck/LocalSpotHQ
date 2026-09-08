"""Regression tests for pipeline/slugs.py - the URL-stability rules.

    python -m unittest tests.test_slugs
"""

import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline import slugs  # noqa: E402

AREA = {'name': 'Testville', 'meta': {'canonical_url': 'https://example.com/testville/'}}


def _ev(title, loc, d):
    ts = datetime(d.year, d.month, d.day).timestamp()
    return {'title': title, 'loc': loc, '_sort_date': ts}


class SlugRules(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.events_file = os.path.join(self.tmp, 'events.json')
        self.registry = slugs.SlugRegistry(os.path.join(self.tmp, 'slug_registry.json'))
        self.today = date(2026, 9, 3)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _assign(self, events):
        with open(self.events_file, 'w', encoding='utf-8') as f:
            json.dump(events, f)
        return slugs.assign_slugs(self.events_file, self.registry, today=self.today)

    def test_new_slug_drops_year(self):
        self.assertEqual(slugs.title_slug('WCU Homecoming 2026'), 'wcu-homecoming')
        self.assertEqual(slugs.title_slug('Blobfest 2026 Opening Night'), 'blobfest-opening-night')
        self.assertEqual(slugs.legacy_slug('WCU Homecoming 2026'), 'wcu-homecoming-2026')

    def test_rename_keeps_url(self):
        d = date(2026, 9, 25)
        first = self._assign([_ev('WCU Homecoming Weekend', 'West Chester University, West Chester', d)])
        self.assertEqual(first[0]['slug'], 'wcu-homecoming-weekend')
        renamed = self._assign([_ev('WCU Homecoming & Family Weekend', 'West Chester University', d)])
        self.assertEqual(renamed[0]['slug'], 'wcu-homecoming-weekend')
        self.assertEqual(self.registry.slugs['wcu-homecoming-weekend']['title'],
                         'WCU Homecoming & Family Weekend')

    def test_different_event_same_venue_same_day_gets_own_url(self):
        d = date(2026, 10, 3)
        self._assign([_ev('Comedy at the Colonial: John Moses', 'Colonial Theatre', d)])
        both = self._assign([_ev('Comedy at the Colonial: John Moses', 'Colonial Theatre', d),
                             _ev('Rocky Horror Picture Show', 'Colonial Theatre', d)])
        self.assertEqual([e['slug'] for e in both],
                         ['comedy-at-the-colonial-john-moses', 'rocky-horror-picture-show'])

    def test_annual_repeat_inherits_url(self):
        self._assign([_ev('Phoenixville Blues Festival – Labor Day 2026', 'Reeves Park', date(2026, 9, 7))])
        nxt = self._assign([_ev('Phoenixville Blues Festival - Labor Day 2027', 'Reeves Park, Phoenixville', date(2027, 9, 6))])
        self.assertEqual(nxt[0]['slug'], 'phoenixville-blues-festival-labor-day')

    def test_same_title_collapses_to_one_page(self):
        evs = [_ev('WCU Homecoming 2026', 'West Chester University', date(2026, 9, 25) + timedelta(days=i))
               for i in range(3)]
        out = self._assign(evs)
        self.assertEqual({e['slug'] for e in out}, {'wcu-homecoming'})
        self.assertEqual(len(self.registry.slugs), 1)

    def test_retired_slug_redirects_stubs_or_goes(self):
        out_dir = os.path.join(self.tmp, 'out')
        os.makedirs(os.path.join(out_dir, 'events'))
        # superseded (same venue+date, similar title), recently ended, long gone
        self.registry.slugs = {
            'josh-blue': {'title': 'Josh Blue', 'venue': 'Uptown Knauer Performing Arts Center, West Chester', 'date': '2026-10-16',
                          'first_seen': '2026-07-18', 'last_seen': '2026-09-01'},
            'blobfest-opening-night': {'title': 'Blobfest Opening Night', 'venue': 'Colonial Theatre',
                                       'date': '2026-08-20', 'first_seen': '2026-06-01', 'last_seen': '2026-08-20'},
            'ancient-history': {'title': 'Ancient History', 'venue': 'Somewhere', 'date': '2025-01-01',
                                'first_seen': '2025-01-01', 'last_seen': '2025-01-01'},
            'forgotten': {'title': 'Forgotten', 'venue': 'Somewhere', 'date': '2020-01-01',
                          'first_seen': '2020-01-01', 'last_seen': '2020-01-01'},
        }
        live = [_ev('Josh Blue: The Road Dog Tour', 'Uptown! Knauer Performing Arts Center', date(2026, 10, 16))]
        live[0]['slug'] = 'josh-blue-the-road-dog-tour'
        result = slugs.emit_retired(self.registry, live, out_dir, AREA, today=self.today)
        self.assertEqual(result['redirects'], [('josh-blue', 'josh-blue-the-road-dog-tour')])
        self.assertEqual(result['stubs'], [('blobfest-opening-night', True)])
        self.assertEqual(result['gone'], ['ancient-history'])
        self.assertEqual(result['pruned'], ['forgotten'])
        self.assertNotIn('forgotten', self.registry.slugs)
        with open(os.path.join(out_dir, '.htaccess'), encoding='utf-8') as f:
            rules = f.read()
        self.assertIn('RewriteRule ^events/josh\\-blue/?$ https://example.com/testville/events/josh-blue-the-road-dog-tour/ [R=301,L]', rules)
        self.assertIn('RewriteRule ^events/ancient\\-history/?$ - [G,L]', rules)
        with open(os.path.join(out_dir, 'events', 'blobfest-opening-night', 'index.html'), encoding='utf-8') as f:
            stub = f.read()
        self.assertIn('content="index, follow"', stub)
        self.assertIn('took place on Thursday, August 20, 2026', stub)

    def test_dropped_future_listing_stub_is_noindex(self):
        out_dir = os.path.join(self.tmp, 'out')
        os.makedirs(os.path.join(out_dir, 'events'))
        self.registry.slugs = {'vanished': {'title': 'Vanished', 'venue': 'Bar', 'date': '2026-09-20',
                                            'first_seen': '2026-08-01', 'last_seen': '2026-08-01'}}
        result = slugs.emit_retired(self.registry, [], out_dir, AREA, today=self.today)
        self.assertEqual(result['stubs'], [('vanished', False)])


    def test_retitled_day_of_multiday_event_shares_the_oldest_url(self):
        # A feed lists "WCU Homecoming 2026" once per day; the merge kept
        # discovery's copy ("WCU Homecoming Weekend") for the Saturday. Both
        # titles are registered - the older URL is the ranked one and wins.
        self.registry.slugs = {
            'wcu-homecoming-weekend': {'title': 'WCU Homecoming Weekend', 'venue': 'West Chester University, West Chester',
                                       'date': '2026-09-26', 'first_seen': '2026-08-28', 'last_seen': '2026-09-07'},
            'wcu-homecoming-2026': {'title': 'WCU Homecoming 2026', 'venue': 'West Chester University, West Chester',
                                    'date': '2026-09-25', 'first_seen': '2026-09-01', 'last_seen': '2026-09-07'},
        }
        venue = 'West Chester University, West Chester'
        out = self._assign([_ev('WCU Homecoming 2026', venue, date(2026, 9, 25)),
                            _ev('WCU Homecoming Weekend', venue, date(2026, 9, 26)),
                            _ev('WCU Homecoming 2026', venue, date(2026, 9, 27)),
                            _ev('WCU Homecoming Football: Golden Rams vs. Millersville', 'Farrell Stadium', date(2026, 9, 26))])
        self.assertEqual([e['slug'] for e in out],
                         ['wcu-homecoming-weekend'] * 3 + ['wcu-homecoming-football-golden-rams-vs-millersville'])
        out_dir = os.path.join(self.tmp, 'out')
        os.makedirs(os.path.join(out_dir, 'events'))
        result = slugs.emit_retired(self.registry, out, out_dir, AREA, today=self.today)
        self.assertEqual(result['redirects'], [('wcu-homecoming-2026', 'wcu-homecoming-weekend')])

    def test_same_series_days_apart_stay_separate(self):
        # Same venue, same year-stripped title, but a month apart: a monthly
        # series, not one multi-day listing. (Identical titles still collapse
        # to one page, as before - that rule is untouched.)
        out = self._assign([_ev('First Friday - September', 'Downtown', date(2026, 9, 4)),
                            _ev('First Friday: October', 'Downtown', date(2026, 10, 2))])
        self.assertEqual(len({e['slug'] for e in out}), 2)

    def test_unknown_event_urls_redirect_across_areas_or_go_410(self):
        out_dir = os.path.join(self.tmp, 'out')
        os.makedirs(os.path.join(out_dir, 'events'))
        slugs.emit_retired(self.registry, [], out_dir, AREA, today=self.today,
                           other_areas=['https://example.com/othertown/'])
        with open(os.path.join(out_dir, '.htaccess'), encoding='utf-8') as f:
            rules = f.read()
        self.assertIn('ErrorDocument 410 /testville/gone.html', rules)
        self.assertIn('RewriteCond %{DOCUMENT_ROOT}/othertown/events/$1/index.html -f\n'
                      'RewriteRule ^events/([^/]+)/?$ https://example.com/othertown/events/$1/ [R=301,L]', rules)
        self.assertTrue(rules.rstrip().endswith('RewriteCond %{REQUEST_FILENAME} !-d\n'
                                                'RewriteCond %{REQUEST_FILENAME} !-f\n'
                                                'RewriteRule ^events/[^/]+/?$ - [G,L]'))
        with open(os.path.join(out_dir, 'gone.html'), encoding='utf-8') as f:
            self.assertIn('no longer listed', f.read())


if __name__ == '__main__':
    unittest.main()

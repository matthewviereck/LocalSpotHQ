"""Regression tests for multi-day runs ("Oct 2 - Nov 15, 2026").

Until 2026-09-14 transform.py kept only a range's start date and dropped
anything that started before today, so every exhibition, season and theatre
run vanished from the site the day after it opened.

    python -m unittest tests.test_date_ranges
"""

import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline import feeds, slugs, transform  # noqa: E402


def _fmt(d):
    return f"{d.strftime('%b')} {d.day}, {d.year}"


class ParseRange(unittest.TestCase):
    def test_single_day(self):
        self.assertEqual(transform.parse_date_range('September 5, 2026 8:00 PM'),
                         (datetime(2026, 9, 5), None))

    def test_run_across_months(self):
        self.assertEqual(transform.parse_date_range('Oct 2 - Nov 15, 2026'),
                         (datetime(2026, 10, 2), datetime(2026, 11, 15)))

    def test_bare_end_day_takes_the_start_month(self):
        self.assertEqual(transform.parse_date_range('Oct 3 - 4, 2026'),
                         (datetime(2026, 10, 3), datetime(2026, 10, 4)))

    def test_run_across_new_year_starts_the_year_before(self):
        self.assertEqual(transform.parse_date_range('Nov 20 - Jan 10, 2027'),
                         (datetime(2026, 11, 20), datetime(2027, 1, 10)))

    def test_en_dash(self):
        self.assertEqual(transform.parse_date_range('October 2 – November 1, 2026'),
                         (datetime(2026, 10, 2), datetime(2026, 11, 1)))

    def test_unspaced_range_with_a_time(self):
        self.assertEqual(transform.parse_date_range('September 25-27, 2026 1:00 PM'),
                         (datetime(2026, 9, 25), datetime(2026, 9, 27)))
        self.assertEqual(transform.parse_date_range('Oct 23-24, 2026'),
                         (datetime(2026, 10, 23), datetime(2026, 10, 24)))

    def test_time_range_is_not_a_day_range(self):
        self.assertEqual(transform.parse_date_range('Sep 5, 2026 7:00 PM - 10:00 PM'),
                         (datetime(2026, 9, 5), None))
        self.assertEqual(transform.parse_date_range('Sep 5, 2026 7-9pm'),
                         (datetime(2026, 9, 5), None))

    def test_start_is_unchanged_for_slug_identity(self):
        # _sort_date feeds the slug registry; the start must parse as before
        self.assertEqual(transform.parse_date_advanced('Sep 16 - Oct 18, 2026'), datetime(2026, 9, 16))


class TransformRuns(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run(self, raw_dates):
        src = os.path.join(self.tmp, 'all.json')
        out = os.path.join(self.tmp, 'formatted.json')
        with open(src, 'w', encoding='utf-8') as f:
            json.dump([{'title': f'Event {i}', 'raw_date_string': r,
                        'venue_info': {'name': f'Venue {i}'}} for i, r in enumerate(raw_dates)], f)
        return {e['title']: e for e in transform.transform_events(src, out)}

    def test_open_run_survives_and_is_filed_under_today(self):
        today = date.today()
        opened, closes = today - timedelta(days=5), today + timedelta(days=30)
        closed = today - timedelta(days=1)
        events = self._run([f"{_fmt(opened)[:-6]} - {_fmt(closes)}",      # open
                            f"{_fmt(opened - timedelta(days=9))[:-6]} - {_fmt(closed)}",  # closed
                            _fmt(closed)])                                  # past single day
        self.assertEqual(list(events), ['Event 0'])
        ev = events['Event 0']
        self.assertTrue(ev['ongoing'])
        self.assertEqual(ev['date_category'], 'today')
        self.assertEqual(ev['date'], f"Now through {closes.strftime('%b')} {closes.day}")
        self.assertEqual(ev['end_iso'], closes.isoformat())
        self.assertEqual(datetime.fromtimestamp(ev['_sort_date']).date(), opened)

    def test_future_run_keeps_its_range_label(self):
        start = date.today() + timedelta(days=40)
        end = start + timedelta(days=3)
        raw = f"{_fmt(start)[:-6]} - {_fmt(end)}"
        ev = self._run([raw])['Event 0']
        self.assertFalse(ev['ongoing'])
        self.assertEqual(ev['end_iso'], end.isoformat())


class Downstream(unittest.TestCase):
    def _ev(self, start, end=None, title='Topdog/Underdog', loc="People's Light"):
        return {'title': title, 'loc': loc, 'link': '', 'type': 'Event',
                '_sort_date': datetime(start.year, start.month, start.day).timestamp(),
                'end_iso': end.isoformat() if end else ''}

    def test_weekend_page_lists_an_open_run_once(self):
        wednesday = date(2026, 9, 16)
        run = self._ev(date(2026, 9, 1), date(2026, 10, 18))
        over = self._ev(date(2026, 9, 1), date(2026, 9, 10), title='Closed Show')
        _, _, picked = feeds.weekend_events([run, over], today=wednesday)
        self.assertEqual([(d, e['title']) for d, e in picked], [(date(2026, 9, 18), 'Topdog/Underdog')])

    def test_registry_keeps_start_as_identity_and_ages_from_the_end(self):
        tmp = tempfile.mkdtemp()
        try:
            reg = slugs.SlugRegistry(os.path.join(tmp, 'reg.json'))
            reg.record('topdog-underdog', 'Topdog/Underdog', "People's Light",
                       date(2026, 9, 16), '2026-09-14', end=date(2026, 10, 18))
            rec = reg.slugs['topdog-underdog']
            self.assertEqual((rec['date'], rec['end']), ('2026-09-16', '2026-10-18'))
            reg.record('topdog-underdog', 'Topdog/Underdog', "People's Light",
                       date(2026, 9, 16), '2026-09-15')
            self.assertNotIn('end', reg.slugs['topdog-underdog'])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()

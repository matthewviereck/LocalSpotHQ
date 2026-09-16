"""Regression tests for the discovered-event verifier's date probe.

Two false negatives from the 2026-09-15 run:

1. The probe demanded an unpadded day after the month, so a page writing
   "Thu, Oct 08" (Wix and Shopify venue pages do) looked like the date was not
   on the page at all.
2. The year had to be printed beside the month/day in the visible text, so
   every venue that leaves the year to its URL, its JSON-LD or its
   add-to-calendar button came back NO_YEAR_ON_PAGE.

The check must not get looser in the process. The cases that earned it its
keep - an abbreviated date whose weekday does not fit ("Saturday, Oct. 30"
when Oct 30 2026 is a Friday) and a page that pairs the date with another
year - still have to fail, markup or no markup.

    python -m unittest tests.test_verify_discovered
"""

import os
import sys
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts import verify_discovered as vd  # noqa: E402

OCT30 = date(2026, 10, 30)   # a Friday
OCT8 = date(2026, 10, 8)     # a Thursday
SEP19 = date(2026, 9, 19)    # a Saturday


def scan(text, when, **hints):
    return vd.scan_page(text, when, hints)


class WeekdayStillFails(unittest.TestCase):
    """The Theatre Rock Live catch: right format, impossible weekday."""

    def test_abbreviated_month_with_wrong_weekday_is_strong(self):
        finding, detail = scan('theatre rock live saturday, oct. 30 tickets', OCT30)
        self.assertEqual(finding, 'WEEKDAY_MISMATCH')
        self.assertEqual(vd.severity(finding), 'strong')
        self.assertIn('friday', detail)

    def test_every_abbreviated_spelling_of_the_conflict_fails(self):
        for text in ['saturday, oct. 30', 'sat, oct 30', 'sat. oct. 30',
                     'saturday, oct 30th', 'saturday oct.30', 'sat., oct 30']:
            with self.subTest(text=text):
                self.assertEqual(scan(text, OCT30)[0], 'WEEKDAY_MISMATCH')

    def test_markup_does_not_rescue_a_weekday_conflict(self):
        """Structured data is a fallback for a missing year, not an override."""
        finding, _ = scan('saturday, oct. 30 tickets', OCT30,
                          canonical='https://uptownwestchester.org/pf/rock/2026-10-30/',
                          schema=[date(2026, 10, 30)])
        self.assertEqual(finding, 'WEEKDAY_MISMATCH')

    def test_printed_wrong_year_still_beats_everything(self):
        finding, _ = scan('fri., oct. 30, 2025 tickets', OCT30,
                          schema=[date(2026, 10, 30)])
        self.assertEqual(finding, 'WRONG_YEAR')


class AbbreviatedMonths(unittest.TestCase):
    def test_matching_weekday_with_abbreviated_month_confirms(self):
        for text in ['friday, oct. 30', 'fri, oct 30', 'fri. oct. 30th',
                     'friday, oct 30']:
            with self.subTest(text=text):
                self.assertEqual(scan(text, OCT30)[0], 'WEEKDAY_CONFIRMED')

    def test_zero_padded_day_is_found(self):
        """"Thu, Oct 08" - the helicopter museum listing read as NOT_ON_PAGE."""
        self.assertEqual(scan('baking soda rocket day thu, oct 08 | museum', OCT8)[0],
                         'WEEKDAY_CONFIRMED')
        self.assertEqual(scan('date & time oct 08, 2026, 10:00 am', OCT8)[0],
                         'YEAR_CONFIRMED')

    def test_september_has_three_abbreviations(self):
        for text in ['sat., sept. 19', 'saturday, sept 19', 'saturday, sep. 19',
                     'sat, sep 19', 'saturday, september 19']:
            with self.subTest(text=text):
                self.assertEqual(scan(text, SEP19)[0], 'WEEKDAY_CONFIRMED')

    def test_a_different_day_is_still_not_on_the_page(self):
        self.assertEqual(scan('thu, oct 08', date(2026, 10, 18))[0], 'NOT_ON_PAGE')
        self.assertEqual(scan('sat, oct 30', date(2026, 8, 30))[0], 'NOT_ON_PAGE')


class YearFromStructuredSources(unittest.TestCase):
    def test_canonical_url_date_resolves_the_year(self):
        finding, detail = scan(
            'intro to marbling september 19 9:00 am', SEP19,
            canonical='https://historicsugartown.org/events/intro-to-marbling-4/2026-09-19/')
        self.assertEqual(finding, 'YEAR_FROM_URL')
        self.assertEqual(vd.severity(finding), 'ok')
        self.assertIn('canonical URL', detail)
        self.assertIn('2026-09-19', detail)

    def test_bare_year_in_the_canonical_url_resolves_the_year(self):
        finding, detail = scan(
            'wcu football vs. millersville september 26', date(2026, 9, 26),
            canonical='https://wcupagoldenrams.com/sports/football/schedule/2026')
        self.assertEqual(finding, 'YEAR_FROM_URL')
        self.assertIn('carries 2026', detail)

    def test_a_season_slug_is_not_a_year(self):
        """"/20262027-season/" is two years glued together, not evidence."""
        finding, _ = scan(
            'topdog/underdog september 19', SEP19,
            canonical='https://www.peopleslight.org/whats-on/20262027-season/topdogunderdog/')
        self.assertEqual(finding, 'NO_YEAR_ON_PAGE')

    def test_jsonld_start_date_resolves_the_year(self):
        finding, detail = scan('intro to marbling september 19', SEP19,
                               schema=[date(2026, 9, 19)])
        self.assertEqual(finding, 'YEAR_FROM_SCHEMA')
        self.assertIn('page markup', detail)

    def test_calendar_link_resolves_the_year(self):
        finding, detail = scan(
            'intro to marbling september 19', SEP19,
            calendar=['https://www.google.com/calendar/event?action=TEMPLATE'
                      '&dates=20260919T090000/20260919T150000&text=Intro'])
        self.assertEqual(finding, 'YEAR_FROM_ICS')
        self.assertIn('calendar link', detail)

    def test_outlook_and_webcal_links_resolve_the_year(self):
        for link in ['https://outlook.office.com/owa/?path=/calendar/action/compose'
                     '&rrv=addevent&startdt=2026-09-19T09:00:00-04:00',
                     'webcal://historicsugartown.org/events/marbling/2026-09-19/?ical=1']:
            with self.subTest(link=link):
                self.assertEqual(scan('september 19', SEP19, calendar=[link])[0],
                                 'YEAR_FROM_ICS')

    def test_a_structured_date_in_another_year_is_a_wrong_year(self):
        finding, detail = scan('intro to marbling september 19', SEP19,
                               schema=[date(2025, 9, 19)])
        self.assertEqual(finding, 'WRONG_YEAR')
        self.assertEqual(vd.severity(finding), 'strong')
        self.assertIn('2025', detail)

    def test_no_year_anywhere_still_reports_no_year_on_page(self):
        """Uptown prints "show time october 10 @ 7:30 pm" and nothing else."""
        finding, detail = scan('the brit pack show time october 10 @ 7:30 pm',
                               date(2026, 10, 10),
                               canonical='https://uptownwestchester.org/pf/thebritpack/')
        self.assertEqual(finding, 'NO_YEAR_ON_PAGE')
        self.assertEqual(vd.severity(finding), 'weak')
        self.assertIn('no year', detail)

    def test_a_year_for_another_date_does_not_count(self):
        """The markup dates a different event on the same page."""
        self.assertEqual(scan('october 10 show', date(2026, 10, 10),
                              schema=[date(2026, 10, 15)])[0], 'NO_YEAR_ON_PAGE')

    def test_a_url_year_that_disagrees_is_reported_but_not_a_verdict(self):
        finding, detail = scan('october 10 show', date(2026, 10, 10),
                               canonical='https://example.org/events/fall-2025/')
        self.assertEqual(finding, 'NO_YEAR_ON_PAGE')
        self.assertIn('2025', detail)


class PageHints(unittest.TestCase):
    HTML = """<html><head>
      <link rel='canonical' href='https://historicsugartown.org/events/m/2026-09-19/' />
      <script type="application/ld+json">{"@type":"Event",
        "startDate":"2026-09-19T09:00:00-04:00"}</script>
      </head><body>
      <abbr class="tribe-events-abbr dtstart" title="2026-09-19"> September 19 </abbr>
      <a href="https://www.google.com/calendar/event?action=TEMPLATE&amp;dates=20260919T090000">Google</a>
      <a href="webcal://historicsugartown.org/events/m/2026-09-19/?ical=1">iCal</a>
      <a href="/about/">About</a>
      </body></html>"""

    def test_hints_come_off_the_html(self):
        h = vd.page_hints(self.HTML, 'https://historicsugartown.org/events/m/2026-09-19/')
        self.assertEqual(h['canonical'],
                         'https://historicsugartown.org/events/m/2026-09-19/')
        self.assertEqual(h['schema'], [date(2026, 9, 19), date(2026, 9, 19)])
        self.assertEqual(len(h['calendar']), 2)

    def test_the_hints_resolve_the_year(self):
        h = vd.page_hints(self.HTML, 'https://historicsugartown.org/events/m/2026-09-19/')
        self.assertEqual(vd.scan_page('intro to marbling september 19', SEP19, h)[0],
                         'YEAR_FROM_SCHEMA')

    def test_no_canonical_tag_falls_back_to_the_fetched_url(self):
        h = vd.page_hints('<html><body>September 19</body></html>',
                          'https://cmsmusic.org/event/bachs-lunch/2026-09-19/')
        self.assertEqual(h['canonical'], 'https://cmsmusic.org/event/bachs-lunch/2026-09-19/')
        self.assertEqual(vd.scan_page('bach\'s lunch september 19', SEP19, h)[0],
                         'YEAR_FROM_URL')

    def test_digits_in_a_host_are_not_a_date(self):
        h = vd.page_hints('<html></html>', 'https://20260919.example.org/event/')
        self.assertEqual(vd.scan_page('september 19', SEP19, h)[0], 'NO_YEAR_ON_PAGE')


if __name__ == '__main__':
    unittest.main()

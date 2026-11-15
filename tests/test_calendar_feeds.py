"""Tests for scrapers/calendar_feeds.py, the published-calendar reader.

Fixtures are trimmed copies of what each real feed returned on 2026-11-14.

    python -m unittest tests.test_calendar_feeds
"""

import os
import sys
import unittest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.transform import extract_time, parse_date_range  # noqa: E402
from scrapers import calendar_feeds as cf  # noqa: E402

TODAY = datetime(2026, 11, 14)

LIBCAL_ICS = (
    "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//Springshare//LibCal//EN\r\n"
    "BEGIN:VEVENT\r\nDTSTART:20261123T233000Z\r\nDTEND:20261124T003000Z\r\n"
    "SUMMARY:Mr. Paul & Holly Bee in Concert\r\n"
    "DESCRIPTION:A family concert\\, with songs\r\n"
    "LOCATION:Community Education Room\\, Phoenixville Library\r\n"
    "CATEGORIES:Family,Preschool\r\nURL:https://ccls.libcal.com/event/1\r\n"
    "END:VEVENT\r\n"
    "BEGIN:VEVENT\r\nDTSTART;VALUE=DATE:20261126\r\nDTEND;VALUE=DATE:20261127\r\n"
    "SUMMARY:LIBRARY CLOSED IN OBSERVANCE OF THANKSGIVING\r\n"
    "LOCATION:Phoenixville Library\r\nCATEGORIES:Library Closed\r\n"
    "END:VEVENT\r\n"
    "BEGIN:VEVENT\r\nDTSTART:20261202T191500Z\r\n"
    "SUMMARY:Afternoon at the Movies: \"Miracle on 34th \r\n Street\"\r\n"
    "LOCATION:Harrop Room\\, Phoenixville Library\r\nCATEGORIES:Adults\r\n"
    "STATUS:CONFIRMED\r\nEND:VEVENT\r\n"
    "BEGIN:VEVENT\r\nDTSTART:20261116T183000\r\nRRULE:FREQ=MONTHLY;BYDAY=3MO\r\n"
    "SUMMARY:Green Drinks\r\nEND:VEVENT\r\n"
    "END:VCALENDAR\r\n"
)

LIBRARY_FEED = {
    'id': 'phoenixville_library', 'format': 'ics',
    'url': 'https://ccls.libcal.com/ical_subscribe.php?src=p&cid=13416',
    'venue': {'name': 'Phoenixville Public Library, 183 Second Ave, Phoenixville',
              'lat': 40.1336, 'lng': -75.5193},
    'exclude_categories': ['Library Closed'],
    'category_map': {'preschool|family': 'Kids & Family'},
}


def _item(title, start, **kw):
    item = {'title': title, 'start': start, 'end': None, 'all_day': False,
            'location': '', 'categories': [], 'link': '', 'image': '', 'status': ''}
    item.update(kw)
    return item


class EasternTime(unittest.TestCase):
    def test_summer_and_winter_offsets(self):
        self.assertEqual(cf.eastern_from_utc(datetime(2026, 7, 4, 23, 0)), datetime(2026, 7, 4, 19, 0))
        self.assertEqual(cf.eastern_from_utc(datetime(2026, 12, 5, 0, 30)), datetime(2026, 12, 4, 19, 30))

    def test_daylight_time_ends_first_sunday_of_november(self):
        # 2026-11-01 is that Sunday: 2 AM EDT (06:00 UTC) falls back to 1 AM EST.
        self.assertEqual(cf.eastern_from_utc(datetime(2026, 11, 1, 5, 59)), datetime(2026, 11, 1, 1, 59))
        self.assertEqual(cf.eastern_from_utc(datetime(2026, 11, 1, 6, 0)), datetime(2026, 11, 1, 1, 0))

    def test_daylight_time_starts_second_sunday_of_march(self):
        # 2027-03-14: 2 AM EST (07:00 UTC) springs to 3 AM EDT.
        self.assertEqual(cf.eastern_from_utc(datetime(2027, 3, 14, 6, 59)), datetime(2027, 3, 14, 1, 59))
        self.assertEqual(cf.eastern_from_utc(datetime(2027, 3, 14, 7, 0)), datetime(2027, 3, 14, 3, 0))


class Ics(unittest.TestCase):
    def setUp(self):
        self.items = cf.parse_ics(LIBCAL_ICS)

    def test_reads_every_occurrence_and_skips_repeat_masters(self):
        self.assertEqual([i['title'] for i in self.items], [
            'Mr. Paul & Holly Bee in Concert',
            'LIBRARY CLOSED IN OBSERVANCE OF THANKSGIVING',
            'Afternoon at the Movies: "Miracle on 34th Street"',  # folded line rejoined
        ])

    def test_utc_stamps_become_local_time(self):
        self.assertEqual(self.items[0]['start'], datetime(2026, 11, 23, 18, 30))
        self.assertEqual(self.items[2]['start'], datetime(2026, 12, 2, 14, 15))

    def test_escapes_categories_and_all_day(self):
        self.assertEqual(self.items[0]['location'], 'Community Education Room, Phoenixville Library')
        self.assertEqual(self.items[0]['categories'], ['Family', 'Preschool'])
        closed = self.items[1]
        self.assertTrue(closed['all_day'])
        self.assertEqual(closed['end'], datetime(2026, 11, 26))  # DTEND of a date is exclusive

    def test_events_have_the_pipeline_shape(self):
        events, dropped, outside = cf.build_events(self.items, LIBRARY_FEED, today=TODAY)
        self.assertEqual((len(events), dropped, outside), (2, 1, 0))
        concert = events[0]
        self.assertEqual(concert['raw_date_string'], 'Nov 23, 2026')
        self.assertEqual(concert['attributes']['time'], '6:30 PM')
        self.assertEqual(concert['attributes']['category'], 'Kids & Family')
        self.assertEqual(concert['venue_info']['name'], LIBRARY_FEED['venue']['name'])
        self.assertEqual(concert['venue_info']['location'], {'lat': 40.1336, 'lng': -75.5193})
        self.assertEqual(concert['action_link'], 'https://ccls.libcal.com/event/1')
        # ...and the rest of the pipeline reads it the way it reads discovery's.
        start, end = parse_date_range(concert['raw_date_string'])
        self.assertEqual((start, end), (datetime(2026, 11, 23), None))
        self.assertEqual(extract_time(concert), '6:30 PM')


class Filters(unittest.TestCase):
    def test_past_beyond_horizon_cancelled_and_online_are_dropped(self):
        items = [
            _item('Yesterday', datetime(2026, 11, 13, 19)),
            _item('Tonight', datetime(2026, 11, 14, 19)),
            _item('In four months', datetime(2027, 3, 20, 19)),
            _item('CANCELLED: Tech Group', datetime(2026, 11, 20, 19)),
            _item('Tech Group', datetime(2026, 11, 21, 19), status='CANCELLED'),
            _item('Phoenix Book Club', datetime(2026, 11, 22, 19), location='Virtual (Zoom)'),
        ]
        kept, dropped = cf.select_items(items, {'format': 'ics'}, today=TODAY)
        self.assertEqual([i['title'] for i in kept], ['Tonight'])
        self.assertEqual(dropped, 5)

    def test_weekly_programs_drop_and_one_offs_stay(self):
        weekly = [_item('All Ages Line Dancing inside SunnyBrook', datetime(2026, 11, 17, 18) + timedelta(days=7 * n))
                  for n in range(4)]
        dated = [_item(f'Mahjong 101 ({m})', d) for m, d in (
            ('November 25th', datetime(2026, 11, 25)), ('December 9th', datetime(2026, 12, 9)),
            ('December 23rd', datetime(2026, 12, 23)), ('January 6th', datetime(2027, 1, 6)))]
        monthly = [_item('A Night with Spirit (November 25th)', datetime(2026, 11, 25, 19)),
                   _item('A Night with Spirit (Dec 30th)', datetime(2026, 12, 30, 19))]
        show = [_item('Comedian Billy Gardell returns', datetime(2026, 11, 21, 20))]
        kept, _ = cf.select_items(weekly + dated + monthly + show, {'format': 'fooevents', 'max_repeats': 3},
                                  today=TODAY)
        self.assertEqual(sorted(i['title'] for i in kept), [
            'A Night with Spirit (Dec 30th)', 'A Night with Spirit (November 25th)',
            'Comedian Billy Gardell returns'])

    def test_category_and_title_and_location_filters(self):
        feed = {'format': 'ics', 'include_categories': ['Performances', 'Community Events'],
                'exclude_categories': ['Athletics'], 'exclude_title': '^APEX',
                'require_location': 'collegeville|hall|theater'}
        items = [
            _item('Jazz Ensemble Concert', datetime(2026, 12, 5, 19), categories=['Performances'],
                  location='Lenfest Theater'),
            _item('Basketball vs Widener', datetime(2026, 11, 21, 13), categories=['Athletics', 'Community Events'],
                  location='Collegeville, PA, Helfferich Hall'),
            _item('APEX-050 Informational Interviews', datetime(2026, 11, 18), categories=['Community Events'],
                  location='IDC 210, Hall'),
            _item('Chemistry Tea', datetime(2026, 11, 20), categories=[], location='Pfahler Hall'),
            _item('Away concert', datetime(2026, 11, 20), categories=['Performances'], location='Dallas, PA'),
        ]
        kept, _ = cf.select_items(items, feed, today=TODAY)
        self.assertEqual([i['title'] for i in kept], ['Jazz Ensemble Concert'])


class Venues(unittest.TestCase):
    TOWNS = {'phoenixville': (40.1304, -75.5149), 'valley forge': (40.1015, -75.4239),
             'collegeville': (40.1859, -75.4527)}

    def test_room_template(self):
        feed = {'id': 'ursinus', 'format': 'ics', 'venue': {'name': 'Ursinus College', 'lat': 40.19, 'lng': -75.45},
                'venue_template': '{room}, Ursinus College, Collegeville',
                'strip_location': r'^Collegeville,\s*PA,?\s*'}
        ev = cf.to_event(_item('Voices of Ursinus Concert', datetime(2026, 11, 21, 16),
                               location='Collegeville, PA, Bomberger Hall'), feed, self.TOWNS)
        self.assertEqual(ev['venue_info']['name'], 'Bomberger Hall, Ursinus College, Collegeville')
        self.assertEqual(ev['attributes']['category'], 'Live Music')

    def test_address_picks_the_town_and_another_town_is_outside(self):
        feed = {'id': 'pf', 'format': 'elfsight',
                'venue': {'name': 'Downtown Phoenixville', 'lat': 40.1304, 'lng': -75.5155}}
        here = cf.to_event(_item('Christmas Bazaar', datetime(2026, 12, 12, 12),
                                 location='Great American Pub, 148 Bridge Street, Phoenixville, PA 19460'),
                           feed, self.TOWNS)
        self.assertEqual(here['venue_info']['name'], 'Great American Pub, 148 Bridge Street, Phoenixville')
        self.assertEqual(here['venue_info']['location'], {'lat': 40.1304, 'lng': -75.5149})
        # The town is the last roster name in the address, not a street name.
        road = cf.to_event(_item('Car Show', datetime(2026, 12, 12, 12),
                                 location='Lot B, 10 Valley Forge Rd, Phoenixville, PA 19460'), feed, self.TOWNS)
        self.assertEqual(road['venue_info']['location'], {'lat': 40.1304, 'lng': -75.5149})
        away = cf.to_event(_item('Holiday Market', datetime(2026, 12, 12, 12),
                                 location='Some Hall, 1 Main St, Lancaster, PA 17602'), feed, self.TOWNS)
        self.assertIsNone(away)
        vague = cf.to_event(_item('Holiday House Tour', datetime(2026, 12, 5, 15),
                                  location='Various Locations, see description!'), feed, self.TOWNS)
        self.assertEqual(vague['venue_info']['name'], 'Downtown Phoenixville')

    def test_title_rules_and_free(self):
        feed = {'id': 'sj', 'format': 'fooevents', 'venue': {'name': "SoulJoel's", 'lat': 40.2, 'lng': -75.6}}
        comic = cf.to_event(_item('Comedian Rafi Bastos returns', datetime(2026, 11, 27, 19)), feed, self.TOWNS)
        self.assertEqual(comic['attributes']['category'], 'Comedy')
        matinee = cf.to_event(_item('Free Matinee Jazz Concert', datetime(2026, 11, 14, 15)), feed, self.TOWNS)
        self.assertEqual(matinee['attributes']['price'], 'Free')

    def test_title_fixes(self):
        feed = {'id': 'pf', 'format': 'elfsight', 'title_fixes': {'Phoenixivlle': 'Phoenixville'},
                'venue': {'name': 'Downtown Phoenixville', 'lat': 40.1304, 'lng': -75.5155}}
        events, _, _ = cf.build_events([_item('Phoenixivlle Firebird Festival', datetime(2026, 12, 12, 16))],
                                       feed, today=TODAY)
        self.assertEqual(events[0]['title'], 'Phoenixville Firebird Festival')


class OtherFormats(unittest.TestCase):
    def test_squarespace(self):
        data = {'upcoming': [{
            'title': 'Key Concert Series: Stealing Society &amp; Violet Arcade ',
            'startDate': 1795219200000,  # 2026-11-21 00:00 UTC = Nov 20, 7 PM EST
            'endDate': 1795230000000,
            'fullUrl': '/events/key-concert-series',
            'assetUrl': 'https://images.squarespace-cdn.com/x.jpg',
            'location': {'addressTitle': '', 'addressLine1': '', 'markerLat': 40.72, 'markerLng': -74.0},
        }]}
        [item] = cf.parse_squarespace(data, 'https://www.watertowerlive.com')
        self.assertEqual(item['title'], 'Key Concert Series: Stealing Society & Violet Arcade')
        self.assertEqual(item['start'], datetime(2026, 11, 20, 19, 0))
        self.assertEqual(item['link'], 'https://www.watertowerlive.com/events/key-concert-series')
        self.assertEqual(item['location'], '')

    def test_elfsight(self):
        data = {'data': {'widgets': {'w1': {'data': {'settings': {
            'locations': [{'id': 'L1', 'name': 'Franklin Commons',
                           'address': '400 Franklin Ave, Phoenixville, PA 19460'}],
            'events': [
                {'name': 'German Christmas Market', 'start': {'type': 'datetime', 'date': '2026-11-21', 'time': '12:00'},
                 'end': {'type': 'datetime', 'date': '2026-11-21', 'time': '17:00'}, 'repeatPeriod': 'noRepeat',
                 'location': ['L1'], 'description': '<a href="https://example.org/market">Info</a>'},
                {'name': 'Small Business Saturday', 'start': {'type': 'date', 'date': '2026-11-28'},
                 'repeatPeriod': 'noRepeat', 'location': []},
                {'name': 'Firebird Festival', 'start': 1670709600000, 'end': 1670727600000,
                 'repeatPeriod': 'noRepeat'},
                {'name': "Phoenixville Farmers' Market", 'start': {'type': 'datetime', 'date': '2026-02-21',
                                                                  'time': '10:00'}, 'repeatPeriod': 'weeklyOn'},
            ]}}}}}}
        items = cf.parse_elfsight(data, 'w1')
        self.assertEqual([i['title'] for i in items],
                         ['German Christmas Market', 'Small Business Saturday', 'Firebird Festival'])
        market, saturday, old = items
        self.assertEqual(market['start'], datetime(2026, 11, 21, 12, 0))
        self.assertEqual(market['location'], 'Franklin Commons, 400 Franklin Ave, Phoenixville, PA 19460')
        self.assertEqual(market['link'], 'https://example.org/market')
        self.assertTrue(saturday['all_day'])
        self.assertEqual(old['start'], datetime(2022, 12, 10, 17, 0))  # epoch form, EST
        self.assertEqual(cf.parse_elfsight({}, 'w1'), [])

    def test_fooevents(self):
        page = (r'''<div id='fooevents_calendar'></div><script>
            var localObj = '{\"defaultView\":\"listMonth\",\"0\":{\"title\":\"Comedian Billy Gardell '''
                r'''returns to SoulJoel\\u0027s\",\"allDay\":false,\"start\":\"2026-11-21T20:00:00\",'''
                r'''\"url\":\"https:\\/\\/souljoels.com\\/shop\\/tickets\\/billygardell\\/\",'''
                r'''\"location\":\"SoulJoel\\u0027s at Sunnybrook 50 Sunnybrook Road Pottstown, PA 19464\"}}';
            </script>''')
        [item] = cf.parse_fooevents(page)
        self.assertEqual(item['title'], "Comedian Billy Gardell returns to SoulJoel's")
        self.assertEqual(item['start'], datetime(2026, 11, 21, 20, 0))
        self.assertEqual(item['link'], 'https://souljoels.com/shop/tickets/billygardell/')
        self.assertIn('Pottstown', item['location'])
        self.assertEqual(cf.parse_fooevents('<html>no calendar</html>'), [])


class FeedConfig(unittest.TestCase):
    def test_every_configured_feed_is_complete(self):
        import json
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(root, 'config', 'phoenixville.json'), encoding='utf-8') as f:
            cfg = json.load(f)
        feeds = [s for s in cfg['scrapers'] if s['module'] == 'scrapers.calendar_feeds']
        self.assertGreaterEqual(len(feeds), 6)
        for s in feeds:
            feed = s['options']['feed']
            for key in ('id', 'format', 'url', 'venue'):
                self.assertIn(key, feed, feed.get('id'))
            self.assertIn(feed['format'], ('ics', 'squarespace', 'elfsight', 'fooevents'))
            self.assertIn(s['output_file'], cfg['merge_sources'], feed['id'])
            for pattern in (feed.get('exclude_title'), feed.get('require_location')):
                if pattern:
                    __import__('re').compile(pattern)


if __name__ == '__main__':
    unittest.main()

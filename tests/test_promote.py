"""The "Promote this event" page and its links (pipeline/promote.py).

    python -m unittest tests.test_promote
"""

import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline import event_pages, promote  # noqa: E402

AREA = {'id': 'testville', 'slug': 'testville', 'name': 'Testville',
        'meta': {'canonical_url': 'https://example.com/testville/'}}


def _ev(title, slug, d):
    ts = datetime(d.year, d.month, d.day).timestamp()
    return {'title': title, 'loc': 'The Hall', 'town': 'Testville', '_sort_date': ts,
            'slug': slug, 'img': '', 'link': '', 'type': 'Event', 'date': 'Sat Oct 3'}


class PromotePage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.events = os.path.join(self.tmp, 'events.json')
        with open(self.events, 'w', encoding='utf-8') as f:
            json.dump([_ev('Fall Fest', 'fall-fest', date(2026, 10, 3))], f)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _page(self, cfg):
        promote.generate_promote_page(self.events, self.tmp, AREA, promote=cfg)
        with open(os.path.join(self.tmp, 'promote', 'index.html'), encoding='utf-8') as f:
            return f.read()

    def test_pay_link_carries_area_and_slug_reference(self):
        html = self._page({'price_label': '$19', 'days': 7,
                           'payment_link': 'https://buy.stripe.com/test_abc', 'contact_email': ''})
        self.assertIn('https://buy.stripe.com/test_abc', html)
        self.assertIn('client_reference_id', html)
        self.assertIn('"testville"', html)           # areaSlug for the reference id
        self.assertIn('"fall-fest"', html)           # catalog names the event
        self.assertIn('Fall Fest', html)
        self.assertIn('for 7 days', html)
        self.assertNotIn('id="signup-form"', html)  # no interest form once payment is on

    def test_without_pay_link_collects_interest_instead(self):
        html = self._page({'price_label': '$19', 'days': 7, 'payment_link': '', 'contact_email': ''})
        self.assertIn('/subscribe.php', html)
        self.assertNotIn('id="pay"', html)

    def test_reference_id_uses_double_underscore(self):
        # Event slugs never contain "_", so the webhook can split unambiguously
        self.assertEqual(promote.reference_id('west-chester', 'blobfest-2027'),
                         'west-chester__blobfest-2027')

    def test_config_defaults_survive_partial_file(self):
        path = os.path.join(self.tmp, 'promote.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({'payment_link': 'https://buy.stripe.com/x'}, f)
        cfg = promote.load_promote_config(path)
        self.assertEqual(cfg['days'], 7)
        self.assertEqual(cfg['payment_link'], 'https://buy.stripe.com/x')


class EventPageLinks(unittest.TestCase):
    def test_event_page_links_to_promote_and_signup(self):
        ev = _ev('Fall Fest', 'fall-fest', date(2026, 10, 3))
        slug, html = event_pages._event_page(ev, date(2026, 10, 3), AREA)
        self.assertIn('https://example.com/testville/promote/?event=fall-fest', html)
        self.assertIn('Promote this event', html)
        self.assertIn('/subscribe.php', html)
        self.assertIn('event-page:testville', html)


if __name__ == '__main__':
    unittest.main()

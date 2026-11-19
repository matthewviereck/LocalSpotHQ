"""The site name is written one way, so Google can learn it (2026-11-19)."""
import json
import os
import re
import sys
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.brand import SITE_NAME, website
from pipeline.hub import render_hub


class BrandTest(unittest.TestCase):
    def setUp(self):
        block = {'slug': 'phoenixville', 'name': 'Phoenixville', 'tagline': '', 'events': [], 'guides': []}
        self.page = render_hub([block], today=date(2026, 11, 19))

    def test_root_website_data_carries_name_variants_and_facebook(self):
        ld = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', self.page, re.S).group(1))
        self.assertEqual(ld['name'], SITE_NAME)
        self.assertIn('LocalSpot HQ', ld['alternateName'])
        self.assertTrue(ld['publisher']['sameAs'])
        self.assertEqual(ld['url'], website()['url'])

    def test_root_has_site_name_and_weekend_link(self):
        self.assertIn('<meta property="og:site_name" content="LocalSpot">', self.page)
        self.assertIn('href="/phoenixville/this-weekend/">Things to do in Phoenixville this weekend', self.page)

    def test_no_hq_variant_left_in_templates(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for rel in ('templates/app_template.html',):
            with open(os.path.join(root, rel), encoding='utf-8') as f:
                self.assertNotIn('content="LocalSpot HQ"', f.read())


if __name__ == '__main__':
    unittest.main()

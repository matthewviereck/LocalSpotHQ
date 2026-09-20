"""Plan pages (pipeline/plans.py): every plan gets a real page, the app tile
links to it, and the sitemap lists it.

    python -m unittest tests.test_plan_pages
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline import plans, event_pages  # noqa: E402

AREA = {'name': 'Testville',
        'meta': {'canonical_url': 'https://example.com/testville/',
                 'og_image': 'https://example.com/og.png'}}

PLAN = {
    'id': 'date_night_test', 'title': 'Test Date Night', 'category': 'Date Night',
    'duration': '3 hours', 'budget': '$$', 'total_cost': '$60 per couple',
    'best_for': ['Couples'], 'description': 'A <test> plan & more',
    'itinerary': [
        {'step': 1, 'time': '6:00 PM', 'activity': 'Dinner at Place <A>', 'type': 'dining',
         'duration': '90 minutes', 'cost': '$$', 'notes': 'Book ahead & bring wine'},
        {'step': 2, 'time': 'Optional', 'activity': 'Walk', 'type': 'outing',
         'duration': '30 minutes', 'cost': 'Free', 'notes': ''},
    ],
    'tips': 'Everything is walkable.', 'img': 'https://images.unsplash.com/x', 'tags': ['date'],
}


class PlanPages(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.data = os.path.join(self.tmp, 'plans.json')
        with open(self.data, 'w', encoding='utf-8') as f:
            json.dump([PLAN], f)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_slug_hyphenates_id(self):
        self.assertEqual(plans.plan_slug(PLAN), 'date-night-test')
        self.assertEqual(plans.plan_slug({'id': 'x_y', 'slug': 'kept'}), 'kept')

    def test_page_and_index_are_written(self):
        slugs = plans.generate_plan_pages(self.data, self.tmp, AREA)
        self.assertEqual(slugs, ['date-night-test'])
        page = open(os.path.join(self.tmp, 'plans', 'date-night-test', 'index.html'), encoding='utf-8').read()
        index = open(os.path.join(self.tmp, 'plans', 'index.html'), encoding='utf-8').read()
        self.assertIn('<link rel="canonical" href="https://example.com/testville/plans/date-night-test/">', page)
        self.assertIn('Dinner at Place &lt;A&gt;', page)       # escaped, not raw
        self.assertIn('Book ahead &amp; bring wine', page)
        self.assertIn('Everything is walkable.', page)
        self.assertNotIn('unsplash', page)                     # no stock hero on the page
        self.assertIn('og:image" content="https://example.com/og.png"', page)
        self.assertIn('href="date-night-test/"', index)
        self.assertIn('<h2>Date Night</h2>', index)

    def test_west_chester_shape(self):
        """West Chester's plans have no id/category/itinerary: title, desc,
        tags and steps[{title, desc, link}]. They must still build."""
        wc = {'title': "Girls' Day Out", 'desc': 'Shopping & wine', 'duration': 'Afternoon',
              'tags': ['Night Out', 'West Chester', 'Shopping'], 'img': '',
              'steps': [{'title': 'Shop Gay Street', 'desc': 'Boutiques', 'link': 'https://example.org/'},
                        {'title': 'Dinner', 'desc': 'Pasta', 'link': ''}]}
        with open(self.data, 'w', encoding='utf-8') as f:
            json.dump([wc], f)
        self.assertEqual(plans.plan_slug(wc), 'girls-day-out')
        self.assertEqual(plans.plan_category(wc), 'Night Out')
        slugs = plans.generate_plan_pages(self.data, self.tmp, AREA)
        self.assertEqual(slugs, ['girls-day-out'])
        page = open(os.path.join(self.tmp, 'plans', 'girls-day-out', 'index.html'), encoding='utf-8').read()
        self.assertIn('<a href="https://example.org/" rel="noopener">Shop Gay Street</a>', page)
        self.assertIn('<p class="what">Dinner</p>', page)
        self.assertIn('Shopping &amp; wine', page)
        self.assertNotIn('class="when"', page)                 # no times in this shape

    def test_empty_data_writes_nothing(self):
        with open(self.data, 'w', encoding='utf-8') as f:
            json.dump([], f)
        self.assertEqual(plans.generate_plan_pages(self.data, self.tmp, AREA), [])
        self.assertFalse(os.path.exists(os.path.join(self.tmp, 'plans', 'index.html')))

    def test_sitemap_lists_plans(self):
        event_pages.generate_area_sitemap(self.tmp, AREA, [], guide_slugs=['g'], plan_slugs=['p1'])
        xml = open(os.path.join(self.tmp, 'sitemap.xml'), encoding='utf-8').read()
        self.assertIn('<loc>https://example.com/testville/plans/p1/</loc>', xml)
        self.assertIn('<loc>https://example.com/testville/guides/g/</loc>', xml)


if __name__ == '__main__':
    unittest.main()

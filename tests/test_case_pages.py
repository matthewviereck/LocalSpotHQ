"""The weekend case (pipeline/cases.py): every case in the data has exactly one
answer, a case never reaches the build before its Thursday, the live one sits
at /weekend-case/ with the earlier ones archived, and the page never shows
the answer in plain text.

    python -m unittest tests.test_case_pages
"""

import base64
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from pipeline import cases, event_pages  # noqa: E402

CASES_FILE = os.path.join(ROOT, 'data', 'phoenixville', 'cases.json')
AREA = {'name': 'Testville', 'slug': 'testville',
        'meta': {'canonical_url': 'https://example.com/testville/',
                 'og_image': 'https://example.com/og.png'}}


def _reader_text(case):
    return ' '.join([case['title'], case['teaser'], case['question']]
                    + case['scene'] + case['reveal'] + [c['text'] for c in case['clues']])


class TheData(unittest.TestCase):
    """Checks on data/phoenixville/cases.json, so a hand edit or a new week's
    case cannot ship with two answers or a giveaway."""

    @classmethod
    def setUpClass(cls):
        cls.cases = cases.load_cases(CASES_FILE)

    def test_there_are_cases(self):
        self.assertGreaterEqual(len(self.cases), 4)

    def test_each_case_has_exactly_one_answer(self):
        for c in self.cases:
            self.assertEqual(cases.count_solutions(c), 1, f"case {c['number']} is not unique")

    def test_the_answer_is_whoever_was_at_the_question_place(self):
        for c in self.cases:
            place = c['solution']['place'][c['culprit']]
            self.assertEqual(c['question'], f"Who was at {place}?", f"case {c['number']}")
            # nobody else was there (a solution is one place per person)
            others = [s for s, p in c['solution']['place'].items() if p == place and s != c['culprit']]
            self.assertEqual(others, [])

    def test_no_clue_puts_a_named_person_at_the_answer_place(self):
        for c in self.cases:
            place = c['solution']['place'][c['culprit']]
            for cl in (x['logic'] for x in c['clues']):
                self.assertFalse(cl['type'] == 'direct' and cl['c'] == 'place' and cl['v'] == place,
                                 f"case {c['number']} gives the answer away")
                self.assertFalse(cl['type'] == 'either' and cl['c'] == 'place' and place in (cl['v1'], cl['v2']),
                                 f"case {c['number']} narrows the answer to two in one clue")

    def test_dates_are_distinct_thursdays_and_slugs_are_unique(self):
        days = [c['publish'] for c in self.cases]
        self.assertEqual(len(days), len(set(days)))
        for d in days:
            self.assertEqual(date.fromisoformat(d).weekday(), 3, f"{d} is not a Thursday")
        self.assertEqual(len({c['slug'] for c in self.cases}), len(self.cases))
        self.assertEqual([c['number'] for c in self.cases], list(range(1, len(self.cases) + 1)))

    def test_reader_text_house_rules(self):
        for c in self.cases:
            text = _reader_text(c)
            self.assertIsNone(re.search(r'[–—]| - ', text), f"case {c['number']} has a dash")
            self.assertNotIn('viereck', text.lower())
            self.assertNotIn('daily dunnit', text.lower())

    def test_suspects_and_categories_line_up(self):
        for c in self.cases:
            ids = {s['id'] for s in c['suspects']}
            self.assertIn(c['culprit'], ids)
            for cat in c['categories']:
                self.assertEqual(len(cat['values']), len(ids))
                self.assertEqual(len(cat['short']), len(cat['values']))
                self.assertEqual(sorted(c['solution'][cat['id']].values()), sorted(cat['values']))


SAMPLE = [
    {'number': 1, 'slug': 'case-1', 'publish': '2026-11-05', 'title': 'First <case>',
     'teaser': 'Teaser one.', 'scene': ['Scene & one.'], 'question': 'Who was at the park?',
     'suspects': [{'id': 'a', 'name': 'Ann'}, {'id': 'b', 'name': 'Bo'}],
     'categories': [{'id': 'place', 'label': 'Where', 'question': 'Where?', 'ordered': False,
                     'values': ['the park', 'the bridge'], 'short': ['Park', 'Bridge']}],
     'clues': [{'text': 'Ann was not at the bridge.', 'logic': {'type': 'negative', 's': 'a', 'c': 'place', 'v': 'the bridge'}}],
     'solution': {'place': {'a': 'the park', 'b': 'the bridge'}}, 'culprit': 'a',
     'reveal': ['ANSWER-ONE-REVEAL'], 'source': 'test'},
    {'number': 2, 'slug': 'case-2', 'publish': '2026-11-12', 'title': 'Second case',
     'teaser': 'Teaser two.', 'scene': ['Scene two.'], 'question': 'Who was at the bridge?',
     'suspects': [{'id': 'a', 'name': 'Ann'}, {'id': 'b', 'name': 'Bo'}],
     'categories': [{'id': 'place', 'label': 'Where', 'question': 'Where?', 'ordered': False,
                     'values': ['the park', 'the bridge'], 'short': ['Park', 'Bridge']}],
     'clues': [{'text': 'Bo was not at the park.', 'logic': {'type': 'negative', 's': 'b', 'c': 'place', 'v': 'the park'}}],
     'solution': {'place': {'a': 'the park', 'b': 'the bridge'}}, 'culprit': 'b',
     'reveal': ['ANSWER-TWO-REVEAL'], 'source': 'test'},
]


class Pages(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.data = os.path.join(self.tmp, 'cases.json')
        with open(self.data, 'w', encoding='utf-8') as f:
            json.dump(SAMPLE, f)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def read(self, *parts):
        with open(os.path.join(self.tmp, *parts), encoding='utf-8') as f:
            return f.read()

    def all_output(self):
        text = ''
        for root, _, files in os.walk(os.path.join(self.tmp, 'weekend-case')):
            for name in files:
                with open(os.path.join(root, name), encoding='utf-8') as f:
                    text += f.read()
        return text

    def test_before_the_first_thursday_only_a_noindex_teaser(self):
        slugs = cases.generate_case_pages(self.data, self.tmp, AREA, today=date(2026, 11, 4))
        self.assertEqual(slugs, [])
        page = self.read('weekend-case', 'index.html')
        self.assertIn('noindex', page)
        self.assertIn('Thursday, November 5', page)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, 'weekend-case', 'case-1')))
        self.assertNotIn('Scene &amp; one.', page)

    def test_a_future_case_never_reaches_the_build(self):
        slugs = cases.generate_case_pages(self.data, self.tmp, AREA, today=date(2026, 11, 8))
        self.assertEqual(slugs, ['case-1'])
        self.assertFalse(os.path.exists(os.path.join(self.tmp, 'weekend-case', 'case-2')))
        out = self.all_output()
        self.assertNotIn('Second case', out)
        self.assertNotIn('Scene two.', out)

    def test_live_case_at_the_index_with_ga_and_escaping(self):
        cases.generate_case_pages(self.data, self.tmp, AREA, today=date(2026, 11, 5))
        page = self.read('weekend-case', 'index.html')
        self.assertIn('G-FXMDYPK8KZ', page)
        self.assertIn('<link rel="canonical" href="https://example.com/testville/weekend-case/">', page)
        self.assertIn('First &lt;case&gt;', page)
        self.assertIn('Scene &amp; one.', page)
        self.assertIn('Ann was not at the bridge.', page)
        self.assertIn('"weekend-case:testville"', page)       # signup source routes to this area
        self.assertIn('case_solve', page)
        self.assertIn('index, follow', page)
        self.assertIn('og:image" content="https://example.com/og.png"', page)

    def test_the_answer_is_not_in_plain_text(self):
        cases.generate_case_pages(self.data, self.tmp, AREA, today=date(2026, 11, 5))
        page = self.read('weekend-case', 'index.html')
        self.assertNotIn('ANSWER-ONE-REVEAL', page)
        blob = re.search(r'"answer": "([A-Za-z0-9+/=]+)"', page).group(1)
        answer = json.loads(base64.b64decode(blob))
        self.assertEqual(answer['culprit'], 'a')
        self.assertEqual(answer['name'], 'Ann')
        self.assertEqual(answer['reveal'], ['ANSWER-ONE-REVEAL'])

    def test_next_thursday_moves_the_old_case_to_the_archive(self):
        slugs = cases.generate_case_pages(self.data, self.tmp, AREA, today=date(2026, 11, 12))
        self.assertEqual(slugs, ['case-1', 'case-2'])
        index = self.read('weekend-case', 'index.html')
        self.assertIn('Second case', index)
        self.assertIn('Earlier cases', index)
        self.assertIn('href="https://example.com/testville/weekend-case/case-1/"', index)
        old = self.read('weekend-case', 'case-1', 'index.html')
        self.assertIn('<link rel="canonical" href="https://example.com/testville/weekend-case/case-1/">', old)
        self.assertIn('From the archive', old)                 # not labelled as this weekend's
        self.assertNotIn("This weekend's case", old)
        self.assertIn('case-2/', old)                          # and points on to the live one

    def test_live_case_helper_and_missing_file(self):
        self.assertIsNone(cases.live_case(self.data, today=date(2026, 11, 4)))
        self.assertEqual(cases.live_case(self.data, today=date(2026, 11, 20))['number'], 2)
        self.assertIsNone(cases.live_case(os.path.join(self.tmp, 'nope.json')))
        self.assertEqual(cases.generate_case_pages(os.path.join(self.tmp, 'nope.json'), self.tmp, AREA), [])

    def test_weekend_page_note_carries_the_live_case(self):
        from unittest import mock
        from pipeline import feeds

        class Nov(date):
            @classmethod
            def today(cls):
                return date(2026, 11, 6)

        with mock.patch.object(cases, 'date', Nov):
            note = feeds._case_note(self.data, 'https://example.com/testville')
        self.assertIn('href="https://example.com/testville/weekend-case/"', note)
        self.assertIn('First &lt;case&gt;', note)
        self.assertIn('Teaser one.', note)                     # the post task drafts its line from this
        self.assertEqual(feeds._case_note(os.path.join(self.tmp, 'nope.json'), 'x'), '')

    def test_sitemap_lists_the_index_only_once_a_case_is_live(self):
        event_pages.generate_area_sitemap(self.tmp, AREA, [], case_slugs=[])
        self.assertNotIn('weekend-case', self.read('sitemap.xml'))
        event_pages.generate_area_sitemap(self.tmp, AREA, [], case_slugs=['case-1'])
        xml = self.read('sitemap.xml')
        self.assertIn('<loc>https://example.com/testville/weekend-case/</loc>', xml)
        self.assertIn('<loc>https://example.com/testville/weekend-case/case-1/</loc>', xml)

    def test_solver_counts_both_ways(self):
        open_case = dict(SAMPLE[0], clues=[])
        self.assertEqual(cases.count_solutions(open_case, limit=5), 2)
        self.assertEqual(cases.count_solutions(SAMPLE[0]), 1)


if __name__ == '__main__':
    unittest.main()

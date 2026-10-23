"""Free-text search must match photograph values, not JSON structure."""
from pathlib import Path
import tempfile
import unittest

from local_browser.catalog import SQLiteCatalog


class SearchTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.catalog = SQLiteCatalog(Path(temp.name) / 'catalog.sqlite3')
        self.metadata = {
            'original_filename': 'harbour.jpg', 'camera': 'Canon EOS R8',
            'lens': 'RF 100mm', 'category': 'landscape',
            'tags': ['coastal', 'blue hour'], 'location': 'Halifax',
            'caption': 'A "quiet" evening', 'description': 'Waterfront',
            'iso': 640, 'aperture': 'f/2.8', 'shutter_speed': '1/250s',
            'date_taken': '2026-10-22T18:00:00', 'width': 900,
            'aspect_ratio': 1.5, 'title': None, 'cache_key': 'internal-cache-token',
        }
        self.put('one', self.metadata)
        self.put('two', {**self.metadata, 'original_filename': 'flower.jpg',
                         'camera': None, 'lens': None, 'category': None,
                         'tags': [], 'location': None, 'caption': None,
                         'description': None, 'iso': None, 'aperture': None,
                         'shutter_speed': None, 'date_taken': None,
                         'width': 600, 'aspect_ratio': 1.0})

    def put(self, image_id, metadata, present=1):
        self.catalog.put(dict(id=image_id, root='/synthetic', path=f'/synthetic/{image_id}',
                              fingerprint='fixture', present=present, metadata=metadata))

    def assert_matches(self, query, expected, **filters):
        result = self.catalog.query({'q': query, **filters})
        self.assertEqual(result['total'], len(expected))
        self.assertEqual({row['id'] for row in result['items']}, set(expected))

    def test_property_names_and_json_representation_do_not_match(self):
        for query in ('camera', 'tags', 'location', 'original_filename', 'iso',
                      'null', '[', '{', 'internal-cache-token', 'coastal", "blue'):
            with self.subTest(query=query):
                self.assert_matches(query, [])

    def test_filename_editorial_tags_and_exif_values_match(self):
        for query in ('HARBOUR.JPG', 'canon eos', 'RF 100', 'LANDSCAPE',
                      'coastal', 'BLUE HOUR', 'halifax', '"quiet"', 'Waterfront',
                      '640', 'f/2.8', '1/250s', '2026-10-22', '900', '1.5'):
            with self.subTest(query=query):
                self.assert_matches(query, ['one'])
        self.assert_matches('flower', ['two'])
        self.assert_matches("' OR 1=1 --", [])

    def test_field_names_are_searchable_when_present_in_values(self):
        self.put('one', {**self.metadata, 'caption': 'Camera tags and location notes'})
        for query in ('camera', 'tags', 'location'):
            with self.subTest(query=query):
                self.assert_matches(query, ['one'])

    def test_search_composes_with_filters_missing_records_and_pagination(self):
        self.put('duplicate', {**self.metadata, 'tags': ['coastal', 'coastal trail']})
        self.put('missing', self.metadata, present=0)
        self.assert_matches('coastal', ['one', 'duplicate'], category='landscape', tag='coastal')
        self.assert_matches('coastal', ['one'], tag='blue hour')
        self.assert_matches('coastal', [], category='nature')
        first = self.catalog.query({'q': 'coastal', 'limit': 1})
        second = self.catalog.query({'q': 'coastal', 'limit': 1, 'offset': 1})
        self.assertEqual(first['total'], 2)
        self.assertEqual(second['total'], 2)
        self.assertEqual(len(first['items']), 1)
        self.assertEqual(len(second['items']), 1)
        self.assertNotEqual(first['items'][0]['id'], second['items'][0]['id'])

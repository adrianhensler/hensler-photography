import hashlib
import http.client
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest

from PIL import Image

from local_browser.catalog import SQLiteCatalog
from local_browser.demo import create_demo
from local_browser.indexer import load_annotations, scan, separate_paths
from local_browser.server import make_server


class BrowserTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = create_demo(self.base / 'demo')
        self.data = self.base / 'catalog'
        self.catalog = SQLiteCatalog(self.data / 'catalog.sqlite3')
        self.annotations = load_annotations(self.base / 'demo' / 'metadata.json')

    def index(self):
        return scan(self.root, self.data, self.catalog, self.annotations)

    def snapshot(self):
        return {str(p): (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns) for p in self.root.rglob('*') if p.is_file()}

    def test_originals_unchanged_and_incremental_cache(self):
        before = self.snapshot()
        first = self.index()
        self.assertEqual(first['indexed'], 24)
        self.assertEqual(first['errors'], [])
        cache_before = {p.name: p.stat().st_mtime_ns for p in (self.data / 'cache').iterdir()}
        self.assertEqual(self.index()['unchanged'], 24)
        self.assertEqual(before, self.snapshot())
        self.assertEqual(cache_before, {p.name: p.stat().st_mtime_ns for p in (self.data / 'cache').iterdir()})

    def test_exif_orientation_and_dimensions(self):
        self.index()
        row = self.catalog.query({'q': 'study-04.jpg'})['items'][0]
        meta = row['metadata']
        self.assertEqual((meta['width'], meta['height']), (600, 900))
        self.assertEqual(meta['iso'], 400)
        self.assertEqual(meta['aperture'], 'f/2.8')
        self.assertEqual(meta['shutter_speed'], '1/250s')
        self.assertEqual(meta['date_taken'], '2026-04-15T12:30:00')
        with Image.open(self.data / 'cache' / f"{meta['cache_key']}-preview.webp") as preview:
            self.assertEqual(preview.size, (600, 900))

    def test_exact_filters_dates_sort_and_pagination(self):
        self.index()
        self.assertEqual(self.catalog.query({'category': 'nature'})['total'], 12)
        self.assertEqual(self.catalog.query({'tag': 'warm'})['total'], 16)
        self.assertEqual(self.catalog.query({'tag': 'war'})['total'], 0)
        self.assertEqual(self.catalog.query({'camera': 'Canon EOS R8', 'lens': 'RF 100mm', 'folder': 'Coast'})['total'], 12)
        result = self.catalog.query({'from': '2026-04-15', 'to': '2026-04-15'})
        self.assertEqual(result['total'], 3)
        result = self.catalog.query({'iso_min': '300', 'iso_max': '400', 'sort': 'iso', 'direction': 'asc', 'limit': 2})
        self.assertEqual(result['total'], 12)
        self.assertTrue(all(r['metadata']['iso'] == 300 for r in result['items']))
        page1 = self.catalog.query({'sort': 'name', 'direction': 'asc', 'limit': 2})['items']
        page2 = self.catalog.query({'sort': 'name', 'direction': 'asc', 'limit': 2, 'offset': 2})['items']
        self.assertFalse({r['id'] for r in page1} & {r['id'] for r in page2})
        self.assertEqual(page1[0]['metadata']['original_filename'], 'study-01.jpg')
        self.assertEqual(self.catalog.query({'q': "' OR 1=1 --"})['total'], 0)
        with self.assertRaises(ValueError):
            self.catalog.query({'sort': 'id; DROP TABLE photos'})

    def test_changed_deleted_and_returning_files(self):
        self.index()
        row = self.catalog.query({'q': 'study-01.jpg'})['items'][0]
        path = Path(row['path'])
        original = path.read_bytes()
        Image.new('RGB', (80, 40), 'red').save(path)
        self.assertEqual(self.index()['indexed'], 1)
        updated = self.catalog.get(row['id'])
        self.assertEqual(updated['metadata']['width'], 80)
        self.assertEqual(updated['metadata']['tags'], self.annotations['Coast/study-01.jpg']['tags'])
        self.assertNotEqual(updated['metadata']['cache_key'], row['metadata']['cache_key'])
        path.unlink()
        self.index()
        self.assertEqual(self.catalog.query({})['total'], 23)
        self.assertEqual(self.catalog.get(row['id'])['present'], 0)
        path.write_bytes(original)
        self.index()
        self.assertEqual(self.catalog.query({})['total'], 24)

    def test_corrupt_unsupported_and_no_exif(self):
        (self.root / 'bad.jpg').write_text('not an image')
        (self.root / 'raw.cr3').write_text('synthetic placeholder')
        Image.new('RGB', (30, 60)).save(self.root / 'plain.png')
        report = self.index()
        self.assertEqual(len(report['errors']), 1)
        self.assertEqual(report['unsupported'], 1)
        self.assertEqual(self.catalog.query({})['total'], 25)
        meta = self.catalog.query({'q': 'plain.png'})['items'][0]['metadata']
        self.assertIsNone(meta['date_taken'])
        self.assertIsNotNone(meta['modified_at'])

    def test_symlinks_and_overlapping_storage_rejected(self):
        outside = self.base / 'outside.jpg'
        Image.new('RGB', (10, 10)).save(outside)
        try:
            (self.root / 'outside.jpg').symlink_to(outside)
        except OSError:
            self.skipTest('Symlinks unavailable on this platform')
        self.index()
        self.assertEqual(self.catalog.query({})['total'], 24)
        for data in (self.root, self.root / 'cache', self.root.parent):
            with self.assertRaises(ValueError):
                separate_paths(self.root, data)
        with self.assertRaises(ValueError):
            separate_paths(self.base / 'missing', self.data)

    def test_reject_foreign_db_and_manifest(self):
        path = self.base / 'gallery.db'
        with sqlite3.connect(path) as db:
            db.execute('CREATE TABLE images (id INTEGER)')
        with self.assertRaises(ValueError):
            SQLiteCatalog(path)
        bad = self.base / 'bad.json'
        for value in [{'a.jpg': {'tags': 'not a list'}}, {'a.jpg': {'path': '/private'}}]:
            bad.write_text(json.dumps(value))
            with self.assertRaises(ValueError):
                load_annotations(bad)
        with self.assertRaises(FileExistsError):
            create_demo(self.base / 'demo')

    def test_manifest_metadata_survives_rescan_without_manifest(self):
        self.index()
        scan(self.root, self.data, self.catalog)
        self.assertEqual(self.catalog.query({'category': 'nature'})['total'], 12)

    def test_server_boundaries_and_cached_preview(self):
        report = self.index()
        server = make_server(self.catalog, self.data, report, port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        def cleanup():
            server.shutdown()
            server.server_close()
            thread.join()
        self.addCleanup(cleanup)
        def get(path, headers=None):
            connection = http.client.HTTPConnection('127.0.0.1', server.server_port)
            connection.request('GET', path, headers=headers or {})
            response = connection.getresponse()
            body = response.read()
            result = response.status, body, dict(response.getheaders())
            connection.close()
            return result
        status, body, headers = get('/api/photos')
        self.assertEqual(status, 200)
        self.assertNotIn(str(self.root).encode(), body)
        self.assertIn("frame-ancestors 'none'", headers['Content-Security-Policy'])
        row = json.loads(body)['items'][0]
        self.assertEqual(get(f"/image/{row['id']}/preview")[0], 200)
        self.assertEqual(get('/image/../../etc/passwd')[0], 404)
        self.assertEqual(get('/api/photos?limit=not-a-number')[0], 400)
        self.assertEqual(get('/api/photos', {'Host': 'evil.example'})[0], 403)
        self.assertEqual(get('/api/photos', {'Origin': 'https://evil.example'})[0], 403)
        self.assertEqual(get('/api/photos', {'Sec-Fetch-Site': 'cross-site'})[0], 403)
        self.assertEqual(get('/api/photos', {'Origin': 'http://localhost:9999'})[0], 403)
        self.assertEqual(get('/')[0], 200)
        self.assertEqual(get('/app.js')[0], 200)

    def test_storage_protocol_can_be_replaced(self):
        class MemoryCatalog:
            def __init__(self):
                self.rows = {}
            def get(self, image_id):
                return self.rows.get(image_id)
            def put(self, record):
                self.rows[record['id']] = record
            def mark_missing(self, root, seen):
                for image_id, row in self.rows.items():
                    if row['root'] == root and image_id not in seen:
                        row['present'] = 0
        catalog = MemoryCatalog()
        result = scan(self.root, self.data, catalog, self.annotations)
        self.assertEqual(result['indexed'], 24)
        self.assertEqual(len(catalog.rows), 24)


if __name__ == '__main__':
    unittest.main()

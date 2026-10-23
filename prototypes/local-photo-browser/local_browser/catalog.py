"""Replaceable catalog boundary. Metadata uses the gallery's images vocabulary."""
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Protocol


class Catalog(Protocol):
    def get(self, image_id: str) -> dict | None: ...
    def put(self, record: dict) -> None: ...
    def mark_missing(self, root: str, seen: set[str]) -> None: ...
    def query(self, filters: dict) -> dict: ...
    def facets(self) -> dict: ...


SORTS = {
    'name': "json_extract(metadata, '$.original_filename') COLLATE NOCASE",
    'date': "COALESCE(json_extract(metadata, '$.date_taken'), json_extract(metadata, '$.modified_at'))",
    'iso': "json_extract(metadata, '$.iso')",
    'size': "json_extract(metadata, '$.file_size')",
    'camera': "json_extract(metadata, '$.camera') COLLATE NOCASE",
}


class SQLiteCatalog:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            # Refuse unrelated databases (especially the production gallery).
            tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if tables and 'local_catalog_version' not in tables:
                raise ValueError('Not a local browser catalog; choose a new data directory')
            db.executescript('''
                CREATE TABLE IF NOT EXISTS local_catalog_version (version INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS photos (
                    id TEXT PRIMARY KEY, root TEXT NOT NULL, path TEXT NOT NULL,
                    fingerprint TEXT NOT NULL, present INTEGER NOT NULL,
                    metadata TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS photos_root ON photos(root, present);
            ''')
            versions = [r[0] for r in db.execute('SELECT version FROM local_catalog_version')]
            if not versions:
                db.execute('INSERT INTO local_catalog_version VALUES (1)')
            elif versions != [1]:
                raise ValueError('Unsupported catalog version')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def decode(row):
        if row is None:
            return None
        record = dict(row)
        record['metadata'] = json.loads(record['metadata'])
        return record

    def get(self, image_id):
        with self.connect() as db:
            return self.decode(db.execute('SELECT * FROM photos WHERE id=?', (image_id,)).fetchone())

    def put(self, record):
        with self.connect() as db:
            db.execute('''INSERT INTO photos VALUES (:id,:root,:path,:fingerprint,:present,:metadata)
                ON CONFLICT(id) DO UPDATE SET root=excluded.root, path=excluded.path,
                fingerprint=excluded.fingerprint, present=excluded.present, metadata=excluded.metadata''',
                       {**record, 'metadata': json.dumps(record['metadata'], ensure_ascii=False)})

    def mark_missing(self, root, seen):
        # Only called after a complete traversal. Retain metadata for disconnected files.
        with self.connect() as db:
            ids = [r[0] for r in db.execute('SELECT id FROM photos WHERE root=?', (root,))]
            db.executemany('UPDATE photos SET present=0 WHERE id=?', [(i,) for i in ids if i not in seen])

    def query(self, filters):
        where, args = ['present=1'], []
        for key in ('camera', 'lens', 'category', 'folder'):
            if filters.get(key):
                where.append(f"json_extract(metadata, '$.{key}') = ?")
                args.append(filters[key])
        if filters.get('tag'):
            where.append("EXISTS (SELECT 1 FROM json_each(metadata, '$.tags') WHERE value=?)")
            args.append(filters['tag'])
        if filters.get('q'):
            # Search decoded leaf values (including individual tags), never JSON
            # keys, container syntax, nulls, or the internal derivative cache key.
            where.append("""EXISTS (
                SELECT 1 FROM json_tree(photos.metadata) AS field
                WHERE field.type IN ('text', 'integer', 'real')
                  AND field.key != 'cache_key'
                  AND instr(lower(CAST(field.atom AS TEXT)), lower(?)) > 0
            )""")
            args.append(filters['q'])
        for key, operator in [('from', '>='), ('to', '<=')]:
            if filters.get(key):
                where.append(f"substr(COALESCE(json_extract(metadata, '$.date_taken'), json_extract(metadata, '$.modified_at')),1,10) {operator} ?")
                args.append(filters[key])
        for key, operator in [('iso_min', '>='), ('iso_max', '<=')]:
            if filters.get(key):
                where.append(f"json_extract(metadata, '$.iso') {operator} ?")
                args.append(int(filters[key]))
        order = SORTS.get(filters.get('sort', 'date'))
        if order is None:
            raise ValueError('Invalid sort')
        direction = 'ASC' if filters.get('direction') == 'asc' else 'DESC'
        limit = min(200, max(1, int(filters.get('limit', 100))))
        offset = max(0, int(filters.get('offset', 0)))
        clause = ' AND '.join(where)
        with self.connect() as db:
            total = db.execute(f'SELECT count(*) FROM photos WHERE {clause}', args).fetchone()[0]
            rows = db.execute(f'SELECT * FROM photos WHERE {clause} ORDER BY ({order}) IS NULL, {order} {direction}, id LIMIT ? OFFSET ?', args + [limit, offset]).fetchall()
        return {'items': [self.decode(r) for r in rows], 'total': total, 'offset': offset, 'limit': limit}

    def facets(self):
        result = {}
        with self.connect() as db:
            for key in ('camera', 'lens', 'category', 'folder'):
                result[key] = [r[0] for r in db.execute(f"SELECT DISTINCT json_extract(metadata, '$.{key}') AS v FROM photos WHERE present=1 AND v IS NOT NULL AND v != '' ORDER BY v")]
            result['tag'] = [r[0] for r in db.execute("SELECT DISTINCT j.value FROM photos, json_each(photos.metadata, '$.tags') j WHERE present=1 ORDER BY j.value")]
        return result

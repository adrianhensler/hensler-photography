"""Explicit scans only; source files are opened for reading, never mutated."""
import hashlib
import json
import os
from pathlib import Path

from .catalog import Catalog
from .imaging import SUPPORTED, RAW_VIDEO, read_metadata, variants

EDITORIAL = {'title', 'caption', 'description', 'alt_text', 'location', 'category', 'tags'}


def separate_paths(root: Path, data: Path):
    root, data = root.resolve(), data.resolve()
    if root == data or root in data.parents or data in root.parents:
        raise ValueError('Photo folder and catalog directory must not overlap')
    if not root.is_dir():
        raise ValueError('Photo folder does not exist')
    return root, data


def load_annotations(path: Path | None):
    """Neutral import seam, deliberately not an ACDSee database parser."""
    if path is None:
        return {}
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise ValueError('Metadata manifest must map relative filenames to objects')
    for name, fields in data.items():
        if not isinstance(fields, dict) or set(fields) - EDITORIAL:
            raise ValueError(f'Unsupported metadata fields for {name}')
        for key, value in fields.items():
            if key == 'tags':
                if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
                    raise ValueError('tags must be a list of strings')
            elif value is not None and not isinstance(value, str):
                raise ValueError(f'{key} must be text or null')
    return data


def scan(root: Path, data: Path, catalog: Catalog, annotations=None):
    root, data = separate_paths(root, data)
    annotations = annotations or {}
    report = {'indexed': 0, 'unchanged': 0, 'unsupported': 0, 'errors': [], 'complete': True}
    seen = set()
    def walk_error(error):
        report['complete'] = False
        report['errors'].append(str(error))
    for parent, dirs, files in os.walk(root, followlinks=False, onerror=walk_error):
        dirs[:] = sorted(d for d in dirs if not (Path(parent) / d).is_symlink())
        for filename in sorted(files):
            path = Path(parent) / filename
            if path.is_symlink():
                continue
            if path.suffix.lower() not in SUPPORTED:
                report['unsupported'] += path.suffix.lower() in RAW_VIDEO
                continue
            relative = path.relative_to(root).as_posix()
            image_id = hashlib.sha256(str(path).encode()).hexdigest()
            seen.add(image_id)
            old = catalog.get(image_id)
            try:
                # Recheck containment to reject symlink replacements since traversal.
                if not path.resolve().is_relative_to(root):
                    raise ValueError('Source escaped photo folder')
                stat = path.stat()
                fingerprint = f'{stat.st_size}:{stat.st_mtime_ns}'
                cache_key = hashlib.sha256(f'{image_id}:{fingerprint}'.encode()).hexdigest()
                cached = all((data / 'cache' / f'{cache_key}-{s}.webp').is_file() for s in ('thumbnail', 'preview'))
                metadata = dict(old['metadata']) if old else {'tags': [], 'category': None}
                if not old or old['fingerprint'] != fingerprint or not cached:
                    metadata.update(read_metadata(path))
                    variants(path, data / 'cache', cache_key)
                    if path.stat().st_mtime_ns != stat.st_mtime_ns or path.stat().st_size != stat.st_size:
                        raise ValueError('File changed during scan; retry after it finishes writing')
                    report['indexed'] += 1
                else:
                    report['unchanged'] += 1
                metadata.update(annotations.get(relative, {}))
                metadata.update(folder=path.parent.relative_to(root).as_posix(), relative_path=relative, cache_key=cache_key)
                catalog.put(dict(id=image_id, root=str(root), path=str(path), fingerprint=fingerprint, present=1, metadata=metadata))
            except Exception as error:
                report['errors'].append(f'{relative}: {error}')
                if old:
                    catalog.put({**old, 'present': 0})
    if report['complete']:
        catalog.mark_missing(str(root), seen)
    return report

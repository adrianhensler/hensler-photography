"""Adapted gallery EXIF conventions and Pillow/LANCZOS/WebP variant strategy.

Unlike api/services/image_processor.py, never write next to the original.
"""
from datetime import datetime, timezone
from pathlib import Path
import os
import tempfile

from PIL import Image, ImageOps

SUPPORTED = {'.jpg', '.jpeg', '.png', '.webp', '.tif', '.tiff', '.bmp'}
RAW_VIDEO = {'.cr2', '.cr3', '.nef', '.arw', '.dng', '.raf', '.heic', '.heif', '.mp4', '.mov'}


def clean(value):
    if isinstance(value, bytes):
        value = value.decode('utf-8', errors='replace')
    return str(value).strip('\x00 ') if value is not None else None


def number(value):
    try:
        return float(value)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def read_metadata(path: Path):
    with Image.open(path) as image:
        exif = image.getexif()
        detail = exif.get_ifd(34665) if 34665 in exif else {}
        values = dict(exif)
        values.update(detail)
        make, model = clean(values.get(271)), clean(values.get(272))
        date = clean(values.get(36867))
        try:
            date = datetime.strptime(date, '%Y:%m:%d %H:%M:%S').isoformat()
        except (TypeError, ValueError):
            date = None
        width, height = image.size
        if exif.get(274) in (5, 6, 7, 8):
            width, height = height, width
        focal, aperture, exposure = [number(values.get(k)) for k in (37386, 33437, 33434)]
        iso = number(values.get(34855))
        location = None
        try:
            gps = exif.get_ifd(34853)
            def degrees(parts):
                return float(parts[0]) + float(parts[1]) / 60 + float(parts[2]) / 3600
            lat, lon = degrees(gps[2]), degrees(gps[4])
            location = f"{lat * (-1 if clean(gps[1]) == 'S' else 1):.6f}, {lon * (-1 if clean(gps[3]) == 'W' else 1):.6f}"
        except (KeyError, TypeError, ValueError, ZeroDivisionError):
            pass
        return {
            'original_filename': path.name, 'camera_make': make, 'camera_model': model,
            'camera': ' '.join(filter(None, (make, model))) or None,
            'lens': clean(values.get(42036)), 'date_taken': date, 'location': location,
            'iso': int(iso) if iso is not None else None,
            'focal_length': f'{focal:g}mm' if focal else None,
            'aperture': f'f/{aperture:g}' if aperture else None,
            'shutter_speed': (f'1/{round(1 / exposure)}s' if exposure < 1 else f'{exposure:g}s') if exposure else None,
            'width': width, 'height': height, 'aspect_ratio': width / height,
            'file_size': path.stat().st_size,
            'modified_at': datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
        }


def variants(path: Path, cache: Path, key: str):
    cache.mkdir(parents=True, exist_ok=True)
    with Image.open(path) as original:
        image = ImageOps.exif_transpose(original)
        if image.mode not in ('RGB', 'RGBA'):
            image = image.convert('RGBA' if 'transparency' in image.info else 'RGB')
        for label, size in [('thumbnail', 400), ('preview', 1600)]:
            target = cache / f'{key}-{label}.webp'
            resized = image.copy()
            resized.thumbnail((size, size), Image.Resampling.LANCZOS)
            fd, name = tempfile.mkstemp(dir=cache, suffix='.webp')
            os.close(fd)
            try:
                resized.save(name, 'WEBP', quality=85, method=4)
                os.replace(name, target)
            finally:
                Path(name).unlink(missing_ok=True)

"""Create only synthetic fixtures in a NEW directory; never overwrite photos."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, TiffImagePlugin


def create_demo(destination: Path):
    destination.mkdir(parents=True, exist_ok=False)
    photos = destination / 'photos'
    annotations = {}
    for i in range(24):
        folder = photos / ('Coast' if i % 2 == 0 else 'Garden')
        folder.mkdir(parents=True, exist_ok=True)
        image = Image.new('RGB', (900, 600), (30 + i * 5, 65 + i * 3, 100 + i * 3))
        draw = ImageDraw.Draw(image)
        draw.ellipse((520 - i * 9, 60, 660 - i * 9, 200), fill=(235, 203, 144))
        draw.polygon([(0, 420), (250, 220 + i * 3), (500, 410), (730, 260), (900, 440), (900, 600), (0, 600)], fill=(28, 52 + i * 3, 55))
        draw.text((28, 28), f'SYNTHETIC / STUDY {i + 1:02}', fill='white')
        exif = Image.Exif()
        exif[271] = 'Canon' if i % 2 == 0 else 'Synthetic'
        exif[272] = 'EOS R8' if i % 2 == 0 else 'Film scan'
        exif[274] = 6 if i == 3 else 1
        exif[34665] = {36867: f'2026:{i % 9 + 1:02}:15 12:30:00', 42036: 'RF 100mm' if i % 2 == 0 else '50mm', 34855: 100 * (i % 4 + 1), 37386: TiffImagePlugin.IFDRational(100), 33437: TiffImagePlugin.IFDRational(28, 10), 33434: TiffImagePlugin.IFDRational(1, 250)}
        path = folder / f'study-{i + 1:02}.jpg'
        image.save(path, exif=exif)
        annotations[path.relative_to(photos).as_posix()] = {'category': 'landscape' if i % 2 == 0 else 'nature', 'tags': ['synthetic', 'warm' if i % 3 else 'cool'], 'caption': f'Generated geometric study {i + 1}; not a real photograph.'}
    (destination / 'metadata.json').write_text(json.dumps(annotations, indent=2), encoding='utf-8')
    return photos

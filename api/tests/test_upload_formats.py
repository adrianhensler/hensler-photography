"""
Uploads only ever reach Pillow's JPEG and PNG decoders. The browser's
Content-Type is client-controlled, so a TIFF (or FPX, BMP, ...) labelled
image/jpeg must be rejected, not decoded. Camera multi-picture JPEGs (MPO)
are still real JPEGs and must keep working. The saved extension follows the
detected format, never the uploaded filename.
"""

import io
from pathlib import Path

import pytest
from PIL import Image

from api.services.image_processor import ACCEPTED_FORMATS


def _image_bytes(fmt: str, **save_args) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (32, 24), "grey").save(buf, format=fmt, **save_args)
    return buf.getvalue()


def test_camera_mpo_still_opens_as_accepted_format():
    second = Image.new("RGB", (32, 24), "white")
    data = _image_bytes("MPO", save_all=True, append_images=[second])
    with Image.open(io.BytesIO(data), formats=ACCEPTED_FORMATS) as img:
        assert img.format == "MPO"


def test_other_decoders_never_run():
    with pytest.raises(Image.UnidentifiedImageError):
        Image.open(io.BytesIO(_image_bytes("TIFF")), formats=ACCEPTED_FORMATS)


@pytest.mark.asyncio
async def test_tiff_labelled_as_jpeg_is_rejected(client, auth_headers_adrian):
    gallery = Path("/app/assets/gallery")
    before = set(gallery.iterdir()) if gallery.exists() else set()

    response = await client.post(
        "/api/images/ingest",
        headers=auth_headers_adrian,
        files={"file": ("disguised.jpg", _image_bytes("TIFF"), "image/jpeg")},
    )

    assert response.status_code == 415
    after = set(gallery.iterdir()) if gallery.exists() else set()
    assert after == before  # nothing was written to disk


@pytest.mark.asyncio
async def test_saved_extension_comes_from_detected_format(client, auth_headers_adrian, monkeypatch):
    # Originals are served by extension, so an image named .html must not be
    # saved as .html. Stop the upload at the EXIF step (no AI call); the
    # endpoint's error path removes the saved file.
    import api.services.exif

    saved = []

    def stop_after_save(path):
        saved.append(path)
        raise RuntimeError("stop test upload here")

    monkeypatch.setattr(api.services.exif, "extract_exif", stop_after_save)

    await client.post(
        "/api/images/ingest",
        headers=auth_headers_adrian,
        files={"file": ("page.html", _image_bytes("PNG"), "image/png")},
    )

    assert len(saved) == 1
    assert Path(saved[0]).suffix == ".png"
    assert not Path(saved[0]).exists()

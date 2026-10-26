"""
Uploads only ever reach Pillow's JPEG and PNG decoders. The browser's
Content-Type is client-controlled, so a TIFF (or FPX, BMP, ...) labelled
image/jpeg must be rejected, not decoded. Camera multi-picture JPEGs (MPO)
are still real JPEGs and must keep working.
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
    assert after == before  # the saved upload was removed

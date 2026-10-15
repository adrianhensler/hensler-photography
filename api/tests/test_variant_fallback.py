"""
Public image URLs never point at the raw upload while a generated (EXIF-
stripped) variant exists. Small originals have no large or medium variant
because the processor never upscales; the original-size `full` stands in.
"""

import pytest

from api.database import get_db_connection
from api.routes.gallery import pick_variants


def test_small_original_uses_full_for_missing_sizes():
    # A 693px original: thumbnail and full only (photo #76 in production)
    picked = pick_variants({"thumbnail": "t.webp", "full": "f.webp"}, "raw.jpg")
    assert picked == {
        "thumbnail": "t.webp",
        "medium": "f.webp",
        "large": "f.webp",
        "full": "f.webp",
    }


def test_medium_sized_original_uses_full_for_large():
    # A 1024px original: no large variant (photo #4 in production)
    picked = pick_variants({"thumbnail": "t.webp", "medium": "m.webp", "full": "f.webp"}, "raw.jpg")
    assert picked["large"] == "f.webp"
    assert picked["medium"] == "m.webp"


def test_raw_upload_only_without_any_variant():
    assert set(pick_variants({}, "raw.jpg").values()) == {"raw.jpg"}
    assert "raw.jpg" not in pick_variants({"thumbnail": "t.webp"}, "raw.jpg").values()


@pytest.mark.asyncio
async def test_published_gallery_never_returns_raw_upload(client):
    async with get_db_connection() as db:
        await db.execute("DELETE FROM image_variants")
        for size, width in (("thumbnail", 400), ("full", 693)):
            await db.execute(
                "INSERT INTO image_variants (image_id, format, size, filename, width, height) "
                "VALUES (1, 'webp', ?, ?, ?, ?)",
                (size, f"adrian_test_{size}.webp", width, width),
            )
        await db.commit()

    images = (await client.get("/api/gallery/published?user_id=1")).json()["images"]
    image = next(i for i in images if i["id"] == 1)
    urls = [image[k] for k in ("thumbnail_url", "medium_url", "large_url", "image_url")]
    assert all(url.endswith(".webp") for url in urls)
    assert image["large_url"] == "/assets/gallery/adrian_test_full.webp"

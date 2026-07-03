"""
Tests for soft-delete image deletion (api/services/image_deletion.py).

Both DELETE /api/images/{id} (api/routes/ingestion.py) and
DELETE /api/photographer/images/{id} (api/routes/photographer.py) now share
this soft-delete implementation instead of hard-deleting the row (and, in
ingestion.py's case, immediately unlinking files with no undo; in
photographer.py's case, leaving files orphaned on disk forever).

These tests exercise api.services.image_deletion directly against a real
SQLite schema (api.database.SCHEMA) so they reflect the actual production
table shape, rather than the simplified fixture schema used by the HTTP
integration tests in test_gallery_security.py / test_simple_security.py.
"""

import sqlite3
from pathlib import Path

import pytest

import api.database as database_module
from api.services.image_deletion import purge_expired_deletes, soft_delete_image


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Create a real gallery.db schema in a temp file and point the app at it."""
    db_path = tmp_path / "test_gallery.db"

    conn = sqlite3.connect(str(db_path))
    conn.executescript(database_module.SCHEMA)
    conn.executescript(database_module.SEED_DATA)
    conn.commit()
    conn.close()

    monkeypatch.setattr(database_module, "DATABASE_PATH", str(db_path))

    return db_path


def _insert_image(db_path: Path, image_id: int, filename: str, user_id: int = 1) -> None:
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """
        INSERT INTO images (id, user_id, filename, slug, title, published)
        VALUES (?, ?, ?, ?, 'Test Image', 1)
        """,
        (image_id, user_id, filename, f"test-image-{image_id}"),
    )
    conn.commit()
    conn.close()


def _get_deleted_at(db_path: Path, image_id: int):
    conn = sqlite3.connect(str(db_path))
    row = conn.execute("SELECT deleted_at FROM images WHERE id = ?", (image_id,)).fetchone()
    conn.close()
    return row[0] if row else None


def _image_exists(db_path: Path, image_id: int) -> bool:
    conn = sqlite3.connect(str(db_path))
    row = conn.execute("SELECT 1 FROM images WHERE id = ?", (image_id,)).fetchone()
    conn.close()
    return row is not None


@pytest.mark.asyncio
async def test_soft_delete_marks_deleted_at_without_removing_row(temp_db):
    _insert_image(temp_db, image_id=1, filename="20260101_000000_abc.jpg")

    deleted = await soft_delete_image(1)

    assert deleted is True
    assert _image_exists(temp_db, 1), "soft delete must not remove the row"
    assert _get_deleted_at(temp_db, 1) is not None


@pytest.mark.asyncio
async def test_soft_delete_is_idempotent(temp_db):
    _insert_image(temp_db, image_id=1, filename="20260101_000000_abc.jpg")

    first = await soft_delete_image(1)
    second = await soft_delete_image(1)

    assert first is True
    assert second is False, "re-deleting an already-deleted image should be a no-op, not an error"


@pytest.mark.asyncio
async def test_soft_delete_nonexistent_image_returns_false(temp_db):
    deleted = await soft_delete_image(99999)
    assert deleted is False


@pytest.mark.asyncio
async def test_purge_removes_expired_soft_deletes_and_files(temp_db, tmp_path):
    gallery_dir = tmp_path / "gallery"
    gallery_dir.mkdir()

    original = gallery_dir / "20260101_000000_abc.jpg"
    original.write_bytes(b"fake image data")

    _insert_image(temp_db, image_id=1, filename="20260101_000000_abc.jpg")
    await soft_delete_image(1)

    # Backdate deleted_at so it's well past any grace period
    conn = sqlite3.connect(str(temp_db))
    conn.execute(
        "UPDATE images SET deleted_at = datetime('now', '-60 days') WHERE id = ?", (1,)
    )
    conn.commit()
    conn.close()

    purged_ids = await purge_expired_deletes(grace_period_days=30, gallery_dir=gallery_dir)

    assert purged_ids == [1]
    assert not _image_exists(temp_db, 1), "purge should hard-delete the row"
    assert not original.exists(), "purge should remove the physical file"


@pytest.mark.asyncio
async def test_purge_leaves_recently_deleted_images_alone(temp_db, tmp_path):
    gallery_dir = tmp_path / "gallery"
    gallery_dir.mkdir()

    original = gallery_dir / "20260101_000000_recent.jpg"
    original.write_bytes(b"fake image data")

    _insert_image(temp_db, image_id=2, filename="20260101_000000_recent.jpg")
    await soft_delete_image(2)  # deleted "now" - well within the grace period

    purged_ids = await purge_expired_deletes(grace_period_days=30, gallery_dir=gallery_dir)

    assert purged_ids == []
    assert _image_exists(temp_db, 2), "recently soft-deleted images must survive the purge"
    assert original.exists(), "files for recently soft-deleted images must not be removed"


@pytest.mark.asyncio
async def test_purge_ignores_active_images(temp_db, tmp_path):
    gallery_dir = tmp_path / "gallery"
    gallery_dir.mkdir()

    _insert_image(temp_db, image_id=3, filename="active.jpg")
    # Never soft-deleted

    purged_ids = await purge_expired_deletes(grace_period_days=0, gallery_dir=gallery_dir)

    assert purged_ids == []
    assert _image_exists(temp_db, 3)

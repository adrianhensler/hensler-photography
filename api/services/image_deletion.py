"""
Shared image deletion logic (soft delete + grace-period physical cleanup).

Previously, DELETE /api/images/{id} (api/routes/ingestion.py) hard-deleted
the image row and immediately unlinked the original + all variant files —
irreversible, no undo. DELETE /api/photographer/images/{id}
(api/routes/photographer.py) hard-deleted the row but never touched the
files, leaving them orphaned on disk forever (see the removed TODO there).

Both endpoints now call soft_delete_image() below, which only marks the row
as deleted (images.deleted_at). Physical files are removed later, in bulk,
by purge_expired_deletes() — intended to run as a periodic/cron cleanup
step (`python -m api.cleanup`), well past the point where an accidental or
malicious delete could reasonably need to be undone.
"""

from pathlib import Path
from typing import Optional

from api.logging_config import get_logger

logger = get_logger(__name__)

GALLERY_DIR = Path("/app/assets/gallery")

# How long a soft-deleted image is kept before its files/row are purged.
DEFAULT_GRACE_PERIOD_DAYS = 30


async def soft_delete_image(image_id: int) -> bool:
    """Mark an image as deleted without touching its files or DB row.

    Returns True if a row was updated, False if the image did not exist or
    was already soft-deleted (idempotent — re-deleting is a no-op, not an
    error, matching DELETE semantics elsewhere in the API).

    Callers are responsible for their own ownership/authorization checks
    before calling this (see verify_image_ownership() in
    api/routes/ingestion.py and api/routes/photographer.py).
    """
    from api.database import get_db_connection

    async with get_db_connection() as db:
        cursor = await db.execute(
            """
            UPDATE images
            SET deleted_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND deleted_at IS NULL
            """,
            (image_id,),
        )
        await db.commit()
        return cursor.rowcount > 0


async def purge_expired_deletes(
    grace_period_days: int = DEFAULT_GRACE_PERIOD_DAYS,
    gallery_dir: Optional[Path] = None,
) -> list[int]:
    """Permanently remove soft-deleted images past the grace period.

    For each image whose deleted_at is older than grace_period_days:
    - unlink the original file and all known WebP variants from disk
      (missing files are ignored — cleanup is best-effort/idempotent)
    - hard-delete the images row (image_variants rows cascade via FK)

    Returns the list of image_ids that were purged.

    Intended to be invoked out-of-band (cron / admin action), not
    synchronously from a delete request — see module docstring.
    """
    from api.database import get_db_connection

    gallery_dir = gallery_dir or GALLERY_DIR
    purged_ids: list[int] = []

    async with get_db_connection() as db:
        cursor = await db.execute(
            """
            SELECT id, filename FROM images
            WHERE deleted_at IS NOT NULL
              AND deleted_at <= datetime('now', ?)
            """,
            (f"-{grace_period_days} days",),
        )
        expired = await cursor.fetchall()

        for row in expired:
            image_id, filename = row[0], row[1]

            variant_cursor = await db.execute(
                "SELECT filename FROM image_variants WHERE image_id = ?", (image_id,)
            )
            variants = await variant_cursor.fetchall()

            # Remove original
            original_path = gallery_dir / filename
            if original_path.exists():
                original_path.unlink()

            # Remove variants
            for variant_row in variants:
                variant_path = gallery_dir / variant_row[0]
                if variant_path.exists():
                    variant_path.unlink()

            await db.execute("DELETE FROM images WHERE id = ?", (image_id,))
            purged_ids.append(image_id)

            logger.info(
                f"Purged soft-deleted image {image_id} ({filename}) after grace period",
                extra={"context": {"image_id": image_id, "filename": filename}},
            )

        await db.commit()

    return purged_ids

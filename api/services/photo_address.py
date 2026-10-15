"""
Photo addresses: the public /photo/<address> a photographer approves.

Every image has a slug from upload, made from the first AI-drafted title.
Those were never public and are often wrong, so a photo page is reachable
by its address only once the photographer approves it in the gallery
manager (images.slug_approved = 1). Until then pages use /photo/<id>.

An approved address is fixed: editing the title later does not change it.
The photographer can choose to update it to match the title; the old
address is kept in image_address_redirects and keeps working (302).
"""

from slugify import slugify

MAX_LENGTH = 80


def address_from_title(title: str, image_id: int) -> str:
    """URL form of a title, e.g. 'Dingle Tower in Fog' -> 'dingle-tower-in-fog'."""
    base = slugify(title or "", max_length=MAX_LENGTH, word_boundary=True)
    if not base:
        return f"photo-{image_id}"
    # An all-digit address would be read as an image id
    if base.isdigit():
        return f"photo-{base}"
    return base


def photo_path(image_id: int, slug: str, slug_approved) -> str:
    """Public path of a photo page: its approved address, else its id."""
    return f"/photo/{slug}" if slug_approved else f"/photo/{image_id}"


async def _taken(db, user_id: int, image_id: int, candidate: str) -> bool:
    """True if another of this photographer's images holds the address."""
    cursor = await db.execute(
        """
        SELECT 1 FROM images WHERE user_id = ? AND slug = ? AND id != ?
        UNION ALL
        SELECT 1 FROM image_address_redirects WHERE user_id = ? AND slug = ? AND image_id != ?
        """,
        (user_id, candidate, image_id, user_id, candidate, image_id),
    )
    return await cursor.fetchone() is not None


async def available_address(db, user_id: int, image_id: int, title: str) -> str:
    """The address this title would get: its URL form, numbered if taken."""
    base = address_from_title(title, image_id)
    candidate, n = base, 2
    while await _taken(db, user_id, image_id, candidate):
        candidate = f"{base}-{n}"
        n += 1
    return candidate


async def address_info(db, image_id: int) -> dict:
    """Address state for the console: current, approved, and what the title gives."""
    cursor = await db.execute(
        "SELECT user_id, title, slug, slug_approved FROM images WHERE id = ?", (image_id,)
    )
    user_id, title, slug, approved = await cursor.fetchone()
    return {
        "approved": bool(approved),
        "address": slug if approved else None,
        "from_title": await available_address(db, user_id, image_id, title),
        "path": photo_path(image_id, slug, approved),
    }


async def approve_address(db, image_id: int) -> dict:
    """
    Set the address from the saved title and mark it approved.

    Approving the address confirms the title it is made from, so the title
    counts as reviewed too (ADR 0004). Idempotent: approving again with the
    same title changes nothing. When an approved address changes, the old
    one becomes a redirect. Caller commits.
    """
    cursor = await db.execute(
        "SELECT user_id, title, slug, slug_approved FROM images WHERE id = ?", (image_id,)
    )
    user_id, title, old_slug, was_approved = await cursor.fetchone()
    new_slug = await available_address(db, user_id, image_id, title)

    if was_approved and old_slug != new_slug:
        await db.execute(
            "INSERT OR REPLACE INTO image_address_redirects (user_id, slug, image_id) "
            "VALUES (?, ?, ?)",
            (user_id, old_slug, image_id),
        )
    # Returning to one of its own former addresses: it is current again
    await db.execute(
        "DELETE FROM image_address_redirects WHERE user_id = ? AND slug = ?",
        (user_id, new_slug),
    )
    await db.execute(
        "UPDATE images SET slug = ?, slug_approved = 1, ai_generated_title = 0, "
        "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (new_slug, image_id),
    )
    return {"old": old_slug if was_approved else None, "new": new_slug}

"""
Photo addresses: the public /photo/<address> a photographer approves.

Every image has a slug from upload, made from the first AI-drafted title.
Those were never public and are often wrong, so a photo page is reachable
by its address only once the photographer approves it in the gallery
manager (images.slug_approved = 1). Until then pages use /photo/<id>.

The address starts as the URL form of the title, but the photographer can
type their own; either way it is normalized to URL form (lowercase words
joined by hyphens). An approved address is fixed: editing the title later
does not change it. The photographer can change it; the old address is kept
in image_address_redirects and keeps working (302).
"""

from slugify import slugify

MAX_LENGTH = 80


class AddressTaken(ValueError):
    """A typed address already belongs to another of the photographer's photos."""


def address_from_title(title: str, image_id: int) -> str:
    """URL form of a title or typed address: 'Dingle Tower in Fog' -> 'dingle-tower-in-fog'."""
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


async def approve_address(db, image_id: int, requested: str = None) -> dict:
    """
    Set the address and mark it approved: the typed `requested` address, or
    the saved title's URL form when none is given.

    A typed address is used exactly (after normalizing), so if another photo
    holds it, AddressTaken is raised rather than quietly numbering it. One
    made from the title is numbered if taken.

    Approving happens in the editor beside the title, so the title counts as
    reviewed too (ADR 0004). Idempotent. When an approved address changes,
    the old one becomes a redirect. Caller commits.
    """
    cursor = await db.execute(
        "SELECT user_id, title, slug, slug_approved FROM images WHERE id = ?", (image_id,)
    )
    user_id, title, old_slug, was_approved = await cursor.fetchone()
    if requested and requested.strip():
        new_slug = address_from_title(requested, image_id)
        if await _taken(db, user_id, image_id, new_slug):
            raise AddressTaken(new_slug)
    else:
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

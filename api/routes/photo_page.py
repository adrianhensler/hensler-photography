"""
Public photo pages: /photo/{id} on each portfolio site.

Server-rendered so that link previews (iMessage, WhatsApp, Facebook,
Slack) show the photo itself: those crawlers read the og: tags without
running JavaScript. The photographer is found from the site's hostname
(adrian.hensler.photography -> users.subdomain = 'adrian'), so one route
serves every portfolio site.

A photo is reachable at /photo/<id> always, and at /photo/<address> once
the photographer approves an address (api/services/photo_address.py).
After approval the id link (301) and any former addresses (302) redirect
to the current address, so every link that was ever shared keeps working.
"""

import re
from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from api.database import get_db_connection
from api.services.photo_address import photo_path

router = APIRouter(tags=["photo-page"])
templates = Jinja2Templates(directory="api/templates", autoescape=True)

# Portfolio hosts only (the hub has no photo pages), optionally with the
# dev stack's port. Absolute URLs in the page are built from this match,
# never from an arbitrary Host header.
PORTFOLIO_HOST = re.compile(r"^([a-z0-9-]+)\.hensler\.photography(:\d+)?$")

# Display variant, best first (sizes from api/services/image_processor.py)
VARIANT_PREFERENCE = ("large", "medium", "full", "thumbnail")


async def _load_photographer(subdomain: str):
    async with get_db_connection() as db:
        cursor = await db.execute(
            "SELECT id, display_name FROM users WHERE subdomain = ?", (subdomain,)
        )
        row = await cursor.fetchone()
    return {"id": row[0], "name": row[1]} if row else None


async def _load_photo(user_id: int, image_id: int):
    """One published photo with its EXIF-stripped WebP variants, or None."""
    async with get_db_connection() as db:
        cursor = await db.execute(
            """
            SELECT
                i.id, i.title, i.caption, i.alt_text, i.width, i.height, i.share_exif,
                i.camera_make, i.camera_model, i.lens, i.focal_length,
                i.aperture, i.shutter_speed, i.iso, i.location,
                i.ai_generated_title, i.ai_generated_caption,
                i.slug, i.slug_approved
            FROM images i
            WHERE i.id = ? AND i.user_id = ? AND i.published = 1 AND i.deleted_at IS NULL
            """,
            (image_id, user_id),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        cursor = await db.execute(
            "SELECT size, filename, width, height FROM image_variants "
            "WHERE image_id = ? AND format = 'webp'",
            (image_id,),
        )
        variants = {v[0]: v[1:] for v in await cursor.fetchall()}

    # Generated variants only, never the raw upload, which still carries
    # whatever EXIF/GPS the camera embedded. Small originals have no large
    # or medium variant, so fall through to full, then thumbnail.
    main_variant = next((variants[size] for size in VARIANT_PREFERENCE if size in variants), None)
    if not main_variant:
        return None
    medium = variants.get("medium")

    exif_parts = []
    if row[6]:  # share_exif; same order and format as the lightbox
        camera = " ".join(part for part in (row[7], row[8]) if part)
        exif_parts = [camera, row[9], row[10], row[11], row[12]]
        exif_parts += [f"ISO {row[13]}" if row[13] else None]
        exif_parts = [str(part) for part in exif_parts if part]

    # NULL counts as AI-drafted, matching the gallery API
    title_unreviewed = row[15] is None or bool(row[15])
    caption_unreviewed = row[16] is None or bool(row[16])

    return {
        "id": row[0],
        "path": photo_path(row[0], row[17], row[18]),
        "ai_note": _ai_note(title_unreviewed, bool(row[2]) and caption_unreviewed),
        "title": row[1] or "Untitled",
        "caption": row[2],
        "alt_text": row[3] or row[1] or "",
        "width": row[4],
        "height": row[5],
        "exif": " · ".join(exif_parts),
        "location": row[14] if row[6] else None,
        "title_unreviewed": title_unreviewed,
        "caption_unreviewed": caption_unreviewed,
        "image_url": f"/assets/gallery/{main_variant[0]}",
        "image_width": main_variant[1],
        "medium_url": f"/assets/gallery/{medium[0]}" if medium else None,
        # Previews size their card from these; stated only when recorded
        "og_size": main_variant[1:] if main_variant[1] and main_variant[2] else None,
    }


def _ai_note(title_unreviewed: bool, caption_unreviewed: bool):
    """Quiet provenance line for visitors (ADR 0004), or None."""
    if title_unreviewed and caption_unreviewed:
        return "Title and description drafted by AI, not yet reviewed."
    if title_unreviewed:
        return "Title drafted by AI, not yet reviewed."
    if caption_unreviewed:
        return "Description drafted by AI, not yet reviewed."
    return None


def _render(request: Request, context: dict, status_code: int = 200):
    context["request"] = request
    context["year"] = datetime.now().year
    response = templates.TemplateResponse("public/photo.html", context, status_code=status_code)
    response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=60"
    return response


async def _image_id_for_address(user_id: int, address: str):
    """(image id, is_current) for an approved or former address, else (None, False)."""
    async with get_db_connection() as db:
        cursor = await db.execute(
            "SELECT id FROM images WHERE user_id = ? AND slug = ? AND slug_approved = 1",
            (user_id, address),
        )
        row = await cursor.fetchone()
        if row:
            return row[0], True
        # Unapproved slugs never resolve: they came from AI drafts and were never public
        cursor = await db.execute(
            "SELECT image_id FROM image_address_redirects WHERE user_id = ? AND slug = ?",
            (user_id, address),
        )
        row = await cursor.fetchone()
    return (row[0], False) if row else (None, False)


@router.get("/photo/{key}", response_class=HTMLResponse)
async def photo_page(request: Request, key: str):
    host = (request.headers.get("host") or "").lower()
    match = PORTFOLIO_HOST.match(host)
    photographer = await _load_photographer(match.group(1)) if match else None
    photo = None
    is_current = False
    if photographer:
        if key.isdigit():
            image_id = int(key)
        else:
            image_id, is_current = await _image_id_for_address(photographer["id"], key)
        if image_id:
            photo = await _load_photo(photographer["id"], image_id)

    if not photo:
        return _render(request, {"photo": None, "photographer": photographer}, 404)

    # Id links move to the current address for good: an id never becomes an
    # address. Former addresses redirect temporarily, since one can become
    # current again, and a cached permanent redirect would then loop.
    if photo["path"] != f"/photo/{key}" and not is_current:
        status = 301 if key.isdigit() else 302
        return RedirectResponse(photo["path"], status_code=status)

    base_url = f"https://{host}"
    page_url = f"{base_url}{photo['path']}"
    # Previews only quote text a person has reviewed, and say so when the
    # title they show is still an AI draft (ADR 0004)
    description = (
        photo["caption"]
        if photo["caption"] and not photo["caption_unreviewed"]
        else f"A photograph by {photographer['name']}."
    )
    if photo["title_unreviewed"]:
        description += " Title drafted by AI, not yet reviewed."
    return _render(
        request,
        {
            "photo": photo,
            "photographer": photographer,
            "page_url": page_url,
            "og_image": f"{base_url}{photo['image_url']}",
            "description": description,
        },
    )

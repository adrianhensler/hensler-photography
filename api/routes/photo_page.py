"""
Public photo pages: /photo/{id} on each portfolio site.

Server-rendered so that link previews (iMessage, WhatsApp, Facebook,
Slack) show the photo itself: those crawlers read the og: tags without
running JavaScript. The photographer is found from the site's hostname
(adrian.hensler.photography -> users.subdomain = 'adrian'), so one route
serves every portfolio site.

Pages are addressed by image id for now. Ids never change, so these
links stay valid when a photographer-approved address is added later.
"""

import re
from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from api.database import get_db_connection

router = APIRouter(tags=["photo-page"])
templates = Jinja2Templates(directory="api/templates", autoescape=True)

# Portfolio hosts only (the hub has no photo pages), optionally with the
# dev stack's port. Absolute URLs in the page are built from this match,
# never from an arbitrary Host header.
PORTFOLIO_HOST = re.compile(r"^([a-z0-9-]+)\.hensler\.photography(:\d+)?$")


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
                i.ai_generated_caption,
                medium.filename, medium.width, medium.height,
                large.filename, large.width, large.height
            FROM images i
            LEFT JOIN image_variants medium ON i.id = medium.image_id
                AND medium.format = 'webp' AND medium.size = 'medium'
            LEFT JOIN image_variants large ON i.id = large.image_id
                AND large.format = 'webp' AND large.size = 'large'
            WHERE i.id = ? AND i.user_id = ? AND i.published = 1 AND i.deleted_at IS NULL
            """,
            (image_id, user_id),
        )
        row = await cursor.fetchone()

    if not row:
        return None
    # Largest generated variant. Never the raw upload, which still carries
    # whatever EXIF/GPS the camera embedded; with no variant, no page.
    if row[19]:
        main_variant = (row[19], row[20], row[21])
    elif row[16]:
        main_variant = (row[16], row[17], row[18])
    else:
        return None

    exif_parts = []
    if row[6]:  # share_exif; same order and format as the lightbox
        camera = " ".join(part for part in (row[7], row[8]) if part)
        exif_parts = [camera, row[9], row[10], row[11], row[12]]
        exif_parts += [f"ISO {row[13]}" if row[13] else None]
        exif_parts = [str(part) for part in exif_parts if part]

    return {
        "id": row[0],
        "title": row[1] or "Untitled",
        "caption": row[2],
        "alt_text": row[3] or row[1] or "",
        "width": row[4],
        "height": row[5],
        "exif": " · ".join(exif_parts),
        "location": row[14] if row[6] else None,
        # NULL counts as AI-drafted, matching the gallery API
        "caption_unreviewed": row[15] is None or bool(row[15]),
        "image_url": f"/assets/gallery/{main_variant[0]}",
        "image_width": main_variant[1],
        "medium_url": f"/assets/gallery/{row[16]}" if row[16] else None,
        # Previews size their card from these; stated only when recorded
        "og_size": main_variant[1:] if main_variant[1] and main_variant[2] else None,
    }


def _render(request: Request, context: dict, status_code: int = 200):
    context["request"] = request
    context["year"] = datetime.now().year
    response = templates.TemplateResponse("public/photo.html", context, status_code=status_code)
    response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=60"
    return response


@router.get("/photo/{key}", response_class=HTMLResponse)
async def photo_page(request: Request, key: str):
    host = (request.headers.get("host") or "").lower()
    match = PORTFOLIO_HOST.match(host)
    photographer = await _load_photographer(match.group(1)) if match else None
    photo = None
    if photographer and key.isdigit():
        photo = await _load_photo(photographer["id"], int(key))

    if not photo:
        return _render(request, {"photo": None, "photographer": photographer}, 404)

    base_url = f"https://{host}"
    page_url = f"{base_url}/photo/{photo['id']}"
    # Previews only quote text a person has reviewed (ADR 0004)
    description = (
        photo["caption"]
        if photo["caption"] and not photo["caption_unreviewed"]
        else f"A photograph by {photographer['name']}."
    )
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

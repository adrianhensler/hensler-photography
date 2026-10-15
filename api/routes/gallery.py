"""
Public gallery API routes - no authentication required.

These endpoints serve published images to the public static sites.
"""

from fastapi import APIRouter, HTTPException, Response

from api.services.photo_address import photo_path

router = APIRouter(prefix="/api/gallery", tags=["gallery"])

# For each display size, the generated variants to use, best first. A size is
# missing only when the original is smaller than it (the processor never
# upscales), so the original-size `full` variant is the right stand-in for
# the larger sizes.
VARIANT_FALLBACKS = {
    "thumbnail": ("thumbnail", "medium", "large", "full"),
    "medium": ("medium", "full", "large", "thumbnail"),
    "large": ("large", "full", "medium", "thumbnail"),
    "full": ("full", "large", "medium", "thumbnail"),
}


def pick_variants(variants: dict, original_filename: str) -> dict:
    """
    Filename to serve for each display size, from {size: filename}.

    Generated WebP variants are EXIF-stripped; the raw upload still carries
    whatever EXIF/GPS the camera embedded, regardless of share_exif. So the
    raw upload is used only for a legacy row with no variants at all.
    """
    picked = {}
    for size, preferences in VARIANT_FALLBACKS.items():
        available = (variants.get(p) for p in preferences)
        picked[size] = next((name for name in available if name), original_filename)
    return picked


@router.get("/published")
async def get_published_gallery(user_id: int, response: Response):
    """
    Get all published (public) images for a photographer.

    This endpoint is used by the public static sites (adrian.hensler.photography, etc.)
    to dynamically load gallery images. No authentication required.

    Args:
        user_id: The photographer's user ID (1=Adrian, 2=Liam, etc.)

    Returns:
        {
            "images": [
                {
                    "id": int,
                    "filename": str,
                    "slug": str,
                    "title": str,
                    "caption": str,
                    "tags": str,
                    "category": str,
                    "width": int,
                    "height": int,
                    "aspect_ratio": float,
                    "thumbnail_url": str,
                    "webp_url": str,
                    "webp_thumbnail_url": str,
                    "created_at": str
                }
            ],
            "total": int,
            "user_id": int
        }
    """
    from api.database import get_db_connection

    async with get_db_connection() as db:
        cursor = await db.execute(
            """
            SELECT
                i.id, i.filename, i.slug, i.title, i.caption, i.alt_text, i.tags, i.category,
                i.featured, i.width, i.height, i.aspect_ratio, i.share_exif,
                i.camera_make, i.camera_model, i.lens, i.focal_length,
                i.aperture, i.shutter_speed, i.iso, i.date_taken, i.location,
                i.created_at,
                thumb.filename as thumbnail_filename,
                medium.filename as medium_filename,
                large.filename as large_filename,
                i.ai_generated_title, i.ai_generated_caption, i.ai_generated_description,
                i.ai_generated_alt_text, i.ai_generated_tags, i.ai_generated_category,
                fullres.filename as full_filename,
                i.slug_approved
            FROM images i
            LEFT JOIN image_variants thumb ON i.id = thumb.image_id
                AND thumb.format = 'webp' AND thumb.size = 'thumbnail'
            LEFT JOIN image_variants medium ON i.id = medium.image_id
                AND medium.format = 'webp' AND medium.size = 'medium'
            LEFT JOIN image_variants large ON i.id = large.image_id
                AND large.format = 'webp' AND large.size = 'large'
            LEFT JOIN image_variants fullres ON i.id = fullres.image_id
                AND fullres.format = 'webp' AND fullres.size = 'full'
            WHERE i.user_id = ? AND i.published = 1 AND i.deleted_at IS NULL
            ORDER BY i.sort_order ASC, i.created_at DESC
        """,
            (user_id,),
        )

        rows = await cursor.fetchall()

        images = []
        for row in rows:
            # Generated variants only; see pick_variants
            original_filename = row[1]
            picked = pick_variants(
                {"thumbnail": row[23], "medium": row[24], "large": row[25], "full": row[32]},
                original_filename,
            )
            thumbnail_filename = picked["thumbnail"]
            medium_filename = picked["medium"]
            large_filename = picked["large"]
            full_filename = picked["full"]

            # Construct URLs
            thumbnail_url = f"/assets/gallery/{thumbnail_filename}"
            medium_url = f"/assets/gallery/{medium_filename}"
            large_url = f"/assets/gallery/{large_filename}"
            full_url = f"/assets/gallery/{full_filename}"

            # Only include EXIF if share_exif = 1
            exif_data = None
            if row[12]:  # share_exif
                exif_data = {
                    "camera_make": row[13],
                    "camera_model": row[14],
                    "lens": row[15],
                    "focal_length": row[16],
                    "aperture": row[17],
                    "shutter_speed": row[18],
                    "iso": row[19],
                    "date_taken": row[20],
                    "location": row[21],
                }

            # AI disclosure: indicates which fields are AI-generated vs human-reviewed
            # A field is AI-generated if its ai_generated_X value is 1 (or NULL for old data)
            ai_disclosure = {
                "title": bool(row[26]) if row[26] is not None else True,
                "caption": bool(row[27]) if row[27] is not None else True,
                "description": bool(row[28]) if row[28] is not None else True,
                "alt_text": bool(row[29]) if row[29] is not None else True,
                "tags": bool(row[30]) if row[30] is not None else True,
                "category": bool(row[31]) if row[31] is not None else True,
            }

            images.append(
                {
                    "id": row[0],
                    "filename": original_filename,
                    "slug": row[2],
                    "title": row[3],
                    "caption": row[4],
                    "alt_text": row[5],  # Alt text for accessibility
                    "tags": row[6],
                    "category": row[7],
                    "featured": bool(row[8]),  # Featured flag for hero weighting
                    "width": row[9],
                    "height": row[10],
                    "aspect_ratio": row[11],
                    "share_exif": bool(row[12]),
                    "exif": exif_data,
                    # Full-resolution, EXIF-stripped (never the raw upload; see comment above)
                    "image_url": full_url,
                    # Optimized WebP variants (400px, 800px, 1200px)
                    "thumbnail_url": thumbnail_url,  # 400px for grid
                    "medium_url": medium_url,  # 800px for tablets
                    "large_url": large_url,  # 1200px for lightbox
                    "created_at": row[22],
                    # The photo's own page: approved address, else its id
                    "page_path": photo_path(row[0], row[2], row[33]),
                    # AI disclosure for public transparency
                    "ai_disclosure": ai_disclosure,
                }
            )

        # Set cache headers: 5 minutes for CDNs, revalidate on stale
        response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=60"
        return {"images": images, "total": len(images), "user_id": user_id}


@router.get("/published/{slug}")
async def get_published_image(user_id: int, slug: str):
    """
    Get a single published image by slug.

    This could be used for individual image pages in the future.
    No authentication required.

    Args:
        user_id: The photographer's user ID
        slug: The image's URL-friendly slug

    Returns:
        Single image object with full details
    """
    from api.database import get_db_connection

    async with get_db_connection() as db:
        cursor = await db.execute(
            """
            SELECT
                id, filename, slug, title, caption, description, tags, category,
                width, height, aspect_ratio, share_exif,
                camera_make, camera_model, lens, focal_length,
                aperture, shutter_speed, iso, date_taken, location,
                created_at
            FROM images
            WHERE user_id = ? AND slug = ? AND published = 1 AND deleted_at IS NULL
        """,
            (user_id, slug),
        )

        row = await cursor.fetchone()

        if not row:
            raise HTTPException(
                status_code=404,
                detail=f"Published image with slug '{slug}' not found for user {user_id}",
            )

        # Never serve the raw upload while a variant exists; see pick_variants
        variant_cursor = await db.execute(
            "SELECT size, filename FROM image_variants WHERE image_id = ? AND format = 'webp'",
            (row[0],),
        )
        variants = {v_row[0]: v_row[1] for v_row in await variant_cursor.fetchall()}
        picked = pick_variants(variants, row[1])
        thumbnail_filename = picked["thumbnail"]
        full_filename = picked["full"]
        base_url = f"/assets/gallery/{full_filename}"
        thumbnail_url = f"/assets/gallery/{thumbnail_filename}"

        # Only return EXIF if share_exif = 1
        exif_data = None
        if row[11]:  # share_exif
            exif_data = {
                "camera_make": row[12],
                "camera_model": row[13],
                "lens": row[14],
                "focal_length": row[15],
                "aperture": row[16],
                "shutter_speed": row[17],
                "iso": row[18],
                "date_taken": row[19],
                "location": row[20],
            }

        return {
            "id": row[0],
            "filename": row[1],
            "slug": row[2],
            "title": row[3],
            "caption": row[4],
            "description": row[5],
            "tags": row[6],
            "category": row[7],
            "width": row[8],
            "height": row[9],
            "aspect_ratio": row[10],
            "share_exif": bool(row[11]),
            "image_url": base_url,
            "thumbnail_url": thumbnail_url,
            "exif": exif_data,
            "created_at": row[21],
        }

"""
Public gallery API routes - no authentication required.

These endpoints serve published images to the public static sites.
"""

from fastapi import APIRouter, HTTPException
from typing import Optional

router = APIRouter(prefix="/api/gallery", tags=["gallery"])


@router.get("/published")
async def get_published_gallery(user_id: int):
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
        cursor = await db.execute("""
            SELECT
                id, filename, slug, title, caption, tags, category,
                width, height, aspect_ratio, share_exif,
                camera_make, camera_model, lens, focal_length,
                aperture, shutter_speed, iso, date_taken, location,
                created_at
            FROM images
            WHERE user_id = ? AND published = 1
            ORDER BY sort_order ASC, created_at DESC
        """, (user_id,))

        rows = await cursor.fetchall()

        images = []
        for row in rows:
            # Construct image URLs from filename
            base_url = f"/assets/gallery/{row[1]}"

            # Only include EXIF if share_exif = 1
            exif_data = None
            if row[10]:  # share_exif
                exif_data = {
                    "camera_make": row[11],
                    "camera_model": row[12],
                    "lens": row[13],
                    "focal_length": row[14],
                    "aperture": row[15],
                    "shutter_speed": row[16],
                    "iso": row[17],
                    "date_taken": row[18],
                    "location": row[19]
                }

            images.append({
                "id": row[0],
                "filename": row[1],
                "slug": row[2],
                "title": row[3],
                "caption": row[4],
                "tags": row[5],
                "category": row[6],
                "width": row[7],
                "height": row[8],
                "aspect_ratio": row[9],
                "share_exif": bool(row[10]),
                "exif": exif_data,
                "image_url": base_url,
                "thumbnail_url": base_url,  # For now, same as full image
                "created_at": row[20]
            })

        return {
            "images": images,
            "total": len(images),
            "user_id": user_id
        }


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
        cursor = await db.execute("""
            SELECT
                id, filename, slug, title, caption, description, tags, category,
                width, height, aspect_ratio, share_exif,
                camera_make, camera_model, lens, focal_length,
                aperture, shutter_speed, iso, date_taken, location,
                created_at
            FROM images
            WHERE user_id = ? AND slug = ? AND published = 1
        """, (user_id, slug))

        row = await cursor.fetchone()

        if not row:
            raise HTTPException(
                status_code=404,
                detail=f"Published image with slug '{slug}' not found for user {user_id}"
            )

        # Construct image URLs from filename
        base_url = f"/assets/gallery/{row[1]}"

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
                "location": row[20]
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
            "thumbnail_url": base_url,
            "exif": exif_data,
            "created_at": row[21]
        }

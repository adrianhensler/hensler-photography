"""
Photographer Management Routes

These routes allow photographers to manage their own images.
Requires authentication and enforces user_id isolation.

SECURITY: All routes MUST verify that the authenticated user
owns the resource they're trying to modify.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from api.routes.auth import get_current_user
from api.database import get_db_connection

router = APIRouter(prefix="/api/photographer", tags=["photographer"])


async def verify_image_ownership(image_id: int, user_id: int) -> None:
    """
    Verify that the specified image belongs to the authenticated user.

    This is the CRITICAL security check that prevents photographers
    from modifying each other's images.

    Args:
        image_id: The image to check
        user_id: The authenticated user's ID

    Raises:
        HTTPException: 404 if image doesn't exist or doesn't belong to user
    """
    async with get_db_connection() as db:
        cursor = await db.execute(
            "SELECT user_id FROM images WHERE id = ?",
            (image_id,)
        )
        row = await cursor.fetchone()

        if not row:
            raise HTTPException(
                status_code=404,
                detail=f"Image {image_id} not found"
            )

        if row[0] != user_id:
            # Image exists but belongs to another user
            # Return 404 (not 403) to avoid leaking image existence
            raise HTTPException(
                status_code=404,
                detail=f"Image {image_id} not found"
            )


@router.get("/images/{image_id}")
async def get_image(
    image_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Get a single image by ID (photographer's own images only).

    Security: Verifies image belongs to authenticated user.
    """
    user_id = current_user.id

    # Security check: Verify ownership
    await verify_image_ownership(image_id, user_id)

    async with get_db_connection() as db:
        cursor = await db.execute("""
            SELECT
                id, filename, slug, title, caption, tags, category,
                width, height, aspect_ratio, published, share_exif,
                camera_make, camera_model, lens, focal_length,
                aperture, shutter_speed, iso, date_taken, location,
                sort_order, created_at, updated_at
            FROM images
            WHERE id = ? AND user_id = ?
        """, (image_id, user_id))

        row = await cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Image not found")

        return {
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
            "published": bool(row[10]),
            "share_exif": bool(row[11]),
            "exif": {
                "camera_make": row[12],
                "camera_model": row[13],
                "lens": row[14],
                "focal_length": row[15],
                "aperture": row[16],
                "shutter_speed": row[17],
                "iso": row[18],
                "date_taken": row[19],
                "location": row[20],
            },
            "sort_order": row[21],
            "created_at": row[22],
            "updated_at": row[23]
        }


@router.put("/images/{image_id}")
async def update_image(
    image_id: int,
    title: Optional[str] = None,
    caption: Optional[str] = None,
    tags: Optional[str] = None,
    category: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Update image metadata (photographer's own images only).

    Security: CRITICAL - This is the route tested by test_gallery_security.py

    Without the verify_image_ownership() check below, a photographer could
    edit another user's images by simply knowing their image_id.

    This demonstrates TDD: The test will FAIL without this security check.
    """
    user_id = current_user.id

    # ⚠️ CRITICAL SECURITY CHECK ⚠️
    # Without this line, the test will FAIL and photographers can edit each other's images!
    await verify_image_ownership(image_id, user_id)

    # Build update query dynamically based on provided fields
    updates = []
    params = []

    if title is not None:
        updates.append("title = ?")
        params.append(title)
    if caption is not None:
        updates.append("caption = ?")
        params.append(caption)
    if tags is not None:
        updates.append("tags = ?")
        params.append(tags)
    if category is not None:
        updates.append("category = ?")
        params.append(category)

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    updates.append("updated_at = CURRENT_TIMESTAMP")
    params.extend([image_id, user_id])

    async with get_db_connection() as db:
        await db.execute(f"""
            UPDATE images
            SET {', '.join(updates)}
            WHERE id = ? AND user_id = ?
        """, tuple(params))
        await db.commit()

    # Return updated image
    return await get_image(image_id, current_user)


@router.delete("/images/{image_id}")
async def delete_image(
    image_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete an image (photographer's own images only).

    Security: CRITICAL - Prevents photographers from deleting each other's work.
    """
    user_id = current_user.id

    # ⚠️ CRITICAL SECURITY CHECK ⚠️
    await verify_image_ownership(image_id, user_id)

    async with get_db_connection() as db:
        # Delete the image record
        await db.execute(
            "DELETE FROM images WHERE id = ? AND user_id = ?",
            (image_id, user_id)
        )
        await db.commit()

    # TODO: Also delete physical image files from /app/assets/gallery/

    return {"success": True, "message": f"Image {image_id} deleted"}


@router.patch("/images/{image_id}/publish")
async def toggle_publish(
    image_id: int,
    published: bool,
    current_user: dict = Depends(get_current_user)
):
    """
    Publish or unpublish an image (photographer's own images only).

    Security: Prevents photographers from publishing each other's images.
    """
    user_id = current_user.id

    # ⚠️ CRITICAL SECURITY CHECK ⚠️
    await verify_image_ownership(image_id, user_id)

    async with get_db_connection() as db:
        await db.execute("""
            UPDATE images
            SET published = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
        """, (1 if published else 0, image_id, user_id))
        await db.commit()

    status = "published" if published else "unpublished"
    return {"success": True, "message": f"Image {image_id} {status}"}


@router.get("/images")
async def list_images(
    current_user: dict = Depends(get_current_user),
    published: Optional[bool] = None
):
    """
    List all images for the authenticated photographer.

    Security: Only returns images belonging to the authenticated user.
    """
    user_id = current_user.id

    async with get_db_connection() as db:
        query = """
            SELECT
                id, filename, slug, title, caption, published,
                width, height, aspect_ratio, created_at
            FROM images
            WHERE user_id = ?
        """
        params = [user_id]

        if published is not None:
            query += " AND published = ?"
            params.append(1 if published else 0)

        query += " ORDER BY sort_order ASC, created_at DESC"

        cursor = await db.execute(query, tuple(params))
        rows = await cursor.fetchall()

        images = []
        for row in rows:
            images.append({
                "id": row[0],
                "filename": row[1],
                "slug": row[2],
                "title": row[3],
                "caption": row[4],
                "published": bool(row[5]),
                "width": row[6],
                "height": row[7],
                "aspect_ratio": row[8],
                "created_at": row[9]
            })

        return {
            "images": images,
            "total": len(images),
            "user_id": user_id
        }

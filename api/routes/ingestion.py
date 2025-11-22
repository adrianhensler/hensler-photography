"""
Image ingestion routes with AI-powered metadata generation

Enhanced with structured error handling for AI and human users.
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
import os
import shutil
import traceback
from datetime import datetime
from pathlib import Path
import hashlib

from api.errors import (
    ErrorResponse,
    file_too_large_error,
    invalid_file_type_error,
    corrupt_image_error,
    database_error,
    not_found_error
)
from api.logging_config import get_logger
from api.models import ImageMetadataUpdate

# Initialize logger
logger = get_logger(__name__)

router = APIRouter(prefix="/api/images", tags=["images"])


# ROUTE ORDER MATTERS: Specific literal paths MUST come before generic path parameters
# Otherwise FastAPI will match /{image_id} before /ingest


@router.post("/ingest")
async def ingest_image(
    file: UploadFile = File(...),
    user_id: int = Form(...)
):
    """
    Upload and process an image with AI analysis

    Steps:
    1. Validate and save original file
    2. Extract EXIF metadata
    3. Analyze with Claude Vision for captions/tags
    4. Generate WebP variants
    5. Insert into database
    6. Return metadata for preview

    Returns structured response with success status, data, and any warnings.
    """
    context = {
        "original_filename": file.filename,
        "user_id": user_id,
        "content_type": file.content_type
    }

    logger.info(f"Starting image ingestion: {file.filename}", extra={"context": context})

    # Validate file type
    allowed_types = ['image/jpeg', 'image/jpg', 'image/png']
    if file.content_type not in allowed_types:
        logger.warning(f"Invalid file type: {file.content_type}", extra={"context": context})
        error = invalid_file_type_error(
            filename=file.filename,
            file_type=file.content_type,
            allowed_types=allowed_types,
            context=context
        )
        return JSONResponse(
            status_code=error.http_status,
            content=error.to_dict()
        )

    # Validate file size (20MB max)
    contents = await file.read()
    max_size = 20 * 1024 * 1024
    if len(contents) > max_size:
        logger.warning(
            f"File too large: {len(contents)} bytes",
            extra={"context": {**context, "file_size": len(contents), "max_size": max_size}}
        )
        error = file_too_large_error(
            file_size=len(contents),
            max_size=max_size,
            filename=file.filename,
            context=context
        )
        return JSONResponse(
            status_code=error.http_status,
            content=error.to_dict()
        )

    file_path = None
    warnings = []  # Collect non-fatal warnings

    try:
        # Generate unique filename using hash
        file_hash = hashlib.sha256(contents).hexdigest()[:16]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        ext = Path(file.filename).suffix.lower()
        original_filename = f"{timestamp}_{file_hash}{ext}"

        context["generated_filename"] = original_filename

        # Save original file
        upload_dir = Path("/app/assets/gallery")
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = upload_dir / original_filename

        logger.info(f"Saving file to {file_path}", extra={"context": context})

        with open(file_path, "wb") as f:
            f.write(contents)

        # Detect actual image format (don't trust browser's content-type)
        from PIL import Image
        actual_media_type = file.content_type  # fallback
        try:
            with Image.open(file_path) as img:
                actual_format = img.format.lower()  # 'jpeg', 'png', 'gif', 'webp'

                # Map PIL format to MIME type
                format_to_mime = {
                    'jpeg': 'image/jpeg',
                    'png': 'image/png',
                    'gif': 'image/gif',
                    'webp': 'image/webp'
                }
                actual_media_type = format_to_mime.get(actual_format, 'image/jpeg')

                # Update context with detected format
                context['actual_format'] = actual_format
                context['actual_media_type'] = actual_media_type

                # If format doesn't match extension, log as warning (will notify user)
                if actual_media_type != file.content_type:
                    warning_msg = f"Format mismatch: uploaded as {file.content_type}, actual format is {actual_media_type}"
                    logger.warning(warning_msg, extra={"context": context})
                    warnings.append({
                        "code": "FORMAT_MISMATCH",
                        "message": warning_msg,
                        "user_message": f"File format corrected: detected {actual_format.upper()} (browser reported {file.content_type})"
                    })
        except Exception as e:
            logger.warning(f"Could not detect image format, using content-type: {e}", extra={"context": context})

        # Import services dynamically
        from api.services.exif import extract_exif
        from api.services.claude_vision import analyze_image
        from api.services.image_processor import generate_variants
        from api.database import get_db_connection
        from slugify import slugify

        # Step 1: Extract EXIF data (never fails, always returns something)
        logger.info("Extracting EXIF metadata", extra={"context": context})
        exif_data = extract_exif(str(file_path))

        # Step 2: Analyze image with Claude Vision (may fail gracefully)
        logger.info("Analyzing image with Claude Vision", extra={"context": context})
        ai_metadata, ai_error = await analyze_image(
            str(file_path),
            user_id=user_id,
            filename=original_filename,
            media_type=actual_media_type  # Use detected format, not browser's claim
        )

        if ai_error:
            # AI analysis failed, but we continue with fallback
            warnings.append(ai_error.to_dict()["error"])
            logger.warning(
                f"AI analysis failed: {ai_error.message}",
                extra={"context": context, "error_code": ai_error.code.value}
            )

        # Step 3: Generate WebP variants (may fail, but we continue)
        logger.info("Generating WebP variants", extra={"context": context})
        variants, variant_error = generate_variants(
            str(file_path),
            original_filename,
            context={**context, "user_id": user_id}
        )

        if variant_error:
            # Variant generation failed - this is more serious but still salvageable
            warnings.append(variant_error.to_dict()["error"])
            logger.error(
                f"Variant generation failed: {variant_error.message}",
                extra={"context": context, "error_code": variant_error.code.value}
            )
            # Continue without variants

        # Step 4: Insert into database
        logger.info("Inserting into database", extra={"context": context})

        # Generate slug from title or filename
        slug_base = slugify(ai_metadata.get('title', Path(file.filename).stem))

        try:
                async with get_db_connection() as db:
                    # Check if slug exists, make it unique
                    cursor = await db.execute(
                        "SELECT COUNT(*) FROM images WHERE user_id = ? AND slug LIKE ?",
                        (user_id, f"{slug_base}%")
                    )
                    count = (await cursor.fetchone())[0]
                    slug = f"{slug_base}-{count + 1}" if count > 0 else slug_base

                    # Insert main image record
                    cursor = await db.execute("""
                        INSERT INTO images (
                            user_id, filename, slug, original_filename,
                            title, caption, description, tags, category,
                            camera_make, camera_model, lens,
                            focal_length, aperture, shutter_speed, iso,
                            date_taken, location,
                            width, height, aspect_ratio, file_size,
                            published, featured, available_for_sale
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        user_id,
                        original_filename,
                        slug,
                        file.filename,
                        ai_metadata.get('title', ''),
                        ai_metadata.get('caption', ''),
                        ai_metadata.get('description', ''),
                        ','.join(ai_metadata.get('tags', [])) if isinstance(ai_metadata.get('tags'), list) else ai_metadata.get('tags', ''),
                        ai_metadata.get('category', ''),
                        exif_data.get('camera_make', ''),
                        exif_data.get('camera_model', ''),
                        exif_data.get('lens', ''),
                        exif_data.get('focal_length', ''),
                        exif_data.get('aperture', ''),
                        exif_data.get('shutter_speed', ''),
                        exif_data.get('iso'),
                        exif_data.get('date_taken', ''),
                        exif_data.get('location', ''),
                        exif_data.get('width'),
                        exif_data.get('height'),
                        exif_data.get('aspect_ratio'),
                        len(contents),
                        0,  # Not published by default
                        0,  # Not featured
                        0   # Not for sale yet
                    ))

                    image_id = cursor.lastrowid

                    # Insert variant records
                    for variant in variants:
                        await db.execute("""
                            INSERT INTO image_variants (
                                image_id, format, size, filename, width, height, file_size
                            ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (
                            image_id,
                            variant['format'],
                            variant['size'],
                            variant['filename'],
                            variant['width'],
                            variant['height'],
                            variant['file_size']
                        ))

                    await db.commit()

                    logger.info(
                        f"Successfully ingested image ID {image_id}",
                        extra={"context": {**context, "image_id": image_id, "slug": slug}}
                    )

        except Exception as db_error:
            logger.error(
                f"Database insertion failed: {db_error}",
                exc_info=db_error,
                extra={"context": context, "error_code": "DATABASE_CONNECTION_FAILED"}
            )

            # Clean up file on database failure
            if file_path and file_path.exists():
                file_path.unlink()

            error = database_error(
                operation="image_insertion",
                error_message=str(db_error),
                context=context,
                stack_trace=traceback.format_exc()
            )
            return JSONResponse(
                status_code=error.http_status,
                content=error.to_dict()
            )

        # Format EXIF for display - include all fields for UI
        exif_display = {
            # Combined legacy fields for backward compatibility
            'camera': f"{exif_data.get('camera_make', '')} {exif_data.get('camera_model', '')}".strip() or None,
            'lens': exif_data.get('lens') or None,
            'focal_length': exif_data.get('focal_length') or None,
            'aperture': exif_data.get('aperture') or None,
            'shutter_speed': exif_data.get('shutter_speed') or None,
            'iso': exif_data.get('iso') or None,
            'date_taken': exif_data.get('date_taken') or None,
            'location': exif_data.get('location') or None,
            'aspect_ratio': exif_data.get('aspect_ratio') or None
        }

        # Build successful response with warnings
        response_data = {
            "success": True,
            "image_id": image_id,
            "slug": slug,
            "filename": original_filename,
            "title": ai_metadata.get('title', ''),
            "caption": ai_metadata.get('caption', ''),
            "description": ai_metadata.get('description', ''),
            "tags": ai_metadata.get('tags', ''),
            "category": ai_metadata.get('category', ''),
            "width": exif_data.get('width'),
            "height": exif_data.get('height'),
            "exif": exif_display,
            "variants_generated": len(variants)
        }

        # Include warnings if any occurred
        if warnings:
            response_data["warnings"] = warnings
            logger.info(
                f"Image ingested with {len(warnings)} warning(s)",
                extra={"context": {**context, "warning_count": len(warnings)}}
            )

        return JSONResponse(response_data)

    except Exception as e:
        # Unexpected error during file save or processing
        logger.error(
            f"Unexpected error during ingestion: {e}",
            exc_info=e,
            extra={"context": context, "error_code": "INTERNAL_ERROR"}
        )

        # Clean up file if processing failed
        if file_path and file_path.exists():
            file_path.unlink()

        from api.errors import internal_error
        error = internal_error(
            error_message=str(e),
            context=context,
            stack_trace=traceback.format_exc()
        )
        return JSONResponse(
            status_code=error.http_status,
            content=error.to_dict()
        )


@router.get("/list")
async def list_images(
    user_id: int = None,
    published: bool = None,
    featured: bool = None,
    category: str = None,
    search: str = None,
    limit: int = 100,
    offset: int = 0,
    with_analytics: bool = False
):
    """
    List all images with optional filters

    Query parameters:
    - user_id: Filter by photographer
    - published: Filter by published status (true/false)
    - featured: Filter by featured status (true/false)
    - category: Filter by category
    - search: Search in title, caption, description, tags
    - limit: Max results to return (default 100)
    - offset: Pagination offset (default 0)
    - with_analytics: Include engagement analytics for each image (default false)
    """
    from api.database import get_db_connection

    async with get_db_connection() as db:
        # Build query dynamically
        query = """
            SELECT id, user_id, filename, slug, title, caption, tags, category,
                   published, featured, share_exif, width, height, created_at, updated_at
            FROM images
            WHERE 1=1
        """
        params = []

        if user_id is not None:
            query += " AND user_id = ?"
            params.append(user_id)

        if published is not None:
            query += " AND published = ?"
            params.append(1 if published else 0)

        if featured is not None:
            query += " AND featured = ?"
            params.append(1 if featured else 0)

        if category:
            query += " AND category = ?"
            params.append(category)

        if search:
            query += " AND (title LIKE ? OR caption LIKE ? OR description LIKE ? OR tags LIKE ?)"
            search_term = f"%{search}%"
            params.extend([search_term, search_term, search_term, search_term])

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor = await db.execute(query, tuple(params))
        rows = await cursor.fetchall()

        # Get total count
        count_query = """
            SELECT COUNT(*) FROM images WHERE 1=1
        """
        count_params = params[:-2]  # Remove limit and offset

        if user_id is not None:
            count_query += " AND user_id = ?"
        if published is not None:
            count_query += " AND published = ?"
        if featured is not None:
            count_query += " AND featured = ?"
        if category:
            count_query += " AND category = ?"
        if search:
            count_query += " AND (title LIKE ? OR caption LIKE ? OR description LIKE ? OR tags LIKE ?)"

        cursor = await db.execute(count_query, tuple(count_params))
        total = (await cursor.fetchone())[0]

        images = []
        for row in rows:
            image = {
                "id": row[0],
                "user_id": row[1],
                "filename": row[2],
                "slug": row[3],
                "title": row[4],
                "caption": row[5],
                "tags": row[6],
                "category": row[7],
                "published": bool(row[8]),
                "featured": bool(row[9]),
                "share_exif": bool(row[10]),
                "width": row[11],
                "height": row[12],
                "created_at": row[13],
                "updated_at": row[14],
                "thumbnail_url": f"/assets/gallery/{Path(row[2]).stem}_thumbnail.webp"
            }

            # Include analytics if requested
            if with_analytics:
                analytics_cursor = await db.execute("""
                    SELECT
                        COUNT(CASE WHEN event_type = 'image_impression' THEN 1 END) as impressions,
                        COUNT(CASE WHEN event_type = 'gallery_click' THEN 1 END) as clicks,
                        COUNT(CASE WHEN event_type = 'lightbox_open' THEN 1 END) as lightbox_opens
                    FROM image_events
                    WHERE image_id = ?
                """, (row[0],))

                analytics_row = await analytics_cursor.fetchone()
                impressions = analytics_row[0] or 0
                clicks = analytics_row[1] or 0
                click_rate = (clicks / impressions) if impressions > 0 else 0

                # Calculate engagement level (compared to user's average)
                # This will be calculated later with full portfolio context
                engagement_level = "medium"  # Default

                lightbox_opens = analytics_row[2] or 0

                image["analytics"] = {
                    "impressions": impressions,
                    "clicks": clicks,
                    "lightbox_opens": lightbox_opens,
                    "views": lightbox_opens,
                    "click_rate": round(click_rate, 3),
                    "engagement_level": engagement_level
                }

            images.append(image)

        # Calculate engagement levels if analytics requested
        if with_analytics and images:
            # Calculate average views across all images
            total_impressions = sum(img["analytics"]["impressions"] for img in images)
            avg_impressions = total_impressions / len(images) if len(images) > 0 else 0

            # Assign engagement levels
            for img in images:
                impressions = img["analytics"]["impressions"]
                if avg_impressions > 0:
                    if impressions >= avg_impressions * 1.5:
                        img["analytics"]["engagement_level"] = "high"
                    elif impressions >= avg_impressions * 0.75:
                        img["analytics"]["engagement_level"] = "medium"
                    else:
                        img["analytics"]["engagement_level"] = "low"
                else:
                    img["analytics"]["engagement_level"] = "low"

        return {
            "images": images,
            "total": total,
            "limit": limit,
            "offset": offset
        }


@router.post("/{image_id}/publish")
async def set_visibility(image_id: int, published: bool = True):
    """
    Set image visibility: published=True (public), published=False (private).
    Public images appear on user.hensler.photography, private remain in management interface only.
    """
    from api.database import get_db_connection

    async with get_db_connection() as db:
        await db.execute(
            "UPDATE images SET published = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (1 if published else 0, image_id)
        )
        await db.commit()

    return {"success": True, "image_id": image_id, "published": published}


@router.post("/{image_id}/exif-sharing")
async def set_exif_sharing(image_id: int, share: bool = True):
    """
    Toggle EXIF data sharing for public gallery.

    When share=False:
    - EXIF data not returned in public API
    - Photographer still sees EXIF in management interface

    Privacy considerations:
    - Location data can be hidden
    - Camera/lens info can be hidden
    - Exposure settings can be hidden
    """
    from api.database import get_db_connection

    async with get_db_connection() as db:
        await db.execute(
            "UPDATE images SET share_exif = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (1 if share else 0, image_id)
        )
        await db.commit()

    return {"success": True, "image_id": image_id, "share_exif": share}


@router.post("/{image_id}/featured")
async def toggle_featured(image_id: int, featured: bool = True):
    """Toggle featured status of an image"""
    from api.database import get_db_connection

    async with get_db_connection() as db:
        await db.execute(
            "UPDATE images SET featured = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (1 if featured else 0, image_id)
        )
        await db.commit()

    return {"success": True, "image_id": image_id, "featured": featured}


# Generic path parameter routes come AFTER specific literal paths
@router.get("/{image_id}")
async def get_image(image_id: int):
    """Get image details"""
    from api.database import get_db_connection

    async with get_db_connection() as db:
        cursor = await db.execute("""
            SELECT id, user_id, filename, slug, title, caption, description,
                   tags, category, published, featured, available_for_sale, share_exif,
                   camera_make, camera_model, lens, focal_length, aperture,
                   shutter_speed, iso, date_taken, location,
                   width, height, aspect_ratio, created_at, updated_at
            FROM images WHERE id = ?
        """, (image_id,))

        row = await cursor.fetchone()

        if not row:
            raise HTTPException(404, "Image not found")

        # Get variants
        cursor = await db.execute("""
            SELECT format, size, filename, width, height, file_size
            FROM image_variants WHERE image_id = ?
        """, (image_id,))

        variants = await cursor.fetchall()

    return {
        "id": row[0],
        "user_id": row[1],
        "filename": row[2],
        "slug": row[3],
        "title": row[4],
        "caption": row[5],
        "description": row[6],
        "tags": row[7],
        "category": row[8],
        "published": bool(row[9]),
        "featured": bool(row[10]),
        "available_for_sale": bool(row[11]),
        "share_exif": bool(row[12]),
        "exif": {
            "camera_make": row[13],
            "camera_model": row[14],
            "lens": row[15],
            "focal_length": row[16],
            "aperture": row[17],
            "shutter_speed": row[18],
            "iso": row[19],
            "date_taken": row[20],
            "location": row[21]
        },
        "dimensions": {
            "width": row[22],
            "height": row[23],
            "aspect_ratio": row[24]
        },
        "created_at": row[25],
        "updated_at": row[26],
        "variants": [
            {
                "format": v[0],
                "size": v[1],
                "filename": v[2],
                "width": v[3],
                "height": v[4],
                "file_size": v[5]
            } for v in variants
        ]
    }


@router.patch("/{image_id}")
async def update_image_metadata(image_id: int, metadata: ImageMetadataUpdate):
    """
    Update image metadata (title, caption, tags, etc.)

    Uses Pydantic ImageMetadataUpdate model for validation.
    """
    from api.database import get_db_connection

    async with get_db_connection() as db:
        # Build update query dynamically based on provided fields
        # Convert Pydantic model to dict, excluding None values
        metadata_dict = metadata.dict(exclude_none=True)

        if not metadata_dict:
            raise HTTPException(400, "No valid fields to update")

        updates = []
        values = []

        for field, value in metadata_dict.items():
            updates.append(f"{field} = ?")
            values.append(value)

        values.append(image_id)

        query = f"UPDATE images SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        await db.execute(query, tuple(values))
        await db.commit()

    logger.info(
        f"Image metadata updated: {image_id}",
        extra={"context": {"image_id": image_id, "updated_fields": list(metadata_dict.keys())}}
    )

    return {"success": True, "image_id": image_id, "updated_fields": list(metadata_dict.keys())}


@router.delete("/{image_id}")
async def delete_image(image_id: int):
    """Delete an image and its variants"""
    from api.database import get_db_connection
    from pathlib import Path

    async with get_db_connection() as db:
        # Get image filename
        cursor = await db.execute("SELECT filename FROM images WHERE id = ?", (image_id,))
        row = await cursor.fetchone()

        if not row:
            raise HTTPException(404, "Image not found")

        filename = row[0]

        # Get variant filenames
        cursor = await db.execute("SELECT filename FROM image_variants WHERE image_id = ?", (image_id,))
        variants = await cursor.fetchall()

        # Delete from database (variants will cascade)
        await db.execute("DELETE FROM images WHERE id = ?", (image_id,))
        await db.commit()

    # Delete files
    upload_dir = Path("/app/assets/gallery")

    # Delete original
    original_path = upload_dir / filename
    if original_path.exists():
        original_path.unlink()

    # Delete variants
    for variant_row in variants:
        variant_path = upload_dir / variant_row[0]
        if variant_path.exists():
            variant_path.unlink()

    return {"success": True, "image_id": image_id, "deleted": True}


@router.get("/{image_id}")
async def get_image(image_id: int):
    """Get image details"""
    from api.database import get_db_connection

    async with get_db_connection() as db:
        cursor = await db.execute("""
            SELECT id, user_id, filename, slug, title, caption, description,
                   tags, category, published, featured, available_for_sale, share_exif,
                   camera_make, camera_model, lens, focal_length, aperture,
                   shutter_speed, iso, date_taken, location,
                   width, height, aspect_ratio, created_at, updated_at
            FROM images WHERE id = ?
        """, (image_id,))

        row = await cursor.fetchone()

        if not row:
            raise HTTPException(404, "Image not found")

        # Get variants
        cursor = await db.execute("""
            SELECT format, size, filename, width, height, file_size
            FROM image_variants WHERE image_id = ?
        """, (image_id,))

        variants = await cursor.fetchall()

    return {
        "id": row[0],
        "user_id": row[1],
        "filename": row[2],
        "slug": row[3],
        "title": row[4],
        "caption": row[5],
        "description": row[6],
        "tags": row[7],
        "category": row[8],
        "published": bool(row[9]),
        "featured": bool(row[10]),
        "available_for_sale": bool(row[11]),
        "share_exif": bool(row[12]),
        "exif": {
            "camera_make": row[13],
            "camera_model": row[14],
            "lens": row[15],
            "focal_length": row[16],
            "aperture": row[17],
            "shutter_speed": row[18],
            "iso": row[19],
            "date_taken": row[20],
            "location": row[21]
        },
        "dimensions": {
            "width": row[22],
            "height": row[23],
            "aspect_ratio": row[24]
        },
        "created_at": row[25],
        "updated_at": row[26],
        "variants": [
            {
                "format": v[0],
                "size": v[1],
                "filename": v[2],
                "width": v[3],
                "height": v[4],
                "file_size": v[5]
            } for v in variants
        ]
    }


@router.patch("/{image_id}")
async def update_image_metadata(
    image_id: int,
    metadata: ImageMetadataUpdate
):
    """
    Update image metadata (title, caption, tags, EXIF fields, etc.)
    
    Note: This updates database only, does NOT modify the original image file.
    """
    from api.database import get_db_connection
    
    context = {"image_id": image_id}
    logger.info(f"Updating metadata for image {image_id}", extra={"context": context})
    
    try:
        async with get_db_connection() as db:
            # Build UPDATE query dynamically based on provided fields
            updates = []
            values = []
            
            if metadata.title is not None:
                updates.append("title = ?")
                values.append(metadata.title)
            if metadata.caption is not None:
                updates.append("caption = ?")
                values.append(metadata.caption)
            if metadata.description is not None:
                updates.append("description = ?")
                values.append(metadata.description)
            if metadata.tags is not None:
                updates.append("tags = ?")
                values.append(metadata.tags)
            if metadata.category is not None:
                updates.append("category = ?")
                values.append(metadata.category)
            
            # Technical metadata (editable)
            if metadata.aperture is not None:
                updates.append("aperture = ?")
                values.append(metadata.aperture)
            if metadata.shutter_speed is not None:
                updates.append("shutter_speed = ?")
                values.append(metadata.shutter_speed)
            if metadata.iso is not None:
                updates.append("iso = ?")
                values.append(metadata.iso)
            if metadata.camera is not None:
                # Split camera into make/model if possible
                camera_parts = metadata.camera.split(maxsplit=1)
                if len(camera_parts) == 2:
                    updates.append("camera_make = ?, camera_model = ?")
                    values.extend(camera_parts)
                else:
                    updates.append("camera_model = ?")
                    values.append(metadata.camera)
            if metadata.lens is not None:
                updates.append("lens = ?")
                values.append(metadata.lens)
            if metadata.focal_length is not None:
                updates.append("focal_length = ?")
                values.append(metadata.focal_length)
            if metadata.location is not None:
                updates.append("location = ?")
                values.append(metadata.location if metadata.location.strip() else None)  # Allow clearing
            if metadata.date_taken is not None:
                updates.append("date_taken = ?")
                values.append(metadata.date_taken)
            
            if not updates:
                return {"success": True, "message": "No fields to update"}
            
            # Add updated_at timestamp
            updates.append("updated_at = CURRENT_TIMESTAMP")
            
            # Add image_id for WHERE clause
            values.append(image_id)
            
            query = f"UPDATE images SET {', '.join(updates)} WHERE id = ?"
            
            cursor = await db.execute(query, values)
            await db.commit()
            
            if cursor.rowcount == 0:
                logger.warning(f"Image {image_id} not found for update", extra={"context": context})
                error = not_found_error(
                    resource_type="image",
                    resource_id=image_id,
                    context=context
                )
                return JSONResponse(
                    status_code=error.http_status,
                    content=error.to_dict()
                )
            
            logger.info(f"Successfully updated {cursor.rowcount} image(s)", extra={"context": context})
            
            return {
                "success": True,
                "image_id": image_id,
                "updated_fields": len(updates) - 1  # Exclude updated_at from count
            }
            
    except Exception as e:
        logger.error(f"Failed to update image metadata: {e}", extra={"context": context}, exc_info=True)
        error = database_error(
            operation="update_image_metadata",
            error_message=str(e),
            context=context,
            stack_trace=traceback.format_exc()
        )
        return JSONResponse(
            status_code=error.http_status,
            content=error.to_dict()
        )


@router.post("/{image_id}/reextract-exif")
async def reextract_exif(image_id: int):
    """
    Re-extract EXIF data from the original image file.
    Useful if original data was missing or corrupted.
    """
    from api.database import get_db_connection
    from api.services.exif import extract_exif
    
    context = {"image_id": image_id}
    logger.info(f"Re-extracting EXIF for image {image_id}", extra={"context": context})
    
    try:
        async with get_db_connection() as db:
            # Get image filename
            cursor = await db.execute("SELECT filename FROM images WHERE id = ?", (image_id,))
            row = await cursor.fetchone()
            
            if not row:
                error = not_found_error(resource_type="image", resource_id=image_id, context=context)
                return JSONResponse(status_code=error.http_status, content=error.to_dict())
            
            filename = row[0]
            file_path = f"/app/assets/gallery/{filename}"
            
            # Re-extract EXIF
            exif_data = extract_exif(file_path)
            
            # Update database
            await db.execute("""
                UPDATE images SET
                    camera_make = ?,
                    camera_model = ?,
                    lens = ?,
                    focal_length = ?,
                    aperture = ?,
                    shutter_speed = ?,
                    iso = ?,
                    date_taken = ?,
                    location = ?,
                    width = ?,
                    height = ?,
                    aspect_ratio = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                exif_data.get('camera_make'),
                exif_data.get('camera_model'),
                exif_data.get('lens'),
                exif_data.get('focal_length'),
                exif_data.get('aperture'),
                exif_data.get('shutter_speed'),
                exif_data.get('iso'),
                exif_data.get('date_taken'),
                exif_data.get('location'),
                exif_data.get('width'),
                exif_data.get('height'),
                exif_data.get('aspect_ratio'),
                image_id
            ))
            await db.commit()
            
            logger.info(f"EXIF re-extracted for image {image_id}", extra={"context": context})
            
            # Return updated EXIF data
            return {
                "success": True,
                "image_id": image_id,
                "exif": {
                    'camera': f"{exif_data.get('camera_make', '')} {exif_data.get('camera_model', '')}".strip() or None,
                    'lens': exif_data.get('lens'),
                    'focal_length': exif_data.get('focal_length'),
                    'aperture': exif_data.get('aperture'),
                    'shutter_speed': exif_data.get('shutter_speed'),
                    'iso': exif_data.get('iso'),
                    'date_taken': exif_data.get('date_taken'),
                    'location': exif_data.get('location'),
                    'aspect_ratio': exif_data.get('aspect_ratio')
                },
                "width": exif_data.get('width'),
                "height": exif_data.get('height')
            }
            
    except Exception as e:
        logger.error(f"Failed to re-extract EXIF: {e}", extra={"context": context}, exc_info=True)
        error = database_error(
            operation="reextract_exif",
            error_message=str(e),
            context=context,
            stack_trace=traceback.format_exc()
        )
        return JSONResponse(status_code=error.http_status, content=error.to_dict())


@router.post("/{image_id}/regenerate-ai")
async def regenerate_ai_metadata(image_id: int, user_id: int = Form(...)):
    """
    Re-run Claude Vision analysis on an existing image.
    Generates new title, caption, tags, category.
    
    Cost: ~$0.02 per image
    """
    from api.database import get_db_connection
    from api.services.claude_vision import analyze_image
    
    context = {"image_id": image_id, "user_id": user_id}
    logger.info(f"Regenerating AI metadata for image {image_id}", extra={"context": context})
    
    try:
        async with get_db_connection() as db:
            # Get image filename
            cursor = await db.execute("SELECT filename FROM images WHERE id = ?", (image_id,))
            row = await cursor.fetchone()
            
            if not row:
                error = not_found_error(resource_type="image", resource_id=image_id, context=context)
                return JSONResponse(status_code=error.http_status, content=error.to_dict())
            
            filename = row[0]
            file_path = f"/app/assets/gallery/{filename}"
            
            # Re-run AI analysis
            ai_metadata, ai_error = await analyze_image(
                file_path,
                user_id=user_id,
                filename=filename
            )
            
            if ai_error:
                logger.warning(f"AI regeneration failed: {ai_error}", extra={"context": context})
                return JSONResponse(status_code=ai_error.http_status, content=ai_error.to_dict())
            
            # Update database with new AI metadata (preserving manual edits to EXIF)
            await db.execute("""
                UPDATE images SET
                    title = ?,
                    caption = ?,
                    description = ?,
                    tags = ?,
                    category = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                ai_metadata.get('title'),
                ai_metadata.get('caption'),
                ai_metadata.get('description'),
                ','.join(ai_metadata.get('tags', [])) if isinstance(ai_metadata.get('tags'), list) else ai_metadata.get('tags'),
                ai_metadata.get('category'),
                image_id
            ))
            await db.commit()
            
            logger.info(f"AI metadata regenerated for image {image_id}", extra={"context": context})
            
            return {
                "success": True,
                "image_id": image_id,
                "title": ai_metadata.get('title'),
                "caption": ai_metadata.get('caption'),
                "description": ai_metadata.get('description'),
                "tags": ai_metadata.get('tags'),
                "category": ai_metadata.get('category')
            }
            
    except Exception as e:
        logger.error(f"Failed to regenerate AI metadata: {e}", extra={"context": context}, exc_info=True)
        error = database_error(
            operation="regenerate_ai",
            error_message=str(e),
            context=context,
            stack_trace=traceback.format_exc()
        )
        return JSONResponse(status_code=error.http_status, content=error.to_dict())

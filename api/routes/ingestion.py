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
            filename=original_filename
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

        # Format EXIF for display
        exif_display = {
            'camera': f"{exif_data.get('camera_make', '')} {exif_data.get('camera_model', '')}".strip() or 'Unknown',
            'settings': f"{exif_data.get('focal_length', '')} {exif_data.get('aperture', '')} {exif_data.get('shutter_speed', '')} ISO {exif_data.get('iso', '')}".strip() or 'N/A'
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
    offset: int = 0
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
    """
    from api.database import get_db_connection

    async with get_db_connection() as db:
        # Build query dynamically
        query = """
            SELECT id, user_id, filename, slug, title, caption, tags, category,
                   published, featured, width, height, created_at, updated_at
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
            images.append({
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
                "width": row[10],
                "height": row[11],
                "created_at": row[12],
                "updated_at": row[13],
                "thumbnail_url": f"/assets/gallery/{Path(row[2]).stem}_thumbnail.webp"
            })

        return {
            "images": images,
            "total": total,
            "limit": limit,
            "offset": offset
        }


@router.post("/{image_id}/publish")
async def publish_image(image_id: int):
    """Mark an image as published"""
    from api.database import get_db_connection

    async with get_db_connection() as db:
        await db.execute(
            "UPDATE images SET published = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (image_id,)
        )
        await db.commit()

    return {"success": True, "image_id": image_id, "published": True}


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
                   tags, category, published, featured, available_for_sale,
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
        "exif": {
            "camera_make": row[12],
            "camera_model": row[13],
            "lens": row[14],
            "focal_length": row[15],
            "aperture": row[16],
            "shutter_speed": row[17],
            "iso": row[18],
            "date_taken": row[19],
            "location": row[20]
        },
        "dimensions": {
            "width": row[21],
            "height": row[22],
            "aspect_ratio": row[23]
        },
        "created_at": row[24],
        "updated_at": row[25],
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
async def update_image_metadata(image_id: int, metadata: dict):
    """Update image metadata (title, caption, tags, etc.)"""
    from api.database import get_db_connection

    async with get_db_connection() as db:
        # Build update query dynamically based on provided fields
        allowed_fields = ['title', 'caption', 'description', 'tags', 'category']
        updates = []
        values = []

        for field in allowed_fields:
            if field in metadata:
                updates.append(f"{field} = ?")
                values.append(metadata[field])

        if not updates:
            raise HTTPException(400, "No valid fields to update")

        values.append(image_id)

        query = f"UPDATE images SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        await db.execute(query, tuple(values))
        await db.commit()

    return {"success": True, "image_id": image_id}


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
                   tags, category, published, featured, available_for_sale,
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
        "exif": {
            "camera_make": row[12],
            "camera_model": row[13],
            "lens": row[14],
            "focal_length": row[15],
            "aperture": row[16],
            "shutter_speed": row[17],
            "iso": row[18],
            "date_taken": row[19],
            "location": row[20]
        },
        "dimensions": {
            "width": row[21],
            "height": row[22],
            "aspect_ratio": row[23]
        },
        "created_at": row[24],
        "updated_at": row[25],
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

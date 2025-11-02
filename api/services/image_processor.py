"""
Image processing: Generate WebP variants at multiple sizes

Enhanced with structured error handling and logging.
"""
from PIL import Image
from pathlib import Path
import traceback
from typing import List, Dict, Any, Tuple

from api.errors import ErrorResponse, image_processing_error
from api.logging_config import get_logger

# Initialize logger
logger = get_logger(__name__)


def generate_variants(original_path: str, original_filename: str, context: Dict[str, Any] = None) -> Tuple[List[Dict], ErrorResponse | None]:
    """
    Generate WebP variants at multiple sizes.

    Sizes:
    - 1200w: Large (gallery detail view)
    - 800w: Medium (grid view)
    - 400w: Thumbnail (preview)

    Returns:
        Tuple of (variants_list, error_response)
        - If successful: (variants, None)
        - If error: ([], ErrorResponse)
    """
    context = context or {}
    context.update({
        "original_path": original_path,
        "original_filename": original_filename
    })

    variants = []
    sizes = {
        "large": 1200,
        "medium": 800,
        "thumbnail": 400
    }

    try:
        logger.info(
            f"Generating image variants for {original_filename}",
            extra={"context": context}
        )

        img = Image.open(original_path)

        # Convert RGBA to RGB if needed (for JPEG compatibility)
        if img.mode in ('RGBA', 'LA', 'P'):
            logger.info(
                f"Converting image mode from {img.mode} to RGB",
                extra={"context": context}
            )
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background

        original_width, original_height = img.size
        aspect_ratio = original_width / original_height

        logger.info(
            f"Original image dimensions: {original_width}x{original_height}",
            extra={"context": {**context, "width": original_width, "height": original_height}}
        )

        base_name = Path(original_filename).stem
        output_dir = Path(original_path).parent

        for size_name, target_width in sizes.items():
            try:
                # Don't upscale (except thumbnails - always generate those)
                if original_width <= target_width and size_name != "thumbnail":
                    logger.info(
                        f"Skipping {size_name} variant (original is smaller than target)",
                        extra={"context": {**context, "size_name": size_name, "target_width": target_width}}
                    )
                    continue

                # Calculate new dimensions
                new_width = min(target_width, original_width)
                new_height = int(new_width / aspect_ratio)

                # Resize image
                resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

                # Save as WebP
                variant_filename = f"{base_name}_{size_name}.webp"
                variant_path = output_dir / variant_filename

                resized.save(
                    variant_path,
                    format="WEBP",
                    quality=85,
                    method=6  # Best compression
                )

                # Get file size
                file_size = variant_path.stat().st_size

                variant_info = {
                    "format": "webp",
                    "size": size_name,
                    "filename": variant_filename,
                    "width": new_width,
                    "height": new_height,
                    "file_size": file_size
                }

                variants.append(variant_info)

                logger.info(
                    f"Generated {size_name} variant: {variant_filename} ({file_size} bytes)",
                    extra={"context": {**context, "variant": variant_info}}
                )

            except Exception as e:
                # Log but don't fail - other variants might still work
                logger.warning(
                    f"Failed to generate {size_name} variant: {e}",
                    exc_info=e,
                    extra={"context": {**context, "size_name": size_name}}
                )
                # Continue with other variants

        if not variants:
            # If no variants were generated, that's a problem
            error_msg = "No variants were successfully generated"
            logger.error(
                error_msg,
                extra={"context": context, "error_code": "PROCESSING_VARIANT_FAILED"}
            )

            error = image_processing_error(
                filename=original_filename,
                step="variant_generation",
                error_message=error_msg,
                context=context
            )
            return [], error

        logger.info(
            f"Successfully generated {len(variants)} variants",
            extra={"context": {**context, "variant_count": len(variants)}}
        )

        return variants, None  # Success!

    except FileNotFoundError as e:
        logger.error(
            f"Image file not found: {original_path}",
            exc_info=e,
            extra={"context": context, "error_code": "VALIDATION_CORRUPT_IMAGE"}
        )

        error = image_processing_error(
            filename=original_filename,
            step="file_open",
            error_message=f"Image file not found: {original_path}",
            context=context,
            stack_trace=traceback.format_exc()
        )
        return [], error

    except OSError as e:
        # PIL raises OSError for corrupt images
        logger.error(
            f"Failed to open image (possibly corrupt): {e}",
            exc_info=e,
            extra={"context": context, "error_code": "VALIDATION_CORRUPT_IMAGE"}
        )

        error = image_processing_error(
            filename=original_filename,
            step="file_open",
            error_message=f"Image file is corrupt or unreadable: {str(e)}",
            context=context,
            stack_trace=traceback.format_exc()
        )
        return [], error

    except Exception as e:
        logger.error(
            f"Unexpected error during image processing: {e}",
            exc_info=e,
            extra={"context": context, "error_code": "PROCESSING_IMAGE_FAILED"}
        )

        error = image_processing_error(
            filename=original_filename,
            step="variant_generation",
            error_message=str(e),
            context=context,
            stack_trace=traceback.format_exc()
        )
        return [], error

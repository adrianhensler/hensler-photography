"""
Image processing: Generate WebP variants at multiple sizes
"""
from PIL import Image
from pathlib import Path


def generate_variants(original_path: str, original_filename: str) -> list:
    """
    Generate WebP variants at multiple sizes

    Sizes:
    - 1200w: Large (gallery detail view)
    - 800w: Medium (grid view)
    - 400w: Thumbnail (preview)

    Returns list of variant metadata
    """

    variants = []
    sizes = {
        "large": 1200,
        "medium": 800,
        "thumbnail": 400
    }

    try:
        img = Image.open(original_path)

        # Convert RGBA to RGB if needed (for JPEG compatibility)
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background

        original_width, original_height = img.size
        aspect_ratio = original_width / original_height

        base_name = Path(original_filename).stem
        output_dir = Path(original_path).parent

        for size_name, target_width in sizes.items():
            # Don't upscale
            if original_width <= target_width and size_name != "thumbnail":
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

            variants.append({
                "format": "webp",
                "size": size_name,
                "filename": variant_filename,
                "width": new_width,
                "height": new_height,
                "file_size": file_size
            })

        return variants

    except Exception as e:
        print(f"Image processing error: {e}")
        return []

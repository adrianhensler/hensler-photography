#!/usr/bin/env python3
"""
Regenerate alt_text ONLY for images that don't have it.
Preserves all other metadata (title, caption, description, tags, category).

Cost: ~$0.02 per image
"""
import asyncio
import sys

sys.path.insert(0, "/app")

from api.database import get_db_connection  # noqa: E402
from api.services.claude_vision import analyze_image  # noqa: E402


async def regenerate_alt_text_only():
    """Regenerate alt_text for all images missing it."""

    async with get_db_connection() as db:
        # Get all images without alt_text
        cursor = await db.execute(
            """
            SELECT id, user_id, filename
            FROM images
            WHERE user_id = 1 AND (alt_text IS NULL OR alt_text = '')
            ORDER BY id
            """
        )
        images = await cursor.fetchall()

        print(f"Found {len(images)} images needing alt_text")
        print(f"Estimated cost: ${len(images) * 0.02:.2f}")
        print()

        success_count = 0
        fail_count = 0

        for i, (image_id, user_id, filename) in enumerate(images, 1):
            print(f"[{i}/{len(images)}] Processing image {image_id} ({filename})...", end=" ")

            try:
                file_path = f"/app/assets/gallery/{filename}"

                # Generate metadata using balanced style (good default)
                ai_metadata, ai_error = await analyze_image(
                    file_path, user_id=user_id, filename=filename, style="balanced"
                )

                if ai_error:
                    print(f"❌ Failed: {ai_error.user_message}")
                    fail_count += 1
                    continue

                # Extract ONLY alt_text
                alt_text = ai_metadata.get("alt_text", "")

                if not alt_text:
                    print("⚠️  No alt_text generated")
                    fail_count += 1
                    continue

                # Update ONLY alt_text field, set ai_generated_alt_text = 1
                await db.execute(
                    """
                    UPDATE images
                    SET alt_text = ?,
                        ai_generated_alt_text = 1,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (alt_text, image_id),
                )
                await db.commit()

                # Truncate for display
                display_alt = alt_text[:60] + "..." if len(alt_text) > 60 else alt_text
                print(f'✅ "{display_alt}"')
                success_count += 1

            except Exception as e:
                print(f"❌ Error: {str(e)}")
                fail_count += 1
                continue

        print()
        print(f"Complete! {success_count} succeeded, {fail_count} failed")
        print(f"Actual cost: ${success_count * 0.02:.2f}")


if __name__ == "__main__":
    asyncio.run(regenerate_alt_text_only())

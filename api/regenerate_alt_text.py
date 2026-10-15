#!/usr/bin/env python3
"""
Regenerate alt text where it is missing or is a copy of the caption.

Until PR #80 the upload path saved the caption as the alt text, so screen
readers read a mood sentence instead of a description, then read it again
as the caption. This replaces only those alt texts with a fresh one from
the tagging model. Nothing else changes: title, caption, tags and category
stay as they are.

Alt text a person has edited or approved (ai_generated_alt_text = 0) is
never touched. Regenerated alt text stays marked as an AI draft for review.

Dry run by default; pass --apply to write. Back up the database first.

Usage (in the api container):
    python api/regenerate_alt_text.py            # list what would change
    python api/regenerate_alt_text.py --apply    # regenerate and save

Cost: about $0.01 per image (Claude Sonnet 5.5; logged to ai_costs).
"""
import argparse
import asyncio
import sys

sys.path.insert(0, "/app")

from api.database import get_db_connection  # noqa: E402
from api.services.claude_vision import analyze_image  # noqa: E402

COST_PER_IMAGE = 0.01

CANDIDATES = """
    SELECT id, user_id, filename, published
    FROM images
    WHERE deleted_at IS NULL
      AND COALESCE(ai_generated_alt_text, 1) = 1
      AND (alt_text IS NULL OR TRIM(alt_text) = '' OR TRIM(alt_text) = TRIM(caption))
    ORDER BY published DESC, id
"""


async def regenerate(apply: bool):
    async with get_db_connection() as db:
        images = await (await db.execute(CANDIDATES)).fetchall()
        published = sum(1 for row in images if row[3])
        print(f"{len(images)} images need alt text ({published} published)")
        print(f"Estimated cost: ${len(images) * COST_PER_IMAGE:.2f}")
        if not apply:
            print("Dry run: ids", ", ".join(str(row[0]) for row in images))
            print("Run with --apply to regenerate.")
            return

        done = failed = 0
        for i, (image_id, user_id, filename, _) in enumerate(images, 1):
            print(f"[{i}/{len(images)}] image {image_id}...", end=" ", flush=True)
            metadata, error = await analyze_image(
                f"/app/assets/gallery/{filename}",
                user_id=user_id,
                filename=filename,
                style="balanced",
            )
            alt_text = (metadata or {}).get("alt_text", "").strip()
            row = await (
                await db.execute("SELECT caption FROM images WHERE id = ?", (image_id,))
            ).fetchone()
            if error or not alt_text or alt_text == (row[0] or "").strip():
                print(f"skipped ({error.user_message if error else 'no distinct alt text'})")
                failed += 1
                continue

            # Re-check the guard at write time: a person may have edited it meanwhile
            await db.execute(
                """
                UPDATE images
                SET alt_text = ?, ai_generated_alt_text = 1, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND COALESCE(ai_generated_alt_text, 1) = 1
                """,
                (alt_text, image_id),
            )
            await db.commit()
            print(alt_text[:70] + ("..." if len(alt_text) > 70 else ""))
            done += 1

        print(f"\nDone: {done} regenerated, {failed} skipped.")
        print(f"Approximate cost: ${done * COST_PER_IMAGE:.2f} (exact figures in ai_costs)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--apply", action="store_true", help="regenerate and save")
    asyncio.run(regenerate(parser.parse_args().apply))

"""
Admin cleanup CLI for permanently purging soft-deleted images.

Images deleted via DELETE /api/images/{id} or
DELETE /api/photographer/images/{id} are soft-deleted (images.deleted_at is
set) rather than removed immediately. This script permanently removes the
DB row and physical files (original + WebP variants) for images that have
been soft-deleted for longer than the grace period.

Usage:
    python -m api.cleanup                    # purge using the default grace period (30 days)
    python -m api.cleanup --days 7            # use a custom grace period
    python -m api.cleanup --dry-run           # report what would be purged, change nothing

Intended to be run periodically (e.g. via cron, alongside scripts/backup.sh)
rather than synchronously from the delete request path.
"""

import argparse
import asyncio

from api.services.image_deletion import DEFAULT_GRACE_PERIOD_DAYS, purge_expired_deletes


async def _run(grace_period_days: int, dry_run: bool) -> None:
    if dry_run:
        from api.database import get_db_connection

        async with get_db_connection() as db:
            cursor = await db.execute(
                """
                SELECT id, filename, deleted_at FROM images
                WHERE deleted_at IS NOT NULL
                  AND deleted_at <= datetime('now', ?)
                """,
                (f"-{grace_period_days} days",),
            )
            rows = await cursor.fetchall()

        if not rows:
            print(f"No images past the {grace_period_days}-day grace period. Nothing to purge.")
            return

        print(f"Would purge {len(rows)} image(s) (grace period: {grace_period_days} days):")
        for row in rows:
            print(f"  - id={row[0]} filename={row[1]} deleted_at={row[2]}")
        return

    purged_ids = await purge_expired_deletes(grace_period_days=grace_period_days)

    if not purged_ids:
        print(f"No images past the {grace_period_days}-day grace period. Nothing to purge.")
    else:
        print(f"Purged {len(purged_ids)} image(s): {purged_ids}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Permanently purge soft-deleted images past their grace period."
    )
    parser.add_argument(
        "--days",
        type=int,
        default=DEFAULT_GRACE_PERIOD_DAYS,
        help=f"Grace period in days (default: {DEFAULT_GRACE_PERIOD_DAYS})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be purged without deleting anything",
    )
    args = parser.parse_args()

    asyncio.run(_run(args.days, args.dry_run))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Migration 004: Add soft-delete support to the images table

Adds:
1. deleted_at column to images table (NULL = active, timestamp = deleted)
2. Index on deleted_at for fast filtering of soft-deleted rows

Context: DELETE /api/images/{id} and DELETE /api/photographer/images/{id}
previously hard-deleted the image row immediately (with no undo), and one
of the two endpoints also left orphaned physical files on disk. Both now
soft-delete (set deleted_at) instead; physical files are removed later by
api.cleanup.purge_expired_deletes() after a grace period.

This script mirrors the standalone-migration pattern used by 001-003 for
manual/one-off application. The same column addition also runs
automatically (idempotently) via run_migrations() in api/database.py.
"""

import sqlite3
import sys
import os
from pathlib import Path

# Database path
DATABASE_PATH = os.getenv("DATABASE_PATH", "/data/gallery.db")


def main():
    """Run migration"""
    print("Running migration 004: Add soft-delete support to images table")
    print(f"Database: {DATABASE_PATH}")

    # Check if database exists
    if not Path(DATABASE_PATH).exists():
        print(f"ERROR: Database not found at {DATABASE_PATH}")
        print("Please ensure the database has been initialized first.")
        sys.exit(1)

    # Connect to database
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute("PRAGMA table_info(images)")
        image_columns = [col[1] for col in cursor.fetchall()]

        if "deleted_at" in image_columns:
            print("✓ Column 'deleted_at' already exists in images. Skipping column addition.")
        else:
            print("Adding 'deleted_at' column to images table...")
            cursor.execute("ALTER TABLE images ADD COLUMN deleted_at DATETIME DEFAULT NULL")
            conn.commit()
            print("✓ deleted_at column added successfully")

        print("Ensuring index on deleted_at exists...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_images_deleted_at ON images(deleted_at)")
        conn.commit()
        print("✓ Index idx_images_deleted_at is present")

        print("\n" + "=" * 60)
        print("Migration 004 complete!")
        print("=" * 60)
        print("\nImage deletes are now soft deletes (deleted_at timestamp).")
        print("Run `python -m api.cleanup` periodically (or via cron) to")
        print("permanently remove rows/files older than the grace period.")
        print("=" * 60)

    except Exception as e:
        print(f"\nERROR: Migration failed: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()

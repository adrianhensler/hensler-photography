#!/usr/bin/env python3
"""
Migration 003: Add photographer activity tracking

Adds support for distinguishing photographer's own activity from visitor activity:
1. Adds metadata column to image_events table (fixes missing column)
2. Adds is_photographer column to image_events table
3. Adds track_own_activity column to users table
4. Creates index on is_photographer for query performance

This enables "self vs other" analytics where photographers can:
- Toggle whether their own activity is tracked
- View separate analytics for visitors vs their own activity
- See combined view with both datasets
"""

import sqlite3
import sys
import os
from pathlib import Path

# Database path
DATABASE_PATH = os.getenv("DATABASE_PATH", "/data/gallery.db")


def main():
    """Run migration"""
    print("Running migration 003: Add photographer activity tracking")
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
        # --- Part 1: Add metadata column to image_events (bug fix) ---
        cursor.execute("PRAGMA table_info(image_events)")
        event_columns = [col[1] for col in cursor.fetchall()]

        if "metadata" in event_columns:
            print("✓ Column 'metadata' already exists in image_events")
        else:
            print("Adding 'metadata' column to image_events table...")
            cursor.execute("ALTER TABLE image_events ADD COLUMN metadata TEXT")
            conn.commit()
            print("✓ metadata column added successfully")

        # --- Part 2: Add is_photographer column to image_events ---
        cursor.execute("PRAGMA table_info(image_events)")
        event_columns = [col[1] for col in cursor.fetchall()]

        if "is_photographer" in event_columns:
            print("✓ Column 'is_photographer' already exists in image_events")
        else:
            print("Adding 'is_photographer' column to image_events table...")
            cursor.execute(
                "ALTER TABLE image_events ADD COLUMN is_photographer BOOLEAN DEFAULT 0"
            )
            conn.commit()
            print("✓ is_photographer column added successfully")

            # Create index for performance
            print("Creating index on is_photographer...")
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_is_photographer ON image_events(is_photographer)"
            )
            conn.commit()
            print("✓ Index created successfully")

        # --- Part 3: Add track_own_activity column to users ---
        cursor.execute("PRAGMA table_info(users)")
        user_columns = [col[1] for col in cursor.fetchall()]

        if "track_own_activity" in user_columns:
            print("✓ Column 'track_own_activity' already exists in users")
        else:
            print("Adding 'track_own_activity' column to users table...")
            cursor.execute(
                "ALTER TABLE users ADD COLUMN track_own_activity BOOLEAN DEFAULT 1"
            )
            conn.commit()
            print("✓ track_own_activity column added successfully")

        # Verify final schema
        print("\n" + "=" * 60)
        print("Verifying schema changes...")

        cursor.execute("PRAGMA table_info(image_events)")
        event_columns = [col[1] for col in cursor.fetchall()]
        print(f"image_events columns: {', '.join(event_columns)}")

        cursor.execute("PRAGMA table_info(users)")
        user_columns = [col[1] for col in cursor.fetchall()]
        print(f"users columns: {', '.join(user_columns)}")

        print("=" * 60)
        print("\nMigration 003 complete!")
        print("=" * 60)
        print("\nNew features enabled:")
        print("  • metadata: Store additional event data (duration, scroll depth, etc.)")
        print("  • is_photographer: Flag to distinguish photographer's own activity")
        print("  • track_own_activity: User preference toggle (default: ON)")
        print("\nNext steps:")
        print("  1. Update frontend tracking code to detect authentication")
        print("  2. Add settings UI for track_own_activity toggle")
        print("  3. Add filtering to analytics API endpoints")
        print("  4. Update analytics dashboard with visitor/mine/combined views")
        print("=" * 60)

    except Exception as e:
        print(f"\nERROR: Migration failed: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()

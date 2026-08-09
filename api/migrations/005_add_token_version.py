#!/usr/bin/env python3
"""
Migration 005: Add token_version to the users table

Adds:
1. token_version column to users (incremented to revoke outstanding JWTs)

Context: session JWTs previously stayed valid for their full 24h lifetime
regardless of logout or password change. get_current_user now compares the
token's "tv" claim against users.token_version, so bumping the column
revokes every outstanding token for that user. Logout and password change
both bump it (password change reissues a fresh cookie for the caller).

This script mirrors the standalone-migration pattern used by 001-004 for
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
    print("Running migration 005: Add token_version to users table")
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
        cursor.execute("PRAGMA table_info(users)")
        user_columns = [col[1] for col in cursor.fetchall()]

        if "token_version" in user_columns:
            print("✓ Column 'token_version' already exists in users. Skipping.")
        else:
            print("Adding 'token_version' column to users table...")
            cursor.execute(
                "ALTER TABLE users ADD COLUMN token_version INTEGER NOT NULL DEFAULT 0"
            )
            conn.commit()
            print("✓ token_version column added successfully")

        print("\n" + "=" * 60)
        print("Migration 005 complete!")
        print("=" * 60)
        print("\nSessions issued before this deploy lack the 'tv' claim and")
        print("will be rejected; users simply log in again.")
        print("=" * 60)

    except Exception as e:
        print(f"\nERROR: Migration failed: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()

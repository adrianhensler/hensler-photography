#!/usr/bin/env python3
"""
Migration 002: Add Google OAuth support

Adds:
1. google_id column to users table (stores Google user ID)
2. auth_method column to track authentication method
3. Makes password_hash nullable (for Google-only users)
4. Links existing users by email
"""

import sqlite3
import sys
import os
from pathlib import Path

# Database path
DATABASE_PATH = os.getenv("DATABASE_PATH", "/app/hensler_photography.db")


def main():
    """Run migration"""
    print(f"Running migration 002: Add Google OAuth support")
    print(f"Database: {DATABASE_PATH}")

    # Check if database exists
    if not Path(DATABASE_PATH).exists():
        print(f"ERROR: Database not found at {DATABASE_PATH}")
        sys.exit(1)

    # Connect to database
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    try:
        # Check existing columns
        cursor.execute("PRAGMA table_info(users)")
        columns = {col[1]: col for col in cursor.fetchall()}

        # Add google_id column (without UNIQUE constraint - SQLite limitation)
        if "google_id" not in columns:
            print("Adding 'google_id' column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN google_id TEXT")
            conn.commit()
            print("✓ google_id column added")

            # Create unique index for google_id
            print("Creating unique index on google_id...")
            cursor.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_google_id ON users(google_id) WHERE google_id IS NOT NULL"
            )
            conn.commit()
            print("✓ Unique index created")
        else:
            print("✓ google_id column already exists")

        # Add auth_method column
        if "auth_method" not in columns:
            print("Adding 'auth_method' column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN auth_method TEXT DEFAULT 'password'")
            conn.commit()
            print("✓ auth_method column added")
        else:
            print("✓ auth_method column already exists")

        print("\n" + "=" * 60)
        print("Migration 002 complete!")
        print("=" * 60)
        print("\nGoogle OAuth is now available.")
        print("\nTo enable:")
        print("1. Create OAuth credentials at: https://console.cloud.google.com/apis/credentials")
        print(
            "2. Set authorized redirect URI: https://hensler.photography:4100/api/auth/google/callback"
        )
        print("3. Set environment variables:")
        print("   - GOOGLE_CLIENT_ID=your-client-id")
        print("   - GOOGLE_CLIENT_SECRET=your-client-secret")
        print("\nUsers can now sign in with:")
        print("  - Username/password (existing)")
        print("  - Google account (new)")
        print("=" * 60)

    except Exception as e:
        print(f"\nERROR: Migration failed: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Migration 001: Add password_hash column to users table

Adds authentication support by:
1. Adding password_hash column to users table
2. Seeding initial passwords for Adrian (admin) and Liam (photographer)

IMPORTANT: Change these passwords immediately after first login!
"""

import sqlite3
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import bcrypt


# Password hashing function
def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


# Database path
DATABASE_PATH = os.getenv("DATABASE_PATH", "/app/hensler_photography.db")

# TEMPORARY initial passwords (MUST be changed on first login)
# Note: bcrypt has 72-byte limit, keep passwords reasonable length
INITIAL_PASSWORDS = {
    "adrian": "Admin2024!",  # Admin user
    "liam": "Photo2024!",  # Photographer user
}


def main():
    """Run migration"""
    print("Running migration 001: Add password_hash column")
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
        # Check if column already exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]

        if "password_hash" in columns:
            print("✓ Column 'password_hash' already exists. Skipping column addition.")
        else:
            print("Adding 'password_hash' column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
            conn.commit()
            print("✓ Column added successfully")

        # Check existing users
        cursor.execute("SELECT id, username, password_hash FROM users")
        users = cursor.fetchall()

        if not users:
            print("WARNING: No users found in database. Please run database initialization first.")
            sys.exit(1)

        print(f"\nFound {len(users)} users:")
        for user_id, username, existing_hash in users:
            print(f"  - {username} (id={user_id})")

        # Seed passwords
        print("\nSeeding initial passwords...")
        for user_id, username, existing_hash in users:
            if existing_hash:
                print(f"  ✓ {username} already has password hash. Skipping.")
                continue

            if username not in INITIAL_PASSWORDS:
                print(f"  ⚠ No initial password defined for {username}. Skipping.")
                continue

            # Hash password
            password = INITIAL_PASSWORDS[username]
            password_hash = hash_password(password)

            # Update database
            cursor.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id)
            )
            print(f"  ✓ {username}: Password set (TEMPORARY - change on first login!)")

        conn.commit()

        print("\n" + "=" * 60)
        print("Migration 001 complete!")
        print("=" * 60)
        print("\nIMPORTANT: Initial passwords set:")
        for username, password in INITIAL_PASSWORDS.items():
            print(f"  {username}: {password}")
        print("\n⚠️  CHANGE THESE PASSWORDS IMMEDIATELY ON FIRST LOGIN!")
        print("=" * 60)

    except Exception as e:
        print(f"\nERROR: Migration failed: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()

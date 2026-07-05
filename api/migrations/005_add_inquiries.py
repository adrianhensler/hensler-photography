#!/usr/bin/env python3
"""
Migration 005: Add inquiry chat tables

Creates two tables:
  - inquiry_sessions: tracks active chat sessions (TTL-based, auto-expire)
  - inquiries: submitted, consent-backed inquiry briefs

Run via:
  docker compose -p hensler_test exec api python -m api.migrations.005_add_inquiries
"""

import sqlite3
import sys
import os
from pathlib import Path

DATABASE_PATH = os.getenv("DATABASE_PATH", "/data/gallery.db")


def main():
    print("Running migration 005: Add inquiry chat tables")
    print(f"Database: {DATABASE_PATH}")

    if not Path(DATABASE_PATH).exists():
        print(f"ERROR: Database not found at {DATABASE_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute("PRAGMA table_info(inquiry_sessions)")
        if cursor.fetchall():
            print("✓ inquiry_sessions already exists")
        else:
            print("Creating inquiry_sessions table...")
            cursor.execute("""
                CREATE TABLE inquiry_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    ip_hash TEXT,
                    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_active DATETIME DEFAULT CURRENT_TIMESTAMP,
                    turn_count INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'active',
                    messages TEXT DEFAULT '[]'
                )
            """)
            cursor.execute(
                "CREATE INDEX idx_inquiry_sessions_session_id ON inquiry_sessions(session_id)"
            )
            cursor.execute(
                "CREATE INDEX idx_inquiry_sessions_status ON inquiry_sessions(status)"
            )
            conn.commit()
            print("✓ inquiry_sessions created")

        cursor.execute("PRAGMA table_info(inquiries)")
        if cursor.fetchall():
            print("✓ inquiries already exists")
        else:
            print("Creating inquiries table...")
            cursor.execute("""
                CREATE TABLE inquiries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    name TEXT,
                    email TEXT,
                    project_type TEXT,
                    timeframe TEXT,
                    location TEXT,
                    style_notes TEXT,
                    budget_range TEXT,
                    transcript TEXT,
                    consent_given INTEGER DEFAULT 0,
                    ip_hash TEXT,
                    status TEXT DEFAULT 'new'
                )
            """)
            cursor.execute(
                "CREATE INDEX idx_inquiries_submitted_at ON inquiries(submitted_at)"
            )
            conn.commit()
            print("✓ inquiries created")

        print("\nMigration 005 complete.")

    except Exception as e:
        print(f"\nERROR: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()

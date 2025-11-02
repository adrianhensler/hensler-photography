"""
Database module for Hensler Photography

SQLite database with multi-tenant support for photographers,
images, analytics, and e-commerce (future).
"""

import sqlite3
import aiosqlite
import os
from contextlib import contextmanager, asynccontextmanager
from datetime import datetime

DATABASE_PATH = os.getenv("DATABASE_PATH", "/data/gallery.db")

# SQL schema for database initialization
SCHEMA = """
-- Users (photographers)
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    display_name TEXT,
    role TEXT DEFAULT 'photographer',
    subdomain TEXT,
    bio TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Images (belongs to user)
CREATE TABLE IF NOT EXISTS images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,

    -- File info
    filename TEXT NOT NULL,
    slug TEXT NOT NULL,
    original_filename TEXT,

    -- Content
    title TEXT,
    caption TEXT,
    description TEXT,

    -- EXIF data
    camera_make TEXT,
    camera_model TEXT,
    lens TEXT,
    focal_length TEXT,
    aperture TEXT,
    shutter_speed TEXT,
    iso INTEGER,
    date_taken DATETIME,
    location TEXT,

    -- Organization
    category TEXT,
    tags TEXT,

    -- Dimensions
    width INTEGER,
    height INTEGER,
    aspect_ratio REAL,
    file_size INTEGER,

    -- Status
    published BOOLEAN DEFAULT 0,
    featured BOOLEAN DEFAULT 0,
    available_for_sale BOOLEAN DEFAULT 0,

    -- Display order
    sort_order INTEGER DEFAULT 0,

    -- Timestamps
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(user_id, slug)
);

-- Image variants (WebP, AVIF, multiple sizes)
CREATE TABLE IF NOT EXISTS image_variants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_id INTEGER NOT NULL,
    format TEXT,
    size TEXT,
    filename TEXT,
    width INTEGER,
    height INTEGER,
    file_size INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (image_id) REFERENCES images(id) ON DELETE CASCADE
);

-- Analytics: Click tracking
CREATE TABLE IF NOT EXISTS image_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_id INTEGER,
    event_type TEXT,
    user_agent TEXT,
    referrer TEXT,
    ip_hash TEXT,
    session_id TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (image_id) REFERENCES images(id)
);

-- Future: Products (print sizes, pricing)
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_id INTEGER NOT NULL,
    product_type TEXT,
    size TEXT,
    price_cents INTEGER,
    available BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (image_id) REFERENCES images(id)
);

-- Future: Orders
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    stripe_payment_id TEXT,
    customer_email TEXT,
    shipping_address TEXT,
    amount_cents INTEGER,
    status TEXT DEFAULT 'pending',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- Future: User sessions
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    expires_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_images_user ON images(user_id);
CREATE INDEX IF NOT EXISTS idx_images_published ON images(published);
CREATE INDEX IF NOT EXISTS idx_images_slug ON images(user_id, slug);
CREATE INDEX IF NOT EXISTS idx_events_image ON image_events(image_id);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON image_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_variants_image ON image_variants(image_id);
"""

# Seed data for initial users
SEED_DATA = """
-- Insert Adrian as first user (admin)
INSERT OR IGNORE INTO users (id, username, email, display_name, role, subdomain, bio)
VALUES (
    1,
    'adrian',
    'adrianhensler@gmail.com',
    'Adrian Hensler',
    'admin',
    'adrian',
    'Images from Halifax and surrounding areas. Light, land, and life.'
);

-- Insert Liam as second user
INSERT OR IGNORE INTO users (id, username, email, display_name, role, subdomain, bio)
VALUES (
    2,
    'liam',
    'liam@hensler.photography',
    'Liam Hensler',
    'photographer',
    'liam',
    'Visual stories through photography.'
);
"""


@contextmanager
def get_db():
    """Context manager for database connections (synchronous)"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@asynccontextmanager
async def get_db_connection():
    """Async context manager for database connections"""
    conn = await aiosqlite.connect(DATABASE_PATH)
    conn.row_factory = aiosqlite.Row
    try:
        yield conn
        await conn.commit()
    except Exception:
        await conn.rollback()
        raise
    finally:
        await conn.close()


def init_database():
    """Initialize database with schema and seed data"""
    # Ensure data directory exists
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

    with get_db() as conn:
        cursor = conn.cursor()

        # Execute schema
        cursor.executescript(SCHEMA)

        # Seed initial data
        cursor.executescript(SEED_DATA)

        print(f"✓ Database initialized at {DATABASE_PATH}")


def get_user(username: str):
    """Get user by username"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        return cursor.fetchone()


def get_all_users():
    """Get all users"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users ORDER BY created_at")
        return cursor.fetchall()


def track_event(image_id: int, event_type: str, session_id: str = None,
                user_agent: str = None, referrer: str = None, ip_hash: str = None):
    """Track an image event"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO image_events
            (image_id, event_type, session_id, user_agent, referrer, ip_hash, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (image_id, event_type, session_id, user_agent, referrer, ip_hash, datetime.utcnow()))
        return cursor.lastrowid


if __name__ == "__main__":
    # Initialize database when run directly
    init_database()
    print("Database initialization complete!")

    # Show users
    users = get_all_users()
    print(f"\nUsers created: {len(users)}")
    for user in users:
        print(f"  - {user['username']} ({user['display_name']})")

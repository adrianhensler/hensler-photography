"""
Test Configuration and Fixtures

This file provides shared test infrastructure:
- In-memory test database
- Sample users (Adrian, Liam)
- Sample images for each user
- Authentication token helpers
"""

import asyncio
import os
import tempfile
from pathlib import Path

import pytest
from httpx import AsyncClient, ASGITransport
from api.main import app
from api.database import get_db_connection
from api.routes.auth import hash_password, create_access_token


# Test database path (in-memory for speed)
TEST_DB_PATH = ":memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_db():
    """
    Create a fresh test database for each test

    This ensures test isolation - each test starts with clean state.
    """
    # Set test database path
    os.environ["DATABASE_PATH"] = TEST_DB_PATH

    # Initialize schema
    async with get_db_connection() as db:
        # Users table
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'photographer',
                subdomain TEXT,
                display_name TEXT,
                bio TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        """
        )

        # Images table
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                slug TEXT NOT NULL,
                title TEXT,
                caption TEXT,
                tags TEXT,
                category TEXT,
                width INTEGER,
                height INTEGER,
                aspect_ratio REAL,
                published BOOLEAN DEFAULT 0,
                share_exif BOOLEAN DEFAULT 0,
                sort_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(user_id, slug)
            )
        """
        )

        # Seed test users
        adrian_hash = hash_password("adrian123")
        liam_hash = hash_password("liam123")

        await db.execute(
            """
            INSERT INTO users (id, username, email, password_hash, role, subdomain, display_name)
            VALUES (1, 'adrian', 'adrian@example.com', ?, 'admin', 'adrian', 'Adrian Hensler')
        """,
            (adrian_hash,),
        )

        await db.execute(
            """
            INSERT INTO users (id, username, email, password_hash, role, subdomain, display_name)
            VALUES (2, 'liam', 'liam@example.com', ?, 'photographer', 'liam', 'Liam Hensler')
        """,
            (liam_hash,),
        )

        # Seed test images
        # Adrian's image
        await db.execute(
            """
            INSERT INTO images (id, user_id, filename, slug, title, published, width, height, aspect_ratio)
            VALUES (1, 1, 'adrian_test_image.jpg', 'adrian-test', 'Adrian Test Image', 1, 1024, 768, 1.33)
        """
        )

        # Liam's image
        await db.execute(
            """
            INSERT INTO images (id, user_id, filename, slug, title, published, width, height, aspect_ratio)
            VALUES (2, 2, 'liam_test_image.jpg', 'liam-test', 'Liam Test Image', 1, 1024, 768, 1.33)
        """
        )

        await db.commit()

    yield

    # Cleanup (in-memory DB is automatically discarded)


@pytest.fixture
async def client(test_db):
    """HTTP client for making API requests in tests"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client


@pytest.fixture
def adrian_token():
    """Generate authentication token for Adrian (admin role)"""
    from api.routes.auth import User

    adrian_user = User(
        id=1,
        username="adrian",
        display_name="Adrian Hensler",
        email="adrian@example.com",
        role="admin",
    )
    return create_access_token(adrian_user)


@pytest.fixture
def liam_token():
    """Generate authentication token for Liam (photographer role)"""
    from api.routes.auth import User

    liam_user = User(
        id=2,
        username="liam",
        display_name="Liam Hensler",
        email="liam@example.com",
        role="photographer",
    )
    return create_access_token(liam_user)


@pytest.fixture
def auth_headers_adrian(adrian_token):
    """Authorization headers for Adrian"""
    return {"Authorization": f"Bearer {adrian_token}"}


@pytest.fixture
def auth_headers_liam(liam_token):
    """Authorization headers for Liam"""
    return {"Authorization": f"Bearer {liam_token}"}

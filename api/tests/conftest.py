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

# Must run before any api.* import: api.database freezes DATABASE_PATH at
# import time, so assigning it later (as this file previously did inside the
# test_db fixture) silently points every connection at the real database.
_TEST_DB = tempfile.NamedTemporaryFile(prefix="hensler_test_", suffix=".db", delete=False)
os.environ["DATABASE_PATH"] = _TEST_DB.name

import pytest
from httpx import AsyncClient, ASGITransport
from api.main import app
from api.database import get_db_connection, SCHEMA, run_migrations
from api.routes.auth import hash_password, create_access_token


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_db():
    """
    Provide a fully-migrated schema with clean seeded state for each test.

    Uses the real SCHEMA plus run_migrations() so the test schema can never
    drift from production (the previous hand-copied DDL here drifted twice).
    The temp-file database persists for the pytest session; row state is
    reset per test for isolation.
    """
    # Initialize schema (idempotent: SCHEMA uses IF NOT EXISTS throughout)
    async with get_db_connection() as db:
        await db.executescript(SCHEMA)
        await db.commit()
    run_migrations()

    async with get_db_connection() as db:
        # Reset state; children before parents to satisfy foreign keys.
        for table in ("image_events", "audit_log", "images", "users"):
            await db.execute(f"DELETE FROM {table}")

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


def _session_headers(token: str) -> dict:
    """Session cookie plus a CSRF token bound to that session.

    get_current_user reads the JWT from the session_token cookie (not an
    Authorization header), and mutating routes require a session-bound
    X-CSRF-Token header, which manage-header.js attaches in production.
    """
    from api.csrf import generate_csrf_token

    return {
        "Cookie": f"session_token={token}",
        "X-CSRF-Token": generate_csrf_token(session_data=token),
    }


@pytest.fixture
def auth_headers_adrian(adrian_token):
    """Auth headers for Adrian (session cookie + bound CSRF token)."""
    return _session_headers(adrian_token)


@pytest.fixture
def auth_headers_liam(liam_token):
    """Auth headers for Liam (session cookie + bound CSRF token)."""
    return _session_headers(liam_token)

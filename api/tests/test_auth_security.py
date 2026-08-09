"""
Auth hardening tests: token revocation, CSRF session binding, login behavior.

Covers the changes from the auth-hardening PR:
- token_version revocation (logout / password change invalidate old JWTs)
- CSRF tokens are bound to the session that minted them
- register and change-password require a CSRF token
- login failures are indistinguishable for unknown user vs wrong password

Note: tests mint JWTs directly (like conftest fixtures) instead of calling
/api/auth/login repeatedly, because the login route is rate-limited to
5/minute per IP and the limiter state persists across tests in-process.
"""

import jwt
import pytest

from api.csrf import generate_csrf_token
from api.routes.auth import (
    ALGORITHM,
    SECRET_KEY,
    User,
    create_access_token,
)


def make_user(token_version: int = 0) -> User:
    """Adrian as seeded by conftest, with a chosen token_version."""
    return User(
        id=1,
        username="adrian",
        display_name="Adrian Hensler",
        email="adrian@example.com",
        role="admin",
        token_version=token_version,
    )


def session_headers(token: str) -> dict:
    """Cookie + session-bound CSRF header, as a real /manage page would send."""
    return {
        "Cookie": f"session_token={token}",
        "X-CSRF-Token": generate_csrf_token(session_data=token),
    }


@pytest.mark.asyncio
async def test_login_sets_cookie_and_authenticates(client):
    """The full login round-trip still works and yields a usable session."""
    response = await client.post(
        "/api/auth/login", data={"username": "adrian", "password": "adrian123"}
    )
    assert response.status_code == 200
    assert "session_token" in response.cookies

    me = await client.get(
        "/api/auth/me", headers={"Cookie": f"session_token={response.cookies['session_token']}"}
    )
    assert me.status_code == 200
    assert me.json()["username"] == "adrian"


@pytest.mark.asyncio
async def test_unknown_user_and_wrong_password_are_indistinguishable(client):
    """Both failure modes return the same status and message."""
    unknown = await client.post(
        "/api/auth/login", data={"username": "nobody", "password": "wrong-password-1!"}
    )
    wrong = await client.post(
        "/api/auth/login", data={"username": "adrian", "password": "wrong-password-1!"}
    )
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json() == wrong.json()


@pytest.mark.asyncio
async def test_token_without_version_claim_is_rejected(client):
    """Pre-upgrade JWTs (no tv claim) fail closed."""
    payload = {"user_id": 1, "username": "adrian", "role": "admin"}
    legacy_token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    response = await client.get(
        "/api/auth/me", headers={"Cookie": f"session_token={legacy_token}"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout_revokes_all_outstanding_tokens(client):
    """After logout, a previously valid JWT no longer authenticates."""
    token = create_access_token(make_user())

    assert (
        await client.get("/api/auth/me", headers={"Cookie": f"session_token={token}"})
    ).status_code == 200

    logout = await client.post("/api/auth/logout", headers=session_headers(token))
    assert logout.status_code == 200

    after = await client.get("/api/auth/me", headers={"Cookie": f"session_token={token}"})
    assert after.status_code == 401


@pytest.mark.asyncio
async def test_password_change_revokes_old_sessions_but_reissues_caller(client):
    """Password change kills old JWTs and hands the caller a fresh cookie."""
    token = create_access_token(make_user())

    response = await client.post(
        "/api/auth/change-password",
        json={
            "current_password": "adrian123",
            "new_password": "NewSecurePass1!",
            "confirm_password": "NewSecurePass1!",
        },
        headers=session_headers(token),
    )
    assert response.status_code == 200

    # The old token is dead...
    old = await client.get("/api/auth/me", headers={"Cookie": f"session_token={token}"})
    assert old.status_code == 401

    # ...but the response set a fresh cookie that works.
    new_token = response.cookies.get("session_token")
    assert new_token is not None
    fresh = await client.get(
        "/api/auth/me", headers={"Cookie": f"session_token={new_token}"}
    )
    assert fresh.status_code == 200


@pytest.mark.asyncio
async def test_csrf_token_must_match_session(client):
    """A CSRF token minted outside the session (anonymous or another session)
    is rejected for a session-cookie request."""
    token = create_access_token(make_user())

    for foreign_csrf in (
        generate_csrf_token(),  # anonymous-context token
        generate_csrf_token(session_data="some-other-session"),
    ):
        response = await client.post(
            "/api/auth/logout",
            headers={"Cookie": f"session_token={token}", "X-CSRF-Token": foreign_csrf},
        )
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_register_requires_csrf(client):
    """register rejects requests without a CSRF token and accepts bound ones."""
    token = create_access_token(make_user())
    new_user = {
        "username": "testuser",
        "email": "testuser@example.com",
        "display_name": "Test User",
        "password": "ValidPass123!x",
        "role": "photographer",
    }

    missing = await client.post(
        "/api/auth/register",
        json=new_user,
        headers={"Cookie": f"session_token={token}"},
    )
    assert missing.status_code == 403

    bound = await client.post(
        "/api/auth/register", json=new_user, headers=session_headers(token)
    )
    assert bound.status_code == 200
    assert bound.json()["success"] is True


@pytest.mark.asyncio
async def test_change_password_requires_csrf(client):
    """change-password rejects requests without a CSRF token."""
    token = create_access_token(make_user())

    response = await client.post(
        "/api/auth/change-password",
        json={
            "current_password": "adrian123",
            "new_password": "NewSecurePass1!",
            "confirm_password": "NewSecurePass1!",
        },
        headers={"Cookie": f"session_token={token}"},
    )
    assert response.status_code == 403

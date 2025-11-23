"""
Simplified Security Test - Demonstrates TDD

This is a streamlined version that tests the critical security bug
without complex fixtures.
"""

import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from api.main import app
from api.routes.auth import User, create_access_token


@pytest.mark.asyncio
async def test_photographer_cannot_edit_other_users_images():
    """
    CRITICAL SECURITY TEST

    This test demonstrates TDD:
    1. Test FAILS initially - security bug exists
    2. Add user_id check in photographer.py
    3. Test PASSES - security hole closed

    Without the verify_image_ownership() check in api/routes/photographer.py,
    Liam can edit Adrian's images!
    """
    # Create test API client
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:

        # Create authentication tokens
        liam_user = User(
            id=2,
            username="liam",
            display_name="Liam Hensler",
            email="liam@example.com",
            role="photographer",
        )

        liam_token = create_access_token(liam_user)

        # Adrian's image (id=1, user_id=1) exists in test database
        adrian_image_id = 1

        # Liam tries to edit Adrian's image (using cookie authentication)
        response = await client.put(
            f"/api/photographer/images/{adrian_image_id}",
            cookies={"session_token": liam_token},
            json={
                "title": "Hacked by Liam!",
                "caption": "This should not work!",
            },
        )

        # EXPECTED: 403 or 404 (Liam doesn't own this image)
        # ACTUAL BEFORE FIX: 200 OK - security bug!
        assert response.status_code in [403, 404], (
            f"Security Bug: Liam (user_id=2) was able to edit Adrian's image (user_id=1). "
            f"Expected 403 or 404, got {response.status_code}. "
            f"This means photographers can modify each other's data!"
        )

        print(f"✓ Security test passed! Status code: {response.status_code}")
        print("✓ Photographers cannot edit each other's images")


if __name__ == "__main__":
    # Run test directly
    asyncio.run(test_photographer_cannot_edit_other_users_images())
    print("\n✓ All security tests passed!")

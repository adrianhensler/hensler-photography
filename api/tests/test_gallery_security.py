"""
Gallery Security Tests

These tests verify multi-tenancy isolation - ensuring photographers
can only access and modify their own images, never another user's data.

This is a CRITICAL security boundary. Without these tests, bugs could allow:
- Liam to edit/delete Adrian's images
- Data leakage across user boundaries
- Privilege escalation attacks

TDD Example: This test will FAIL initially, exposing a real security bug
in the photographer routes. After fixing the bug, the test passes.
"""

import pytest
from httpx import AsyncClient


class TestMultiTenancyIsolation:
    """
    Test suite for multi-tenancy security

    These tests verify the core security principle:
    User A cannot access User B's data
    """

    @pytest.mark.asyncio
    async def test_photographer_cannot_edit_other_users_images(
        self, client, auth_headers_liam, auth_headers_adrian
    ):
        """
        CRITICAL SECURITY TEST: Verify photographers cannot edit each other's images

        Scenario:
        1. Adrian has image_id=1 (created in conftest.py)
        2. Liam authenticates and tries to edit Adrian's image
        3. Expected: 403 Forbidden (or 404 Not Found)
        4. Actual (before fix): 200 OK - BUG! Liam can modify Adrian's data

        This test demonstrates TDD:
        - Write test first (it FAILS - bug exists)
        - Fix the bug (add user_id check in photographer.py)
        - Test passes - security hole closed
        """
        # Adrian's image (id=1, user_id=1)
        adrian_image_id = 1

        # Liam tries to update Adrian's image title
        response = await client.put(
            f"/api/photographer/images/{adrian_image_id}",
            headers=auth_headers_liam,
            json={
                "title": "Hacked by Liam!",
                "caption": "Liam should not be able to edit this",
            },
        )

        # EXPECTED: 403 Forbidden (Liam doesn't own this image)
        # ACTUAL (before fix): 200 OK - security bug exists!
        assert response.status_code in [403, 404], (
            f"Security Bug: Liam (user_id=2) was able to edit Adrian's image "
            f"(user_id=1). Expected 403 or 404, got {response.status_code}. "
            f"This means photographers can modify each other's data!"
        )

        # Verify Adrian's image was NOT modified
        response = await client.get(
            f"/api/photographer/images/{adrian_image_id}", headers=auth_headers_adrian
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Adrian Test Image"  # Original title unchanged
        assert "Hacked" not in data["title"]

    @pytest.mark.asyncio
    async def test_photographer_cannot_delete_other_users_images(
        self, client: AsyncClient, auth_headers_liam
    ):
        """
        CRITICAL SECURITY TEST: Verify photographers cannot delete each other's images

        This is even more critical than editing - deletion is irreversible.
        """
        adrian_image_id = 1

        # Liam tries to delete Adrian's image
        response = await client.delete(
            f"/api/photographer/images/{adrian_image_id}", headers=auth_headers_liam
        )

        # EXPECTED: 403 Forbidden
        assert response.status_code in [403, 404], (
            f"Security Bug: Liam was able to delete Adrian's image. "
            f"Expected 403 or 404, got {response.status_code}"
        )

    @pytest.mark.asyncio
    async def test_photographer_cannot_publish_other_users_images(
        self, client: AsyncClient, auth_headers_liam
    ):
        """
        SECURITY TEST: Verify photographers cannot publish each other's images

        While less critical than edit/delete, this could allow:
        - Publishing incomplete/embarrassing photos
        - Reputation damage
        """
        adrian_image_id = 1

        # Liam tries to publish/unpublish Adrian's image
        response = await client.patch(
            f"/api/photographer/images/{adrian_image_id}/publish",
            headers=auth_headers_liam,
            json={"published": False},
        )

        # EXPECTED: 403 Forbidden
        assert response.status_code in [
            403,
            404,
        ], "Security Bug: Liam was able to change Adrian's publish status"

    @pytest.mark.asyncio
    async def test_photographer_can_edit_own_images(self, client: AsyncClient, auth_headers_liam):
        """
        POSITIVE TEST: Verify photographers CAN edit their own images

        This ensures our security fix doesn't break legitimate functionality.
        """
        liam_image_id = 2  # Created in conftest.py, belongs to Liam

        # Liam edits his own image - should succeed
        response = await client.put(
            f"/api/photographer/images/{liam_image_id}",
            headers=auth_headers_liam,
            json={
                "title": "Updated by Liam",
                "caption": "This should work",
            },
        )

        # EXPECTED: 200 OK
        assert (
            response.status_code == 200
        ), f"Liam should be able to edit his own image, got {response.status_code}"

        # Verify update succeeded
        data = response.json()
        assert data["title"] == "Updated by Liam"

    @pytest.mark.asyncio
    async def test_gallery_api_only_returns_own_images(
        self, client: AsyncClient, auth_headers_liam
    ):
        """
        DATA ISOLATION TEST: Verify gallery API filters by user_id

        Even if a photographer knows another user's image IDs,
        they should never appear in the gallery response.
        """
        # Request Liam's gallery
        response = await client.get("/api/gallery/published?user_id=2", headers=auth_headers_liam)

        assert response.status_code == 200
        data = response.json()

        # Verify all images belong to Liam (user_id=2)
        for image in data.get("images", []):
            assert (
                image["id"] == 2
            ), f"Liam's gallery contains image {image['id']} which doesn't belong to him"

        # Verify Adrian's image (id=1) is NOT in Liam's gallery
        image_ids = [img["id"] for img in data.get("images", [])]
        assert 1 not in image_ids, "Adrian's image leaked into Liam's gallery!"


class TestAuthorizationEdgeCases:
    """
    Edge case tests for authorization logic

    These tests verify corner cases that might be missed in simple testing.
    """

    @pytest.mark.asyncio
    async def test_cannot_edit_nonexistent_image(self, client: AsyncClient, auth_headers_liam):
        """Verify proper error handling for nonexistent images"""
        response = await client.put(
            "/api/photographer/images/99999", headers=auth_headers_liam, json={"title": "Test"}
        )

        # Should return 404, not 500 or 403
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_unauthenticated_request_rejected(self, client: AsyncClient):
        """Verify unauthenticated requests are rejected"""
        response = await client.put(
            "/api/photographer/images/1",
            json={"title": "Test"},
            # No Authorization header
        )

        # Should return 401 Unauthorized
        assert response.status_code == 401


# Documentation for running these tests:
"""
HOW TO RUN THESE TESTS:

1. Install test dependencies:
   pip install pytest pytest-asyncio httpx

2. Run all tests:
   pytest api/tests/test_gallery_security.py -v

3. Run specific test:
   pytest api/tests/test_gallery_security.py::TestMultiTenancyIsolation::test_photographer_cannot_edit_other_users_images -v

4. Expected output BEFORE fix:
   FAILED test_photographer_cannot_edit_other_users_images - AssertionError: Security Bug: Liam (user_id=2) was able to edit Adrian's image

5. Expected output AFTER fix:
   PASSED test_photographer_cannot_edit_other_users_images

WHY THESE TESTS MATTER:

Without these tests, a security bug could go unnoticed until production,
where it could result in:
- Data loss (images deleted by wrong user)
- Data corruption (metadata changed by wrong user)
- Privacy violations (unpublished images made public)
- Reputation damage (embarrassing photos published)

With these tests, any code change that breaks multi-tenancy isolation
will be caught immediately during development.

This is TDD at its best: catching critical bugs before they reach users.
"""

"""
Approved photo addresses: a photo page lives at /photo/<id> until the
photographer approves an address made from the title; after that the id
link and any former addresses redirect (301) to the current address.
"""

from unittest.mock import patch

import pytest

from api.database import get_db_connection
from api.services.photo_address import address_from_title

ADRIAN_SITE = {"Host": "adrian.hensler.photography"}


@pytest.fixture
async def photos(test_db):
    """Adrian's image 1 gets a variant so its page renders; redirects start empty."""
    async with get_db_connection() as db:
        await db.execute("DELETE FROM image_address_redirects")
        await db.execute("DELETE FROM image_variants")
        await db.execute(
            "INSERT INTO image_variants (image_id, format, size, filename, width, height) "
            "VALUES (1, 'webp', 'large', 'adrian_test_large.webp', 1200, 900)"
        )
        await db.commit()


async def _set_title(image_id: int, title: str):
    async with get_db_connection() as db:
        await db.execute("UPDATE images SET title = ? WHERE id = ?", (title, image_id))
        await db.commit()


async def _redirects() -> list:
    async with get_db_connection() as db:
        cursor = await db.execute("SELECT slug, image_id FROM image_address_redirects")
        return sorted(tuple(row) for row in await cursor.fetchall())


def test_address_from_title():
    assert address_from_title("Dingle Tower in Fog", 5) == "dingle-tower-in-fog"
    assert address_from_title("Lion's Mane, Close-Up", 5) == "lion-s-mane-close-up"
    assert address_from_title("", 5) == "photo-5"
    # An all-digit address would be read as an image id
    assert address_from_title("1984", 5) == "photo-1984"


@pytest.mark.asyncio
async def test_unapproved_photo_uses_its_id(client, photos):
    page = await client.get("/photo/1", headers=ADRIAN_SITE)
    assert page.status_code == 200
    assert 'href="https://adrian.hensler.photography/photo/1"' in page.text

    # The AI-drafted slug from upload was never public and does not resolve
    assert (await client.get("/photo/adrian-test", headers=ADRIAN_SITE)).status_code == 404


@pytest.mark.asyncio
async def test_approving_sets_address_and_id_redirects(client, photos, auth_headers_adrian):
    response = await client.post("/api/images/1/address", headers=auth_headers_adrian)
    assert response.status_code == 200
    address = response.json()["address"]
    assert address["approved"] is True
    assert address["address"] == "adrian-test-image"
    assert address["path"] == "/photo/adrian-test-image"

    page = await client.get("/photo/adrian-test-image", headers=ADRIAN_SITE)
    assert page.status_code == 200
    assert 'href="https://adrian.hensler.photography/photo/adrian-test-image"' in page.text

    old = await client.get("/photo/1", headers=ADRIAN_SITE)
    assert old.status_code == 301
    assert old.headers["location"] == "/photo/adrian-test-image"

    published = await client.get("/api/gallery/published?user_id=1")
    image = next(i for i in published.json()["images"] if i["id"] == 1)
    assert image["page_path"] == "/photo/adrian-test-image"


@pytest.mark.asyncio
async def test_approving_the_address_approves_the_title(client, photos, auth_headers_adrian):
    async with get_db_connection() as db:
        await db.execute("UPDATE images SET ai_generated_title = 1, ai_generated_caption = 1")
        await db.commit()

    await client.post("/api/images/1/address", headers=auth_headers_adrian)

    disclosure = (await client.get("/api/images/1", headers=auth_headers_adrian)).json()[
        "ai_disclosure"
    ]
    assert disclosure["title"] is False
    assert disclosure["caption"] is True


def test_app_startup_runs_migrations():
    # A deploy rebuilds the image but the live database is a mounted volume;
    # migrations must run when the app starts, not only at image build
    from fastapi.testclient import TestClient

    from api.main import app

    with patch("api.main.run_migrations") as migrate, TestClient(app):
        migrate.assert_called_once()


@pytest.mark.asyncio
async def test_approved_address_is_fixed_until_updated(client, photos, auth_headers_adrian):
    await client.post("/api/images/1/address", headers=auth_headers_adrian)
    await _set_title(1, "Heron at Dawn")

    # A title edit alone leaves the address alone, but offers the new form
    info = (await client.get("/api/images/1", headers=auth_headers_adrian)).json()["address"]
    assert info["address"] == "adrian-test-image"
    assert info["from_title"] == "heron-at-dawn"

    # Updating moves it; the old address keeps working as a redirect
    await client.post("/api/images/1/address", headers=auth_headers_adrian)
    assert await _redirects() == [("adrian-test-image", 1)]
    # Temporary: a former address can become current again (no cached loops)
    old = await client.get("/photo/adrian-test-image", headers=ADRIAN_SITE)
    assert old.status_code == 302
    assert old.headers["location"] == "/photo/heron-at-dawn"
    assert (await client.get("/photo/heron-at-dawn", headers=ADRIAN_SITE)).status_code == 200


@pytest.mark.asyncio
async def test_approving_again_changes_nothing(client, photos, auth_headers_adrian):
    await client.post("/api/images/1/address", headers=auth_headers_adrian)
    await client.post("/api/images/1/address", headers=auth_headers_adrian)
    assert await _redirects() == []


@pytest.mark.asyncio
async def test_returning_to_a_former_address_reclaims_it(client, photos, auth_headers_adrian):
    await client.post("/api/images/1/address", headers=auth_headers_adrian)
    await _set_title(1, "Heron at Dawn")
    await client.post("/api/images/1/address", headers=auth_headers_adrian)
    await _set_title(1, "Adrian Test Image")
    await client.post("/api/images/1/address", headers=auth_headers_adrian)

    assert await _redirects() == [("heron-at-dawn", 1)]
    assert (await client.get("/photo/adrian-test-image", headers=ADRIAN_SITE)).status_code == 200


@pytest.mark.asyncio
async def test_taken_address_gets_a_number(client, photos, auth_headers_adrian):
    async with get_db_connection() as db:
        await db.execute(
            "INSERT INTO images (id, user_id, filename, slug, title, published, slug_approved) "
            "VALUES (3, 1, 'other.jpg', 'adrian-test-image', 'Adrian Test Image', 1, 1)"
        )
        await db.commit()

    response = await client.post("/api/images/1/address", headers=auth_headers_adrian)
    assert response.json()["address"]["address"] == "adrian-test-image-2"


@pytest.mark.asyncio
async def test_cannot_approve_another_photographers_address(client, photos, auth_headers_liam):
    response = await client.post("/api/images/1/address", headers=auth_headers_liam)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_address_on_the_wrong_site_is_not_found(client, photos, auth_headers_adrian):
    await client.post("/api/images/1/address", headers=auth_headers_adrian)
    response = await client.get(
        "/photo/adrian-test-image", headers={"Host": "liam.hensler.photography"}
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_typed_address_is_normalized_and_used(client, photos, auth_headers_adrian):
    response = await client.post(
        "/api/images/1/address",
        headers=auth_headers_adrian,
        json={"address": "  Dingle Tower, Winter Fog "},
    )
    assert response.status_code == 200
    assert response.json()["address"]["address"] == "dingle-tower-winter-fog"
    assert (
        await client.get("/photo/dingle-tower-winter-fog", headers=ADRIAN_SITE)
    ).status_code == 200


@pytest.mark.asyncio
async def test_typed_address_taken_by_another_photo_is_refused(client, photos, auth_headers_adrian):
    async with get_db_connection() as db:
        await db.execute(
            "INSERT INTO images (id, user_id, filename, slug, title, published, slug_approved) "
            "VALUES (3, 1, 'other.jpg', 'heron-at-dawn', 'Heron at Dawn', 1, 1)"
        )
        await db.commit()

    response = await client.post(
        "/api/images/1/address", headers=auth_headers_adrian, json={"address": "Heron at Dawn"}
    )
    assert response.status_code == 409
    info = (await client.get("/api/images/1", headers=auth_headers_adrian)).json()["address"]
    assert info["approved"] is False


@pytest.mark.asyncio
async def test_changing_an_approved_address_by_typing(client, photos, auth_headers_adrian):
    await client.post("/api/images/1/address", headers=auth_headers_adrian)
    await client.post(
        "/api/images/1/address", headers=auth_headers_adrian, json={"address": "boardwalk"}
    )

    assert await _redirects() == [("adrian-test-image", 1)]
    old = await client.get("/photo/adrian-test-image", headers=ADRIAN_SITE)
    assert old.headers["location"] == "/photo/boardwalk"


@pytest.mark.asyncio
async def test_typed_address_rejects_bad_input(client, photos, auth_headers_adrian):
    for body in ({"address": 42}, {"address": "x" * 201}):
        response = await client.post(
            "/api/images/1/address", headers=auth_headers_adrian, json=body
        )
        assert response.status_code == 400
    # Nothing usable typed: falls back to the title, and digits never pass as an id
    response = await client.post(
        "/api/images/1/address", headers=auth_headers_adrian, json={"address": "2026"}
    )
    assert response.json()["address"]["address"] == "photo-2026"

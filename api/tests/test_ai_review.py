"""
AI-review semantics (ADR 0004): AI-drafted fields stay marked until a human
edits them or explicitly approves them. Saving unchanged text, or
publishing, is not approval.
"""

import pytest

from api.database import get_db_connection

FLAG_COLUMNS = (
    "ai_generated_title",
    "ai_generated_caption",
    "ai_generated_description",
    "ai_generated_alt_text",
    "ai_generated_tags",
    "ai_generated_category",
)


async def _mark_all_ai(image_id: int, **values):
    """Give an image AI-drafted text with every provenance flag set."""
    defaults = {
        "title": "Heron at Dawn",
        "caption": "A heron stands in still water.",
        "alt_text": "A grey heron standing in shallow water.",
        "tags": "heron,marsh",
        "category": "wildlife",
    }
    defaults.update(values)
    async with get_db_connection() as db:
        await db.execute(
            f"""UPDATE images SET title = ?, caption = ?, alt_text = ?, tags = ?, category = ?,
                {', '.join(f'{c} = 1' for c in FLAG_COLUMNS)} WHERE id = ?""",
            (*defaults.values(), image_id),
        )
        await db.commit()


async def _flags(image_id: int) -> dict:
    async with get_db_connection() as db:
        cursor = await db.execute(
            f"SELECT {', '.join(FLAG_COLUMNS)} FROM images WHERE id = ?", (image_id,)
        )
        row = await cursor.fetchone()
    return {c.removeprefix("ai_generated_"): v for c, v in zip(FLAG_COLUMNS, row)}


@pytest.mark.asyncio
async def test_saving_unchanged_text_keeps_ai_flags(client, auth_headers_adrian):
    await _mark_all_ai(1)

    # A form save sends every field, unchanged (trailing whitespace ignored)
    response = await client.patch(
        "/api/images/1",
        headers=auth_headers_adrian,
        json={
            "title": "Heron at Dawn ",
            "caption": "A heron stands in still water.",
            "alt_text": "A grey heron standing in shallow water.",
            "tags": "heron,marsh",
            "category": "wildlife",
        },
    )

    assert response.status_code == 200
    assert all(v == 1 for v in (await _flags(1)).values())


@pytest.mark.asyncio
async def test_editing_a_field_clears_only_that_flag(client, auth_headers_adrian):
    await _mark_all_ai(1)

    response = await client.patch(
        "/api/images/1",
        headers=auth_headers_adrian,
        json={"title": "Heron at Dawn", "caption": "A heron waits on the Northwest Arm."},
    )

    assert response.status_code == 200
    flags = await _flags(1)
    assert flags["caption"] == 0
    assert flags["title"] == 1
    assert flags["alt_text"] == 1


@pytest.mark.asyncio
async def test_publishing_does_not_approve(client, auth_headers_adrian):
    await _mark_all_ai(1)

    response = await client.post("/api/images/1/publish?published=true", headers=auth_headers_adrian)

    assert response.status_code == 200
    assert all(v == 1 for v in (await _flags(1)).values())


@pytest.mark.asyncio
async def test_approve_without_body_clears_every_flag(client, auth_headers_adrian):
    await _mark_all_ai(1)

    response = await client.post("/api/images/1/approve", headers=auth_headers_adrian)

    assert response.status_code == 200
    assert all(v == 0 for v in (await _flags(1)).values())


@pytest.mark.asyncio
async def test_approve_selected_fields(client, auth_headers_adrian):
    await _mark_all_ai(1)

    response = await client.post(
        "/api/images/1/approve", headers=auth_headers_adrian, json={"fields": ["alt_text"]}
    )

    assert response.status_code == 200
    flags = await _flags(1)
    assert flags["alt_text"] == 0
    assert flags["caption"] == 1


@pytest.mark.asyncio
async def test_approve_rejects_unknown_fields(client, auth_headers_adrian):
    await _mark_all_ai(1)

    response = await client.post(
        "/api/images/1/approve", headers=auth_headers_adrian, json={"fields": ["published"]}
    )

    assert response.status_code == 400
    assert all(v == 1 for v in (await _flags(1)).values())


@pytest.mark.asyncio
async def test_approve_other_photographers_image_is_not_found(client, auth_headers_liam):
    await _mark_all_ai(1)

    response = await client.post("/api/images/1/approve", headers=auth_headers_liam)

    assert response.status_code == 404
    assert all(v == 1 for v in (await _flags(1)).values())


@pytest.mark.asyncio
async def test_list_reports_needs_review(client, auth_headers_adrian):
    await _mark_all_ai(1)

    listed = (await client.get("/api/images/list?user_id=1", headers=auth_headers_adrian)).json()
    assert listed["images"][0]["needs_review"] is True

    await client.post("/api/images/1/approve", headers=auth_headers_adrian)

    listed = (await client.get("/api/images/list?user_id=1", headers=auth_headers_adrian)).json()
    assert listed["images"][0]["needs_review"] is False

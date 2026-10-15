"""
The tagging call on Claude Sonnet 5.5, with the API client mocked: request
settings, reading the reply by block type (thinking comes first), stopping
on a refusal or a cut-off reply, and cost from the model that answered.
"""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from PIL import Image

from api.services import claude_vision

METADATA = {
    "title": "Heron at Dawn",
    "caption": "A heron waits in still water.",
    "description": "A grey heron stands in shallow water at first light.",
    "alt_text": "A grey heron standing in shallow water at sunrise.",
    "tags": ["heron", "marsh"],
    "category": "wildlife",
}


def _reply(text=None, stop_reason="end_turn", model="claude-sonnet-5-5", category=None):
    content = [SimpleNamespace(type="thinking", thinking="")]
    if text is not None:
        content.append(SimpleNamespace(type="text", text=text))
    return SimpleNamespace(
        content=content,
        stop_reason=stop_reason,
        stop_details=SimpleNamespace(category=category) if category else None,
        model=model,
        usage=SimpleNamespace(input_tokens=2000, output_tokens=500),
    )


@pytest.fixture(autouse=True)
async def clear_ai_costs(test_db):
    """analyze_image logs to ai_costs, which references users; clear it so the
    shared test_db reset can delete users afterwards."""
    from api.database import get_db_connection

    yield
    async with get_db_connection() as db:
        await db.execute("DELETE FROM ai_costs")
        await db.commit()


@pytest.fixture
def photo(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    path = tmp_path / "heron.jpg"
    Image.new("RGB", (64, 48), "grey").save(path)
    return str(path)


async def _analyze(photo, reply):
    create = AsyncMock(return_value=reply)
    client = SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(create=create)))
    with patch.object(claude_vision.anthropic, "AsyncAnthropic", return_value=client):
        result = await claude_vision.analyze_image(photo, user_id=1)
    return result, create


@pytest.mark.asyncio
async def test_request_settings_and_reply_after_thinking_block(test_db, photo):
    (metadata, error), create = await _analyze(photo, _reply(json.dumps(METADATA)))

    assert error is None
    assert metadata["alt_text"] == METADATA["alt_text"]
    kwargs = create.call_args.kwargs
    assert kwargs["model"] == "claude-sonnet-5-5"
    assert kwargs["output_config"] == {"effort": "medium"}
    assert kwargs["fallbacks"] == "default"
    assert kwargs["max_tokens"] >= 16000
    assert "thinking" not in kwargs  # disabled thinking is a 400 on this model


@pytest.mark.asyncio
@pytest.mark.parametrize("stop_reason", ["refusal", "max_tokens"])
async def test_stopped_reply_is_an_error_not_parsed(test_db, photo, stop_reason):
    (metadata, error), _ = await _analyze(
        photo, _reply(None, stop_reason=stop_reason, category="general_harms")
    )

    assert error is not None
    assert metadata["caption"] == "AI analysis unavailable"
    assert metadata["alt_text"] == ""  # never the fallback caption


@pytest.mark.asyncio
async def test_cost_uses_the_model_that_answered(test_db, photo):
    from api.database import get_db_connection

    await _analyze(photo, _reply(json.dumps(METADATA), model="claude-sonnet-5"))

    async with get_db_connection() as db:
        row = await (
            await db.execute("SELECT model, cost_usd FROM ai_costs ORDER BY id DESC LIMIT 1")
        ).fetchone()
    assert row[0] == "claude-sonnet-5"
    assert row[1] == pytest.approx(2000 / 1e6 * 2.00 + 500 / 1e6 * 10.00)

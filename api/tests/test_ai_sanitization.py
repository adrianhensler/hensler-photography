"""
Tests for server-side sanitization of AI-generated text (api/sanitize.py).

AI-generated title/caption/tags/category come from Claude Vision and were
previously only checked for "field present", then stored as-is. These tests
verify that HTML/script content and dangerous URI schemes never survive
sanitization before persistence to the database.
"""

from api.sanitize import strip_html, sanitize_ai_metadata


class TestStripHtml:
    def test_removes_script_tags_and_keeps_text(self):
        result = strip_html("<script>alert(1)</script>Sunset over mountains")
        assert "<script>" not in result
        assert "</script>" not in result
        assert "Sunset over mountains" in result

    def test_removes_event_handler_attributes(self):
        result = strip_html('<img src=x onerror="alert(1)">Nice photo')
        assert "onerror" not in result
        assert "<img" not in result
        assert "Nice photo" in result

    def test_removes_nested_obfuscated_tags(self):
        result = strip_html("<scr<script>ipt>alert(1)</scr</script>ipt>")
        # No real tag should survive (a stray literal ">" left over from the
        # obfuscated payload, with no matching "<", cannot form a tag).
        assert "<script" not in result.lower()
        assert "<" not in result

    def test_removes_javascript_uri_scheme(self):
        result = strip_html("javascript:alert(1)")
        assert "javascript:" not in result.lower()

    def test_removes_javascript_uri_with_whitespace_obfuscation(self):
        result = strip_html("java\tscript:alert(1)")
        assert "script:" not in result.lower()

    def test_plain_text_is_unaffected(self):
        text = "A perfectly normal caption, with punctuation!"
        assert strip_html(text) == text

    def test_handles_empty_and_none_like_values(self):
        assert strip_html("") == ""

    def test_strips_control_characters(self):
        result = strip_html("Golden\x00hour\x1flight")
        assert "\x00" not in result
        assert "\x1f" not in result


class TestSanitizeAiMetadata:
    def test_sanitizes_all_text_fields(self):
        metadata = {
            "title": "<b>Bold</b> Title",
            "caption": "<script>alert(1)</script>A caption",
            "description": "<i>Italic</i> description",
            "alt_text": "<img onerror=alert(1)>alt text",
            "category": "<span>landscape</span>",
            "tags": ["<i>tag1</i>", "tag2"],
        }

        sanitized = sanitize_ai_metadata(metadata)

        assert sanitized["title"] == "Bold Title"
        assert "<script>" not in sanitized["caption"]
        assert sanitized["description"] == "Italic description"
        assert "onerror" not in sanitized["alt_text"]
        assert sanitized["category"] == "landscape"
        assert sanitized["tags"] == ["tag1", "tag2"]

    def test_sanitizes_comma_separated_tag_string(self):
        metadata = {"tags": "<b>nature</b>, <script>x</script>wildlife"}
        sanitized = sanitize_ai_metadata(metadata)
        assert "<b>" not in sanitized["tags"]
        assert "<script>" not in sanitized["tags"]

    def test_leaves_non_string_and_missing_fields_untouched(self):
        metadata = {"title": "Clean title"}
        sanitized = sanitize_ai_metadata(metadata)
        assert sanitized == {"title": "Clean title"}

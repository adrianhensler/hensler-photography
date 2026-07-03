"""
Server-side sanitization for AI-generated text fields.

Claude Vision returns free-form text (title, caption, description, alt_text,
tags, category) that gets written directly into the database and later
rendered on the public sites and in the management UI. The only prior XSS
protection was client-side escaping (escapeHtml() in sites/shared/gallery.js)
applied at render time — nothing prevented HTML/script content from being
*stored*, which meant every future renderer of this data (templates, APIs,
exports, etc.) had to remember to escape it correctly.

This module strips all HTML markup from AI-returned text server-side, before
persistence, as defense in depth. These fields are plain-text metadata and
never need to contain markup, so stripping is safe and simple — no HTML
allowlist is required.

No new third-party dependency is introduced (the project has no HTML
sanitization library such as `bleach` in api/requirements.txt, and adding one
requires approval per CLAUDE.md's "no new dependencies" rule). This uses only
the Python standard library.
"""

import re
from html.parser import HTMLParser
from typing import Any


class _TagStripper(HTMLParser):
    """Extracts only the text content of a string, discarding all tags.

    Using HTMLParser (rather than a regex) correctly tokenizes malformed or
    obfuscated markup (e.g. "<scr<script>ipt>") instead of naively matching
    "<...>" pairs, which is easy to bypass with nested/broken tags.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []

    def handle_data(self, data: str) -> None:
        self._chunks.append(data)

    def get_text(self) -> str:
        return "".join(self._chunks)


# Matches javascript:, data:, and vbscript: URI schemes anywhere in the
# string (case-insensitive), including with whitespace/control-character
# obfuscation between characters (e.g. "java\tscript:").
_DANGEROUS_URI_SCHEME_RE = re.compile(
    r"j\s*a\s*v\s*a\s*s\s*c\s*r\s*i\s*p\s*t\s*:|data\s*:|vbscript\s*:",
    re.IGNORECASE,
)

# Strips control characters (other than common whitespace) that have no
# legitimate use in display metadata.
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def strip_html(value: str) -> str:
    """Remove all HTML markup and dangerous URI schemes from a string.

    Repeatedly strips tags until the output is stable, so that obfuscated or
    nested payloads (e.g. "<scr<script>ipt>alert(1)</scr</script>ipt>")
    cannot survive a single pass.
    """
    if not value:
        return value

    text = value
    for _ in range(5):
        parser = _TagStripper()
        parser.feed(text)
        parser.close()
        stripped = parser.get_text()
        if stripped == text:
            break
        text = stripped

    text = _DANGEROUS_URI_SCHEME_RE.sub("", text)
    text = _CONTROL_CHARS_RE.sub("", text)
    return text.strip()


def sanitize_ai_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Sanitize the free-text fields of an AI-generated metadata dict in place.

    Applies strip_html() to each known plain-text field. `tags` may be a
    list of strings or a comma-separated string; each individual tag is
    sanitized. Unknown fields and non-string values are left untouched.
    """
    text_fields = ("title", "caption", "description", "alt_text", "category")

    for field in text_fields:
        value = metadata.get(field)
        if isinstance(value, str):
            metadata[field] = strip_html(value)

    tags = metadata.get("tags")
    if isinstance(tags, list):
        metadata["tags"] = [
            strip_html(tag) if isinstance(tag, str) else tag for tag in tags
        ]
    elif isinstance(tags, str):
        metadata["tags"] = strip_html(tags)

    return metadata

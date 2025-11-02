"""
Claude Vision API integration for AI-powered image analysis

Enhanced with structured error handling for both humans and AI assistants.
"""
import anthropic
import base64
import os
import json
import traceback
from pathlib import Path
from typing import Dict, Any, Tuple

from api.errors import (
    ErrorResponse,
    missing_api_key_error,
    invalid_api_key_error,
    rate_limit_error,
    claude_api_error
)
from api.logging_config import get_logger

# Initialize logger
logger = get_logger(__name__)


async def analyze_image(image_path: str, user_id: int = None, filename: str = None) -> Tuple[Dict[str, Any], ErrorResponse | None]:
    """
    Analyze an image using Claude Vision API.

    Returns:
        Tuple of (metadata_dict, error_response)
        - If successful: (metadata, None)
        - If error: (fallback_metadata, ErrorResponse)

    This allows the caller to decide whether to fail hard or use fallback.
    """
    context = {
        "image_path": image_path,
        "user_id": user_id,
        "filename": filename or Path(image_path).name
    }

    # Check API key
    api_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        logger.warning(
            "Claude API key not configured - AI features unavailable",
            extra={"context": context, "error_code": "AUTH_MISSING_KEY"}
        )

        fallback = _get_fallback_metadata(image_path)
        error = missing_api_key_error(context=context)
        return fallback, error

    try:
        # Read and encode image
        with open(image_path, "rb") as img_file:
            image_data = base64.standard_b64encode(img_file.read()).decode("utf-8")

        # Determine media type
        ext = Path(image_path).suffix.lower()
        media_type_map = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.webp': 'image/webp'
        }
        media_type = media_type_map.get(ext, 'image/jpeg')

        logger.info(
            f"Analyzing image with Claude Vision API",
            extra={"context": {**context, "media_type": media_type, "image_size_kb": len(image_data) / 1024}}
        )

        # Initialize Claude client
        client = anthropic.Anthropic(api_key=api_key)

        # Craft photography-aware prompt
        prompt = """You are an expert photography curator analyzing this image for a professional photography portfolio.

Provide a JSON response with the following fields:

{
  "title": "A short, compelling title (3-8 words)",
  "caption": "A 1-2 sentence caption describing the scene, mood, or story",
  "description": "A detailed description (2-3 sentences) covering composition, lighting, technical aspects, and emotional impact",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "category": "one of: landscape, portrait, street, nature, architecture, abstract, wildlife, urban, night, or other"
}

Guidelines:
- Title should be evocative and professional, not generic
- Caption should tell a story or highlight what makes this image special
- Tags should include: subject matter, mood/emotion, technical style, color palette, time of day
- Category should be the primary genre this fits into
- Write in a sophisticated, gallery-quality tone

Return ONLY valid JSON, no other text."""

        # Call Claude Vision API
        message = client.messages.create(
            model="claude-3-opus-20240229",  # Using Claude 3 Opus
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ],
                }
            ],
        )

        # Parse response
        response_text = message.content[0].text.strip()

        # Extract JSON from response (Claude sometimes adds markdown formatting)
        if response_text.startswith("```json"):
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif response_text.startswith("```"):
            response_text = response_text.split("```")[1].split("```")[0].strip()

        try:
            metadata = json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(
                f"Failed to parse Claude response as JSON: {e}",
                exc_info=e,
                extra={
                    "context": {**context, "response_text": response_text[:500]},
                    "error_code": "PROCESSING_AI_FAILED"
                }
            )

            fallback = _get_fallback_metadata(image_path)
            error = claude_api_error(
                error_message=f"Failed to parse AI response as JSON: {str(e)}",
                context={**context, "response_preview": response_text[:200]},
                stack_trace=traceback.format_exc()
            )
            return fallback, error

        # Ensure tags is a list
        if isinstance(metadata.get('tags'), str):
            metadata['tags'] = [tag.strip() for tag in metadata['tags'].split(',')]

        # Validate required fields
        required_fields = ['title', 'caption', 'description', 'tags', 'category']
        for field in required_fields:
            if field not in metadata:
                logger.warning(
                    f"Claude response missing required field: {field}",
                    extra={"context": context}
                )
                metadata[field] = "" if field != 'tags' else []

        logger.info(
            f"Successfully analyzed image with Claude Vision",
            extra={
                "context": {
                    **context,
                    "title": metadata.get('title'),
                    "category": metadata.get('category'),
                    "tag_count": len(metadata.get('tags', []))
                }
            }
        )

        return metadata, None  # Success!

    except anthropic.AuthenticationError as e:
        logger.error(
            f"Claude API authentication failed: {e}",
            exc_info=e,
            extra={"context": context, "error_code": "AUTH_INVALID_KEY"}
        )

        fallback = _get_fallback_metadata(image_path)
        error = invalid_api_key_error(context=context)
        return fallback, error

    except anthropic.RateLimitError as e:
        logger.warning(
            f"Claude API rate limit exceeded: {e}",
            extra={"context": context, "error_code": "RATE_CLAUDE_LIMIT"}
        )

        fallback = _get_fallback_metadata(image_path)
        error = rate_limit_error(retry_after=60, context=context)
        return fallback, error

    except anthropic.APIError as e:
        logger.error(
            f"Claude API error: {e}",
            exc_info=e,
            extra={"context": context, "error_code": "EXTERNAL_CLAUDE_ERROR"}
        )

        fallback = _get_fallback_metadata(image_path)
        error = claude_api_error(
            error_message=str(e),
            context=context,
            stack_trace=traceback.format_exc()
        )
        return fallback, error

    except Exception as e:
        logger.error(
            f"Unexpected error during image analysis: {e}",
            exc_info=e,
            extra={"context": context, "error_code": "PROCESSING_AI_FAILED"}
        )

        fallback = _get_fallback_metadata(image_path)
        error = claude_api_error(
            error_message=f"Unexpected error: {str(e)}",
            context=context,
            stack_trace=traceback.format_exc()
        )
        return fallback, error


def _get_fallback_metadata(image_path: str) -> Dict[str, Any]:
    """Generate basic fallback metadata from filename"""
    return {
        "title": Path(image_path).stem.replace('_', ' ').replace('-', ' ').title(),
        "caption": "AI analysis unavailable",
        "description": "",
        "tags": [],
        "category": "uncategorized"
    }

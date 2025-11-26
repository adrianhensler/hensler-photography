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
    claude_api_error,
)
from api.logging_config import get_logger
from api.services.image_processor import generate_ai_analysis_image, cleanup_temp_file

# Initialize logger
logger = get_logger(__name__)


def get_analysis_prompt(style: str = "balanced") -> str:
    """
    Get AI analysis prompt based on photographer's preferred style.

    Args:
        style: One of 'technical', 'artistic', 'documentary', or 'balanced'

    Returns:
        Prompt string for Claude Vision API
    """
    prompts = {
        "technical": """You are a technical photography analyst with expertise in composition, lighting, and camera techniques.

Provide a JSON response with the following fields:

{
  "title": "A descriptive, factual title (3-8 words)",
  "caption": "A 1-2 sentence description focusing on what is actually in the image and how it was captured",
  "description": "A detailed technical analysis (2-3 sentences) covering composition, lighting setup, technical execution, and photographic techniques used",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "category": "one of: landscape, portrait, street, nature, architecture, abstract, wildlife, urban, night, or other"
}

Guidelines:
- Title should be direct and descriptive (e.g., "Foggy Valley at Dawn" not "Whispers of Morning Mist")
- Caption should describe what is actually visible and the capture conditions
- Description should read like a photographer explaining their work to another photographer
- Focus on: composition techniques, lighting quality, exposure decisions, depth of field choices
- Tags should include: subject matter, lighting conditions, compositional technique, equipment used (if apparent), time of day
- Write in a grounded, technical tone focused on photographic craft

Return ONLY valid JSON, no other text.""",
        "artistic": """You are an expert photography curator analyzing this image for a fine art gallery.

Provide a JSON response with the following fields:

{
  "title": "A short, evocative title (3-8 words)",
  "caption": "A 1-2 sentence caption describing the mood, emotion, or story",
  "description": "A detailed description (2-3 sentences) covering the narrative, emotional impact, and artistic vision",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "category": "one of: landscape, portrait, street, nature, architecture, abstract, wildlife, urban, night, or other"
}

Guidelines:
- Title should be evocative and poetic (e.g., "Whispers of Morning Mist" or "Solitude's Embrace")
- Caption should tell a story or evoke an emotional response
- Description should explore the mood, atmosphere, and artistic intent
- Focus on: emotional resonance, symbolism, narrative elements, aesthetic qualities
- Tags should include: mood/emotion, artistic style, color palette, thematic elements, atmosphere
- Write in a sophisticated, gallery-quality tone that elevates the artistic vision

Return ONLY valid JSON, no other text.""",
        "documentary": """You are a documentary photography expert analyzing this image for journalistic or educational purposes.

Provide a JSON response with the following fields:

{
  "title": "A clear, informative title (3-8 words)",
  "caption": "A 1-2 sentence factual description of what is shown",
  "description": "A detailed objective description (2-3 sentences) covering the subject matter, context, and relevant details",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "category": "one of: landscape, portrait, street, nature, architecture, abstract, wildlife, urban, night, or other"
}

Guidelines:
- Title should be clear and informative (e.g., "Street Market in Morning Light" or "Urban Cyclist at Intersection")
- Caption should state facts about what is depicted
- Description should provide context and relevant information about the subject
- Focus on: what is shown, where it might be, when (time of day/season), who/what is the subject
- Tags should include: subject matter, location type, activity shown, documentary genre, contextual details
- Write in a neutral, journalistic tone focused on accuracy and information

Return ONLY valid JSON, no other text.""",
        "balanced": """You are an experienced photography expert analyzing this image for a professional portfolio.

Provide a JSON response with the following fields:

{
  "title": "A compelling, descriptive title (3-8 words)",
  "caption": "A 1-2 sentence caption balancing what is shown with how it makes viewers feel",
  "description": "A detailed description (2-3 sentences) covering both technical execution and artistic qualities",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "category": "one of: landscape, portrait, street, nature, architecture, abstract, wildlife, urban, night, or other"
}

Guidelines:
- Title should be both descriptive and engaging
- Caption should describe the scene while acknowledging its mood or appeal
- Description should balance technical observations (lighting, composition) with artistic qualities (mood, impact)
- Focus on: what makes the image work both technically and aesthetically
- Tags should include: subject matter, mood, technical aspects, compositional elements, time of day
- Write in a professional tone that respects both craft and creativity

Return ONLY valid JSON, no other text.""",
    }

    # Default to balanced if invalid style provided
    return prompts.get(style, prompts["balanced"])


async def analyze_image(
    image_path: str,
    user_id: int = None,
    filename: str = None,
    media_type: str = None,
    style: str = "balanced",
) -> Tuple[Dict[str, Any], ErrorResponse | None]:
    """
    Analyze an image using Claude Vision API.

    Args:
        image_path: Path to the image file
        user_id: User ID for context
        filename: Filename for context
        media_type: MIME type of image (e.g., 'image/jpeg', 'image/png'). If not provided, will guess from extension.
        style: AI analysis style - 'technical', 'artistic', 'documentary', or 'balanced' (default)

    Returns:
        Tuple of (metadata_dict, error_response)
        - If successful: (metadata, None)
        - If error: (fallback_metadata, ErrorResponse)

    This allows the caller to decide whether to fail hard or use fallback.
    """
    context = {
        "image_path": image_path,
        "user_id": user_id,
        "filename": filename or Path(image_path).name,
    }

    # Check API key
    api_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        logger.warning(
            "Claude API key not configured - AI features unavailable",
            extra={"context": context, "error_code": "AUTH_MISSING_KEY"},
        )

        fallback = _get_fallback_metadata(image_path)
        error = missing_api_key_error(context=context)
        return fallback, error

    # Track whether we need to cleanup a temp file (initialize before try block)
    needs_cleanup = False
    ai_image_path = image_path  # Default to original

    try:
        # Generate appropriately-sized image for AI analysis (max 1568px per Anthropic recommendation)
        ai_image_path, resize_error = generate_ai_analysis_image(image_path, context=context)

        # Log if resize had issues but continue with original
        if resize_error:
            logger.warning(
                f"AI image resize failed, using original: {resize_error.error.message}",
                extra={"context": context},
            )

        # Track if we created a temp file that needs cleanup
        needs_cleanup = ai_image_path != image_path

        # Read and encode image (either temp resized or original)
        with open(ai_image_path, "rb") as img_file:
            image_data = base64.standard_b64encode(img_file.read()).decode("utf-8")

        # Determine media type (use provided, or guess from extension)
        if not media_type:
            ext = Path(image_path).suffix.lower()
            media_type_map = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".webp": "image/webp",
            }
            media_type = media_type_map.get(ext, "image/jpeg")

        logger.info(
            "Analyzing image with Claude Vision API",
            extra={
                "context": {
                    **context,
                    "media_type": media_type,
                    "image_size_kb": len(image_data) / 1024,
                    "using_temp_image": needs_cleanup,
                }
            },
        )

        # Initialize Claude client
        client = anthropic.Anthropic(api_key=api_key)

        # Get analysis prompt based on photographer's style preference
        prompt = get_analysis_prompt(style)

        logger.info(f"Using AI style: {style}", extra={"context": {**context, "ai_style": style}})

        # Call Claude Vision API
        model_name = "claude-3-opus-20240229"
        message = client.messages.create(
            model=model_name,
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
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        )

        # Calculate API cost
        input_tokens = message.usage.input_tokens
        output_tokens = message.usage.output_tokens

        # Claude 3 Opus pricing (as of 2024)
        input_cost_per_mtok = 15.00  # $15 per 1M input tokens
        output_cost_per_mtok = 75.00  # $75 per 1M output tokens

        cost_usd = (input_tokens / 1_000_000) * input_cost_per_mtok + (
            output_tokens / 1_000_000
        ) * output_cost_per_mtok

        logger.info(
            f"Claude API call completed: {input_tokens} input tokens, {output_tokens} output tokens, ${cost_usd:.4f}",
            extra={
                "context": {
                    **context,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "cost_usd": cost_usd,
                }
            },
        )

        # Log cost to database (async, don't block on failure)
        try:
            from api.database import get_db_connection

            async with get_db_connection() as db:
                await db.execute(
                    """
                    INSERT INTO ai_costs (
                        user_id, operation, model, input_tokens, output_tokens, cost_usd, image_path
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        user_id,
                        "analyze_image",
                        model_name,
                        input_tokens,
                        output_tokens,
                        cost_usd,
                        image_path,
                    ),
                )
                await db.commit()
        except Exception as e:
            logger.warning(f"Failed to log AI cost: {e}", extra={"context": context})

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
                    "error_code": "PROCESSING_AI_FAILED",
                },
            )

            fallback = _get_fallback_metadata(image_path)
            error = claude_api_error(
                error_message=f"Failed to parse AI response as JSON: {str(e)}",
                context={**context, "response_preview": response_text[:200]},
                stack_trace=traceback.format_exc(),
            )
            return fallback, error

        # Ensure tags is a list
        if isinstance(metadata.get("tags"), str):
            metadata["tags"] = [tag.strip() for tag in metadata["tags"].split(",")]

        # Validate required fields
        required_fields = ["title", "caption", "description", "tags", "category"]
        for field in required_fields:
            if field not in metadata:
                logger.warning(
                    f"Claude response missing required field: {field}", extra={"context": context}
                )
                metadata[field] = "" if field != "tags" else []

        logger.info(
            "Successfully analyzed image with Claude Vision",
            extra={
                "context": {
                    **context,
                    "title": metadata.get("title"),
                    "category": metadata.get("category"),
                    "tag_count": len(metadata.get("tags", [])),
                }
            },
        )

        return metadata, None  # Success!

    except anthropic.AuthenticationError as e:
        logger.error(
            f"Claude API authentication failed: {e}",
            exc_info=e,
            extra={"context": context, "error_code": "AUTH_INVALID_KEY"},
        )

        fallback = _get_fallback_metadata(image_path)
        error = invalid_api_key_error(context=context)
        return fallback, error

    except anthropic.RateLimitError as e:
        logger.warning(
            f"Claude API rate limit exceeded: {e}",
            extra={"context": context, "error_code": "RATE_CLAUDE_LIMIT"},
        )

        fallback = _get_fallback_metadata(image_path)
        error = rate_limit_error(retry_after=60, context=context)
        return fallback, error

    except anthropic.APIError as e:
        logger.error(
            f"Claude API error: {e}",
            exc_info=e,
            extra={"context": context, "error_code": "EXTERNAL_CLAUDE_ERROR"},
        )

        fallback = _get_fallback_metadata(image_path)
        error = claude_api_error(
            error_message=str(e), context=context, stack_trace=traceback.format_exc()
        )
        return fallback, error

    except Exception as e:
        logger.error(
            f"Unexpected error during image analysis: {e}",
            exc_info=e,
            extra={"context": context, "error_code": "PROCESSING_AI_FAILED"},
        )

        fallback = _get_fallback_metadata(image_path)
        error = claude_api_error(
            error_message=f"Unexpected error: {str(e)}",
            context=context,
            stack_trace=traceback.format_exc(),
        )
        return fallback, error

    finally:
        # Clean up temporary AI analysis file if one was created
        if needs_cleanup:
            cleanup_temp_file(ai_image_path, context=context)


def _get_fallback_metadata(image_path: str) -> Dict[str, Any]:
    """Generate basic fallback metadata from filename"""
    return {
        "title": Path(image_path).stem.replace("_", " ").replace("-", " ").title(),
        "caption": "AI analysis unavailable",
        "description": "",
        "tags": [],
        "category": "uncategorized",
    }

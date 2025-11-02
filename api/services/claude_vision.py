"""
Claude Vision API integration for AI-powered image analysis
"""
import anthropic
import base64
import os
from pathlib import Path


async def analyze_image(image_path: str) -> dict:
    """
    Analyze an image using Claude Vision API

    Returns structured metadata:
    - title: Short descriptive title
    - caption: 1-2 sentence caption
    - description: Detailed description
    - tags: List of relevant tags
    - category: Primary category
    """

    api_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        # Return empty metadata if no API key configured
        return {
            "title": Path(image_path).stem.replace('_', ' ').replace('-', ' ').title(),
            "caption": "No caption available",
            "description": "",
            "tags": [],
            "category": "uncategorized"
        }

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
        # Note: Using Claude 3 Opus - upgrade API key for Claude 3.5 access
        message = client.messages.create(
            model="claude-3-opus-20240229",
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

        # Extract JSON from response (sometimes Claude adds markdown formatting)
        if response_text.startswith("```json"):
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif response_text.startswith("```"):
            response_text = response_text.split("```")[1].split("```")[0].strip()

        import json
        metadata = json.loads(response_text)

        # Ensure tags is a list
        if isinstance(metadata.get('tags'), str):
            metadata['tags'] = [tag.strip() for tag in metadata['tags'].split(',')]

        return metadata

    except Exception as e:
        print(f"Claude Vision error: {e}")

        # Fallback to basic metadata
        return {
            "title": Path(image_path).stem.replace('_', ' ').replace('-', ' ').title(),
            "caption": "AI analysis unavailable",
            "description": "",
            "tags": [],
            "category": "uncategorized"
        }

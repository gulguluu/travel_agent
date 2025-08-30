#!/usr/bin/env python3
"""
OpenAI client utilities for the travel agent.
Provides a shared OpenAI client for AI-powered tools.
"""

import base64
import json
from pathlib import Path

import openai

from config import Config

_openai_client = None


def get_openai_client():
    """Get the shared OpenAI client instance."""
    global _openai_client
    if _openai_client is None:
        # Use OpenRouter if available, otherwise use OpenAI directly
        if Config.OPENROUTER_API_KEY and Config.OPENROUTER_API_KEY.startswith("sk-or-"):
            _openai_client = openai.AsyncOpenAI(
                api_key=Config.OPENROUTER_API_KEY,
                base_url="https://openrouter.ai/api/v1",
            )
        elif Config.OPENAI_API_KEY:
            _openai_client = openai.AsyncOpenAI(api_key=Config.OPENAI_API_KEY)
    return _openai_client


def has_openai_client():
    """Check if OpenAI client is available."""
    client = get_openai_client()
    if client is None:
        print(
            f"DEBUG: OpenAI client check failed - OPENAI_API_KEY: {bool(Config.OPENAI_API_KEY)}, OPENROUTER_API_KEY: {bool(Config.OPENROUTER_API_KEY)}"
        )
    return client is not None


async def analyze_image_with_vision(
    image_data: str, prompt: str, image_format: str = "png"
) -> dict:
    """Generic image analysis using OpenAI Vision API.

    Args:
        image_data: Base64 encoded image data or file path
        prompt: Analysis prompt
        image_format: Image format (png, jpg, jpeg)

    Returns:
        Dictionary with analysis results
    """
    client = get_openai_client()
    if not client:
        return {"error": "OpenAI client not available", "success": False}

    try:
        if image_data.startswith("/") or image_data.startswith("./"):
            with open(image_data, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode("utf-8")
        else:
            base64_image = image_data
        if base64_image.startswith("data:image/"):
            base64_image = base64_image.split(",", 1)[1]
        try:
            base64.b64decode(base64_image)
        except Exception:
            return {"error": "Invalid base64 image data", "success": False}

        base64_image = f"data:image/{image_format};base64,{base64_image}"
        response = await client.chat.completions.create(
            model=(
                Config.OPENROUTER_MODEL if Config.OPENROUTER_API_KEY else "gpt-4o-mini"
            ),
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": base64_image}},
                    ],
                }
            ],
            max_tokens=1500,
            temperature=0.1,
        )

        result_text = response.choices[0].message.content.strip()

        return {
            "analysis": result_text,
            "model": (
                Config.OPENROUTER_MODEL if Config.OPENROUTER_API_KEY else "gpt-4o-mini"
            ),
            "success": True,
        }

    except Exception as e:
        return {"error": f"Vision analysis failed: {str(e)}", "success": False}

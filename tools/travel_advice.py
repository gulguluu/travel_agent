#!/usr/bin/env python3
"""
AI-powered tools for the travel agent.
Provides travel advice and itinerary creation using OpenAI.
"""

from mcp.server.fastmcp import FastMCP

from config import Config
from utils.openai_client import get_openai_client, has_openai_client
from utils.prompt_loader import load_prompt


def register_ai_tools(app: FastMCP):
    """Register AI-powered tools with the FastMCP app."""

    @app.tool()
    async def travel_advice(query, context=None):
        """Get intelligent travel advice using an LLM. Provide travel tips, recommendations, and guidance."""
        client = get_openai_client()
        if not client:
            return {
                "error": "OpenAI client not configured. Set OPENROUTER_API_KEY or OPENAI_API_KEY."
            }

        system_prompt = load_prompt("travel_advice_prompt")

        user_prompt = f"Travel query: {query}"
        if context:
            user_prompt += f"\nAdditional context: {context}"

        try:
            response = await client.chat.completions.create(
                model=Config.OPENROUTER_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=500,
                temperature=0.7,
            )

            return {
                "advice": response.choices[0].message.content,
                "model": Config.OPENROUTER_MODEL,
            }
        except Exception as e:
            return {"error": f"Travel advice failed: {e}"}

    @app.tool()
    async def create_itinerary(query, tool_outputs):
        """Synthesizes information from other tools to create a structured travel itinerary. This should be the final step after all other tools have been called."""
        client = get_openai_client()
        if not client:
            return {
                "error": "OpenAI client not configured. Set OPENROUTER_API_KEY or OPENAI_API_KEY."
            }

        system_prompt = load_prompt("itinerary_creation_prompt")
        user_prompt = f"Original user query: '{query}'\n\nTool outputs:\n{tool_outputs}"

        try:
            response = await client.chat.completions.create(
                model=Config.OPENROUTER_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=4096,  # Increased token limit for more detailed itineraries
                temperature=0.2,
            )
            return {"itinerary": response.choices[0].message.content}
        except Exception as e:
            return {"error": f"Failed to create itinerary: {e}"}

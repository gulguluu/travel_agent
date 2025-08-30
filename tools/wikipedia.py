#!/usr/bin/env python3
"""
Wikipedia tool for the travel agent.
Provides Wikipedia summary functionality.
"""

from mcp.server.fastmcp import FastMCP

from utils.geo_utils import geocode_place
from utils.http_client import get_http_client


def register_wikipedia_tool(app: FastMCP):
    """Register the Wikipedia tool with the FastMCP app."""

    async def _wiki_summary_raw(title):
        """Get Wikipedia summary for a given title."""
        client = get_http_client()
        safe = title.replace(" ", "_")
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{safe}"
        r = await client.get(url)
        if r.status_code == 200:
            j = r.json()
            return {
                "title": j.get("title"),
                "extract": j.get("extract"),
                "description": j.get("description"),
                "url": j.get("content_urls", {}).get("desktop", {}).get("page"),
            }
        return None

    @app.tool()
    async def wiki_summary(title_or_place):
        """Get Wikipedia summary for a title or place."""
        s = await _wiki_summary_raw(title_or_place)
        if s:
            return s
        g = await geocode_place(title_or_place)
        if g and g.get("name"):
            s = await _wiki_summary_raw(g["name"])
            if s:
                return s
        return {"error": f"no summary for '{title_or_place}'"}

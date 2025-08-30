#!/usr/bin/env python3
"""
Geocoding tool for the travel agent.
Provides place name to coordinates conversion.
"""

from mcp.server.fastmcp import FastMCP

from utils.geo_utils import geocode_place


def register_geocoding_tool(app: FastMCP):
    """Register the geocoding tool with the FastMCP app."""

    @app.tool()
    async def geocode_place_tool(name):
        """Geocode a place name to get coordinates and location information."""
        result = await geocode_place(name)
        return result or {"error": f"could not geocode '{name}'"}

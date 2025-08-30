#!/usr/bin/env python3
"""
Airport tools for the travel agent.
Provides airport lookup and nearest airport functionality.
"""

from mcp.server.fastmcp import FastMCP

from utils.airports import find_nearest_airports, iata_lookup
from utils.geo_utils import geocode_place, parse_latlon


def register_airport_tools(app: FastMCP):
    """Register airport-related tools with the FastMCP app."""

    @app.tool()
    async def iata_lookup_tool(term, limit=5):
        """
        Guess IATA codes by city/airport name or exact code.
        """
        return await iata_lookup(term, limit)

    @app.tool()
    async def nearest_airports(place_or_latlon, limit=5):
        """Find nearest airports to a place or coordinates."""
        ll = parse_latlon(place_or_latlon)
        if not ll:
            g = await geocode_place(place_or_latlon)
            if not g:
                return [{"error": f"could not geocode '{place_or_latlon}'"}]
            ll = (g["lat"], g["lon"])

        lat, lon = ll
        return find_nearest_airports(lat, lon, limit)

#!/usr/bin/env python3
"""
Weather tool for the travel agent.
Provides weather forecast functionality.
"""

from mcp.server.fastmcp import FastMCP

from config import Config
from utils.geo_utils import geocode_place, parse_latlon
from utils.http_client import get_http_client


def register_weather_tool(app: FastMCP):
    """Register the weather tool with the FastMCP app."""

    async def _weather_daily(lat, lon, days=7):
        """Get weather forecast for given coordinates."""
        client = get_http_client()
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": "weathercode,temperature_2m_max,temperature_2m_min,precipitation_sum",
            "forecast_days": max(1, min(14, int(days))),
            "timezone": "auto",
        }
        r = await client.get(url, params=params)
        return r.json()

    @app.tool()
    async def weather_forecast(place_or_latlon, days=Config.DEFAULT_WEATHER_DAYS):
        """Get weather forecast for a place or coordinates."""
        ll = parse_latlon(place_or_latlon)
        if ll:
            lat, lon = ll
        else:
            g = await geocode_place(place_or_latlon)
            if not g:
                return {"error": f"could not geocode '{place_or_latlon}'"}
            lat, lon = g["lat"], g["lon"]
        return await _weather_daily(lat, lon, days)

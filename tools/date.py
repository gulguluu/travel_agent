#!/usr/bin/env python3
"""
Date tool for the travel agent.
Provides current date functionality.
"""

from mcp.server.fastmcp import FastMCP

from utils.date_utils import get_current_date


def register_date_tool(app: FastMCP):
    """Register the date tool with the FastMCP app."""

    @app.tool()
    async def get_current_date_tool():
        """Returns the current date in YYYY-MM-DD format."""
        return get_current_date()

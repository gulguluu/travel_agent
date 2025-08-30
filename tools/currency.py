#!/usr/bin/env python3
"""
Currency conversion tool for the travel agent.
Provides currency exchange rate functionality.
"""

from mcp.server.fastmcp import FastMCP

from utils.http_client import get_http_client


def register_currency_tool(app: FastMCP):
    """Register the currency conversion tool with the FastMCP app."""

    @app.tool()
    async def currency_convert(amount, from_code, to_code):
        """Convert currency from one code to another."""
        client = get_http_client()
        url = "https://api.exchangerate.host/convert"
        r = await client.get(
            url,
            params={"from": from_code.upper(), "to": to_code.upper(), "amount": amount},
        )
        j = r.json()
        return {
            "query": {
                "amount": amount,
                "from": from_code.upper(),
                "to": to_code.upper(),
            },
            "result": j.get("result"),
            "info": {"rate": (j.get("info") or {}).get("rate")},
        }

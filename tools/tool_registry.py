#!/usr/bin/env python3
"""
Tool registry for the travel agent MCP server.
Centralizes tool registration and management.
"""

from fastmcp.client import Client
from fastmcp.client.transports import StreamableHttpTransport
from mcp.server.fastmcp import FastMCP

from config import Config
from tools.airports import register_airport_tools
from tools.currency import register_currency_tool
from tools.date import register_date_tool
from tools.geocoding import register_geocoding_tool
from tools.memory import register_memory_tool
from tools.sequential_thinking import register_sequential_thinking_tool
from tools.transit import register_transit_tools
from tools.travel_advice import register_ai_tools
from tools.weather import register_weather_tool
from tools.web_search import register_web_search_tool
from tools.wikipedia import register_wikipedia_tool

from .flights import register_flights_tool
from .hotels import register_hotels_tool


def register_all_tools(app: FastMCP):
    """Register all travel agent tools with the FastMCP app."""

    # Essential core tools
    register_web_search_tool(app)  # Basic web search
    register_geocoding_tool(app)  # Location resolution
    register_weather_tool(app)  # Weather info
    register_wikipedia_tool(app)  # Destination information
    register_currency_tool(app)  # Currency conversion
    register_date_tool(app)  # Date/time utilities
    register_airport_tools(app)  # Airport codes/info

    # Main travel search tools (screenshot + vision)
    register_flights_tool(app)
    register_hotels_tool(app)

    # Local transport
    register_transit_tools(app)

    # AI and memory tools
    register_ai_tools(app)
    register_memory_tool(app)
    register_sequential_thinking_tool(app)

    # Enhanced tools
    register_enhanced_tools(app)


def register_enhanced_tools(app: FastMCP):
    """Register enhanced tools for quality assurance and MCP integration."""

    @app.tool()
    def verify_travel_plan(travel_plan):
        """Basic travel plan verification."""
        issues = []
        warnings = []

        # Check flights
        flights = travel_plan.get("flights", [])
        if not flights:
            warnings.append("No flights found in travel plan")
        else:
            for i, flight in enumerate(flights):
                if not flight.get("departure") or not flight.get("arrival"):
                    issues.append(f"Flight {i+1}: Missing departure or arrival")
                if not flight.get("date"):
                    issues.append(f"Flight {i+1}: Missing date")

        # Check accommodations
        accommodations = travel_plan.get("accommodations", [])
        if not accommodations:
            warnings.append("No accommodations found")
        else:
            for i, hotel in enumerate(accommodations):
                if not hotel.get("name") or not hotel.get("location"):
                    issues.append(f"Hotel {i+1}: Missing name or location")

        # Check itinerary
        itinerary = travel_plan.get("itinerary", [])
        if not itinerary:
            warnings.append("No itinerary found")

        status = "failed" if issues else ("warning" if warnings else "passed")

        return {
            "status": status,
            "issues": issues,
            "warnings": warnings,
            "summary": f"Verification {status}: {len(issues)} issues, {len(warnings)} warnings",
        }

    @app.tool()
    def discover_mcp_tools():
        """Discover tools from MCP servers."""
        mcp_servers = Config.get_mcp_servers()
        discovered = {}

        for server_name, server_config in mcp_servers.items():
            if not server_config.get("enabled", True):
                continue

            try:
                # Simple HTTP MCP client discovery
                if server_config.get("transport") == "http":
                    url = server_config.get("url")
                    if url:
                        discovered[server_name] = {
                            "status": "configured",
                            "url": url,
                            "transport": "http",
                            "note": "MCP server configured but discovery requires async context",
                        }
                    else:
                        discovered[server_name] = {
                            "status": "error",
                            "error": "No URL configured",
                        }
                else:
                    discovered[server_name] = {
                        "status": "unsupported",
                        "transport": server_config.get("transport"),
                    }

            except Exception as e:
                discovered[server_name] = {"status": "error", "error": str(e)}

        return {
            "discovered_servers": discovered,
            "total_servers": len(mcp_servers),
            "note": "Full MCP tool discovery requires async initialization",
        }

    @app.tool()
    def manage_workspace_config(action="get", updates=None):
        """Manage workspace configuration."""
        if action == "get":
            config = Config.get_workspace_config()
            return {
                "workspace_config": config,
                "config_location": ".travel_agent/config.json",
            }

        elif action == "update" and updates:
            current_config = Config.get_workspace_config()
            current_config.update(updates)
            Config.save_workspace_config(current_config)

            return {
                "success": True,
                "message": "Workspace configuration updated",
                "updated_config": current_config,
            }

        return {"error": "Invalid action or missing updates parameter"}


async def discover_mcp_tools_async():
    """Async MCP tool discovery for server initialization."""
    mcp_servers = Config.get_mcp_servers()
    discovered_tools = {}

    for server_name, server_config in mcp_servers.items():
        if not server_config.get("enabled", True):
            continue

        if server_config.get("transport") == "http":
            url = server_config.get("url")
            if not url:
                continue

            try:
                transport = StreamableHttpTransport(url=f"{url}/mcp")
                async with Client(transport) as client:
                    tools = await client.list_tools()
                    discovered_tools[server_name] = [
                        {
                            "name": tool.name,
                            "description": tool.description or "",
                            "server": server_name,
                        }
                        for tool in tools
                    ]
            except Exception as e:
                print(f"Warning: Could not discover tools from {server_name}: {e}")
                discovered_tools[server_name] = {"error": str(e)}

    return discovered_tools

#!/usr/bin/env python3
"""
Web search tool for the travel agent.
Provides basic web search functionality using DuckDuckGo.
"""

from duckduckgo_search import DDGS
from mcp.server.fastmcp import FastMCP


def register_web_search_tool(app: FastMCP):
    """Register the web search tool with the FastMCP app."""

    @app.tool()
    async def web_search(query, max_results=5):
        """Search the web using DuckDuckGo."""
        max_results = int(max_results) if isinstance(max_results, str) else max_results
        items = []
        try:
            with DDGS() as ddgs:
                results = ddgs.text(
                    query, region="us-en", max_results=max(1, min(10, max_results))
                )
                for r in results:
                    items.append(
                        {
                            "title": r.get("title", ""),
                            "url": r.get("href", ""),
                            "snippet": r.get("body", ""),
                        }
                    )
        except Exception as e:
            print(f"Web search error: {e}")
            pass
        return {"query": query, "results": items, "count": len(items)}

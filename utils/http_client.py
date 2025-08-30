#!/usr/bin/env python3
"""
HTTP client utilities for the travel agent.
Provides a shared HTTP client with proper timeouts and headers.
"""

import httpx

from config import Config

_http_client: httpx.AsyncClient = None


def get_http_client() -> httpx.AsyncClient:
    """Get the shared HTTP client instance."""
    global _http_client
    if _http_client is None:
        timeout = httpx.Timeout(
            Config.HTTP_TIMEOUT, connect=Config.HTTP_CONNECT_TIMEOUT
        )
        headers = {"User-Agent": Config.USER_AGENT}
        _http_client = httpx.AsyncClient(timeout=timeout, headers=headers)
    return _http_client


async def close_http_client():
    """Close the shared HTTP client."""
    global _http_client
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None

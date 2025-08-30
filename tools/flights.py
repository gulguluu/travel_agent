#!/usr/bin/env python3
"""
Flights tool for the travel agent.
Provides flight search and screenshot capture functionality.
"""
import asyncio
import base64
import os
import tempfile
from datetime import datetime, timedelta

from mcp.server.fastmcp import FastMCP
from playwright.async_api import async_playwright

from utils.openai_client import analyze_image_with_vision, has_openai_client
from utils.prompt_loader import load_prompt


def register_flights_tool(app: FastMCP):
    """Register the Flights tool with the FastMCP app."""

    def build_flight_url(
        origin: str, destination: str, date: str, return_date: str = None
    ):
        """Build Google Flights URL."""
        if return_date:
            return f"https://www.google.com/travel/flights?q=Flights%20from%20{origin.upper()}%20to%20{destination.upper()}%20on%20{date}%20returning%20{return_date}"
        else:
            return f"https://www.google.com/travel/flights?q=Flights%20from%20{origin.upper()}%20to%20{destination.upper()}%20on%20{date}"

    async def capture_flight_screenshot(url: str):
        """Capture screenshot of Google Flights page."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": 1200, "height": 800})
            await page.set_extra_http_headers(
                {
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                }
            )

            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(15000)
                screenshot = await page.screenshot(full_page=True)
                screenshot_b64 = base64.b64encode(screenshot).decode()

                return {
                    "screenshot_base64": screenshot_b64,
                    "url": url,
                    "success": True,
                }

            except Exception as e:
                return {
                    "error": f"Failed to capture flight screenshot: {str(e)}",
                    "success": False,
                }
            finally:
                await browser.close()

    @app.tool()
    async def search_flights(
        origin: str, destination: str, departure_date: str, return_date: str = None
    ):
        """
        Search for flights with integrated screenshot capture and analysis.

        Args:
            origin: Origin airport code (e.g., 'SFO', 'LAX')
            destination: Destination airport code (e.g., 'JFK', 'LHR')
            departure_date: Departure date in YYYY-MM-DD format
            return_date: Return date in YYYY-MM-DD format (optional for round-trip)

        Returns:
            Dictionary with flight analysis results (no base64 data)
        """
        if not has_openai_client():
            return {
                "error": "OpenAI client not configured for flight analysis",
                "success": False,
            }

        try:
            datetime.strptime(departure_date, "%Y-%m-%d")
            if return_date:
                datetime.strptime(return_date, "%Y-%m-%d")
        except ValueError:
            return {"error": "Date must be in YYYY-MM-DD format", "success": False}

        url = build_flight_url(origin, destination, departure_date, return_date)
        screenshot_result = await capture_flight_screenshot(url)
        screenshot_size = len(base64.b64decode(screenshot_result["screenshot_base64"]))
        print(f"Screenshot size: {screenshot_size} bytes")
        with open("debug_flight.png", "wb") as f:
            f.write(base64.b64decode(screenshot_result["screenshot_base64"]))

        if not screenshot_result.get("success"):
            return screenshot_result

        try:
            prompt = load_prompt("flight_analysis_prompt")
            print(
                f"Prompt loaded: {prompt[:100]}..."
                if prompt
                else "Prompt is None/empty"
            )
            analysis_result = await analyze_image_with_vision(
                screenshot_result["screenshot_base64"], prompt
            )
            print(f"Analysis result keys: {analysis_result.keys()}")
            print(
                f"Analysis content: {analysis_result.get('analysis', 'NO ANALYSIS KEY')}"
            )

            return {
                "success": True,
                "url": url,
                "origin": origin.upper(),
                "destination": destination.upper(),
                "departure_date": departure_date,
                "return_date": return_date,
                "trip_type": "round-trip" if return_date else "one-way",
                "flight_analysis": analysis_result.get("analysis", ""),
                "model_used": analysis_result.get("model", ""),
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            return {
                "error": f"Flight analysis failed: {str(e)}",
                "success": False,
                "url": url,
            }

    @app.tool()
    async def search_flights_flexible(origin: str, destination: str, month_year: str):
        """
        Search for flights with flexible dates (whole month view).

        Args:
            origin: Origin airport code
            destination: Destination airport code
            month_year: Month and year in YYYY-MM format

        Returns:
            Screenshot of flexible date flight search
        """

        try:
            # Parse month/year and get first day of month
            date_obj = datetime.strptime(f"{month_year}-01", "%Y-%m-%d")
            first_day = date_obj.strftime("%Y-%m-%d")
        except ValueError:
            return {"error": "month_year must be in YYYY-MM format", "success": False}

        url = f"https://www.google.com/travel/flights/search?tfs=CBwQAhopag0IAxIJL20vMDJfMjg2EgoyMDI1LTEwLTAxcgwIAxIIL20vMDY0eWo"
        url = build_flight_url(origin, destination, first_day)
        result = await capture_flight_screenshot(url)
        if result.get("success"):
            result.update(
                {
                    "origin": origin.upper(),
                    "destination": destination.upper(),
                    "month_year": month_year,
                    "search_type": "flexible_dates",
                    "note": "Showing results for first day of month - full flexible calendar requires complex URL encoding",
                }
            )

        return result

    @app.tool()
    async def compare_flight_routes(routes: list):
        """
        Compare multiple flight routes by capturing screenshots of each.

        Args:
            routes: List of route dictionaries with 'origin', 'destination', 'date' keys

        Returns:
            Dictionary with screenshots for each route
        """

        if not routes or len(routes) < 2:
            return {"error": "Need at least 2 routes to compare", "success": False}

        results = {}

        for i, route in enumerate(routes):
            try:
                origin = route.get("origin")
                destination = route.get("destination")
                date = route.get("date")

                if not all([origin, destination, date]):
                    results[f"route_{i+1}"] = {
                        "error": "Missing required fields: origin, destination, date",
                        "success": False,
                    }
                    continue

                # Search this route
                route_result = await search_flights(
                    origin, destination, date, route.get("return_date")
                )
                results[f"route_{i+1}"] = route_result

            except Exception as e:
                results[f"route_{i+1}"] = {
                    "error": f"Failed to search route: {str(e)}",
                    "success": False,
                }

        successful_searches = sum(1 for r in results.values() if r.get("success"))
        return {
            "routes": results,
            "summary": {
                "total_routes": len(routes),
                "successful_searches": successful_searches,
                "comparison_ready": successful_searches >= 2,
            },
        }

    @app.tool()
    async def get_flight_deals(origin: str, budget_max: int = 500):
        """
        Find flight deals from origin within budget (uses Google Flights explore feature).

        Args:
            origin: Origin airport code
            budget_max: Maximum budget in USD

        Returns:
            Screenshot of flight deals/explore page
        """

        # Use natural language query format for Google Flights
        # This is more reliable than complex encoded URLs
        url = f"https://www.google.com/travel/flights?q=Flights from {origin} under ${budget_max}"

        result = await capture_flight_screenshot(url)

        if result.get("success"):
            result.update(
                {
                    "origin": origin.upper(),
                    "budget_max": budget_max,
                    "search_type": "deals_explore",
                    "note": "Explore page - manual destination selection may be needed",
                }
            )

        return result

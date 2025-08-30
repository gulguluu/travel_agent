#!/usr/bin/env python3
"""
Hotels tool for the travel agent.
Provides hotel search and screenshot capture functionality.
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


def register_hotels_tool(app: FastMCP):
    """Register the Hotels tool with the FastMCP app."""

    def build_hotel_url(
        destination: str,
        checkin_date: str,
        checkout_date: str,
        guests: int = 2,
        rooms: int = 1,
    ):
        """Build Google Hotels URL with language parameter to ensure consistency."""
        base_url = "https://www.google.com/travel/hotels"
        # URL-encode the destination to handle spaces and special characters
        from urllib.parse import quote

        encoded_destination = quote(destination)

        # Construct the query string with all parameters
        query_params = f"q=Hotels%20in%20{encoded_destination}%20checkin%20{checkin_date}%20checkout%20{checkout_date}"

        # Add guests and rooms if not default
        if guests != 2 or rooms != 1:
            query_params += f"%20{guests}%20guests%20{rooms}%20rooms"

        # Add hl=en to force English results and avoid location-based language redirection
        return f"{base_url}?{query_params}&hl=en"

    async def capture_hotel_screenshot(url: str):
        """Capture screenshot of Google Hotels page."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": 1200, "height": 800})

            # Set realistic headers
            await page.set_extra_http_headers(
                {
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                }
            )

            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(6000)
                screenshot = await page.screenshot(full_page=True)
                screenshot_b64 = base64.b64encode(screenshot).decode()
                return {
                    "screenshot_base64": screenshot_b64,
                    "url": url,
                    "success": True,
                }
            except Exception as e:
                return {
                    "error": f"Failed to capture hotel screenshot: {str(e)}",
                    "success": False,
                }
            finally:
                await browser.close()

    @app.tool()
    async def search_hotels(
        destination: str,
        checkin_date: str,
        checkout_date: str,
        guests: int = 2,
        rooms: int = 1,
    ):
        """
        Search for hotels with integrated screenshot capture and analysis.

        Args:
            destination: Hotel destination (city name or location)
            checkin_date: Check-in date in YYYY-MM-DD format
            checkout_date: Check-out date in YYYY-MM-DD format
            guests: Number of guests (default: 2)
            rooms: Number of rooms (default: 1)

        Returns:
            Dictionary with hotel analysis results (no base64 data)
        """

        if not has_openai_client():
            return {
                "error": "OpenAI client not configured for hotel analysis",
                "success": False,
            }

        try:
            checkin = datetime.strptime(checkin_date, "%Y-%m-%d")
            checkout = datetime.strptime(checkout_date, "%Y-%m-%d")

            if checkout <= checkin:
                return {
                    "error": "Checkout date must be after checkin date",
                    "success": False,
                }

        except ValueError:
            return {"error": "Dates must be in YYYY-MM-DD format", "success": False}

        nights = (checkout - checkin).days
        url = build_hotel_url(destination, checkin_date, checkout_date, guests, rooms)
        screenshot_result = await capture_hotel_screenshot(url)

        if not screenshot_result.get("success"):
            return screenshot_result

        try:
            prompt = load_prompt("hotel_analysis_prompt")
            analysis_result = await analyze_image_with_vision(
                screenshot_result["screenshot_base64"], prompt
            )

            return {
                "success": True,
                "url": url,
                "destination": destination,
                "checkin_date": checkin_date,
                "checkout_date": checkout_date,
                "nights": nights,
                "guests": guests,
                "rooms": rooms,
                "hotel_analysis": analysis_result.get("analysis", ""),
                "model_used": analysis_result.get("model", ""),
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            return {
                "error": f"Hotel analysis failed: {str(e)}",
                "success": False,
                "url": url,
            }

    @app.tool()
    async def search_hotels_by_budget(
        destination: str,
        checkin_date: str,
        checkout_date: str,
        budget_category: str = "mid",
        guests: int = 2,
    ):
        """
        Search for hotels within specific budget category.

        Args:
            destination: Destination city/area
            checkin_date: Check-in date in YYYY-MM-DD format
            checkout_date: Check-out date in YYYY-MM-DD format
            budget_category: 'budget', 'mid', 'luxury' (default: 'mid')
            guests: Number of guests

        Returns:
            Hotel search results with budget context
        """

        budget_terms = {
            "budget": "budget hotels hostels affordable",
            "mid": "hotels mid-range",
            "luxury": "luxury hotels 4 star 5 star premium",
        }

        enhanced_destination = f"{destination} {budget_terms.get(budget_category, '')}"
        result = await search_hotels(
            enhanced_destination, checkin_date, checkout_date, guests
        )
        if result.get("success"):
            result.update(
                {
                    "budget_category": budget_category,
                    "search_enhanced": True,
                    "note": f"Search enhanced with {budget_category} keywords",
                }
            )

        return result

    @app.tool()
    async def search_hotels_near_landmark(
        destination: str,
        landmark: str,
        checkin_date: str,
        checkout_date: str,
        guests: int = 2,
    ):
        """
        Search for hotels near a specific landmark or area.

        Args:
            destination: Destination city
            landmark: Specific landmark, area, or attraction
            checkin_date: Check-in date in YYYY-MM-DD format
            checkout_date: Check-out date in YYYY-MM-DD format
            guests: Number of guests

        Returns:
            Hotel search results near landmark
        """

        location_query = f"{destination} near {landmark}"
        result = await search_hotels(
            location_query, checkin_date, checkout_date, guests
        )
        if result.get("success"):
            result.update(
                {
                    "landmark": landmark,
                    "location_type": "landmark_proximity",
                    "enhanced_query": location_query,
                }
            )

        return result

    @app.tool()
    async def compare_hotel_areas(
        destination: str, areas: list, checkin_date: str, checkout_date: str
    ):
        """
        Compare hotels across different areas/neighborhoods in a city.

        Args:
            destination: Main destination city
            areas: List of neighborhoods/areas to compare
            checkin_date: Check-in date in YYYY-MM-DD format
            checkout_date: Check-out date in YYYY-MM-DD format

        Returns:
            Dictionary with hotel search results for each area
        """

        if not areas or len(areas) < 2:
            return {"error": "Need at least 2 areas to compare", "success": False}

        results = {}

        for i, area in enumerate(areas):
            try:
                area_destination = f"{destination} {area}"
                area_result = await search_hotels(
                    area_destination, checkin_date, checkout_date
                )
                if area_result.get("success"):
                    area_result["area"] = area
                results[f"area_{i+1}_{area.replace(' ', '_').lower()}"] = area_result
            except Exception as e:
                results[f"area_{i+1}_{area.replace(' ', '_').lower()}"] = {
                    "error": f"Failed to search area {area}: {str(e)}",
                    "success": False,
                }

        successful_searches = sum(1 for r in results.values() if r.get("success"))
        return {
            "areas": results,
            "summary": {
                "destination": destination,
                "total_areas": len(areas),
                "successful_searches": successful_searches,
                "comparison_ready": successful_searches >= 2,
                "checkin_date": checkin_date,
                "checkout_date": checkout_date,
            },
        }

    @app.tool()
    async def get_last_minute_hotels(destination: str, checkin_days_from_now: int = 1):
        """
        Find last-minute hotel deals.

        Args:
            destination: Destination city
            checkin_days_from_now: Days from today for checkin (default: 1 for tomorrow)

        Returns:
            Hotel search results for immediate booking
        """

        checkin = datetime.now() + timedelta(days=checkin_days_from_now)
        checkout = checkin + timedelta(days=1)  # Default 1 night stay
        checkin_date = checkin.strftime("%Y-%m-%d")
        checkout_date = checkout.strftime("%Y-%m-%d")
        enhanced_destination = f"{destination} last minute deals tonight"
        result = await search_hotels(enhanced_destination, checkin_date, checkout_date)
        if result.get("success"):
            result.update(
                {
                    "search_type": "last_minute",
                    "checkin_days_from_now": checkin_days_from_now,
                    "booking_urgency": (
                        "high" if checkin_days_from_now <= 1 else "medium"
                    ),
                }
            )

        return result

    @app.tool()
    async def search_extended_stay_hotels(
        destination: str, checkin_date: str, nights: int = 7
    ):
        """
        Search for extended stay hotels (weekly/monthly rates).

        Args:
            destination: Destination city
            checkin_date: Check-in date in YYYY-MM-DD format
            nights: Number of nights (default: 7 for weekly)

        Returns:
            Extended stay hotel search results
        """

        try:
            checkin = datetime.strptime(checkin_date, "%Y-%m-%d")
            checkout = checkin + timedelta(days=nights)
            checkout_date = checkout.strftime("%Y-%m-%d")
        except ValueError:
            return {
                "error": "checkin_date must be in YYYY-MM-DD format",
                "success": False,
            }

        extended_destination = f"{destination} extended stay weekly monthly apartments"
        result = await search_hotels(extended_destination, checkin_date, checkout_date)
        if result.get("success"):
            result.update(
                {
                    "search_type": "extended_stay",
                    "nights": nights,
                    "duration_category": "weekly" if nights >= 7 else "short_term",
                }
            )

        return result

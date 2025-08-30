#!/usr/bin/env python3
"""
Transit and routing tools for the travel agent.
Provides public transport and routing functionality.
"""

from dateutil import parser as dateparser
from duckduckgo_search import DDGS
from mcp.server.fastmcp import FastMCP

from utils.geo_utils import geocode_place, parse_latlon
from utils.http_client import get_http_client


def register_transit_tools(app: FastMCP):
    """Register transit and routing tools with the FastMCP app."""

    async def _osrm_route(mode, a, b):
        """Get route information using OSRM."""
        profile = {
            "driving": "driving",
            "walking": "walking",
            "cycling": "cycling",
        }.get(mode, "driving")

        try:
            client = get_http_client()
            url = f"https://router.project-osrm.org/route/v1/{profile}/{a[1]},{a[0]};{b[1]},{b[0]}"
            params = {"overview": "false", "alternatives": "false", "steps": "false"}

            response = await client.get(url, params=params)

            if response.status_code == 200:
                j = response.json()

                if not j.get("routes"):
                    return {"error": "no route found", "success": False}

                rt = j["routes"][0]
                return {
                    "mode": profile,
                    "distance_km": round(rt.get("distance", 0) / 1000, 2),
                    "duration_min": round(rt.get("duration", 0) / 60, 1),
                    "success": True,
                }
            else:
                return {
                    "error": f"OSRM API returned status {response.status_code}",
                    "success": False,
                }

        except Exception as e:
            return {"error": f"Route calculation failed: {str(e)}", "success": False}

    @app.tool()
    async def transit_journeys(from_place, to_place, datetime_iso=None, max_results=3):
        """
        Finds public transport options using a web search.
        from_place/to_place = city names or 'lat,lon'.
        datetime_iso example: '2025-09-01T09:00:00'
        """

        query = f"train bus public transport {from_place} to {to_place}"
        if datetime_iso:
            try:
                date_str = dateparser.parse(datetime_iso).strftime("%B %d, %Y")
                query += f" {date_str}"
            except:
                pass  # Ignore if datetime is invalid

        try:
            items = []
            with DDGS() as ddgs:
                search_results = ddgs.text(query, max_results=max_results)
                for r in search_results:
                    items.append(
                        {
                            "title": r.get("title", ""),
                            "url": r.get("href", ""),
                            "snippet": r.get("body", ""),
                        }
                    )

            return {
                "search_query": query,
                "transit_results": items,
                "from_place": from_place,
                "to_place": to_place,
                "datetime": datetime_iso,
                "success": True,
            }

        except Exception as e:
            return {
                "error": f"Transit search failed: {str(e)}",
                "search_query": query,
                "success": False,
            }

    @app.tool()
    async def driving_route(from_place, to_place, mode="driving"):
        """
        Get distance/time by car/walk/bike via OSRM.
        mode options: 'driving', 'walking', 'cycling'
        """

        def norm(q):
            """Normalize place to lat,lon coordinates."""
            return parse_latlon(q)

        # Try to parse coordinates directly first
        a = norm(from_place)
        b = norm(to_place)

        # Geocode if needed
        if not a:
            g = await geocode_place(from_place)
            if not g:
                return {"error": f"could not geocode '{from_place}'", "success": False}
            a = (g["lat"], g["lon"])

        if not b:
            g = await geocode_place(to_place)
            if not g:
                return {"error": f"could not geocode '{to_place}'", "success": False}
            b = (g["lat"], g["lon"])

        # Get route
        result = await _osrm_route(mode, a, b)

        # Add place info to result
        if result.get("success"):
            result.update(
                {
                    "from_place": from_place,
                    "to_place": to_place,
                    "from_coords": a,
                    "to_coords": b,
                }
            )

        return result

    @app.tool()
    async def multi_modal_route(from_place, to_place):
        """
        Get routing options for multiple transportation modes.
        """

        results = {}
        modes = ["driving", "walking", "cycling"]

        for mode in modes:
            try:
                route_result = await driving_route(from_place, to_place, mode)
                results[mode] = route_result
            except Exception as e:
                results[mode] = {
                    "error": f"Failed to get {mode} route: {str(e)}",
                    "success": False,
                }

        # Add transit search
        try:
            transit_result = await transit_journeys(from_place, to_place, max_results=2)
            results["public_transit"] = transit_result
        except Exception as e:
            results["public_transit"] = {
                "error": f"Transit search failed: {str(e)}",
                "success": False,
            }

        # Calculate summary
        successful_modes = sum(1 for r in results.values() if r.get("success"))

        return {
            "routes": results,
            "from_place": from_place,
            "to_place": to_place,
            "summary": {
                "total_modes": len(results),
                "successful_routes": successful_modes,
            },
        }

    @app.tool()
    async def nearby_transit_stops(place, radius_km=1.0):
        """
        Find nearby public transit stops using web search.
        """

        query = f"public transit stops stations near {place} within {radius_km}km"

        try:
            items = []
            with DDGS() as ddgs:
                search_results = ddgs.text(query, max_results=5)
                for r in search_results:
                    items.append(
                        {
                            "title": r.get("title", ""),
                            "url": r.get("href", ""),
                            "snippet": r.get("body", ""),
                        }
                    )

            return {
                "search_query": query,
                "place": place,
                "radius_km": radius_km,
                "transit_stops": items,
                "success": True,
            }

        except Exception as e:
            return {"error": f"Transit stop search failed: {str(e)}", "success": False}

#!/usr/bin/env python3
"""
Geographic utilities for the travel agent.
Handles geocoding, coordinate parsing, and distance calculations.
"""

import math

from utils.http_client import get_http_client


def haversine_km(lat1, lon1, lat2, lon2):
    """Calculate the great circle distance between two points on Earth in kilometers."""
    R = 6371.0  # Earth's radius in kilometers
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def parse_latlon(s):
    """Parse a lat,lon string into a tuple of floats."""
    try:
        if "," in s:
            a, b = s.split(",", 1)
            return float(a.strip()), float(b.strip())
    except Exception:
        return None
    return None


async def geocode_place(name):
    """
    Geocode a place name using Nominatim (OpenStreetMap).
    Returns a dict with name, lat, lon or None if not found.
    """
    client = get_http_client()
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": name,
        "format": "json",
        "limit": 1,
        "addressdetails": 1,
        "extratags": 1,
    }
    headers = {"User-Agent": "TravelAgent/1.0 (travel-planning-service)"}

    try:
        r = await client.get(url, params=params, headers=headers)
        r.raise_for_status()
        j = r.json()
        if j and len(j) > 0:
            item = j[0]
            lat = item.get("lat")
            lon = item.get("lon")
            if lat and lon:
                return {
                    "name": item.get("display_name"),
                    "lat": float(lat),
                    "lon": float(lon),
                }
    except Exception as e:
        print(f"Geocoding error for '{name}': {e}")
        return None
    return None

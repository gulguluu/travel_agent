#!/usr/bin/env python3
"""
Airport utilities for the travel agent.
Handles airport data loading and IATA code lookups.
"""

from airportsdata import load as load_airports

from utils.geo_utils import haversine_km

# Load airports data once at module level
_AIRPORTS_IATA = load_airports("IATA")
_AIRPORTS = [
    {
        "iata": code,
        "name": d.get("name"),
        "city": d.get("city"),
        "country": d.get("country"),
        "lat": d.get("lat"),
        "lon": d.get("lon"),
    }
    for code, d in _AIRPORTS_IATA.items()
    if isinstance(d.get("lat"), (int, float)) and isinstance(d.get("lon"), (int, float))
]


def get_airports_data():
    """Get the loaded airports data."""
    return _AIRPORTS


async def iata_lookup(term, limit=5):
    """
    Guess IATA codes by city/airport name or exact code.
    Returns a scored list of matching airports.
    """
    # Ensure limit is an integer
    limit = int(limit) if isinstance(limit, str) else limit

    term_low = term.lower()
    scored = []

    for ap in _AIRPORTS:
        score = 0
        if ap["iata"] and term_low == ap["iata"].lower():
            score = 100
        elif ap["city"] and term_low in ap["city"].lower():
            score = 50
            if ap["city"] and ap["city"].lower() in [
                "portland",
                "seattle",
                "los angeles",
                "san francisco",
            ]:
                score = 80
        elif ap["name"] and term_low in ap["name"].lower():
            score = 40
        elif ap["country"] and term_low in ap["country"].lower():
            score = 10

        if score:
            scored.append((score, ap))

    scored.sort(key=lambda x: -x[0])
    return [ap for _, ap in scored[: max(1, min(10, limit))]]


def find_nearest_airports(lat, lon, limit=5):
    """Find the nearest airports to a given coordinate."""
    scored = []
    for ap in _AIRPORTS:
        distance = haversine_km(lat, lon, ap["lat"], ap["lon"])
        scored.append((distance, ap))

    scored.sort(key=lambda x: x[0])

    result = []
    for distance, ap in scored[: max(1, min(10, int(limit)))]:
        result.append(
            {
                "iata": ap["iata"],
                "name": ap["name"],
                "city": ap["city"],
                "country": ap["country"],
                "distance_km": round(distance, 1),
                "lat": ap["lat"],
                "lon": ap["lon"],
            }
        )

    return result

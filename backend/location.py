"""Shared location state used by chat_routes, executor, and main."""
import httpx

# Location: prefer browser GPS, fall back to Ridgway PA (home base)
_location_cache: dict = {
    "location": "Ridgway, PA",
    "timezone": "America/New_York",
    "lat": 41.4203,
    "lon": -78.7286,
    "source": "default",
}

async def _update_location_from_gps(lat: float, lon: float):
    """Reverse geocode GPS coordinates to city name."""
    global _location_cache
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"https://nominatim.openstreetmap.org/reverse",
                params={"lat": lat, "lon": lon, "format": "json", "zoom": 10},
                headers={"User-Agent": "ClaudeUI/1.0"},
            )
            data = resp.json()
            addr = data.get("address", {})
            city = addr.get("city") or addr.get("town") or addr.get("village") or addr.get("county", "Unknown")
            state = addr.get("state", "")
            _location_cache = {
                "location": f"{city}, {state}" if state else city,
                "timezone": "America/New_York",  # Could detect from coords but this covers most US
                "lat": lat,
                "lon": lon,
                "source": "gps",
            }
    except Exception:
        _location_cache = {"location": f"{lat},{lon}", "timezone": "America/New_York", "source": "gps"}


async def _get_user_location() -> tuple[str, str]:
    """Returns (location_string, timezone). Prefers GPS, falls back to home base."""
    global _location_cache
    if _location_cache:
        return _location_cache["location"], _location_cache["timezone"]
    # Default: Ridgway, PA (home base — IP geolocation is unreliable on Starlink)
    _location_cache = {
        "location": "Ridgway, PA",
        "timezone": "America/New_York",
        "lat": 41.4203,
        "lon": -78.7286,
        "source": "default",
    }
    return "Ridgway, PA", "America/New_York"

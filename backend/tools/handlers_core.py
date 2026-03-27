"""Core tool handlers — code execution, web, weather, calculator, artifacts."""
import json
import subprocess
import tempfile
import os
import math
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup


# ── Code Execution ──────────────────────────────────────────────────────────

async def _execute_code(args: dict) -> dict:
    code = args.get("code", "")
    language = args.get("language", "python")

    if language == "python":
        return _run_subprocess(["python3", "-c", code])
    elif language == "javascript":
        return _run_subprocess(["node", "-e", code])
    elif language == "bash":
        return _run_subprocess(["bash", "-c", code])
    return {"error": f"Unsupported language: {language}"}


def _run_subprocess(cmd: list[str]) -> dict:
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        output = result.stdout
        if result.stderr:
            output += ("\n" if output else "") + result.stderr
        return {"output": output.strip(), "exit_code": result.returncode}
    except subprocess.TimeoutExpired:
        return {"output": "Execution timed out (30s limit)", "exit_code": -1}


# ── Web Search ──────────────────────────────────────────────────────────────

async def _web_search(args: dict) -> dict:
    query = args.get("query", "")
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        resp = await client.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"},
        )
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for r in soup.select(".result"):
            title_el = r.select_one(".result__a")
            snippet_el = r.select_one(".result__snippet")
            if title_el:
                results.append({
                    "title": title_el.get_text(strip=True),
                    "url": title_el.get("href", ""),
                    "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
                })
            if len(results) >= 8:
                break
        return {"results": results}


# ── Fetch URL ───────────────────────────────────────────────────────────────

async def _fetch_url(args: dict) -> dict:
    url = args.get("url", "")
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        resp = await client.get(url, headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        })
        soup = BeautifulSoup(resp.text, "html.parser")
        # Remove script/style
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        # Truncate to ~4000 chars
        if len(text) > 4000:
            text = text[:4000] + "\n...(truncated)"
        title = soup.title.string if soup.title else ""
        return {"title": title, "content": text}


# ── Date/Time ───────────────────────────────────────────────────────────────

async def _get_datetime(args: dict) -> dict:
    tz_name = args.get("timezone", "local")
    now = datetime.now()
    return {
        "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
        "date": now.strftime("%A, %B %d, %Y"),
        "time": now.strftime("%I:%M %p"),
        "timezone": tz_name,
        "unix": int(now.timestamp()),
    }


# ── Weather (Open-Meteo, free, no API key, GPS-based) ───────────────────────

# Ridgway, PA default coords
DEFAULT_LAT = 41.4203
DEFAULT_LON = -78.7286

WEATHER_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Foggy", 48: "Rime fog", 51: "Light drizzle", 53: "Moderate drizzle",
    55: "Dense drizzle", 61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    66: "Light freezing rain", 67: "Heavy freezing rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow", 77: "Snow grains",
    80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
    85: "Slight snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Thunderstorm with heavy hail",
}


async def _get_weather(args: dict) -> dict:
    location = args.get("location", "")
    lat = args.get("lat")
    lon = args.get("lon")

    async with httpx.AsyncClient(timeout=10.0) as client:
        # If a city name is given but no coords, geocode it
        if location and not lat:
            try:
                geo_resp = await client.get(
                    "https://geocoding-api.open-meteo.com/v1/search",
                    params={"name": location, "count": 1, "language": "en"},
                )
                geo_data = geo_resp.json()
                results = geo_data.get("results", [])
                if results:
                    lat = results[0]["latitude"]
                    lon = results[0]["longitude"]
                    location = f"{results[0].get('name', location)}, {results[0].get('admin1', '')}"
            except Exception:
                pass

        # Fall back to cached GPS location from browser, then default
        if not lat:
            try:
                from location import _location_cache
                if _location_cache.get("lat"):
                    lat = _location_cache["lat"]
                    lon = _location_cache["lon"]
                    location = _location_cache.get("location", "Your location")
            except Exception:
                pass

        if not lat:
            lat = DEFAULT_LAT
            lon = DEFAULT_LON
            location = location or "Ridgway, PA"

        # Reverse geocode if we have coords but no name
        if not location:
            try:
                rgeo = await client.get(
                    "https://api.bigdatacloud.net/data/reverse-geocode-client",
                    params={"latitude": lat, "longitude": lon, "localityLanguage": "en"},
                )
                rgeo_data = rgeo.json()
                city = rgeo_data.get("city") or rgeo_data.get("locality") or rgeo_data.get("principalSubdivision", "")
                state = rgeo_data.get("principalSubdivision", "")
                location = f"{city}, {state}" if state and state != city else city or f"{lat:.2f}, {lon:.2f}"
            except Exception:
                location = f"{lat:.2f}, {lon:.2f}"

        # Fetch weather from Open-Meteo
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m"
            f"&daily=temperature_2m_max,temperature_2m_min,sunrise,sunset"
            f"&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone=auto"
        )
        resp = await client.get(url)
        data = resp.json()

        current = data.get("current", {})
        daily = data.get("daily", {})
        weather_code = current.get("weather_code", 0)

        return {
            "location": location,
            "temperature_f": round(current.get("temperature_2m", 0)),
            "feels_like_f": round(current.get("apparent_temperature", 0)),
            "condition": WEATHER_CODES.get(weather_code, "Unknown"),
            "humidity": current.get("relative_humidity_2m", ""),
            "wind_mph": round(current.get("wind_speed_10m", 0)),
            "high_f": round(daily.get("temperature_2m_max", [0])[0]),
            "low_f": round(daily.get("temperature_2m_min", [0])[0]),
            "sunrise": daily.get("sunrise", [""])[0].split("T")[-1] if daily.get("sunrise") else "",
            "sunset": daily.get("sunset", [""])[0].split("T")[-1] if daily.get("sunset") else "",
        }


# ── Calculator ──────────────────────────────────────────────────────────────

async def _calculator(args: dict) -> dict:
    expression = args.get("expression", "")
    # Safe math evaluation
    allowed_names = {
        k: v for k, v in math.__dict__.items() if not k.startswith("_")
    }
    allowed_names.update({"abs": abs, "round": round, "min": min, "max": max})
    try:
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return {"expression": expression, "result": str(result)}
    except Exception as e:
        return {"expression": expression, "error": str(e)}


# ── Artifact Creation ───────────────────────────────────────────────────────

async def _create_artifact(args: dict) -> dict:
    return {
        "artifact_created": True,
        "id": args.get("id", ""),
        "type": args.get("type", "code"),
        "title": args.get("title", "Untitled"),
    }

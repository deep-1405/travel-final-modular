import os
import urllib.parse
import httpx
from typing import Optional, Dict
from fastapi import APIRouter, HTTPException
from dotenv import load_dotenv
load_dotenv(override=True)
router = APIRouter(prefix="/api/geolocation", tags=["geolocation"])

async def fetch_geolocation(location: str) -> Optional[Dict[str, float]]:
    """
    Fetches geolocation (latitude, longitude) for a given location using Google Geocoding API.

    Args:
        location (str): The address or location to geocode (e.g., "New York, NY").

    Returns:
        Optional[Dict[str, float]]: A dictionary with 'latitude' and 'longitude' keys, or None if no results.

    Raises:
        ValueError: If the location is invalid or the API key is missing.
        HTTPException: If the API request fails or returns an error status.
    """
    if not location or not location.strip():
        raise ValueError("Location cannot be empty")

    GOOGLE_GEOLOCATION_API = os.getenv("GOOGLE_GEOLOCATION_API")
    if not GOOGLE_GEOLOCATION_API:
        raise ValueError("Google Geocoding API key not configured")

    normalized = location.strip()
    safe_address = urllib.parse.quote_plus(normalized)
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={safe_address}&key={GOOGLE_GEOLOCATION_API}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

            if data.get("status") != "OK":
                if data.get("status") == "ZERO_RESULTS":
                    return None
                raise HTTPException(status_code=400, detail=f"Geocoding API error: {data.get('status')}")

            coords = data["results"][0]["geometry"]["location"]
            latitude = round(coords["lat"], 4)
            longitude = round(coords["lng"], 4)

            return {"latitude": latitude, "longitude": longitude}

    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail="Failed to fetch geolocation")
    except (KeyError, IndexError):
        raise HTTPException(status_code=500, detail="Invalid geolocation data from API")

@router.get("")
async def get_geolocation(location: str) -> Optional[Dict[str, float]]:
    """
    Retrieve geolocation (latitude, longitude) for a given location.

    Query Parameters:
        location (str): The address or location to geocode (e.g., "New York, NY").

    Returns:
        JSON response with latitude and longitude, or null if no results.

    Raises:
        HTTPException: If the location is invalid or the API request fails.
    """
    try:
        result = await fetch_geolocation(location)
        return result if result else {"message": "No geolocation found for the provided location"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")
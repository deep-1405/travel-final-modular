import os
import httpx
import time
from typing import List, Dict, Optional
from fastapi import APIRouter, HTTPException
from .geolocation import fetch_geolocation
from utils.logger import logger

logger = logger()

router = APIRouter(prefix="/api/airports", tags=["airports"])

_access_token = None
_token_expiry = 0

async def get_access_token():
    """
    Fetches OAuth2 access token from Amadeus API.
    """
    global _access_token, _token_expiry
    if _access_token and time.time() < _token_expiry:
        return _access_token

    AMADEUS_CLIENT_ID = os.getenv("AMADEUS_CLIENT_ID")
    AMADEUS_CLIENT_SECRET = os.getenv("AMADEUS_CLIENT_SECRET")
    if not AMADEUS_CLIENT_ID or not AMADEUS_CLIENT_SECRET:
        raise ValueError("Amadeus API credentials not found")
    
    async with httpx.AsyncClient(timeout=float(os.getenv("HTTP_TIMEOUT", 30.0))) as client:
        token_url = "https://test.api.amadeus.com/v1/security/oauth2/token"
        payload = {
            "grant_type": "client_credentials",
            "client_id": AMADEUS_CLIENT_ID,
            "client_secret": AMADEUS_CLIENT_SECRET,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        response = await client.post(token_url, data=payload, headers=headers)
        response.raise_for_status()        
        token_data = response.json()
    
    _access_token = token_data["access_token"]
    _token_expiry = time.time() + token_data["expires_in"] - 10
    return _access_token

async def get_airport(location: str):
    """
    Fetch the nearest airports for a given location using the Amadeus API.

    Args:
        location (str): The address or location to find nearby airports (e.g., "New York, NY").

    Returns:
        Optional[List[Dict]]: A list of airport data (with IATA codes) if found, or None if no airports are found.

    Raises:
        ValueError: If the location is invalid or empty.
        HTTPException: If the geolocation or Amadeus API request fails.
    """

    if not location or not location.strip():
        raise ValueError("Location cannot be empty")

    try:
        coords = await fetch_geolocation(location)
        if not coords:
            return {"status": 404, "response": {"title": f"NO GEOLOCATION DATA FOUND FOR {location}"}}
        
        lat = coords["latitude"]
        lon = coords["longitude"]
        logger.info(f"Fetched coordinates for {location}: {coords}")
        
        access_token = await get_access_token()
        if not access_token:
            raise HTTPException(status_code=500, detail="Failed to obtain access token")
        
        url = "https://test.api.amadeus.com/v1/reference-data/locations/airports"
        params = {
            "latitude": lat,
            "longitude": lon,
            "radius": 200  # Explicit radius in km
        }
        headers = {"Authorization": f"Bearer {access_token}"}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params, headers=headers)
            logger.info(f"Amadeus API response status: {response.status_code}")
            response.raise_for_status()

            data = response.json()
            if not data.get("data"):
                raise HTTPException(status_code=404, detail=f"No airports found near {location}")

            return data["data"]
        
    except httpx.HTTPStatusError as e:
        logger.error(f"Amadeus API error: {str(e)}")
        raise HTTPException(status_code=e.response.status_code, detail=f"Failed to fetch airports: {str(e)}")
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

@router.get("")
async def get_nearest_airports(location: str) -> Optional[List[Dict]]:
    """
    Retrieve a list of airports near a given location.

    Query Parameters:
        location (str): The address or location to find nearby airports (e.g., "New York, NY").

    Returns:
        JSON response with a list of airport data (including IATA codes), or an error if none found.

    Raises:
        HTTPException: If the location is invalid, geolocation fails, or the Amadeus API request fails.
    """
    try:
        result = await get_airport(location)
        if not result:
            raise HTTPException(status_code=404, detail=f"No airports found near {location}")
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

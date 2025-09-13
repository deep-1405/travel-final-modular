import os
import time
import urllib.parse
import httpx
from dotenv import load_dotenv
import json
from serpapi import GoogleSearch

# Load environment variables
load_dotenv(override=True)

_access_token = None
_token_expiry = 0

async def fetch_geolocation(location: str):
    """
    Fetches geolocation (latitude, longitude) for a given location using Google Geocoding API.
    """
    GOOGLE_GEOLOCATION_API = os.getenv("GOOGLE_GEOLOCATION_API")
    if not GOOGLE_GEOLOCATION_API:
        raise ValueError("Google Developer API not found")

    normalized = location.strip()
    safe_address = urllib.parse.quote_plus(normalized)
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={safe_address}&key={GOOGLE_GEOLOCATION_API}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()

        if not data.get("results"):
            return None

        coords = data["results"][0]["geometry"]["location"]
        latitude = float(format(coords["lat"], ".4f"))
        longitude = float(format(coords["lng"], ".4f"))

        if latitude is None or longitude is None:
            raise ValueError("Invalid geolocation data: latitude or longitude missing")

        return {"latitude": latitude, "longitude": longitude}

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

from pydantic import BaseModel, Field
from typing import Optional

class FlightsInput(BaseModel):
    departure_id: str = Field(description='Departure airport code (IATA)')
    arrival_id: str = Field(description='Arrival airport code (IATA)')
    outbound_date: str = Field(description='Outbound date in YYYY-MM-DD format')
    adults: Optional[int] = Field(description="Number of adults", default=1)
    children: Optional[int] = Field(description="Number of children", default=0)
    return_date: Optional[str] = Field(description="Return date in YYYY-MM-DD format", default=None)

class FlightsInputSchema(BaseModel):
    params: FlightsInput

class BookingInput(BaseModel):
    booking_token: str = Field(description='Booking token from a flight search result')
    original_params: FlightsInput = Field(description='Original flight search parameters to ensure consistency')

class BookingInputSchema(BaseModel):
    params: BookingInput

from backend.load_data import load_json_data

def get_booking_options(params: BookingInput):
    '''
    Fetch booking options for a specific flight using its booking token, reusing the original flight search parameters.

    Args:
        params: BookingInput object containing booking_token and original_params (FlightsInput).

    Returns:
        dict: Booking options data or error details.
    '''
    # print("BookingInput:", params.model_dump())
    print("getting booking options for booking token:", params.get("booking_token"))
    serpapi_key = os.getenv('SERPAPI_API_KEY')
    if not serpapi_key:
        return {"status": 500, "error": "SERPAPI_API_KEY not found in environment variables"}

    query_params = {
        'api_key': serpapi_key,
        'engine': 'google_flights',
        'hl': 'en',
        'gl': 'in',
        'currency': 'INR',
        'departure_id': params.get("departure_id"),
        'arrival_id': params.get("arrival_id"),
        'outbound_date': params.get("outbound_date"),
        'adults': int(params.get("adults")),
        'children': int(params.get("children")),
        'type': 1 if params.get("return_date") else 2,
        'booking_token': params.get("booking_token")
    }
    if params.return_date:
        query_params['return_date'] = params.return_date
    
    print("Flight Booking Options payload:")
    print(json.dumps(query_params, indent=2))

    #static 
    # result = load_json_data("round_flights_options.json")
    # return result

    #real-time
    try:
        search = GoogleSearch(query_params)
        result = search.get_dict()
        # print("SerpAPI Response (Booking):", result)  # Debug log
        if "booking_options" not in result and "error" not in result:
            return {"status": 404, "error": "No booking options found for the given booking token"}
        return result
    except Exception as e:
        print("SerpAPI Error:", str(e))  # Debug log
        return {"status": 500, "error": f"Failed to fetch booking options: {str(e)}"}


def get_flights(params: FlightsInput):
    '''
    Find flights using the Google Flights engine via SerpAPI.

    Args:
        params: FlightsInput object containing departure_id, arrival_id, outbound_date, adults, children, and optional return_date.

    Returns:
        dict: Flight search results containing 'best_flights' or error details.
    '''
    # print("FlightsInput:", params.model_dump())
    
    serpapi_key = os.getenv('SERPAPI_API_KEY')
    if not serpapi_key:
        return {"status": 500, "error": "SERPAPI_API_KEY not found in environment variables"}

    # SerpAPI related inputs
    query_params = {
        'api_key': serpapi_key,
        'engine': 'google_flights',
        'hl': 'en',
        'gl': 'in',
        'currency': 'INR'
    }

    # Use original search params if present, otherwise current params
    flight_request = getattr(params, "original_params", params)

    # Common fields
    query_params.update({
        "departure_id": flight_request.get("departure_id"),
        "arrival_id": flight_request.get("arrival_id"),
        "outbound_date": flight_request.get("outbound_date"),
        "adults": int(flight_request.get("adults")),
        "children": int(flight_request.get("children")),
        "departure_token": flight_request.get("departure_token")
    })

    if flight_request.get("return_date"):
        query_params["return_date"] = flight_request.get("return_date")
        query_params["type"] = 1
    else:
        query_params["type"] = 2

    
    # static
    # result = {}
    # if hasattr(params, "departure_token"):
    #     query_params["departure_token"] = params.departure_token
    #     print("Getting return flights with departure token:", params.departure_token)
    #     result = load_json_data("round_return_flights.json")
    # else:
    #     print("Getting departure flights")
    #     result = load_json_data("round_go_flights.json")
    
    # print("Flight Booking payload: ")
    # print(json.dumps(query_params, indent=2))
    
    # return result

    # real-time
    try:
        print(json.dumps(query_params, indent=2))
        search = GoogleSearch(query_params)
        result = search.get_dict()
        print(result.keys())
        if "best_flights" not in result and "error" not in result:
            return {"status": 404, "error": "No flights found for the given parameters"}
        return result  # Contains 'best_flights' or 'error'
    except Exception as e:
        print("SerpAPI Error:", str(e))  # Debug log
        return {"status": 500, "error": f"Failed to fetch flights: {str(e)}"}
    

import os
import httpx
import urllib.parse

SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")  # keep your key in .env

BASE_URL = "https://serpapi.com/search.json"

async def fetch_flights(params: dict):
    # Always include engine and API key
    query = {
        "engine": "google_flights",
        "api_key": SERPAPI_API_KEY,
    }
    clean_params = {}
    for k, v in params.items():
        if isinstance(v, float) and v.is_integer():
            clean_params[k] = int(v)
        else:
            clean_params[k] = v

    query.update(clean_params)
    # query.update(params)  # merge in your own params

    url = f"{BASE_URL}?{urllib.parse.urlencode(query)}"

    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()
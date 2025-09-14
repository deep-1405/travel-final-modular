from langchain_core.tools import tool
from serpapi import GoogleSearch
from typing import Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import os
import json
from backend.load_data import load_json_data
from backend.routers.flights import router
import httpx
import asyncio

load_dotenv(override=True)

BASE_URL = "http://localhost:8000/api/"

class FlightsInput(BaseModel):
    departure_id: str = Field(description='Departure airport code (IATA)')
    arrival_id: str = Field(description='Arrival airport code (IATA)')
    outbound_date: str = Field(description='Outbound date in YYYY-MM-DD format')
    adults: Optional[int] = Field(description="Number of adults", default=1)
    children: Optional[int] = Field(description="Number of children", default=0)
    return_date: Optional[str] = Field(description="Return date in YYYY-MM-DD format", default=None)

class FlightsInputSchema(BaseModel):
    params: FlightsInput

@tool(args_schema=FlightsInputSchema)
async def get_flights(params: FlightsInput):
    '''
    Find flights using the Google Flights engine via SerpAPI.

    Args:
        params: FlightsInput object containing departure_id, arrival_id, outbound_date, adults, children, and optional return_date.

    Returns:
        dict: Flight search results containing 'best_flights' or error details.
    '''
    # print("FlightsInput:", params.model_dump())
    
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
        try:
            response = await client.post(f"{BASE_URL}flights", json={"params": params.model_dump()})
            response.raise_for_status()
            result = response.json()
            return result
        except httpx.HTTPStatusError as e:
            print(f"HTTP error occurred: {e.response.status_code}")
            try:
                print(f"Error details: {e.response.json()}")
            except ValueError:
                print(f"Error text: {e.response.text}")
                raise
        except httpx.RequestError as e:
            print(f"Request error occurred: {e}")
            raise

class BookingInput(BaseModel):
    booking_token: str = Field(description='Booking token from a flight search result')
    original_params: FlightsInput = Field(description='Original flight search parameters to ensure consistency')

class BookingInputSchema(BaseModel):
    params: BookingInput

@tool(args_schema=BookingInputSchema)
def get_booking_options(params: BookingInput):
    '''
    Fetch booking options for a specific flight using its booking token, reusing the original flight search parameters.

    Args:
        params: BookingInput object containing booking_token and original_params (FlightsInput).

    Returns:
        dict: Booking options data or error details.
    '''
    # print("BookingInput:", params.model_dump())
    print("getting booking options for booking token:", params.booking_token)
    serpapi_key = os.getenv('SERPAPI_API_KEY')
    if not serpapi_key:
        return {"status": 500, "error": "SERPAPI_API_KEY not found in environment variables"}

    query_params = {
        'api_key': serpapi_key,
        'engine': 'google_flights',
        'hl': 'en',
        'gl': 'in',
        'currency': 'INR',
        'departure_id': params.departure_id,
        'arrival_id': params.arrival_id,
        'outbound_date': params.outbound_date,
        'adults': params.adults,
        'children': params.children,
        'type': 1 if params.return_date else 2,
        'booking_token': params.booking_token
    }
    if params.return_date:
        query_params['return_date'] = params.return_date
    
    print("Flight Booking Options payload:")
    print(json.dumps(query_params, indent=2))

    #static 
    result = load_json_data("round_flights_options.json")
    return result

    #real-time
    # try:
    #     search = GoogleSearch(query_params)
    #     result = search.get_dict()
    #     # print("SerpAPI Response (Booking):", result)  # Debug log
    #     if "booking_options" not in result and "error" not in result:
    #         return {"status": 404, "error": "No booking options found for the given booking token"}
    #     return result
    # except Exception as e:
    #     print("SerpAPI Error:", str(e))  # Debug log
    #     return {"status": 500, "error": f"Failed to fetch booking options: {str(e)}"}
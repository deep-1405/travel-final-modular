from langchain_core.tools import tool
from serpapi import GoogleSearch
from typing import Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import os
import json
from backend.load_data import load_json_data

load_dotenv(override=True)

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
        "departure_id": flight_request.departure_id,
        "arrival_id": flight_request.arrival_id,
        "outbound_date": flight_request.outbound_date,
        "adults": flight_request.adults,
        "children": flight_request.children,
    })

    if hasattr(query_params, "type"):
        query_params["type"] = query_params.type
    else:
        query_params["type"] = 1 if params.return_date else 2

    if flight_request.return_date:
        query_params["return_date"] = flight_request.return_date

    
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
        search = GoogleSearch(query_params)
        result = search.get_dict()
        if "best_flights" not in result and "error" not in result:
            return {"status": 404, "error": "No flights found for the given parameters"}
        return result  # Contains 'best_flights' or 'error'
    except Exception as e:
        print("SerpAPI Error:", str(e))  # Debug log
        return {"status": 500, "error": f"Failed to fetch flights: {str(e)}"}

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
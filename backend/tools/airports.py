import os
from langchain_core.tools import tool
from backend.load_data import load_json_data
from backend.utils import fetch_geolocation, get_access_token
import httpx

@tool
async def get_airport(location: str):
    """
    Fetch the nearest airports information for a given location.
    Returns the nearest airports data if found
    Provides with IATA code required for making call to "get_flights" tools
    """

    # static
    # print(f"getting nearby airports for the: {location}")
    # lower_location = location.lower()
    # nearest_releavant_airports = {}
    # if(lower_location == 'umreth'):
    #     nearest_releavant_airports = load_json_data("airport_ahmedabad.json")
    # else:
    #     nearest_releavant_airports = load_json_data("airport_london.json")
    # return nearest_releavant_airports['data']
    
    # real-time
    try:
        coords = await fetch_geolocation(location)
        print("Coordinates:", coords)  # Debug
        if not coords:
            return {"status": 404, "response": {"title": f"NO GEOLOCATION DATA FOUND FOR {location}"}}
        lat = coords["latitude"]
        lon = coords["longitude"]
        
        access_token = await get_access_token()
        url = "https://test.api.amadeus.com/v1/reference-data/locations/airports"

        params = {
            "latitude": lat,
            "longitude": lon,
            "radius": 200  # Explicit radius in km
        }
        headers = {"Authorization": f"Bearer {access_token}"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params, headers=headers)
            print("Amadeus API Response:", response.json())  # Debug

            if response.status_code == 200:
                nearest_releavant_airports = response.json()
                if not nearest_releavant_airports.get("data"):
                    return {
                        "status": 404,
                        "response": {"title": f"NO AIRPORT FOUND NEAR {location}"}
                    }
                return nearest_releavant_airports["data"]

            if response.status_code in (400, 404):
                return {
                    "status": response.status_code,
                    "response": {"title": f"NO AIRPORT FOUND FOR {location}"}
                }

            response.raise_for_status()
    except httpx.HTTPStatusError as e:
        return {
            "status": e.response.status_code,
            "response": {"title": f"FAILED TO FETCH AIRPORT: {str(e)}"}
        }
    except Exception as e:
        return {
            "status": 500,
            "response": {"title": f"ERROR PROCESSING REQUEST: {str(e)}"}
        }

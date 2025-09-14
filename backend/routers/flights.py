import os
import httpx
# from typing import Optional
# from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException
from dotenv import load_dotenv
from backend.utils import format_params, merge_flights_fields
import urllib.parse

load_dotenv(override=True)

router = APIRouter(prefix="/api/flights", tags=["flights"])

serpapi_key = os.getenv("SERPAPI_API_KEY")
BASE_URL = "https://serpapi.com/search.json"

SERPAPI_PARAMETERS = {
    'api_key': serpapi_key,
    'engine': 'google_flights',
    'hl': 'en',
    'gl': 'in',
    'currency': 'INR'
}

async def fetch_flights(params: dict):
    clean_params = format_params(params)
    if(clean_params.get("return_date")):
        clean_params["return_date"] = clean_params.get("return_date")
        clean_params["type"] = 1
    else:
        clean_params["type"] = 2
    query_params = SERPAPI_PARAMETERS | clean_params

    url = f"{BASE_URL}?{urllib.parse.urlencode(query_params)}"

    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
        response = await client.get(url)
        response.raise_for_status()
        
        # response_data = response.json()
        try:
            response_data = response.json()
        except ValueError as e:
            raise HTTPException(status_code=500, detail="Failed to parse API response as JSON")
        update_response = merge_flights_fields(response_data)
        return update_response

@router.post("")
async def get_flights(params: dict):
    """
    ## Retrieve a list of flights for given params

    ### Query Parameters
    - **api_key**: SerpAPI key  
    - **engine**: Google Flights engine  
    - **hl**: Response language  
    - **gl**: Geo location  
    - **currency**: Currency for flight prices  
    - **departure_id**: IATA code of departure airport  
    - **arrival_id**: IATA code of arrival airport  
    - **outbound_date**: Outbound date in YYYY-MM-DD format  
    - **adults**: Number of adults travelling  
    - **children**: Number of children travelling  
    - **return_date**: Return date in YYYY-MM-DD format  
    - **type**: 1 = round-trip if return_date present, else 2 = one-way trip  
    - **departure_token**: Token for getting return flights (round-trip only)  

    ### Returns
    JSON response with:
    - List of available flights  
    - Search metadata  
    - Price insights  
    - Airports involved  

    ### Raises
    - **HTTPException**: If the params are invalid or SerpAPI fails  
    """
    try:
        result = await fetch_flights(params)
        return result
    except HTTPException as e:
        print("Error:", e.response.status_code)
        try:
            error_info = e.response.json()
            print("Error details:", error_info)
        except ValueError:
            print("Error text:", e.response.text)
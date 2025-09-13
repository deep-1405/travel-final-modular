import json
import os

# Base directory where JSON files are stored
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "flight_responses"))

def load_json_data(filename: str) -> dict:
    """Load JSON data from a file in the flight_responses folder."""
    filepath = os.path.join(BASE_DIR, filename)
    try:
        with open(filepath, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {"status": 404, "error": f"JSON file {filename} not found at {filepath}"}
    except json.JSONDecodeError:
        return {"status": 500, "error": f"Failed to parse JSON file {filename}"}

# Load static JSON data
# ROUND_GO_FLIGHTS = load_json_data("round_go_flights.json")
# ROUND_RETURN_FLIGHTS = load_json_data("round_return_flights.json")
# ROUND_FLIGHTS_OPTIONS = load_json_data("round_flights_options.json")
# print(ROUND_GO_FLIGHTS)
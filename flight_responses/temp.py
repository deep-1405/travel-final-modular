import json
import os
import sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.append(PROJECT_ROOT)
from backend.utils import merge_flights_fields
with open('round_go_flights.json', 'r') as file:
    json_data = json.load(file)

# Merge best_flights and other_flights into flights
result = merge_flights_fields(json_data)

# Save the modified JSON to a new file
with open('modified_flights.json', 'w') as file:
    json.dump(result, file, indent=4)

# Print the modified JSON (for verification)
print(json.dumps(result, indent=4))
import re
import requests
from typing import Optional, List, Dict

def format_duration(minutes: Optional[int]) -> str:
    if minutes is None:
        return ""
    hours, mins = divmod(int(minutes), 60)
    if hours and mins:
        return f"{hours} hr {mins} min"
    elif hours:
        return f"{hours} hr"
    else:
        return f"{mins} min"

def extract_redirect_url(html_content: str) -> Optional[str]:
    match = re.search(r"content=\"0;url='(.*?)'\"", html_content, re.IGNORECASE)
    if match:
        return match.group(1)
    return None

def book_flight(post_data: str) -> str:
    if not post_data:
        return "No booking link provided."
    url = "https://www.google.com/travel/clk/f"
    if post_data.startswith("u="):
        post_data_value = post_data[2:]
    else:
        post_data_value = post_data
    try:
        response = requests.post(url, data={"u": post_data_value})
        if response.status_code == 200:
            redirect_url = extract_redirect_url(response.text)
            if redirect_url:
                return f"[Click here to complete booking]({redirect_url})"
            else:
                return "Failed to extract redirect URL from response."
        else:
            return f"Failed to initiate booking. Status code: {response.status_code}"
    except Exception as e:
        return f"Error during booking: {str(e)}"

def build_details(index: Optional[int], flights: Dict) -> str:
    if index is None or index < 0 or index >= len(flights):
        return "Select a flight below to see full details"
    best_flights = flights.get("best_flights")
    flight = best_flights[index]
    details = f"## ✈️ Flight Option {index+1}\n"
    details += f"**Total Duration:** {format_duration(flight.get('total_duration'))}\n"
    details += f"**Price:** ₹{flight.get('price', 'N/A')}\n"
    details += f"**Type:** {flight.get('type', 'N/A')}\n"
    carbon = flight.get('carbon_emissions', {})
    details += f"**Carbon Emissions:** {carbon.get('this_flight', 'N/A')} g (vs {carbon.get('typical_for_this_route', 'N/A')}; difference: {carbon.get('difference_percent', 'N/A')}%) \n\n"

    for i, f in enumerate(flight.get("flights", []), 1):
        details += f"### Leg {i}\n"
        dep = f.get('departure_airport', {})
        arr = f.get('arrival_airport', {})
        details += f"- **Route:** {dep.get('name')} ({dep.get('id')}, {dep.get('time')}) → {arr.get('name')} ({arr.get('id')}, {arr.get('time')})\n"
        details += f"- **Airline:** {f.get('airline')} ({f.get('flight_number')})\n"
        if 'ticket_also_sold_by' in f and f['ticket_also_sold_by']:
            details += f"- **Also Sold By:** {', '.join(f['ticket_also_sold_by'])}\n"
        details += f"- **Aircraft:** {f.get('airplane')} | **Class:** {f.get('travel_class')}\n"
        details += f"- **Duration:** {format_duration(f.get('duration'))}\n"
        details += f"- **Legroom:** {f.get('legroom', 'N/A')}\n"
        details += f"- **Extensions:** {', '.join(f.get('extensions', []))}\n"
        if 'overnight' in f and f['overnight']:
            details += "- **Overnight:** Yes\n\n"
        else:
            details += "\n"

    if "layovers" in flight and flight["layovers"]:
        details += "## Layovers\n"
        for layover in flight["layovers"]:
            overnight = " (Overnight)" if 'overnight' in layover and layover['overnight'] else ""
            details += f"- {layover.get('name')} ({layover.get('id')}): {format_duration(layover.get('duration'))} {overnight}\n"

    return details

def ordinal(n: int) -> str:
    """Convert integer into its ordinal representation (1 -> 1st, 2 -> 2nd, etc)."""
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"
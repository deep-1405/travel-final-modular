import gradio as gr
from typing import Optional, List, Dict
from utils.helpers import format_duration, build_details, ordinal
from backend.agents.travel_agent import TravelAgent
import json
from langchain_core.messages import ToolMessage
from backend import utils

MAX_FLIGHTS = 20
MAX_BOOKING_OPTIONS = 10
VIEW_OUTBOUND_CARDS = "outbound cards"
VIEW_RETURN_CARDS = "return cards"
VIEW_OUTBOUND_DETAILS = "outbound details"
VIEW_RETURN_DETAILS = "return details"
VIEW_BOOKING = "booking"
PLACEHOLDER_IMAGE_URL = "https://via.placeholder.com/32"

class UIManager:
    @staticmethod
    def get_card_html(idx: int, flight: Dict, selected: bool = False) -> str:
        first = flight["flights"][0] if flight.get("flights") else {}
        last = flight["flights"][-1] if flight.get("flights") else {}
        stops = len(flight.get("flights", [])) - 1
        stops_text = f"{stops} stop{'s' if stops != 1 else ''}" if stops > 0 else "Non-stop"
        logos = "".join(
            # f'<img src="{f.get("airline_logo", "")}" title="{f.get("airline", "")}" onerror="this.src=\'https://via.placeholder.com/32\'">'
            f'<img src="{f.get("airline_logo", "")}"'
            f'title="{f.get("airline", "")}"'
            f' onerror="this.src={PLACEHOLDER_IMAGE_URL}">'
            for f in flight.get("flights", [])
        )
        selected_class = "selected" if selected else ""
        return f"""
        <div class="card {selected_class}" id="card-{idx}">
            <div class="logo-chain">{logos}</div>
            <div class="route">{first.get('departure_airport', {}).get('id', '')} → {last.get('arrival_airport', {}).get('id', '')}</div>
            <div class="price">₹{flight.get('price', 'N/A')}</div>
            <div class="duration">{format_duration(flight.get('total_duration'))} total</div>
            <div class="stops">{stops_text}</div>
        </div>
        """

    @staticmethod
    def update_cards(selected: int, flight_data: Dict) -> List[str]:
        if selected is not None:
            print(f"Selected {ordinal(selected + 1)} card, updating highlights")
        else:
            print("Reloading flight cards")

        best_flights = flight_data.get("best_flights", []) if flight_data else []
        other_flights = flight_data.get("other_flights", []) if flight_data else []
        flights = best_flights + other_flights
        
        html_updates = []
        for idx in range(MAX_FLIGHTS):
            if idx < len(flights):
                html_updates.append(UIManager.get_card_html(idx, flights[idx], idx == selected))
            else:
                html_updates.append("")
        return html_updates

    @staticmethod
    def update_flight_interface(flight_data: Dict):
        if(flight_data):
            print(f"loading outbound flights")
        
        best_flights = flight_data.get("best_flights", []) if flight_data else []
        other_flights = flight_data.get("other_flights", []) if flight_data else []
        flights = best_flights + other_flights

        visible = bool(flights)
        html_updates = []
        visible_updates = []
        for idx in range(MAX_FLIGHTS):
            if idx < len(flights):
                html_updates.append(UIManager.get_card_html(idx, flights[idx]))
                visible_updates.append(gr.update(visible=True))
            else:
                html_updates.append("")
                visible_updates.append(gr.update(visible=False))
        return gr.update(visible=visible), *html_updates, *visible_updates

    @staticmethod
    def update_booking_ui(booking_data: Dict):
        print(f"Loading booking options...")
        
        booking_options = booking_data.get("booking_options", []) if booking_data else []
        group_visibles = []
        info_updates = []
        button_values = []
        for i in range(MAX_BOOKING_OPTIONS):
            if i < len(booking_options):
                option = booking_options[i].get("together", {})
                book_with = option.get("book_with", "Unknown")
                price = option.get("price", "N/A")
                currency = booking_data.get("search_parameters", {}).get("currency", "INR") if booking_data else "INR"
                flight_numbers = ', '.join(option.get("marketed_as", []))
                baggage = ', '.join(option.get("baggage_prices", []))
                info = f"### Option {i+1}: {book_with}\n**Price**: {price} {currency}\n**Flights**: {flight_numbers}\n**Baggage**: {baggage}"
                group_visibles.append(gr.update(visible=True))
                info_updates.append(info)
                button_values.append(gr.update(value=f"Book with {book_with}", visible=True))
            else:
                group_visibles.append(gr.update(visible=False))
                info_updates.append("")
                button_values.append(gr.update(visible=False))
        return group_visibles + info_updates + button_values

    @staticmethod
    def get_flight_details(selected: int, flight_data: Dict, params: Dict):
        
        print(f"Showing flight details for {ordinal(selected)} flight")
        print(f"params: {json.dumps(params, indent=2)}")
        if params.get("return_date"):
            return VIEW_OUTBOUND_DETAILS, build_details(selected, flight_data)
        else:
            if params.get("departure_token"):
                return VIEW_RETURN_DETAILS, build_details(selected, flight_data)
            elif params.get("booking_token"):
                return VIEW_BOOKING, build_details(selected, flight_data)

    @staticmethod
    async def on_booking_options(selected: int, flight_data: Dict, initial_payload: Dict):
        best_flights = flight_data.get("best_flights", []) if flight_data else []
        other_flights = flight_data.get("other_flights", []) if flight_data else []
        flights = best_flights + other_flights

        booking_token = flights[selected].get("booking_token", "")

        print(f"Selected flight booking token: {booking_token}")
        print(f"Fetching booking options for {ordinal(selected)} flight")

        if not booking_token:
            print("no booking token found for the selected flight.")
            return VIEW_BOOKING, {"error": "No booking token available"}

        booking_input = {
            **initial_payload,
            "booking_token": booking_token,
        }

        # state = TravelAgent.State(messages=[TravelAgent.HumanMessage(content=json.dumps({
        #     "tool_call": {
        #         "name": "get_booking_options",
        #         "arguments": {"params": booking_input}
        #     }
        # }))])
        # config = {"configurable": {"thread_id": TravelAgent.make_thread_id()}}
        # result = await TravelAgent.graph.ainvoke(state, config=config)
        result = utils.get_booking_options(booking_input)
        booking_data = result
        # messages = result.get("messages", [])
        # for message in reversed(messages):
        #     if isinstance(message, ToolMessage) and message.name == "get_booking_options":
        #         try:
        #             booking_data = json.loads(message.content)
        #         except json.JSONDecodeError:
        #             booking_data = {"error": "Failed to parse booking data"}
        #         break
        print(booking_data)
        print("Booking options loaded")
        return VIEW_BOOKING, booking_data
    
    @staticmethod
    async def on_get_return_flights(selected: int, flight_data: Dict, initial_payload: Dict):

        best_flights = flight_data.get("best_flights", []) if flight_data else []
        other_flights = flight_data.get("other_flights", []) if flight_data else []
        flights = best_flights + other_flights

        departure_token = flights[selected].get("departure_token", "")
        
        print(f"Selected flight departure token: {departure_token}")
        print(f"Fetching return flights for the {ordinal(selected + 1)} flight")
        
        if not departure_token:
            print("No departure token found for selected flight.")
            return VIEW_RETURN_CARDS, {"error": "No departure token available"}
        
        departure_input = {
            **initial_payload,
            "departure_token": departure_token
        }
        # result = utils.get_flights(departure_input)
        result = await utils.fetch_flights(departure_input)
        flight_data = result
        print("return flights data", json.dumps(flight_data, indent=2))

        print("Return flights loaded")
        return VIEW_RETURN_CARDS, flight_data

    @staticmethod
    def update_view(view: str):
        if view == VIEW_OUTBOUND_CARDS:
            return gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False)
        elif view == VIEW_RETURN_CARDS:
            return gr.update(visible=False), gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False)
        elif view == VIEW_OUTBOUND_DETAILS:
            return gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), gr.update(visible=False), gr.update(visible=False)
        elif view == VIEW_RETURN_DETAILS:
            return gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), gr.update(visible=False)
        elif view == VIEW_BOOKING:
            return gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=True)
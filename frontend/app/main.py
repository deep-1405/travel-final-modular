# Gradio App Setup
import gradio as gr
from frontend.components.ui_manager import UIManager
from backend.agents.travel_agent import TravelAgent
from utils.helpers import build_details, book_flight
MAX_FLIGHTS = 20
MAX_BOOKING_OPTIONS = 10
VIEW_OUTBOUND_CARDS = "outbound cards"
VIEW_RETURN_CARDS = "return cards"
VIEW_OUTBOUND_DETAILS = "outbound details"
VIEW_RETURN_DETAILS = "return details"
VIEW_BOOKING = "booking"

CSS = """
    .card-container {
        position: relative;
        width: 250px;
        margin: 10px;
    }
    .card {
        border: 1px solid #d1d5db;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        transition: 0.2s ease-in-out;
        box-shadow: 0 4px 8px rgba(0,0,0,0.05);
        background: #fafafa;
        width: 100%;
        box-sizing: border-box;
    }
    .card:hover {
        background: #f3f4f6;
        transform: scale(1.02);
        box-shadow: 0 6px 14px rgba(0,0,0,0.1);
    }
    .card.selected {
        border: 2px solid #2563eb;
        box-shadow: 0 6px 14px rgba(0,0,0,0.2);
        background: #eff6ff;
    }
    .logo-chain {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 6px;
        margin-bottom: 8px;
    }
    .logo-chain img {
        max-height: 36px;
        width: auto;
    }
    .route {
        font-weight: 700;
        font-size: 18px;
        color: #111827;
        margin-bottom: 4px;
    }
    .price {
        font-weight: 700;
        color: #1d4ed8;
        font-size: 16px;
        margin-bottom: 4px;
    }
    .duration {
        font-size: 14px;
        color: #374151;
        margin-bottom: 4px;
    }
    .stops {
        font-size: 14px;
        color: #374151;
    }
    .click-overlay {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        opacity: 0;
        cursor: pointer;
    }
    #confirm-button {
        margin-top: 20px;
        width: 100%;
    }
    #details-section {
        margin-top: 20px;
    }
"""

def create_travel_app():
    travel_agent = TravelAgent()

    def create_booking_handler(option_index):
        """Create booking handler for specific option"""
        def handle_booking(booking_data):
            booking_options = booking_data.get("booking_options", []) if booking_data else []
            if option_index < len(booking_options):
                post_data = booking_options[option_index].get("together", {}).get("booking_request", {}).get("post_data", "")
                return book_flight(post_data)
            return "⚠️ Invalid option"
        return handle_booking

    def update_button_visibility(params):
        if(params):
            type_ = 1 if params.get("return_date") else 2

            if type_ == 2:  # One-way
                return gr.update(visible=True), gr.update(visible=False)
            elif type_ == 1:  # Round-trip
                return gr.update(visible=False), gr.update(visible=True)
        return gr.update(visible=False), gr.update(visible=False)

    with gr.Blocks(theme=gr.themes.Default(primary_hue="emerald"), css=CSS) as demo:
        gr.Markdown("Enter your travel query")
        
        thread_id_state = gr.State(travel_agent.make_thread_id())
        current_view = gr.State(value=VIEW_OUTBOUND_CARDS)
        initial_flight_payload = gr.State(value={})
        outbound_flights_state = gr.State(value={})
        selected_outbound_index = gr.State(value=None)
        return_flights_state = gr.State(value={})
        selected_return_index = gr.State(value=None)
        booking_data_state = gr.State(value={})
        
        with gr.Row():
            with gr.Column():
                chatbot = gr.Chatbot(label="Travel Chatbot", height=600, type="messages")
            
            with gr.Column(visible=False) as flight_section:
                gr.Markdown("# 🛫 Available Flights")
                
                
                with gr.Column(visible=True) as outbound_flight_cards:
                    with gr.Row():
                        outbound_card_html_components = []
                        outbound_card_containers = []
                        for card_index in range(MAX_FLIGHTS):
                            with gr.Column(elem_classes=["card-container"], visible=False) as card_col:
                                card_html = gr.HTML("")
                                card_button = gr.Button("", elem_classes=["click-overlay"])
                                # the button is being binded to function upon click event
                                outbound_card_html_components.append(card_html)
                                card_button.click(
                                    fn=lambda x=card_index: x,
                                    outputs=selected_outbound_index
                                ).then(
                                    fn=UIManager.update_cards,
                                    inputs=[selected_outbound_index, outbound_flights_state],
                                    outputs=outbound_card_html_components
                                )
                            outbound_card_containers.append(card_col)
                    outbound_view_flight_button = gr.Button("View Flight", interactive=False, elem_id="confirm-button")
                
                with gr.Column(visible=False) as outbound_flight_details:
                    outbound_flight_details_box = gr.Markdown()
                    with gr.Row():
                        outbound_details_go_back_button = gr.Button("Go Back")
                        outbound_booking_options_button = gr.Button("Finalise Flight", visible=False)  # Initially hidden
                        get_return_flights_button = gr.Button("Get Return Flights", visible=False)  # Initially hidden
                        # elif initial_flight_payload.get("type") == 1:

                with gr.Column(visible=False) as return_flight_cards:
                    with gr.Row():
                        return_card_html_components = []
                        return_card_containers = []
                        for card_index in range(MAX_FLIGHTS):
                            with gr.Column(elem_classes=["card-container"], visible=False) as card_col:
                                card_html = gr.HTML("")
                                card_button = gr.Button("", elem_classes=["click-overlay"])
                                return_card_html_components.append(card_html)
                                # the button is being binded to function upon click event
                                card_button.click(
                                    fn=lambda x=card_index: x,
                                    outputs=selected_return_index
                                ).then(
                                    fn=UIManager.update_cards,
                                    inputs=[selected_return_index, return_flights_state],
                                    outputs=return_card_html_components
                                )
                            return_card_containers.append(card_col)

                    return_flights_go_back_button = gr.Button("Go Back")
                    return_view_flight_button = gr.Button("View Flight", interactive=False, elem_id="confirm-button")

                
                with gr.Column(visible=False) as return_flight_details:
                    return_flight_details_box = gr.Markdown()
                    with gr.Row():
                        # if initial_flight_payload:
                            # if initial_flight_payload.get("type") == 1 and initial_flight_payload.get("departure_token"):
                        return_details_go_back_button = gr.Button("Go Back")
                        return_booking_options_button = gr.Button("Finalise Flight")
                
                with gr.Column(visible=False) as flight_booking_section:
                    gr.Markdown("# Flight Booking Options")
                    gr.Markdown("Select a booking option to proceed to the booking partner's website.")
                    
                    booking_groups = []
                    info_mds = []
                    booking_buttons = []
                    booking_results = []
                    
                    for i in range(MAX_BOOKING_OPTIONS):
                        with gr.Group(visible=False) as group:
                            info_md = gr.Markdown("")
                            btn = gr.Button("Book")
                            result = gr.Markdown(label=f"Booking Result {i+1}")
                            
                            info_mds.append(info_md)
                            booking_buttons.append(btn)
                            booking_results.append(result)
                            
                            btn.click(
                                fn=create_booking_handler(i),
                                inputs=booking_data_state,
                                outputs=booking_results[i]
                            )
                        booking_groups.append(group)

        with gr.Group():
            with gr.Row():
                message = gr.Textbox(show_label=False, placeholder="Enter your travel query")
        with gr.Row():
            reset_button = gr.Button("Reset", variant="stop")
            go_button = gr.Button("Go!", variant="primary")

        # (0) user clicks on "go" button or "enter" inside the textbox -> message is processed and flight cards are shown if available
        message.submit(
            fn=travel_agent.process_message,
            inputs=[message, chatbot, thread_id_state],
            outputs=[chatbot, outbound_flights_state, initial_flight_payload]
        ).then(
            fn=UIManager.update_flight_interface,
            inputs=[outbound_flights_state],
            outputs=[flight_section] + outbound_card_html_components + outbound_card_containers
        ).then(
            fn=update_button_visibility,
            inputs=initial_flight_payload,
            outputs=[outbound_booking_options_button, get_return_flights_button]
        )

        go_button.click(
            fn=travel_agent.process_message,
            inputs=[message, chatbot, thread_id_state],
            outputs=[chatbot, outbound_flights_state, initial_flight_payload]
        ).then(
            fn=UIManager.update_flight_interface,
            inputs=[outbound_flights_state],
            outputs=[flight_section] + outbound_card_html_components + outbound_card_containers
        ).then(
            fn=update_button_visibility,
            inputs=initial_flight_payload,
            outputs=[outbound_booking_options_button, get_return_flights_button]
        )
        
        # (1) User clicks on the outbound flights cards -> view flight button becomes interactive
        selected_outbound_index.change(
            fn=lambda idx: gr.update(interactive=idx is not None),
            inputs=selected_outbound_index,
            outputs=outbound_view_flight_button
        )
        
        # (2) User clicks on the "view flight" button -> flight details are shown
        outbound_view_flight_button.click(
            fn=UIManager.get_flight_details,
            inputs=[selected_outbound_index, outbound_flights_state, initial_flight_payload],
            outputs=[current_view, outbound_flight_details_box]
        ).then(
            fn=UIManager.update_view,
            inputs=current_view,
            outputs=[outbound_flight_cards, return_flight_cards, outbound_flight_details, return_flight_details, flight_booking_section]
        )

        # (3) User clicks on the "go back" button -> outbound flight cards are shown again
        outbound_details_go_back_button.click(
            fn=lambda: (None, VIEW_OUTBOUND_CARDS),
            outputs=[selected_outbound_index, current_view]
        ).then(
            fn=UIManager.update_view,
            inputs=current_view,
            outputs=[outbound_flight_cards, return_flight_cards, outbound_flight_details, return_flight_details, flight_booking_section]
        ).then(
            fn=UIManager.update_cards,
            inputs=[selected_outbound_index, outbound_flights_state],
            outputs=outbound_card_html_components
        )

        # (4) user clicks on "finalise flight" button -> booking options are shown (type = 2)
        outbound_booking_options_button.click(
            fn=UIManager.on_booking_options,
            inputs=[selected_outbound_index, outbound_flights_state, initial_flight_payload],
            outputs=[current_view, booking_data_state]
        ).then(
            fn=UIManager.update_view,
            inputs=current_view,
            outputs=[outbound_flight_cards, return_flight_cards, outbound_flight_details, return_flight_details, flight_booking_section]
        ).then(
            fn=UIManager.update_booking_ui,
            inputs=booking_data_state,
            outputs=booking_groups + info_mds + [b for b in booking_buttons]
        )

        # (5) user clicks on "get return flights" button -> return flight cards are show (type = 1)
        get_return_flights_button.click(
            fn=UIManager.on_get_return_flights,
            inputs=[selected_outbound_index, outbound_flights_state, initial_flight_payload],
            outputs=[current_view, return_flights_state]
        ).then(
            fn=UIManager.update_view,
            inputs=current_view,
            outputs=[outbound_flight_cards, return_flight_cards, outbound_flight_details, return_flight_details, flight_booking_section]
        ).then(
            fn=UIManager.update_cards,
            inputs=[selected_return_index, return_flights_state],
            outputs=return_card_html_components
        )

        # (6) user clicks on any of the return flight cards -> view flight button becomes interactive
        selected_return_index.change(
            fn=lambda idx: gr.update(interactive=idx is not None),
            inputs=selected_return_index,
            outputs=return_view_flight_button
        )

        # (7) use clicks on "go back" button -> outbound flight details are shown again
        return_flights_go_back_button.click(
            fn=lambda: (VIEW_OUTBOUND_DETAILS),
            outputs=[current_view]
        ).then(
            fn=UIManager.update_view,
            inputs=current_view,
            outputs=[outbound_flight_cards, return_flight_cards, outbound_flight_details, return_flight_details, flight_booking_section]
        ).then(
            fn=build_details,
            inputs=[selected_outbound_index, outbound_flights_state],
            outputs=outbound_flight_details_box
        )

        # (8) user clicks on "view flight" button -> return flight details are shown
        return_view_flight_button.click(
            fn=UIManager.get_flight_details,
            inputs=[selected_return_index, return_flights_state, initial_flight_payload],
            outputs=[current_view, return_flight_details_box]
        ).then(
            fn=UIManager.update_view,
            inputs=current_view,
            outputs=[outbound_flight_cards, return_flight_cards, outbound_flight_details, return_flight_details, flight_booking_section]
        )

        # (9) use clicks on "go back" button -> return flight cards are shown again
        return_details_go_back_button.click(
            fn=lambda: (None, VIEW_RETURN_CARDS),
            outputs=[selected_return_index, current_view]
        ).then(
            fn=UIManager.update_view,
            inputs=current_view,
            outputs=[outbound_flight_cards, return_flight_cards, outbound_flight_details, return_flight_details, flight_booking_section]
        ).then(
            fn=UIManager.update_cards,
            inputs=[selected_return_index, return_flights_state],
            outputs=return_card_html_components
        )

        # (10) user clicks on "finalise flight" button -> booking options are shown
        return_booking_options_button.click(
            fn=UIManager.on_booking_options,
            inputs=[selected_return_index, return_flights_state, initial_flight_payload],
            outputs=[current_view, booking_data_state]
        ).then(
            fn=UIManager.update_view,
            inputs=current_view,
            outputs=[outbound_flight_cards, return_flight_cards, outbound_flight_details, return_flight_details, flight_booking_section]
        ).then(
            fn=UIManager.update_booking_ui,
            inputs=booking_data_state,
            outputs=booking_groups + info_mds + [b for b in booking_buttons]
        )

        # (11) user clicks on "reset" button -> everything is reset
        reset_button.click(
            fn=travel_agent.reset,
            inputs=[],
            outputs=[message, chatbot, thread_id_state, outbound_flights_state]
        ).then(
            fn=UIManager.update_flight_interface,
            inputs=outbound_flights_state,
            outputs=[flight_section] + outbound_card_html_components + outbound_card_containers
        )

    return demo

if __name__ == "__main__":
    demo = create_travel_app()
    demo.launch()
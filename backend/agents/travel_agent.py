import os
import json
import uuid
from datetime import datetime
from typing import Annotated, List, Dict, Tuple
from pydantic import BaseModel
from langgraph.graph.message import add_messages
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, StateGraph, START
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode
from dotenv import load_dotenv
import sys
from typing import Optional
import gradio as gr

load_dotenv(override=True)
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), '..')))
from backend.tools.airports import get_airport
from backend.tools.flights import get_flights, get_booking_options

class State(BaseModel):
    messages: Annotated[List, add_messages]

class TravelAgent:
    google_api_key = os.getenv("google_api_key")
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=google_api_key
    )
    current_year = datetime.now().year
    TOOLS = [get_airport, get_flights, get_booking_options]
    graph = None

    def __init__(self):
        system_message = f"""
            you are a smart travel agency, use the tool to lookup information
            only lookup information when you are sure you want that
            If you need to look up some information before asking a follow up question, you are allowed to do that!
            respond with flights from departure city to arrival city
            current year is: {self.current_year}
        """
        self.memory = MemorySaver()
        self.graph = self._build_graph(system_message)

    def _build_graph(self, system_message):
        graph_builder = StateGraph(State)
        graph_builder.add_node("worker", lambda state: self._worker(state, system_message))
        graph_builder.add_node("tools", ToolNode(tools=self.TOOLS))
        graph_builder.add_edge(START, "worker")
        graph_builder.add_conditional_edges("worker", self._worker_router, {"tools": "tools", END: END})
        graph_builder.add_edge("tools", "worker")
        return graph_builder.compile(checkpointer=self.memory)

    def _worker(self, state: State, system_message: str):
        messages = [SystemMessage(content=system_message)] + state.messages
        worker_llm = self.llm.bind_tools(self.TOOLS)
        response = worker_llm.invoke(messages)
        print(json.dumps(state.model_dump(), indent=2, default=str))

        return {'messages': [response]}

    def _worker_router(self, state: State) -> str:
        last_message = state.messages[-1]
        print("-"*50)
        print(json.dumps(state.model_dump(), indent=2, default=str))

        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return END

    @staticmethod
    def make_thread_id() -> str:
        return str(uuid.uuid4())

    async def process_message(self, message: str, history: List, thread: str) -> Tuple[List, Dict, Dict, Dict]:
        """"
        process used message when user clicks "enter" or "go button" inside the chatbot
        invokes the graph with the 
        """
        config = {"configurable": {"thread_id": thread}}
        # as the accumulator is add_message, the state message will be updated automatically
        state = State(messages=[HumanMessage(content=message)])
        try:
            result = await self.graph.ainvoke(state, config=config)
        except Exception as e:
            print(f"Graph error: {e}")
            return history + [{"role": "assistant", "content": f"System error: {str(e)}"}], {"error": str(e)}
        
        user = {"role": "user", "content": message}
        ai_msg = result["messages"][-1]
        reply = {"role": "assistant", "content": ai_msg.content}
        history = history + [user, reply]

        flight_data, original_params = self._extract_flight_data_and_params(result["messages"])
        if self._has_available_flights(flight_data):
            history[-1]["content"] += "\n\nI've loaded the available flights in the panel to the right. Please select one to view details and booking options."
        
        return history, flight_data, original_params
        

    def _extract_flight_data_and_params(self, messages: List) -> Tuple[Dict, Optional[Dict]]:
        """Extract flight data and original params from tool response messages"""
        flight_data = {}
        original_params = None

        for message in reversed(messages):
            if isinstance(message, ToolMessage) and message.name == "get_flights": # this thing is looking for the tool message coming from the tool, the message coming from the tool node is flights data in this case 
                try:
                    flight_data = json.loads(message.content)
                    for prev_msg in reversed(messages):
                        # here we need to find the params used for tool calls by backtracking the messages again as the tool message only contains response coming from the tool, params used to call the tool is not part of it, it is present inside the tool call of the previos message
                        if hasattr(prev_msg, "tool_calls"):
                            for call in prev_msg.tool_calls:
                                if isinstance(call, dict):
                                    print("is a dict")
                                    if call.get("name") == "get_flights":
                                        original_params = call.get("args", {}).get("params", {})
                                        break
                                else:
                                    print("is an object")
                                    if getattr(call, "name", None) == "get_flights":
                                        original_params = getattr(call, "args", {}).get("params", {})
                                        break
                except json.JSONDecodeError:
                    flight_data = {"error": "Failed to parse flight data"}
                break
        print("original_params:", original_params)
        return flight_data, original_params

    def _has_available_flights(self, flight_data: Dict) -> bool:
        """Check if flight data contains available flights"""
        return bool(flight_data.get("best_flights"))
    
    async def reset(self):
        return "", [], self.make_thread_id(), {}
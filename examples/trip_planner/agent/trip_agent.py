"""
Trip Planner Agent - Compatible with AG2 >= 0.7.4

Changes from older versions:
- Uses AssistantAgent instead of SwarmAgent (recommended)
- Uses register_hand_off() standalone function
- Uses OnCondition and AfterWork (new names)
"""

import os
import json
import requests
import copy
from typing import Any, Dict
from pydantic import BaseModel

from autogen import AssistantAgent, UserProxyAgent
from autogen.agentchat.contrib.swarm_agent import (
    AfterWork,
    OnCondition,
    SwarmResult,
    initiate_swarm_chat,
    register_hand_off,
)


# Pydantic models for structured output
class Event(BaseModel):
    type: str  # Attraction, Restaurant, Travel
    location: str
    city: str
    description: str


class Day(BaseModel):
    events: list[Event]


class Itinerary(BaseModel):
    days: list[Day]


# Initialize LLM Configuration
config_list = [
    {
        "model": "gpt-4o",
        "api_key": os.environ.get("OPENAI_API_KEY"),
    }
]

llm_config = {"config_list": config_list, "timeout": 120}


def _fetch_travel_time(origin: str, destination: str) -> dict:
    """Retrieves route information using Google Maps Directions API."""
    endpoint = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": origin,
        "destination": destination,
        "mode": "walking",
        "key": os.environ.get("GOOGLE_MAP_API_KEY"),
    }
    
    try:
        response = requests.get(endpoint, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            return {
                "error": "Failed to retrieve route information",
                "status_code": response.status_code,
            }
    except Exception as e:
        return {"error": str(e)}


def add_travel_times_to_itinerary(itinerary_data: dict) -> dict:
    """Add travel times between events in the itinerary using Google Maps API."""
    if not isinstance(itinerary_data, dict) or "days" not in itinerary_data:
        return itinerary_data
    
    google_api_key = os.environ.get("GOOGLE_MAP_API_KEY")
    if not google_api_key:
        print("Warning: GOOGLE_MAP_API_KEY not set. Skipping travel time calculations.")
        return itinerary_data
    
    for day in itinerary_data["days"]:
        if "events" not in day:
            continue
            
        events = day["events"]
        new_events = []
        
        for i, event in enumerate(events):
            new_events.append(event)
            
            # Add travel event between this and next event
            if i < len(events) - 1:
                current_event = event
                next_event = events[i + 1]
                
                origin = f"{current_event['location']}, {current_event['city']}"
                destination = f"{next_event['location']}, {next_event['city']}"
                
                maps_response = _fetch_travel_time(origin, destination)
                
                if "routes" in maps_response and len(maps_response["routes"]) > 0:
                    try:
                        leg = maps_response["routes"][0]["legs"][0]
                        travel_time = f"{leg['duration']['text']} ({leg['distance']['text']})"
                        
                        new_events.append({
                            "type": "Travel",
                            "location": f"Walking from {current_event['location']} to {next_event['location']}",
                            "city": current_event["city"],
                            "description": travel_time
                        })
                    except Exception as e:
                        print(f"Error adding travel time: {e}")
        
        day["events"] = new_events
    
    return itinerary_data


def create_trip_planner(destination: str, num_days: int, preferences: str):
    """
    Create a trip itinerary based on user inputs using AI agents
    
    Args:
        destination: City to visit (e.g., "Rome", "Paris", "Tokyo")
        num_days: Number of days for the trip
        preferences: User preferences (e.g., "historical sites, Italian food")
    """
    
    # Context for the swarm
    trip_context = {
        "itinerary_confirmed": False,
        "itinerary": "",
        "structured_itinerary": None,
        "destination": destination,
        "num_days": num_days,
        "preferences": preferences,
    }
    
    def mark_itinerary_as_complete(
        final_itinerary: str, context_variables: Any
    ) -> SwarmResult:
        """Store and mark our itinerary as accepted."""
        # Normalize framework-provided context into a plain dict
        try:
            if not isinstance(context_variables, dict):
                if hasattr(context_variables, "data"):
                    context_variables = dict(context_variables.data)
                elif hasattr(context_variables, "dict"):
                    context_variables = dict(context_variables.dict())
                else:
                    context_variables = {}
        except Exception:
            context_variables = {}

        context_variables["itinerary_confirmed"] = True
        context_variables["itinerary"] = final_itinerary
        
        return SwarmResult(
            agent="structured_output_agent",
            context_variables=context_variables,
            values="Itinerary recorded and confirmed.",
        )
    
    def create_structured_itinerary(
        context_variables: Any, structured_itinerary: Any
    ) -> SwarmResult:
        """Once a structured itinerary is created, store it."""
        # Normalize context to plain dict
        try:
            if not isinstance(context_variables, dict):
                if hasattr(context_variables, "data"):
                    context_variables = dict(context_variables.data)
                elif hasattr(context_variables, "dict"):
                    context_variables = dict(context_variables.dict())
                else:
                    context_variables = {}
        except Exception:
            context_variables = {}

        # Proceed even if not explicitly confirmed; planner may have failed to call the tool
        # Normalize structured itinerary value if it's a pydantic model or JSON string
        try:
            if isinstance(structured_itinerary, BaseModel):
                structured_itinerary = structured_itinerary.model_dump()
            elif isinstance(structured_itinerary, str):
                structured_itinerary = json.loads(structured_itinerary)
        except Exception:
            pass

        context_variables["structured_itinerary"] = structured_itinerary
        
        return SwarmResult(
            context_variables=context_variables,
            values="Structured itinerary stored and ready.",
        )
    
    # Create Planner Agent using AssistantAgent (recommended for AG2 0.7.4+)
    planner_agent = AssistantAgent(
        name="planner_agent",
        system_message=f"""You are an expert trip planner with deep knowledge of destinations worldwide.

Create a detailed {num_days}-day itinerary for {destination} based on these preferences: {preferences}.

For each day, provide:
1. Morning attraction/activity
2. Lunch restaurant (local cuisine preferred)
3. Afternoon attraction/activity  
4. Dinner restaurant

Each event MUST have:
- type: 'Attraction' or 'Restaurant'
- location: Exact name of the place
- city: {destination}
- description: Brief description (1-2 sentences)

Focus on:
- Popular and well-rated places
- Logical geographic clustering (places close together)
- Mix of famous landmarks and local experiences
- Variety in cuisine types
- Appropriate pacing (not too rushed)

After creating the complete itinerary, mark it as complete.

IMPORTANT: When the itinerary is complete, you MUST call the tool `mark_itinerary_as_complete` with the entire final itinerary as plain text in the `final_itinerary` argument. Do not just print the itinerary; always call the tool to persist it.""",
        llm_config=llm_config,
    )
    
    # Register function for planner agent
    planner_agent.register_for_llm(
        name="mark_itinerary_as_complete",
        description="Call this when the itinerary is complete and ready to be formatted."
    )(mark_itinerary_as_complete)
    
    # Create Structured Output Agent with response format
    structured_config_list = copy.deepcopy(config_list)
    for config in structured_config_list:
        config["response_format"] = Itinerary
    
    structured_output_agent = AssistantAgent(
        name="structured_output_agent",
        system_message=(
            "You are a data formatting agent. Format the provided itinerary into the required structured JSON "
            "format with days and events. When you have produced the structured itinerary, you MUST call the "
            "tool `create_structured_itinerary` and pass the full JSON object via the `structured_itinerary` argument. "
            "Do not only print the JSON; always call the tool to persist it."
        ),
        llm_config={"config_list": structured_config_list, "timeout": 120},
    )
    
    # Register function for structured output agent
    structured_output_agent.register_for_llm(
        name="create_structured_itinerary",
        description="Call this to store the structured itinerary."
    )(create_structured_itinerary)
    
    # Register hand-offs using the new standalone function
    register_hand_off(
        agent=planner_agent,
        hand_to=[
            OnCondition(
                target=structured_output_agent,
                condition="Itinerary is complete and ready to format",
            ),
            # Ensure structured agent gets a turn even if tool call fails
            AfterWork(agent=structured_output_agent),
        ]
    )
    
    register_hand_off(
        agent=structured_output_agent,
        hand_to=[AfterWork(agent="TERMINATE")]
    )
    
    # Create user proxy (auto-approves)
    user_proxy = UserProxyAgent(
        name="user_proxy",
        code_execution_config=False,
        human_input_mode="NEVER",
    )
    
    # Register functions for execution
    user_proxy.register_for_execution(name="mark_itinerary_as_complete")(mark_itinerary_as_complete)
    user_proxy.register_for_execution(name="create_structured_itinerary")(create_structured_itinerary)
    
    # Start the conversation
    initial_message = f"Create a complete {num_days}-day trip itinerary for {destination}. Preferences: {preferences}. Include specific restaurant and attraction names with descriptions."
    
    chat_result, context_variables, last_agent = initiate_swarm_chat(
        initial_agent=planner_agent,
        agents=[planner_agent, structured_output_agent],
        user_agent=user_proxy,
        context_variables=trip_context,
        messages=initial_message,
        max_rounds=30,
    )
    
    # Extract the structured itinerary
    if context_variables.get("structured_itinerary"):
        itinerary = context_variables["structured_itinerary"]

        # Normalize structured itinerary into a dict
        try:
            if isinstance(itinerary, BaseModel):
                itinerary = itinerary.model_dump()
            elif isinstance(itinerary, str):
                itinerary = json.loads(itinerary)
        except Exception as e:
            print(f"Warning: Could not normalize structured itinerary: {e}")

        # Add travel times using Google Maps API if available
        if os.environ.get("GOOGLE_MAP_API_KEY") and isinstance(itinerary, dict):
            try:
                itinerary = add_travel_times_to_itinerary(itinerary)
            except Exception as e:
                print(f"Warning: Could not add travel times: {e}")

        return {
            "success": True,
            "itinerary": itinerary,
            "message": "Trip itinerary created successfully!"
        }
    else:
        # Fallback: try to recover JSON produced by structured agent or any text from chat
        recovered_structured: Dict[str, Any] | None = None
        fallback_text = context_variables.get("itinerary")

        def try_parse_json_from_text(text: str) -> Dict[str, Any] | None:
            if not isinstance(text, str):
                return None
            s = text.strip()
            # Heuristic: extract largest JSON object
            try:
                if s.startswith("{") and s.endswith("}"):
                    return json.loads(s)
                first = s.find("{")
                last = s.rfind("}")
                if first != -1 and last != -1 and last > first:
                    return json.loads(s[first:last + 1])
            except Exception:
                return None
            return None

        # 1) Inspect chat_result common shapes
        try:
            # dict-like
            if isinstance(chat_result, dict):
                # messages array
                msgs = chat_result.get("messages")
                if isinstance(msgs, list) and msgs:
                    last_msg = msgs[-1]
                    content = last_msg.get("content") if isinstance(last_msg, dict) else None
                    recovered_structured = try_parse_json_from_text(content)
                # top-level text fields
                if recovered_structured is None:
                    for key in ["values", "content", "message", "text", "response"]:
                        val = chat_result.get(key)
                        recovered_structured = try_parse_json_from_text(val)
                        if recovered_structured is not None:
                            break
            # object-like with .messages
            if recovered_structured is None and hasattr(chat_result, "messages"):
                msgs = getattr(chat_result, "messages", None)
                if isinstance(msgs, list) and msgs:
                    last_msg = msgs[-1]
                    if isinstance(last_msg, dict):
                        recovered_structured = try_parse_json_from_text(last_msg.get("content"))
            # string-like
            if recovered_structured is None and isinstance(chat_result, str):
                recovered_structured = try_parse_json_from_text(chat_result)
        except Exception as e:
            print(f"Warning: Could not recover itinerary from chat_result: {e}")

        # 2) Inspect last_agent chat buffer (autogen often stores messages on the agent)
        if recovered_structured is None:
            try:
                if last_agent is not None:
                    # Common internal buffers in autogen
                    for attr in [
                        "chat_messages",
                        "_oai_messages",
                        "_chat_messages",
                        "history",
                    ]:
                        buf = getattr(last_agent, attr, None)
                        if isinstance(buf, list) and buf:
                            last_msg = buf[-1]
                            if isinstance(last_msg, dict):
                                recovered_structured = try_parse_json_from_text(last_msg.get("content"))
                                if recovered_structured is not None:
                                    break
                        elif isinstance(buf, dict):
                            # Some buffers are dict[role] -> list[messages]
                            for v in buf.values():
                                if isinstance(v, list) and v:
                                    last_msg = v[-1]
                                    if isinstance(last_msg, dict):
                                        recovered_structured = try_parse_json_from_text(last_msg.get("content"))
                                        if recovered_structured is not None:
                                            break
                            if recovered_structured is not None:
                                break
            except Exception as e:
                print(f"Warning: Could not recover itinerary from last_agent: {e}")

        # If we recovered a structured JSON, return it
        if isinstance(recovered_structured, dict) and recovered_structured.get("days"):
            return {
                "success": True,
                "itinerary": recovered_structured,
                "message": "Trip itinerary created successfully!"
            }

        # Otherwise, fallback to any text we can find from chat_result
        if not fallback_text:
            try:
                if isinstance(chat_result, dict):
                    for key in ["values", "content", "message", "text", "response"]:
                        val = chat_result.get(key)
                        if isinstance(val, str) and val.strip():
                            fallback_text = val
                            break
                    if not fallback_text and isinstance(chat_result.get("messages"), list):
                        msgs = chat_result["messages"]
                        if msgs:
                            last = msgs[-1]
                            if isinstance(last, dict) and isinstance(last.get("content"), str):
                                fallback_text = last["content"]
                elif isinstance(chat_result, str):
                    fallback_text = chat_result
            except Exception as e:
                print(f"Warning: Could not derive text itinerary from chat_result: {e}")

        if not fallback_text:
            fallback_text = "Unable to create itinerary"

        return {
            "success": True,
            "itinerary": fallback_text,
            "message": "Trip itinerary created successfully!"
        }


def create_trip_planner_stream(destination: str, num_days: int, preferences: str):
    """Streaming version of trip planner"""
    try:
        result = create_trip_planner(destination, num_days, preferences)
        # Simulate streaming by yielding the result
        yield {"content": json.dumps(result, indent=2)}
    except Exception as e:
        yield {"content": json.dumps({"error": str(e)})}
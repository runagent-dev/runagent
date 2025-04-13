# runagent/templates/langgraph/default/agent.py
"""
Default LangGraph agent template.
"""

from typing import Dict, TypedDict, List, Annotated
import os
from langgraph.graph import StateGraph, END

class AgentState(TypedDict):
    """Represents the state of the agent."""
    input: str
    steps: List[str]
    output: str


def process_input(state: AgentState) -> AgentState:
    """First step: process the input."""
    user_input = state["input"]
    steps = state.get("steps", [])
    steps.append(f"Received input: {user_input}")
    
    return {"input": user_input, "steps": steps}


def generate_response(state: AgentState) -> AgentState:
    """Second step: generate a response."""
    user_input = state["input"]
    steps = state.get("steps", [])
    
    # In a real agent, you'd use an LLM or other logic here
    response = f"This is a simple response to: {user_input}"
    
    steps.append(f"Generated response: {response}")
    
    return {"input": user_input, "steps": steps, "output": response}


def should_end(state: AgentState) -> str:
    """Determine if the workflow should end."""
    if "output" in state and state["output"]:
        return END
    return "generate_response"


def create_agent_graph() -> StateGraph:
    """Create and return the agent workflow graph."""
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("process_input", process_input)
    workflow.add_node("generate_response", generate_response)
    
    # Add edges - using conditional edges
    workflow.add_conditional_edges(
        "process_input",
        should_end,
        {
            "generate_response": "generate_response",
            END: END
        }
    )
    
    # Set entry point
    workflow.set_entry_point("process_input")
    
    return workflow


# Create the compiled graph
agent_graph = create_agent_graph().compile()


def run(input_data: Dict) -> Dict:
    """
    Run the agent with the given input.
    
    Args:
        input_data: The input data for the agent
    
    Returns:
        Dictionary containing the agent output
    """
    # Extract input text from the input data
    input_text = input_data.get("query", "")
    if not input_text and "input" in input_data:
        input_text = input_data["input"]
    
    # Initialize the state
    state = {"input": input_text, "steps": []}
    
    # Run the agent
    result = agent_graph.invoke(state)
    return result
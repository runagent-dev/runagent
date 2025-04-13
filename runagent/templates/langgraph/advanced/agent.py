# runagent/templates/langgraph/advanced/agent.py
"""
Advanced LangGraph agent template with LLM integration.
"""

from typing import Dict, TypedDict, List, Annotated, Optional
import os
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage

# Get OpenAI API key from environment variable
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    print("Warning: OPENAI_API_KEY not found in environment variables.")

# Initialize the LLM
llm = ChatOpenAI(
    model="gpt-3.5-turbo",
    temperature=0.7,
    api_key=OPENAI_API_KEY
)

class AgentState(TypedDict):
    """Represents the state of the agent."""
    input: str
    messages: List[Dict]
    output: Optional[str]


def process_input(state: AgentState) -> AgentState:
    """First step: process the input."""
    user_input = state["input"]
    messages = state.get("messages", [])
    
    # Add user message to the conversation
    messages.append({"role": "human", "content": user_input})
    
    return {
        "input": user_input,
        "messages": messages
    }


def generate_response(state: AgentState) -> AgentState:
    """Second step: generate a response using LLM."""
    messages = state.get("messages", [])
    
    # Convert to LangChain message format
    lc_messages = []
    for msg in messages:
        if msg["role"] == "human":
            lc_messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "ai":
            lc_messages.append(AIMessage(content=msg["content"]))
    
    # Generate response using LLM
    ai_message = llm.invoke(lc_messages)
    response = ai_message.content
    
    # Add AI message to the conversation
    messages.append({"role": "ai", "content": response})
    
    return {
        "input": state["input"],
        "messages": messages,
        "output": response
    }


def create_agent_graph() -> StateGraph:
    """Create and return the agent workflow graph."""
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("process_input", process_input)
    workflow.add_node("generate_response", generate_response)
    
    # Add edges
    workflow.add_edge("process_input", "generate_response")
    workflow.add_edge("generate_response", END)
    
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
    
    # Extract conversation history if provided
    messages = input_data.get("messages", [])
    
    # Initialize the state
    state = {"input": input_text, "messages": messages}
    
    # Run the agent
    result = agent_graph.invoke(state)
    return result
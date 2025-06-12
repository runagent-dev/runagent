from langgraph.graph import StateGraph, END
from typing import TypedDict


# Simple state with just query and response
class State(TypedDict):
    query: str
    response: str


def receive_query(state: State) -> State:
    """Node 1: Receive and acknowledge the query"""
    query = state["query"]
    print(f"Received query: {query}")
    return state


def generate_response(state: State) -> State:
    """Node 2: Generate a simple response"""
    query = state["query"].lower()

    # Simple pattern matching for responses
    if "hello" in query or "hi" in query:
        response = "Hello! How can I help you?"
    elif "weather" in query:
        response = "I can't check the weather, but it's probably nice!"
    elif "time" in query:
        response = "I don't have access to the current time."
    elif "help" in query:
        response = "I'm a simple agent. I can respond to basic queries!"
    else:
        response = f"You asked: '{state['query']}'. Thanks for your question!"

    state["response"] = response
    print(f"Generated response: {response}")
    return state


# Create the agent
def create_agent():
    workflow = StateGraph(State)

    # Add two nodes
    workflow.add_node("receive", receive_query)
    workflow.add_node("respond", generate_response)

    # Simple flow: receive -> respond -> end
    workflow.set_entry_point("receive")
    workflow.add_edge("receive", "respond")
    workflow.add_edge("respond", END)

    return workflow.compile()


# Run the agent
def ask_agent(query: str):
    agent = create_agent()
    result = agent.invoke({"query": query, "response": ""})
    return result["response"]


# Test it
if __name__ == "__main__":
    queries = ["Hello!", "What's the weather?", "Help me", "How are you?"]
    
    for q in queries:
        print(f"\nQ: {q}")
        print(f"A: {ask_agent(q)}")
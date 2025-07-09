"""
Fixed LangGraph Problem Solver - Proper Input Format Handling
=============================================================

The agent now properly handles input kwargs and converts them to the
state format that LangGraph expects.
"""

from typing import List, TypedDict, Optional, Dict, Any
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph


# Enhanced state with complex types
class ProblemState(TypedDict):
    query: str
    num_solutions: int
    solutions: List[str]
    validated_results: str
    metadata: Optional[Dict[str, Any]]
    constraints: Optional[List[Dict[str, Any]]]
    user_context: Optional[Dict[str, Any]]


llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)


def problem_solver_agent(state: ProblemState) -> ProblemState:
    """Agent 1: Problem solver with complex input handling"""
    print(f"🔍 Solver: '{state['query']}'")
    
    # Handle optional complex inputs
    context_info = ""
    if state.get("user_context"):
        level = state["user_context"].get("experience_level", "unknown")
        context_info = f" (User level: {level})"
    
    constraint_info = ""
    if state.get("constraints"):
        constraint_info = f" with {len(state['constraints'])} constraints"

    prompt = f"""Problem: {state['query']}{context_info}{constraint_info}

Provide {state['num_solutions']} practical solutions.
Format as numbered list."""

    response = llm.invoke([HumanMessage(content=prompt)])
    
    # Extract solutions
    solutions = []
    for line in response.content.split("\n"):
        if line.strip() and (line.strip()[0].isdigit() or line.strip().startswith("-")):
            solution = line.strip()
            if ". " in solution:
                solution = solution.split(". ", 1)[1]
            solutions.append(solution)

    return {**state, "solutions": solutions}


def solution_validator_agent(state: ProblemState) -> ProblemState:
    """Agent 2: Validator with metadata support"""
    print(f"✅ Validator: {len(state['solutions'])} solutions")

    solutions_text = "\n".join([f"{i+1}. {sol}" for i, sol in enumerate(state["solutions"])])
    
    prompt = f"""Problem: {state['query']}

Solutions:
{solutions_text}

Rank and explain each solution briefly."""

    response = llm.invoke([HumanMessage(content=prompt)])
    return {**state, "validated_results": response.content}


def create_workflow():
    """Create the workflow"""
    workflow = StateGraph(ProblemState)
    workflow.add_node("solve", problem_solver_agent)
    workflow.add_node("validate", solution_validator_agent)
    workflow.set_entry_point("solve")
    workflow.add_edge("solve", "validate")
    workflow.add_edge("validate", END)
    return workflow.compile()


# Create workflow
app = create_workflow()


def run(*input_args, **input_kwargs):
    """
    Main entrypoint that converts kwargs to LangGraph state format
    This is what gets called by the generic entrypoint
    """
    print(f"🚀 LangGraph run called with:")
    print(f"  Args: {input_args}")
    print(f"  Kwargs: {list(input_kwargs.keys())}")
    
    # Convert input_kwargs to ProblemState format
    initial_state = {
        "query": input_kwargs.get("query", "Default problem"),
        "num_solutions": input_kwargs.get("num_solutions", 3),
        "solutions": [],
        "validated_results": "",
        "metadata": input_kwargs.get("metadata"),
        "constraints": input_kwargs.get("constraints"),
        "user_context": input_kwargs.get("user_context")
    }
    
    print(f"🔄 Converted to state: {list(initial_state.keys())}")
    
    # Run the workflow
    result = app.invoke(initial_state)
    
    print(f"✅ LangGraph completed with {len(result.get('solutions', []))} solutions")
    
    return result


def run_stream(*input_args, **input_kwargs):
    """
    Streaming entrypoint that converts kwargs to LangGraph state format
    """
    print(f"🌊 LangGraph stream called with:")
    print(f"  Args: {input_args}")
    print(f"  Kwargs: {list(input_kwargs.keys())}")
    
    # Convert input_kwargs to ProblemState format
    initial_state = {
        "query": input_kwargs.get("query", "Default problem"),
        "num_solutions": input_kwargs.get("num_solutions", 3),
        "solutions": [],
        "validated_results": "",
        "metadata": input_kwargs.get("metadata"),
        "constraints": input_kwargs.get("constraints"),
        "user_context": input_kwargs.get("user_context")
    }
    
    print(f"🔄 Streaming with state: {list(initial_state.keys())}")
    
    # Stream the workflow
    for chunk in app.stream(initial_state):
        print(f"📦 Yielding chunk: {list(chunk.keys())}")
        yield chunk

# app = create_workflow()

# # For direct testing
# if __name__ == "__main__":
#     # Test the run function directly
#     test_result = run(
#         query="My phone battery drains quickly",
#         num_solutions=2,
#         constraints=[{"type": "budget", "value": 0, "priority": "high"}],
#         user_context={"experience_level": "beginner", "tools": ["basic"]},
#         metadata={"test": True, "nested": {"data": 123}}
#     )
#     print("Test result:", test_result)
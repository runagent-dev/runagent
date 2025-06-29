"""
Simple LangGraph Problem Solver & Validator
===========================================

Two-agent workflow with simple functions and easy-to-understand prompts.
Perfect for LangGraph demos and tutorials.
"""

from typing import List, TypedDict

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph


# Simple state definition
class ProblemState(TypedDict):
    query: str
    num_solutions: int
    solutions: List[str]
    validated_results: str


# Initialize LLM (make sure to set your OpenAI API key)
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.3)


def problem_solver_agent(state: ProblemState) -> ProblemState:
    """
    Agent 1: Simple problem solver that generates solutions
    """
    print(f"🔍 Problem Solver: Working on '{state['query']}'...")

    # Simple, clear prompt
    prompt = f"""Problem: {state['query']}

Please provide {state['num_solutions']} simple solutions. 
Format: Return only a numbered list, one solution per line.

Example:
1. Restart your device
2. Clear browser cache
3. Update your software"""

    response = llm.invoke([HumanMessage(content=prompt)])

    # Extract solutions from response
    solutions = []
    for line in response.content.split("\n"):
        if line.strip() and (line.strip()[0].isdigit() or line.strip().startswith("-")):
            # Clean up the solution text
            solution = line.strip()
            if ". " in solution:
                solution = solution.split(". ", 1)[1]  # Remove number prefix
            elif "- " in solution:
                solution = solution.split("- ", 1)[1]  # Remove dash prefix
            solutions.append(solution)

    return {**state, "solutions": solutions}


def solution_validator_agent(state: ProblemState) -> ProblemState:
    """
    Agent 2: Simple validator that ranks and explains solutions
    """
    print(f"✅ Validator: Checking {len(state['solutions'])} solutions...")

    solutions_text = "\n".join(
        [f"{i+1}. {sol}" for i, sol in enumerate(state["solutions"])]
    )

    # Simple validation prompt
    prompt = f"""Problem: {state['query']}

Solutions to validate:
{solutions_text}

Please rank these solutions from best to worst and explain why.
Keep it simple and practical."""

    response = llm.invoke([HumanMessage(content=prompt)])

    return {**state, "validated_results": response.content}


def create_workflow():
    """
    Creates the simple two-agent workflow
    """
    # Create the graph
    workflow = StateGraph(ProblemState)

    # Add our two agents
    workflow.add_node("solve", problem_solver_agent)
    workflow.add_node("validate", solution_validator_agent)

    # Set up the flow: solve -> validate -> end
    workflow.set_entry_point("solve")
    workflow.add_edge("solve", "validate")
    workflow.add_edge("validate", END)

    return workflow.compile()


def solve_problem(query: str, num_solutions: int = 3):
    """
    Main function to solve problems

    Args:
        query: Your problem description
        num_solutions: How many solutions you want (1-5)

    Returns:
        Complete analysis with validated solutions
    """
    print(f"\n🚀 Starting Problem Solving Workflow")
    print(f"Problem: {query}")
    print(f"Requested solutions: {num_solutions}")
    print("-" * 50)

    # Create workflow
    app = create_workflow()

    # Set up initial state
    initial_state = {
        "query": query,
        "num_solutions": min(max(num_solutions, 1), 5),  # Keep between 1-5
        "solutions": [],
        "validated_results": "",
    }

    # Run the workflow
    result = app.invoke(initial_state)

    # Print results nicely
    print("\n📋 SOLUTIONS FOUND:")
    for i, solution in enumerate(result["solutions"], 1):
        print(f"{i}. {solution}")

    print(f"\n🎯 VALIDATION RESULTS:")
    print(result["validated_results"])

    return result


def get_solutions(query: str, num_solutions: int = 3):
    """
    Main function to solve problems

    Args:
        query: Your problem description
        num_solutions: How many solutions you want (1-5)

    Returns:
        Complete analysis with validated solutions
    """
    print(f"\n🚀 Starting Problem Solving Workflow")
    print(f"Problem: {query}")
    print(f"Requested solutions: {num_solutions}")
    print("-" * 50)

    # Create workflow
    app = create_workflow()

    # Set up initial state
    initial_state = {
        "query": query,
        "num_solutions": min(max(num_solutions, 1), 5),  # Keep between 1-5
        "solutions": [],
        "validated_results": "",
    }

    # Run the workflow
    result = app.invoke(initial_state)

    # Print results nicely
    print("\n📋 SOLUTIONS FOUND:")
    for i, solution in enumerate(result["solutions"], 1):
        print(f"{i}. {solution}")

    print(f"\n🎯 VALIDATION RESULTS:")
    print(result["validated_results"])

    return result


# Create workflow
app = create_workflow()


if __name__ == "__main__":
    for out in app.stream(
        {
            "query": "How to I fix my broken phone?",
            "num_solutions": 4,
        }
    ):
        print(out)
        print("-" * 50)
# Set up initial state
# initial_state = {
#     "query": query,
#     "num_solutions": min(max(num_solutions, 1), 5),  # Keep between 1-5
#     "solutions": [],
#     "validated_results": "",
# }
# def stream_solutions(query: str, num_solutions: int = 3):
#     """
#     Main function to solve problems

#     Args:
#         query: Your problem description
#         num_solutions: How many solutions you want (1-5)

#     Returns:
#         Complete analysis with validated solutions
#     """
#     print(f"\n🚀 Starting Problem Solving Workflow")
#     print(f"Problem: {query}")
#     print(f"Requested solutions: {num_solutions}")
#     print("-" * 50)

#     # Create workflow
#     app = create_workflow()

#     # Set up initial state
#     initial_state = {
#         "query": query,
#         "num_solutions": min(max(num_solutions, 1), 5),  # Keep between 1-5
#         "solutions": [],
#         "validated_results": "",
#     }

#     # Run the workflow
#     result = app.invoke(initial_state)

#     # Print results nicely
#     print("\n📋 SOLUTIONS FOUND:")
#     for i, solution in enumerate(result["solutions"], 1):
#         print(f"{i}. {solution}")

#     print(f"\n🎯 VALIDATION RESULTS:")
#     print(result["validated_results"])

#     return result

import time
from typing import Any, Dict

from agent import LangGraphAdvancedAgent


def run(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entry point for the LangGraph Advanced agent

    Args:
        input_data: Dictionary containing:
            - messages: List of message objects with 'role' and 'content'
            - config: Optional configuration parameters
            - context: Optional context data

    Returns:
        Dictionary with result, errors, and success status
    """
    start_time = time.time()

    try:
        # Extract data
        config = input_data.get("config", {})
        messages = input_data.get("messages", [])
        context = input_data.get("context", {})

        if not messages:
            return {
                "result": {
                    "type": "string",
                    "content": "No messages provided",
                    "metadata": {"execution_time": time.time() - start_time},
                },
                "errors": ["No messages provided"],
                "success": False,
            }

        # Initialize agent
        agent = LangGraphAdvancedAgent(config)

        # Process messages
        response = agent.process_messages(messages, context)

        # Calculate execution time
        execution_time = time.time() - start_time

        return {
            "result": {
                "type": "string",
                "content": response["final_answer"],
                "metadata": {
                    "model_used": config.get("model", "gpt-4"),
                    "framework": "langgraph",
                    "template": "advanced",
                    "execution_time": execution_time,
                    "graph_structure": agent.get_graph_structure(),
                    "tools_available": agent.get_available_tools(),
                    "tools_used": response.get("tools_used", []),
                    "steps_taken": response.get("steps_taken", 0),
                    "conversation_length": len(messages),
                },
            },
            "errors": [],
            "success": True,
        }

    except Exception as e:
        execution_time = time.time() - start_time
        return {
            "result": None,
            "errors": [str(e)],
            "success": False,
            "metadata": {"execution_time": execution_time},
        }

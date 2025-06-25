import time
from typing import Any, Dict

from agent import LangGraphBasicAgent


def run(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entry point for the LangGraph Basic agent

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
        agent = LangGraphBasicAgent(config)

        # Process messages
        response = agent.process_messages(messages, context)

        # Calculate execution time
        execution_time = time.time() - start_time

        return {
            "result": {
                "type": "string",
                "content": response["response"],
                "metadata": {
                    "model_used": config.get("model", "gpt-4"),
                    "framework": "langgraph",
                    "template": "basic",
                    "execution_time": execution_time,
                    "graph_structure": agent.get_graph_structure(),
                    "steps_taken": response.get("steps_taken", 1),
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

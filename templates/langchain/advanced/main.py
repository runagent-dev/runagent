import time
from typing import Any, Dict

from agent import LangChainAdvancedAgent


def run(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entry point for the LangChain Advanced agent

    Args:
        input_data: Dictionary containing:
            - messages: List of message objects with 'role' and 'content'
            - config: Optional configuration parameters

    Returns:
        Dictionary with result, errors, and success status
    """
    start_time = time.time()

    try:
        # Extract configuration
        config = input_data.get("config", {})
        messages = input_data.get("messages", [])

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
        agent = LangChainAdvancedAgent(config)

        # Process messages
        response = agent.process_messages(messages)

        # Calculate execution time
        execution_time = time.time() - start_time

        return {
            "result": {
                "type": "string",
                "content": response["output"],
                "metadata": {
                    "model_used": config.get("model", "gpt-4"),
                    "framework": "langchain",
                    "template": "advanced",
                    "execution_time": execution_time,
                    "tools_available": agent.get_available_tools(),
                    "tools_used": response.get("tools_used", []),
                    "conversation_length": len(messages),
                    "intermediate_steps": len(response.get("intermediate_steps", [])),
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

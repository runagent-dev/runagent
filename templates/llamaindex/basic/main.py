import time
from typing import Any, Dict

from agent import LlamaIndexBasicAgent


def run(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entry point for the LlamaIndex Basic agent

    Args:
        input_data: Dictionary containing:
            - messages: List of message objects with 'role' and 'content'
            - config: Optional configuration parameters
            - documents: Optional list of additional documents to index

    Returns:
        Dictionary with result, errors, and success status
    """
    start_time = time.time()

    try:
        # Extract data
        config = input_data.get("config", {})
        messages = input_data.get("messages", [])
        additional_docs = input_data.get("documents", [])

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
        agent = LlamaIndexBasicAgent(config)

        # Add additional documents if provided
        if additional_docs:
            agent.add_documents(additional_docs)

        # Process messages
        response = agent.process_messages(messages)

        # Calculate execution time
        execution_time = time.time() - start_time

        return {
            "result": {
                "type": "string",
                "content": response["answer"],
                "metadata": {
                    "model_used": config.get("model", "gpt-4"),
                    "framework": "llamaindex",
                    "template": "basic",
                    "execution_time": execution_time,
                    "index_stats": agent.get_index_stats(),
                    "sources_used": len(response.get("source_nodes", [])),
                    "source_nodes": response.get("source_nodes", []),
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

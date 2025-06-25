"""
RunAgent - Deploy and manage AI agents easily.

This package provides both a CLI and SDK for deploying and managing AI agents
built with frameworks like LangGraph, LangChain, and LlamaIndex.
"""

__version__ = "0.1.0"

# Import the main SDK components
from .sdk import RunAgentSDK, RunAgentError, AuthenticationError, ValidationError, ConnectionError, ServerError

# Main export - this is what was missing!
RunAgent = RunAgentSDK

# Expose the main components for easy import
__all__ = [
    "RunAgent",
    "RunAgentSDK",
    "RunAgentError",
    "AuthenticationError",
    "ValidationError",
    "ConnectionError",
    "ServerError"
]

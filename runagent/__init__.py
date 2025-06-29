"""
RunAgent - Deploy and manage AI agents easily.

This package provides both a CLI and SDK for deploying and managing AI agents
built with frameworks like LangGraph, LangChain, and LlamaIndex.
"""

__version__ = "0.1.0"

from .client import RunAgentClient, AsyncRunAgentClient

# Import the main SDK components
from .sdk import (
    AuthenticationError,
    ConnectionError,
    RunAgentError,
    RunAgentSDK,
    ServerError,
    ValidationError,
)

# Main export
RunAgent = RunAgentSDK

# Expose the main components for easy import
__all__ = [
    "RunAgent",
    "RunAgentSDK",
    "RunAgentClient",
    "AsyncRunAgentClient",
    "RunAgentError",
    "AuthenticationError",
    "ValidationError",
    "ConnectionError",
    "ServerError",
]

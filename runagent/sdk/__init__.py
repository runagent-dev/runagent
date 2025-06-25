"""
RunAgent SDK - Standalone Python SDK for deploying and managing AI agents.

This module provides a comprehensive SDK that can work independently of the CLI.
"""

from .sdk import RunAgentSDK
from .exceptions import (
    RunAgentError,
    AuthenticationError,
    ValidationError,
    ConnectionError,
    ServerError
)

# Main SDK class for easy import
RunAgent = RunAgentSDK

# Version info
__version__ = "0.1.0"

# Expose main components
__all__ = [
    "RunAgentSDK",
    "RunAgent",
    "RunAgentError", 
    "AuthenticationError",
    "ValidationError",
    "ConnectionError",
    "ServerError"
]
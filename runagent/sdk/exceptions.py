"""
RunAgent SDK Custom exceptions.
"""

import typing as t


class RunAgentError(Exception):
    """Base exception for all RunAgent SDK errors."""

    def __init__(self, message: str, details: t.Optional[t.Dict[str, t.Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(RunAgentError):
    """Exception for authentication and authorization errors."""

    pass


class ValidationError(RunAgentError):
    """Exception for input validation errors."""

    pass


class ConnectionError(RunAgentError):
    """Exception for network and connection errors."""

    pass


class ServerError(RunAgentError):
    """Exception for server-side errors."""

    pass


class TemplateError(RunAgentError):
    """Exception for template-related errors."""

    pass


class DeploymentError(RunAgentError):
    """Exception for deployment-related errors."""

    pass

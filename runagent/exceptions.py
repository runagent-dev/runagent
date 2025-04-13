# runagent/exceptions.py
"""
Custom exceptions for the RunAgent package.
"""

class RunAgentError(Exception):
    """Base exception for all RunAgent errors."""
    pass

class AuthenticationError(RunAgentError):
    """Raised when authentication fails."""
    pass

class DeploymentError(RunAgentError):
    """Raised when deployment fails."""
    pass

class InvalidConfigError(RunAgentError):
    """Raised when configuration is invalid."""
    pass

class ApiError(RunAgentError):
    """Raised when API requests fail."""
    def __init__(self, message, status_code=None, response=None):
        self.status_code = status_code
        self.response = response
        super().__init__(message)
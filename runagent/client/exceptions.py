"""
RunAgent SDK Custom exceptions.
"""

class ClientError(Exception):
    """Base exception for client errors."""
    def __init__(self, message: str, status_code: t.Optional[int] = None, response: t.Optional[t.Any] = None):
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(self.message)


class ServerError(Exception):
    """Exception for server errors."""
    pass


class ConnectionError(Exception):
    """Exception for connection errors."""
    pass


class AuthenticationError(ClientError):
    """Exception for authentication errors."""
    pass


class ValidationError(ClientError):
    """Exception for validation errors."""
    pass


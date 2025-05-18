"""
Http client implementation for Composio SDK
"""

import typing as t

# from requests import ReadTimeout
# from requests import Session as SyncSession

# from runagent.__version__ import __version__
# from runagent.exceptions import SDKTimeoutError
# from composio.utils import logging
# from composio.utils.shared import generate_request_id
import os
import requests
from urllib.parse import urljoin
from runagent.utils.config import Config


DEFAULT_RUNTIME = "composio"
SOURCE_HEADER = "python_sdk"
DEFAULT_REQUEST_TIMEOUT = 60.0


# Custom exception classes
class RunAgentClientError(Exception):
    """Exception raised for API errors."""
    
    def __init__(
        self,
        message: str,
        status_code: t.Optional[int] = None,
        response: t.Optional[t.Any] = None
    ):
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(self.message)


class HttpHandler:
    def __init__(self, api_key: t.Optional[str] = None, base_url: t.Optional[str] = None):
        
        self.api_key = api_key
        self.base_url = base_url
        self.base_url = self.base_url.rstrip("/")
        self.default_headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }

    def _get_url(self, path: str) -> str:
        return f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"

    def _request(
        self, 
        method: str,
        path: str,
        data: t.Optional[t.Dict[str, t.Any]] = None, 
        params: t.Optional[t.Dict[str, t.Any]] = None,
        headers: t.Optional[t.Dict[str, str]] = None,
        files: t.Optional[t.Dict[str, t.Any]] = None,
        timeout: int = 30
    ) -> t.Dict[str, t.Any]:
        """
        Generic request method to handle all HTTP requests.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            path: API endpoint path
            data: Request payload for POST/PUT requests
            params: Query parameters
            headers: Additional headers (will be merged with default headers)
            files: Files to upload
            timeout: Request timeout in seconds
            
        Returns:
            Response data as a dictionary
            
        Raises:
            ApiError: If the API returns an error
            ConnectionError: If there's a network issue
        """
        # Merge default headers with any additional headers
        request_headers = self.default_headers.copy()
        if headers:
            request_headers.update(headers)
            
        # Construct the full URL
        url = self._get_url(path)
        
        try:
            # For GET and DELETE requests, data should be sent as params
            if method.lower() in ['get', 'delete'] and data and not params:
                params = data
                data = None
                
            # Convert data to JSON string if it's a dictionary
            json_data = None
            if data and not files:
                json_data = data
                data = None
                
            # Make the request
            response = requests.request(
                method=method.upper(),
                url=url,
                params=params,
                data=data,
                json=json_data,
                headers=request_headers,
                files=files,
                timeout=timeout
            )
            
            # Raise an exception for 4XX and 5XX responses
            response.raise_for_status()
            
            # Return JSON response if present, otherwise return success message
            if response.content and response.headers.get('Content-Type', '').startswith('application/json'):
                return response.json()
            else:
                return {"status": "success", "status_code": response.status_code}
                
        except requests.exceptions.HTTPError as e:
            # Handle API errors with proper error message extraction
            error_message = f"HTTP Error: {e}"
            try:
                error_data = e.response.json()
                if "detail" in error_data:
                    error_message = error_data["detail"]
                elif "message" in error_data:
                    error_message = error_data["message"]
            except ValueError:
                pass  # Use the default error message if response isn't JSON
                
            raise RunAgentClientError(
                message=error_message,
                status_code=e.response.status_code if hasattr(e, 'response') else None,
                response=e.response if hasattr(e, 'response') else None
            )
            
        except requests.exceptions.ConnectionError:
            raise ConnectionError(f"Failed to connect to {self.base_url}")
            
        except requests.exceptions.Timeout:
            raise TimeoutError(f"Request to {url} timed out after {timeout} seconds")
            
        except Exception as e:
            raise RunAgentClientError(f"Unexpected error: {str(e)}")
            
    # Convenience methods for common HTTP methods
    def _get(self, path: str, params: t.Optional[t.Dict[str, t.Any]] = None, **kwargs) -> t.Dict[str, t.Any]:
        """Send a GET request to the API."""
        return self._request("GET", path, params=params, **kwargs)
        
    def _post(self, path: str, data: t.Optional[t.Dict[str, t.Any]] = None, **kwargs) -> t.Dict[str, t.Any]:
        """Send a POST request to the API."""
        return self._request("POST", path, data=data, **kwargs)
        
    def _put(self, path: str, data: t.Optional[t.Dict[str, t.Any]] = None, **kwargs) -> t.Dict[str, t.Any]:
        """Send a PUT request to the API."""
        return self._request("PUT", path, data=data, **kwargs)
        
    def _delete(self, path: str, **kwargs) -> t.Dict[str, t.Any]:
        """Send a DELETE request to the API."""
        return self._request("DELETE", path, **kwargs)
        
    def _patch(self, path: str, data: t.Optional[t.Dict[str, t.Any]] = None, **kwargs) -> t.Dict[str, t.Any]:
        """Send a PATCH request to the API."""
        return self._request("PATCH", path, data=data, **kwargs)

    
    # def get_protected_resource(self) -> t.Dict[str, t.Any]:
    #     """Get a protected resource."""
    #     return self.get("api/protected-resource")
    
    # def create_something(self, data: t.Dict[str, t.Any]) -> t.Dict[str, t.Any]:
    #     """Create a new resource."""
    #     return self.post("api/create-something", data=data)


def EndpointHandler(HttpHandler):
    def __init__(
        self,
        api_key: t.Optional[str] = None,
        base_url: t.Optional[str] = None,
        api_prefix: t.Optional[str] = "/api/v1",

    ):

        self.api_key = api_key or Config.get_api_key()
        self.base_url = base_url or Config.get_base_url()
        super().__init__(self.api_key, self.base_url)
        if api_prefix:
            self.base_url = self._get_url(api_prefix)

    # API-specific methods using the generic request methods
    def validate_api_key(self) -> t.Dict[str, t.Any]:
        """Validate the API key and get user data."""
        return self.get("/auth/validate")



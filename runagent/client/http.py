import typing as t
import requests
import json
import sys
from enum import Enum
from rich.console import Console
from rich import print as rprint
from runagent.utils.config import Config
from runagent.utils.enums import ResponseStatus


# Console for pretty printing
console = Console()


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


class HttpHandler:
    def __init__(self, api_key: t.Optional[str] = None, base_url: t.Optional[str] = None):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/") if base_url else ""
        self.default_headers = {
            "x-api-key": api_key,
            "accept": "application/json",
            "content-type": "application/json"
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
        timeout: int = 30,
        handle_errors: bool = True,
        raw_response: bool = False
    ) -> t.Union[t.Dict[str, t.Any], requests.Response]:
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
            handle_errors: Whether to handle errors or raise exceptions
            raw_response: Whether to return the raw response object
            
        Returns:
            Response data as a dictionary or raw response
        """
        # Merge default headers with any additional headers
        request_headers = self.default_headers.copy()
        if headers:
            request_headers.update(headers)
            
        # Special case for file uploads
        if files:
            # Don't set content-type for multipart/form-data
            if 'content-type' in request_headers:
                del request_headers['content-type']
        
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
            
            # Return raw response if requested
            if raw_response:
                return response
                
            # Process response based on status code
            if response.status_code < 400:  # Success
                if not response.content:
                    return {"status": ResponseStatus.SUCCESS.value, "message": "Operation completed successfully"}
                    
                if response.headers.get('Content-Type', '').startswith('application/json'):
                    return response.json()
                else:
                    return {
                        "status": ResponseStatus.SUCCESS.value, 
                        "status_code": response.status_code,
                        "content": response.text
                    }
            else:  # Error
                if not handle_errors:
                    response.raise_for_status()
                    
                # Handle different error types
                self._handle_error_response(response)
                
        except requests.exceptions.ConnectionError as e:
            if not handle_errors:
                raise
            raise ConnectionError(f"Failed to connect to {self.base_url}. Please check your internet connection and try again.")
            
        except requests.exceptions.Timeout as e:
            if not handle_errors:
                raise
            raise ConnectionError(f"Request to {url} timed out after {timeout} seconds. Please try again later.")
            
        except (ClientError, ServerError, ConnectionError, AuthenticationError, ValidationError):
            # Re-raise our custom exceptions
            raise
            
        except Exception as e:
            if not handle_errors:
                raise
            raise ClientError(f"Unexpected error: {str(e)}")
            
    def _handle_error_response(self, response: requests.Response) -> None:
        """Extract error details from response and raise appropriate exception."""
        status_code = response.status_code
        error_message = f"HTTP Error: {status_code}"
        
        try:
            error_data = response.json()
            if isinstance(error_data, dict):
                if "detail" in error_data:
                    error_message = error_data["detail"]
                elif "message" in error_data:
                    error_message = error_data["message"]
                elif "error" in error_data:
                    error_message = error_data["error"]
        except ValueError:
            # Not JSON or empty response
            if response.text:
                error_message = response.text
        
        # Handle different error types based on status code
        if status_code == 401:
            raise AuthenticationError(error_message, status_code, response)
        elif status_code == 403:
            raise AuthenticationError(f"Access denied: {error_message}", status_code, response)
        elif status_code == 400 or status_code == 422:
            raise ValidationError(error_message, status_code, response)
        elif 400 <= status_code < 500:
            raise ClientError(error_message, status_code, response)
        else:  # 500+ errors
            raise ServerError(f"Server error: {error_message}", status_code, response)
    
    # Convenience methods for common HTTP methods
    def _get(self, path: str, **kwargs) -> t.Dict[str, t.Any]:
        """Send a GET request to the API."""
        return self._request("GET", path, **kwargs)
        
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


class EndpointHandler(HttpHandler):
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
        try:
            return self._get("/auth/validate")
        except AuthenticationError:
            console.print("[red]Invalid API key. Please check your credentials.[/red]")
            return {"status": ResponseStatus.ERROR.value, "message": "Invalid API key"}
        except ConnectionError as e:
            console.print(f"[yellow]{str(e)}[/yellow]")
            return {"status": ResponseStatus.ERROR.value, "message": str(e)}
        except Exception as e:
            console.print(f"[red]Error validating API key: {str(e)}[/red]")
            return {"status": ResponseStatus.ERROR.value, "message": str(e)}
    
    def create_resource(self, data: t.Dict[str, t.Any]) -> t.Dict[str, t.Any]:
        """Create a new resource."""
        try:
            return self._post("/resources", data=data)
        except ValidationError as e:
            console.print(f"[yellow]Validation error: {e.message}[/yellow]")
            return {"status": ResponseStatus.ERROR.value, "message": e.message, "errors": self._extract_validation_errors(e.response)}
        except ConnectionError as e:
            console.print(f"[yellow]{str(e)}[/yellow]")
            return {"status": ResponseStatus.ERROR.value, "message": str(e)}
        except Exception as e:
            console.print(f"[red]Error creating resource: {str(e)}[/red]")
            return {"status": ResponseStatus.ERROR.value, "message": str(e)}
    
    def get_resource(self, resource_id: str) -> t.Dict[str, t.Any]:
        """Get a resource by ID."""
        try:
            return self._get(f"/resources/{resource_id}")
        except ClientError as e:
            if e.status_code == 404:
                console.print(f"[yellow]Resource with ID {resource_id} not found.[/yellow]")
                return {"status": ResponseStatus.ERROR.value, "message": f"Resource with ID {resource_id} not found"}
            else:
                console.print(f"[red]Error: {e.message}[/red]")
                return {"status": ResponseStatus.ERROR.value, "message": e.message}
        except ConnectionError as e:
            console.print(f"[yellow]{str(e)}[/yellow]")
            return {"status": ResponseStatus.ERROR.value, "message": str(e)}
        except Exception as e:
            console.print(f"[red]Error retrieving resource: {str(e)}[/red]")
            return {"status": ResponseStatus.ERROR.value, "message": str(e)}
    
    def delete_resource(self, resource_id: str) -> t.Dict[str, t.Any]:
        """Delete a resource by ID."""
        try:
            return self._delete(f"/resources/{resource_id}")
        except ClientError as e:
            if e.status_code == 404:
                console.print(f"[yellow]Resource with ID {resource_id} not found.[/yellow]")
                return {"status": ResponseStatus.ERROR.value, "message": f"Resource with ID {resource_id} not found"}
            else:
                console.print(f"[red]Error: {e.message}[/red]")
                return {"status": ResponseStatus.ERROR.value, "message": e.message}
        except ConnectionError as e:
            console.print(f"[yellow]{str(e)}[/yellow]")
            return {"status": ResponseStatus.ERROR.value, "message": str(e)}
        except Exception as e:
            console.print(f"[red]Error deleting resource: {str(e)}[/red]")
            return {"status": ResponseStatus.ERROR.value, "message": str(e)}
    
    def _extract_validation_errors(self, response: t.Optional[requests.Response]) -> t.List[t.Dict[str, t.Any]]:
        """Extract validation errors from response."""
        if not response:
            return []
            
        try:
            data = response.json()
            if isinstance(data, dict):
                if "errors" in data:
                    return data["errors"]
                elif "detail" in data and isinstance(data["detail"], list):
                    return data["detail"]
            return []
        except Exception:
            return []
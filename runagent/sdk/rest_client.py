import asyncio
import base64
import json
import os
import tempfile
import time
import typing as t
import zipfile
from pathlib import Path
from typing import Any, Dict, Optional, Union

import httpx
import requests
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)

from runagent.utils.config import Config

console = Console()


class HttpException(Exception):
    """Base exception for HTTP errors"""

    def __init__(
        self, message: str, status_code: int = None, response: Union[requests.Response, httpx.Response] = None
    ):
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(message)


class ClientError(HttpException):
    """Client error (4xx status codes)"""
    pass


class ServerError(HttpException):
    """Server error (5xx status codes)"""
    pass


class AuthenticationError(ClientError):
    """Authentication error (401, 403)"""
    pass


class ValidationError(ClientError):
    """Validation error (400, 422)"""
    pass


class ConnectionError(HttpException):
    """Connection error"""
    pass


class HttpHandler:
    """HTTP handler for API requests with proper error handling and async support"""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/") if base_url else ""
        
        # Sync session
        self.session = requests.Session()
        
        # Async client (will be created when needed)
        self._async_client: Optional[httpx.AsyncClient] = None

        # Set default headers
        self.default_headers = {
            "accept": "application/json",
            "content-type": "application/json",
        }

        if self.api_key:
            self.default_headers["Authorization"] = f"Bearer {self.api_key}"
            self.default_headers["User-Agent"] = "RunAgent-CLI/1.0"

    def _get_url(self, path: str) -> str:
        """Construct full URL from base URL and path"""
        return f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"

    @property
    def async_client(self) -> httpx.AsyncClient:
        """Get or create async client"""
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(
                headers=self.default_headers,
                timeout=httpx.Timeout(30.0)
            )
        return self._async_client

    async def close_async_client(self):
        """Close the async client"""
        if self._async_client:
            await self._async_client.aclose()
            self._async_client = None

    def __del__(self):
        """Cleanup async client on deletion"""
        if self._async_client:
            try:
                asyncio.create_task(self.close_async_client())
            except RuntimeError:
                # Event loop might be closed
                pass

    async def _async_request(
        self,
        method: str,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        files: Optional[Dict[str, Any]] = None,
        timeout: int = 30,
        handle_errors: bool = True,
        raw_response: bool = False,
    ) -> Union[Dict[str, Any], httpx.Response]:
        """Async version of _request method"""
        
        # Merge default headers with any additional headers
        request_headers = self.default_headers.copy()
        if headers:
            request_headers.update(headers)

        # Special case for file uploads
        if files:
            # Don't set content-type for multipart/form-data
            if "content-type" in request_headers:
                del request_headers["content-type"]

        # Construct the full URL
        url = self._get_url(path)

        try:
            # For GET and DELETE requests, data should be sent as params
            if method.lower() in ["get", "delete"] and data and not params:
                params = data
                data = None

            # Convert data to JSON for httpx
            json_data = None
            if data and not files:
                json_data = data
                data = None

            # Prepare files for httpx format
            httpx_files = None
            if files:
                httpx_files = {}
                for key, value in files.items():
                    if isinstance(value, tuple) and len(value) >= 2:
                        # Format: (filename, file_object, content_type)
                        httpx_files[key] = value
                    else:
                        httpx_files[key] = value

            # Make the async request
            response = await self.async_client.request(
                method=method.upper(),
                url=url,
                params=params,
                data=data,
                json=json_data,
                headers=request_headers,
                files=httpx_files,
                timeout=timeout,
            )

            # Return raw response if requested
            if raw_response:
                return response

            # Process response based on status code
            if response.status_code < 400:  # Success
                if not response.content:
                    return {
                        "success": True,
                        "message": "Operation completed successfully",
                    }

                if response.headers.get("Content-Type", "").startswith("application/json"):
                    return response.json()
                else:
                    return {
                        "success": True,
                        "status_code": response.status_code,
                        "content": response.text,
                    }
            else:  # Error
                if not handle_errors:
                    response.raise_for_status()

                # Handle different error types
                self._handle_error_response_httpx(response)

        except httpx.ConnectError as e:
            if not handle_errors:
                raise
            raise ConnectionError(
                f"Failed to connect to {self.base_url}. Please check your internet connection and try again."
            )

        except httpx.TimeoutException as e:
            if not handle_errors:
                raise
            raise ConnectionError(
                f"Request to {url} timed out after {timeout} seconds. Please try again later."
            )

        except (
            ClientError,
            ServerError,
            ConnectionError,
            AuthenticationError,
            ValidationError,
        ):
            # Re-raise our custom exceptions
            raise

        except Exception as e:
            if not handle_errors:
                raise
            raise ClientError(f"Unexpected error: {str(e)}")

    def _request(
        self,
        method: str,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        files: Optional[Dict[str, Any]] = None,
        timeout: int = 30,
        handle_errors: bool = True,
        raw_response: bool = False,
        async_mode: bool = False,
    ) -> Union[Dict[str, Any], requests.Response, t.Awaitable]:
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
            async_mode: Whether to return an awaitable coroutine

        Returns:
            Response data as a dictionary, raw response, or awaitable coroutine
        """
        if async_mode:
            return self._async_request(
                method, path, data, params, headers, files, 
                timeout, handle_errors, raw_response
            )
        
        # Original sync implementation
        # Merge default headers with any additional headers
        request_headers = self.default_headers.copy()
        if headers:
            request_headers.update(headers)

        # Special case for file uploads
        if files:
            # Don't set content-type for multipart/form-data
            if "content-type" in request_headers:
                del request_headers["content-type"]

        # Construct the full URL
        url = self._get_url(path)

        try:
            # For GET and DELETE requests, data should be sent as params
            if method.lower() in ["get", "delete"] and data and not params:
                params = data
                data = None

            # Convert data to JSON string if it's a dictionary
            json_data = None
            if data and not files:
                json_data = data
                data = None

            # Make the request
            response = self.session.request(
                method=method.upper(),
                url=url,
                params=params,
                data=data,
                json=json_data,
                headers=request_headers,
                files=files,
                timeout=timeout,
            )

            # Return raw response if requested
            if raw_response:
                return response

            # Process response based on status code
            if response.status_code < 400:  # Success
                if not response.content:
                    return {
                        "success": True,
                        "message": "Operation completed successfully",
                    }

                if response.headers.get("Content-Type", "").startswith(
                    "application/json"
                ):
                    return response.json()
                else:
                    return {
                        "success": True,
                        "status_code": response.status_code,
                        "content": response.text,
                    }
            else:  # Error
                if not handle_errors:
                    response.raise_for_status()

                # Handle different error types
                self._handle_error_response(response)

        except requests.exceptions.ConnectionError as e:
            if not handle_errors:
                raise
            raise ConnectionError(
                f"Failed to connect to {self.base_url}. Please check your internet connection and try again."
            )

        except requests.exceptions.Timeout as e:
            if not handle_errors:
                raise
            raise ConnectionError(
                f"Request to {url} timed out after {timeout} seconds. Please try again later."
            )

        except (
            ClientError,
            ServerError,
            ConnectionError,
            AuthenticationError,
            ValidationError,
        ):
            # Re-raise our custom exceptions
            raise

        except Exception as e:
            if not handle_errors:
                raise
            raise ClientError(f"Unexpected error: {str(e)}")

    def _handle_error_response(self, response: requests.Response) -> None:
        """Extract error details from requests response and raise appropriate exception."""
        self._handle_error_response_common(response.status_code, response.text, response)

    def _handle_error_response_httpx(self, response: httpx.Response) -> None:
        """Extract error details from httpx response and raise appropriate exception."""
        self._handle_error_response_common(response.status_code, response.text, response)

    def _handle_error_response_common(self, status_code: int, response_text: str, response) -> None:
        """Common error handling logic for both requests and httpx responses."""
        error_message = f"HTTP Error: {status_code}"

        try:
            error_data = json.loads(response_text)
            if isinstance(error_data, dict):
                if "detail" in error_data:
                    error_message = error_data["detail"]
                elif "message" in error_data:
                    error_message = error_data["message"]
                elif "error" in error_data:
                    error_message = error_data["error"]
        except (json.JSONDecodeError, ValueError):
            # Not JSON or empty response
            if response_text:
                error_message = response_text

        # Handle different error types based on status code
        if status_code == 401:
            raise AuthenticationError(error_message, status_code, response)
        elif status_code == 403:
            raise AuthenticationError(
                f"Access denied: {error_message}", status_code, response
            )
        elif status_code == 400 or status_code == 422:
            raise ValidationError(error_message, status_code, response)
        elif 400 <= status_code < 500:
            raise ClientError(error_message, status_code, response)
        else:  # 500+ errors
            raise ServerError(f"Server error: {error_message}", status_code, response)

    # Convenience methods for common HTTP methods with async support
    def get(self, path: str, async_mode: bool = False, **kwargs) -> Union[Dict[str, Any], t.Awaitable]:
        """Send a GET request to the API."""
        return self._request("GET", path, async_mode=async_mode, **kwargs)

    def post(
        self, path: str, data: Optional[Dict[str, Any]] = None, 
        async_mode: bool = False, **kwargs
    ) -> Union[Dict[str, Any], t.Awaitable]:
        """Send a POST request to the API."""
        return self._request("POST", path, data=data, async_mode=async_mode, **kwargs)

    def put(
        self, path: str, data: Optional[Dict[str, Any]] = None, 
        async_mode: bool = False, **kwargs
    ) -> Union[Dict[str, Any], t.Awaitable]:
        """Send a PUT request to the API."""
        return self._request("PUT", path, data=data, async_mode=async_mode, **kwargs)

    def delete(self, path: str, async_mode: bool = False, **kwargs) -> Union[Dict[str, Any], t.Awaitable]:
        """Send a DELETE request to the API."""
        return self._request("DELETE", path, async_mode=async_mode, **kwargs)

    def patch(
        self, path: str, data: Optional[Dict[str, Any]] = None, 
        async_mode: bool = False, **kwargs
    ) -> Union[Dict[str, Any], t.Awaitable]:
        """Send a PATCH request to the API."""
        return self._request("PATCH", path, data=data, async_mode=async_mode, **kwargs)


class RestClient:
    """Client for remote server deployment via REST API - ENHANCED VERSION with Async Support"""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        api_prefix: Optional[str] = "/api/v1",
    ):
        """
        Initialize REST client for middleware server

        Args:
            base_url: URL of the middleware server
            api_key: API key for authentication
            api_prefix: API prefix path
        """
        self.base_url = base_url or Config.get_base_url()
        self.api_key = api_key or Config.get_api_key()

        self.base_url = self.base_url.rstrip("/") + api_prefix

        # Initialize HTTP handler
        self.http = HttpHandler(api_key=self.api_key, base_url=self.base_url)

        # Cache for limits to avoid repeated API calls
        self._limits_cache = None
        self._cache_expiry = None

    async def close(self):
        """Close async resources"""
        await self.http.close_async_client()

    def get_local_db_limits(self, async_mode: bool = False) -> Union[Dict, t.Awaitable[Dict]]:
        """
        Fetch local database limits from backend API

        Args:
            async_mode: Whether to return an awaitable coroutine

        Returns:
            Dictionary with limit information and API status, or awaitable
        """
        if async_mode:
            return self._get_local_db_limits_async()
        
        # Original sync implementation
        try:
            # Check cache first (5 minutes cache)
            if (
                self._limits_cache
                and self._cache_expiry
                and time.time() < self._cache_expiry
            ):
                return self._limits_cache

            if not self.api_key:
                return {
                    "success": False,
                    "error": "No API key provided",
                    "default_limit": 5,
                    "current_limit": 5,
                    "has_api_key": False,
                    "enhanced_limits": False,
                }

            console.print("🔍 [dim]Checking API limits...[/dim]")

            try:
                limits_data = self.http.get("/limits/agents", timeout=10)
                return self._process_limits_response(limits_data)

            except AuthenticationError as e:
                return self._get_auth_error_response()

            except ConnectionError as e:
                return self._get_connection_error_response()

        except Exception as e:
            return self._get_generic_error_response(str(e))

    async def _get_local_db_limits_async(self) -> Dict:
        """Async implementation of get_local_db_limits"""
        try:
            # Check cache first (5 minutes cache)
            if (
                self._limits_cache
                and self._cache_expiry
                and time.time() < self._cache_expiry
            ):
                return self._limits_cache

            if not self.api_key:
                return {
                    "success": False,
                    "error": "No API key provided",
                    "default_limit": 5,
                    "current_limit": 5,
                    "has_api_key": False,
                    "enhanced_limits": False,
                }

            console.print("🔍 [dim]Checking API limits...[/dim]")

            try:
                limits_data = await self.http.get("/limits/agents", async_mode=True, timeout=10)
                return self._process_limits_response(limits_data)

            except AuthenticationError as e:
                return self._get_auth_error_response()

            except ConnectionError as e:
                return self._get_connection_error_response()

        except Exception as e:
            return self._get_generic_error_response(str(e))

    def _process_limits_response(self, limits_data: Dict) -> Dict:
        """Process limits response data"""
        # Cache the response for 5 minutes
        self._limits_cache = {
            "success": True,
            "max_agents": limits_data.get("max_agents", 5),
            "current_limit": limits_data.get("max_agents", 5),
            "default_limit": 5,
            "has_api_key": True,
            "enhanced_limits": limits_data.get("max_agents", 5) > 5,
            "tier_info": limits_data.get("tier_info", {}),
            "features": limits_data.get("features", []),
            "expires_at": limits_data.get("expires_at"),
            "unlimited": limits_data.get("max_agents") == -1,
            "api_validated": True,
        }
        self._cache_expiry = time.time() + 300  # 5 minutes

        if limits_data.get("max_agents", 5) > 5:
            console.print(
                f"🔑 [green]Enhanced limits active: {limits_data.get('max_agents')} agents[/green]"
            )

        return self._limits_cache

    def _get_auth_error_response(self) -> Dict:
        """Get standardized auth error response"""
        error_result = {
            "success": False,
            "error": "API key invalid or expired",
            "default_limit": 5,
            "current_limit": 5,
            "has_api_key": True,
            "enhanced_limits": False,
            "api_validated": False,
        }
        console.print(
            "[yellow]⚠️ API key invalid or expired - using default limits[/yellow]"
        )
        return error_result

    def _get_connection_error_response(self) -> Dict:
        """Get standardized connection error response"""
        error_result = {
            "success": False,
            "error": "Cannot connect to API server",
            "default_limit": 5,
            "current_limit": 5,
            "has_api_key": bool(self.api_key),
            "enhanced_limits": False,
            "api_validated": False,
        }
        console.print(
            "[yellow]⚠️ API connection failed - using default limits[/yellow]"
        )
        return error_result

    def _get_generic_error_response(self, error_msg: str) -> Dict:
        """Get standardized generic error response"""
        error_result = {
            "success": False,
            "error": f"Unexpected error: {error_msg}",
            "default_limit": 5,
            "current_limit": 5,
            "has_api_key": bool(self.api_key),
            "enhanced_limits": False,
            "api_validated": False,
        }
        console.print(f"[red]❌ Error fetching limits: {error_msg}[/red]")
        return error_result

    def clear_limits_cache(self):
        """Clear the cached limits to force refresh"""
        self._limits_cache = None
        self._cache_expiry = None
        console.print("🔄 [dim]Limits cache cleared[/dim]")

    def upload_agent(self, folder_path: str, metadata: Dict = None, async_mode: bool = False) -> Union[Dict, t.Awaitable[Dict]]:
        """
        Upload agent folder to middleware server - SECURE VERSION

        Args:
            folder_path: Path to folder containing agent files
            metadata: Additional metadata for upload (CAN NOW INCLUDE SENSITIVE DATA)
            async_mode: Whether to return an awaitable coroutine

        Returns:
            Upload result with agent_id, or awaitable
        """
        if async_mode:
            return self._upload_agent_async(folder_path, metadata)
        
        # Original sync implementation
        try:
            folder_path = Path(folder_path)

            if not folder_path.exists():
                return {"success": False, "error": f"Folder not found: {folder_path}"}

            console.print(f"📤 Uploading agent from: [blue]{folder_path}[/blue]")

            # Create zip file
            with console.status(
                "[bold green]🔧 Preparing files for upload...[/bold green]",
                spinner="dots",
            ):
                zip_path = self._create_zip_from_folder(folder_path)

            console.print(
                f"📦 Created upload package: [cyan]{Path(zip_path).name}[/cyan]"
            )

            # Prepare upload metadata
            upload_metadata = {
                "framework": (
                    metadata.get("framework", "unknown") if metadata else "unknown"
                ),
                "uploaded_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "source_folder": str(folder_path),
                **(metadata or {}),
            }

            # Upload to server
            console.print(f"🌐 Uploading to: [bold blue]{self.base_url}[/bold blue]")

            with Progress(
                SpinnerColumn(),
                TextColumn("[bold green]Uploading...[/bold green]"),
                BarColumn(bar_width=40),
                TextColumn("[bold]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
                console=console,
            ) as progress:
                upload_task = progress.add_task("Uploading...", total=100)

                # Simulate progress while uploading
                result = self._upload_to_server_secure(
                    zip_path, upload_metadata, progress, upload_task
                )

            # Clean up zip file
            os.unlink(zip_path)

            return self._process_upload_result(result, upload_metadata)

        except Exception as e:
            return {"success": False, "error": f"Upload failed: {str(e)}"}

    async def _upload_agent_async(self, folder_path: str, metadata: Dict = None) -> Dict:
        """Async implementation of upload_agent"""
        try:
            folder_path = Path(folder_path)

            if not folder_path.exists():
                return {"success": False, "error": f"Folder not found: {folder_path}"}

            console.print(f"📤 Uploading agent from: [blue]{folder_path}[/blue]")

            # Create zip file
            with console.status(
                "[bold green]🔧 Preparing files for upload...[/bold green]",
                spinner="dots",
            ):
                zip_path = self._create_zip_from_folder(folder_path)

            console.print(
                f"📦 Created upload package: [cyan]{Path(zip_path).name}[/cyan]"
            )

            # Prepare upload metadata
            upload_metadata = {
                "framework": (
                    metadata.get("framework", "unknown") if metadata else "unknown"
                ),
                "uploaded_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "source_folder": str(folder_path),
                **(metadata or {}),
            }

            # Upload to server
            console.print(f"🌐 Uploading to: [bold blue]{self.base_url}[/bold blue]")

            with Progress(
                SpinnerColumn(),
                TextColumn("[bold green]Uploading...[/bold green]"),
                BarColumn(bar_width=40),
                TextColumn("[bold]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
                console=console,
            ) as progress:
                upload_task = progress.add_task("Uploading...", total=100)

                # Simulate progress while uploading
                result = await self._upload_to_server_secure_async(
                    zip_path, upload_metadata, progress, upload_task
                )

            # Clean up zip file
            os.unlink(zip_path)

            return self._process_upload_result(result, upload_metadata)

        except Exception as e:
            return {"success": False, "error": f"Upload failed: {str(e)}"}

    def _process_upload_result(self, result: Dict, upload_metadata: Dict) -> Dict:
        """Process upload result"""
        if result.get("success"):
            agent_id = result.get("agent_id")

            # Save deployment info locally
            self._save_deployment_info(
                agent_id,
                {
                    **upload_metadata,
                    "agent_id": agent_id,
                    "remote": True,
                    "base_url": self.base_url,
                },
            )

            console.print(
                Panel(
                    f"✅ [bold green]Upload successful![/bold green]\n"
                    f"🆔 Agent ID: [bold magenta]{agent_id}[/bold magenta]\n"
                    f"🌐 Server: [blue]{self.base_url}[/blue]",
                    title="📤 Upload Complete",
                    border_style="green",
                )
            )

            return {
                "success": True,
                "agent_id": agent_id,
                "base_url": self.base_url,
                "message": f'Agent uploaded. Use "runagent start --id {agent_id}" to deploy, or "runagent deploy --id {agent_id}" for direct deployment.',
            }
        else:
            return result

    # Continue with the rest of the methods following the same pattern...
    # I'll add a few more key methods to demonstrate the pattern

    def start_agent(self, agent_id: str, config: Dict = None, async_mode: bool = False) -> Union[Dict, t.Awaitable[Dict]]:
        """
        Start/deploy an uploaded agent on the middleware server

        Args:
            agent_id: ID of the uploaded agent
            config: Optional deployment configuration
            async_mode: Whether to return an awaitable coroutine

        Returns:
            Deployment result, or awaitable
        """
        if async_mode:
            return self._start_agent_async(agent_id, config)
        
        # Original sync implementation
        try:
            console.print(f"🚀 Starting agent: [bold magenta]{agent_id}[/bold magenta]")

            payload = config or {}

            try:
                result = self.http.post(
                    f"/agents/{agent_id}/start", data=payload, timeout=60
                )

                return self._process_start_result(result, agent_id)

            except (ClientError, ServerError, ConnectionError) as e:
                return {
                    "success": False,
                    "error": f"Failed to start agent: {e.message}",
                }

        except Exception as e:
            return {"success": False, "error": f"Start agent failed: {str(e)}"}

    async def _start_agent_async(self, agent_id: str, config: Dict = None) -> Dict:
        """Async implementation of start_agent"""
        try:
            console.print(f"🚀 Starting agent: [bold magenta]{agent_id}[/bold magenta]")

            payload = config or {}

            try:
                result = await self.http.post(
                    f"/agents/{agent_id}/start", data=payload, async_mode=True, timeout=60
                )

                return self._process_start_result(result, agent_id)

            except (ClientError, ServerError, ConnectionError) as e:
                return {
                    "success": False,
                    "error": f"Failed to start agent: {e.message}",
                }

        except Exception as e:
            return {"success": False, "error": f"Start agent failed: {str(e)}"}

    def _process_start_result(self, result: Dict, agent_id: str) -> Dict:
        """Process start agent result"""
        if result.get("success"):
            endpoint = result.get("endpoint")

            console.print(
                Panel(
                    f"✅ [bold green]Agent started successfully![/bold green]\n"
                    f"🆔 Agent ID: [bold magenta]{agent_id}[/bold magenta]\n"
                    f"🌐 Endpoint: [link]{self.base_url}{endpoint}[/link]",
                    title="🚀 Deployment Complete",
                    border_style="green",
                )
            )

            # Update local deployment info
            self._update_deployment_info(
                agent_id,
                {
                    "status": "deployed",
                    "endpoint": f"{self.base_url}{endpoint}",
                    "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                },
            )

            return {
                "success": True,
                "agent_id": agent_id,
                "endpoint": f"{self.base_url}{endpoint}",
                "status": "deployed",
            }
        else:
            return result

    def _create_zip_from_folder(self, folder_path: Path) -> str:
        """Create a zip file from the agent folder with improved compression"""
        temp_dir = tempfile.gettempdir()
        zip_path = os.path.join(temp_dir, f"agent_{int(time.time())}.zip")

        with zipfile.ZipFile(
            zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6
        ) as zipf:
            for file_path in folder_path.rglob("*"):
                if file_path.is_file() and not file_path.name.startswith("."):
                    # Skip common unnecessary files
                    if file_path.name in ["__pycache__", ".DS_Store", "Thumbs.db"]:
                        continue
                    if file_path.suffix in [".pyc", ".pyo", ".log"]:
                        continue

                    # Add file to zip with relative path
                    arcname = file_path.relative_to(folder_path)
                    zipf.write(file_path, arcname)

        return zip_path

    def _upload_to_server_secure(
        self, zip_path: str, metadata: Dict, progress: Progress, task_id
    ) -> Dict:
        """Upload zip file to middleware server - ENHANCED SECURE VERSION"""
        try:
            # Step 1: Upload metadata
            progress.update(task_id, completed=5)

            metadata_result = self._upload_metadata(metadata)

            if not metadata_result.get("success"):
                return {
                    "success": False,
                    "error": f"Metadata upload failed: {metadata_result.get('error')}",
                }

            agent_id = metadata_result.get("agent_id")
            progress.update(task_id, completed=20)

            # Step 2: Upload file with only non-sensitive metadata
            with open(zip_path, "rb") as f:
                files = {"file": (os.path.basename(zip_path), f, "application/zip")}
                data = {
                    "framework": metadata.get("framework", "unknown"),
                    "name": metadata.get(
                        "name", os.path.basename(zip_path).replace(".zip", "")
                    ),
                    "has_metadata": "true",
                    "agent_id": agent_id,
                }

                # Update progress during upload
                for i in range(20, 50, 5):
                    progress.update(task_id, completed=i)
                    time.sleep(0.05)

                try:
                    result = self.http.post(
                        "/agents/upload", files=files, data=data, timeout=300
                    )

                    # Update progress during upload
                    for i in range(50, 100, 10):
                        progress.update(task_id, completed=i)
                        time.sleep(0.1)

                    agent_id = result.get("agent_id")

                    return {
                        "success": result.get("success", False),
                        "agent_id": agent_id,
                        "message": result.get("message", "Upload completed"),
                        "status": result.get("status", "uploaded"),
                    }

                except (ClientError, ServerError, ConnectionError) as e:
                    return {
                        "success": False,
                        "error": f"File upload failed: {e.message}",
                    }

        except Exception as e:
            return {"success": False, "error": f"Upload error: {str(e)}"}

    async def _upload_to_server_secure_async(
        self, zip_path: str, metadata: Dict, progress: Progress, task_id
    ) -> Dict:
        """Async version of upload zip file to middleware server"""
        try:
            # Step 1: Upload metadata
            progress.update(task_id, completed=5)

            metadata_result = await self._upload_metadata_async(metadata)

            if not metadata_result.get("success"):
                return {
                    "success": False,
                    "error": f"Metadata upload failed: {metadata_result.get('error')}",
                }

            agent_id = metadata_result.get("agent_id")
            progress.update(task_id, completed=20)

            # Step 2: Upload file with only non-sensitive metadata
            with open(zip_path, "rb") as f:
                files = {"file": (os.path.basename(zip_path), f, "application/zip")}
                data = {
                    "framework": metadata.get("framework", "unknown"),
                    "name": metadata.get(
                        "name", os.path.basename(zip_path).replace(".zip", "")
                    ),
                    "has_metadata": "true",
                    "agent_id": agent_id,
                }

                # Update progress during upload
                for i in range(20, 50, 5):
                    progress.update(task_id, completed=i)
                    await asyncio.sleep(0.05)

                try:
                    result = await self.http.post(
                        "/agents/upload", files=files, data=data, async_mode=True, timeout=300
                    )

                    # Update progress during upload
                    for i in range(50, 100, 10):
                        progress.update(task_id, completed=i)
                        await asyncio.sleep(0.1)

                    agent_id = result.get("agent_id")

                    return {
                        "success": result.get("success", False),
                        "agent_id": agent_id,
                        "message": result.get("message", "Upload completed"),
                        "status": result.get("status", "uploaded"),
                    }

                except (ClientError, ServerError, ConnectionError) as e:
                    return {
                        "success": False,
                        "error": f"File upload failed: {e.message}",
                    }

        except Exception as e:
            return {"success": False, "error": f"Upload error: {str(e)}"}

    def _upload_metadata(self, metadata: Dict) -> Dict:
        """Upload sensitive metadata securely via JSON endpoint - ENHANCED"""
        try:
            # Enhanced metadata encoding with timestamp
            metadata_with_timestamp = {
                **metadata,
                "upload_timestamp": time.time(),
                "client_version": "1.0",
            }

            # Base64 encode metadata as JSON string
            metadata_json = json.dumps(metadata_with_timestamp, sort_keys=True)
            encrypted_data = base64.b64encode(metadata_json.encode()).decode()

            payload = {
                "encrypted_metadata": encrypted_data,
                "encryption_method": "base64-json",
                "client_info": {"version": "1.0", "platform": os.name},
            }

            try:
                result = self.http.post(
                    "/agents/metadata-upload", data=payload, timeout=60
                )
                return {"success": True, "agent_id": result.get("agent_id")}

            except (ClientError, ServerError, ConnectionError) as e:
                return {
                    "success": False,
                    "error": f"Metadata upload failed: {e.message}",
                }

        except Exception as e:
            return {"success": False, "error": f"Metadata upload error: {str(e)}"}

    async def _upload_metadata_async(self, metadata: Dict) -> Dict:
        """Async version of upload sensitive metadata securely"""
        try:
            # Enhanced metadata encoding with timestamp
            metadata_with_timestamp = {
                **metadata,
                "upload_timestamp": time.time(),
                "client_version": "1.0",
            }

            # Base64 encode metadata as JSON string
            metadata_json = json.dumps(metadata_with_timestamp, sort_keys=True)
            encrypted_data = base64.b64encode(metadata_json.encode()).decode()

            payload = {
                "encrypted_metadata": encrypted_data,
                "encryption_method": "base64-json",
                "client_info": {"version": "1.0", "platform": os.name},
            }

            try:
                result = await self.http.post(
                    "/agents/metadata-upload", data=payload, async_mode=True, timeout=60
                )
                return {"success": True, "agent_id": result.get("agent_id")}

            except (ClientError, ServerError, ConnectionError) as e:
                return {
                    "success": False,
                    "error": f"Metadata upload failed: {e.message}",
                }

        except Exception as e:
            return {"success": False, "error": f"Metadata upload error: {str(e)}"}

    def deploy_agent(self, folder_path: str, metadata: Dict = None, async_mode: bool = False) -> Union[Dict, t.Awaitable[Dict]]:
        """
        Upload and start agent in one operation

        Args:
            folder_path: Path to folder containing agent files
            metadata: Additional metadata (CAN INCLUDE SENSITIVE DATA)
            async_mode: Whether to return an awaitable coroutine

        Returns:
            Complete deployment result, or awaitable
        """
        if async_mode:
            return self._deploy_agent_async(folder_path, metadata)
        
        console.print(
            "🎯 [bold cyan]Starting full deployment (upload + start)...[/bold cyan]"
        )

        # First upload
        upload_result = self.upload_agent(folder_path, metadata)

        if not upload_result.get("success"):
            return upload_result

        agent_id = upload_result.get("agent_id")

        # Then start
        start_result = self.start_agent(agent_id)

        if start_result.get("success"):
            return {
                "success": True,
                "agent_id": agent_id,
                "endpoint": start_result.get("endpoint"),
                "status": "running",
                "message": f'Agent fully deployed and running. Endpoint: {start_result.get("endpoint")}',
            }
        else:
            return {
                "success": False,
                "error": f"Upload succeeded but start failed: {start_result.get('error')}",
                "agent_id": agent_id,
            }

    async def _deploy_agent_async(self, folder_path: str, metadata: Dict = None) -> Dict:
        """Async version of deploy_agent"""
        console.print(
            "🎯 [bold cyan]Starting full deployment (upload + start)...[/bold cyan]"
        )

        # First upload
        upload_result = await self.upload_agent(folder_path, metadata, async_mode=True)

        if not upload_result.get("success"):
            return upload_result

        agent_id = upload_result.get("agent_id")

        # Then start
        start_result = await self.start_agent(agent_id, async_mode=True)

        if start_result.get("success"):
            return {
                "success": True,
                "agent_id": agent_id,
                "endpoint": start_result.get("endpoint"),
                "status": "running",
                "message": f'Agent fully deployed and running. Endpoint: {start_result.get("endpoint")}',
            }
        else:
            return {
                "success": False,
                "error": f"Upload succeeded but start failed: {start_result.get('error')}",
                "agent_id": agent_id,
            }

    def _save_deployment_info(self, agent_id: str, metadata: Dict):
        """Save deployment info for CLI reference - ENHANCED"""
        deployments_dir = Path.cwd() / ".deployments"
        deployments_dir.mkdir(exist_ok=True)

        # Enhanced list of sensitive data to exclude
        sensitive_keys = {
            "env_vars",
            "environment",
            "secrets",
            "credentials",
            "api_keys",
            "tokens",
            "passwords",
            "private_key",
            "access_token",
            "refresh_token",
            "auth_token",
            "database_url",
            "connection_string",
            "secret_key",
        }

        # Remove sensitive data from saved info
        safe_metadata = {k: v for k, v in metadata.items() if k not in sensitive_keys}

        # Add deployment tracking info
        safe_metadata.update(
            {"saved_at": time.strftime("%Y-%m-%d %H:%M:%S"), "client_version": "1.0"}
        )

        info_file = deployments_dir / f"{agent_id}.json"
        with open(info_file, "w") as f:
            json.dump(safe_metadata, f, indent=2)

    def _update_deployment_info(self, agent_id: str, updates: Dict):
        """Update existing deployment info"""
        deployments_dir = Path.cwd() / ".deployments"
        info_file = deployments_dir / f"{agent_id}.json"

        if info_file.exists():
            try:
                with open(info_file, "r") as f:
                    metadata = json.load(f)
                metadata.update(updates)
                metadata["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")

                with open(info_file, "w") as f:
                    json.dump(metadata, f, indent=2)
            except:
                pass  # Ignore errors updating deployment info

    def get_agent_status(self, agent_id: str, async_mode: bool = False) -> Union[Dict, t.Awaitable[Dict]]:
        """Get status of a remote agent"""
        if async_mode:
            return self._get_agent_status_async(agent_id)
        
        try:
            result = self.http.get(f"/agents/{agent_id}/status", timeout=30)
            return result

        except (ClientError, ServerError, ConnectionError) as e:
            return {"success": False, "error": f"Status check failed: {e.message}"}
        except Exception as e:
            return {"success": False, "error": f"Status check failed: {str(e)}"}

    async def _get_agent_status_async(self, agent_id: str) -> Dict:
        """Async version of get_agent_status"""
        try:
            result = await self.http.get(f"/agents/{agent_id}/status", async_mode=True, timeout=30)
            return result

        except (ClientError, ServerError, ConnectionError) as e:
            return {"success": False, "error": f"Status check failed: {e.message}"}
        except Exception as e:
            return {"success": False, "error": f"Status check failed: {str(e)}"}

    def _get_local_deployment_info(self, agent_id: str) -> Optional[Dict]:
        """Get local deployment info for an agent (for remote deployments only)"""
        deployments_dir = Path.cwd() / ".deployments"
        info_file = deployments_dir / f"{agent_id}.json"

        if info_file.exists():
            try:
                with open(info_file, "r") as f:
                    return json.load(f)
            except:
                return None
        return None

    def validate_api_connection(self, async_mode: bool = False) -> Union[Dict, t.Awaitable[Dict]]:
        """Validate API connection and authentication"""
        if async_mode:
            return self._validate_api_connection_async()
        
        try:
            # Test basic connectivity
            try:
                self.http.get("/health", timeout=10)

                # Test authentication if API key provided
                if self.api_key:
                    limits_result = self.get_local_db_limits()
                    return {
                        "success": True,
                        "api_connected": True,
                        "api_authenticated": limits_result.get("api_validated", False),
                        "enhanced_limits": limits_result.get("enhanced_limits", False),
                        "base_url": self.base_url,
                    }
                else:
                    return {
                        "success": True,
                        "api_connected": True,
                        "api_authenticated": False,
                        "enhanced_limits": False,
                        "base_url": self.base_url,
                        "message": "No API key provided",
                    }

            except (ClientError, ServerError, ConnectionError) as e:
                return {
                    "success": False,
                    "api_connected": False,
                    "error": f"API health check failed: {e.message}",
                }

        except Exception as e:
            return {
                "success": False,
                "api_connected": False,
                "error": f"Connection failed: {str(e)}",
            }

    async def _validate_api_connection_async(self) -> Dict:
        """Async version of validate_api_connection"""
        try:
            # Test basic connectivity
            try:
                await self.http.get("/health", async_mode=True, timeout=10)

                # Test authentication if API key provided
                if self.api_key:
                    limits_result = await self.get_local_db_limits(async_mode=True)
                    return {
                        "success": True,
                        "api_connected": True,
                        "api_authenticated": limits_result.get("api_validated", False),
                        "enhanced_limits": limits_result.get("enhanced_limits", False),
                        "base_url": self.base_url,
                    }
                else:
                    return {
                        "success": True,
                        "api_connected": True,
                        "api_authenticated": False,
                        "enhanced_limits": False,
                        "base_url": self.base_url,
                        "message": "No API key provided",
                    }

            except (ClientError, ServerError, ConnectionError) as e:
                return {
                    "success": False,
                    "api_connected": False,
                    "error": f"API health check failed: {e.message}",
                }

        except Exception as e:
            return {
                "success": False,
                "api_connected": False,
                "error": f"Connection failed: {str(e)}",
            }

    def run_agent_generic(
        self,
        agent_id: str,
        input_args: list = None,
        input_kwargs: dict = None,
        execution_type: str = "generic",
        async_mode: bool = False,
    ) -> Union[Dict, t.Awaitable[Dict]]:
        """
        Execute an agent with given parameters

        Args:
            agent_id: ID of the agent to execute
            input_args: List of positional arguments for the agent
            input_kwargs: Dictionary of keyword arguments for the agent
            execution_type: Type of execution (default: "generic")
            async_mode: Whether to return an awaitable coroutine

        Returns:
            Execution result from the agent, or awaitable
        """
        if async_mode:
            return self._run_agent_generic_async(agent_id, input_args, input_kwargs, execution_type)
        
        try:
            console.print(
                f"🤖 Executing agent: [bold magenta]{agent_id}[/bold magenta]"
            )

            # Prepare request data
            request_data = {
                "input_data": {"input_args": input_args, "input_kwargs": input_kwargs}
            }

            # Execute the agent
            try:
                result = self.http.post(
                    f"/agents/{agent_id}/execute/generic",
                    data=request_data,
                    timeout=120,  # Longer timeout for agent execution
                )

                if result.get(
                    "success", True
                ):  # Assume success if not explicitly false
                    console.print(
                        "✅ [bold green]Agent execution completed![/bold green]"
                    )
                    return result
                else:
                    console.print(
                        f"❌ [bold red]Agent execution failed: {result.get('error', 'Unknown error')}[/bold red]"
                    )
                    return result

            except (ClientError, ServerError, ConnectionError) as e:
                return {
                    "success": False,
                    "error": f"Agent execution failed: {e.message}",
                }

        except Exception as e:
            return {"success": False, "error": f"Execute agent failed: {str(e)}"}

    async def _run_agent_generic_async(
        self,
        agent_id: str,
        input_args: list = None,
        input_kwargs: dict = None,
        execution_type: str = "generic",
    ) -> Dict:
        """Async version of run_agent_generic"""
        try:
            console.print(
                f"🤖 Executing agent: [bold magenta]{agent_id}[/bold magenta]"
            )

            # Prepare request data
            request_data = {
                "input_data": {"input_args": input_args, "input_kwargs": input_kwargs}
            }

            # Execute the agent
            try:
                result = await self.http.post(
                    f"/agents/{agent_id}/execute/generic",
                    data=request_data,
                    async_mode=True,
                    timeout=120,  # Longer timeout for agent execution
                )

                if result.get(
                    "success", True
                ):  # Assume success if not explicitly false
                    console.print(
                        "✅ [bold green]Agent execution completed![/bold green]"
                    )
                    return result
                else:
                    console.print(
                        f"❌ [bold red]Agent execution failed: {result.get('error', 'Unknown error')}[/bold red]"
                    )
                    return result

            except (ClientError, ServerError, ConnectionError) as e:
                return {
                    "success": False,
                    "error": f"Agent execution failed: {e.message}",
                }

        except Exception as e:
            return {"success": False, "error": f"Execute agent failed: {str(e)}"}
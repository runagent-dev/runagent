import base64
import json
import os
import re
import tempfile
import time
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union

import requests
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

from runagent.utils.config import Config
from runagent.constants import DEFAULT_TIMEOUT_SECONDS
from runagent.utils.agent_id import (
    generate_agent_id,
    generate_agent_fingerprint,
    get_agent_metadata
)
from runagent.utils.agent import get_agent_config, validate_agent

console = Console()


class HttpException(Exception):
    """Base exception for HTTP errors"""

    def __init__(self, message: str, status_code: int = None, response: requests.Response = None):
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
    """HTTP handler for API requests"""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/") if base_url else ""
        
        # Create persistent session
        self.session = requests.Session()
        
        # Set default headers
        self.session.headers.update({
            "accept": "application/json",
            "content-type": "application/json",
            "User-Agent": "RunAgent-CLI/1.0"
        })

        if self.api_key:
            # Support both JWT tokens and API keys
            self.session.headers.update({
                "Authorization": f"Bearer {self.api_key}"
            })

    def _get_url(self, path: str) -> str:
        """Construct full URL from base URL and path"""
        return f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"

    def _handle_error_response(self, response: requests.Response) -> None:
        """Handle error responses - UPDATED for middleware errors"""
        error_message = f"HTTP Error: {response.status_code}"

        try:
            error_data = response.json()
            if isinstance(error_data, dict):
                # Handle middleware-style errors
                if "detail" in error_data:
                    error_message = error_data["detail"]
                elif "error" in error_data:
                    # Handle both string errors and error objects
                    error_obj = error_data["error"]
                    if isinstance(error_obj, dict):
                        error_message = error_obj.get("message", str(error_obj))
                    else:
                        error_message = str(error_obj)
                elif "message" in error_data and error_data["message"] is not None:
                    error_message = error_data["message"]
        except (json.JSONDecodeError, ValueError):
            if response.text:
                error_message = response.text

        # Handle different error types based on status code
        if response.status_code == 401:
            if "Not authenticated" in error_message:
                raise AuthenticationError("API key is invalid or expired", response.status_code, response)
            else:
                raise AuthenticationError(error_message, response.status_code, response)
        elif response.status_code == 403:
            raise AuthenticationError(f"Access denied: {error_message}", response.status_code, response)
        elif response.status_code in (400, 422):
            raise ValidationError(error_message, response.status_code, response)
        elif 400 <= response.status_code < 500:
            raise ClientError(error_message, response.status_code, response)
        else:  # 500+ errors
            raise ServerError(f"Server error: {error_message}", response.status_code, response)

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
    ) -> Union[Dict[str, Any], requests.Response]:
        """Core request method"""

        url = self._get_url(path)

        # Prepare headers
        request_headers = {}
        if headers:
            request_headers.update(headers)

        # Special case for file uploads - remove content-type for multipart
        if files and "content-type" in self.session.headers:
            request_headers["content-type"] = None

        # For GET and DELETE requests, data should be sent as params
        if method.upper() in ["GET", "DELETE"] and data and not params:
            params = data
            data = None

        try:
            if os.getenv("DISABLE_TRY_CATCH"):
                console.print("[REQUEST] to: ", url)
            response = self.session.request(
                method=method.upper(),
                url=url,
                params=params,
                json=data if data is not None and not files else None,
                data=None if data is not None and not files else data,
                headers=request_headers if request_headers else None,
                files=files,
                timeout=timeout,
            )

            if response.status_code >= 400:
                if handle_errors:
                    self._handle_error_response(response)
                else:
                    response.raise_for_status()

            return response

        except requests.exceptions.ConnectTimeout:
            if not handle_errors:
                raise
            raise ConnectionError(
                f"Failed to connect to {self.base_url}. Please check your internet connection and try again."
            )
        except requests.exceptions.Timeout:
            if not handle_errors:
                raise
            raise ConnectionError(
                f"Request to {url} timed out after {timeout} seconds. Please try again later."
            )
        except requests.exceptions.ConnectionError:
            if not handle_errors:
                raise
            raise ConnectionError(
                f"Failed to connect to {self.base_url}. Please check your internet connection and try again."
            )
        except (ClientError, ServerError, ConnectionError, AuthenticationError, ValidationError):
            raise
        except Exception as e:
            if os.getenv('DISABLE_TRY_CATCH'):
                raise
            if not handle_errors:
                raise
            raise ClientError(f"Unexpected error: {str(e)}")

    def get(self, path: str, **kwargs) -> Union[Dict[str, Any], requests.Response]:
        """Send a GET request to the API."""
        return self._request("GET", path, **kwargs)

    def post(self, path: str, data: Optional[Dict[str, Any]] = None, **kwargs) -> Union[Dict[str, Any], requests.Response]:
        """Send a POST request to the API."""
        return self._request("POST", path, data=data, **kwargs)

    def put(self, path: str, data: Optional[Dict[str, Any]] = None, **kwargs) -> Union[Dict[str, Any], requests.Response]:
        """Send a PUT request to the API."""
        return self._request("PUT", path, data=data, **kwargs)

    def delete(self, path: str, **kwargs) -> Union[Dict[str, Any], requests.Response]:
        """Send a DELETE request to the API."""
        return self._request("DELETE", path, **kwargs)

    def patch(self, path: str, data: Optional[Dict[str, Any]] = None, **kwargs) -> Union[Dict[str, Any], requests.Response]:
        """Send a PATCH request to the API."""
        return self._request("PATCH", path, data=data, **kwargs)

    def close(self):
        """Close the session"""
        self.session.close()

    def __del__(self):
        """Cleanup session on deletion"""
        try:
            self.session.close()
        except:
            pass



# runagent/sdk/rest_client.py - FIXED RestClient initialization

class RestClient:
    """Client for remote server deployment via REST API"""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        api_prefix: Optional[str] = "/api/v1",
        is_local: Optional[bool] = True
    ):
        """Initialize REST client for middleware server"""
        self.api_key = api_key or Config.get_api_key()
        
        # Fix base URL construction
        if base_url:
            self.base_url = base_url.rstrip("/") + api_prefix
        else:
            raw_base_url = Config.get_base_url()
            self.base_url = raw_base_url.rstrip("/") + api_prefix

        # Initialize HTTP handler directly with API key
        # The middleware auth system will handle JWT conversion automatically
        # if is_local:
        #     self.http = HttpHandler(base_url=self.base_url)
        # else:
        self.http = HttpHandler(api_key=self.api_key, base_url=self.base_url)

        # Cache for limits to avoid repeated API calls
        self._limits_cache = None
        self._cache_expiry = None

    def close(self):
        """Close HTTP resources"""
        self.http.close()

    def _validate_entrypoint_files(self, folder_path: Path, agent_config) -> None:
        """Validate that all entrypoint files exist in the filtered file structure"""
        from runagent.utils.gitignore import get_filtered_files
        
        # Get filtered file structure
        file_structure = get_filtered_files(folder_path)
        
        # Check each entrypoint
        if agent_config.agent_architecture is None or not agent_config.agent_architecture.entrypoints:
            return []  # No entrypoints configured
        for entrypoint in agent_config.agent_architecture.entrypoints:
            file_path = entrypoint.file
            
            if file_path not in file_structure:
                raise ValueError(
                    f"Entrypoint file '{file_path}' not found in agent directory. "
                    f"This file may be ignored by .gitignore or doesn't exist. "
                    f"Available files: {', '.join(file_structure[:10])}{'...' if len(file_structure) > 10 else ''}"
                )

    def _get_project_id(self) -> str:
        """Get the active project ID from configuration"""
        try:
            from runagent.sdk.config import SDKConfig
            config = SDKConfig()
            project_id = config._config.get("active_project_id")
            if project_id:
                return project_id
            
            # Fallback to a default project ID if none is configured
            console.print("⚠️ [yellow]No active project ID found, using default[/yellow]")
            return "default"
        except Exception as e:
            console.print(f"⚠️ [yellow]Could not get project ID: {e}, using default[/yellow]")
            return "default"

    def _check_limits_cache(self) -> Optional[Dict]:
        """Check if limits cache is valid"""
        if self._limits_cache and self._cache_expiry and time.time() < self._cache_expiry:
            return self._limits_cache
        return None

    def _get_no_api_key_response(self) -> Dict:
        """Get standardized no API key response"""
        return {
            "success": False,
            "error": "No API key provided",
            "default_limit": 5,
            "current_limit": 5,
            "has_api_key": False,
            "enhanced_limits": False,
        }

    def _process_limits_response(self, response: requests.Response) -> Dict:
        """Process limits response data"""
        limits_data = response.json()
        
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
            console.print(f"🔑 [green]Enhanced limits active: {limits_data.get('max_agents')} agents[/green]")

        return self._limits_cache

    def _get_error_response(self, error_type: str, error_msg: str = None) -> Dict:
        """Get standardized error response"""
        error_responses = {
            "auth": {
                "success": False,
                "error": "API key invalid or expired",
                "message": "[yellow]⚠️ API key invalid or expired - using default limits[/yellow]"
            },
            "connection": {
                "success": False,
                "error": "Cannot connect to API server",
                "message": "[yellow]⚠️ API connection failed - using default limits[/yellow]"
            },
            "generic": {
                "success": False,
                "error": f"Unexpected error: {error_msg}",
                "message": f"[red]❌ Error fetching limits: {error_msg}[/red]"
            }
        }
        
        response = error_responses.get(error_type, error_responses["generic"])
        response.update({
            "default_limit": 5,
            "current_limit": 5,
            "has_api_key": bool(self.api_key),
            "enhanced_limits": False,
            "api_validated": False,
        })
        
        console.print(response["message"])
        return response

    def _create_progress_bar(self, initial_description: str = "Processing..."):
        """Create a standardized progress bar for operations"""
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold green]{task.description}[/bold green]"),
            BarColumn(bar_width=40),
            TextColumn("[bold]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=console,
        )
        task_id = progress.add_task(initial_description, total=100)
        return progress, task_id

    def get_local_db_limits(self) -> Dict:
        """Fetch local database limits from backend API"""
        try:
            # Check cache first
            cached_result = self._check_limits_cache()
            if cached_result:
                return cached_result

            if not self.api_key:
                return self._get_no_api_key_response()

            console.print("🔍 [dim]Checking API limits...[/dim]")

            try:
                response = self.http.get("/limits/agents", timeout=10)
                return self._process_limits_response(response)

            except AuthenticationError:
                return self._get_error_response("auth")
            except ConnectionError:
                return self._get_error_response("connection")

        except Exception as e:
            if os.getenv('DISABLE_TRY_CATCH'):
                raise
            return self._get_error_response("generic", str(e))

    def clear_limits_cache(self):
        """Clear the cached limits to force refresh"""
        self._limits_cache = None
        self._cache_expiry = None
        console.print("🔄 [dim]Limits cache cleared[/dim]")

    def _create_zip_from_folder(self, agent_id: str, folder_path: Path) -> str:
        """Create zip file from agent folder respecting .gitignore"""
        import tempfile
        import zipfile
        import shutil
        from runagent.utils.gitignore import get_filtered_files
        
        # Create temporary directory for filtered files
        temp_dir = tempfile.mkdtemp()
        filtered_dir = os.path.join(temp_dir, "agent")
        os.makedirs(filtered_dir, exist_ok=True)
        
        try:
            # Get filtered file structure
            filtered_files = get_filtered_files(folder_path)
            
            # Copy filtered files to temporary directory
            for file_path in filtered_files:
                src_path = folder_path / file_path
                dst_path = Path(filtered_dir) / file_path
                
                # Create parent directories if needed
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Copy file
                shutil.copy2(src_path, dst_path)
            
            # Create zip file from filtered directory
            zip_path = os.path.join(temp_dir, f"agent_{agent_id[:8]}.zip")
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
                for root, dirs, files in os.walk(filtered_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, filtered_dir)
                        zipf.write(file_path, arcname)
            
            return zip_path
            
        except Exception as e:
            # Clean up temporary directory on error
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise e

    def _check_agent_exists_error(self, result: Dict, folder_path: Path, overwrite: bool) -> Dict:
        """Check if the error is due to agent already existing and handle user prompt"""
        from rich.prompt import Confirm
        from runagent.utils.agent import get_agent_config
        
        # Get agent ID for error messages
        agent_config = get_agent_config(folder_path)
        agent_id = agent_config.agent_id
        
        error_info = result.get("error", {})
        
        # Handle both string and dict error formats
        if isinstance(error_info, str):
            error_message = error_info
            # Check for common error patterns
            if "already exists" in error_message.lower() or "agent already exists" in error_message.lower():
                console.print(f"[yellow]Agent Already Exists[/yellow]")
                console.print(f"   Agent ID: [magenta]{agent_id}[/magenta]")
                console.print(f"   {error_message}")
                
                # Ask user if they want to overwrite
                if not overwrite:
                    console.print(f"[cyan]Use --overwrite flag or confirm below to replace the existing agent[/cyan]")
                    if Confirm.ask("Do you want to overwrite the existing agent?", default=True):
                        # Return special code to indicate retry needed
                        return {
                            "success": False,
                            "error": "RETRY_WITH_OVERWRITE",
                            "code": "RETRY_WITH_OVERWRITE"
                        }
                    else:
                        return {
                            "success": False,
                            "error": "Upload cancelled by user",
                            "code": "USER_CANCELLED"
                        }
                else:
                    # Already trying to overwrite but still failed
                    return result
            elif "permission" in error_message.lower() or "not found" in error_message.lower():
                console.print(f"❌ [red]Project Access Error[/red]")
                console.print(f"   {error_message}")
                console.print(f"[cyan]This agent exists under a different project. Switch to the correct project to modify it.[/cyan]")
                return {
                    "success": False,
                    "error": f"Agent exists under different project: {error_message}",
                    "code": "WRONG_PROJECT"
                }
        
        elif isinstance(error_info, dict):
            error_code = error_info.get("code")
            error_message = error_info.get("message", "")
            
            if error_code == "INSUFFICIENT_PERMISSIONS":
                console.print(f"❌ [red]Project Access Error[/red]")
                console.print(f"   {error_message}")
                console.print(f"[cyan]This agent exists under a different project. Switch to the correct project to modify it.[/cyan]")
                return {
                    "success": False,
                    "error": f"Agent exists under different project: {error_message}",
                    "code": "WRONG_PROJECT"
                }
            
            elif error_code == "RESOURCE_ALREADY_EXISTS":
                console.print(f"[yellow]Agent Already Exists[/yellow]")
                console.print(f"   Agent ID: [magenta]{agent_id}[/magenta]")
                console.print(f"   {error_message}")
                
                # Ask user if they want to overwrite
                if not overwrite:
                    console.print(f"[cyan]Use --overwrite flag or confirm below to replace the existing agent[/cyan]")
                    if Confirm.ask("Do you want to overwrite the existing agent?", default=True):
                        # Return special code to indicate retry needed
                        return {
                            "success": False,
                            "error": "RETRY_WITH_OVERWRITE",
                            "code": "RETRY_WITH_OVERWRITE"
                        }
                    else:
                        return {
                            "success": False,
                            "error": "Upload cancelled by user",
                            "code": "USER_CANCELLED"
                        }
                else:
                    # Already trying to overwrite but still failed
                    return result
        
        # For other errors, return as-is
        return result

    def _upload_agent_metadata_to_server(self, config_data: Dict, agent_id: str) -> Dict:
        """Upload agent metadata (config, entrypoints) to middleware server"""
        try:
            if not agent_id:
                return {"success": False, "error": "No agent_id provided"}
            
            # Use the full agent config directly
            # payload = {
            #     "id": agent_id,
            #     "config": agent_config
            # }

            try:

                response = self.http.post("/agents/metadata-upload", data=config_data, timeout=60)
                result = response.json()
                
                # Handle new API response format
                if result.get("success"):
                    return {
                        "success": True, 
                        "agent_id": result.get("data", {}).get("agent_id", agent_id),
                        "entrypoints_created": result.get("data", {}).get("entrypoints_created", 0),
                        "entrypoint_ids": result.get("data", {}).get("entrypoint_ids", [])
                    }
                else:
                    error_info = result.get("error", {})
                    return {
                        "success": False, 
                        "error": f"Metadata upload failed: {error_info.get('message', 'Unknown error')}",
                        "error_code": error_info.get("code", "UNKNOWN_ERROR")
                    }

            except (ClientError, ServerError, ConnectionError) as e:
                if os.getenv('DISABLE_TRY_CATCH'):
                    raise
                return {"success": False, "error": f"Metadata upload failed: {e.message}"}

        except Exception as e:
            if os.getenv('DISABLE_TRY_CATCH'):
                raise
            return {"success": False, "error": f"Metadata upload error: {str(e)}"}

    def _upload_agent_metadata_core(self, folder_path: Path, overwrite: bool = False) -> Dict:
        """Core logic for uploading agent metadata - handles metadata formation internally"""
        try:
            # Load agent config from folder
            from runagent.utils.agent import get_agent_config
            from runagent.utils.gitignore import get_filtered_files
            from runagent.utils.env_vars import merge_env_vars
            
            agent_config = get_agent_config(folder_path)
            agent_id = agent_config.agent_id
            
            # Validate entrypoint files exist in the filtered file structure
            self._validate_entrypoint_files(folder_path, agent_config)
            
            # Get filtered file structure respecting .gitignore
            file_structure = get_filtered_files(folder_path)
            
            # Merge environment variables from config and .env file
            merged_env_vars = merge_env_vars(agent_config.env_vars, folder_path)
            
            # Create enhanced agent metadata
            agent_metadata = {
                "file_structure": file_structure,
                "auth_settings": agent_config.auth_settings,
                "env_vars": merged_env_vars
            }
            
            # Form the metadata payload
            config_data = {
                "agent_id": agent_id,
                "agent_metadata": agent_metadata,
                "config": agent_config.to_dict(),  # Keep original config for compatibility
                "project_id": self._get_project_id(),
                "overwrite": overwrite
            }
            
            return self._upload_agent_metadata_to_server(config_data, agent_id)
            
        except Exception as e:
            if os.getenv('DISABLE_TRY_CATCH'):
                raise
            return {"success": False, "error": f"Metadata formation failed: {str(e)}"}

    def _upload_agent_zip_file_to_server(self, zip_path: str, agent_id: str, progress: Progress, task_id) -> Dict:
        """Upload agent zip file (source code) to middleware server"""
        try:
            # Upload zip file
            file_size = os.path.getsize(zip_path)
            progress.update(task_id, completed=30, description=f"Uploading {os.path.basename(zip_path)} ({file_size:,} bytes)...")
            
            with open(zip_path, "rb") as f:
                files = {"file": (os.path.basename(zip_path), f, "application/zip")}
                data = {
                    "agent_id": agent_id,
                }

                try:
                    response = self.http.post("/agents/upload", files=files, data=data, timeout=300)
                    
                    # Complete the progress bar
                    progress.update(task_id, completed=95, description="Processing upload...")
                    result = response.json()
                    
                    # Handle new API response format
                    if result.get("success"):
                        progress.update(task_id, completed=100, description="Upload completed!")
                        time.sleep(0.5)  # Brief pause to show completion
                        
                        return {
                            "success": True,
                            "agent_id": result.get("data", {}).get("agent_id", agent_id),
                            "message": result.get("message", "Upload completed"),
                            "status": result.get("data", {}).get("status", "uploaded"),
                            "file_size": result.get("data", {}).get("file_size", file_size),
                            "file_name": result.get("data", {}).get("file_name", os.path.basename(zip_path))
                        }
                    else:
                        error_info = result.get("error", {})
                        return {
                            "success": False, 
                            "error": f"File upload failed: {error_info.get('message', 'Unknown error')}",
                            "error_code": error_info.get("code", "UNKNOWN_ERROR")
                        }

                except (ClientError, ServerError, ConnectionError) as e:
                    if os.getenv('DISABLE_TRY_CATCH'):
                        raise
                    return {"success": False, "error": f"File upload failed: {e.message}"}

        except Exception as e:
            if os.getenv('DISABLE_TRY_CATCH'):
                raise
            return {"success": False, "error": f"Upload error: {str(e)}"}

    def _upload_agent_zip_file_core(self, zip_path: str, agent_id: str) -> Dict:
        """Core logic for uploading agent zip file without progress bar"""
        try:
            # Upload zip file
            file_size = os.path.getsize(zip_path)
            
            with open(zip_path, "rb") as f:
                files = {"file": (os.path.basename(zip_path), f, "application/zip")}
                data = {
                    "agent_id": agent_id,
                }

                try:
                    response = self.http.post("/agents/upload", files=files, data=data, timeout=300)
                    result = response.json()
                    
                    # Handle new API response format
                    if result.get("success"):
                        return {
                            "success": True,
                            "agent_id": result.get("data", {}).get("agent_id", agent_id),
                            "message": result.get("message", "Upload completed"),
                            "status": result.get("data", {}).get("status", "uploaded"),
                            "file_size": result.get("data", {}).get("file_size", file_size),
                            "file_name": result.get("data", {}).get("file_name", os.path.basename(zip_path))
                        }
                    else:
                        error_info = result.get("error", {})
                        return {
                            "success": False, 
                            "error": f"File upload failed: {error_info.get('message', 'Unknown error')}",
                            "error_code": error_info.get("code", "UNKNOWN_ERROR")
                        }

                except (ClientError, ServerError, ConnectionError) as e:
                    if os.getenv('DISABLE_TRY_CATCH'):
                        raise
                    return {"success": False, "error": f"File upload failed: {e.message}"}

        except Exception as e:
            if os.getenv('DISABLE_TRY_CATCH'):
                raise
            return {"success": False, "error": f"Upload error: {str(e)}"}

    def _process_upload_result(self, result: Dict, upload_metadata: Dict) -> Dict:
        """Process upload result"""
        if result.get("success"):
            agent_id = result.get("agent_id")

            # Save to database
            try:
                from runagent.sdk.db import DBService
                db_service = DBService()
                
                # Check if agent already exists in database (from init command)
                existing_agent = db_service.get_agent(agent_id)
                
                if existing_agent:
                    # Agent exists - update it instead of adding new one
                    db_result = db_service.update_agent(
                    agent_id=agent_id,
                        framework=upload_metadata.get("framework", "unknown"),
                        remote_status="uploaded",  # Remote status for upload
                        deployed_at=datetime.now()
                )
                
                if db_result.get("success"):
                        console.print(f"🔄 [green]Agent updated in local database[/green]")
                else:
                        console.print(f"⚠️ [yellow]Warning: Could not update local database: {db_result.get('error')}[/yellow]")
                # else:
                #     # Agent doesn't exist - this shouldn't happen with new flow, but handle gracefully
                #     console.print(f"⚠️ [yellow]Warning: Agent not found in local database[/yellow]")
                #     console.print(f"💡 [cyan]This agent was not created via 'runagent init'[/cyan]")
                #     console.print(f"🔧 [blue]Consider using 'runagent config --register-agent .' to register it[/blue]")
                    
            except Exception as e:
                if os.getenv('DISABLE_TRY_CATCH'):
                    raise
                console.print(f"⚠️ [yellow]Warning: Database error: {str(e)}[/yellow]")

            # Save deployment info locally
            self._save_deployment_info(agent_id, {
                **upload_metadata,
                "agent_id": agent_id,
                "remote": True,
                "base_url": self.base_url,
            })

            console.print(Panel(
                f"✅ [bold green]Upload successful![/bold green]\n"
                f"Agent ID: [bold magenta]{agent_id}[/bold magenta]\n"
                f"Server: [blue]{self.base_url}[/blue]\n"
                f"Status: [cyan]uploaded[/cyan]",
                title="Upload Complete",
                border_style="green",
            ))

            return {
                "success": True,
                "agent_id": agent_id,
                "base_url": self.base_url,
                "message": f'Agent uploaded. Use "runagent start --id {agent_id}" to deploy, or "runagent deploy --id {agent_id}" for direct deployment.',
            }
        return result

    def upload_agent_metadata_and_zip(self, folder_path: Path, overwrite: bool = False) -> Dict:
        """Upload agent folder to middleware server with validation and progress bar"""
        try:
            if not folder_path.exists():
                return {"success": False, "error": f"Folder not found: {folder_path}"}

            console.print(f"Uploading agent from: [blue]{folder_path}[/blue]")

            # Step 1: Validate agent
            console.print(f"Validating agent...")

            is_valid, validation_details = validate_agent(folder_path)
            
            if not is_valid:
                error_msgs = validation_details.get("error_msgs", [])
                console.print(f"❌ [red]Agent validation failed:[/red]")
                for error in error_msgs:
                    console.print(f"  • {error}")
                return {
                    "success": False, 
                    "error": "Agent validation failed", 
                    "validation_details": validation_details
                }
            
            console.print(f"✅ [green]Agent validation passed[/green]")

            # Step 2: Load agent config
            try:
                agent_config = get_agent_config(folder_path)
                console.print(f"✅ [green]Agent config loaded successfully[/green]")
            except Exception as e:
                if os.getenv('DISABLE_TRY_CATCH'):
                    raise
                return {"success": False, "error": f"Failed to load agent config: {str(e)}"}

            # Step 3: Use agent ID from config (required field)
            if not agent_config.agent_id:
                    return {
                        "success": False,
                    "error": "Agent ID not found in configuration. Please run 'runagent init' first to initialize your agent."
                }
            
            agent_id = agent_config.agent_id
            console.print(f"Using Agent ID: [magenta]{agent_id}[/magenta]")

            # Step 4: Validate agent ID exists in database
            from runagent.sdk.db import DBService
            db_service = DBService()
            
            validation_result = db_service.validate_agent_id(agent_id)
            
            if not validation_result["valid"]:
                console.print(f"❌ [red]Error: {validation_result['error']}[/red]")
                suggestion_text = validation_result.get(
                    "suggestion",
                    "Use 'runagent config --register-agent .' to register the agent",
                )

                return {
                    "success": False,
                    "error": {
                        "code": "AGENT_NOT_REGISTERED",
                        "message": validation_result["error"],
                        "suggestion": suggestion_text,
                    },
                }
            else:
                existing_agent = validation_result["agent"]
                console.print(f"✅ [green]Agent ID validated in database[/green]")
                console.print(f"Current Status: [cyan]{existing_agent['status']}[/cyan]")
                console.print(f"Remote Status: [cyan]{existing_agent['remote_status']}[/cyan]")
                
                # Step 4.5: Validate agent path matches database
                path_validation_result = db_service.validate_agent_path(agent_id, str(folder_path))
                
                if not path_validation_result["valid"]:
                    if path_validation_result["code"] == "PATH_MISMATCH":
                        console.print(f"[yellow]Agent path mismatch detected![/yellow]")
                        console.print(f"Database path: [dim]{path_validation_result['details']['db_path']}[/dim]")
                        console.print(f"Current path: [dim]{path_validation_result['details']['current_path']}[/dim]")
                    else:
                        # Other path validation errors
                        console.print(f"❌ [red]Path validation error: {path_validation_result['error']}[/red]")

                    suggestion_text = path_validation_result.get(
                        "suggestion",
                        "Use 'runagent config --register-agent .' to update the agent location",
                    )

                    return {
                        "success": False,
                        "error": {
                            "code": path_validation_result.get("code", "PATH_VALIDATION_ERROR"),
                            "message": path_validation_result["error"],
                            "suggestion": suggestion_text,
                            "details": path_validation_result.get("details"),
                        },
                    }
                else:
                    console.print(f"✅ [green]Agent path validated - matches database record[/green]")

            # Step 5: Upload with progress bar
            console.print(f"Uploading to: [bold blue]{self.base_url}[/bold blue]")

            with Progress(
                SpinnerColumn(),
                TextColumn("[bold green]{task.description}[/bold green]"),
                BarColumn(bar_width=40),
                TextColumn("[bold]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
                TimeRemainingColumn(),
                console=console,
            ) as progress:
                upload_task = progress.add_task("Initializing upload...", total=100)
                
                # Step 1: Upload metadata first
                progress.update(upload_task, completed=10, description="Uploading agent metadata...")
                metadata_result = self._upload_agent_metadata_core(folder_path, overwrite)
                
                if not metadata_result.get("success"):
                    # Stop progress bar before showing user prompt
                    progress.stop()
                    
                    # Check if this is an agent exists error that needs user input
                    error_check = self._check_agent_exists_error(metadata_result, folder_path, overwrite)
                    
                    if error_check.get("code") == "RETRY_WITH_OVERWRITE":
                        # User confirmed overwrite, restart the progress bar
                        console.print(f"[cyan]Restarting upload with overwrite enabled...[/cyan]")
                        progress.stop()
                        
                        # Restart with fresh progress bar
                        with Progress(
                            SpinnerColumn(),
                            TextColumn("[bold green]{task.description}[/bold green]"),
                            BarColumn(bar_width=40),
                            TextColumn("[bold]{task.percentage:>3.0f}%"),
                            TimeElapsedColumn(),
                            TimeRemainingColumn(),
                            console=console,
                        ) as retry_progress:
                            retry_task = retry_progress.add_task("Restarting upload...", total=100)
                            
                            # Retry with overwrite=True
                            retry_progress.update(retry_task, completed=10, description="Uploading agent metadata (overwrite)...")
                            metadata_result = self._upload_agent_metadata_core(folder_path, overwrite=True)
                            
                            if not metadata_result.get("success"):
                                return {"success": False, "error": f"Metadata upload failed: {metadata_result.get('error')}"}
                            
                            retry_progress.update(retry_task, completed=20, description="Metadata uploaded successfully")
                            
                            # Continue with zip upload
                            retry_progress.update(retry_task, completed=30, description="Creating agent package...")
                            zip_path = self._create_zip_from_folder(agent_id, folder_path)
                            retry_progress.update(retry_task, completed=40, description="Package created successfully")
                            
                            # Upload zip file
                            retry_progress.update(retry_task, completed=50, description="Uploading agent files...")
                            zip_result = self._upload_agent_zip_file_to_server(zip_path, agent_id, retry_progress, retry_task)
                            
                            if not zip_result.get("success"):
                                return {"success": False, "error": f"File upload failed: {zip_result.get('error')}"}
                            
                            retry_progress.update(retry_task, completed=100, description="Upload completed successfully!")
                            
                            # Clean up zip file
                            try:
                                os.remove(zip_path)
                            except:
                                pass
                            
                            return {
                                "success": True,
                                "agent_id": agent_id,
                                "base_url": self.base_url,
                                "message": f'Agent uploaded. Use "runagent start --id {agent_id}" to deploy, or "runagent deploy --id {agent_id}" for direct deployment.',
                            }
                    
                    elif error_check.get("code") == "USER_CANCELLED":
                        return {"success": False, "error": "Upload cancelled by user"}
                    
                    else:
                        return {"success": False, "error": f"Metadata upload failed: {metadata_result.get('error')}"}
                
                progress.update(upload_task, completed=20, description="Metadata uploaded successfully")
                
                # Step 2: Create zip file
                progress.update(upload_task, completed=25, description="Creating upload package...")
                zip_path = self._create_zip_from_folder(agent_id, folder_path)
                
                console.print(f"Created upload package: [cyan]{Path(zip_path).name}[/cyan]")
                
                # Step 3: Upload zip file with progress updates
                progress.update(upload_task, completed=30, description="Uploading agent files...")
                result = self._upload_agent_zip_file_core(zip_path, agent_id)
                
                if result.get("success"):
                    progress.update(upload_task, completed=100, description="Upload completed!")
                    time.sleep(0.5)  # Brief pause to show completion

            # Clean up zip file
            os.unlink(zip_path)

            return self._process_upload_result(result, {
                "agent_id": agent_id, 
                "source_folder": str(folder_path),
                "framework": agent_config.framework.value if hasattr(agent_config.framework, 'value') else str(agent_config.framework)
            })

        except Exception as e:
            if os.getenv('DISABLE_TRY_CATCH'):
                raise
            return {"success": False, "error": f"Upload failed: {str(e)}"}

    def start_agent(self, agent_id: str, config: Dict = None) -> Dict:
        """Start/deploy an uploaded agent on the middleware server with progress bar"""
        try:
            console.print(f"Starting agent: [bold magenta]{agent_id}[/bold magenta]")

            with Progress(
                SpinnerColumn(),
                TextColumn("[bold green]{task.description}[/bold green]"),
                BarColumn(bar_width=40),
                TextColumn("[bold]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
                TimeRemainingColumn(),
                console=console,
            ) as progress:
                start_task = progress.add_task("Initializing agent startup...", total=100)
                
                # Step 1: Prepare startup
                progress.update(start_task, completed=20, description="Preparing agent deployment...")
                
                # Step 2: Start agent
                progress.update(start_task, completed=50, description="Starting agent on server...")
                result = self._start_agent_core(agent_id, config)
                
                if result.get("success"):
                    progress.update(start_task, completed=100, description="Agent started successfully!")
                    time.sleep(0.5)  # Brief pause to show completion
                else:
                    progress.update(start_task, completed=100, description="Agent startup failed!")

            return result

        except Exception as e:
            if os.getenv('DISABLE_TRY_CATCH'):
                raise
            return {"success": False, "error": f"Start agent failed: {str(e)}"}

    def _start_agent_core(self, agent_id: str, config: Dict = None) -> Dict:
        """Core logic for starting agent without progress bar"""
        try:
            payload = config or {}

            try:
                # Increased timeout to 5 minutes to allow for background processing
                response = self.http.post(f"/agents/{agent_id}/start", data=payload, timeout=300)
                result = response.json()
                return self._process_start_result(result, agent_id)

            except (ClientError, ServerError, ConnectionError) as e:
                return {"success": False, "error": f"Failed to start agent: {e.message}"}

        except Exception as e:
            if os.getenv('DISABLE_TRY_CATCH'):
                raise
            return {"success": False, "error": f"Start agent failed: {str(e)}"}

    def _process_start_result(self, result: Dict, agent_id: str) -> Dict:
        """Process start agent result"""
        if result.get("success"):
            result_data = result["data"]
            endpoint = result_data.get("endpoint")
            
            # Generate dashboard URL instead of API endpoint
            dashboard_url = f"https://app.run-agent.ai/dashboard/agents/{agent_id}"

            console.print(Panel(
                f"✅ [bold green]Agent started successfully![/bold green]\n"
                f"🆔 Agent ID: [bold magenta]{agent_id}[/bold magenta]\n"
                f"🌐 Agent URL: [link]{dashboard_url}[/link]",
                title="🚀 Deployment Complete",
                border_style="green",
            ))

            # Update local deployment info
            self._update_deployment_info(agent_id, {
                "status": "deployed",
                "endpoint": f"{self.base_url}{endpoint}",
                "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            })

            return {
                "success": True,
                "agent_id": agent_id,
                "endpoint": f"{self.base_url}{endpoint}",
                "dashboard_url": dashboard_url,
                "status": "deployed",
            }
        return result

    def deploy_agent(self, folder_path: str, metadata: Dict = None, overwrite: bool = False) -> Dict:
        """Upload and start agent in one operation with single progress bar"""
        console.print("🎯 [bold cyan]Starting full deployment (upload + start)...[/bold cyan]")

        try:
            folder_path = Path(folder_path)
            if not folder_path.exists():
                return {"success": False, "error": f"Folder not found: {folder_path}"}

            # Step 1: Validate agent
            console.print(f"🔍 Validating agent...")
            is_valid, validation_details = validate_agent(folder_path)
            
            if not is_valid:
                error_msgs = validation_details.get("error_msgs", [])
                console.print(f"❌ [red]Agent validation failed:[/red]")
                for error in error_msgs:
                    console.print(f"  • {error}")
                return {
                    "success": False, 
                    "error": "Agent validation failed", 
                    "validation_details": validation_details
                }
            
            console.print(f"✅ [green]Agent validation passed[/green]")

            # Step 2: Load agent config
            try:
                agent_config = get_agent_config(folder_path)
                console.print(f"✅ [green]Agent config loaded successfully[/green]")
            except Exception as e:
                if os.getenv('DISABLE_TRY_CATCH'):
                    raise
                return {"success": False, "error": f"Failed to load agent config: {str(e)}"}

            # Step 3: Use agent ID from config (required field)
            if not agent_config.agent_id:
                    return {
                        "success": False,
                    "error": "Agent ID not found in configuration. Please run 'runagent init' first to initialize your agent."
                }
            
            agent_id = agent_config.agent_id
            console.print(f"Using Agent ID: [magenta]{agent_id}[/magenta]")

            # Step 4: Validate agent ID exists in database
            from runagent.sdk.db import DBService
            db_service = DBService()
            
            validation_result = db_service.validate_agent_id(agent_id)
            
            if not validation_result["valid"]:
                console.print(f"❌ [red]Error: {validation_result['error']}[/red]")
                suggestion_text = validation_result.get(
                    "suggestion",
                    "Use 'runagent config --register-agent .' to register the agent",
                )

                return {
                    "success": False,
                    "error": {
                        "code": "AGENT_NOT_REGISTERED",
                        "message": validation_result["error"],
                        "suggestion": suggestion_text,
                    },
                }
            else:
                existing_agent = validation_result["agent"]
                console.print(f"✅ [green]Agent ID validated in database[/green]")
                console.print(f"Current Status: [cyan]{existing_agent['status']}[/cyan]")
                console.print(f"Remote Status: [cyan]{existing_agent['remote_status']}[/cyan]")
                
                # Step 4.5: Validate agent path matches database
                path_validation_result = db_service.validate_agent_path(agent_id, str(folder_path))
                
                if not path_validation_result["valid"]:
                    if path_validation_result["code"] == "PATH_MISMATCH":
                        console.print(f"[yellow]Agent path mismatch detected![/yellow]")
                        console.print(f"Database path: [dim]{path_validation_result['details']['db_path']}[/dim]")
                        console.print(f"Current path: [dim]{path_validation_result['details']['current_path']}[/dim]")
                    else:
                        # Other path validation errors
                        console.print(f"❌ [red]Path validation error: {path_validation_result['error']}[/red]")

                    suggestion_text = path_validation_result.get(
                        "suggestion",
                        "Use 'runagent config --register-agent .' to update the agent location",
                    )

                    return {
                        "success": False,
                        "error": {
                            "code": path_validation_result.get("code", "PATH_VALIDATION_ERROR"),
                            "message": path_validation_result["error"],
                            "suggestion": suggestion_text,
                            "details": path_validation_result.get("details"),
                        },
                    }
                else:
                    console.print(f"✅ [green]Agent path validated - matches database record[/green]")

            # Step 5: Full deployment with single progress bar
            console.print(f"🌐 Deploying to: [bold blue]{self.base_url}[/bold blue]")

            with Progress(
                SpinnerColumn(),
                TextColumn("[bold green]{task.description}[/bold green]"),
                BarColumn(bar_width=40),
                TextColumn("[bold]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
                TimeRemainingColumn(),
                console=console,
            ) as progress:
                deploy_task = progress.add_task("Initializing deployment...", total=100)
                
                # Phase 1: Upload metadata (0-20%)
                progress.update(deploy_task, completed=5, description="Uploading agent metadata...")
                metadata_result = self._upload_agent_metadata_core(folder_path, overwrite)
                
                if not metadata_result.get("success"):
                    # Stop progress bar before showing user prompt
                    progress.stop()
                    
                    # Check if this is an agent exists error that needs user input
                    error_check = self._check_agent_exists_error(metadata_result, folder_path, overwrite)
                    
                    if error_check.get("code") == "RETRY_WITH_OVERWRITE":
                        # User confirmed overwrite, restart the progress bar
                        console.print(f"[cyan]Restarting deployment with overwrite enabled...[/cyan]")
                        progress.stop()
                        
                        # Restart with fresh progress bar
                        with Progress(
                            SpinnerColumn(),
                            TextColumn("[bold green]{task.description}[/bold green]"),
                            BarColumn(bar_width=40),
                            TextColumn("[bold]{task.percentage:>3.0f}%"),
                            TimeElapsedColumn(),
                            TimeRemainingColumn(),
                            console=console,
                        ) as retry_progress:
                            retry_task = retry_progress.add_task("Restarting deployment...", total=100)
                            
                            # Retry with overwrite=True
                            retry_progress.update(retry_task, completed=5, description="Uploading agent metadata (overwrite)...")
                            metadata_result = self._upload_agent_metadata_core(folder_path, overwrite=True)
                            
                            if not metadata_result.get("success"):
                                return {"success": False, "error": f"Metadata upload failed: {metadata_result.get('error')}"}
                            
                            retry_progress.update(retry_task, completed=20, description="Metadata uploaded successfully")
                            
                            # Continue with zip upload
                            retry_progress.update(retry_task, completed=30, description="Creating agent package...")
                            zip_path = self._create_zip_from_folder(agent_id, folder_path)
                            retry_progress.update(retry_task, completed=40, description="Package created successfully")
                            
                            # Upload zip file
                            retry_progress.update(retry_task, completed=50, description="Uploading agent files...")
                            zip_result = self._upload_agent_zip_file_to_server(zip_path, agent_id, retry_progress, retry_task)
                            
                            if not zip_result.get("success"):
                                return {"success": False, "error": f"File upload failed: {zip_result.get('error')}"}
                            
                            retry_progress.update(retry_task, completed=60, description="Files uploaded successfully")
                            
                            # Clean up zip file
                            try:
                                os.remove(zip_path)
                            except:
                                pass
                            
                            # Phase 2: Start agent (60-100%)
                            retry_progress.update(retry_task, completed=70, description="Starting agent...")
                            start_result = self.start_agent(agent_id, {})
                            
                            if not start_result.get("success"):
                                return {"success": False, "error": f"Agent start failed: {start_result.get('error')}"}
                            
                            retry_progress.update(retry_task, completed=100, description="Deployment completed successfully!")
                            
                            endpoint = start_result.get("endpoint", "/api/v1/agents/run")
                            return {
                                "success": True,
                                "agent_id": agent_id,
                                "endpoint": f"{self.base_url}{endpoint}",
                                "status": "deployed",
                            }
                    
                    elif error_check.get("code") == "USER_CANCELLED":
                        return {"success": False, "error": "Deployment cancelled by user"}
                    
                    else:
                        return {"success": False, "error": f"Metadata upload failed: {metadata_result.get('error')}"}
                
                progress.update(deploy_task, completed=20, description="Metadata uploaded successfully")
                
                # Phase 2: Create and upload zip file (20-70%)
                progress.update(deploy_task, completed=25, description="Creating upload package...")
                zip_path = self._create_zip_from_folder(agent_id, folder_path)
                
                console.print(f"📦 Created upload package: [cyan]{Path(zip_path).name}[/cyan]")
                
                progress.update(deploy_task, completed=30, description="Uploading agent files...")
                upload_result = self._upload_agent_zip_file_core(zip_path, agent_id)
                
                if not upload_result.get("success"):
                    os.unlink(zip_path)  # Clean up zip file
                    return {"success": False, "error": f"File upload failed: {upload_result.get('error')}"}
                
                progress.update(deploy_task, completed=70, description="Files uploaded successfully")
                
                # Clean up zip file
                os.unlink(zip_path)
                
                # Phase 3: Start agent (70-100%)
                progress.update(deploy_task, completed=75, description="Starting agent deployment...")
                start_result = self._start_agent_core(agent_id, metadata)
                
                if start_result.get("success"):
                    progress.update(deploy_task, completed=100, description="Deployment completed successfully!")
                    time.sleep(0.5)  # Brief pause to show completion
                    
                    # Update remote_status to "deployed" for successful deployment
                    try:
                        from runagent.sdk.db import DBService
                        db_service = DBService()
                        db_service.update_agent(
                            agent_id=agent_id,
                            remote_status="deployed"
                        )
                        console.print(f"🔄 [green]Agent remote status updated to 'deployed'[/green]")
                    except Exception as e:
                        console.print(f"⚠️ [yellow]Warning: Could not update remote status: {e}[/yellow]")
                    
                    # Process upload result for database storage
                    self._process_upload_result(upload_result, {
                        "agent_id": agent_id, 
                        "source_folder": str(folder_path),
                        "framework": agent_config.framework.value if hasattr(agent_config.framework, 'value') else str(agent_config.framework)
                    })
                    
                    return {
                        "success": True,
                        "agent_id": agent_id,
                        "endpoint": start_result.get("endpoint"),
                        "status": "running",
                        "message": f'Agent fully deployed and running. Endpoint: {start_result.get("endpoint")}',
                    }
                else:
                    progress.update(deploy_task, completed=100, description="Deployment failed!")
                    return {
                        "success": False,
                        "error": f"Upload succeeded but start failed: {start_result.get('error')}",
                        "agent_id": agent_id,
                    }

        except Exception as e:
            if os.getenv('DISABLE_TRY_CATCH'):
                raise
            return {"success": False, "error": f"Deployment failed: {str(e)}"}

    def _save_deployment_info(self, agent_id: str, metadata: Dict):
        """Save deployment info for CLI reference"""
        deployments_dir = Path.cwd() / ".deployments"
        deployments_dir.mkdir(exist_ok=True)

        # Remove sensitive data
        sensitive_keys = {
            "env_vars", "environment", "secrets", "credentials", "api_keys", "tokens",
            "passwords", "private_key", "access_token", "refresh_token", "auth_token",
            "database_url", "connection_string", "secret_key",
        }

        safe_metadata = {k: v for k, v in metadata.items() if k not in sensitive_keys}
        safe_metadata.update({
            "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "client_version": "1.0"
        })

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

    def get_agent_status(self, agent_id: str) -> Dict:
        """Get status of a remote agent"""
        try:
            response = self.http.get(f"/agents/{agent_id}/status", timeout=30)
            return response.json()

        except (ClientError, ServerError, ConnectionError) as e:
            return {"success": False, "error": f"Status check failed: {e.message}"}
        except Exception as e:
            if os.getenv('DISABLE_TRY_CATCH'):
                raise
            return {"success": False, "error": f"Status check failed: {str(e)}"}

    def _get_local_deployment_info(self, agent_id: str) -> Optional[Dict]:
        """Get local deployment info for an agent"""
        deployments_dir = Path.cwd() / ".deployments"
        info_file = deployments_dir / f"{agent_id}.json"

        if info_file.exists():
            try:
                with open(info_file, "r") as f:
                    return json.load(f)
            except:
                return None
        return None


    def _clean_error_message(self, error_message: str) -> str:
        """Clean up error messages by removing redundant prefixes"""
        if not error_message:
            return "Unknown error"
        
        # Remove common redundant prefixes
        prefixes_to_remove = [
            "Server error: ",
            "Database error: ",
            "HTTP Error: ",
            "Agent execution failed: ",
        ]
        
        cleaned = error_message
        for prefix in prefixes_to_remove:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()
        
        # Remove status codes that appear at the start (e.g., "403: ")
        cleaned = re.sub(r'^\d{3}:\s*', '', cleaned)
        
        return cleaned.strip() if cleaned.strip() else error_message

    def run_agent(
        self,
        agent_id: str,
        entrypoint_tag: str,
        input_args: list = None,
        input_kwargs: dict = None,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        async_execution: bool = False,
    ) -> Dict:
        """Execute an agent with given parameters"""
        try:
            console.print(f"🤖 Executing agent: [bold magenta]{agent_id}[/bold magenta]")

            # Prepare request data according to API specification
            request_data = {
                "entrypoint_tag": entrypoint_tag,
                "input_args": input_args or [],
                "input_kwargs": input_kwargs or {},
                "timeout_seconds": timeout_seconds,
                "async_execution": async_execution
            }

            # Execute the agent
            try:
                response = self.http.post(
                    f"/agents/{agent_id}/run",
                    data=request_data,
                    timeout=timeout_seconds + 10,  # Add buffer to request timeout
                )
                result = response.json()

                if result.get("success", True):  # Assume success if not explicitly false
                    console.print("✅ [bold green]Agent execution completed![/bold green]")
                    return result
                else:
                    # Handle new error format with ErrorDetail object
                    error_info = result.get('error')
                    if isinstance(error_info, dict) and "message" in error_info:
                        # New format with ErrorDetail object - don't print here, let client handle it
                        pass
                    else:
                        # Fallback to old format for backward compatibility - don't print, let CLI handle it
                        pass
                    return result

            except AuthenticationError as e:
                # Handle authentication/permission errors (401, 403)
                error_message = self._clean_error_message(e.message)
                error_code = "AUTHENTICATION_ERROR"
                if "403" in error_message or "permission" in error_message.lower() or "access denied" in error_message.lower():
                    error_code = "PERMISSION_ERROR"
                    # Create a clean, single error message for permission errors
                    error_message = "You do not have permission to access this agent"
                return {
                    "success": False, 
                    "data": None,
                    "message": None,
                    "error": {
                        "code": error_code,
                        "message": error_message,
                        "details": None,
                        "field": None
                    },
                    "timestamp": None,
                    "request_id": None
                }
            except ServerError as e:
                # Check if server error message contains permission/403 info (even if status is 500)
                error_message = e.message
                error_code = "SERVER_ERROR"
                if ("403" in error_message or "permission" in error_message.lower() or 
                    "access denied" in error_message.lower() or "do not have permission" in error_message.lower()):
                    error_code = "PERMISSION_ERROR"
                    # Create a clean, single error message for permission errors
                    error_message = "You do not have permission to access this agent"
                else:
                    # Clean up server error messages to remove redundant prefixes
                    error_message = self._clean_error_message(error_message)
                return {
                    "success": False, 
                    "data": None,
                    "message": None,
                    "error": {
                        "code": error_code,
                        "message": error_message,
                        "details": None,
                        "field": None
                    },
                    "timestamp": None,
                    "request_id": None
                }
            except (ClientError, ConnectionError) as e:
                error_message = self._clean_error_message(e.message)
                return {
                    "success": False, 
                    "data": None,
                    "message": None,
                    "error": {
                        "code": "CONNECTION_ERROR",
                        "message": error_message,
                        "details": None,
                        "field": None
                    },
                    "timestamp": None,
                    "request_id": None
                }

        except Exception as e:
            if os.getenv('DISABLE_TRY_CATCH'):
                raise
            return {
                "success": False, 
                "data": None,
                "message": None,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Execute agent failed: {str(e)}",
                    "details": None,
                    "field": None
                },
                "timestamp": None,
                "request_id": None
            }

    def get_agent_architecture(self, agent_id: str) -> Dict:
        """Get the architecture information for a specific agent"""
        try:
            response = self.http.get(f"/agents/{agent_id}/architecture")
            payload = response.json()

            if isinstance(payload, dict) and "success" in payload:
                if payload.get("success"):
                    return payload.get("data") or {}

                error_info = payload.get("error")
                if isinstance(error_info, dict):
                    message = error_info.get("message") or payload.get("message") or "Failed to get architecture"
                else:
                    message = error_info or payload.get("message") or "Failed to get architecture"

                raise ValueError(message)

            return payload
        except Exception as e:
            if os.getenv('DISABLE_TRY_CATCH'):
                raise
            return {"success": False, "error": f"Failed to get architecture: {str(e)}"}

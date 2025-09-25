import base64
import json
import os
import tempfile
import time
import zipfile
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
        })

        if self.api_key:
            # Support both JWT tokens and API keys
            self.session.headers.update({
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": "RunAgent-CLI/1.0"
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
                elif "message" in error_data:
                    error_message = error_data["message"]
                elif "error" in error_data:
                    error_message = error_data["error"]
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
            response = self.session.request(
                method=method.upper(),
                url=url,
                params=params,
                json=data if data and not files else None,
                data=None if data and not files else data,
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
        self.http = HttpHandler(
            api_key=self.api_key,  # Use API key directly - middleware handles conversion
            base_url=self.base_url
        )

        # Cache for limits to avoid repeated API calls
        self._limits_cache = None
        self._cache_expiry = None

    def close(self):
        """Close HTTP resources"""
        self.http.close()

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
            return self._get_error_response("generic", str(e))

    def clear_limits_cache(self):
        """Clear the cached limits to force refresh"""
        self._limits_cache = None
        self._cache_expiry = None
        console.print("🔄 [dim]Limits cache cleared[/dim]")

    def _create_zip_from_folder(self, agent_id: str, folder_path: Path) -> str:
        """Create a zip file from the agent folder"""
        temp_dir = tempfile.gettempdir()
        zip_path = os.path.join(temp_dir, f"agent_{agent_id[:8]}.zip")

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
            for file_path in folder_path.rglob("*"):
                if file_path.is_file() and not file_path.name.startswith("."):
                    # Skip unnecessary files
                    if file_path.name in ["__pycache__", ".DS_Store", "Thumbs.db"]:
                        continue
                    if file_path.suffix in [".pyc", ".pyo", ".log"]:
                        continue

                    arcname = file_path.relative_to(folder_path)
                    zipf.write(file_path, arcname)

        return zip_path

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
                return {"success": False, "error": f"Metadata upload failed: {e.message}"}

        except Exception as e:
            return {"success": False, "error": f"Metadata upload error: {str(e)}"}

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
                    return {"success": False, "error": f"File upload failed: {e.message}"}

        except Exception as e:
            return {"success": False, "error": f"Upload error: {str(e)}"}

    def _process_upload_result(self, result: Dict, upload_metadata: Dict) -> Dict:
        """Process upload result"""
        if result.get("success"):
            agent_id = result.get("agent_id")

            # Save to database
            try:
                from runagent.sdk.db import DBService
                db_service = DBService()
                
                # Add remote agent to database
                db_result = db_service.add_remote_agent(
                    agent_id=agent_id,
                    agent_path="",  # Remote agent, no local path
                    framework="unknown",  # Will be updated when agent is started
                    fingerprint=upload_metadata.get("fingerprint", ""),
                    status="uploaded"
                )
                
                if db_result.get("success"):
                    console.print(f"💾 [green]Agent saved to local database[/green]")
                else:
                    console.print(f"⚠️ [yellow]Warning: Could not save to local database: {db_result.get('error')}[/yellow]")
                    
            except Exception as e:
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
                f"🆔 Agent ID: [bold magenta]{agent_id}[/bold magenta]\n"
                f"🌐 Server: [blue]{self.base_url}[/blue]\n"
                f"🔍 Fingerprint: [dim]{upload_metadata.get('fingerprint', 'N/A')[:16]}...[/dim]",
                title="📤 Upload Complete",
                border_style="green",
            ))

            return {
                "success": True,
                "agent_id": agent_id,
                "base_url": self.base_url,
                "message": f'Agent uploaded. Use "runagent start --id {agent_id}" to deploy, or "runagent deploy --id {agent_id}" for direct deployment.',
            }
        return result

    def upload_agent(self, folder_path: str) -> Dict:
        """Upload agent folder to middleware server with validation"""
        try:
            folder_path = Path(folder_path)

            if not folder_path.exists():
                return {"success": False, "error": f"Folder not found: {folder_path}"}

            console.print(f"📤 Uploading agent from: [blue]{folder_path}[/blue]")

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
                console.print(f"📋 [green]Agent config loaded successfully[/green]")
            except Exception as e:
                return {"success": False, "error": f"Failed to load agent config: {str(e)}"}

            # Step 3: Generate agent fingerprint for duplicate detection
            fingerprint = generate_agent_fingerprint(folder_path)
            console.print(f"🔍 Agent fingerprint: [dim]{fingerprint[:16]}...[/dim]")

            # Step 4: Check for existing agents (both by fingerprint and by path)
            from runagent.sdk.db import DBService
            db_service = DBService()
            
            # Check for exact fingerprint match (identical content)
            existing_agent_by_fingerprint = db_service.get_agent_by_fingerprint(fingerprint)
            
            # Check for existing agent by path (same folder, potentially modified)
            existing_agent_by_path = db_service.get_agent_by_path(str(folder_path))
            
            if existing_agent_by_fingerprint:
                # Identical content detected
                existing_agent = existing_agent_by_fingerprint
                console.print(f"⚠️ [yellow]Agent with identical content already exists![/yellow]")
                console.print(f"🆔 Existing Agent ID: [magenta]{existing_agent['agent_id']}[/magenta]")
                console.print(f"📊 Status: [cyan]{existing_agent['status']}[/cyan]")
                console.print(f"📍 Type: [cyan]{'Local' if existing_agent['is_local'] else 'Remote'}[/cyan]")
                
                # Ask user if they want to overwrite identical content
                from rich.prompt import Confirm
                overwrite = Confirm.ask("Do you want to overwrite the existing agent?", default=False)
                
                if not overwrite:
                    return {
                        "success": False,
                        "error": "Upload cancelled by user",
                        "code": "USER_CANCELLED",
                        "existing_agent": existing_agent
                    }
                
                # Use existing agent ID for overwrite
                agent_id = existing_agent['agent_id']
                console.print(f"🔄 [yellow]Overwriting existing agent: {agent_id}[/yellow]")
                
            elif existing_agent_by_path:
                # Modified content detected (same folder, different fingerprint)
                existing_agent = existing_agent_by_path
                console.print(f"⚠️ [yellow]Agent content has changed![/yellow]")
                console.print(f"🆔 Existing Agent ID: [magenta]{existing_agent['agent_id']}[/magenta]")
                console.print(f"📊 Status: [cyan]{existing_agent['status']}[/cyan]")
                console.print(f"📍 Type: [cyan]{'Local' if existing_agent['is_local'] else 'Remote'}[/cyan]")
                console.print(f"🔍 Content fingerprint changed (modified files detected)")
                
                # Show enhanced options for modified content
                from rich.prompt import Prompt
                choice = Prompt.ask(
                    "What would you like to do?",
                    choices=["overwrite", "new", "cancel"],
                    default="new"
                )
                
                if choice == "overwrite":
                    # Feature not available yet - show message and fallback
                    console.print(f"\n🚧 [yellow]Overwrite functionality is not yet available.[/yellow]")
                    console.print(f"💡 [cyan]This feature is coming soon! For now, we'll create a new agent.[/cyan]")
                    console.print(f"📢 [blue]Contact us on Discord if you need this feature sooner.[/blue]")
                    console.print(f"🔗 [link]https://discord.gg/Q9P9AdHVHz[/link]")
                    
                    # Fallback to new agent creation
                    agent_id = generate_agent_id()
                    console.print(f"🆔 New Agent ID: [magenta]{agent_id}[/magenta]")
                    
                elif choice == "new":
                    # Create new agent with new ID
                    agent_id = generate_agent_id()
                    console.print(f"🆔 New Agent ID: [magenta]{agent_id}[/magenta]")
                    
                else:  # cancel
                    return {
                        "success": False,
                        "error": "Upload cancelled by user",
                        "code": "USER_CANCELLED",
                        "existing_agent": existing_agent
                    }
            else:
                # No existing agent found - create new one
                agent_id = generate_agent_id()
                console.print(f"🆔 New Agent ID: [magenta]{agent_id}[/magenta]")

            # Step 5: Create zip file and upload in parallel
            console.print(f"🌐 Uploading to: [bold blue]{self.base_url}[/bold blue]")

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
                config_data = {
                    "id": agent_id,
                    "config": agent_config.to_dict()
                }

                metadata_result = self._upload_agent_metadata_to_server(config_data, agent_id)
                
                if not metadata_result.get("success"):
                    return {"success": False, "error": f"Metadata upload failed: {metadata_result.get('error')}"}
                
                progress.update(upload_task, completed=20, description="Metadata uploaded successfully")
                
                # Step 2: Create zip file
                progress.update(upload_task, completed=25, description="Creating upload package...")
                zip_path = self._create_zip_from_folder(agent_id, folder_path)
                
                console.print(f"📦 Created upload package: [cyan]{Path(zip_path).name}[/cyan]")
                
                # Step 3: Upload zip file
                result = self._upload_agent_zip_file_to_server(zip_path, agent_id, progress, upload_task)

            # Clean up zip file
            os.unlink(zip_path)

            return self._process_upload_result(result, {
                "agent_id": agent_id, 
                "fingerprint": fingerprint,
                "source_folder": str(folder_path)
            })

        except Exception as e:
            return {"success": False, "error": f"Upload failed: {str(e)}"}

    def start_agent(self, agent_id: str, config: Dict = None) -> Dict:
        """Start/deploy an uploaded agent on the middleware server"""
        try:
            console.print(f"Starting agent: [bold magenta]{agent_id}[/bold magenta]")

            payload = config or {}

            try:
                response = self.http.post(f"/agents/{agent_id}/start", data=payload, timeout=60)
                result = response.json()
                return self._process_start_result(result, agent_id)

            except (ClientError, ServerError, ConnectionError) as e:
                return {"success": False, "error": f"Failed to start agent: {e.message}"}

        except Exception as e:
            return {"success": False, "error": f"Start agent failed: {str(e)}"}

    def _process_start_result(self, result: Dict, agent_id: str) -> Dict:
        """Process start agent result"""
        if result.get("success"):
            result_data = result["data"]
            endpoint = result_data.get("endpoint")

            console.print(Panel(
                f"✅ [bold green]Agent started successfully![/bold green]\n"
                f"🆔 Agent ID: [bold magenta]{agent_id}[/bold magenta]\n"
                f"🌐 Endpoint: [link]{self.base_url}{endpoint}[/link]",
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
                "status": "deployed",
            }
        return result

    def deploy_agent(self, folder_path: str, metadata: Dict = None) -> Dict:
        """Upload and start agent in one operation"""
        console.print("🎯 [bold cyan]Starting full deployment (upload + start)...[/bold cyan]")

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

# runagent/sdk/rest_client.py - FIXED RestClient initialization

# class RestClient:
#     """Client for remote server deployment via REST API"""

#     def __init__(
#         self,
#         base_url: Optional[str] = None,
#         api_key: Optional[str] = None,
#         api_prefix: Optional[str] = "/api/v1",
#     ):
#         """Initialize REST client for middleware server"""
#         self.api_key = api_key or Config.get_api_key()
        
#         # Fix base URL construction
#         if base_url:
#             self.base_url = base_url.rstrip("/") + api_prefix
#         else:
#             raw_base_url = Config.get_base_url()
#             self.base_url = raw_base_url.rstrip("/") + api_prefix

#         # Initialize HTTP handler directly with API key
#         # The middleware auth system will handle JWT conversion automatically
#         self.http = HttpHandler(
#             api_key=self.api_key,  # Use API key directly - middleware handles conversion
#             base_url=self.base_url
#         )

#         # Cache for limits to avoid repeated API calls
#         self._limits_cache = None
#         self._cache_expiry = None


#     def validate_api_connection(self) -> Dict[str, Any]:
#         """Validate API connection and authentication - SIMPLIFIED"""
#         try:
#             # Test basic connectivity first
#             try:
#                 health_response = self.http.get("/health", timeout=10, handle_errors=False)
                
#                 if health_response.status_code != 200:
#                     return {
#                         "success": False,
#                         "api_connected": False,
#                         "error": f"Health check failed: {health_response.status_code}",
#                     }

#             except Exception as e:
#                 return {
#                     "success": False,
#                     "api_connected": False,
#                     "error": f"Cannot connect to middleware: {str(e)}",
#                 }

#             # Test authentication if API key provided
#             if self.api_key:
#                 try:
#                     # Try to get user profile which requires authentication
#                     auth_response = self.http.get("/users/profile", timeout=10)
                    
#                     if auth_response.status_code == 200:
#                         profile_data = auth_response.json()
#                         auth_data = profile_data.get("auth_data", {})
                        
#                         return {
#                             "success": True,
#                             "api_connected": True,
#                             "api_authenticated": True,
#                             "user_info": {
#                                 "email": auth_data.get("email"),
#                                 "id": auth_data.get("id")
#                             },
#                             "base_url": self.base_url,
#                         }
#                     else:
#                         error_data = auth_response.json() if hasattr(auth_response, 'json') else {}
#                         return {
#                             "success": False,
#                             "api_connected": True,
#                             "api_authenticated": False,
#                             "error": error_data.get("detail", f"Authentication failed: {auth_response.status_code}"),
#                             "base_url": self.base_url,
#                         }
                        
#                 except AuthenticationError as e:
#                     return {
#                         "success": False,
#                         "api_connected": True,
#                         "api_authenticated": False,
#                         "error": f"Invalid API key: {e.message}",
#                         "base_url": self.base_url,
#                     }
#                 except Exception as e:
#                     return {
#                         "success": False,
#                         "api_connected": True,
#                         "api_authenticated": False,
#                         "error": f"Authentication test failed: {str(e)}",
#                         "base_url": self.base_url,
#                     }
#             else:
#                 return {
#                     "success": True,
#                     "api_connected": True,
#                     "api_authenticated": False,
#                     "base_url": self.base_url,
#                     "message": "No API key provided",
#                 }

#         except Exception as e:
#             return {
#                 "success": False,
#                 "api_connected": False,
#                 "error": f"Connection validation failed: {str(e)}",
#             }



#     def _make_request(self, method: str, endpoint: str, **kwargs) -> dict:
#         """
#         Make authenticated HTTP request to middleware API (for middleware sync)
        
#         Args:
#             method: HTTP method (GET, POST, PUT, DELETE)
#             endpoint: API endpoint path
#             **kwargs: Additional arguments for requests
            
#         Returns:
#             Response data as dict
#         """
#         if not self.api_key:
#             raise Exception("API key not configured")
        
#         try:
#             # Convert 'json' kwarg to 'data' to match HttpHandler interface
#             if 'json' in kwargs:
#                 kwargs['data'] = kwargs.pop('json')
            
#             # Use the existing HTTP handler for consistency
#             if method.upper() == "GET":
#                 response = self.http.get(endpoint, **kwargs)
#             elif method.upper() == "POST":
#                 response = self.http.post(endpoint, **kwargs)
#             elif method.upper() == "PUT":
#                 response = self.http.put(endpoint, **kwargs)
#             elif method.upper() == "DELETE":
#                 response = self.http.delete(endpoint, **kwargs)
#             elif method.upper() == "PATCH":
#                 response = self.http.patch(endpoint, **kwargs)
#             else:
#                 raise ValueError(f"Unsupported HTTP method: {method}")
            
#             # Handle response - check if it's already a dict or a Response object
#             if hasattr(response, 'json') and callable(response.json):
#                 return response.json()
#             elif isinstance(response, dict):
#                 return response
#             else:
#                 # Fallback: try to get json content
#                 try:
#                     return response.json()
#                 except:
#                     return {"success": False, "error": "Invalid response format"}
                
#         except (ClientError, ServerError, ConnectionError, AuthenticationError, ValidationError) as e:
#             raise Exception(f"API request failed: {e.message}")
#         except Exception as e:
#             raise Exception(f"Request error: {e}")

#     def run_agent(
#         self,
#         agent_id: str,
#         entrypoint_tag: str,
#         input_args: list = None,
#         input_kwargs: dict = None,
#         execution_type: str = "generic",
#     ) -> Dict:
#         """Execute an agent with given parameters"""
#         try:
#             console.print(f"🤖 Executing agent: [bold magenta]{agent_id}[/bold magenta]")

#             # Prepare request data
#             request_data = {
#                 "input_data": {"input_args": input_args, "input_kwargs": input_kwargs}
#             }

#             # Execute the agent
#             try:
#                 response = self.http.post(
#                     f"/agents/{agent_id}/execute/{entrypoint_tag}",
#                     data=request_data,
#                     timeout=120,  # Longer timeout for agent execution
#                 )
#                 result = response.json()

#                 if result.get("success", True):  # Assume success if not explicitly false
#                     console.print("✅ [bold green]Agent execution completed![/bold green]")
#                     return result
#                 else:
#                     console.print(f"❌ [bold red]Agent execution failed: {result.get('error', 'Unknown error')}[/bold red]")
#                     return result

#             except (ClientError, ServerError, ConnectionError) as e:
#                 return {"success": False, "error": f"Agent execution failed: {e.message}"}

#         except Exception as e:
#             return {"success": False, "error": f"Execute agent failed: {str(e)}"}

#     def get_agent_architecture(self, agent_id: str) -> Dict:
#         """Get the architecture information for a specific agent"""
#         try:
#             response = self.http.get(f"/agents/{agent_id}/architecture")
#             return response.json()
#         except Exception as e:
#             return {"success": False, "error": f"Failed to get architecture: {str(e)}"}


#     def sync_local_agent(self, agent_data: Dict[str, Any]) -> Dict[str, Any]:
#         """Sync local agent to middleware"""
#         try:
#             response = self.http.post("/local-agents", data=agent_data, timeout=30)
#             return response.json()
#         except Exception as e:
#             return {"success": False, "error": str(e)}

#     def create_local_invocation(self, invocation_data: Dict[str, Any]) -> Dict[str, Any]:
#         """Create local invocation in middleware"""
#         try:
#             response = self.http.post("/local-invocations", data=invocation_data, timeout=30)
#             return response.json()
#         except Exception as e:
#             return {"success": False, "error": str(e)}

#     def update_local_invocation(self, invocation_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
#         """Update local invocation in middleware"""
#         try:
#             response = self.http.put(f"/local-invocations/{invocation_id}", data=update_data, timeout=30)
#             return response.json()
#         except Exception as e:
#             return {"success": False, "error": str(e)}

#     def _get_jwt_token_from_api_key(self) -> Optional[str]:
#         """Convert API key to JWT token using middleware auth endpoint"""
#         if not self.api_key:
#             return None
            
#         try:
#             # Check if API key is already a JWT token
#             if self.api_key.startswith('eyJ'):  # JWT tokens start with 'eyJ'
#                 return self.api_key
            
#             # Create a temporary HTTP handler without auth for this request
#             temp_http = HttpHandler(base_url=self.base_url)
            
#             # The middleware auth.py shows that API keys are validated and converted to JWT
#             # We'll use the validation endpoint which should return a JWT
#             try:
#                 response = temp_http.post("/tokens/validate", data={"token": self.api_key}, timeout=10)
                
#                 if response.status_code == 200:
#                     validation_result = response.json()
#                     if validation_result.get("valid"):

#                         return self.api_key
#                 else:
#                     console.print(f"[red]API key validation failed: {response.status_code}[/red]")
#                     return None
                    
#             except Exception as e:
#                 console.print(f"[yellow]Could not validate API key: {e}[/yellow]")
#                 # Return API key anyway - let middleware handle the conversion
#                 return self.api_key
                
#         except Exception as e:
#             console.print(f"[red]Error processing API key: {e}[/red]")
#             return None

#     def validate_api_connection(self) -> Dict[str, Any]:
#         """Validate API connection and authentication - UPDATED"""
#         try:
#             # Test basic connectivity first
#             try:
#                 health_response = self.http.get("/health", timeout=10, handle_errors=False)
                
#                 if health_response.status_code != 200:
#                     return {
#                         "success": False,
#                         "api_connected": False,
#                         "error": f"Health check failed: {health_response.status_code}",
#                     }

#             except Exception as e:
#                 return {
#                     "success": False,
#                     "api_connected": False,
#                     "error": f"Cannot connect to middleware: {str(e)}",
#                 }

#             # Test authentication if API key provided
#             if self.api_key:
#                 try:
#                     # Try to get user profile which requires authentication
#                     auth_response = self.http.get("/users/profile", timeout=10)
                    
#                     if auth_response.status_code == 200:
#                         profile_data = auth_response.json()
#                         user_info = profile_data.get("auth_data", {})
                        
#                         return {
#                             "success": True,
#                             "api_connected": True,
#                             "api_authenticated": True,
#                             "user_info": {
#                                 "email": user_info.get("email"),
#                                 "id": user_info.get("id")
#                             },
#                             "base_url": self.base_url,
#                         }
#                     else:
#                         error_data = auth_response.json() if hasattr(auth_response, 'json') else {}
#                         return {
#                             "success": False,
#                             "api_connected": True,
#                             "api_authenticated": False,
#                             "error": error_data.get("detail", f"Authentication failed: {auth_response.status_code}"),
#                             "base_url": self.base_url,
#                         }
                        
#                 except AuthenticationError as e:
#                     return {
#                         "success": False,
#                         "api_connected": True,
#                         "api_authenticated": False,
#                         "error": f"Invalid API key: {e.message}",
#                         "base_url": self.base_url,
#                     }
#                 except Exception as e:
#                     return {
#                         "success": False,
#                         "api_connected": True,
#                         "api_authenticated": False,
#                         "error": f"Authentication test failed: {str(e)}",
#                         "base_url": self.base_url,
#                     }
#             else:
#                 return {
#                     "success": True,
#                     "api_connected": True,
#                     "api_authenticated": False,
#                     "base_url": self.base_url,
#                     "message": "No API key provided",
#                 }

#         except Exception as e:
#             return {
#                 "success": False,
#                 "api_connected": False,
#                 "error": f"Connection validation failed: {str(e)}",
#             }
#     def __del__(self):
#         """Cleanup on deletion"""
#         try:
#             self.close()
#         except:
#             pass

#     def debug_connection(self) -> Dict:
#         """Debug middleware connection"""
#         try:
#             print(f"🔍 Debug: Testing connection to {self.base_url}")
            
#             # Test health endpoint
#             try:
#                 response = self.http.get("health", timeout=5)
#                 print(f"✅ Health check successful: {response}")
#                 health_data = response.json() if hasattr(response, 'json') else response
                
#                 # Test auth validation if API key exists
#                 if self.api_key:
#                     try:
#                         auth_response = self.http.get("validate", timeout=5)
#                         print(f"✅ Auth validation successful: {auth_response}")
#                         auth_data = auth_response.json() if hasattr(auth_response, 'json') else auth_response
                        
#                         return {
#                             "success": True,
#                             "health": health_data,
#                             "auth": auth_data,
#                             "base_url": self.base_url
#                         }
#                     except Exception as auth_e:
#                         print(f"❌ Auth validation failed: {auth_e}")
#                         return {
#                             "success": False,
#                             "health": health_data,
#                             "auth_error": str(auth_e),
#                             "base_url": self.base_url
#                         }
#                 else:
#                     return {
#                         "success": True,
#                         "health": health_data,
#                         "auth": "No API key provided",
#                         "base_url": self.base_url
#                     }
                    
#             except Exception as health_e:
#                 print(f"❌ Health check failed: {health_e}")
#                 return {
#                     "success": False,
#                     "health_error": str(health_e),
#                     "base_url": self.base_url
#                 }
                
#         except Exception as e:
#             print(f"❌ Connection debug failed: {e}")
#             return {
#                 "success": False,
#                 "error": str(e),
#                 "base_url": self.base_url
#             }
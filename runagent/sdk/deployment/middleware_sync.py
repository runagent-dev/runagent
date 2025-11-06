import json
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from rich.console import Console
from runagent.sdk.rest_client import RestClient
from runagent.sdk.config import SDKConfig
from runagent.utils.logging_utils import is_verbose_logging_enabled

console = Console()

_global_middleware_sync = None


class MiddlewareSyncService:
    """Middleware sync service - UPDATED for simplified ID structure"""
    
    def __init__(self, config):
        self.config = config
        self.rest_client = None
        
        # Check if we have a valid API key
        self.api_key = getattr(config, 'api_key', None)
        if not self.api_key:
            console.print("[dim]No API key configured - middleware sync disabled[/dim]")
            self.sync_enabled = False
            self.enabled = False
            return
        
        # Initialize RestClient if we have an API key
        try:
            self.rest_client = RestClient(
                base_url=config.base_url,
                api_key=self.api_key
            )
            
            # If we have user info, authentication was successful, enable sync
            if hasattr(config, '_config') and config._config.get("user_email") and config._config.get("user_id"):
                console.print("[dim]Using cached authentication - middleware sync enabled[/dim]")
                self.sync_enabled = True
                self.enabled = True
            else:
                console.print("[dim]No cached authentication - middleware sync disabled[/dim]")
                self.sync_enabled = False
                self.enabled = False
                
        except Exception as e:
            console.print(f"[red]Could not initialize middleware sync: {e}[/red]")
            self.sync_enabled = False
            self.enabled = False
            self.rest_client = None

    def is_sync_enabled(self) -> bool:
        """Public method to check if sync is enabled"""
        return getattr(self, 'sync_enabled', False)
    
    async def sync_agent_startup(self, agent_id: str, agent_data: Dict[str, Any]) -> bool:
        """Sync agent data when local server starts"""
        if not self.is_sync_enabled():
            console.print("[dim]Middleware sync disabled - agent will run in local-only mode[/dim]")
            return False
            
        try:
            verbose = is_verbose_logging_enabled()
            if verbose:
                console.print(f"[cyan]Syncing agent {agent_id[:8]}... to middleware...[/cyan]")
            
            # Load full agent config from agent path
            from pathlib import Path
            from runagent.utils.agent import get_agent_config
            from runagent.utils.gitignore import get_filtered_files
            
            agent_path = Path(agent_data.get("path", ""))
            if not agent_path.exists():
                console.print(f"[red]❌ Agent path not found: {agent_path}[/red]")
                return False
            
            # Get agent config
            agent_config = get_agent_config(agent_path)
            
            # Get filtered file structure respecting .gitignore
            file_structure = get_filtered_files(agent_path)
            
            # Create agent metadata for local sync
            # Note: env_vars are NOT included for local sync since the agent runs locally
            # with its own environment variables already configured
            agent_metadata = {
                "file_structure": file_structure,
                "auth_settings": agent_config.auth_settings if hasattr(agent_config, 'auth_settings') else {"type": "none"}
            }
            
            # Get active project ID from user config (same as RestClient._get_project_id)
            # This ensures we use the user's currently active/selected project
            project_id = "default"
            try:
                from runagent.utils.config import Config
                user_config = Config.get_user_config()
                project_id = user_config.get("active_project_id", "default")
                if not project_id:
                    project_id = "default"
            except Exception as e:
                console.print(f"[yellow]⚠️ Could not get active project ID: {e}, using default[/yellow]")
                project_id = "default"
            
            # Build new payload structure matching updated API
            sync_data = {
                "agent_id": agent_id,  # Changed from local_agent_id
                "config": agent_config.to_dict(),  # Full config with agent_name, framework, version
                "agent_metadata": agent_metadata,
                "project_id": project_id
            }
            
            verbose = is_verbose_logging_enabled()
            if verbose:
                console.print(f"[dim]Sending POST to /local-agents/create[/dim]")
                console.print(f"[dim]Full URL: {self.rest_client.base_url}/local-agents/create[/dim]")
            
            # Make direct HTTP call instead of using _make_async_request
            try:
                response = self.rest_client.http.post("/local-agents/create", data=sync_data, timeout=30)
                result = response.json() if hasattr(response, 'json') else response
                
                if verbose:
                    console.print(f"[cyan]Response status: {response.status_code if hasattr(response, 'status_code') else 'N/A'}[/cyan]")
                    console.print(f"[cyan]Response: {result}[/cyan]")
                
                if result.get("success"):
                    console.print("[green]✅ Agent synced successfully[/green]")
                    return True
                else:
                    error_msg = result.get("error", "Unknown error")
                    console.print(f"[yellow]⚠️ Agent sync failed: {error_msg}[/yellow]")
                    return False
                    
            except Exception as e:
                console.print(f"[red]❌ HTTP request failed: {str(e)}[/red]")
                return False
                
        except Exception as e:
            console.print(f"[red]❌ Agent sync error: {str(e)}[/red]")
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
            return False


    # async def sync_invocation_start(self, invocation_data: Dict[str, Any]) -> Optional[str]:
    #     """Sync invocation start to middleware"""
    #     if not self.is_sync_enabled():
    #         return None
            
    #     try:
    #         verbose = is_verbose_logging_enabled()
    #         if not verbose:
    #             # Minimal log in non-verbose mode
    #             pass
    #         else:
    #             console.print(f"[cyan]📡 Syncing invocation start...[/cyan]")
            
    #         sync_payload = {
    #             "agent_id": invocation_data.get("agent_id"),
    #             "local_execution_id": invocation_data.get("local_execution_id"),
    #             "input_data": invocation_data.get("input_data", {}),
    #             "entrypoint_tag": invocation_data.get("entrypoint_tag", ""),
    #             "sdk_type": invocation_data.get("sdk_type", "local_server"),
    #             "client_info": invocation_data.get("client_info", {})
    #         }
            
    #         verbose = is_verbose_logging_enabled()
    #         if verbose:
    #             console.print(f"[dim]POST to /local-agents/invocations[/dim]")
            
    #         response = self.rest_client.http.post("/local-agents/invocations", data=sync_payload, timeout=30)
    #         result = response.json() if hasattr(response, 'json') else response
            
    #         if verbose:
    #             console.print(f"[cyan]Response: {result}[/cyan]")
            
    #         if result.get("success"):
    #             execution_id = result.get("data", {}).get("id")
    #             if execution_id:
    #                 console.print(f"[green]✅ Invocation synced: {execution_id[:8]}...[/green]")
    #                 return execution_id
            
    #         return None
            
    #     except Exception as e:
    #         console.print(f"[red]❌ Invocation sync error: {str(e)}[/red]")
    #         return None


    async def sync_execution(self, agent_id: str, execution_data: Dict[str, Any]) -> bool:
        """
        Sync complete execution to middleware using new unified endpoint.
        
        Args:
            agent_id: The agent ID
            execution_data: Complete execution data including:
                - local_execution_id: Local invocation ID
                - entrypoint_tag: Entrypoint tag
                - status: "completed" or "failed"
                - started_at: ISO timestamp
                - completed_at: ISO timestamp
                - input_data: Input data dict
                - result_data: Result data (if success)
                - error_message: Error message (if failed)
                - execution_metadata: Metadata dict with sdk_type, client_info, runtime_seconds, error_code
        """
        if not self.is_sync_enabled():
            return False
            
        try:
            verbose = is_verbose_logging_enabled()
            if verbose:
                console.print(f"[cyan]📡 Syncing execution to middleware...[/cyan]")
            
            # Prepare payload according to new API spec
            payload = {
                "local_execution_id": execution_data.get("local_execution_id"),
                "entrypoint_tag": execution_data.get("entrypoint_tag"),
                "status": execution_data.get("status"),  # "completed" or "failed"
                "started_at": execution_data.get("started_at"),
                "completed_at": execution_data.get("completed_at"),
                "input_data": execution_data.get("input_data", {}),
                "execution_metadata": execution_data.get("execution_metadata", {})
            }
            
            # Add result_data for successful executions
            if execution_data.get("status") == "completed" and execution_data.get("result_data"):
                payload["result_data"] = execution_data.get("result_data")
            
            # Add error_message for failed executions
            if execution_data.get("status") == "failed" and execution_data.get("error_message"):
                payload["error_message"] = execution_data.get("error_message")
            
            if verbose:
                console.print(f"[dim]POST to /local-agents/{agent_id}/execution[/dim]")
            
            # Note: RestClient already adds /api/v1 prefix to base_url, so we don't include it here
            response = self.rest_client.http.post(
                f"/local-agents/{agent_id}/execution",
                data=payload,
                timeout=30
            )
            result = response.json() if hasattr(response, 'json') else response
            
            if verbose:
                console.print(f"[cyan]Response: {result}[/cyan]")
            
            if result.get("success"):
                console.print(f"[green]✅ Execution synced to middleware[/green]")
                return True
            
            return False
            
        except Exception as e:
            console.print(f"[red]❌ Execution sync error: {str(e)}[/red]")
            if verbose:
                import traceback
                console.print(f"[dim]{traceback.format_exc()}[/dim]")
            return False


    # async def sync_invocation_complete(self, execution_id: str, completion_data: Dict[str, Any]) -> bool:
    #     """DEPRECATED: Use sync_execution instead. Sync invocation completion to middleware"""
    #     if not self.is_sync_enabled() or not execution_id:
    #         return False
            
    #     try:
    #         verbose = is_verbose_logging_enabled()
    #         if not verbose:
    #             # Minimal log in non-verbose mode  
    #             pass
    #         else:
    #             console.print(f"[cyan]📡 Syncing completion: {execution_id[:8]}...[/cyan]")
            
    #         update_payload = {}
            
    #         if completion_data.get("output_data"):
    #             update_payload["output_data"] = completion_data["output_data"]
            
    #         if completion_data.get("error_detail"):
    #             update_payload["error_detail"] = completion_data["error_detail"]
            
    #         if completion_data.get("execution_time_ms"):
    #             update_payload["execution_time_ms"] = completion_data["execution_time_ms"]
            
    #         if completion_data.get("status"):
    #             update_payload["status"] = completion_data["status"]
            
    #         verbose = is_verbose_logging_enabled()
    #         if verbose:
    #             console.print(f"[dim]PUT to /local-agents/invocations/{execution_id[:8]}...[/dim]")
            
    #         response = self.rest_client.http.put(f"/local-agents/invocations/{execution_id}", data=update_payload, timeout=30)
    #         result = response.json() if hasattr(response, 'json') else response
            
    #         if verbose:
    #             console.print(f"[cyan]Response: {result}[/cyan]")
            
    #         if result.get("success"):
    #             console.print(f"[green]✅ Completion synced[/green]")
    #             return True
            
    #         return False
            
    #     except Exception as e:
    #         console.print(f"[red]❌ Completion sync error: {str(e)}[/red]")
    #         return False

    def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status with detailed info"""
        return {
            "sync_enabled": getattr(self, 'sync_enabled', False),
            "api_configured": bool(getattr(self, 'api_key', None)),
            "authenticated": bool(getattr(self.config, '_config', {}).get("user_email") and getattr(self.config, '_config', {}).get("user_id")),
            "base_url": getattr(self.config, 'base_url', None),
            "middleware_available": self._test_middleware_connection() if getattr(self, 'rest_client', None) else False
        }

    def test_connection(self) -> Dict[str, Any]:
        """Test middleware connection and return detailed result"""
        try:
            result = self._test_middleware_connection()
            
            return {
                "success": result,
                "error": None if result else "Connection failed"
            }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _test_middleware_connection(self) -> bool:
        """Test if middleware is reachable"""
        if not getattr(self, 'rest_client', None):
            return False
            
        try:
            response = self.rest_client.http.get("/health", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def _test_supabase_authentication(self) -> bool:
        """Test Supabase authentication"""
        if not getattr(self, 'rest_client', None):
            return False
            
        try:
            response = self.rest_client.http.get("/users/profile", timeout=10)
            return response.status_code == 200
        except Exception:
            return False

    async def _make_async_request(self, method: str, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make async HTTP request to middleware"""
        if not getattr(self, 'rest_client', None) or not self.is_sync_enabled():
            return {"success": False, "error": "Middleware sync not available"}
            
        try:
            if method == "POST":
                response = await asyncio.to_thread(
                    self.rest_client.http.post, 
                    endpoint, 
                    data=data, 
                    timeout=30
                )
            elif method == "PUT":
                response = await asyncio.to_thread(
                    self.rest_client.http.put, 
                    endpoint, 
                    data=data, 
                    timeout=30
                )
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            if hasattr(response, 'json') and callable(response.json):
                return response.json()
            elif hasattr(response, 'status_code'):
                if 200 <= response.status_code < 300:
                    return {"success": True}
                else:
                    return {"success": False, "error": f"HTTP {response.status_code}"}
            else:
                return {"success": True, "response": response}
            
        except Exception as e:
            return {"success": False, "error": str(e)}


def get_middleware_sync() -> Optional[MiddlewareSyncService]:
    """Get the global middleware sync instance"""
    global _global_middleware_sync
    
    if _global_middleware_sync is None:
        try:
            config = SDKConfig()
            _global_middleware_sync = MiddlewareSyncService(config)
        except Exception as e:
            console.print(f"Could not initialize middleware sync: {e}")
            _global_middleware_sync = None
    
    return _global_middleware_sync
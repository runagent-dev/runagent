import json
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from rich.console import Console
from runagent.sdk.rest_client import RestClient
from runagent.sdk.config import SDKConfig

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
            
            # If authentication was successful during setup, enable sync
            if hasattr(config, '_config') and config._config.get("auth_validated"):
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
            console.print(f"[cyan]Syncing agent {agent_id[:8]}... to middleware...[/cyan]")
            
            sync_data = {
                "local_agent_id": agent_id,
                "name": agent_data.get("name", "Local Agent"),
                "framework": agent_data.get("framework", "unknown"),
                "version": agent_data.get("version", "1.0.0"),
                "path": agent_data.get("path", ""),
                "host": agent_data.get("host", "127.0.0.1"),
                "port": agent_data.get("port", 8450),
                "entrypoints": agent_data.get("entrypoints", []),
                "status": "running",
                "sync_source": "local_server"
            }
            
            console.print(f"[dim]Sending POST to /local-agents[/dim]")
            console.print(f"[dim]Full URL: {self.rest_client.base_url}/local-agents[/dim]")
            
            # Make direct HTTP call instead of using _make_async_request
            try:
                response = self.rest_client.http.post("/local-agents", data=sync_data, timeout=30)
                result = response.json() if hasattr(response, 'json') else response
                
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


    async def sync_invocation_start(self, invocation_data: Dict[str, Any]) -> Optional[str]:
        """Sync invocation start to middleware"""
        if not self.is_sync_enabled():
            return None
            
        try:
            console.print(f"[cyan]📡 Syncing invocation start...[/cyan]")
            
            sync_payload = {
                "agent_id": invocation_data.get("agent_id"),
                "local_execution_id": invocation_data.get("local_execution_id"),
                "input_data": invocation_data.get("input_data", {}),
                "entrypoint_tag": invocation_data.get("entrypoint_tag", ""),
                "sdk_type": invocation_data.get("sdk_type", "local_server"),
                "client_info": invocation_data.get("client_info", {})
            }
            
            console.print(f"[dim]POST to /local-agents/invocations[/dim]")
            
            response = self.rest_client.http.post("/local-agents/invocations", data=sync_payload, timeout=30)
            result = response.json() if hasattr(response, 'json') else response
            
            console.print(f"[cyan]Response: {result}[/cyan]")
            
            if result.get("success"):
                execution_id = result.get("data", {}).get("id")
                if execution_id:
                    console.print(f"[green]✅ Invocation synced: {execution_id[:8]}...[/green]")
                    return execution_id
            
            return None
            
        except Exception as e:
            console.print(f"[red]❌ Invocation sync error: {str(e)}[/red]")
            return None


    async def sync_invocation_complete(self, execution_id: str, completion_data: Dict[str, Any]) -> bool:
        """Sync invocation completion to middleware"""
        if not self.is_sync_enabled() or not execution_id:
            return False
            
        try:
            console.print(f"[cyan]📡 Syncing completion: {execution_id[:8]}...[/cyan]")
            
            update_payload = {}
            
            if completion_data.get("output_data"):
                update_payload["output_data"] = completion_data["output_data"]
            
            if completion_data.get("error_detail"):
                update_payload["error_detail"] = completion_data["error_detail"]
            
            if completion_data.get("execution_time_ms"):
                update_payload["execution_time_ms"] = completion_data["execution_time_ms"]
            
            if completion_data.get("status"):
                update_payload["status"] = completion_data["status"]
            
            console.print(f"[dim]PUT to /local-agents/invocations/{execution_id[:8]}...[/dim]")
            
            response = self.rest_client.http.put(f"/local-agents/invocations/{execution_id}", data=update_payload, timeout=30)
            result = response.json() if hasattr(response, 'json') else response
            
            console.print(f"[cyan]Response: {result}[/cyan]")
            
            if result.get("success"):
                console.print(f"[green]✅ Completion synced[/green]")
                return True
            
            return False
            
        except Exception as e:
            console.print(f"[red]❌ Completion sync error: {str(e)}[/red]")
            return False

    def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status with detailed info"""
        return {
            "sync_enabled": getattr(self, 'sync_enabled', False),
            "api_configured": bool(getattr(self, 'api_key', None)),
            "auth_validated": getattr(self.config, '_config', {}).get("auth_validated", False),
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
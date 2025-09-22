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

        self.sync_enabled = False
        self.enabled = False

        # Check if we have a valid API key
        self.api_key = getattr(config, 'api_key', None)
        if not self.api_key:
            console.print("[dim]No API key configured - middleware sync disabled[/dim]")
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
                
        except Exception as e:
            console.print(f"[red]Could not initialize middleware sync: {e}[/red]")
            self.rest_client = None

    def is_sync_enabled(self) -> bool:
        """Public method to check if sync is enabled"""
        return self.sync_enabled
    
    async def sync_agent_startup(self, agent_id: str, agent_data: Dict[str, Any]) -> bool:
        """Sync agent data when local server starts"""
        if not self.is_sync_enabled():
            console.print("[dim]Middleware sync disabled - agent will run in local-only mode[/dim]")
            return False
            
        try:
            console.print(f"Syncing agent {agent_id} to middleware...")
            
            # FIXED: Use simplified structure - agent_id becomes the main ID
            sync_data = {
                "local_agent_id": agent_id,  # This becomes the main agent ID in middleware
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
            
            response = await self._make_async_request("POST", "/local-agents", sync_data)
            
            if response.get("success"):
                console.print("Agent synced successfully to middleware")
                return True
            else:
                console.print(f"Agent sync failed: {response.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            console.print(f"Agent sync error: {str(e)}")
            return False

    async def sync_invocation_start(self, invocation_data: Dict[str, Any]) -> Optional[str]:
        """Sync invocation start to middleware - FIXED for simplified ID structure"""
        if not self.is_sync_enabled():
            return None
            
        try:
            # FIXED: Use simplified structure
            sync_payload = {
                "agent_id": invocation_data.get("agent_id"),  # Main agent ID (no separate local_agent_id)
                "local_execution_id": invocation_data.get("local_execution_id"),  # This becomes main execution ID
                "input_data": invocation_data.get("input_data", {}),
                "entrypoint_tag": invocation_data.get("entrypoint_tag", ""),
                "sdk_type": invocation_data.get("sdk_type", "local_server"),
                "client_info": invocation_data.get("client_info", {})
            }
            
            response = await self._make_async_request(
                "POST",
                "/local-agents/invocations", 
                sync_payload
            )
            
            if response.get("success"):
                # Return the execution ID (which is now the main ID)
                return response.get("id")
            
        except Exception as e:
            console.print(f"Invocation start sync error: {str(e)}")
        
        return None

    async def sync_invocation_complete(self, execution_id: str, completion_data: Dict[str, Any]) -> bool:
        """Sync invocation completion to middleware - FIXED for simplified ID structure"""
        if not self.is_sync_enabled() or not execution_id:
            return False
            
        try:
            # FIXED: Use main execution ID directly (no separate local_execution_id)
            response = await self._make_async_request(
                "PUT", 
                f"/local-agents/invocations/{execution_id}",  # execution_id is now the main ID
                completion_data
            )
            
            return response.get("success", False)
            
        except Exception as e:
            console.print(f"Invocation completion sync error: {str(e)}")
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
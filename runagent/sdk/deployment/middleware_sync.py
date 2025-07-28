# runagent/sdk/deployment/middleware_sync.py - FIX THE GLOBAL VARIABLE BUG

import json
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from rich.console import Console

console = Console()

# ⭐ FIX: Initialize global variable at module level
_global_middleware_sync = None


class MiddlewareSyncService:
    """Service to sync local agent data with middleware - FIXED VERSION"""
    
    def __init__(self, config):
        self.config = config
        self.rest_client = None
        self.auth_validated = False
        
        # Check if we have a valid API key FIRST
        self.api_key = getattr(config, 'api_key', None)
        if not self.api_key:
            console.print("[dim]No API key configured - middleware sync disabled[/dim]")
            self.sync_enabled = False
            self.enabled = False
            return
        
        # Only initialize RestClient if we have an API key
        try:
            from runagent.sdk.rest_client import RestClient
            self.rest_client = RestClient(
                base_url=config.base_url,
                api_key=self.api_key
            )
            
            # Test authentication
            self.auth_validated = self._test_authentication()
            if self.auth_validated:
                console.print("[green]✅ API key validated - middleware sync enabled[/green]")
                self.sync_enabled = True
                self.enabled = True
            else:
                console.print("[yellow]⚠️ API key invalid - middleware sync disabled[/yellow]")
                self.sync_enabled = False
                self.enabled = False
                self.rest_client = None
                
        except Exception as e:
            console.print(f"⚠️ [yellow]Could not initialize middleware sync: {e}[/yellow]")
            self.sync_enabled = False
            self.enabled = False
            self.rest_client = None

    def _test_authentication(self) -> bool:
        """Test authentication before enabling sync"""
        if not self.rest_client or not self.api_key:
            return False
            
        try:
            # Test with the auth validation endpoint
            response = self.rest_client.http.get("/auth/validate", timeout=10)
            
            if response.status_code == 200:
                auth_data = response.json()
                if auth_data.get("status") == "success":
                    console.print(f"[dim]Authenticated as: {auth_data.get('user', {}).get('email', 'Unknown')}[/dim]")
                    return True
            
            console.print(f"[yellow]Authentication failed: HTTP {response.status_code}[/yellow]")
            return False
            
        except Exception as e:
            console.print(f"[dim]Authentication test failed: {str(e)}[/dim]")
            return False
    
    def is_sync_enabled(self) -> bool:
        """Public method to check if sync is enabled"""
        return getattr(self, 'sync_enabled', False) and getattr(self, 'auth_validated', False)
    
    async def sync_agent_startup(self, agent_id: str, agent_data: Dict[str, Any]) -> bool:
        """Sync agent data when local server starts - FIXED VERSION"""
        
        # CRITICAL: Check if sync is enabled FIRST
        if not self.is_sync_enabled():
            console.print("[dim]Middleware sync disabled - agent will run in local-only mode[/dim]")
            return False
            
        try:
            console.print(f"🔄 [cyan]Syncing agent {agent_id} to middleware...[/cyan]")
            
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
                "sync_timestamp": datetime.utcnow().isoformat()
            }
            
            response = await self._make_async_request("POST", "/local-agents", sync_data)
            
            if response.get("success"):
                console.print(f"✅ [green]Agent synced successfully to middleware[/green]")
                console.print(f"🔍 [dim]Project ID: {response.get('project_id', 'Unknown')}[/dim]")
                return True
            else:
                console.print(f"⚠️ [yellow]Agent sync failed: {response.get('error', 'Unknown error')}[/yellow]")
                # Don't disable sync completely - might be temporary
                return False
                
        except Exception as e:
            console.print(f"❌ [red]Agent sync error: {str(e)}[/red]")
            return False

    async def sync_agent_logs(self, logs_data: List[Dict[str, Any]]) -> bool:
        """Sync multiple agent logs to middleware - FIXED VERSION"""
        
        # CRITICAL: Don't try to sync if not enabled
        if not self.is_sync_enabled() or not logs_data:
            return False
            
        try:
            console.print(f"📋 [dim]Syncing {len(logs_data)} logs to middleware...[/dim]")
            
            # Prepare logs for middleware
            middleware_logs = []
            for log in logs_data:
                middleware_log = {
                    "agent_id": log["agent_id"],
                    "log_level": log["log_level"],
                    "message": log["message"],
                    "execution_id": log.get("execution_id"),
                    "timestamp": log["timestamp"].isoformat() if hasattr(log["timestamp"], 'isoformat') else str(log["timestamp"]),
                    "source": "local_server"
                }
                middleware_logs.append(middleware_log)
            
            # Send logs to middleware
            response = await self._make_async_request(
                "POST", 
                "/agent-logs/bulk", 
                {"logs": middleware_logs}
            )
            
            if response.get("success"):
                console.print(f"📋 [dim]Successfully synced {len(logs_data)} logs to middleware[/dim]")
                return True
            else:
                console.print(f"⚠️ [yellow]Log sync failed: {response.get('error')}[/yellow]")
                return False
                
        except Exception as e:
            console.print(f"❌ [red]Log sync error: {str(e)}[/red]")
            return False

    async def sync_invocation_start(self, invocation_data: Dict[str, Any]) -> Optional[str]:
        """Sync invocation start to middleware and return middleware invocation ID"""
        if not self.sync_enabled:
            return None
            
        try:
            console.print(f"🚀 [dim]Syncing invocation start to middleware...[/dim]")
            
            middleware_data = {
                "local_agent_id": invocation_data["agent_id"],
                "input_data": invocation_data["input_data"],
                "entrypoint_tag": invocation_data.get("entrypoint_tag"),
                "source": "local",
                "sdk_type": invocation_data.get("sdk_type", "local_server"),
                "client_info": invocation_data.get("client_info", {}),
                "local_timestamp": datetime.utcnow().timestamp()
            }
            
            response = await self._make_async_request("POST", "/local-invocations", middleware_data)
            
            if response.get("success"):
                middleware_invocation_id = response.get("invocation_id")
                console.print(f"📊 [dim]Invocation synced to middleware: {middleware_invocation_id[:8]}...[/dim]")
                return middleware_invocation_id
            else:
                console.print(f"⚠️ [yellow]Invocation sync failed: {response.get('error')}[/yellow]")
                return None
                
        except Exception as e:
            console.print(f"❌ [red]Invocation sync error: {str(e)}[/red]")
            return None

    async def sync_invocation_complete(self, middleware_invocation_id: str, completion_data: Dict[str, Any]) -> bool:
        """Sync invocation completion to middleware"""
        if not self.sync_enabled or not middleware_invocation_id:
            return False
            
        try:
            console.print(f"✅ [dim]Syncing invocation completion to middleware...[/dim]")
            
            update_data = {
                "output_data": completion_data.get("output_data"),
                "error_detail": completion_data.get("error_detail"),
                "execution_time_ms": completion_data.get("execution_time_ms"),
                "completed_timestamp": datetime.utcnow().timestamp()
            }
            
            response = await self._make_async_request(
                "PUT", 
                f"/local-invocations/{middleware_invocation_id}", 
                update_data
            )
            
            if response.get("success"):
                console.print(f"📊 [dim]Invocation completion synced to middleware[/dim]")
                return True
            else:
                console.print(f"⚠️ [yellow]Invocation completion sync failed: {response.get('error')}[/yellow]")
                return False
                
        except Exception as e:
            console.print(f"❌ [red]Invocation completion sync error: {str(e)}[/red]")
            return False

    def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status with detailed info"""
        return {
            "sync_enabled": getattr(self, 'sync_enabled', False),
            "api_configured": bool(getattr(self, 'api_key', None)),
            "auth_validated": getattr(self, 'auth_validated', False),
            "base_url": getattr(self.config, 'base_url', None),
            "middleware_available": self._test_middleware_connection() if getattr(self, 'rest_client', None) else False
        }

    def test_connection(self) -> Dict[str, Any]:
        """Test middleware connection and return detailed result"""
        try:
            result = self._test_middleware_connection()
            
            if isinstance(result, bool):
                return {
                    "success": result,
                    "error": None if result else "Connection failed"
                }
            elif isinstance(result, dict):
                return result
            else:
                return {
                    "success": False,
                    "error": "Invalid response format"
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

    async def _make_async_request(self, method: str, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make async HTTP request to middleware - FIXED VERSION"""
        if not getattr(self, 'rest_client', None) or not self.is_sync_enabled():
            return {"success": False, "error": "Middleware sync not available"}
            
        try:
            # Use the existing RestClient for consistency
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
            
            # Parse the response properly
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
    """Get the global middleware sync instance - FIXED with proper global variable"""
    global _global_middleware_sync
    
    if _global_middleware_sync is None:
        try:
            from runagent.sdk.config import SDKConfig
            config = SDKConfig()
            _global_middleware_sync = MiddlewareSyncService(config)
        except Exception as e:
            console.print(f"⚠️ [yellow]Could not initialize middleware sync: {e}[/yellow]")
            _global_middleware_sync = None
    
    return _global_middleware_sync


# Create an alias for backwards compatibility
class MiddlewareSync:
    """Alias for MiddlewareSyncService for backwards compatibility"""
    
    def __init__(self, config):
        self._service = MiddlewareSyncService(config)
    
    def __getattr__(self, name):
        return getattr(self._service, name)
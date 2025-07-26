# runagent/sdk/middleware_sync.py
"""
Middleware synchronization service for syncing local agent data to middleware
"""

import json
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from rich.console import Console

from runagent.sdk.constants import DEFAULT_BASE_URL
from .rest_client import RestClient
from .config import SDKConfig

console = Console()


class MiddlewareSyncService:
    """Service to sync local agent data with middleware"""
    
    def __init__(self, config: SDKConfig):
        self.config = config
        self.rest_client = RestClient(
            base_url=config.base_url,
            api_key=config.api_key
        ) if config.is_configured() else None
        self.sync_enabled = self._check_sync_enabled()
    
    def _check_sync_enabled(self) -> bool:
        """Check if middleware sync is enabled"""
        return bool(self.rest_client and self.config.api_key)
    
    async def sync_agent_startup(self, agent_id: str, agent_data: Dict[str, Any]) -> bool:
        """Sync agent data when local server starts"""
        if not self.sync_enabled:
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
                return True
            else:
                console.print(f"⚠️ [yellow]Agent sync failed: {response.get('error', 'Unknown error')}[/yellow]")
                return False
                
        except Exception as e:
            console.print(f"❌ [red]Agent sync error: {str(e)}[/red]")
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
    
    async def _make_async_request(self, method: str, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make async HTTP request to middleware"""
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
            
            return response.json()
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status"""
        return {
            "sync_enabled": self.sync_enabled,
            "api_configured": bool(self.config.api_key),
            "base_url": self.config.base_url,
            "middleware_available": self._test_middleware_connection()
        }
    
    def _test_middleware_connection(self) -> bool:
        """Test if middleware is reachable"""
        if not self.rest_client:
            return False
            
        try:
            response = self.rest_client.http.get("/health", timeout=5)
            return response.status_code == 200
        except:
            return False
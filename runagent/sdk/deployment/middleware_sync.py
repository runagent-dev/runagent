"""
Middleware synchronization service for syncing local agent data to middleware
"""

import json
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from rich.console import Console

console = Console()


class MiddlewareSyncService:
    """Service to sync local agent data with middleware"""
    
    def __init__(self, config):
        self.config = config
        self.rest_client = None
        
        # Import RestClient only if config is available and configured
        if hasattr(config, 'is_configured') and config.is_configured():
            try:
                from runagent.sdk.rest_client import RestClient
                self.rest_client = RestClient(
                    base_url=config.base_url,
                    api_key=config.api_key
                )
            except Exception as e:
                console.print(f"⚠️ [yellow]Could not initialize RestClient: {e}[/yellow]")
                self.rest_client = None
        
        self.sync_enabled = self._check_sync_enabled()
        self.enabled = self.sync_enabled  
        self.enabled = self.sync_enabled  

    def _check_sync_enabled(self) -> bool:
        """Check if middleware sync is enabled"""
        return bool(
            self.rest_client and 
            hasattr(self.config, 'api_key') and 
            self.config.api_key
        )
    
    def is_sync_enabled(self) -> bool:
        """Public method to check if sync is enabled"""
        return self.sync_enabled
    
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
        """Test if middleware is reachable - FIXED"""
        if not self.rest_client:
            return False
            
        try:
            response = self.rest_client.http.get("/health", timeout=5)
            return response.status_code == 200
        except Exception as e:
            console.print(f"[dim]Connection test failed: {str(e)}[/dim]")
            return False

    def remove_agent(self, agent_id: str) -> bool:
        """Remove agent from middleware (called on shutdown)"""
        if not self.sync_enabled:
            return False
            
        try:
            # This could be implemented if middleware supports agent removal
            console.print(f"🧹 [dim]Would remove agent {agent_id} from middleware[/dim]")
            return True
        except Exception as e:
            console.print(f"⚠️ [yellow]Could not remove agent from middleware: {e}[/yellow]")
            return False

    # Rest of the methods remain the same...
    def remove_agent(self, agent_id: str) -> bool:
        """Remove agent from middleware (called on shutdown)"""
        if not self.sync_enabled:
            return False
            
        try:

            console.print(f"🧹 [dim]Would remove agent {agent_id} from middleware[/dim]")
            return True
        except Exception as e:
            console.print(f"⚠️ [yellow]Could not remove agent from middleware: {e}[/yellow]")
            return False


    async def sync_agent_startup(self, agent_id: str, agent_data: Dict[str, Any]) -> bool:
        """Sync agent data when local server starts - ENHANCED WITH DEBUG"""
        if not self.sync_enabled:
            return False
            
        try:
            console.print(f"🔄 [cyan]Syncing agent {agent_id} to middleware...[/cyan]")
            
            # DEBUG: Print what we're syncing
            console.print(f"🔍 [dim]Agent data being synced:[/dim]")
            console.print(f"   • Agent ID: {agent_id}")
            console.print(f"   • Name: {agent_data.get('name', 'Unknown')}")
            console.print(f"   • Framework: {agent_data.get('framework', 'Unknown')}")
            console.print(f"   • Host:Port: {agent_data.get('host')}:{agent_data.get('port')}")
            
            sync_data = {
                "local_agent_id": agent_id,  # This should match the agent_id parameter
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
            
            # DEBUG: Verify the local_agent_id matches
            console.print(f"🔍 [dim]Sync payload local_agent_id: {sync_data['local_agent_id']}[/dim]")
            
            response = await self._make_async_request("POST", "/local-agents", sync_data)
            
            if response.get("success"):
                console.print(f"✅ [green]Agent synced successfully to middleware[/green]")
                console.print(f"🔍 [dim]Middleware response: {response.get('action', 'unknown')}[/dim]")
                return True
            else:
                console.print(f"⚠️ [yellow]Agent sync failed: {response.get('error', 'Unknown error')}[/yellow]")
                return False
                
        except Exception as e:
            console.print(f"❌ [red]Agent sync error: {str(e)}[/red]")
            return False

    async def sync_agent_logs(self, logs_data: List[Dict[str, Any]]) -> bool:
        """Sync multiple agent logs to middleware - ENHANCED WITH DEBUG"""
        if not self.sync_enabled or not logs_data:
            return False
            
        try:
            console.print(f"📋 [dim]Syncing {len(logs_data)} logs to middleware...[/dim]")
            
            # DEBUG: Print first log's agent_id
            if logs_data:
                first_log = logs_data[0]
                console.print(f"🔍 [dim]First log agent_id: {first_log.get('agent_id')}[/dim]")
            
            # Prepare logs for middleware
            middleware_logs = []
            for log in logs_data:
                middleware_log = {
                    "agent_id": log["agent_id"],  # This should be the same agent_id
                    "log_level": log["log_level"],
                    "message": log["message"],
                    "execution_id": log.get("execution_id"),
                    "timestamp": log["timestamp"].isoformat() if hasattr(log["timestamp"], 'isoformat') else str(log["timestamp"]),
                    "source": "local_server"
                }
                middleware_logs.append(middleware_log)
            
            # DEBUG: Print what we're sending
            console.print(f"🔍 [dim]Sending {len(middleware_logs)} logs to /agent-logs/bulk[/dim]")
            
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
                # DEBUG: Print the full error response
                console.print(f"🔍 [dim]Full error response: {response}[/dim]")
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
    
    async def _make_async_request(self, method: str, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make async HTTP request to middleware"""
        if not self.rest_client:
            return {"success": False, "error": "No REST client available"}
            
        try:
            # Use the correct RestClient method
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
            if hasattr(response, 'json'):
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



    async def sync_agent_logs(self, logs_data: List[Dict[str, Any]]) -> bool:
        """Sync multiple agent logs to middleware"""
        if not self.sync_enabled or not logs_data:
            return False
            
        try:
            console.print(f"📋 [dim]Syncing {len(logs_data)} logs to middleware...[/dim]")
            
            # Prepare logs for middleware
            middleware_logs = []
            for log in logs_data:
                middleware_logs.append({
                    "agent_id": log["agent_id"],
                    "log_level": log["log_level"],
                    "message": log["message"],
                    "execution_id": log.get("execution_id"),
                    "timestamp": log["timestamp"].isoformat() if hasattr(log["timestamp"], 'isoformat') else str(log["timestamp"]),
                    "source": "local_server"
                })
            
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

    async def sync_single_log(self, log_data: Dict[str, Any]) -> bool:
        """Sync a single log entry to middleware"""
        if not self.sync_enabled:
            return False
            
        try:
            middleware_log = {
                "agent_id": log_data["agent_id"],
                "log_level": log_data["log_level"],
                "message": log_data["message"],
                "execution_id": log_data.get("execution_id"),
                "timestamp": log_data["timestamp"].isoformat() if hasattr(log_data["timestamp"], 'isoformat') else str(log_data["timestamp"]),
                "source": "local_server"
            }
            
            response = await self._make_async_request(
                "POST", 
                "/agent-logs", 
                middleware_log
            )
            
            return response.get("success", False)
            
        except Exception as e:
            console.print(f"❌ [red]Single log sync error: {str(e)}[/red]")
            return False
    
    def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status"""
        return {
            "sync_enabled": self.sync_enabled,
            "api_configured": bool(getattr(self.config, 'api_key', None)),
            "base_url": getattr(self.config, 'base_url', None),
            "middleware_available": self._test_middleware_connection()
        }
    
    def _test_middleware_connection(self) -> bool:
        """Test if middleware is reachable"""
        if not self.rest_client:
            return False
            
        try:
            # Use the correct method to make HTTP requests
            response = self.rest_client.http.get("/health", timeout=5)
            return response.status_code == 200
        except Exception as e:
            console.print(f"🔍 [dim]Connection test failed: {str(e)}[/dim]")
            return False


# Global instance for easy access
_global_middleware_sync = None


def get_middleware_sync() -> Optional[MiddlewareSyncService]:
    """Get the global middleware sync instance"""
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
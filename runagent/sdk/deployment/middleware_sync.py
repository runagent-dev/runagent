# File: runagent/sdk/middleware_sync.py
# New file to handle middleware synchronization

import json
import time
from typing import Dict, Any, Optional
from rich.console import Console
from runagent.utils.config import Config
from runagent.sdk.rest_client import RestClient

console = Console()


class MiddlewareSync:
    """Service to sync local invocations to middleware"""
    
    def __init__(self):
        self.rest_client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize REST client if API key is available"""
        api_key = Config.get_api_key()
        base_url = Config.get_base_url()
        
        if api_key and base_url:
            try:
                self.rest_client = RestClient(api_key=api_key, base_url=base_url)
            except Exception as e:
                console.print(f"[dim]Warning: Could not initialize middleware client: {e}[/dim]")
                self.rest_client = None
    
    def is_sync_enabled(self) -> bool:
        """Check if sync is enabled and properly configured"""
        # Check if sync is disabled by user
        user_config = Config.get_user_config()
        if not user_config.get("local_sync_enabled", True):
            return False
        
        # Check if API key is available
        if not Config.get_api_key():
            return False
        
        # Check if client is initialized
        if not self.rest_client:
            return False
        
        return True
    
    def sync_invocation_start(
        self, 
        agent_id: str, 
        input_data: Dict[str, Any], 
        entrypoint_tag: str,
        client_info: Dict[str, Any] = None
    ) -> Optional[str]:
        """
        Sync invocation start to middleware
        
        Returns:
            middleware_invocation_id if successful, None otherwise
        """
        if not self.is_sync_enabled():
            return None
        
        try:
            sync_data = {
                "local_agent_id": agent_id,
                "input_data": input_data,
                "entrypoint_tag": entrypoint_tag,
                "source": "local",
                "sdk_type": "local_server",
                "client_info": client_info or {},
                "local_timestamp": time.time()
            }
            
            # Call middleware API to create invocation record
            response = self.rest_client._make_request(
                "POST", 
                "/api/v1/local-invocations", 
                json=sync_data
            )
            
            if response.get("success"):
                middleware_id = response.get("invocation_id")
                console.print(f"[dim]🔄 Synced invocation start to middleware: {middleware_id[:8]}...[/dim]")
                return middleware_id
            
        except Exception as e:
            # Don't fail the main operation if sync fails
            console.print(f"[dim]⚠️ Failed to sync invocation start: {e}[/dim]")
        
        return None
    
    def sync_invocation_complete(
        self,
        middleware_invocation_id: str,
        output_data: Any = None,
        error_detail: str = None,
        execution_time_ms: float = None
    ) -> bool:
        """
        Sync invocation completion to middleware
        
        Returns:
            True if successful, False otherwise
        """
        if not self.is_sync_enabled() or not middleware_invocation_id:
            return False
        
        try:
            sync_data = {
                "output_data": output_data,
                "error_detail": error_detail,
                "execution_time_ms": execution_time_ms,
                "completed_timestamp": time.time()
            }
            
            # Call middleware API to update invocation record
            response = self.rest_client._make_request(
                "PUT", 
                f"/api/v1/local-invocations/{middleware_invocation_id}", 
                json=sync_data
            )
            
            if response.get("success"):
                console.print(f"[dim]✅ Synced invocation completion to middleware: {middleware_invocation_id[:8]}...[/dim]")
                return True
            
        except Exception as e:
            # Don't fail the main operation if sync fails
            console.print(f"[dim]⚠️ Failed to sync invocation completion: {e}[/dim]")
        
        return False
    
    def test_connection(self) -> Dict[str, Any]:
        """Test connection to middleware"""
        if not self.rest_client:
            return {
                "success": False,
                "error": "REST client not initialized. Check API key configuration."
            }
        
        try:
            # Test with a simple ping or health check
            response = self.rest_client._make_request("GET", "/health")
            return {
                "success": True,
                "middleware_status": response.get("status"),
                "response": response
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


# Global instance for easy access
_middleware_sync = None

def get_middleware_sync() -> MiddlewareSync:
    """Get global middleware sync instance"""
    global _middleware_sync
    if _middleware_sync is None:
        _middleware_sync = MiddlewareSync()
    return _middleware_sync